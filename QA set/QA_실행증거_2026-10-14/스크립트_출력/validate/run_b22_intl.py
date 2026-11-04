import sys, json, time, re, requests
sys.path.insert(0, "<home>/AppData/Local/Temp/claude/c--Users-parkj-Desktop-Project-01-in-progress/18367f8b-184a-424d-99ad-8ce7d7ee1121/scratchpad/qa/work")
from harness_common import *
from playwright.sync_api import sync_playwright
SHOTS = QA/"shots"
res = []
def req_rows(): return requests.get(BASE+"/api/all").json()["request"]
def digits(s): return int(re.sub(r"[^0-9]", "", s or "0") or 0)
def run_case(pg, tag, title, trip, fill, expect):
    pg.click('#request-tabs [data-rtype="학회"]')
    pg.click('#rpanel [data-add="request"]')
    pg.wait_for_selector("#dlg[open]")
    pg.select_option("#f-_국내외", trip["country"])
    pg.fill("#f-품목", title)
    pg.fill("#f-신청인", "가상담당자Alex")
    pg.click("#req-calc-btn")
    pg.wait_for_selector("#dlg-conf[open]")
    fill(pg)
    time.sleep(0.4)
    pg.screenshot(path=str(SHOTS/f"validate_B22_{tag}_calc.png"))
    blocked = pg.locator("#conf-form").get_attribute("data-blocked")
    pg.click("#conf-apply")
    time.sleep(0.8)
    amt_before_save = pg.input_value("#f-금액")
    ro = pg.get_attribute("#f-금액", "readonly")
    pg.screenshot(path=str(SHOTS/f"validate_B22_{tag}_applied.png"))
    pg.click("#dlg-save")
    time.sleep(1.5)
    rows = [r for r in req_rows() if r.get("품목") == title]
    row = rows[-1] if rows else {}
    saved_amt = row.get("금액")
    det = row.get("상세")
    try: det_out = json.loads(det).get("out", {}) if isinstance(det, str) else (det or {}).get("out", {})
    except Exception: det_out = {}
    r = dict(tag=tag, title=title, expected=expect, applied_in_form=amt_before_save, form_readonly=ro, saved_row=row.get("신청번호"), saved_금액=saved_amt,
             saved_detail_합계=det_out.get("합계"), detail_keys=list(row.keys())[:30], match_expected=(digits(amt_before_save)==expect and saved_amt==expect))
    res.append(r); print(json.dumps({k:v for k,v in r.items() if k!='detail_keys'}, ensure_ascii=False), flush=True)
    pg.screenshot(path=str(SHOTS/f"validate_B22_{tag}_after_save.png"))
    return r
print("reset", reset())  # 국내 케이스는 앞 실행에서 확인됨(R-2026-017); 이번에는 국외 2건만 재실행
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width":1400,"height":900})
    pg.goto(BASE + "/request")
    pg.wait_for_selector('#request-tabs [data-rtype="학회"]', state="attached", timeout=20000)
    time.sleep(1)
    try:
        # 국내 케이스
        def fill_dom(pg):  # (완료 후 생략 가능)
            pg.select_option("#cf-trip", "dom")
            pg.fill("#cf-cs", "2026-09-01"); pg.fill("#cf-ce", "2026-09-02")
            pg.select_option("#cf-region", "100000")
            pg.fill("#cf-fare", "100000"); pg.fill("#cf-lodge", "150000")
            pg.fill('#cf-legbody tr[data-leg="0"] .lg-at[data-end="dep"]', "2026-09-01T09:00")
            pg.fill('#cf-legbody tr[data-leg="0"] .lg-at[data-end="arr"]', "2026-09-01T11:00")
            pg.fill('#cf-legbody tr[data-leg="1"] .lg-at[data-end="dep"]', "2026-09-02T17:00")
            pg.fill('#cf-legbody tr[data-leg="1"] .lg-at[data-end="arr"]', "2026-09-02T19:00")
        pass
    except Exception as e:
        res.append({"tag":"dom","error":str(e)[:500]}); print("ERR dom", str(e)[:500])
    try:
        pg.goto(BASE + "/request"); pg.wait_for_selector('#request-tabs [data-rtype="학회"]', state="attached", timeout=20000); time.sleep(1)
        def fill_intl(ext):
            def f(pg):
                pg.select_option("#cf-trip", "intl")
                pg.select_option("#cf-grade", "1ra")
                pg.fill("#cf-fx", "1400")
                pg.fill("#cf-cs", "2026-09-01"); pg.fill("#cf-ce", "2026-09-05")
                pg.fill("#cf-city", "파리")
                pg.fill("#cf-fare", "2000000"); pg.fill("#cf-lodge", "1000000"); pg.fill("#cf-reg", "500000")
                if ext: pg.fill("#cf-ext", str(ext))
                pg.fill('#cf-legbody tr[data-leg="0"] .lg-at[data-end="dep"]', "2026-09-01T10:00")
                pg.fill('#cf-legbody tr[data-leg="0"] .lg-at[data-end="arr"]', "2026-09-01T15:00")
                pg.fill('#cf-legbody tr[data-leg="0"] .lg-place[data-end="arr"]', "파리")
                pg.fill('#cf-legbody tr[data-leg="1"] .lg-place[data-end="dep"]', "파리")
                pg.fill('#cf-legbody tr[data-leg="1"] .lg-at[data-end="dep"]', "2026-09-05T10:00")
                pg.fill('#cf-legbody tr[data-leg="1"] .lg-at[data-end="arr"]', "2026-09-05T21:00")
            return f
        run_case(pg, "intl_normal", "QA B-22 국외 정상", {"country":"국외"}, fill_intl(0), 4494000)
    except Exception as e:
        res.append({"tag":"intl_normal","error":str(e)[:500]}); print("ERR intl", str(e)[:500])
    try:
        pg.goto(BASE + "/request"); pg.wait_for_selector('#request-tabs [data-rtype="학회"]', state="attached", timeout=20000); time.sleep(1)
        run_case(pg, "intl_ext_exceed", "QA B-22 국외 지원금초과", {"country":"국외"}, fill_intl(5000000), 0)
    except Exception as e:
        res.append({"tag":"intl_ext_exceed","error":str(e)[:500]}); print("ERR ext", str(e)[:500])
    b.close()
json.dump(res, open(QA/"work"/"b22_results.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
