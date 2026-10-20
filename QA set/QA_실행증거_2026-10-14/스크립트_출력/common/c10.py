from ui import *
import openpyxl, sys
def dash_cell(d, f, i):
    return [x for x in d["dashboard"]["table"] if x["재원"] == f and x["예산목"] == i][0]
d0 = all_(); print("before: QA03 연구개발부담비 집행액", dash_cell(d0, "QA03", "연구개발부담비")["집행액"], "| exec row:", [ (r["거래번호"], r["금액"]) for r in d0["exec"] if r["_row"] == 38])
stop()
wb = openpyxl.load_workbook(LEDGER); ws = wb["집행내역"]; hd = {c.value: c.column for c in ws[1]}
cell = ws.cell(38, hd["금액"]); print("cell before:", cell.coordinate, cell.value); cell.value = "=1000*2"; wb.save(LEDGER)
wb2 = openpyxl.load_workbook(LEDGER); c2 = wb2["집행내역"].cell(38, hd["금액"]); print("cell after:", c2.value, c2.data_type)
launch(False)
d1 = all_(); m = d1["meta"]
print("meta formula_count:", m["formula_count"], m["formula_cells"])
print("exec row 38:", [(r["거래번호"], r["금액"]) for r in d1["exec"] if r["_row"] == 38])
print("dash QA03 연구개발부담비 집행액:", dash_cell(d1, "QA03", "연구개발부담비")["집행액"])
with sync_playwright() as p:
    b, c, pg = open_page(p)
    print("header status (dash):", pg.locator("#file-status").inner_text())
    bn = pg.locator(".alert.formula"); print("banner on dash visible:", bn.count() and bn.first.is_visible(), bn.first.inner_text() if bn.count() and bn.first.is_visible() else "")
    shot(pg, "C-10_dash_formula")
    tab_exec(pg); pg.wait_for_timeout(300)
    bn = pg.locator(".alert.formula"); print("banner on exec visible:", bn.count() and bn.first.is_visible(), "|", bn.first.inner_text() if bn.count() else "")
    row = find_row(pg, "2026-QA03-001"); print("row display:", row.inner_text().replace("\n", " | ").replace("\t", " "))
    print("row has formula marker?:", row.evaluate("e=>e.className + ' ' + (e.title||'')"))
    pg.fill('[data-filter="q"][data-kind="exec"]', ""); pg.wait_for_timeout(300)
    shot(pg, "C-10_exec_formula")
    b.close()
