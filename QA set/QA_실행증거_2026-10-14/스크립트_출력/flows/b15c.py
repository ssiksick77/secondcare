from pw2 import *
from h import *
# server-side mixed
a=all_()['request']; m={r['신청번호']:r for r in a}
print('API mixed:',api('POST','/api/order/create',{'rows':[m['R-2026-018']['_row'],m['R-2026-020']['_row']],'extra':{'적립금사용':'N'}}))
def f(pg):
    pg.get_by_role('tab',name='소모품').first.click(); pg.wait_for_timeout(600)
    for no in ('R-2026-018','R-2026-019'):
        pg.locator(f'tr:has-text("{no}") input[type=checkbox]').check()
    pg.click('#rq-order-btn'); pg.wait_for_timeout(800)
    cb=pg.locator('dialog[open] input[type=checkbox]'); print('checkboxes',cb.count(),[c.is_checked() for c in cb.all()])
    cb.first.uncheck()
    pg.screenshot(path=S+'flows_B15_3_order_nodeposit.png')
    pg.locator('dialog[open] button:has-text("주문 생성")').click(); pg.wait_for_timeout(1200)
    print('alerts',[x for x in pg.locator('[role=alert],[role=status],.toast').all_inner_texts() if x])
    a=all_(); print('orders',[(o['주문번호'],o['거래처'],o['주문금액'],o['결제금액'],o['적립금사용'],o['신청번호목록']) for o in a['order']])
    print([ (r['신청번호'],r['주문번호'],r['상태']) for r in a['request'] if r['신청번호'] in ('R-2026-018','R-2026-019','R-2026-020')])
    pg.screenshot(path=S+'flows_B15_4_after_order.png')
run(f)
