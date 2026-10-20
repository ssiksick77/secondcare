from pw import *
from h import *
def dump(tag):
    a=all_()
    print(tag, 'deposit V:',[ (d['_row'],d['구분'],d['금액'],d['태그'],d['연결거래번호']) for d in a['deposit'] if d['거래처']=='신규거래처V'],
      'exec V:',[(e['거래번호'],e['금액'],e['거래처'],e['재원'],e['예산목'],e['태그'],e['비고']) for e in a['exec'] if e['거래처']=='신규거래처V'])
def f(pg):
    pg.get_by_role('tab',name='적립금').click(); pg.wait_for_timeout(600)
    pg.locator('button[data-add=deposit]').click(); pg.wait_for_timeout(500)
    pg.fill('#f-일자','2026-10-14'); pg.fill('#f-거래처','신규거래처V'); pg.select_option('#f-구분','적립'); pg.fill('#f-금액','300000')
    pg.check('#f-_record_exec'); pg.wait_for_timeout(300)
    pg.select_option('#f-_재원','QA01'); pg.select_option('#f-_예산목','연구재료비')
    pg.screenshot(path=S+'flows_B10_1_dep_form.png')
    pg.click('#dlg-save'); pg.wait_for_timeout(1000)
    print('err:',pg.locator('#dlg-error').inner_text())
    dump('after 적립')
    pg.screenshot(path=S+'flows_B10_2_after_dep.png')
    pg.locator('button[data-add=deposit]').click(); pg.wait_for_timeout(500)
    pg.fill('#f-일자','2026-10-14'); pg.fill('#f-거래처','신규거래처V'); pg.select_option('#f-구분','사용'); pg.fill('#f-금액','100000')
    pg.wait_for_timeout(300)
    print('tag field', pg.locator('#f-태그').count())
    try: pg.select_option('#f-태그','가상태그1')
    except Exception as e:
        pg.fill('#f-태그','가상태그1')
    pg.screenshot(path=S+'flows_B10_3_use_form.png')
    pg.click('#dlg-save'); pg.wait_for_timeout(1000)
    print('err:',pg.locator('#dlg-error').inner_text())
    dump('after 사용')
if __name__=="__main__": run(f)
