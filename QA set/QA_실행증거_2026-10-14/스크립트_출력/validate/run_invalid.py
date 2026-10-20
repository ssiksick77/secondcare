import json, sys, requests, time
sys.path.insert(0, "C:/Users/parkj/AppData/Local/Temp/claude/c--Users-parkj-Desktop-Project-01-in-progress/18367f8b-184a-424d-99ad-8ce7d7ee1121/scratchpad/qa/work")
from harness_common import *
cases = json.load(open(ORIG/"invalid_cases_NOT_SUBMITTED.json", encoding="utf-8"))
results = []
for c in cases:
    h0, c0, _ = snap()
    t = time.time()
    r = requests.request(c["method"], BASE + c["path"], json=c["body"], timeout=60)
    dt = time.time() - t
    try: detail = r.json()
    except Exception: detail = r.text[:500]
    h1, c1, _ = snap()
    saved = (h1 != h0)
    diff = {k: c1[k]-c0[k] for k in c1 if c1[k]!=c0[k]}
    rec = dict(id=c["scenario_id"], method=c["method"], path=c["path"], status=r.status_code, detail=detail if isinstance(detail,str) else json.dumps(detail, ensure_ascii=False)[:800], ledger_changed=saved, count_diff=diff, elapsed=round(dt,2), issue=c["intentional_issue"], expected=c["expected"])
    if saved:
        rec["reset_note"] = reset()
    results.append(rec)
    print(rec["id"], rec["status"], "changed" if saved else "unchanged", diff, str(rec["detail"])[:160], flush=True)
json.dump(results, open(QA/"work"/"invalid_results.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
