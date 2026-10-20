"""장부 조회 도구 (공통 모듈).

MCP 서버(mcp_server.py)와 앱 내 AI 에이전트(ai.py)가 같은 함수를 쓴다.
- 함수는 파이썬 객체(dict/list)를 반환한다. JSON 직렬화는 호출자가 한다.
- 함수 서명과 docstring 이 도구 정의다: MCP 는 그대로 노출하고, AI 쪽은 tool_schema() 로 JSON 스키마를 만든다.
- 역할별 도구 세트는 이름 목록으로 조립한다 (READ_TOOLS 등). 어떤 역할에 어떤 도구를 줄지는 호출자가 정한다.
- 쓰기는 이 모듈에 없다. 장부를 바꾸는 일은 store 를 직접 쓰는 MCP 쓰기 도구나 화면 저장이 한다.
"""
from __future__ import annotations

import inspect
import json
import typing
import urllib.request
from typing import Any

import store


def _dashboard(data: dict) -> dict:
    import main  # 지연 임포트 (main → ai → tools 순환 방지)
    return main.build_dashboard(data)


def _filter(rows, fund="", year="", month="", vendor="", q=""):
    out = []
    for r in rows:
        d = str(r.get("원인발생일") or r.get("일자") or "")
        if fund and r.get("재원") != fund: continue
        if year and not d.startswith(year): continue
        if month and d[5:7] != month.zfill(2): continue
        if vendor and vendor not in str(r.get("거래처") or ""): continue
        if q and not any(q.lower() in str(v).lower() for v in r.values()): continue
        out.append(r)
    return out


def _page(rows: list, limit: int, offset: int) -> dict:
    return {"total": len(rows), "rows": rows[offset:offset + max(1, min(limit, 1000))]}


# ---------- 조회 ----------
def list_funds() -> list[dict]:
    """재원(과제) 목록을 반환한다: 재원코드, 과제명, 시작일, 종료일, 비고, 인건비예산, 종류(국책/원내/위탁/교육/공금/기타), 잔액미관리(Y 면 재원 출처로만 쓰고 예산·잔액을 관리하지 않음). 공금 재원은 예산목별 예산 없이 예산변동 '입금' 합계 − 집행으로 잔액만 관리한다."""
    return store.read_all()["funds"]


def list_vendors() -> list[dict]:
    """적립금 거래처 목록: 거래처명, 코드(적립번호 앞자리), 비고. 미등록 거래처로 적립금을 넣으면 이름 앞 글자로 코드가 자동 등록된다."""
    return store.read_all()["vendor"]


def list_tags() -> list[dict]:
    """태그(센터 내부 계정) 목록: 태그명, 분류, 설명. 집행·품의·적립금의 태그는 이 목록 중 1개여야 한다."""
    return store.read_all()["tags"]


def get_dashboard(fund: str = "", year: str = "") -> dict:
    """재원×예산목별 예산현액·집행액·잔액·집행률·품의대기·가용잔액 표와 월별 집행액, 거래처/태그별 집계를 반환한다.
    fund 로 재원코드를, year 로 연도(YYYY)를 지정하면 집행·품의가 그 범위로 좁혀진다.
    웹 대시보드와 같은 집계 범위: 재원 시트에 없는 재원(외부 지급처 인건비 등)이나 11개 예산목 밖의 집행·대기 품의는 table 에 넣지 않고
    excluded.exec / excluded.req (거래번호·품의번호, 재원, 예산목, 금액, 사유)와 excluded_total 로 따로 반환한다."""
    data = store.read_all()
    if year:
        data["exec"] = [r for r in data["exec"] if str(r["원인발생일"] or "").startswith(year)]
        data["req"] = [r for r in data["req"] if str(r["원인발생일"] or "").startswith(year)]
    d = _dashboard(data)
    if fund:
        d["table"] = [t for t in d["table"] if t["재원"] == fund]
        d["monthly"] = {fund: d["monthly"].get(fund, {})}
        d["excluded"] = {k: [x for x in v if x["재원"] == fund] for k, v in d["excluded"].items()}
        d["excluded_total"] = {"exec": sum(x["금액"] or 0 for x in d["excluded"]["exec"]), "exec_count": len(d["excluded"]["exec"]),
                               "req": sum(x["금액"] or 0 for x in d["excluded"]["req"]), "req_count": len(d["excluded"]["req"])}
    return d


