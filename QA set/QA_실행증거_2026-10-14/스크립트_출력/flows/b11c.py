from playwright.sync_api import sync_playwright
import sys
sys.stdout.reconfigure(encoding='utf-8')
from h import *
S='../shots/'
n0=len(all_()['exec'])
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_context(viewport={'width':1500,'height':950}).new_page()
    pg.goto('http://127.0.0.1:8813/labor'); pg.wait_for_timeout(1500)
    pg.get_by_role('tab',name='지급 원장').click(); pg.wait_for_timeout(700)
    pg.locator('button[data-labor="unconfirm"][data-row="8"]').click(); pg.wait_for_timeout(600)
    pg.screenshot(path=S+'flows_B11_4_unconfirm_dialog.png')
    print(pg.locator('dialog[open]').inner_text().replace('\n',' | '))
    pg.locator('dialog[open] button:has-text("확정 취소")').click(); pg.wait_for_timeout(1000)
    a=all_(); l=[x for x in a['labor'] if x['_row']==8][0]; print(l)
    print('exec 026 exists:',any(e['거래번호']=='2026-QA01-026' for e in a['exec']),'exec count',n0,'->',len(a['exec']))
    pg.screenshot(path=S+'flows_B11_5_after_unconfirm.png')
    # PUT labor with unregistered name
    print(api('PUT','/api/labor/8',{'rec':{**{k:v for k,v in l.items() if not k.startswith('_')},'이름':'가상미등록인원'}}))
    b.close()
