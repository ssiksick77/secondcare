from ui import *
import openpyxl
# unrelated save: formula preserved?
x = exec_by_no("2026-QA03-002")[0]
r = put(f"/api/exec/{x['_row']}", {"rec": dict({k: v for k, v in x.items() if not k.startswith('_')}, 비고="C10 다른행 저장"), "expect": expect(x)}); print("other row save:", r.status_code)
wb = openpyxl.load_workbook(LEDGER); print("N38 after other save:", wb["집행내역"]["N38"].value, "| meta count:", all_()["meta"]["formula_count"])
# UI: open formula row edit form, change 적요 only, save
with sync_playwright() as p:
    b, c, pg = open_page(p); tab_exec(pg)
    find_row(pg, "2026-QA03-001").dblclick(); pg.wait_for_selector("#dlg[open]")
    print("form 금액 shows:", F(pg, "금액").input_value())
    F(pg, "적요").fill("C10 수식행 적요 수정"); pg.click("#dlg-save"); pg.wait_for_timeout(1000); print("confirm:", confirm_ok(pg))
    print("form err:", err(pg), "toasts:", toasts(pg)); shot(pg, "C-10_save_formula_row")
    b.close()
wb = openpyxl.load_workbook(LEDGER); print("N38 after UI save attempt:", wb["집행내역"]["N38"].value, "| exec:", [(r["금액"], r["적요"]) for r in exec_by_no("2026-QA03-001")])