def list_exec(fund: str = "", year: str = "", month: str = "", vendor: str = "", q: str = "", unpaid_only: bool = False,
              limit: int = 200, offset: int = 0) -> dict:
    """집행내역을 조회한다. month 는 MM, vendor 는 거래처 부분일치, q 는 전체 열 검색, unpaid_only 는 지출완료일이 비어 있는 건만.
    각 행의 _row 는 수정/삭제에 쓰는 행 번호(삭제 후 바뀜). 최신순 정렬, limit/offset 으로 나눠 받는다. 반환: {total, rows}.
    상태는 저장값(발생/청구/보완/완료/결의), 상태표시는 화면 이름(발생/청구/보완/승인/완료: 완료→승인, 결의→완료). 사용자에게는 상태표시로 말할 것.
    연결품의번호는 품의→집행 전환으로 생긴 행의 원 품의번호."""
    rows = _filter(store.read_all()["exec"], fund, year, month, vendor, q)
    if unpaid_only:
        rows = [r for r in rows if not r.get("지출완료일")]
    rows.sort(key=lambda r: (str(r.get("원인발생일") or ""), r["_row"]), reverse=True)
    return _page(rows, limit, offset)


def list_req(fund: str = "", year: str = "", status: str = "", q: str = "", limit: int = 200, offset: int = 0) -> dict:
    """품의내역을 조회한다. status 는 대기/집행완료/취소. 최신순, limit/offset. 반환: {total, rows}."""
    rows = _filter(store.read_all()["req"], fund, year, "", "", q)
    if status:
        rows = [r for r in rows if r.get("상태") == status]
    rows.sort(key=lambda r: (str(r.get("원인발생일") or ""), r["_row"]), reverse=True)
    return _page(rows, limit, offset)


def list_budget(fund: str = "") -> list[dict]:
    """예산변동 이력을 조회한다. 변경회차 '이월'=이월금, '당초'=당초액, 숫자=변경 회차. 예산현액은 재원·예산목별 합계."""
    rows = store.read_all()["budget"]
    return [r for r in rows if not fund or r["재원"] == fund]


def list_deposit(vendor: str = "") -> dict:
    """적립금(거래처 선결제) 내역과 거래처별 잔액을 반환한다."""
    rows = store.read_all()["deposit"]
    if vendor:
        rows = [r for r in rows if vendor in str(r.get("거래처") or "")]
    bal, bad = {}, []
    for r in rows:
        if r["구분"] not in store.DEP_TYPES:
            bad.append(r)
            continue
        v = r["거래처"]
        bal.setdefault(v, {"적립": 0, "사용": 0})
        bal[v][r["구분"]] += r["금액"] or 0
    for v in bal:
        bal[v]["잔액"] = bal[v]["적립"] - bal[v]["사용"]
    return {"잔액": bal, "내역": rows, "구분오류행": bad}


def get_exec(number: str) -> dict:
    """거래번호로 집행 1건을 상세 조회한다 (_row 포함). 진행 상태는 상태표시(발생→청구→보완→승인→완료, 취소)와 날짜 열(지급청구일·지출완료일·결의일)로 본다.
    함께 반환: 증빙(등록된 증빙 목록: 증빙번호·증빙종류·파일명·업로드일·has_file), 연결품의(품의→집행 전환 원 품의, 없으면 null), 적립금연결(이 거래로 선결제한 적립금 행)."""
    data = store.read_all()
    r = next((x for x in data["exec"] if x["거래번호"] == number), None)
    if r is None:
        raise store.NotFound(f"거래번호 {number} 를 찾을 수 없습니다.")
    out = dict(r)
    out["증빙"] = [{**_pick(e, "증빙번호", "증빙종류", "파일명", "업로드일", "비고"), "has_file": store.evid_has_file(e)}
                 for e in data.get("evidence", []) if e.get("거래번호") == number]
    link = str(r.get("연결품의번호") or "").strip()
    req = next((x for x in data["req"] if x.get("품의번호") == link), None) if link else None
    out["연결품의"] = _pick(req, *_REQ_BRIEF) if req else None
    out["적립금연결"] = [_pick(d, "적립번호", "일자", "거래처", "구분", "금액", "상태") for d in data["deposit"] if d.get("연결거래번호") == number]
    return out


