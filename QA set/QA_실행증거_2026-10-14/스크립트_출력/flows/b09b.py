from pw import *
from h import *
def vb(pg,row):
    pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    pg.click(f'tr[data-kind="exec"][data-row="{row}"] td[data-col="재원"]'); pg.wait_for_timeout(700)
    v=pg.locator('#exec-drawer button[data-act="voucher"]')
    return (v.count(), v.is_disabled() if v.count() else None, v.get_attribute('title') if v.count() else '')
def f(pg):
    print('row3 (청구, E002) voucher btn:',vb(pg,3))
    pg.screenshot(path=S+'flows_B09_6_voucher_off_claimed.png')
    print('row2 (승인) voucher btn:',vb(pg,2))
    pg.screenshot(path=S+'flows_B09_7_drawer_approved.png')
    print(pg.locator('#exec-drawer').inner_text()[:700].replace('\n',' | '))
    # 앞 단계 취소 시도: 청구일 지우기 (승인 있는 상태)
    print(pg.locator('#exec-drawer .xd-step').all_inner_texts())
run(f)
