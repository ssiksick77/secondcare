from ui import *
X = "2026-QA05-001"
with sync_playwright() as p:
    br = p.chromium.launch()
    ca = br.new_context(viewport={"width": 1500, "height": 950}); cb = br.new_context(viewport={"width": 1500, "height": 950})
    A = ca.new_page(); Bp = cb.new_page()
    for pg in (A, Bp): pg.goto(B + "/"); pg.wait_for_load_state("networkidle"); tab_exec(pg)
    orig = exec_by_no(X)[0]; print("orig", orig["적요"], orig["금액"])
    find_row(A, X).dblclick(); A.wait_for_selector("#dlg[open]"); print("A dialog:", A.locator("#dlg-title").inner_text())
    find_row(Bp, X).dblclick(); Bp.wait_for_selector("#dlg[open]")
    F(Bp, "적요").fill("C08 B가 먼저 수정"); Bp.click("#dlg-save"); Bp.wait_for_timeout(1000); confirm_ok(Bp)
    print("B toasts:", toasts(Bp), "B dlg open:", Bp.locator("#dlg[open]").count())
    print("after B api:", exec_by_no(X)[0]["적요"], exec_by_no(X)[0]["금액"])
    F(A, "금액").fill("99,999"); A.click("#dlg-save"); A.wait_for_timeout(1000); c = confirm_ok(A)
    print("A confirm:", c); print("A form error:", err(A)); print("A toasts:", toasts(A)); print("A dlg open:", A.locator("#dlg[open]").count(), "A 금액 field kept:", F(A, "금액").input_value() if A.locator("#dlg[open]").count() else None)
    shot(A, "C-08_A_update_conflict")
    print("after A update api:", exec_by_no(X)[0]["적요"], exec_by_no(X)[0]["금액"])
    # close A dialog without reload
    A.evaluate("document.querySelector('#dlg').dataset.initial='';document.querySelector('#dlg').close()")
    print("A DATA 적요 (stale?):", A.evaluate(f"DATA.exec.find(r=>r['거래번호']=='{X}')['적요']"))
    A.click("#btn-del-mode"); A.wait_for_timeout(300)
    row = find_row(A, X); row.locator("input[data-selrow]").check(); A.click("#exec-del-run"); A.wait_for_timeout(500); c = confirm_ok(A); A.wait_for_timeout(800)
    print("A delete confirm body:", c); print("A toasts:", toasts(A)); shot(A, "C-08_A_delete_conflict")
    print("after A delete api exists:", len(exec_by_no(X)), exec_by_no(X)[0]["적요"] if exec_by_no(X) else None)
    br.close()
# API-level
cur = exec_by_no(X)[0]
stale = dict(cur, 적요="stale값")
r = put(f"/api/exec/{cur['_row']}", {"rec": {"금액": 1}, "expect": {"거래번호": X, "_snapshot": dict(cur, 적요="옛값")}}); print("API PUT stale snapshot:", show(r))
r = put(f"/api/exec/{cur['_row']}", {"rec": {"금액": 1}, "expect": {"거래번호": "2026-QA05-999"}}); print("API PUT wrong ident:", show(r))
r = delete(f"/api/exec/{cur['_row']}", {"expect": {"거래번호": X, "_snapshot": dict(cur, 금액=123)}}); print("API DELETE stale snapshot:", show(r))
r = delete(f"/api/exec/{cur['_row']}", {"expect": {"거래번호": "2026-QA05-002"}}); print("API DELETE wrong ident:", show(r))
print("still exists:", exec_by_no(X)[0]["적요"], exec_by_no(X)[0]["금액"])
