"""Google Drive 연동 (OAuth, drive.file 범위).

- 자격증명: app/google_client_secret.json (Google Cloud 콘솔에서 받은 데스크톱 앱 OAuth 클라이언트)
- 토큰: app/google_token.json (최초 1회 브라우저 로그인 후 저장, 자동 갱신)
- 루트: 내 드라이브/증빙관리 (앱이 생성). 아래에 YYYY/재원코드/거래번호 폴더.
- LEDGER_DRIVE_MOCK=1 이면 드라이브 대신 app/drive_mock/ 로컬 폴더에 저장 (테스트·오프라인용).
  LEDGER_DRIVE_MOCK_DIR 로 그 폴더를 바꿀 수 있다 (상대 경로는 app 폴더 기준).
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import threading
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
CLIENT_SECRET = APP_DIR / "google_client_secret.json"
TOKEN_PATH = APP_DIR / "google_token.json"
FOLDER_CACHE = APP_DIR / "drive_folders.json"
_MOCK_ENV = os.environ.get("LEDGER_DRIVE_MOCK_DIR", "").strip()
MOCK_DIR = (APP_DIR / _MOCK_ENV).resolve() if _MOCK_ENV else APP_DIR / "drive_mock"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
ROOT_NAME = "증빙관리"
REQUEST_ROOT = "신청"  # 신청 첨부: 내 드라이브/신청/YYYY/신청번호

_lock = threading.RLock()
_service = None


class DriveError(Exception):
    pass


def mock() -> bool:
    return os.environ.get("LEDGER_DRIVE_MOCK") == "1"


def configured() -> bool:
    return mock() or CLIENT_SECRET.exists()


def connected() -> bool:
    return mock() or (TOKEN_PATH.exists() and not _expired_flag())


EXPIRED_FLAG = APP_DIR / "google_token.expired"


def _expired_flag() -> bool:
    return EXPIRED_FLAG.exists()


def _mark_expired():
    EXPIRED_FLAG.write_text("expired", encoding="utf-8")


def _clear_expired():
    EXPIRED_FLAG.unlink(missing_ok=True)


def status() -> dict:
    return {"mock": mock(), "configured": configured(), "connected": connected(), "expired": _expired_flag(),
            "client_secret_path": str(CLIENT_SECRET), "root": ROOT_NAME}


# ---------- 인증 ----------
def _creds():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    if not TOKEN_PATH.exists():
        raise DriveError("구글 드라이브가 연결되지 않았습니다. 설정에서 '드라이브 연결'을 누르세요.")
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        except Exception as e:  # refresh token 만료(테스트 모드 7일) 등
            _mark_expired()
            raise DriveError("드라이브 인증이 만료되었습니다 (테스트 모드 앱은 7일마다 만료). 설정에서 '다시 연결'을 누르세요.") from e
    if not creds.valid:
        _mark_expired()
        raise DriveError("드라이브 인증이 만료되었습니다. 설정에서 '다시 연결'을 누르세요.")
    _clear_expired()
    return creds


def connect() -> dict:
    """브라우저를 열어 OAuth 동의 후 토큰 저장 (서버 PC에서 실행)."""
    if mock():
        return status()
    if not CLIENT_SECRET.exists():
        raise DriveError(f"OAuth 클라이언트 파일이 없습니다: {CLIENT_SECRET.name}. README 의 발급 절차를 따라 설정에서 업로드하세요.")
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    try:
        creds = flow.run_local_server(port=0, open_browser=True, prompt="consent", timeout_seconds=180,
                                      success_message="드라이브 연결이 완료되었습니다. 이 창을 닫고 앱으로 돌아가세요.")
    except Exception as e:
        msg = str(e)
        if "access_denied" in msg:
            raise DriveError("접근이 거부되었습니다. Google Cloud 콘솔의 '대상 → 테스트 사용자'에 이 계정을 추가했는지 확인하세요.") from e
        raise DriveError(f"로그인이 완료되지 않았습니다 (3분 초과 또는 취소). 다시 시도하세요. {msg[:120]}") from e
    if creds is None:
        raise DriveError("로그인이 완료되지 않았습니다 (3분 초과 또는 창 닫힘). 다시 시도하세요.")
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    _clear_expired()
    global _service
    _service = None
    return status()


def disconnect() -> dict:
    global _service
    _service = None
    TOKEN_PATH.unlink(missing_ok=True)
    FOLDER_CACHE.unlink(missing_ok=True)
    _clear_expired()
    return status()


def save_client_secret(data: bytes):
    try:
        j = json.loads(data.decode("utf-8"))
    except Exception:
        raise DriveError("JSON 파일이 아닙니다.")
    if not any(k in j for k in ("installed", "web")):
        raise DriveError("OAuth 클라이언트 JSON 형식이 아닙니다 ('installed' 항목 필요: 데스크톱 앱 유형으로 발급하세요).")
    if "web" in j and "installed" not in j:
        raise DriveError("'웹 애플리케이션' 유형입니다. '데스크톱 앱' 유형으로 다시 발급하세요.")
    CLIENT_SECRET.write_bytes(data)


def _svc():
    global _service
    if _service is None:
        from googleapiclient.discovery import build
        _service = build("drive", "v3", credentials=_creds(), cache_discovery=False)
    return _service


def _guard(thunk):
    try:
        return thunk()
    except DriveError:
        raise
    except Exception as e:  # googleapiclient.errors.HttpError 등
        msg = str(e)
        if "invalid_grant" in msg or "Token has been expired" in msg:
            _mark_expired()
            raise DriveError("드라이브 인증이 만료되었습니다. 설정에서 '다시 연결'을 누르세요.")
        raise DriveError(f"드라이브 오류: {msg[:200]}")


# ---------- 폴더 ----------
def _cache_load() -> dict:
    try:
        return json.loads(FOLDER_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _cache_save(d: dict):
    FOLDER_CACHE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def _find_or_create_folder(name: str, parent: str | None) -> str:
    svc = _svc()
    q = f"name = '{name.replace(chr(39), chr(92) + chr(39))}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    q += f" and '{parent}' in parents" if parent else " and 'root' in parents"
    res = svc.files().list(q=q, fields="files(id)", pageSize=5).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent:
        meta["parents"] = [parent]
    return svc.files().create(body=meta, fields="id").execute()["id"]


def ensure_folder(parts: list[str], root: str | None = None) -> dict:
    """root/parts... 폴더를 보장하고 {id, url} 반환. root 기본값은 증빙 루트(ROOT_NAME)."""
    root = root or ROOT_NAME
    key = "/".join([root] + parts)
    if mock():
        p = MOCK_DIR.joinpath(root, *parts)
        p.mkdir(parents=True, exist_ok=True)
        return {"id": key, "url": p.resolve().as_uri()}
    with _lock:
        cache = _cache_load()
        if key in cache:
            try:  # 폴더가 휴지통/삭제됐으면 캐시를 버리고 다시 만든다
                meta = _svc().files().get(fileId=cache[key]["id"], fields="trashed").execute()
                if not meta.get("trashed"):
                    return cache[key]
            except Exception:
                pass
            cache = {k: v for k, v in cache.items() if not k.startswith(key.split("/")[0])}
            _cache_save(cache)
        def run():
            parent = None
            path = []
            for name in [root] + parts:
                path.append(name)
                k = "/".join(path)
                if k in cache:
                    parent = cache[k]["id"]
                    continue
                parent = _find_or_create_folder(name, parent)
                cache[k] = {"id": parent, "url": f"https://drive.google.com/drive/folders/{parent}"}
            _cache_save(cache)
            return cache[key]
        return _guard(run)


# ---------- 파일 ----------
def upload(folder: dict, name: str, data: bytes, mime: str) -> dict:
    """파일 업로드 → {id, url, size}"""
    if mock():
        p = MOCK_DIR.joinpath(*folder["id"].split("/")) / name
        p.write_bytes(data)
        return {"id": f"mock:{p.relative_to(MOCK_DIR).as_posix()}", "url": p.resolve().as_uri(), "size": len(data)}
    from googleapiclient.http import MediaIoBaseUpload
    def run():
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime or "application/octet-stream", resumable=len(data) > 5 * 1024 * 1024)
        f = _svc().files().create(body={"name": name, "parents": [folder["id"]]}, media_body=media,
                                  fields="id, webViewLink, size").execute()
        return {"id": f["id"], "url": f.get("webViewLink", ""), "size": int(f.get("size") or len(data))}
    return _guard(run)


def trash(file_id: str):
    """드라이브 휴지통으로 이동 (복구 가능)."""
    if not file_id:
        return
    if file_id.startswith("mock:"):
        p = MOCK_DIR / file_id[5:]
        if p.exists():
            t = MOCK_DIR / "_trash"
            t.mkdir(exist_ok=True)
            shutil.move(str(p), str(t / p.name))
        return
    _guard(lambda: _svc().files().update(fileId=file_id, body={"trashed": True}).execute())


def rename(file_id: str, name: str) -> dict:
    """드라이브 파일 이름 변경 → {id, url}. 모의 모드는 파일을 옮기므로 id 가 바뀐다."""
    if file_id.startswith("mock:"):
        p = MOCK_DIR / file_id[5:]
        q = p.with_name(name)
        if p.exists() and p != q:
            p.rename(q)
        return {"id": f"mock:{q.relative_to(MOCK_DIR).as_posix()}", "url": q.resolve().as_uri()}
    _guard(lambda: _svc().files().update(fileId=file_id, body={"name": name}, fields="id").execute())
    return {"id": file_id, "url": file_url(file_id)}


def file_meta(file_id: str) -> dict | None:
    """드라이브의 현재 파일 정보 {name, trashed}. 없으면(삭제·권한 없음) None. 모의 모드는 파일 존재 여부로 판단."""
    if not file_id:
        return None
    if file_id.startswith("mock:"):
        p = MOCK_DIR / file_id[5:]
        return {"name": p.name, "trashed": False} if p.exists() else None
    def run():
        try:
            f = _svc().files().get(fileId=file_id, fields="name, trashed, parents").execute()
        except Exception as e:
            if "404" in str(e) or "notFound" in str(e):
                return None
            raise
        return {"name": f.get("name") or "", "trashed": bool(f.get("trashed")), "parents": list(f.get("parents") or [])}
    return _guard(run)


def fix_folder_name(folder_id: str, expected: str) -> bool:
    """폴더 이름이 expected(현재 번호)와 다르면 바꾸고 캐시 키도 옮긴다 (번호 재부여 뒤 정리). 바꿨으면 True."""
    if not folder_id or folder_id.startswith("mock:") or mock():
        return False
    def run():
        f = _svc().files().get(fileId=folder_id, fields="name").execute()
        if (f.get("name") or "") == expected:
            return False
        _svc().files().update(fileId=folder_id, body={"name": expected}, fields="id").execute()
        with _lock:
            cache = _cache_load()
            for k, v in list(cache.items()):
                if v.get("id") == folder_id:
                    del cache[k]
                    cache["/".join(k.split("/")[:-1] + [expected])] = v
            _cache_save(cache)
        return True
    return _guard(run)


def file_url(file_id: str) -> str:
    if file_id.startswith("mock:"):
        return (MOCK_DIR / file_id[5:]).resolve().as_uri()
    return f"https://drive.google.com/file/d/{file_id}/view"


# ---------- 썸네일 (증빙 표 미리보기) ----------
_IMG_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}


def _downscale(data: bytes, mime: str, box: int = 160) -> tuple[bytes, str]:
    """Pillow 가 있으면 작은 JPEG/PNG 로 줄임. 없거나 실패하면 원본 그대로."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        im.thumbnail((box, box))
        out = io.BytesIO()
        if im.mode in ("RGBA", "LA", "P"):
            im.save(out, "PNG", optimize=True)
            return out.getvalue(), "image/png"
        im.convert("RGB").save(out, "JPEG", quality=80)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return data, mime


