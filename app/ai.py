"""AI 연동 진입점: 장부 Q&A/거래 제안, 영수증 추출, 입력 검증/추천, 보고서 초안.

제공자(provider)는 설정(LEDGER_PROVIDER)에 따라 Anthropic(이 파일) 또는 OpenAI 호환(ai_openai.py)로 분기한다.
프롬프트·도구 정의·결과 매핑은 이 파일에 두고 두 백엔드가 공유한다.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any

import anthropic
from pydantic import BaseModel, ConfigDict, Field

import settings
import store

# 안전장치 거부(refusal) 시 서버 측에서 다른 모델로 자동 재시도
_FALLBACK = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

_client: anthropic.Anthropic | None = None
_client_key: str | None = None


class AIError(Exception):
    pass


# ---------- 설정 접근 ----------
def provider() -> str:
    return "openai" if settings.get("LEDGER_PROVIDER") == "openai" else "anthropic"


def model() -> str:
    return settings.get("OPENAI_MODEL") if provider() == "openai" else settings.get("LEDGER_MODEL")


def effort() -> str:
    return settings.get("LEDGER_EFFORT") or "medium"


def enabled() -> bool:
    if provider() == "openai":
        return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_BASE_URL"))
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _c() -> anthropic.Anthropic:
    """키가 바뀌면 클라이언트를 새로 만든다 (설정 패널에서 즉시 반영)."""
    global _client, _client_key
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not key:
        raise AIError("Anthropic API 키가 설정되지 않았습니다. 우하단 설정에서 키를 입력하세요.")
    if _client is None or _client_key != key:
        _client = anthropic.Anthropic()
        _client_key = key
    return _client


def _guard(thunk):
    """SDK 호출을 감싸 사용자에게 보여줄 오류 메시지로 변환."""
    try:
        return thunk()
    except anthropic.AuthenticationError:
        raise AIError("API 키가 올바르지 않습니다. 설정에서 키를 다시 입력하세요.")
    except anthropic.PermissionDeniedError:
        raise AIError("이 키로는 사용할 수 없는 기능입니다 (권한 거부). 키 발급 조직의 설정을 확인하세요.")
    except anthropic.NotFoundError as e:
        raise AIError(f"모델을 찾을 수 없습니다. 설정의 모델명을 확인하세요. ({e.message[:80]})")
    except anthropic.RateLimitError as e:
        raise AIError(f"요청 한도 초과. {e.response.headers.get('retry-after', '60')}초 후 다시 시도하세요.")
    except anthropic.BadRequestError as e:
        m = str(e.message)
        if "credit" in m.lower() or "billing" in m.lower():
            raise AIError("API 크레딧이 부족합니다. console.anthropic.com 에서 결제·잔액을 확인하세요.")
        if "too large" in m.lower() or "exceed" in m.lower():
            raise AIError("요청이 너무 큽니다 (장부·이미지 크기). 이미지를 줄이거나 범위를 좁혀 다시 시도하세요.")
        raise AIError(f"요청 오류: {m[:200]}")
    except anthropic.APIStatusError as e:
        if e.status_code == 529 or e.status_code == 503:
            raise AIError("AI 서버가 혼잡합니다 (일시 과부하). 잠시 후 다시 시도하세요.")
        raise AIError(f"API 오류 ({e.status_code}): {str(e.message)[:200]}")
    except anthropic.APITimeoutError:
        raise AIError("응답 시간 초과. 질문을 줄이거나 잠시 후 다시 시도하세요.")
    except anthropic.APIConnectionError:
        raise AIError("AI 서버에 연결할 수 없습니다. 인터넷 연결을 확인하세요.")


def _call(fn, **kw):
    return _guard(lambda: fn(**kw))


def _stream_final(**kw):
    """긴 출력은 스트리밍으로 받아 타임아웃을 피하고 최종 메시지만 반환."""
    def run():
        with _c().beta.messages.stream(**kw) as s:
            return s.get_final_message()
    return _guard(run)


def _text(resp) -> str:
    if resp.stop_reason == "refusal":
        raise AIError("모델이 요청을 거부했습니다.")
    return "".join(b.text for b in resp.content if b.type == "text").strip()


# ========== 공유: 장부 컨텍스트 · 프롬프트 · 도구 정의 ==========
def ledger_context(data: dict | None = None) -> str:
    """장부 전체를 모델에 넘길 텍스트로 직렬화 (정렬 고정 → 프롬프트 캐시 안정)."""
    data = data or store.read_all()
    def rows(kind, cols):
        return [{"_row": r["_row"], **{c: r.get(c) for c in cols if r.get(c) not in (None, "", 0)}} for r in data[kind]]
    ctx = {
        "재원": rows("funds", store.FUND_COLS),
        "예산변동": rows("budget", store.BUDGET_COLS),
        "집행내역": rows("exec", store.EXEC_COLS),
        "품의내역": rows("req", store.REQ_COLS),
        "적립금": rows("deposit", store.DEP_COLS),
        "태그목록": rows("tags", store.TAG_COLS),
        "예산목": store.BUDGET_ITEMS,
    }
    return json.dumps(ctx, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


SYSTEM_BASE = """당신은 분당서울대학교병원 의료인공지능센터의 연구비 회계 담당자를 돕는 보조원입니다.
아래 JSON은 센터 회계대장 전체입니다. 질문에는 이 데이터만 근거로, 금액은 천 단위 쉼표와 '원'으로, 한국어로 간결하게 답하세요.

