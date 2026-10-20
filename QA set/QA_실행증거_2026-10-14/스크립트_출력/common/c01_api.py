from h import *
n0 = {k: len(v) for k, v in all_().items() if isinstance(v, list)}
print("== exec: omit each field")
for f in ["원인발생일", "재원", "예산목", "거래처", "금액", "적요"]:
    rec = dict(EXEC_OK); rec[f] = ""; r = post("/api/exec", rec); print(f, "->", show(r))
    if r.status_code == 200:
        # cleanup
        x = r.json(); delete(f"/api/exec/{x['_row']}", {"expect": {"거래번호": x["거래번호"]}})
print("all empty ->", show(post("/api/exec", {})))
print("== req")
REQ = {"원인발생일": "2026-10-14", "재원": "QA10", "예산목": "연구활동비", "금액": 5000, "상태": "대기"}
for f in REQ:
    rec = dict(REQ); rec[f] = ""; r = post("/api/req", rec); print(f, "->", show(r))
    if r.status_code == 200:
        x = r.json(); print("  created", x.get("품의번호")); delete(f"/api/req/{x['_row']}", {"expect": {"품의번호": x["품의번호"]}})
print("all empty ->", show(post("/api/req", {})))
print("== deposit")
DEP = {"일자": "2026-10-14", "거래처": "QA몰", "구분": "적립", "금액": 1000}
for f in DEP:
    rec = dict(DEP); rec[f] = ""; print(f, "->", show(post("/api/deposit", rec)))
print("all empty ->", show(post("/api/deposit", {})))
print("== budget")
BUD = {"재원": "QA10", "변경회차": "9"}
for f in BUD:
    rec = dict(BUD); rec[f] = ""; print(f, "->", show(post("/api/budget", rec)))
print("all empty ->", show(post("/api/budget", {})))
print("== funds", show(post("/api/funds", {"재원코드": "", "과제명": "x"})), show(post("/api/funds", {})))
print("== tags", show(post("/api/tags", {"태그명": "", "분류": "x"})), show(post("/api/tags", {})))
n1 = {k: len(v) for k, v in all_().items() if isinstance(v, list)}
print("counts before", n0); print("counts after ", n1)
