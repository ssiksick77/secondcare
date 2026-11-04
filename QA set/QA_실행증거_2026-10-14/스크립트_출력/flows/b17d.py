from pw2 import *
from h import *
def f(pg):
    pg.get_by_role('tab',name='소모품').first.click(); pg.wait_for_timeout(500)
    pg.locator('tr:has-text("R-2026-021") input[type=checkbox]').check(); pg.wait_for_timeout(300)
    cv=pg.locator('button[data-rq="convert"]'); print('partial: convert enabled',cv.is_enabled(),'why:',pg.locator('#req-sel-why').inner_text())
    pg.screenshot(path=S+'flows_B17_1_partial.png')
    if False:
        cv.click(); pg.wait_for_timeout(800); print('dialog:',pg.locator('dialog[open]').last.inner_text()[:300].replace('\n',' | '))
        pg.screenshot(path=S+'flows_B17_1b_partial_dialog.png')
        pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
        pg.reload(); pg.wait_for_timeout(1200); pg.get_by_role('button',name='신청',exact=True).click(); pg.wait_for_timeout(800); pg.get_by_role('tab',name='소모품').first.click(); pg.wait_for_timeout(500)
        pg.locator('tr:has-text("R-2026-021") input[type=checkbox]').check()
    pg.locator('tr:has-text("R-2026-022") input[type=checkbox]').check(); pg.wait_for_timeout(300)
    cv.click(); pg.wait_for_timeout(800)
    pg.screenshot(path=S+'flows_B17_2_convert_form.png')
    for k in ['재원','예산목','거래처','적요','금액','품의자','비고']:
        el=pg.locator(f'#f-{k}'); print(k, el.input_value() if el.count() else None)
    print('dlg-title',pg.locator('#dlg-title').inner_text(), '| err', pg.locator('#dlg-error').inner_text())
    pg.select_option('#f-예산목','연구재료비'); 
    pg.click('#dlg-save'); pg.wait_for_timeout(1200)
    print('err',pg.locator('#dlg-error').inner_text(), [x for x in pg.locator('[role=alert],[role=status],.toast').all_inner_texts() if x])
    a=all_(); print([ (r['품의번호'],r['금액'],r['거래처'],r['비고'],r['상태']) for r in a['req'] if '021' in (r['비고'] or '')])
    print([ (r['신청번호'],r['상태'],r['연결품의번호']) for r in a['request'] if r['주문번호']=='알파-20261014-02'])
run(f)
