"""앱 설정: app/.env 파일을 읽고 쓰며 os.environ 에 즉시 반영한다 (서버 재시작 불필요)."""
from __future__ import annotations

import os
import re
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / ".env"

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
    # 신청 화면 발주서 (소모품 주문)
    "REQUEST_BUYER": ("", False),                  # 구매처 (예: 의료인공지능센터)
    "REQUEST_SHIP_TO": ("", False),                # 배송지
    "REQUEST_CONTACT": ("", False),                # 담당자 (이름·연락처)
}


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
