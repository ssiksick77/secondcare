import json, sys, requests, os, pathlib
sys.path.insert(0, "<home>/AppData/Local/Temp/claude/<session>/18367f8b-184a-424d-99ad-8ce7d7ee1121/scratchpad/qa/work")
from harness_common import *
F = pathlib.Path(QA/"work"/"files")
out = {}
def show(tag, r):
    try: body = r.json()
    except Exception: body = r.text[:400]
    out[tag] = {"status": r.status_code, "body": body}
    print(tag, r.status_code, json.dumps(body, ensure_ascii=False)[:600], flush=True)
    return body
def ev(num): return requests.get(f"{BASE}/api/evidence/{num}").json()
show("ev_before_QA01-001", requests.get(f"{BASE}/api/evidence/2026-QA01-001"))
# 1) file upload to F01 exec 2026-QA01-001
with open(F/"qa_receipt_1x1.png","rb") as fh:
    r = requests.post(f"{BASE}/api/evidence/2026-QA01-001", files=[("files", ("qa_receipt_1x1.png", fh, "image/png"))], data={"kind":"영수증","note":"QA validate B-18 upload"}, timeout=60)
b1 = show("upload_QA01-001_png", r)
show("ev_after_QA01-001", requests.get(f"{BASE}/api/evidence/2026-QA01-001"))
show("ev_QA02-001 (other fund, should be empty)", requests.get(f"{BASE}/api/evidence/2026-QA02-001"))
d = requests.get(BASE+"/api/all").json()
out["all_evidence_rows"] = d["evidence"]
print("all evidence rows:", json.dumps(d["evidence"], ensure_ascii=False)[:800])
# 2) 실물만 entry
show("entry_QA01-002", requests.post(f"{BASE}/api/evidence/2026-QA01-002/entry", json={"증빙종류":"영수증","비고":"QA B-18 실물만"}))
ent = requests.get(f"{BASE}/api/evidence/2026-QA01-002").json()
out["ev_QA01-002_after_entry"] = ent
print("after entry:", json.dumps(ent, ensure_ascii=False)[:700])
row = ent["items"][0]["_row"] if ent.get("items") else None
# 3) attach file to entry row
with open(F/"qa_receipt.pdf","rb") as fh:
    r = requests.post(f"{BASE}/api/evidence/2026-QA01-002", files=[("files", ("qa_receipt.pdf", fh, "application/pdf"))], data={"kind":"영수증","row":str(row)}, timeout=60)
show("attach_to_entry_row", r)
# 4) duplicate attach 409 expected
with open(F/"qa_receipt.pdf","rb") as fh:
    r = requests.post(f"{BASE}/api/evidence/2026-QA01-002", files=[("files", ("qa_receipt_dup.pdf", fh, "application/pdf"))], data={"kind":"영수증","row":str(row)}, timeout=60)
show("attach_dup_same_row (expect 409)", r)
ent2 = requests.get(f"{BASE}/api/evidence/2026-QA01-002").json()
out["ev_QA01-002_after_attach"] = ent2
print("after attach:", json.dumps(ent2, ensure_ascii=False)[:700])
# 5) delete the file-bearing evidence row for QA01-001
ev1 = requests.get(f"{BASE}/api/evidence/2026-QA01-001").json()
out["ev_QA01-001_rows"] = ev1
row1 = ev1["items"][0]["_row"] if ev1.get("items") else None
r = requests.delete(f"{BASE}/api/evidence/{row1}", json={}, timeout=60)
show("delete_evidence_row_QA01-001", r)
print("after delete QA01-001:", requests.get(f"{BASE}/api/evidence/2026-QA01-001").text[:300])
json.dump(out, open(QA/"work"/"b18_results.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
