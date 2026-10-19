"""센터 회계대장 MCP 서버 (stdio).

Claude Desktop / Claude Code 에서 장부를 도구로 조회·입력할 수 있게 노출한다.
등록 예 (Claude Code):
  claude mcp add ledger -- python "<이 폴더 절대경로>/mcp_server.py"
Claude Desktop 은 claude_desktop_config.json 의 mcpServers 에 같은 command/args 를 추가.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.chdir(Path(__file__).resolve().parent)
from dotenv import load_dotenv  # noqa: E402
import settings  # noqa: E402
load_dotenv(settings.ENV_PATH)  # store 를 불러오기 전에 .env 적용 (LEDGER_XLSX 등). LEDGER_ENV 가 있으면 그 파일

from mcp.server.mcpserver import MCPServer  # mcp 2.x
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

import store
from main import build_dashboard

mcp = MCPServer(
    "ledger",
    instructions=(
        "의료인공지능센터 연구비 회계대장. 재원(과제)별 예산·집행·품의·적립금을 조회하고 입력한다. "
        f"예산목은 {store.BUDGET_ITEMS} 중 하나. 번호(거래번호/품의번호)는 자동 부여되며 YYYY-재원코드-NNN 형식. "
        "쓰기 도구는 엑셀 파일을 직접 수정하므로 사용자 확인 후 호출할 것. 삭제 후에는 다른 행의 _row 가 바뀌므로 반드시 다시 조회할 것. "
        "오늘 날짜는 서버가 알려주지 않으므로 상대 날짜('어제')는 사용자에게 확인."
    ),
)


def _j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _safe(fn):
    """store 예외를 짧은 한국어 메시지의 예외로 다시 올려 클라이언트가 isError 로 인식하게 함."""
    import functools
    @functools.wraps(fn)
    def w(*a, **k):
        try:
            return fn(*a, **k)
        except ToolError:
            raise
        except (ValueError, store.NotFound, store.LedgerLocked) as e:
            raise ToolError(str(e)) from None
        except Exception as e:  # 파일 없음·openpyxl 오류 등
            raise ToolError(f"{type(e).__name__}: {e}") from None
    return w


READONLY = os.environ.get("LEDGER_MCP_READONLY") == "1"
RO = ToolAnnotations(readOnlyHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True)


def write_tool(annotations=WRITE):
    """쓰기 도구: LEDGER_MCP_READONLY=1 이면 등록하지 않음."""
    def deco(fn):
        return fn if READONLY else mcp.tool(annotations=annotations)(fn)
    return deco


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


# ---------- 조회 ----------
@mcp.tool(annotations=RO)
@_safe
def list_funds() -> str:
    """재원(과제) 목록을 반환한다: 재원코드, 과제명, 시작일, 종료일, 비고, 인건비예산, 종류(국책/원내/위탁/교육/공금/기타), 잔액미관리(Y 면 재원 출처로만 쓰고 예산·잔액을 관리하지 않음). 공금 재원은 예산목별 예산 없이 예산변동 '입금' 합계 − 집행으로 잔액만 관리한다."""
    return _j(store.read_all()["funds"])


@mcp.tool(annotations=RO)
@_safe
def list_vendors() -> str:
    """적립금 거래처 목록: 거래처명, 코드(적립번호 앞자리), 비고. 미등록 거래처로 적립금을 넣으면 이름 앞 글자로 코드가 자동 등록된다."""
    return _j(store.read_all()["vendor"])


@mcp.tool(annotations=RO)
@_safe
def list_tags() -> str:
    """태그(센터 내부 계정) 목록: 태그명, 분류, 설명. 집행·품의·적립금의 태그는 이 목록 중 1개여야 한다."""
    return _j(store.read_all()["tags"])


@mcp.tool(annotations=RO)
@_safe
def get_dashboard(fund: str = "", year: str = "") -> str:
    """재원×예산목별 예산현액·집행액·잔액·집행률·품의대기·가용잔액 표와 월별 집행액, 거래처/태그별 집계를 반환한다.
    fund 로 재원코드를, year 로 연도(YYYY)를 지정하면 집행·품의가 그 범위로 좁혀진다.
    웹 대시보드와 같은 집계 범위: 재원 시트에 없는 재원(외부 지급처 인건비 등)이나 11개 예산목 밖의 집행·대기 품의는 table 에 넣지 않고
    excluded.exec / excluded.req (거래번호·품의번호, 재원, 예산목, 금액, 사유)와 excluded_total 로 따로 반환한다."""
    data = store.read_all()
    if year:
        data["exec"] = [r for r in data["exec"] if str(r["원인발생일"] or "").startswith(year)]
        data["req"] = [r for r in data["req"] if str(r["원인발생일"] or "").startswith(year)]
    d = build_dashboard(data)
    if fund:
        d["table"] = [t for t in d["table"] if t["재원"] == fund]
        d["monthly"] = {fund: d["monthly"].get(fund, {})}
        d["excluded"] = {k: [x for x in v if x["재원"] == fund] for k, v in d["excluded"].items()}
        d["excluded_total"] = {"exec": sum(x["금액"] or 0 for x in d["excluded"]["exec"]), "exec_count": len(d["excluded"]["exec"]),
                               "req": sum(x["금액"] or 0 for x in d["excluded"]["req"]), "req_count": len(d["excluded"]["req"])}
    return _j(d)


@mcp.tool(annotations=RO)
@_safe
def list_exec(fund: str = "", year: str = "", month: str = "", vendor: str = "", q: str = "", unpaid_only: bool = False,
              limit: int = 200, offset: int = 0) -> str:
    """집행내역을 조회한다. month 는 MM, vendor 는 거래처 부분일치, q 는 전체 열 검색, unpaid_only 는 지출완료일이 비어 있는 건만.
    각 행의 _row 는 수정/삭제에 쓰는 행 번호(삭제 후 바뀜). 최신순 정렬, limit/offset 으로 나눠 받는다. 반환: {total, rows}.
    상태는 저장값(발생/청구/보완/완료/결의), 상태표시는 화면 이름(발생/청구/보완/승인/완료: 완료→승인, 결의→완료). 사용자에게는 상태표시로 말할 것.
    연결품의번호는 품의→집행 전환으로 생긴 행의 원 품의번호."""
    rows = _filter(store.read_all()["exec"], fund, year, month, vendor, q)
    if unpaid_only:
        rows = [r for r in rows if not r.get("지출완료일")]
    rows.sort(key=lambda r: (str(r.get("원인발생일") or ""), r["_row"]), reverse=True)
    return _j({"total": len(rows), "rows": rows[offset:offset + max(1, min(limit, 1000))]})


@mcp.tool(annotations=RO)
@_safe
def list_req(fund: str = "", year: str = "", status: str = "", q: str = "", limit: int = 200, offset: int = 0) -> str:
    """품의내역을 조회한다. status 는 대기/집행완료/취소. 최신순, limit/offset. 반환: {total, rows}."""
    rows = _filter(store.read_all()["req"], fund, year, "", "", q)
    if status:
        rows = [r for r in rows if r.get("상태") == status]
    rows.sort(key=lambda r: (str(r.get("원인발생일") or ""), r["_row"]), reverse=True)
    return _j({"total": len(rows), "rows": rows[offset:offset + max(1, min(limit, 1000))]})


@mcp.tool(annotations=RO)
@_safe
def list_budget(fund: str = "") -> str:
    """예산변동 이력을 조회한다. 변경회차 '이월'=이월금, '당초'=당초액, 숫자=변경 회차. 예산현액은 재원·예산목별 합계."""
    rows = store.read_all()["budget"]
    return _j([r for r in rows if not fund or r["재원"] == fund])


@mcp.tool(annotations=RO)
@_safe
def list_deposit(vendor: str = "") -> str:
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
    return _j({"잔액": bal, "내역": rows, "구분오류행": bad})


# ---------- 입력 ----------
@write_tool()
@_safe
def add_exec(원인발생일: str, 재원: str, 예산목: str, 금액: float, 거래처: str = "", 적요: str = "",
             세목: str = "", 세세목: str = "", 사용자: str = "", 태그: str = "", 관리번호: str = "",
             지급청구일: str = "", 지출완료일: str = "", 비고: str = "") -> str:
    """집행내역에 한 행을 추가한다. 날짜는 YYYY-MM-DD. 재원은 list_funds 의 재원코드, 예산목은 11개 목록 중 하나, 태그는 list_tags 의 태그명 1개(없으면 빈 값).
    금액은 원 단위 양수 정수. 지출완료일이 비어 있으면 '지급대기'. 관리번호는 병원 ERP/전자결재 문서번호(선택). 거래번호는 자동 부여. 반환값에 거래번호와 _row."""
    rec = dict(원인발생일=원인발생일, 재원=재원, 예산목=예산목, 금액=금액, 거래처=거래처, 적요=적요, 세목=세목,
               세세목=세세목, 사용자=사용자, 태그=태그, 관리번호=관리번호, 지급청구일=지급청구일, 지출완료일=지출완료일, 비고=비고)
    return _j(store.create("exec", rec))


@write_tool()
@_safe
def add_req(원인발생일: str, 재원: str, 예산목: str, 금액: float, 거래처: str = "", 적요: str = "",
            지출예정일: str = "", 세목: str = "", 세세목: str = "", 결제수단: str = "", 태그: str = "",
            품의자: str = "", 비고: str = "") -> str:
    """품의내역에 한 행을 추가한다(상태=대기). 재원은 list_funds 의 재원코드, 예산목은 11개 목록 중 하나, 태그는 list_tags 값. 결제수단은 연구비카드/계좌이체/연구자선지출/공금통장/적립금/기타 중 하나 또는 빈 값. 금액은 원 단위 양수."""
    rec = dict(원인발생일=원인발생일, 재원=재원, 예산목=예산목, 금액=금액, 거래처=거래처, 적요=적요, 지출예정일=지출예정일,
               세목=세목, 세세목=세세목, 결제수단=결제수단, 태그=태그, 품의자=품의자, 비고=비고, 상태="대기")
    return _j(store.create("req", rec))


@write_tool()
@_safe
def add_budget(재원: str, 변경회차: str, 금액: dict[str, float], 신청일자: str, 변경사유: str = "") -> str:
    """예산변동 행을 추가한다. 변경회차는 '이월', '당초' 또는 숫자. 금액은 {예산목: 금액} 사전 (음수 가능).
    신청일자(YYYY-MM-DD)는 필수: 집행 표의 거래별 예산목 잔액은 이 날짜부터 변경액을 반영한다."""
    rec = dict(재원=재원, 변경회차=변경회차, 신청일자=신청일자, 변경사유=변경사유)
    for k, v in 금액.items():
        if k not in store.BUDGET_ITEMS:
            return _j({"error": f"알 수 없는 예산목: {k}"})
        rec[k] = v
    return _j(store.create("budget", rec))


@write_tool()
@_safe
def add_deposit(일자: str, 거래처: str, 구분: str, 금액: float, 적요: str = "", 사용자: str = "", 증빙번호: str = "",
                비고: str = "", 태그: str = "", record_exec: bool = False, 재원: str = "", 예산목: str = "",
                발주일: str = "", 결제일: str = "", 수령일: str = "") -> str:
    """적립금 적립/사용을 기록한다. 구분은 '적립' 또는 '사용'. 적립이면서 record_exec=True 이면 재원·예산목으로 집행내역에도 선결제 한 건을 기록한다.
    사용 행은 발주일(비우면 일자)·결제일·수령일로 단계(대기/발주/결제/수령)가 정해진다. 적립 행은 단계 없음."""
    rec = dict(일자=일자, 거래처=거래처, 구분=구분, 금액=금액, 적요=적요, 사용자=사용자, 증빙번호=증빙번호, 비고=비고, 태그=태그,
               발주일=발주일, 결제일=결제일, 수령일=수령일)
    if record_exec:
        rec.update(_record_exec=True, _재원=재원, _예산목=예산목)
    return _j(store.create("deposit", rec))


@write_tool(DESTRUCTIVE)
@_safe
def update_row(kind: str, row: int, fields: dict, expect_id: str = "") -> str:
    """행을 수정한다. kind 는 exec/req/budget/funds/deposit/tags, row 는 조회 결과의 _row. fields 는 바꿀 열만 넣어도 된다(나머지는 유지).
    expect_id 에 그 행의 거래번호/품의번호/재원코드/태그명을 넣으면 행이 밀렸을 때(삭제 후 _row 변경) 엉뚱한 행을 고치지 않도록 검사한다. 삭제 뒤에는 반드시 다시 조회할 것."""
    if kind not in store._SHEETS:
        raise ToolError(f"알 수 없는 kind: {kind}")
    data = store.read_all()
    cur = next((r for r in data[kind] if r["_row"] == row), None)
    if cur is None:
        raise ToolError("행을 찾을 수 없습니다. 다시 조회하세요.")
    _check_id(kind, cur, expect_id)
    rec = {k: v for k, v in cur.items() if k != "_row"}
    rec.update(fields)
    return _j(store.update(kind, row, rec, store._ident(kind, cur)))


@write_tool(DESTRUCTIVE)
@_safe
def delete_row(kind: str, row: int, expect_id: str = "") -> str:
    """행을 삭제한다. 되돌릴 수 없으므로 사용자 확인 후 호출. expect_id(거래번호/품의번호/재원코드/태그명)를 함께 주면 행 밀림을 검사한다.
    삭제 후에는 다른 행의 _row 가 바뀌므로 반드시 다시 조회할 것. 반환값에 삭제된 행 내용이 들어 있다."""
    data = store.read_all()
    cur = next((r for r in data.get(kind, []) if r["_row"] == row), None)
    if cur is None:
        raise ToolError("행을 찾을 수 없습니다. 다시 조회하세요.")
    _check_id(kind, cur, expect_id)
    store.delete(kind, row, store._ident(kind, cur))
    return _j({"ok": True, "deleted": cur})


@write_tool(DESTRUCTIVE)
@_safe
def req_to_exec(row: int, expect_id: str = "") -> str:
    """대기 중인 품의를 집행내역으로 옮기고 품의 상태를 집행완료로 바꾼다. row 는 품의의 _row, expect_id 는 품의번호(행 밀림 검사)."""
    cur = next((r for r in store.read_all()["req"] if r["_row"] == row), None)
    if cur is None:
        raise ToolError("품의 행을 찾을 수 없습니다. 다시 조회하세요.")
    _check_id("req", cur, expect_id)
    return _j(store.req_to_exec(row, {}, store._ident("req", cur)))


def _check_id(kind: str, cur: dict, expect_id: str):
    key = store._SHEETS[kind][3]
    if expect_id and key and str(cur.get(key)) != str(expect_id):
        raise ToolError(f"행 {cur['_row']} 의 {key} 는 '{cur.get(key)}' 인데 expect_id 는 '{expect_id}' 입니다. 행이 밀렸을 수 있으니 다시 조회하세요.")


@mcp.tool(annotations=RO)
@_safe
def get_exec(number: str) -> str:
    """거래번호로 집행 1건을 조회한다 (_row 포함)."""
    r = next((x for x in store.read_all()["exec"] if x["거래번호"] == number), None)
    if r is None:
        raise ToolError(f"거래번호 {number} 를 찾을 수 없습니다.")
    return _j(r)


if __name__ == "__main__":
    mcp.run(transport="stdio")
