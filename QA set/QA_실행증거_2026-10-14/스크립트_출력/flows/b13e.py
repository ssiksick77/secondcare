from pw import *
from h import *
def f(pg):
    pg.get_by_role('tab',name='품의내역').click(); pg.wait_for_timeout(600)
    pg.locator('tr[data-kind="req"]:has-text("2026-QA05-003") button:has-text("집행전환")').click(); pg.wait_for_timeout(800)
    pg.screenshot(path=S+'flows_B13_8_toexec_form.png')
    for k in ['재원','예산목','거래처','적요','금액','결제수단','사용자','비고','원인발생일']:
        el=pg.locator(f'#f-{k}'); print(k, el.input_value() if el.count() else None)
    print('title', pg.locator('#dlg-title').inner_text(), pg.locator('#dlg-error').inner_text())
    pg.fill('#f-거래처','가상장비업체'); pg.select_option('#f-결제수단','연구비카드')
    pg.click('#dlg-save'); pg.wait_for_timeout(1200)
    print('err',pg.locator('#dlg-error').inner_text(), [x for x in pg.locator('[role=alert],[role=status],.toast').all_inner_texts() if x])
    a=all_(); print([ (e['거래번호'],e['금액'],e['비고'],e['상태']) for e in a['exec'] if '2026-QA05-003' in (e['비고'] or '')])
    print([ (r['품의번호'],r['상태']) for r in a['req'] if r['품의번호']=='2026-QA05-003'])
    print([ (r['신청번호'],r['상태'],r['연결품의번호'],r['_can_convert']) for r in a['request'] if r['신청번호'] in ('R-2026-011','R-2026-017')])
run(f)