집계 규칙:
- 예산현액 = 재원·예산목별 예산변동 행의 모든 금액 합계 (변경회차 '이월'=이월금, '당초'=당초액, 숫자=변경)
- 집행액 = 집행내역 금액 합계. 기준일은 원인발생일. 지출완료일이 비어 있으면 '지급대기'이지만 집행액에는 포함
- 품의대기 = 상태가 '대기'인 품의 금액. 가용잔액 = 예산현액 - 집행액 - 품의대기
- 거래번호·품의번호 형식은 YYYY-재원코드-NNN. 각 행의 _row 는 행 수정 제안(propose_update)에 쓰는 행 번호
- 태그는 센터 내부 계정이며 태그목록에 있는 값 1개만 사용. 태그 집계에는 집행내역(적립 선결제 건 제외) + 적립금 사용 건이 포함
- 적립금: 거래처별 적립 누계 - 사용 누계 = 잔액. 적립 시 연결거래번호가 있으면 집행내역에도 같은 금액이 있음
- 금액 계산은 반드시 행을 하나씩 더해 확인하고, 근거가 된 거래번호나 행을 함께 제시하세요.
- 데이터에 없는 내용은 모른다고 답하세요.

거래 반영: 사용자가 집행·품의·적립금 입력이나 기존 행 수정을 요청하면 직접 반영하지 말고 propose_* 도구로 '제안'을 만드세요.
제안은 사용자가 화면에서 검토·수정한 뒤 직접 저장합니다. 도구 호출 후에는 무엇을 제안했는지 한두 문장으로 요약하고, 확인을 요청하세요.
금액·날짜·재원처럼 확실하지 않은 값은 추측하지 말고 사용자에게 물어보세요. 재원은 반드시 재원 목록의 코드여야 합니다."""


def _today_line() -> str:
    import datetime as _dt
    d = _dt.date.today()
    return f"오늘 날짜: {d.isoformat()} ({'월화수목금토일'[d.weekday()]}). 연도가 없는 날짜('5/20')는 오늘 기준 연도로 해석하고 제안 카드에 그대로 표시하세요. '어제' 같은 상대 날짜는 오늘 기준으로 계산하세요."


def system_text(data: dict | None = None) -> str:
    return SYSTEM_BASE + "\n" + _today_line() + "\n\n<ledger>\n" + ledger_context(data) + "\n</ledger>"


def _system_blocks(data: dict | None = None) -> list[dict]:
    return [
        {"type": "text", "text": SYSTEM_BASE + "\n" + _today_line()},
        {"type": "text", "text": "<ledger>\n" + ledger_context(data) + "\n</ledger>",
         "cache_control": {"type": "ephemeral", "ttl": "1h"}},
    ]


def _schema(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


_S = lambda d: {"type": "string", "description": d}  # noqa: E731
_N = lambda d: {"type": "number", "description": d}  # noqa: E731

# 도구 입력 키는 API 제약상 영문. _KEYMAP 으로 한글 열명에 대응.
_KEYMAP = {"date": "원인발생일", "due_date": "지출예정일", "fund": "재원", "budget_item": "예산목", "amount": "금액",
           "vendor": "거래처", "summary": "적요", "sub_item": "세목", "user": "사용자", "tags": "태그", "paid_date": "지출완료일",
           "pay_method": "결제수단", "requester": "품의자", "dep_type": "구분", "receipt_no": "증빙번호"}
_KEYMAP_DESC = ", ".join(f"{k}={v}" for k, v in _KEYMAP.items())

PROPOSE_TOOLS = [
    {"name": "propose_exec", "description": f"집행내역 추가를 제안한다. 사용자가 검토·수정 후 저장한다. 키 대응: {_KEYMAP_DESC}", "strict": True,
     "input_schema": _schema({
         "date": _S("원인발생일 YYYY-MM-DD"), "fund": _S("재원코드"), "budget_item": {"type": "string", "enum": store.BUDGET_ITEMS, "description": "예산목"},
         "amount": _N("금액, 원 단위 정수"), "vendor": _S("거래처명"), "summary": _S("적요"), "sub_item": _S("세목, 없으면 빈 문자열"),
         "user": _S("사용자명, 없으면 빈 문자열"), "tags": _S("태그 (태그목록 중 1개), 없으면 빈 문자열"),
         "paid_date": _S("지출완료일 YYYY-MM-DD 또는 빈 문자열(지급대기)"),
     }, ["date", "fund", "budget_item", "amount", "vendor", "summary", "sub_item", "user", "tags", "paid_date"])},
    {"name": "propose_req", "description": "품의내역 추가를 제안한다(상태=대기). 사용자가 검토·수정 후 저장한다.", "strict": True,
     "input_schema": _schema({
         "date": _S("원인발생일 YYYY-MM-DD"), "due_date": _S("지출예정일 YYYY-MM-DD 또는 빈 문자열"), "fund": _S("재원코드"),
         "budget_item": {"type": "string", "enum": store.BUDGET_ITEMS, "description": "예산목"}, "amount": _N("금액, 원 단위 정수"),
         "vendor": _S("거래처명"), "summary": _S("적요"), "pay_method": {"type": "string", "enum": [""] + store.PAY_METHODS, "description": "결제수단"},
         "requester": _S("품의자, 없으면 빈 문자열"),
     }, ["date", "due_date", "fund", "budget_item", "amount", "vendor", "summary", "pay_method", "requester"])},
    {"name": "propose_deposit", "description": "적립금 적립/사용 기록을 제안한다.", "strict": True,
     "input_schema": _schema({
         "date": _S("일자 YYYY-MM-DD"), "vendor": _S("거래처명"), "dep_type": {"type": "string", "enum": store.DEP_TYPES, "description": "구분"},
         "amount": _N("금액, 원 단위 정수"), "summary": _S("적요"), "user": _S("사용자, 없으면 빈 문자열"),
         "receipt_no": _S("증빙번호, 없으면 빈 문자열"), "tags": _S("태그 (태그목록 중 1개), 없으면 빈 문자열"),
     }, ["date", "vendor", "dep_type", "amount", "summary", "user", "receipt_no", "tags"])},
    {"name": "propose_update", "description": "기존 행의 일부 열 수정을 제안한다. row 는 장부 JSON의 _row 값. fields 의 column 은 장부의 한글 열명 그대로(예: 지출완료일).", "strict": True,
     "input_schema": _schema({
         "kind": {"type": "string", "enum": ["exec", "req", "deposit", "budget", "funds"]},
         "row": {"type": "integer", "description": "_row"},
         "fields": {"type": "array", "description": "바꿀 열 목록", "items": _schema({"column": _S("한글 열명, 예: 지출완료일"), "value": _S("새 값")}, ["column", "value"])},
         "reason": _S("수정 이유 한 문장"),
     }, ["kind", "row", "fields", "reason"])},
    {"name": "propose_req_to_exec", "description": "대기 중인 품의를 집행내역으로 전환하도록 제안한다. row 는 품의의 _row.", "strict": True,
     "input_schema": _schema({"row": {"type": "integer"}, "reason": _S("한 문장")}, ["row", "reason"])},
]

TOOL_RESULT_TEXT = "제안 {pid} 가 화면에 표시되었습니다. 사용자가 검토 후 저장하면 반영됩니다. 직접 반영되지 않았습니다."


def localize(tool: str, inp: dict) -> dict:
    """도구 입력의 영문 키를 장부 열명으로 변환."""
    if tool == "propose_update":
        f = inp.get("fields")
        if isinstance(f, list):
            inp["fields"] = {x["column"]: x["value"] for x in f if isinstance(x, dict) and "column" in x}
        return inp
    if tool == "propose_req_to_exec":
        return inp
    out = {_KEYMAP.get(k, k): v for k, v in inp.items()}
    if tool == "propose_deposit" and "원인발생일" in out:
        out["일자"] = out.pop("원인발생일")
    return out


def finalize_answer(answer: str, stop: str, proposals: list) -> dict:
    """stop: 'end' | 'max_tokens' | 'tool_use'(상한 도달)"""
    if stop == "max_tokens":
        answer += "\n\n[응답이 길이 제한으로 잘렸습니다. 질문을 나눠서 다시 물어보세요.]"
    elif stop == "tool_use":
        answer += "\n\n[한 번에 처리할 수 있는 제안 수를 넘었습니다. 나머지는 다시 요청해 주세요.]"
    return {"answer": answer.strip() or ("제안을 만들었습니다. 아래에서 검토해 주세요." if proposals else ""), "proposals": proposals}


# ---------- 영수증 / 추천 스키마 ----------
class ReceiptDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: str = Field(description="거래/영수 일자(원인발생일) YYYY-MM-DD. 모르면 빈 문자열")
    vendor: str = Field(description="거래처: 상호 또는 공급자명")
    amount: int = Field(description="금액: 총 결제금액(원, 정수). 부가세 포함 합계")
    summary: str = Field(description="적요: 구매 내용을 한 줄로 요약 (예: 회의 식대, A4 용지 10박스)")
    sub_item: str = Field(description="세목: 추정 세목 (예: 회의비, 소모품비, 국내출장비). 모르면 빈 문자열")
    budget_item: str = Field(description="예산목: 예산목 목록 중 가장 적합한 값. 모르면 빈 문자열")
    receipt_no: str = Field(description="증빙번호: 승인번호/영수증 번호. 없으면 빈 문자열")
    confidence: str = Field(description="신뢰도: high / medium / low")
    note: str = Field(description="메모: 판독이 불확실한 부분이나 확인이 필요한 사항")


RECEIPT_MAP = {"date": "원인발생일", "vendor": "거래처", "amount": "금액", "summary": "적요", "sub_item": "세목",
               "budget_item": "예산목", "receipt_no": "증빙번호", "confidence": "신뢰도", "note": "메모"}


class Suggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    budget_item: str = Field(description="예산목: 추천 예산목 (목록 중 하나)")
    sub_item: str = Field(description="세목: 추천 세목. 기존 세목 표기를 우선 재사용")
    tags: str = Field(description="태그: 태그 목록 중 가장 적합한 1개. 없으면 빈 문자열")
    reason: str = Field(description="근거: 추천 근거 한두 문장")
    warnings: list[str] = Field(description="경고: 이상 징후 목록. 없으면 빈 배열. 예: 같은 거래처·금액·일자의 중복 가능성, 예산 잔액 초과, 예산목 불일치, 금액 단위 오류 의심")


SUGGEST_MAP = {"budget_item": "예산목", "sub_item": "세목", "tags": "태그", "reason": "근거", "warnings": "경고"}

IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}


def receipt_prompt() -> str:
    data = store.read_all()
    vendors = sorted({r["거래처"] for r in data["exec"] + data["req"] if r.get("거래처")})
    items = sorted({(r["거래처"], r["세목"], r["예산목"]) for r in data["exec"] if r.get("거래처") and r.get("세목")})
    return (
        "영수증·세금계산서·거래명세서 이미지에서 집행 입력에 필요한 항목을 추출하세요. 한국어 문서입니다.\n"
        f"예산목 목록: {store.BUDGET_ITEMS}\n"
        f"기존 거래처(표기 통일용): {vendors[:200]}\n"
        f"기존 거래처→세목→예산목 사례: {[list(i) for i in items[:200]]}\n"
        "금액은 숫자만, 날짜는 YYYY-MM-DD. 읽을 수 없는 항목은 빈 문자열로 두고 메모에 적으세요."
    )


def suggest_prompt(rec: dict, kind: str) -> tuple[str, str]:
    data = store.read_all()
    vendor = str(rec.get("거래처") or "").strip()
    history = [r for r in data["exec"] if vendor and r.get("거래처") == vendor][-30:]
    similar = [r for r in data["exec"] if rec.get("금액") and abs((r.get("금액") or 0) - store._to_num(rec.get("금액"))) < 1][-10:]
    import main  # 지연 임포트 (순환 방지)
    dash = main.build_dashboard(data)
    budget_rows = [t for t in dash["table"] if t["재원"] == rec.get("재원")]
    system = (
        "회계 입력 보조원입니다. 입력 중인 행을 보고 예산목·세목·태그를 추천하고 이상 징후를 경고하세요.\n"
        f"예산목 목록: {store.BUDGET_ITEMS}\n"
        f"기존 세목 목록: {sorted({r['세목'] for r in data['exec'] if r.get('세목')})[:200]}\n"
        f"태그 목록(센터 내부 계정, 1개만 선택): {[(t['태그명'], t['분류'], t['설명']) for t in data['tags']][:200]}\n"
        "경고는 확실한 근거가 있을 때만, 각 항목을 한 문장으로."
    )
    user = json.dumps({
        "입력중인행": rec, "종류": "집행" if kind == "exec" else "품의",
        "같은거래처_최근이력": history, "같은금액_최근이력": similar, "해당재원_예산현황": budget_rows,
    }, ensure_ascii=False, default=str)
    return system, user


def report_facts(fund: str, year: str, month: str) -> str:
    """서버가 미리 집계한 수치 (모델은 계산하지 않고 서술만 하도록)."""
    import main  # 지연 임포트
    data = store.read_all()
    def in_scope(r, dcol):
        d = str(r.get(dcol) or "")
        return (not fund or r.get("재원") == fund) and (not year or d.startswith(year)) and (not month or d[5:7] <= month.zfill(2))
    sub = dict(data)
    sub["exec"] = [r for r in data["exec"] if in_scope(r, "원인발생일")]
    sub["req"] = [r for r in data["req"] if in_scope(r, "원인발생일")]
    if fund:
        sub["funds"] = [f for f in data["funds"] if f["재원코드"] == fund]
        sub["budget"] = [b for b in data["budget"] if b["재원"] == fund]
    dash = main.build_dashboard(sub)
    month_rows = [r for r in sub["exec"] if month and str(r.get("원인발생일") or "")[5:7] == month.zfill(2)]
    top = sorted(sub["exec"], key=lambda r: -(r.get("금액") or 0))[:10]
    facts = {
        "범위": {"재원": fund or "전체", "연도": year or "전체", "월": (month + "월 (누계는 연초~해당월)") if month else "전체"},
        "재원별_예산목별": dash["table"],
        "당월_집행합계": sum(r.get("금액") or 0 for r in month_rows) if month else None,
        "당월_건수": len(month_rows) if month else None,
        "누계_집행합계": sum(r.get("금액") or 0 for r in sub["exec"]),
        "품의대기": [{k: r.get(k) for k in ("품의번호", "거래처", "적요", "금액")} for r in sub["req"] if r.get("상태") == "대기"],
        "미완료_집행": [{k: r.get(k) for k in ("거래번호", "거래처", "금액", "지급청구일")} for r in sub["exec"] if not r.get("지출완료일")],
        "상위_지출": [{k: r.get(k) for k in ("거래번호", "원인발생일", "거래처", "적요", "예산목", "금액")} for r in top],
        "태그별": [{k: t[k] for k in ("태그", "분류", "금액", "건수")} for t in dash["tag_table"]],
        "예산집계_제외": dash["excluded_total"],  # 재원·예산목 목록 밖 (재원별_예산목별 표에 없음)
    }
    return json.dumps(facts, ensure_ascii=False, default=str)


def report_prompt(fund: str, year: str, month: str, style: str) -> str:
    scope = []
    if fund: scope.append(f"재원: {fund}")
    if year: scope.append(f"연도: {year}")
    if month: scope.append(f"월: {month}")
    kind = {"monthly": "월별 집행 보고", "project": "과제(재원)별 집행 현황 보고", "summary": "센터 전체 요약"}.get(style, "집행 보고")
    return (
        f"{kind} 초안을 작성하세요. 범위: {', '.join(scope) or '전체'}.\n"
        "아래 <facts> 는 서버가 미리 집계한 확정 수치입니다. 합계·집행률 등 모든 숫자는 <facts> 의 값을 그대로 옮기고 직접 계산하지 마세요. "
        "장부 원본은 거래처·적요 같은 서술 보강에만 쓰세요.\n"
        "구성: 1) 요약(3줄 이내) 2) 예산목별 예산현액·집행액·잔액·집행률 표(마크다운) 3) 주요 지출 내역(상위 10건) "
        "4) 품의 대기·미완료 집행 현황 5) 특이사항 및 유의점. 실무 보고용 문체.\n"
        f"<facts>\n{report_facts(fund, year, month)}\n</facts>"
    )


# ========== 공개 API (제공자 분기) ==========
def _oa():
    import ai_openai
    return ai_openai


def chat(messages: list[dict], turn: int = 0) -> dict:
    if not messages or messages[-1].get("role") != "user":
        raise AIError("마지막 메시지는 사용자 질문이어야 합니다.")
    msgs = [{"role": m["role"], "content": str(m["content"])} for m in messages if m.get("role") in ("user", "assistant")]
    prefix = f"t{turn}-" if turn else ""
    if provider() == "openai":
        return _oa().chat(msgs, prefix)
    return _chat_anthropic(msgs, prefix)


def extract_receipt(file_bytes: bytes, media_type: str) -> dict:
    if media_type not in IMAGE_TYPES and media_type != "application/pdf":
        raise AIError("이미지(png/jpg/webp/gif) 또는 PDF만 지원합니다.")
    if provider() == "openai":
        return _oa().extract_receipt(file_bytes, media_type)
    return _extract_anthropic(file_bytes, media_type)


def suggest(rec: dict, kind: str = "exec") -> dict:
    if provider() == "openai":
        return _oa().suggest(rec, kind)
    return _suggest_anthropic(rec, kind)


def report(fund: str = "", year: str = "", month: str = "", style: str = "monthly") -> str:
    if provider() == "openai":
        return _oa().report(fund, year, month, style)
    return _report_anthropic(fund, year, month, style)


def test_connection() -> str:
    """설정 패널의 '연결 확인': 아주 짧은 호출로 키·모델 유효성 확인."""
    if provider() == "openai":
        return _oa().test_connection()
    resp = _call(_c().messages.create, model=model(), max_tokens=20,
                 messages=[{"role": "user", "content": "OK 라고만 답하세요."}])
    return f"{model()} 응답: {_text(resp)[:40]}"


# ========== Anthropic 구현 ==========
def _chat_anthropic(msgs: list[dict], prefix: str = "") -> dict:
    system = _system_blocks()
    proposals: list[dict] = []
    stop = "end"
    usage = {"input": 0, "cached": 0, "output": 0}
    for _ in range(6):  # 한 턴 내 도구 호출 루프 상한
        resp = _call(_c().beta.messages.create, model=model(), max_tokens=16000, output_config={"effort": effort()},
                     system=system, messages=msgs, tools=PROPOSE_TOOLS, **_FALLBACK)
        if resp.stop_reason == "refusal":
            raise AIError("모델이 요청을 거부했습니다.")
        u = getattr(resp, "usage", None)
        if u:
            usage["input"] += (u.input_tokens or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0)
            usage["cached"] += getattr(u, "cache_read_input_tokens", 0) or 0
            usage["output"] += u.output_tokens or 0
        uses = [b for b in resp.content if b.type == "tool_use"]
        if resp.stop_reason != "tool_use" or not uses:
            stop = "max_tokens" if resp.stop_reason == "max_tokens" else "end"
            break
        msgs.append({"role": "assistant", "content": resp.content})
        results = []
        for tu in uses:
            pid = f"{prefix}p{len(proposals) + 1}"
            proposals.append({"id": pid, "tool": tu.name, "input": localize(tu.name, dict(tu.input))})
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": TOOL_RESULT_TEXT.format(pid=pid)})
        msgs.append({"role": "user", "content": results})
    else:
        stop = "tool_use"
    answer = "".join(b.text for b in resp.content if b.type == "text")
    out = finalize_answer(answer, stop, proposals)
    out["usage"] = usage
    return out


def _extract_anthropic(file_bytes: bytes, media_type: str) -> dict:
    b64 = base64.standard_b64encode(file_bytes).decode()
    if media_type in IMAGE_TYPES:
        block = {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}}
    else:
        block = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
    resp = _call(_c().beta.messages.parse, model=model(), max_tokens=4000, output_config={"effort": effort()},
                 system=receipt_prompt(), output_format=ReceiptDraft,
                 messages=[{"role": "user", "content": [block, {"type": "text", "text": "이 증빙에서 항목을 추출해 주세요."}]}],
                 **_FALLBACK)
    if resp.stop_reason == "refusal":
        raise AIError("모델이 요청을 거부했습니다.")
    if resp.parsed_output is None:
        raise AIError("구조화 응답을 받지 못했습니다 (응답 잘림). 다시 시도하세요.")
    return {RECEIPT_MAP[k]: v for k, v in resp.parsed_output.model_dump().items()}


def _suggest_anthropic(rec: dict, kind: str) -> dict:
    system, user = suggest_prompt(rec, kind)
    resp = _call(_c().beta.messages.parse, model=model(), max_tokens=2000, output_config={"effort": effort()},
                 system=system, output_format=Suggestion,
                 messages=[{"role": "user", "content": user}], **_FALLBACK)
    if resp.stop_reason == "refusal":
        raise AIError("모델이 요청을 거부했습니다.")
    if resp.parsed_output is None:
        raise AIError("구조화 응답을 받지 못했습니다 (응답 잘림). 다시 시도하세요.")
    return {SUGGEST_MAP[k]: v for k, v in resp.parsed_output.model_dump().items()}


def _report_anthropic(fund: str, year: str, month: str, style: str) -> str:
    data = store.read_all()
    resp = _stream_final(model=model(), max_tokens=16000, output_config={"effort": effort()},
                         system=_system_blocks(data), messages=[{"role": "user", "content": report_prompt(fund, year, month, style)}], **_FALLBACK)
    return _text(resp)