def thumbnail(file_id: str) -> tuple[bytes, str] | None:
    """이미지 증빙의 작은 미리보기 (bytes, mime). 이미지가 아니거나 못 받으면 None."""
    if not file_id:
        return None
    if file_id.startswith("mock:"):
        root = MOCK_DIR.resolve()
        p = (MOCK_DIR / file_id[5:]).resolve()
        if root not in p.parents or not p.is_file():  # 모의 폴더 밖 경로는 거부
            return None
        mime = _IMG_EXT.get(p.suffix.lower())
        if not mime:
            return None
        return _downscale(p.read_bytes(), mime)
    if mock() or not connected():
        return None

    def meta():
        with _lock:
            return _svc().files().get(fileId=file_id, fields="thumbnailLink,mimeType").execute()
    m = _guard(meta)
    link = m.get("thumbnailLink")
    if not link or not str(m.get("mimeType", "")).startswith("image/"):
        return None
    from google.auth.transport.requests import AuthorizedSession
    res = AuthorizedSession(_creds()).get(link, timeout=10)
    if res.status_code != 200 or not res.content:
        return None
    return res.content, res.headers.get("Content-Type", "image/jpeg")


# ---------- 이름 규칙 ----------
_BAD = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def safe_part(s: str, limit: int = 40) -> str:
    s = _BAD.sub(" ", str(s or "")).strip().replace("_", "-")
    s = re.sub(r"\s+", " ", s)
    return s[:limit].strip() or "-"


