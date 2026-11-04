from pw2 import *
from h import *
n0=len(all_()['request'])
def f(pg):
    pg.get_by_role('tab',name='소모품').first.click(); pg.wait_for_timeout(500)
    pg.get_by_role('button',name='신청 추가').click(); pg.wait_for_timeout(600)
    print('options',pg.locator('#f-구매처 option').all_inner_texts())
    pg.fill('#f-신청인','가상신청인1'); pg.fill('#f-품목','QA 드림디포건'); pg.fill('#f-단가','10000'); pg.fill('#f-상품코드','D-1')
    pg.select_option('#f-구매처',label='드림디포 (현재 이용 불가)')
    pg.screenshot(path=S+'flows_B15_5_dreamdepot_form.png')
    pg.click('#dlg-save'); pg.wait_for_timeout(1000)
    print('dlg-error:',pg.locator('#dlg-error').inner_text())
    pg.screenshot(path=S+'flows_B15_6_dreamdepot_err.png')
run(f)
print('count delta',len(all_()['request'])-n0)
