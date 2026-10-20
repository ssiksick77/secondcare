from pw2 import *
from h import *
def bal(v): return sum((1 if d['구분']=='적립' else -1)*d['금액'] for d in all_()['deposit'] if d['거래처']==v)
def snap(tag):
    a=all_(); print(tag,'orders',[o['주문번호'] for o in a['order']],
      'dep A',[(d['_row'],d['구분'],d['금액'],d['적요']) for d in a['deposit'] if d['거래처']=='가상문구A'],'balA',bal('가상문구A'),
      'req',[(r['신청번호'],r['주문번호'],r['상태']) for r in a['request'] if r['신청번호'] in('R-2026-001','R-2026-002')])
snap('before')
def f(pg):
    pg.get_by_role('tab',name='소모품').first.click(); pg.wait_for_timeout(500)
    pg.locator('#rsub-order').click(); pg.wait_for_timeout(700)
    pg.screenshot(path=S+'flows_B16_1_order_view.png')
    # ORDER2 cancel attempt
    r2=pg.locator('tr:has-text("가상-20260703-02")'); print([b.inner_text() for b in r2.locator('button').all()])
    cb=r2.locator('button:has-text("주문 취소")')
    print('ORDER2 cancel btn count',cb.count(), 'disabled' if cb.count() and cb.first.is_disabled() else '')
    # try via API
    o2=[o for o in all_()['order'] if o['주문번호']=='가상-20260703-02'][0]
    print('API cancel ORDER2:',api('POST',f"/api/order/{o2['_row']}/action",{'action':'cancel'}))
    # ORDER1 cancel via UI
    r1=pg.locator('tr:has-text("가상-20260703-01")'); r1.locator('button:has-text("주문 취소")').click(); pg.wait_for_timeout(700)
    pg.screenshot(path=S+'flows_B16_2_cancel_confirm.png')
    print('confirm:',pg.locator('dialog[open]').last.inner_text().replace('\n',' | '))
    pg.locator('dialog[open] button:has-text("주문 취소")').last.click(); pg.wait_for_timeout(1000)
    print('alerts',[x for x in pg.locator('[role=alert],[role=status],.toast').all_inner_texts() if x])
    snap('after ORDER1 cancel')
    pg.screenshot(path=S+'flows_B16_3_after.png')
run(f)
