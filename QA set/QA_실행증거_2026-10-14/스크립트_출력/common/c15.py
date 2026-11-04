from ui import *
with sync_playwright() as p:
    b, c, pg = open_page(p); tab_exec(pg)
    pg.evaluate("sessionStorage.clear()")
    open_add(pg); seq = [focused(pg)]
    # Walk from first field with Enter
    F(pg, "원인발생일").focus(); seq = ["원인발생일"]
    for i in range(6): pg.keyboard.press("Enter"); seq.append(focused(pg))
    print("Enter order from 원인발생일:", seq)
    open_focus = None
    pg.evaluate("document.querySelector('#dlg').dataset.initial='';document.querySelector('#dlg').close()")
    open_add(pg); print("initial focus:", focused(pg))
    pg.keyboard.type("C15거래처"); pg.keyboard.press("Enter"); print("after Enter on 거래처 ->", focused(pg))
    pg.keyboard.type("=1000*15"); pg.keyboard.press("Enter"); print("after Enter on 금액 ->", focused(pg), "금액 shown:", F(pg, "금액").input_value())
    pg.keyboard.type("C15 키보드 저장"); 
    # select 재원 / 예산목 by keyboard: shift+tab back
    F(pg, "재원").focus(); F(pg, "재원").select_option("QA10"); F(pg, "예산목").select_option("연구활동비"); F(pg, "적요").focus()
    n0 = len(all_()["exec"])
    pg.keyboard.press("Control+Enter"); pg.wait_for_timeout(1500); confirm_ok(pg)
    print("Ctrl+Enter: dialog open:", pg.locator("#dlg[open]").count(), "toasts:", toasts(pg), "exec +", len(all_()["exec"]) - n0)
    # Esc on dirty form
    open_add(pg); pg.keyboard.type("C15 버릴 입력"); pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
    print("Esc dirty -> confirm open:", pg.locator("#dlg-confirm[open]").count(), "title:", pg.locator("#confirm-title").inner_text() if pg.locator("#dlg-confirm[open]").count() else None, "body:", pg.locator("#confirm-body").inner_text() if pg.locator("#dlg-confirm[open]").count() else None)
    shot(pg, "C-15_esc_confirm")
    pg.click("#confirm-cancel"); pg.wait_for_timeout(300); print("계속 입력 -> form open:", pg.locator("#dlg[open]").count(), "거래처 kept:", F(pg, "거래처").input_value())
    pg.keyboard.press("Escape"); pg.wait_for_timeout(400); pg.click("#confirm-ok"); pg.wait_for_timeout(400); print("버리고 닫기 -> form open:", pg.locator("#dlg[open]").count())
    # Esc in confirm dialog itself (keyboard only)
    open_add(pg); pg.keyboard.type("C15 버릴2"); pg.keyboard.press("Escape"); pg.wait_for_timeout(400); pg.keyboard.press("Escape"); pg.wait_for_timeout(400)
    print("Esc twice -> form open:", pg.locator("#dlg[open]").count(), "confirm open:", pg.locator("#dlg-confirm[open]").count(), "focus:", focused(pg))
    if pg.locator("#dlg-confirm[open]").count(): pg.click("#confirm-ok")
    if pg.locator("#dlg[open]").count(): pg.keyboard.press("Escape"); pg.wait_for_timeout(300); pg.locator("#confirm-ok").click() if pg.locator("#dlg-confirm[open]").count() else None
    # Esc on clean form
    open_add(pg); pg.keyboard.press("Escape"); pg.wait_for_timeout(300); print("Esc clean -> form open:", pg.locator("#dlg[open]").count(), "confirm open:", pg.locator("#dlg-confirm[open]").count())
    # Ctrl+Shift+Enter
    open_add(pg); F(pg, "재원").select_option("QA10"); F(pg, "예산목").select_option("연구활동비"); F(pg, "거래처").fill("C15거래처2"); F(pg, "금액").fill("1,234"); F(pg, "금액").focus()
    pg.keyboard.press("Control+Shift+Enter"); pg.wait_for_timeout(1500); confirm_ok(pg)
    print("Ctrl+Shift+Enter: dialog open:", pg.locator("#dlg[open]").count(), "거래처:", F(pg, "거래처").input_value(), "재원:", F(pg, "재원").input_value())
    b.close()
print([ (r["거래번호"], r["금액"], r["거래처"], r["적요"]) for r in all_()["exec"] if "C15" in (r["거래처"] + r["적요"])])
