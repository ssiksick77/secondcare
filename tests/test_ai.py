"""AI 도우미 검사 (모델 호출 없음): 공통 도구 모듈 tools.py, MCP 서버의 읽기 도구, 메모 저장소, 채팅 에이전트 루프(가짜 클라이언트).
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
ck("memo: 메타 memo_kinds", store.read_all()["meta"]["memo_kinds"] == ["재원", "거래처", "비세목", "일반"])
# 비세목 메모: 대상이 행의 예산목·세목·세세목 중 하나와 같으면 활성화
try:
    store.create("memo", {"종류": "비세목", "내용": "x"}); ck("memo: 비세목은 대상 필수", False)
except ValueError as e:
    ck("memo: 비세목은 대상 필수", "예산목·세목·세세목" in str(e), str(e))
mi = store.create("memo", {"종류": "비세목", "대상": "연구활동비", "내용": "연구활동비는 50만원 초과 시 견적서 2부"})
ms = store.create("memo", {"종류": "비세목", "대상": "회의비", "내용": "회의비는 참석자 명단"})
mg = store.create("memo", {"종류": "일반", "내용": "모든 집행은 영수증 원본"})
mv = store.create("memo", {"종류": "거래처", "대상": vend, "내용": "이 거래처는 세금계산서 월말 일괄"})
allm = store.read_all()["memo"]
got = lambda rec: sorted(m["내용"] for m in tools.memos_for(rec, allm))
ck("memos_for: 예산목 일치 + 일반", got({"재원": "ZZ", "예산목": "연구활동비", "세목": "", "거래처": ""}) == ["모든 집행은 영수증 원본", "연구활동비는 50만원 초과 시 견적서 2부"])
ck("memos_for: 세목 일치 (대소문자·공백 무시)", got({"예산목": "연구시설.장비비", "세목": " 회의비 "}) == ["모든 집행은 영수증 원본", "회의비는 참석자 명단"])
ck("memos_for: 세세목 일치", "회의비는 참석자 명단" in got({"예산목": "x", "세목": "y", "세세목": "회의비"}))
ck("memos_for: 거래처·재원 메모", got({"재원": f0, "거래처": vend, "예산목": "없음"}) == sorted(["모든 집행은 영수증 원본", "이 거래처는 세금계산서 월말 일괄", "장비 구매 전 사전승인 필요 (100만원 이상)"]))
ck("memos_for: 일치 없으면 일반만", got({"예산목": "없는것"}) == ["모든 집행은 영수증 원본"])
import ai
sg2 = json.loads(ai.suggest_prompt({"재원": f0, "거래처": vend, "예산목": "연구활동비", "금액": 10000}, "exec")[1])
ck("suggest_prompt: 관련메모 포함 (재원·거래처·비세목·일반)", {m["종류"] for m in sg2["관련메모"]} == {"재원", "거래처", "비세목", "일반"} and all(set(m) == {"종류", "대상", "내용"} for m in sg2["관련메모"]), sg2["관련메모"])
for r_ in (mi, ms, mg, mv):
    pass  # xlsx 는 삭제 시 행이 당겨지므로 내용으로 지운다
for content in ("연구활동비는 50만원 초과 시 견적서 2부", "회의비는 참석자 명단", "모든 집행은 영수증 원본", "이 거래처는 세금계산서 월말 일괄"):
    row = next(m["_row"] for m in store.read_all()["memo"] if m["내용"] == content)
    store.delete("memo", row)
ck("memo: 비세목 검사 뒤 정리", [m["내용"] for m in tools.read_memo()] == [up["내용"]])

# --- 채팅 에이전트 (ai.py): 요약 프롬프트 + 도구 루프, 가짜 Anthropic 클라이언트 ---
import ai, types
NS = types.SimpleNamespace
sysb = ai.agent_system()
systxt = "".join(b["text"] for b in sysb)
ck("agent_system: 장부 전체 없음, 작음", "<ledger>" not in systxt and "<summary>" in systxt and len(systxt) < 12000, len(systxt))
ck("agent_system: 재원 코드·오늘 날짜", f0 in systxt and "오늘 날짜" in systxt)
names = [t["name"] for t in ai.agent_tools()]
ck("agent_tools: 읽기 도구 + 제안 도구 + propose_memo", names[:len(tools.READ_TOOLS)] == tools.READ_TOOLS and "propose_exec" in names and names[-1] == "propose_memo")
def usage(): return NS(input_tokens=100, output_tokens=10, cache_read_input_tokens=0, cache_creation_input_tokens=0)
script = [
    NS(stop_reason="tool_use", content=[NS(type="text", text="확인 중"), NS(type="tool_use", id="t1", name="budget_balance", input={"fund": f0}),
                                        NS(type="tool_use", id="t2", name="get_exec", input={"number": "0000-없음-999"})], usage=usage()),
    NS(stop_reason="tool_use", content=[NS(type="tool_use", id="t3", name="propose_memo", input={"kind": "재원", "target": f0, "text": "장비는 사전승인", "reason": "규정"})], usage=usage()),
    NS(stop_reason="end_turn", content=[NS(type="text", text="답입니다")], usage=usage()),
]
sent = []
def fake_create(**kw):
    sent.append(kw); return script[len(sent) - 1]
ai._c = lambda: NS(beta=NS(messages=NS(create=fake_create)))
before = len(tools.read_memo())
res = ai.chat([{"role": "user", "content": f"{f0} 잔액?"}], turn=1)
ck("chat: 답변·calls (오류 표시)", res["answer"] == "답입니다" and [c["tool"] for c in res["calls"]] == ["budget_balance", "get_exec"] and res["calls"][0]["error"] is False and res["calls"][1]["error"] is True, res)
ck("chat: propose_memo 는 한글 키 제안 카드, 장부에 저장 안 됨", res["proposals"] == [{"id": "t1-p1", "tool": "propose_memo", "input": {"종류": "재원", "대상": f0, "내용": "장비는 사전승인", "이유": "규정"}}] and len(tools.read_memo()) == before, res["proposals"])
r1 = sent[0]["messages"][2]["content"]  # messages 는 같은 목록 (질문, 응답1, 결과1, 응답2, 결과2)
ck("chat: tool_result 에 도구 결과 JSON, 오류는 is_error", r1[0]["type"] == "tool_result" and "가용잔액" in r1[0]["content"] and r1[1].get("is_error") is True and "찾을 수 없습니다" in r1[1]["content"])
ck("chat: 제안 tool_result 는 '직접 반영되지 않았습니다'", "직접 반영되지" in sent[0]["messages"][4]["content"][0]["content"])
ck("chat: 요청에 장부 전체 없음, 도구 목록 전달", all("<ledger>" not in b["text"] for b in sent[0]["system"]) and [t["name"] for t in sent[0]["tools"]] == names and len(sent) == 3)
ck("chat: 사용량 합산", res["usage"]["input"] == 300 and res["usage"]["output"] == 30, res["usage"])
sent.clear()
script[:] = [NS(stop_reason="tool_use", content=[NS(type="tool_use", id=f"x{i}", name="list_tags", input={})], usage=usage()) for i in range(ai.AGENT_ROUNDS + 1)]
out2 = ai.chat([{"role": "user", "content": "루프"}])
ck("chat: 왕복 상한에서 멈추고 안내", len(sent) == ai.AGENT_ROUNDS and "횟수를 넘었습니다" in out2["answer"] and len(out2["calls"]) == ai.AGENT_ROUNDS)
big = tools.list_exec(limit=1000)
ck("run_tool: 긴 결과는 잘라서 안내", len(ai.run_tool("list_exec", {"limit": 1000})[0]) <= ai.TOOL_RESULT_MAX + 120 or len(json.dumps(big, ensure_ascii=False)) <= ai.TOOL_RESULT_MAX)
ck("run_tool: 알 수 없는 인자는 무시", ai.run_tool("list_funds", {"nope": 1})[1] is False)

# --- 추천(/api/ai/suggest) 프롬프트: 장부 전체가 아니라 같은 거래처 이력·같은 금액·해당 재원 예산만 ---
sg_sys, sg_user = ai.suggest_prompt({"재원": f0, "거래처": vend, "금액": 10000, "적요": "검사"}, "exec")
sg = json.loads(sg_user)
ck("suggest_prompt: 장부 전체 없음", "<ledger>" not in sg_sys and set(sg) == {"입력중인행", "종류", "같은거래처_최근이력", "같은금액_최근이력", "해당재원_예산현황", "관련메모"}, list(sg))
ck("suggest_prompt: 같은 거래처 이력만 (30건 이하)", all(r["거래처"] == vend for r in sg["같은거래처_최근이력"]) and len(sg["같은거래처_최근이력"]) <= 30)
ck("suggest_prompt: 해당 재원 예산만", all(t["재원"] == f0 for t in sg["해당재원_예산현황"]) and sg["해당재원_예산현황"])

# --- 채팅방 저장소 (chat_store) + chat_in_room (가짜 클라이언트) ---
import chat_store, datetime as _dt
A, B = "a@example.com", "b@example.com"
c1 = chat_store.create_chat(A)
ck("chat_store: 새 방 (제목 없음, 보관 아님)", c1["id"] and c1["title"] == "" and c1["kept"] is False and c1["count"] == 0)
m1 = chat_store.add_message(A, c1["id"], "user", "  QA01   연구활동비 잔액이 얼마나 남았는지 자세히 알려줘 " + "x" * 50)
ck("chat_store: 첫 질문으로 제목 30자", chat_store.get_chat(A, c1["id"])["title"] == ("QA01 연구활동비 잔액이 얼마나 남았는지 자세히 알려줘 " + "x" * 50)[:30] and m1["seq"] == 1)
m2 = chat_store.add_message(A, c1["id"], "assistant", "답", calls=[{"tool": "budget_balance", "input": {"fund": "QA01"}, "error": False}], proposals=[{"id": "t1-p1", "tool": "propose_memo", "input": {"종류": "일반"}}])
ms = chat_store.messages(A, c1["id"])
ck("chat_store: 메시지 조회 (calls·proposals 복원)", len(ms) == 2 and ms[1]["calls"][0]["tool"] == "budget_balance" and ms[1]["proposals"][0]["id"] == "t1-p1" and ms[0]["calls"] == [])
n1 = chat_store.add_message(A, c1["id"], "user", "[알림] 제안 t1-p1 저장됨", note=True)
ck("chat_store: 알림은 note, 건수에서 제외", n1["note"] is True and chat_store.get_chat(A, c1["id"])["count"] == 2)
for other in ("get_chat", "messages", "delete_chat"):
    try:
        getattr(chat_store, other)(B, c1["id"]); ck(f"chat_store: 다른 사용자 {other} → ChatNotFound", False)
    except chat_store.ChatNotFound:
        ck(f"chat_store: 다른 사용자 {other} → ChatNotFound", True)
ck("chat_store: 다른 사용자 목록에 없음", chat_store.list_chats(B) == [] and [c["id"] for c in chat_store.list_chats(A)] == [c1["id"]])
u = chat_store.update_chat(A, c1["id"], title="  새  제목 ", kept=True)
ck("chat_store: 제목·보관 수정", u["title"] == "새 제목" and u["kept"] is True)
try:
    chat_store.update_chat(A, c1["id"], title="  "); ck("chat_store: 빈 제목 거부", False)
except ValueError:
    ck("chat_store: 빈 제목 거부", True)
c2 = chat_store.create_chat(A, "둘째")
for i in range(45):
    chat_store.add_message(A, c2["id"], "user" if i % 2 == 0 else "assistant", f"m{i}")
h = chat_store.history(A, c2["id"])
ck("chat_store: history 는 최근 40개, 순서 유지", len(h) == chat_store.HISTORY_LIMIT == 40 and h[0]["content"] == "m5" and h[-1]["content"] == "m44")
ck("chat_store: 목록은 최근 활동순", [c["id"] for c in chat_store.list_chats(A)] == [c2["id"], c1["id"]])
# 7일 정리: c2 의 updated 를 8일 전으로, c1(보관) 도 8일 전으로 → c2 만 지워진다
with chat_store._connect() as con:
    old = (_dt.datetime.now() - _dt.timedelta(days=8)).isoformat(sep=" ")
    con.execute("UPDATE chat SET updated = ?", (old,))
ck("chat_store: purge 는 보관 안 한 7일 지난 방만", chat_store.purge() == 1 and [c["id"] for c in chat_store.list_chats(A)] == [c1["id"]])
with chat_store._connect() as con:
    ck("chat_store: 방 삭제 시 메시지도 삭제 (cascade)", con.execute("SELECT COUNT(*) FROM message WHERE chat_id = ?", (c2["id"],)).fetchone()[0] == 0)
c3 = chat_store.create_chat(A)
with chat_store._connect() as con:
    con.execute("UPDATE chat SET updated = ? WHERE id = ?", ((_dt.datetime.now() - _dt.timedelta(days=6)).isoformat(sep=" "), c3["id"]))
ck("chat_store: 6일 된 방은 남는다", chat_store.purge() == 0)
chat_store.delete_chat(A, c3["id"])
# chat_in_room: 가짜 클라이언트로 (답 저장, 40개 제한, 실패 시 저장 없음)
sent.clear()
script[:] = [NS(stop_reason="end_turn", content=[NS(type="text", text="방 답변")], usage=usage())]
c4 = chat_store.create_chat(A)
for i in range(44):
    chat_store.add_message(A, c4["id"], "user" if i % 2 == 0 else "assistant", f"h{i}")
res2 = ai.chat_in_room(A, c4["id"], "질문입니다")
ck("chat_in_room: 답 저장 + message·chat 반환", res2["answer"] == "방 답변" and res2["message"]["role"] == "assistant" and res2["message"]["content"] == "방 답변" and res2["chat"]["count"] == 46)
ck("chat_in_room: 모델에는 최근 40개 + 질문", len(sent[0]["messages"]) == 41 and sent[0]["messages"][-1]["content"] == "질문입니다" and sent[0]["messages"][0]["content"] == "h4")
ck("chat_in_room: 질문·답이 마지막 두 메시지", [m["content"] for m in chat_store.messages(A, c4["id"])[-2:]] == ["질문입니다", "방 답변"])
def fail_create(**kw): raise ai.AIError("모델 실패")
ai._c = lambda: NS(beta=NS(messages=NS(create=fail_create)))
try:
    ai.chat_in_room(A, c4["id"], "실패 질문"); ck("chat_in_room: 실패는 AIError", False)
except ai.AIError:
    ck("chat_in_room: 실패는 AIError", True)
ck("chat_in_room: 실패하면 아무것도 저장 안 함", chat_store.get_chat(A, c4["id"])["count"] == 46)
try:
    ai.chat_in_room(A, c4["id"], "  "); ck("chat_in_room: 빈 질문 거부", False)
except ai.AIError:
    ck("chat_in_room: 빈 질문 거부", True)
os.environ["LEDGER_AI_FAKE"] = "1"
rf = ai.chat_in_room(A, c4["id"], "가짜로")
ck("chat_in_room: LEDGER_AI_FAKE 는 모델 없이 답", rf["answer"].startswith("(가짜 답변)") and ai.enabled() is True)
del os.environ["LEDGER_AI_FAKE"]

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
    env = dict(os.environ, LEDGER_XLSX=xlsx, LEDGER_ENV=os.path.join(QA_DIR, "qa.env"), LEDGER_DRIVE_MOCK="1", PYTHONIOENCODING="utf-8",
               LEDGER_CHAT_DB=os.path.join(d, "chats.sqlite"))
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
    # --- 채팅방 API: 사용자별 격리, 모델 실패 시 저장 없음, 알림 ---
    with Server("ai-chat", auth_bypass=False) as sv:
        ca, cb = sv.session_cookie(), sv.session_cookie(sv.OTHER_EMAIL)
        s, r = sv.call("POST", "/api/chats", {}, cookie=ca)
        ck("API chats: POST 새 방", s == 200 and r.get("id"), (s, r))
        cid = r["id"]
        s, r = sv.call("GET", "/api/chats", cookie=ca)
        ck("API chats: 목록에 내 방", s == 200 and [c["id"] for c in r] == [cid])
        s, r = sv.call("GET", "/api/chats", cookie=cb)
        ck("API chats: 다른 사용자 목록은 비어 있음", s == 200 and r == [])
        for m, p, b in (("GET", f"/api/chats/{cid}/messages", None), ("PATCH", f"/api/chats/{cid}", {"title": "x"}), ("DELETE", f"/api/chats/{cid}", None), ("POST", f"/api/chats/{cid}/messages", {"content": "q"})):
            s, r = sv.call(m, p, b, cookie=cb)
            ck(f"API chats: 다른 사용자 {m} {p.split('/')[-1]} → 404", s == 404, (s, r))
        s, r = sv.call("GET", "/api/chats", cookie=None)
        ck("API chats: 미로그인 401", s == 401)
        s, r = sv.call("POST", f"/api/chats/{cid}/messages", {"content": "키 없이"}, cookie=ca)
        ck("API chats: AI 키 없으면 502, 저장 없음", s == 502 and sv.call("GET", f"/api/chats/{cid}/messages", cookie=ca)[1] == [], (s, r))
        s, r = sv.call("POST", f"/api/chats/{cid}/notes", {"content": "[알림] 제안 p1 무시함"}, cookie=ca)
        ck("API chats: 알림 저장", s == 200 and r["note"] is True and r["role"] == "user")
        s, r = sv.call("PATCH", f"/api/chats/{cid}", {"title": "회의비 질문", "kept": True}, cookie=ca)
        ck("API chats: PATCH 제목·보관", s == 200 and r["title"] == "회의비 질문" and r["kept"] is True, (s, r))
        s, r = sv.call("PATCH", f"/api/chats/{cid}", {"title": " "}, cookie=ca)
        ck("API chats: 빈 제목 400", s == 400, (s, r))
        s, r = sv.call("DELETE", f"/api/chats/{cid}", cookie=ca)
        ck("API chats: DELETE", s == 200 and sv.call("GET", "/api/chats", cookie=ca)[1] == [])
        s, r = sv.call("POST", "/api/ai/chat", {"messages": []}, cookie=ca)
        ck("API chats: 옛 /api/ai/chat 없음", s in (404, 405), s)


if __name__ == "__main__":
    sys.exit(main())
