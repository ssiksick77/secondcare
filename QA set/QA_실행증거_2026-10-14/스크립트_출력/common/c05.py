from ui import *
import sys
step = sys.argv[1]
if step == "save":
    with sync_playwright() as p:
        b, c, pg = open_page(p); tab_exec(pg); open_add(pg)
        F(pg, "원인발생일").fill("2026-09-30"); F(pg, "재원").select_option("QA08"); F(pg, "예산목").select_option("연구재료비")
        F(pg, "거래처").fill("C05거래처"); F(pg, "금액").fill("77,700"); F(pg, "적요").fill("C05 저장재조회 확인"); F(pg, "사용자").fill("Alex")
        pg.click("#dlg-save"); pg.wait_for_timeout(800)
        if pg.locator("#dlg-confirm[open]").count(): print("confirm:", pg.locator("#confirm-body").inner_text()); pg.click("#confirm-ok"); pg.wait_for_timeout(800)
        print("toast:", alert_text(pg)); shot(pg, "C-05_saved")
        pg.click("#tab-dash"); pg.wait_for_timeout(300)
        b.close()
    rows = [r for r in all_()["exec"] if r["적요"] == "C05 저장재조회 확인"]; print("api:", rows)
else:
    with sync_playwright() as p:
        b, c, pg = open_page(p); tab_exec(pg)
        no = sys.argv[2]
        pg.fill('[data-filter="q"][data-kind="exec"]', no); pg.wait_for_timeout(500)
        print("rows shown:", pg.locator("#exec-table tbody tr").count(), "|", pg.locator("#exec-table tbody tr").first.inner_text().replace("\n", " | "))
        shot(pg, "C-05_after_restart_search"); b.close()
    rows = [r for r in all_()["exec"] if r["거래번호"] == no]; print("api:", rows)
