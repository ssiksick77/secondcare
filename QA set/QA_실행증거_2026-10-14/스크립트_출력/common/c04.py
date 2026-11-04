from h import *
import openpyxl
vals = ["=1+1", "+ABC", "@ABC", "-ABC", "=HYPERLINK(\"http://x\",\"y\")", "-1", "=SUM(A1:A2)"]
made = []
for v in vals:
    r = post("/api/exec", dict(EXEC_OK, 재원="QA09", 적요=v, 거래처=v, 세목=v)); print("exec", repr(v), r.status_code, r.json().get("거래번호"), repr(r.json().get("적요")))
    made.append(("exec", r.json()))
    r = post("/api/request", {"구분": "장비", "신청인": "QA", "품목": v, "규격": v, "사유": v, "단가": 100, "수량": 1})
    print("request", repr(v), r.status_code, r.json().get("신청번호"), repr(r.json().get("품목")))
    made.append(("request", r.json()))
d = all_()
ex = {r["거래번호"]: r for r in d["exec"]}; rq = {r["신청번호"]: r for r in d["request"]}
wb = openpyxl.load_workbook(LEDGER)
wse = wb["집행내역"]; wsr = wb["신청"]
he = {c.value: c.column for c in wse[1]}; hr = {c.value: c.column for c in wsr[1]}
print("--- readback and cells")
for kind, j in made:
    if kind == "exec":
        a = ex[j["거래번호"]]; row = a["_row"]
        for col in ["적요", "거래처", "세목"]:
            c = wse.cell(row, he[col]); print(kind, j["거래번호"], col, "api=", repr(a[col]), "cell=", repr(c.value), "type=", c.data_type, "quotePrefix=", c.quotePrefix)
    else:
        a = rq[j["신청번호"]]; row = a["_row"]
        for col in ["품목", "규격", "사유"]:
            c = wsr.cell(row, hr[col]); print(kind, j["신청번호"], col, "api=", repr(a[col]), "cell=", repr(c.value), "type=", c.data_type, "quotePrefix=", c.quotePrefix)
