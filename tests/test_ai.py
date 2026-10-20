"""AI 도우미 검사 (모델 호출 없음): 공통 도구 모듈 tools.py 와 MCP 서버의 읽기 도구.
QA 장부 복사본(tests/.tmp/ai/)에 대해 실행한다: python -I tests/test_ai.py
"""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import APP, QA_DIR, QA_XLSX, TMP, Check, settle_xlsx  # noqa: E402

# app/ 안에서 실행되는 탐침: 검사 결과를 [이름, 성공여부, 상세] 목록으로 출력한다.
PROBE = r'''
import json, inspect, os, sys
sys.path.insert(0, os.getcwd())
import store, tools, mcp_server
out = []
def ck(name, cond, detail=""):
    out.append([name, bool(cond), str(detail)[:200]])

# --- tools.py 조회 함수 ---
funds = tools.list_funds()
ck("list_funds: 재원이 있다", len(funds) > 0, len(funds))
ck("list_tags: 태그가 있다", len(tools.list_tags()) > 0)
ck("list_vendors: 목록 반환", isinstance(tools.list_vendors(), list))
ex = tools.list_exec()
ck("list_exec: {total, rows}", set(ex) == {"total", "rows"} and ex["total"] == len(ex["rows"]), ex.get("total"))
dates = [str(r.get("원인발생일") or "") for r in ex["rows"]]
ck("list_exec: 최신순 정렬", dates == sorted(dates, reverse=True))
import collections
f0 = collections.Counter(r["재원"] for r in ex["rows"]).most_common(1)[0][0]  # 행이 가장 많은 재원
sub = tools.list_exec(fund=f0, limit=5)
ck("list_exec: fund 필터·limit", sub["total"] >= 5 and len(sub["rows"]) == 5 and all(r["재원"] == f0 for r in sub["rows"]))
yr = dates[0][:4]
ck("list_exec: year 필터", all(str(r["원인발생일"]).startswith(yr) for r in tools.list_exec(year=yr)["rows"]))
unpaid = tools.list_exec(unpaid_only=True)
ck("list_exec: unpaid_only", all(not r.get("지출완료일") for r in unpaid["rows"]))
vend = next((r["거래처"] for r in ex["rows"] if r.get("거래처")), "")
ck("list_exec: vendor 부분일치", vend and all(vend in r["거래처"] for r in tools.list_exec(vendor=vend)["rows"]), vend)
q = tools.list_exec(q=vend)
ck("list_exec: q 전체 열 검색", q["total"] >= tools.list_exec(vendor=vend)["total"])
rq = tools.list_req()
ck("list_req: {total, rows}", set(rq) == {"total", "rows"})
ck("list_req: status 필터", all(r["상태"] == "대기" for r in tools.list_req(status="대기")["rows"]))
ck("list_budget: fund 필터", all(r["재원"] == f0 for r in tools.list_budget(fund=f0)))
dep = tools.list_deposit()
ck("list_deposit: 잔액 = 적립 - 사용", all(v["잔액"] == v["적립"] - v["사용"] for v in dep["잔액"].values()))
d = tools.get_dashboard()
ck("get_dashboard: table 이 있다", len(d["table"]) > 0)
d1 = tools.get_dashboard(fund=f0)
ck("get_dashboard: fund 필터", all(t["재원"] == f0 for t in d1["table"]) and list(d1["monthly"]) == [f0])
no = ex["rows"][0]["거래번호"]
ck("get_exec: 거래번호 조회", tools.get_exec(no)["거래번호"] == no)
try:
    tools.get_exec("0000-없음-999"); ck("get_exec: 없으면 NotFound", False)
except store.NotFound:
    ck("get_exec: 없으면 NotFound", True)

# --- 새 도구: budget_balance · search_ledger · get_exec 상세 · fx_rate ---
bb = tools.budget_balance(f0)
ck("budget_balance: 재원 전체 = 대시보드 표", bb["행"] == [t for t in d["table"] if t["재원"] == f0] and bb["과제명"])
item = bb["행"][0]["예산목"]
b1 = tools.budget_balance(f0, item)
ck("budget_balance: 예산목 한 줄 = 대시보드 표 행", b1["행"] == [t for t in d["table"] if t["재원"] == f0 and t["예산목"] == item])
ck("budget_balance: 가용잔액 = 예산현액 − 집행액 − 품의대기", all(abs(t["가용잔액"] - (t["예산현액"] - t["집행액"] - t["품의대기"])) < 1 for t in bb["행"]))
have = {(t["재원"], t["예산목"]) for t in d["table"]}
tracked = [f["재원코드"] for f in funds if (f.get("잔액미관리") or "").upper() != "Y" and (f.get("종류") or "국책") != "공금"]
fo, other = next(((f, i) for f in tracked for i in store.BUDGET_ITEMS if (f, i) not in have), (None, None))
if other:
    b2 = tools.budget_balance(fo, other)
    ck("budget_balance: 예산 없는 예산목은 '예산 미입력' 한 줄", len(b2["행"]) == 1 and b2["행"][0]["설명"].startswith("예산 미입력") and b2["행"][0]["가용잔액"] == 0, b2)
try:
    tools.budget_balance(f0, "없는예산목"); ck("budget_balance: 목록 밖 예산목은 ValueError", False)
except ValueError as e:
    ck("budget_balance: 목록 밖 예산목은 ValueError", "예산목" in str(e))
try:
    tools.budget_balance("ZZ99"); ck("budget_balance: 없는 재원은 NotFound", False)
except store.NotFound:
    ck("budget_balance: 없는 재원은 NotFound", True)
unt = next((f["재원코드"] for f in funds if (f.get("잔액미관리") or "").upper() == "Y"), None)
if unt:
    ck("budget_balance: 잔액미관리 재원은 행 없음", tools.budget_balance(unt)["잔액미관리"] is True and tools.budget_balance(unt)["행"] == [])

rqs = store.read_all()["request"]
word = next((str(r["품목"]).split()[0] for r in rqs if r.get("품목")), "")
sr = tools.search_ledger(word)
ck("search_ledger: 세 종류 모두 반환", set(sr) == {"exec", "request", "req"}, list(sr))
ck("search_ledger: 신청 품목 검색", word and sr["request"]["total"] >= 1 and all(word.lower() in " ".join(str(v) for v in r.values()).lower() for r in sr["request"]["rows"]), word)
ck("search_ledger: 요약 열만", word and set(sr["request"]["rows"][0]) == set(tools._RQ_BRIEF))
w2 = vend.split()[0]
se = tools.search_ledger(w2, kinds="exec", limit=3)
ck("search_ledger: kinds·limit", list(se) == ["exec"] and len(se["exec"]["rows"]) <= 3 and se["exec"]["total"] >= 1)
ck("search_ledger: AND 검색은 결과가 줄거나 같다", tools.search_ledger(w2 + " 없는낱말xyz", kinds="exec")["exec"]["total"] == 0)
dr = sorted(dates)
mid = dr[len(dr) // 2]
sd = tools.search_ledger("", kinds="exec", date_from=mid, limit=200)["exec"]
ck("search_ledger: 날짜 범위", sd["total"] == sum(1 for x in dates if x >= mid) and all(r["원인발생일"] >= mid for r in sd["rows"]))
ck("search_ledger: fund 필터", all(r["재원"] == f0 for r in tools.search_ledger("", fund=f0, kinds="exec")["exec"]["rows"]))

gx = tools.get_exec(no)
ck("get_exec: 증빙·연결품의·적립금연결 키", all(k in gx for k in ("증빙", "연결품의", "적립금연결", "상태표시")))
linked = next((r for r in ex["rows"] if r.get("연결품의번호")), None)
if linked:
    g2 = tools.get_exec(linked["거래번호"])
    ck("get_exec: 연결품의 행", g2["연결품의"] and g2["연결품의"]["품의번호"] == linked["연결품의번호"])
evn = next((e["거래번호"] for e in store.read_all().get("evidence", []) if e.get("거래번호")), None)
if evn:
    ck("get_exec: 증빙 목록", len(tools.get_exec(evn)["증빙"]) >= 1 and "has_file" in tools.get_exec(evn)["증빙"][0])

calls = []
tools._http_get_json = lambda url, timeout=6.0: (calls.append(url), {"amount": 1.0, "base": "USD", "date": "2026-10-17", "rates": {"KRW": 1385.2}})[1]
fx = tools.fx_rate("usd")
ck("fx_rate: 원화환율·날짜·출처", fx == {"통화": "USD", "날짜": "2026-10-17", "원화환율": 1385.2, "출처": fx["출처"]} and "frankfurter" in fx["출처"])
ck("fx_rate: latest URL", calls[-1] == "https://api.frankfurter.app/latest?from=USD&to=KRW", calls[-1])
tools.fx_rate("EUR", "2026-10-01")
ck("fx_rate: 날짜 URL", calls[-1] == "https://api.frankfurter.app/2026-10-01?from=EUR&to=KRW", calls[-1])
ck("fx_rate: KRW 는 error", "error" in tools.fx_rate("KRW"))
def boom(url, timeout=6.0): raise OSError("no network")
tools._http_get_json = boom
ck("fx_rate: 실패는 error 로 (예외 없음)", "error" in tools.fx_rate("USD") and "no network" in tools.fx_rate("USD")["error"])

# --- 메모: store 검증 + read_memo ---
m1 = store.create("memo", {"종류": "일반", "내용": "식대는 참석자 명단과 영수증이 필요", "비고": ""})
ck("memo: 일반 메모 저장, 작성일 자동", m1.get("_row") and m1["작성일"] and m1["대상"] == "", m1)
m2 = store.create("memo", {"종류": "재원", "대상": f0, "내용": "장비 구매 전 사전승인 필요", "작성일": "2026-10-01"})
ck("memo: 재원 메모 저장", m2["대상"] == f0 and m2["작성일"] == "2026-10-01")
for bad, why in (({"종류": "기타", "내용": "x"}, "종류"), ({"종류": "일반", "내용": " "}, "내용"), ({"종류": "거래처", "내용": "x"}, "대상"), ({"종류": "재원", "대상": "ZZ99", "내용": "x"}, "재원코드")):
    try:
        store.create("memo", bad); ck(f"memo: 거부 ({why})", False)
    except ValueError as e:
        ck(f"memo: 거부 ({why})", why in str(e), str(e))
allm = tools.read_memo()
ck("read_memo: 전부", len(allm) == 2 and {r["종류"] for r in allm} == {"일반", "재원"})
ck("read_memo: kind 필터", [r["내용"] for r in tools.read_memo(kind="일반")] == ["식대는 참석자 명단과 영수증이 필요"])
ck("read_memo: target 부분일치", [r["_row"] for r in tools.read_memo(target=f0[:3])] == [m2["_row"]])
ck("read_memo: 없으면 빈 목록", tools.read_memo(kind="거래처") == [])
up = store.update("memo", m2["_row"], {**{k: v for k, v in m2.items() if not k.startswith("_")}, "내용": "장비 구매 전 사전승인 필요 (100만원 이상)"})
ck("memo: 수정", up["내용"].endswith("(100만원 이상)"))
store.delete("memo", m1["_row"])
ck("memo: 삭제 후 read_memo (xlsx 는 행 번호가 당겨짐)", [r["내용"] for r in tools.read_memo()] == [up["내용"]])
ck("memo: 메타 memo_kinds", store.read_all()["meta"]["memo_kinds"] == ["재원", "거래처", "일반"])

# --- 도구 정의·호출 ---
for n in tools.READ_TOOLS:
    s = tools.tool_schema(n)
    ck(f"tool_schema({n}): 설명·스키마", s["description"] and s["input_schema"]["type"] == "object")
s = tools.tool_schema("list_exec")
ck("tool_schema: 선택 인자는 required 에 없다", s["input_schema"]["required"] == [] and s["input_schema"]["properties"]["limit"]["type"] == "integer")
ck("tool_schema(get_exec): number 필수", tools.tool_schema("get_exec")["input_schema"]["required"] == ["number"])
ck("call: 알 수 없는 인자는 버린다", tools.call("list_exec", {"fund": f0, "made_up": 1})["total"] == sub["total"])

# --- MCP 서버가 같은 함수를 쓴다 ---
for n in tools.READ_TOOLS:
    ck(f"mcp.{n}: 서명 같음", inspect.signature(getattr(mcp_server, n)) == inspect.signature(getattr(tools, n)))
    ck(f"mcp.{n}: 설명 같음", inspect.getdoc(getattr(mcp_server, n)) == inspect.getdoc(getattr(tools, n)))
same = lambda a, b: json.loads(a) == json.loads(json.dumps(b, ensure_ascii=False, default=str))
ck("mcp.list_exec == tools.list_exec", same(mcp_server.list_exec(fund=f0, limit=5), sub))
ck("mcp.get_dashboard == tools.get_dashboard", same(mcp_server.get_dashboard(fund=f0), d1))
ck("mcp.list_deposit == tools.list_deposit", same(mcp_server.list_deposit(), dep))
ck("mcp.get_exec == tools.get_exec", same(mcp_server.get_exec(no), tools.get_exec(no)))
try:
    mcp_server.get_exec("0000-없음-999"); ck("mcp.get_exec: 없으면 ToolError", False)
except Exception as e:
    ck("mcp.get_exec: 없으면 ToolError", type(e).__name__ == "ToolError" and "찾을 수 없습니다" in str(e), repr(e))
print(json.dumps(out, ensure_ascii=False))
'''


