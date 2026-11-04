from h import *
from playwright.sync_api import sync_playwright
def snap(tag):
    d=all_(); t=[x for x in d['dashboard']['table'] if x['재원']=='QA02' and x['예산목']=='연구활동비'][0]
    rq=[r for r in d['req'] if r['품의번호']=='2026-QA02-001'][0]
    ex=[e for e in d['exec'] if e['재원']=='QA02']
    print(tag,'dash',{k:t[k] for k in('집행액','잔액','품의대기','가용잔액')},'req상태',rq['상태'],'exec건수',len(ex),'전체exec',len(d['exec']))
    return d
snap('BEFORE')
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.goto(B); pg.wait_for_timeout(1200)
    pg.click('#tab-req'); pg.select_option('[data-filter=재원][data-kind=req]','QA02'); pg.wait_for_timeout(400)
    print(pg.inner_text('#req-table'))
    pg.click('#req-table [data-act=toexec]'); pg.wait_for_timeout(500)
    print('FORM',pg.inner_text('#dlg-title'),pg.eval_on_selector_all('#dlg-fields input,#dlg-fields select,#dlg-fields textarea','els=>els.map(e=>(e.name||e.id)+"="+e.value)'))
    pg.screenshot(path=SH+'B06_toexec_form.png')
    pg.click('#dlg-cancel'); pg.wait_for_timeout(400)
    if pg.is_visible('#dlg-confirm'): print('cancel confirm shown:',pg.inner_text('#dlg-confirm')); pg.click('#confirm-ok'); pg.wait_for_timeout(300)
    snap('AFTER_CANCEL')
    pg.click('#req-table [data-act=toexec]'); pg.wait_for_timeout(500)
    pg.click('#dlg-save'); pg.wait_for_timeout(900)
    print('ERR', pg.inner_text('#dlg-error') if pg.is_visible('#dlg-error') else 'none','| alert',pg.inner_text('#alert') if pg.is_visible('#alert') else '')
    pg.screenshot(path=SH+'B06_after_save.png',full_page=True)
    print(pg.inner_text('#req-table'))
    b.close()
d=snap('AFTER_SAVE')
for e in d['exec']:
    if e['재원']=='QA02' and e['_row']>=150: print(e)
