from ui import *
def fill_exec(pg, fund, amt, vendor, memo, item="연구활동비"):
    F(pg, "재원").select_option(fund); F(pg, "예산목").select_option(item)
    F(pg, "거래처").fill(vendor); F(pg, "금액").fill(amt); F(pg, "적요").fill(memo)
with sync_playwright() as p:
    b, c, pg = open_page(p); tab_exec(pg)
    for i, amt in enumerate(["150,000", "=12000*3+500", "=1/0", "abc", "1e3", "350만", "=2**10", "1.5"]):
        n0 = len(all_()["exec"])
        open_add(pg); fill_exec(pg, "QA10", amt, f"C02거래처{i}", f"C02 UI {amt}")
        F(pg, "적요").focus()  # blur 금액
        pg.wait_for_timeout(150)
        shown_after_blur = F(pg, "금액").input_value(); inv = F(pg, "금액").get_attribute("aria-invalid"); title = F(pg, "금액").get_attribute("title")
        pg.click("#dlg-save"); pg.wait_for_timeout(700)
        conf = None
        if pg.locator("#dlg-confirm[open]").count():
            conf = pg.locator("#confirm-body").inner_text(); pg.click("#confirm-ok"); pg.wait_for_timeout(700)
        e = err(pg); still = pg.locator("#dlg[open]").count()
        if amt in ("=1/0", "abc"): shot(pg, f"C-02_ui_{ 'div0' if amt=='=1/0' else 'abc'}")
        rows = [r for r in all_()["exec"] if r["적요"] == f"C02 UI {amt}"]
        print(f"{amt!r}: blur->{shown_after_blur!r} invalid={inv} title={title!r} | err={e!r} confirm={conf!r} dlgOpen={still} | saved={[ (r['거래번호'], r['금액']) for r in rows]} n {n0}->{len(all_()['exec'])}")
        if still:
            pg.evaluate("document.querySelector('#dlg').dataset.initial='';document.querySelector('#dlg').close()")
    b.close()
