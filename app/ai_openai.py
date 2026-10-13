"""OpenAI 호환 백엔드 (OpenAI 또는 OpenAI 호환 서버: Ollama, vLLM, LM Studio 등).

프롬프트·도구 정의는 ai.py 의 것을 그대로 사용한다. Chat Completions API 기준.
"""
from __future__ import annotations

import base64
import json
import os

import openai

import ai
import settings
import store

_client: openai.OpenAI | None = None
_client_sig: tuple | None = None


def _c() -> openai.OpenAI:
    global _client, _client_sig
    key = os.environ.get("OPENAI_API_KEY") or ""
    base = os.environ.get("OPENAI_BASE_URL") or None
    if not key and not base:
        raise ai.AIError("OpenAI API 키(또는 호환 서버 주소)가 설정되지 않았습니다. 우하단 설정에서 입력하세요.")
    sig = (key, base)
    if _client is None or _client_sig != sig:
        _client = openai.OpenAI(api_key=key or "none", base_url=base)  # 호환 서버는 키가 없어도 됨
        _client_sig = sig
    return _client


def _guard(thunk):
    try:
        return thunk()
    except openai.AuthenticationError:
        raise ai.AIError("OpenAI API 키가 올바르지 않습니다. 설정에서 키를 다시 입력하세요.")
    except openai.NotFoundError as e:
        raise ai.AIError(f"모델 또는 주소를 찾을 수 없습니다. 설정의 모델명·Base URL을 확인하세요. ({getattr(e, 'message', str(e))[:80]})")
    except openai.RateLimitError as e:
        m = getattr(e, "message", str(e)).lower()
        if "quota" in m or "billing" in m:
            raise ai.AIError("OpenAI 사용량 한도(크레딧)가 소진되었습니다. 결제 설정을 확인하세요.")
        raise ai.AIError("요청 한도 초과. 잠시 후 다시 시도하세요.")
    except openai.BadRequestError as e:
        m = getattr(e, "message", str(e))
        if "reasoning" in m.lower():
            raise ai.AIError("이 모델은 '추론 수준'을 지원하지 않습니다. 설정에서 추론 수준을 '미전송'으로 바꾸세요.")
        if "tool" in m.lower() or "function" in m.lower():
            raise ai.AIError(f"이 모델/서버는 도구 호출을 지원하지 않는 것 같습니다. ({m[:120]})")
        if "context" in m.lower() or "too long" in m.lower() or "maximum" in m.lower():
            raise ai.AIError("요청이 모델의 컨텍스트 한도를 넘었습니다. 장부가 크면 컨텍스트가 큰 모델을 쓰거나 범위를 줄이세요.")
        raise ai.AIError(f"요청 오류: {m[:200]}")
    except openai.APIStatusError as e:
        raise ai.AIError(f"API 오류 ({e.status_code}): {getattr(e, 'message', str(e))[:200]}")
    except openai.APITimeoutError:
        raise ai.AIError("응답 시간 초과. 로컬 모델이 느리거나 서버가 응답하지 않습니다.")
    except openai.APIConnectionError:
        raise ai.AIError("AI 서버에 연결할 수 없습니다. Base URL 과 네트워크를 확인하세요.")


def _common(**extra) -> dict:
    kw = {"model": settings.get("OPENAI_MODEL"), **extra}
    re_ = settings.get("OPENAI_REASONING_EFFORT")
    if re_:
        kw["reasoning_effort"] = re_
    return kw


def _create(**kw):
    return _guard(lambda: _c().chat.completions.create(**_common(**kw)))


def _tools() -> list[dict]:
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                              "parameters": t["input_schema"], "strict": True}} for t in ai.PROPOSE_TOOLS]


def _json_format(model_cls, name: str) -> dict:
    return {"type": "json_schema", "json_schema": {"name": name, "schema": model_cls.model_json_schema(), "strict": True}}


def _parse(model_cls, content: str | None):
    if not content:
        raise ai.AIError("구조화 응답을 받지 못했습니다. 다시 시도하세요.")
    try:
        return model_cls.model_validate_json(content)
    except Exception as e:
        raise ai.AIError(f"응답 형식 오류: {e}")


