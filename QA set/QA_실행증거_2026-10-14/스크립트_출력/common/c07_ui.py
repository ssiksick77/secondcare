from ui import *
import hashlib
def cell(pg, ri, ci): return pg.locator(f'#edit-grid td[data-ri="{ri}"][data-ci="{ci}"]')
def edit_text(pg, ri, ci, v):
    cell(pg, ri, ci).dblclick(); inp = pg.locator("#edit-grid .cell-input"); 
    if inp.evaluate("e=>e.tagName") == "SELECT": inp.select_option(v); pg.keyboard.press("Tab")
    else: inp.fill(v); pg.keyboard.press("Tab")
    pg.wait_for_timeout(100)
with sync_playwright() as p:
    b, c, pg = open_page(p); tab_exec(pg)
    pg.select_option('[data-filter="재원"][data-kind="exec"]', "QA06"); pg.wait_for_timeout(300)
    pg.click("#btn-edit-mode"); pg.wait_for_selector("#dlg-edit[open]"); pg.wait_for_timeout(300)
    nrows = pg.locator("#edit-grid tbody tr").count(); print("grid rows", nrows)
    t0 = cell(pg, 0, 0).inner_text(); t1 = cell(pg, 1, 0).inner_text(); print("edit rows:", t0, t1)
    before = {r["거래번호"]: (r["적요"], r["금액"]) for r in all_()["exec"] if r["거래번호"] in (t0, t1)}; print("before", before)
    h0 = hashlib.md5(LEDGER.read_bytes()).hexdigest(); n0 = len(all_()["exec"])
    edit_text(pg, 0, 12, "C07UI 수정A"); edit_text(pg, 1, 12, "C07UI 수정B")
    last = nrows - 1
    edit_text(pg, last, 2, "2026-10-14"); edit_text(pg, last, 7, "연구재료비"); edit_text(pg, last, 12, "C07UI 신규"); edit_text(pg, last, 13, "0")
    print("count label:", pg.locator("#edit-count").inner_text())
    pg.click("#edit-save"); pg.wait_for_timeout(1200)
    errrows = pg.locator("#edit-grid tr.err"); print("err rows:", errrows.count(), [errrows.nth(i).get_attribute("title") for i in range(errrows.count())])
    if errrows.count(): print("err row bg:", errrows.first.evaluate("e=>getComputedStyle(e.querySelector('td.sel')||e).boxShadow + ' / ' + getComputedStyle(e).backgroundColor + ' / ' + getComputedStyle(e.cells[0]).borderLeft"))
    print("alert:", alert_text(pg))
    shot(pg, "C-07_editgrid_error")
    h1 = hashlib.md5(LEDGER.read_bytes()).hexdigest(); print("file unchanged:", h0 == h1, "count", n0, len(all_()["exec"]))
    # fix the bad row
    last = pg.locator("#edit-grid tbody tr").count() - 1
    # find new row index (the one with 'C07UI 신규')
    ri_new = None
    for i in range(pg.locator("#edit-grid tbody tr").count()):
        if cell(pg, i, 12).inner_text() == "C07UI 신규": ri_new = i
    edit_text(pg, ri_new, 13, "4,321")
    print("err rows after fix edit:", pg.locator("#edit-grid tr.err").count())
    pg.click("#edit-save"); pg.wait_for_timeout(1500)
    print("dialog open after save:", pg.locator("#dlg-edit[open]").count(), "alert:", alert_text(pg))
    shot(pg, "C-07_editgrid_saved")
    after = {r["거래번호"]: (r["적요"], r["금액"]) for r in all_()["exec"] if r["거래번호"] in (t0, t1) or r["적요"] == "C07UI 신규"}; print("after", after, "count", len(all_()["exec"]))
    b.close()
