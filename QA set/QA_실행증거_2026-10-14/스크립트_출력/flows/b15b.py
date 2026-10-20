from pw2 import *
from h import *
def f(pg):
    pg.get_by_role('tab',name='소모품').first.click(); pg.wait_for_timeout(600)
    for no in ('R-2026-018','R-2026-019','R-2026-020'):
        pg.locator(f'tr:has-text("{no}") input[type=checkbox]').check()
    pg.click('button[data-rq="approve"]'); pg.wait_for_timeout(1000)
    print([ (r['신청번호'],r['상태']) for r in all_()['request'] if r['신청번호'] in ('R-2026-018','R-2026-019','R-2026-020')])
    pg.click('button[data-rq="clear"]') if pg.locator('button[data-rq="clear"]').is_enabled() else None
    pg.wait_for_timeout(300)
    for no in ('R-2026-018','R-2026-020'):
        pg.locator(f'tr:has-text("{no}") input[type=checkbox]').check()
    pg.wait_for_timeout(300)
    ob=pg.locator('#rq-order-btn'); print('mixed: order btn visible',ob.is_visible(),'enabled',ob.is_enabled(),'why:',pg.locator('#req-sel-why').inner_text())
    pg.screenshot(path=S+'flows_B15_1_mixed_blocked.png')
    pg.locator('tr:has-text("R-2026-020") input[type=checkbox]').uncheck()
    pg.locator('tr:has-text("R-2026-019") input[type=checkbox]').check(); pg.wait_for_timeout(300)
    print('same vendor: enabled', ob.is_enabled(), pg.locator('#req-sel-n').inner_text())
    ob.click(); pg.wait_for_timeout(800)
    pg.screenshot(path=S+'flows_B15_2_order_dialog.png')
    print(pg.locator('dialog[open]').last.inner_text().replace('\n',' | ')[:900])
run(f)
