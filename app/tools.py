"""장부 조회 도구 (공통 모듈).

MCP 서버(mcp_server.py)와 앱 내 AI 에이전트(ai.py)가 같은 함수를 쓴다.
- 함수는 파이썬 객체(dict/list)를 반환한다. JSON 직렬화는 호출자가 한다.
- 함수 서명과 docstring 이 도구 정의다: MCP 는 그대로 노출하고, AI 쪽은 tool_schema() 로 JSON 스키마를 만든다.
- 역할별 도구 세트는 이름 목록으로 조립한다 (READ_TOOLS 등). 어떤 역할에 어떤 도구를 줄지는 호출자가 정한다.
- 쓰기는 이 모듈에 없다. 장부를 바꾸는 일은 store 를 직접 쓰는 MCP 쓰기 도구나 화면 저장이 한다.
"""
from __future__ import annotations

import inspect
import typing
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
    """거래번호로 집행 1건을 조회한다 (_row 포함)."""
    r = next((x for x in store.read_all()["exec"] if x["거래번호"] == number), None)
    if r is None:
        raise store.NotFound(f"거래번호 {number} 를 찾을 수 없습니다.")
    return r


# ---------- 도구 세트 ----------
READ_TOOLS = ["list_funds", "list_vendors", "list_tags", "get_dashboard", "list_exec", "list_req", "list_budget", "list_deposit", "get_exec"]

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
