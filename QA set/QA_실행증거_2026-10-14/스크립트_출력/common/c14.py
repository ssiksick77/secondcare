from ui import *
KEYS = ["원인발생일", "재원", "예산목", "거래처", "금액", "적요", "세목", "세세목", "태그", "결제수단", "사용자", "관리번호", "비고"]
def vals(pg): return {k: F(pg, k).input_value() for k in KEYS}
with sync_playwright() as p:
    b, c, pg = open_page(p); tab_exec(pg); open_add(pg)
    v1 = {"원인발생일": "2026-10-01", "재원": "QA10", "예산목": "연구재료비", "거래처": "C14거래처A", "금액": "21,000", "적요": "C14 첫건", "세목": "시약", "세세목": "세세A", "태그": "가상태그1", "결제수단": "연구비카드", "사용자": "Alex", "관리번호": "M-001", "비고": "비고A"}
    for k, v in v1.items():
        el = F(pg, k)
        if el.evaluate("e=>e.tagName") == "SELECT": el.select_option(v)
        else: el.fill(v)
    pg.click("#dlg-save-more"); pg.wait_for_timeout(1500); print("confirm:", confirm_ok(pg))
    pg.wait_for_timeout(500)
    print("dialog open after save-more:", pg.locator("#dlg[open]").count(), "title:", pg.locator("#dlg-title").inner_text(), "focus:", focused(pg))
    after = vals(pg); print("second form values:", after)
    print("kept:", [k for k in KEYS if after[k] == v1[k]]); print("cleared:", [k for k in KEYS if after[k] == ""])
    shot(pg, "C-14_second_form")
    F(pg, "거래처").fill("C14거래처B"); F(pg, "금액").fill("22,000"); F(pg, "적요").fill("C14 둘째건")
    pg.keyboard.press("Control+Enter"); pg.wait_for_timeout(1500); confirm_ok(pg)
    print("after 2nd save dialog open:", pg.locator("#dlg[open]").count(), "toasts:", toasts(pg))
    # Alex: filter QA05, then 집행 추가 -> 재원?
    pg.select_option('[data-filter="재원"][data-kind="exec"]', "QA05"); pg.wait_for_timeout(300); open_add(pg)
    print("new form with filter QA05 -> 재원:", F(pg, "재원").input_value(), "예산목:", F(pg, "예산목").input_value(), "사용자:", F(pg, "사용자").input_value(), "날짜:", F(pg, "원인발생일").input_value())
    shot(pg, "C-14_new_form_after_filter_QA05")
    b.close()
for r in all_()["exec"]:
    if r["적요"].startswith("C14"): print({k: r[k] for k in ["거래번호"] + KEYS})
