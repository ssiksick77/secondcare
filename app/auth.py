"""구글 로그인 (OpenID Connect) + 서명 쿠키 세션.

- 모든 화면·API 는 로그인 필수 (main.py 미들웨어). 화면은 /login 으로, /api/* 는 401.
- 허용 이메일: LEDGER_ALLOWED_EMAILS (쉼표 구분, app/.env). 비어 있으면 아무도 로그인할 수 없다.
- 세션 쿠키: HMAC 서명 JSON, 30일. 서명 키 LEDGER_SESSION_SECRET 은 없으면 첫 실행 때 만들어 .env 에 저장.
- OAuth 클라이언트: LEDGER_OAUTH_CLIENT (기본 google_client_secret.json, 드라이브와 같은 파일도 됨).
  리다이렉트 URI: LEDGER_OAUTH_REDIRECT (기본 http://127.0.0.1:<포트>/auth/callback). 다른 PC 접속 때는 이 값만 바꾼다.
- 검사용 우회: LEDGER_AUTH_BYPASS=<이메일> 이면 모든 요청을 그 이메일로 로그인한 것으로 본다 (구글 호출 없음).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

import settings

APP_DIR = Path(__file__).resolve().parent
COOKIE = "ledger_session"
STATE_COOKIE = "ledger_oauth_state"
SESSION_DAYS = 30
SCOPES = ["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]


class AuthError(Exception):
    pass


# ---------- 설정 ----------
def bypass_email() -> str:
    return os.environ.get("LEDGER_AUTH_BYPASS", "").strip()


def allowed_emails() -> list[str]:
    return [e.lower() for e in settings._split(settings.get("LEDGER_ALLOWED_EMAILS"))]


def is_allowed(email: str) -> bool:
    return bool(email) and email.lower() in allowed_emails()


def redirect_uri() -> str:
    v = settings.get("LEDGER_OAUTH_REDIRECT").strip()
    if v:
        return v
    port = os.environ.get("LEDGER_PORT", "8791")
    return f"http://127.0.0.1:{port}/auth/callback"


def client_path() -> Path:
    v = settings.get("LEDGER_OAUTH_CLIENT").strip() or "google_client_secret.json"
    p = Path(v)
    return p if p.is_absolute() else APP_DIR / p


def client_info() -> dict:
    """클라이언트 JSON 의 web 또는 installed 항목."""
    p = client_path()
    if not p.exists():
        raise AuthError(f"OAuth 클라이언트 파일이 없습니다: {p.name}. README 의 '구글 로그인 설정'을 보세요.")
    data = json.loads(p.read_text(encoding="utf-8"))
    info = data.get("web") or data.get("installed")
    if not info or not info.get("client_id"):
        raise AuthError(f"OAuth 클라이언트 파일 형식이 아닙니다: {p.name}")
    return info


def configured() -> bool:
    return bool(bypass_email()) or client_path().exists()


def _secret() -> bytes:
    v = settings.get("LEDGER_SESSION_SECRET").strip()
    if not v:
        v = secrets.token_urlsafe(32)
        settings.save({"LEDGER_SESSION_SECRET": v})
    return v.encode()


# ---------- 서명 토큰 ----------
def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign(payload: dict) -> str:
    body = _b64(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode())
    sig = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify(token: str | None) -> dict | None:
    """서명이 맞고 exp 가 남아 있으면 payload, 아니면 None."""
    if not token or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    good = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(good, sig):
        return None
    try:
        payload = json.loads(_unb64(body))
    except Exception:
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return payload


def session_token(email: str, name: str = "") -> str:
    return sign({"email": email.lower(), "name": name, "exp": int(time.time()) + SESSION_DAYS * 86400})


def user_from_request(request) -> dict | None:
    """요청의 로그인 사용자 {email, name} 또는 None. 우회 이메일이 있으면 항상 그 사용자."""
    bp = bypass_email()
    if bp:
        return {"email": bp.lower(), "name": bp.split("@")[0]}
    p = verify(request.cookies.get(COOKIE))
    if not p or not is_allowed(p.get("email", "")):
        return None
    return {"email": p["email"], "name": p.get("name", "")}


# ---------- OAuth 흐름 ----------
def _flow(state: str | None = None):
    from google_auth_oauthlib.flow import Flow
    uri = redirect_uri()
    if uri.startswith("http://"):  # 로컬(루프백)은 http. oauthlib 기본은 https 만 허용
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")  # 구글이 범위 순서·표기를 바꿔 돌려줌
    info = client_info()
    flow = Flow.from_client_config({"web": info}, scopes=SCOPES, state=state)
    flow.redirect_uri = uri
    return flow


def login_url() -> tuple[str, str]:
    """(구글 인증 주소, state 쿠키값). state 와 PKCE code verifier 를 서명 쿠키로 보관해 콜백에서 쓴다.
    (Flow 는 요청마다 새로 만들므로 verifier 를 메모리에 둘 수 없다: 없으면 구글이 invalid_grant 'Missing code verifier')"""
    flow = _flow()
    url, state = flow.authorization_url(prompt="select_account", include_granted_scopes="false")
    return url, sign({"state": state, "verifier": flow.code_verifier, "exp": int(time.time()) + 600})


def finish_login(code: str, state: str, state_cookie: str | None) -> dict:
    """콜백: state 대조 → 토큰 교환 → ID 토큰 검증. {email, name} 반환. 허용 목록 검사는 호출자가 한다."""
    saved = verify(state_cookie)
    if not saved or saved.get("state") != state:
        raise AuthError("로그인 요청이 만료되었거나 일치하지 않습니다. 다시 시도하세요.")
    flow = _flow(state=state)
    flow.code_verifier = saved.get("verifier")
    flow.fetch_token(code=code)
    from google.oauth2 import id_token as gid
    from google.auth.transport.requests import Request
    info = gid.verify_oauth2_token(flow.credentials.id_token, Request(), client_info()["client_id"])
    email = (info.get("email") or "").lower()
    if not email or not info.get("email_verified", True):
        raise AuthError("구글 계정의 이메일을 확인할 수 없습니다.")
    return {"email": email, "name": info.get("name") or email.split("@")[0]}
