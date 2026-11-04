import json, sys, requests, io, time
sys.path.insert(0, "<home>/AppData/Local/Temp/claude/<session>/18367f8b-184a-424d-99ad-8ce7d7ee1121/scratchpad/qa/work")
from harness_common import *
MB = 1024*1024
out = []
def ratt(num): return requests.get(f"{BASE}/api/ratt/{num}").json()["items"]
def up(num, parts, note="QA B-19"):
    files = [("files", (fn, io.BytesIO(data), "application/octet-stream")) for fn, data in parts]
    r = requests.post(f"{BASE}/api/ratt/{num}", files=files, data={"note": note}, timeout=600)
    try: body = r.json()
    except Exception: body = r.text[:300]
    return r.status_code, body
def rec(tag, num, parts, expect_code):
    before = ratt(num)
    t=time.time(); code, body = up(num, parts)
    after = ratt(num)
    detail = body.get("detail") if isinstance(body, dict) and "detail" in body else (f"items={len(body.get('items',[]))}" if isinstance(body, dict) and "items" in body else str(body)[:200])
    row = dict(tag=tag, request=num, files=len(parts), total_bytes=sum(len(d) for _,d in parts), status=code, expected=expect_code, match=(code==expect_code),
               count_before=len(before), count_after=len(after), bytes_before=sum(int(a.get('크기') or 0) for a in before), bytes_after=sum(int(a.get('크기') or 0) for a in after), detail=str(detail)[:400], secs=round(time.time()-t,1))
    out.append(row); print(json.dumps(row, ensure_ascii=False), flush=True)
    return row
print("reset:", reset())
N="R-2026-011"  # 신청 상태, 장비
big25 = b"\0"*(25*MB)
# (a) 25MB exact single file
rec("a: 25MB exact (25*1024*1024) single", N, [("qa_25mb_exact.bin", big25)], 200)
# (b) 25MB+1 single file
rec("b: 25MB+1 byte single", N, [("qa_25mb_plus1.bin", b"\0"*(25*MB+1))], 413)
# (c) fill to 20 files then 21st
small = b"\0"*1024
rec("c1: 19 small files (total 20 with 25MB exact)", N, [(f"qa_small_{i:02d}.bin", small) for i in range(19)], 200)
rec("c2: 21st file (count limit)", N, [("qa_small_21st.bin", small)], 413)
# multi-file request exceeding count in one shot on another request
reset()
rec("c3: 21 files in one request on fresh request", N, [(f"qa_many_{i:02d}.bin", small) for i in range(21)], 413)
# (d) 100MB boundary on R-2026-010 (fresh)
N2="R-2026-010"
rec("d1: 4 x 25MB = 100MB exact in one request", N2, [(f"qa_100_{i}.bin", big25) for i in range(4)], 200)
rec("d2: +1 byte single file over 100MB total", N2, [("qa_plus1.bin", b"\0")], 413)
reset()
rec("d3: 5 x 21MB = 105MB one request (fresh)", N2, [(f"qa_105_{i}.bin", b"\0"*(21*MB)) for i in range(5)], 413)
rec("d4: 25MB+1 among multi files (pre-read size check) fresh", N2, [("ok.bin", small), ("over.bin", b"\0"*(25*MB+1))], 413)
json.dump(out, open(QA/"work"/"b19_results.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("done")
