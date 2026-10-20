from h import *
import openpyxl, shutil, time, hashlib
BK = QA / "app" / "backup"
def bks(): return sorted(BK.glob("ledger_common_*.xlsx"), key=lambda p: p.stat().st_mtime)
X = "2026-QA01-002"
d0 = all_(); x = [r for r in d0["exec"] if r["거래번호"] == X][0]
tot0 = (len(d0["exec"]), sum(r["금액"] for r in d0["exec"]))
print("before:", x["금액"], x["적요"], "totals", tot0, "| backups:", len(bks()))
h_before = hashlib.md5(LEDGER.read_bytes()).hexdigest()
time.sleep(1.1)
r = put(f"/api/exec/{x['_row']}", {"rec": dict({k: v for k, v in x.items() if not k.startswith('_')}, 금액=999999, 적요="C13 변경"), "expect": expect(x)}); print("change:", r.status_code)
d1 = all_(); tot1 = (len(d1["exec"]), sum(r["금액"] for r in d1["exec"])); print("after change totals", tot1)
newest = bks()[-1]; print("newest backup:", newest.name, "| backup count:", len(bks()), "| md5 equals pre-change file:", hashlib.md5(newest.read_bytes()).hexdigest() == h_before)
wb = openpyxl.load_workbook(newest); ws = wb["집행내역"]; hd = {c.value: c.column for c in ws[1]}
print("backup row value:", ws.cell(x["_row"], hd["금액"]).value, ws.cell(x["_row"], hd["적요"]).value)
stop()
shutil.copy2(newest, LEDGER)
launch(False)
d2 = all_(); y = [r for r in d2["exec"] if r["거래번호"] == X][0]; tot2 = (len(d2["exec"]), sum(r["금액"] for r in d2["exec"]))
print("after restore:", y["금액"], y["적요"], "totals", tot2, "match pre-change:", tot2 == tot0 and y["금액"] == x["금액"])
print("backup naming sample:", [p.name for p in bks()[-3:]])
