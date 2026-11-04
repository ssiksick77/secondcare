from pw2 import *
from h import *
def rq(no): return next(r for r in all_()['request'] if r['신청번호']==no)
def f(pg):
    pg.get_by_role('tab',name='장비').first.click(); pg.wait_for_timeout(500)
    for no in ('R-2026-011','R-2026-017'):
        pg.locator(f'tr:has-text("{no}") input[type=checkbox]').check()
    pg.click('button[data-rq="convert"]'); pg.wait_for_timeout(800)
    pg.screenshot(path=S+'flows_B13_5_convert_form.png')
    for k in ['품의번호','재원','예산목','거래처','적요','금액','품의자','비고','원인발생일']:
        el=pg.locator(f'#f-{k}'); print(k, el.input_value() if el.count() else None)
    pg.select_option('#f-재원','QA05'); pg.select_option('#f-예산목','연구시설.장비비')
    pg.click('#dlg-save'); pg.wait_for_timeout(1200)
    print('err',pg.locator('#dlg-error').inner_text())
    a=all_(); new=[r for r in a['req'] if '신청 R-2026-011' in (r['비고'] or '')]; print(new)
    for no in ('R-2026-011','R-2026-017'):
        r=rq(no); print(no,r['상태'],r['연결품의번호'])
    pg.screenshot(path=S+'flows_B13_6_after_convert.png')
run(f)