# ---------- 채팅 ----------
def chat(msgs: list[dict], prefix: str = "") -> dict:
    messages = [{"role": "system", "content": ai.system_text()}] + msgs
    proposals: list[dict] = []
    stop = "end"
    usage = {"input": 0, "cached": 0, "output": 0}
    for _ in range(6):
        resp = _create(messages=messages, tools=_tools(), max_completion_tokens=16000)
        choice = resp.choices[0]
        m = choice.message
        if getattr(resp, "usage", None):
            usage["input"] += resp.usage.prompt_tokens or 0
            usage["output"] += resp.usage.completion_tokens or 0
        calls = m.tool_calls or []
        if choice.finish_reason == "length":
            stop = "max_tokens"
            break
        if not calls:
            break
        messages.append({"role": "assistant", "content": m.content or "", "tool_calls": [
            {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in calls]})
        for c in calls:
            pid = f"{prefix}p{len(proposals) + 1}"
            try:
                args = json.loads(c.function.arguments or "{}")
            except json.JSONDecodeError:
                messages.append({"role": "tool", "tool_call_id": c.id, "content": "오류: 인수 JSON 을 해석할 수 없습니다. 다시 시도하세요."})
                continue
            proposals.append({"id": pid, "tool": c.function.name, "input": ai.localize(c.function.name, args)})
            messages.append({"role": "tool", "tool_call_id": c.id, "content": ai.TOOL_RESULT_TEXT.format(pid=pid)})
    else:
        stop = "tool_use"
    out = ai.finalize_answer(m.content or "", stop, proposals)
    out["usage"] = usage
    return out


# ---------- 영수증 ----------
def extract_receipt(file_bytes: bytes, media_type: str) -> dict:
    b64 = base64.standard_b64encode(file_bytes).decode()
    if media_type in ai.IMAGE_TYPES:
        part = {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}}
    else:
        part = {"type": "file", "file": {"filename": "receipt.pdf", "file_data": f"data:application/pdf;base64,{b64}"}}
    resp = _create(messages=[{"role": "system", "content": ai.receipt_prompt()},
                             {"role": "user", "content": [part, {"type": "text", "text": "이 증빙에서 항목을 추출해 JSON 으로 답하세요."}]}],
                   response_format=_json_format(ai.ReceiptDraft, "receipt"), max_completion_tokens=4000)
    out = _parse(ai.ReceiptDraft, resp.choices[0].message.content)
    return {ai.RECEIPT_MAP[k]: v for k, v in out.model_dump().items()}


# ---------- 추천 ----------
def suggest(rec: dict, kind: str) -> dict:
    system, user = ai.suggest_prompt(rec, kind)
    resp = _create(messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                   response_format=_json_format(ai.Suggestion, "suggestion"), max_completion_tokens=2000)
    out = _parse(ai.Suggestion, resp.choices[0].message.content)
    return {ai.SUGGEST_MAP[k]: v for k, v in out.model_dump().items()}


# ---------- 보고서 ----------
def report(fund: str, year: str, month: str, style: str) -> str:
    data = store.read_all()
    resp = _create(messages=[{"role": "system", "content": ai.system_text(data)},
                             {"role": "user", "content": ai.report_prompt(fund, year, month, style)}],
                   max_completion_tokens=16000)
    return (resp.choices[0].message.content or "").strip()


def test_connection() -> str:
    resp = _create(messages=[{"role": "user", "content": "OK 라고만 답하세요."}], max_completion_tokens=20)
    base = f"{settings.get('OPENAI_MODEL')} 응답: {(resp.choices[0].message.content or '')[:40]}"
    try:
        t = _create(messages=[{"role": "user", "content": "ping 도구를 호출하세요."}], max_completion_tokens=50,
                    tools=[{"type": "function", "function": {"name": "ping", "description": "연결 확인", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}, "strict": True}}])
        tool_ok = bool(t.choices[0].message.tool_calls)
    except Exception:
        tool_ok = False
    return base + (" · 도구 호출 OK" if tool_ok else " · 도구 호출 미지원(거래 제안·영수증·추천 불가)")