def _pick(r: dict, *cols) -> dict:
    return {c: r.get(c) for c in cols}


_EXEC_BRIEF = ("거래번호", "원인발생일", "재원", "예산목", "세목", "거래처", "적요", "금액", "상태표시", "지출완료일", "_row")
_REQ_BRIEF = ("품의번호", "원인발생일", "재원", "예산목", "거래처", "적요", "금액", "상태", "_row")
_RQ_BRIEF = ("신청번호", "구분", "상태", "신청인", "신청일", "관련과제", "품목", "규격", "단가", "수량", "금액", "구매처", "주문번호", "연결품의번호", "_row")
# 검색 대상 종류: (read_all 키, 검색 열, 날짜 열, 재원 열, 거래처 열, 요약 열)
_SEARCH = {
    "exec": ("exec", ("거래번호", "적요", "거래처", "세목", "세세목", "사용자", "비고", "관리번호"), "원인발생일", "재원", "거래처", _EXEC_BRIEF),
    "request": ("request", ("신청번호", "품목", "규격", "사유", "신청인", "구매처", "비고", "상세"), "신청일", "관련과제", "구매처", _RQ_BRIEF),
    "req": ("req", ("품의번호", "적요", "거래처", "세목", "세세목", "품의자", "비고"), "원인발생일", "재원", "거래처", _REQ_BRIEF),
}


def search_ledger(q: str, fund: str = "", vendor: str = "", date_from: str = "", date_to: str = "",
                  kinds: str = "exec,request,req", limit: int = 30) -> dict:
    """장부 텍스트 검색: 품목·장비·거래처 이름으로 "전에 얼마에 샀나", "언제 어느 재원으로 샀나"를 찾을 때 쓴다.
    q 는 공백으로 나눈 낱말을 모두 포함하는 행(AND, 대소문자 무시). kinds 는 쉼표 목록: exec 집행내역(적요·거래처·세목·사용자·비고),
    request 신청(품목·규격·단가·수량·사유·신청인·구매처), req 품의(적요·거래처·비고). fund 는 재원코드(신청은 관련과제), vendor 는 거래처 부분일치,
    date_from/date_to 는 YYYY-MM-DD(집행·품의는 원인발생일, 신청은 신청일). 반환 {종류: {total, rows}}, 최신순, 요약 열만. 상세는 get_exec."""
    words = [w.lower() for w in str(q or "").split() if w.strip()]
    data = store.read_all()
    out = {}
    for kind in [k.strip() for k in str(kinds or "").split(",") if k.strip() in _SEARCH]:
        key, cols, dcol, fcol, vcol, brief = _SEARCH[kind]
        rows = []
        for r in data.get(key, []):
            d = str(r.get(dcol) or "")
            if fund and r.get(fcol) != fund: continue
            if vendor and vendor not in str(r.get(vcol) or ""): continue
            if date_from and d < date_from: continue
            if date_to and d > date_to: continue
            text = " ".join(str(r.get(c) or "") for c in cols).lower()
            if all(w in text for w in words):
                rows.append(r)
        rows.sort(key=lambda r: (str(r.get(dcol) or ""), r["_row"]), reverse=True)
        out[kind] = {"total": len(rows), "rows": [_pick(r, *brief) for r in rows[:max(1, min(limit, 200))]]}
    return out


