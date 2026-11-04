from pw2 import *
from h import *
def f(pg):
    pg.get_by_role('tab',name='장비').first.click(); pg.wait_for_timeout(500)
    pg.get_by_role('button',name='신청 추가').click(); pg.wait_for_timeout(600)
    pg.screenshot(path=S+'flows_B13_1_new_request_form.png')
    pg.fill('#f-신청인','가상신청인3'); pg.fill('#f-관련과제','QA05'); pg.fill('#f-품목','QA 장비 VAT건'); pg.fill('#f-단가','50000'); pg.fill('#f-수량','1')
    pg.check('#f-부가세구분'); pg.wait_for_timeout(300)
    print('부가세액 default:', pg.locator('#f-부가세액').input_value(), '금액 ro:', pg.locator('#f-_금액').input_value() if pg.locator('#f-_금액').count() else None)
    pg.fill('#f-사유','QA B-13')
    pg.screenshot(path=S+'flows_B13_2_new_request_filled.png')
    pg.click('#dlg-save'); pg.wait_for_timeout(1000)
    print('err:',pg.locator('#dlg-error').inner_text())
    a=all_(); print([ (r['신청번호'],r['상태'],r['금액'],r['부가세구분'],r['부가세액']) for r in a['request'] if r['품목']=='QA 장비 VAT건'])
run(f)
