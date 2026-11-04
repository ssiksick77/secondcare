from h import *
import hashlib
d = all_(); q = [r for r in d["exec"] if r["재원"] == "QA07"][:2]
for r in q: print("before", r["거래번호"], r["금액"], r["적요"])
h0 = hashlib.md5(LEDGER.read_bytes()).hexdigest(); n0 = len(d["exec"])
ups = [{"row": q[0]["_row"], "rec": {"금액": q[0]["금액"] + 1, "적요": "C07 수정1"}, "expect": expect(q[0])},
       {"row": q[1]["_row"], "rec": {"금액": q[1]["금액"] + 2, "적요": "C07 수정2"}, "expect": expect(q[1])}]
bad_new = {"원인발생일": "2026-10-14", "재원": "QA07", "예산목": "없는예산목", "금액": 5000, "적요": "C07 신규"}
r = post("/api/exec/batch", {"creates": [bad_new], "updates": ups, "deletes": []}); print("1) bad new row:", show(r))
# also bad update (second) with good new
ups_bad = [ups[0], dict(ups[1], rec={"금액": "abc"})]
good_new = dict(bad_new, 예산목="연구재료비")
r2 = post("/api/exec/batch", {"creates": [good_new], "updates": ups_bad, "deletes": []}); print("2) bad update row:", show(r2))
d1 = all_(); h1 = hashlib.md5(LEDGER.read_bytes()).hexdigest()
for r in q: x = [y for y in d1["exec"] if y["거래번호"] == r["거래번호"]][0]; print("after fail", x["거래번호"], x["금액"], x["적요"])
print("file unchanged:", h0 == h1, "count", n0, len(d1["exec"]), "C07 신규 exists:", any(y["적요"] == "C07 신규" for y in d1["exec"]))
r3 = post("/api/exec/batch", {"creates": [good_new], "updates": ups, "deletes": []}); print("3) fixed:", show(r3))
d2 = all_()
for r in q: x = [y for y in d2["exec"] if y["거래번호"] == r["거래번호"]][0]; print("after ok", x["거래번호"], x["금액"], x["적요"])
print("new rows:", [(y["거래번호"], y["금액"]) for y in d2["exec"] if y["적요"] == "C07 신규"], "count", len(d2["exec"]))
# replay same batch (stale expect) -> should be rejected
r4 = post("/api/exec/batch", {"creates": [good_new], "updates": ups, "deletes": []}); print("4) replay stale:", show(r4))
print("count after replay", len(all_()["exec"]))
