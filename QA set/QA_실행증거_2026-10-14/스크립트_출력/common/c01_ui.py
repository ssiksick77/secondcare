from ui import *
FORMS = {
 "exec": ("#tab-exec", {"원인발생일": "2026-10-14", "재원": "QA10", "예산목": "연구활동비", "금액": "10000"}),
 "req": ("#tab-req", {"원인발생일": "2026-10-14", "재원": "QA10", "예산목": "연구활동비", "금액": "10000", "상태": "대기"}),
 "deposit": ("#tab-deposit", {"일자": "2026-10-14", "거래처": "QA몰", "구분": "적립", "금액": "1000"}),
 "budget": ("#tab-budget", {"재원": "QA10", "변경회차": "당초"}),
 "funds": ("#tab-funds", {"재원코드": "QAZZ"}),
 "tags": ("#tab-tags", {"태그명": "QA태그Z"}),
}
def setv(pg, k, v):
    el = F(pg, k); tag = el.evaluate("e=>e.tagName")
    if tag == "SELECT": el.select_option(v if v else "")
    else: el.fill(v)
with sync_playwright() as p:
    b, c, pg = open_page(p)
    for kind, (tab, vals) in FORMS.items():
        pg.click(tab); pg.wait_for_timeout(300)
        n0 = len(all_()[kind])
        reqmarks = pg.evaluate("()=>0")
        for miss in list(vals) + ["__ALL__"]:
            open_add(pg, kind)
            if kind == "exec" and miss == list(vals)[0]:
                marks = pg.locator("#dlg-fields .lab").all_inner_texts()
                print(kind, "starred:", [m for m in marks if "*" in m])
            elif miss == list(vals)[0]:
                print(kind, "starred:", [m for m in pg.locator("#dlg-fields .lab").all_inner_texts() if "*" in m])
            for k, v in vals.items():
                if miss == "__ALL__" or k == miss: setv(pg, k, "")
                else: setv(pg, k, v)
            pg.click("#dlg-save"); pg.wait_for_timeout(400)
            print(f"  {kind} missing={miss}: error={err(pg)!r} focus={focused(pg)} open={pg.locator('#dlg[open]').count()}")
            if miss == "__ALL__": shot(pg, f"C-01_{kind}_all_empty")
            # close
            pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
            if pg.locator("#dlg-confirm[open]").count(): pg.click("#confirm-ok"); pg.wait_for_timeout(200)
            if pg.locator("#dlg[open]").count(): pg.evaluate("document.querySelector('#dlg').close()")
        print(f"  {kind} count before {n0} after {len(all_()[kind])}")
    b.close()