def safe_ext(ext: str) -> str:
    """확장자 정제: safe_part 로 금지 문자(: 등, NTFS 대체 스트림 방지) 제거, 공백 제거, 10자 이하, 소문자. 비면 ''."""
    e = safe_part(str(ext or "").lstrip("."), 10).replace(" ", "").lower()
    return "" if e in ("", "-") else "." + e


def build_request_filename(number: str, item: str, original: str, existing: list[str]) -> str:
    """신청번호_품목_원본파일명(_n).ext — 같은 이름이 있으면 _2, _3"""
    original = str(original or "")
    stem, ext = (original.rsplit(".", 1) if "." in original else (original, ""))
    base = "_".join([safe_part(number, 20), safe_part(item), safe_part(stem, 60)])
    ext = safe_ext(ext)
    name, n = base + ext, 2
    taken = set(existing)
    while name in taken:
        name = f"{base}_{n}{ext}"
        n += 1
    return name


def build_filename(head: str, kind: str, amount, yymmdd: str, ext: str, existing: list[str]) -> str:
    """{재원|거래처}_증빙종류_금액_YYMMDD(_n).ext — 같은 이름이 있으면 _2, _3. 적요는 넣지 않는다 (2026-10-20 사용자 결정: 짧게, 내부 메모 노출 방지)"""
    amt = str(int(float(amount))) if str(amount).strip() not in ("", "None") else "0"
    base = "_".join([safe_part(head, 20), safe_part(kind, 20), amt, yymmdd])
    ext = safe_ext(ext)
    name, n = base + ext, 2
    taken = set(existing)
    while name in taken:
        name = f"{base}_{n}{ext}"
        n += 1
    return name