def budget_balance(fund: str, item: str = "") -> dict:
    """"<재원>의 <예산목> 지금 얼마 쓸 수 있어?"에 답하는 도구. 대시보드·집행 화면과 같은 계산:
    가용잔액 = 예산현액(예산변동 이월+당초+변경 합계) − 집행액(취소 제외, 전체 기간) − 품의대기(상태 '대기' 품의). 잔액 = 예산현액 − 집행액.
    item 을 비우면 그 재원의 예산목 전부. 공금 재원은 예산목 없이 '(공금 잔액)' 한 줄(입금 합계 − 집행 − 대기). 잔액미관리 재원은 예산을 관리하지 않으므로 행이 없다.
    예산현액이 0이면 예산 미입력(화면은 '-' 표시)."""
    data = store.read_all()
    f = next((x for x in data["funds"] if x.get("재원코드") == fund), None)
    if f is None:
        raise store.NotFound(f"재원 {fund} 이(가) 재원 목록에 없습니다. list_funds 로 재원코드를 확인하세요.")
    out = {"재원": fund, "과제명": f.get("과제명"), "종류": f.get("종류") or store.FUND_TYPE_DEFAULT, "기간": f"{f.get('시작일') or ''}~{f.get('종료일') or ''}"}
    if (f.get("잔액미관리") or "").upper() == "Y":
        out.update(잔액미관리=True, 행=[], 설명="재원 출처로만 쓰고 예산·잔액을 관리하지 않는 재원입니다.")
        return out
    table = [t for t in _dashboard(data)["table"] if t["재원"] == fund and (not item or t["예산목"] == item)]
    if item and not table:
        if item not in store.BUDGET_ITEMS and out["종류"] != store.FUND_TYPE_POOL:
            raise ValueError(f"예산목 '{item}' 은(는) 목록에 없습니다. 예산목: {store.BUDGET_ITEMS}")
        table = [{"재원": fund, "예산목": item, "예산현액": 0, "집행액": 0, "잔액": 0, "집행률": None, "품의대기": 0, "가용잔액": 0, "설명": "예산 미입력"}]
    for t in table:
        if not t.get("예산현액") and "설명" not in t:
            t["설명"] = "예산 미입력 (집행·대기만 있음)"
    out["행"] = table
    return out


FX_URL = "https://api.frankfurter.app/{date}?from={cur}&to=KRW"


def _http_get_json(url: str, timeout: float = 6.0) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ledger-ai/1"}), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fx_rate(currency: str = "USD", date: str = "") -> dict:
    """환율: 외화 1단위당 원화 (학회 여비 계산 등). 출처는 유럽중앙은행 기준 환율(frankfurter.app, 영업일 기준, 키 없음)이며 은행 고시 환율과 다를 수 있다고 사용자에게 알릴 것.
    currency 는 USD/EUR/JPY/GBP/CNY 같은 ISO 코드. date 를 비우면 최신, YYYY-MM-DD 를 주면 그 날짜(휴일이면 직전 영업일). 반환 {통화, 날짜, 원화환율, 출처} 또는 {error}."""
    cur = str(currency or "USD").strip().upper()
    if cur == "KRW" or len(cur) != 3:
        return {"error": f"통화 코드 '{cur}' 은(는) 조회할 수 없습니다. USD, EUR, JPY 같은 ISO 코드를 쓰세요."}
    url = FX_URL.format(date=(date or "latest").strip(), cur=cur)
    try:
        j = _http_get_json(url)
    except Exception as e:
        return {"error": f"환율 조회 실패 ({type(e).__name__}: {str(e)[:120]}). 인터넷 연결 또는 통화 코드를 확인하세요."}
    rate = (j.get("rates") or {}).get("KRW")
    if rate is None:
        return {"error": f"'{cur}' 환율을 받지 못했습니다: {str(j)[:120]}"}
    return {"통화": cur, "날짜": j.get("date"), "원화환율": rate, "출처": "유럽중앙은행 기준 환율 (frankfurter.app)"}


# ---------- 도구 세트 ----------
READ_TOOLS = ["list_funds", "list_vendors", "list_tags", "get_dashboard", "list_exec", "list_req", "list_budget", "list_deposit", "get_exec",
              "budget_balance", "search_ledger", "fx_rate"]

_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean"}


def tool_schema(name: str) -> dict:
    """함수 서명 → AI API 도구 정의 {name, description, input_schema}. 기본값이 있는 인자는 선택."""
    fn = globals()[name]
    props, required = {}, []
    hints = typing.get_type_hints(fn)  # 문자열 주석(from __future__ import annotations)을 실제 타입으로
    for p in inspect.signature(fn).parameters.values():
        t = _JSON_TYPES.get(hints.get(p.name), "string")
        props[p.name] = {"type": t}
        if p.default is inspect.Parameter.empty:
            required.append(p.name)
    return {"name": name, "description": inspect.getdoc(fn) or "", "input_schema": {"type": "object", "properties": props, "required": required}}


def call(name: str, args: dict[str, Any]) -> Any:
    """이름으로 도구를 호출한다. 알 수 없는 인자는 버린다 (모델이 지어낸 인자 방어)."""
    fn = globals()[name]
    allowed = inspect.signature(fn).parameters
    return fn(**{k: v for k, v in args.items() if k in allowed})