def main() -> int:
    ck = Check()
    d = os.path.join(TMP, "ai")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    xlsx = os.path.join(d, "ledger.xlsx")
    shutil.copyfile(QA_XLSX, xlsx)
    settle_xlsx(xlsx)
    env = dict(os.environ, LEDGER_XLSX=xlsx, LEDGER_ENV=os.path.join(QA_DIR, "qa.env"), LEDGER_DRIVE_MOCK="1", PYTHONIOENCODING="utf-8")
    pr = subprocess.run([sys.executable, "-I", "-X", "utf8", "-c", PROBE], cwd=APP, env=env, capture_output=True, text=True, encoding="utf-8")
    ck("탐침 종료 코드 0", pr.returncode == 0, pr.stderr[-800:])
    if pr.returncode == 0:
        for name, cond, detail in json.loads(pr.stdout.strip().splitlines()[-1]):
            ck(name, cond, detail)
    api_checks(ck)
    return ck.done("AI 도구 검사")


def api_checks(ck: Check):
    """메모 CRUD 를 HTTP 로 (일반 /api/{kind} 경로). 서버는 QA 장부 복사본으로 뜬다."""
    from _env import Server
    with Server("ai-api") as sv:
        s, r = sv.call("POST", "/api/memo", {"종류": "거래처", "대상": "알파미금역점", "내용": "결제는 적립금 우선"})
        ck("API memo: POST 201/200", s == 200 and r.get("_row"), (s, r))
        row = r["_row"]
        s2, r2 = sv.call("POST", "/api/memo", {"종류": "재원", "대상": "없는재원", "내용": "x"})
        ck("API memo: 없는 재원은 400", s2 == 400 and "재원코드" in r2.get("detail", ""), (s2, r2))
        s3, all_ = sv.call("GET", "/api/all")
        ck("API memo: /api/all 에 memo", any(m["_row"] == row and m["내용"] == "결제는 적립금 우선" for m in all_.get("memo", [])))
        s4, r4 = sv.call("PUT", f"/api/memo/{row}", {"rec": {"종류": "거래처", "대상": "알파미금역점", "내용": "결제는 적립금 우선, 세금계산서 월말 일괄"}, "expect": {"종류": "거래처", "대상": "알파미금역점", "내용": "결제는 적립금 우선"}})
        ck("API memo: PUT", s4 == 200 and r4["내용"].endswith("일괄"), (s4, r4))
        s5, r5 = sv.call("PUT", f"/api/memo/{row}", {"rec": {"종류": "거래처", "대상": "알파미금역점", "내용": "다른 값"}, "expect": {"종류": "거래처", "대상": "알파미금역점", "내용": "옛 값"}})
        ck("API memo: expect 불일치는 거부 (행 불일치 404)", s5 == 404 and "일치하지" in r5.get("detail", ""), (s5, r5))
        s6, r6 = sv.call("DELETE", f"/api/memo/{row}", {"expect": {"종류": "거래처", "대상": "알파미금역점", "내용": "결제는 적립금 우선, 세금계산서 월말 일괄"}})
        ck("API memo: DELETE", s6 == 200 and r6.get("ok"), (s6, r6))
        s7, all2 = sv.call("GET", "/api/all")
        ck("API memo: 삭제 뒤 목록에 없음", not any(m["_row"] == row for m in all2.get("memo", [])))


if __name__ == "__main__":
    sys.exit(main())
