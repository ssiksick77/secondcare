"""앱 설정: app/.env 파일을 읽고 쓰며 os.environ 에 즉시 반영한다 (서버 재시작 불필요).
환경변수 LEDGER_ENV 로 다른 설정 파일을 쓸 수 있다 (QA 장부 실행 run_qa.bat 등). 상대 경로는 app 폴더 기준."""
from __future__ import annotations

import os
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent


def env_path() -> Path:
    """설정 파일 경로: LEDGER_ENV 가 있으면 그 파일 (상대 경로는 app 폴더 기준), 없으면 app/.env."""
    v = os.environ.get("LEDGER_ENV", "").strip()
    if not v:
        return APP_DIR / ".env"
    p = Path(v)
    return p if p.is_absolute() else (APP_DIR / p).resolve()


ENV_PATH = env_path()

# 키: (기본값, 비밀 여부)
FIELDS = {
    "LEDGER_PROVIDER": ("anthropic", False),      # anthropic | openai
    "ANTHROPIC_API_KEY": ("", True),
    "LEDGER_MODEL": ("claude-sonnet-5-5", False),  # Anthropic 모델
    "LEDGER_EFFORT": ("medium", False),           # low | medium | high
    "OPENAI_API_KEY": ("", True),
    "OPENAI_BASE_URL": ("", False),               # 비우면 api.openai.com. OpenAI 호환 서버(Ollama, vLLM 등) 주소 가능
    "OPENAI_MODEL": ("gpt-4.1", False),
    "OPENAI_REASONING_EFFORT": ("", False),       # 비우면 미전송. 추론 모델(o-시리즈 등)에서만 low/medium/high
    "LEDGER_ORG": ("분당서울대학교병원 의료인공지능센터", False),  # 기관명: 지출결의서 머리글 (비우면 기본값)
    # 신청 화면 발주서 (소모품 주문)
    "REQUEST_BUYER": ("", False),                  # 발주기관 = 우리 기관 (예: 의료인공지능센터). 발주서 독자는 공급처(쇼핑몰)
    "REQUEST_SHIP_TO": ("", False),                # 배송지
    "REQUEST_CONTACT": ("", False),                # 담당자 (이름·연락처)
    # 소모품 구매처 (store.SUPPLIERS_DEFAULT 와 같은 기본값)
    "REQUEST_SUPPLIERS": ("알파미금역점,드림디포", False),  # 구매처 목록 (쉼표 구분)
    "REQUEST_SUPPLIERS_OFF": ("", False),          # 지금 신청할 수 없는 구매처 (쉼표 구분, 목록에 있는 이름만)
    "REQUEST_SUPPLIER_NOTE": ("", False),          # 연구원 화면 안내 (예: 드림디포는 10월 말까지 이용 불가)
}
SUPPLIER_KEYS = ("REQUEST_SUPPLIERS", "REQUEST_SUPPLIERS_OFF")


def _split(v) -> list[str]:
    out: list[str] = []
    for x in re.split(r"[,，、\n]", str(v or "")):
        x = x.strip()
        if x and x not in out:
            out.append(x)
    return out


def get(key: str) -> str:
    return os.environ.get(key, FIELDS[key][0]) if key in FIELDS else os.environ.get(key, "")


def current() -> dict:
    return {k: get(k) for k in FIELDS}


def masked() -> dict:
    """화면 표시용: 비밀값은 설정 여부와 끝 4자리만."""
    out = {}
    for k, (default, secret) in FIELDS.items():
        v = get(k)
        out[k] = ({"set": bool(v), "hint": ("…" + v[-4:]) if len(v) >= 8 else ""} if secret else v)
    return out


def save(values: dict) -> dict:
    """values 에 있는 키만 갱신. 비밀값은 빈 문자열이면 '유지', '__clear__' 면 삭제."""
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    updates = {}
    for k, v in values.items():
        if k not in FIELDS:
            continue
        v = str(v or "").strip()
        if FIELDS[k][1]:  # secret
            if v == "":
                continue
            if v == "__clear__":
                v = ""
        if "\n" in v or "\r" in v:
            raise ValueError(f"{k} 값에 줄바꿈을 넣을 수 없습니다.")
        updates[k] = v
    if any(k in updates for k in SUPPLIER_KEYS):
        # 구매처 목록 정리 (비우면 기본값), 이용 불가는 목록에 있는 이름만
        master = _split(updates.get("REQUEST_SUPPLIERS", get("REQUEST_SUPPLIERS"))) or _split(FIELDS["REQUEST_SUPPLIERS"][0])
        if "REQUEST_SUPPLIERS" in updates:
            updates["REQUEST_SUPPLIERS"] = ",".join(master)
        off = _split(updates.get("REQUEST_SUPPLIERS_OFF", get("REQUEST_SUPPLIERS_OFF")))
        updates["REQUEST_SUPPLIERS_OFF"] = ",".join(x for x in master if x in off)

    seen = set()
    out = []
    for ln in lines:
        m = re.match(r"^\s*#?\s*([A-Z0-9_]+)\s*=", ln)
        key = m[1] if m else None
        if key in updates and key not in seen:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        elif key in updates:
            continue  # 중복 줄 제거
        else:
            out.append(ln)
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(out).rstrip("\n") + "\n", encoding="utf-8")

    for k, v in updates.items():
        if v == "":
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return masked()
