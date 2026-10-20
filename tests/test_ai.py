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
    return ck.done("AI 도구 검사")


if __name__ == "__main__":
    sys.exit(main())
