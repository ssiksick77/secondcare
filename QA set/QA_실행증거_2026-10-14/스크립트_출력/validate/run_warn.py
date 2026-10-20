import json, sys, requests, time
sys.path.insert(0, "C:/Users/parkj/AppData/Local/Temp/claude/c--Users-parkj-Desktop-Project-01-in-progress/18367f8b-184a-424d-99ad-8ce7d7ee1121/scratchpad/qa/work")
from harness_common import *
cases = json.load(open(ORIG/"warning_cases_NOT_SUBMITTED.json", encoding="utf-8"))
results = []
for c in cases:
    reset()
    h0, c0, d0 = snap()
    dash0 = json.dumps(d0.get("dashboard"), sort_keys=True, ensure_ascii=False)
    funds0 = [f.get("재원코드") for f in d0["funds"]]
    r = requests.post(BASE + c["path"], json=c["body"], timeout=60)
    try: detail = r.json()
    except Exception: detail = r.text[:500]
    h1, c1, d1 = snap()
    dash1 = json.dumps(d1.get("dashboard"), sort_keys=True, ensure_ascii=False)
    funds1 = [f.get("재원코드") for f in d1["funds"]]
    diff = {k: c1[k]-c0[k] for k in c1 if c1[k]!=c0[k]}
    rec = dict(id=c["scenario_id"], status=r.status_code, detail=json.dumps(detail, ensure_ascii=False)[:800], ledger_changed=(h1!=h0), count_diff=diff,
               dashboard_changed=(dash0!=dash1), funds_before=funds0, funds_after=funds1, funds_added=[x for x in funds1 if x not in funds0],
               exec_new_rows=[e for e in d1["exec"] if e.get("_row") not in [x.get("_row") for x in d0["exec"]]][:3],
               expected=c["expected"])
    if rec["dashboard_changed"]:
        rec["dash_before_funds_summary"] = None
    results.append(rec)
    print(rec["id"], rec["status"], rec["ledger_changed"], diff, "dash_changed=",rec["dashboard_changed"], "funds_added=",rec["funds_added"], rec["detail"][:200], flush=True)
    if rec["ledger_changed"]:
        rec["dash_after_sample"] = d1.get("dashboard")
        rec["dash_before_sample"] = d0.get("dashboard")
json.dump(results, open(QA/"work"/"warn_results.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
reset()
