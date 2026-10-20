from pw2 import *
from h import *
ids={}
for tag,proj in [('ZZ','미등록과제ZZ'),('lc','qa05'),('sp','  QA05  '),('ko','가상영상연구 A')]:
    s,j=api('POST','/api/request',{'구분':'장비','신청인':'가상신청인2','신청일':'2026-10-14','관련과제':proj,'품목':f'QA관련과제-{tag}','단가':10000,'수량':1,'금액':10000,'부가세구분':'N','부가세액':0,'사유':'QA alex5'})
    print(tag,s,repr(j.get('관련과제')) if isinstance(j,dict) else j); ids[tag]=j
    if s==200: print('  approve',api('POST',f"/api/request/{j['_row']}/action",{'action':'approve'})[0])
def f(pg):
    pg.get_by_role('tab',name='장비').first.click(); pg.wait_for_timeout(500)
    for tag in ids:
        if not isinstance(ids[tag],dict) or '_row' not in ids[tag]: continue
        pg.reload(); pg.wait_for_timeout(1200); pg.get_by_role('button',name='신청',exact=True).click(); pg.wait_for_timeout(800)
        pg.get_by_role('tab',name='장비').first.click(); pg.wait_for_timeout(500)
        pg.locator(f'tr:has-text("QA관련과제-{tag}") input[type=checkbox]').check()
        pg.click('button[data-rq="convert"]'); pg.wait_for_timeout(800)
        print(tag,'-> convert form 재원:',repr(pg.locator('#f-재원').input_value()), 'options', len(pg.locator('#f-재원 option').all()))
        if tag=='ZZ':
            pg.screenshot(path=S+'flows_ALEX3_free_project_convert.png')
            pg.select_option('#f-예산목','연구활동비')
            pg.click('#dlg-save'); pg.wait_for_timeout(800); print('   save w/o 재원 err:',pg.locator('#dlg-error').inner_text())
            pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
            if pg.locator('dialog[open]').count(): 
                try: pg.locator('dialog[open] button:has-text("취소")').first.click()
                except Exception as e: pass
run(f)
