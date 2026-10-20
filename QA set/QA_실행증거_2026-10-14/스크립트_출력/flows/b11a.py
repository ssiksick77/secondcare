from playwright.sync_api import sync_playwright
import sys
sys.stdout.reconfigure(encoding='utf-8')
from h import *
S='../shots/'
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_context(viewport={'width':1500,'height':950}).new_page()
    pg.on('dialog', lambda d: d.accept())
    pg.goto('http://127.0.0.1:8813/labor'); pg.wait_for_timeout(1500)
    pg.get_by_role('tab',name='지급 원장').click(); pg.wait_for_timeout(700)
    pg.screenshot(path=S+'flows_B11_1_ledger.png')
    rows=pg.locator('tr[data-kind="labor"]'); print('rows',rows.count())
    print(pg.locator('button[data-labor="confirm"]').first.get_attribute('data-row'))
    r=pg.locator('tr:has(button[data-labor="confirm"][data-row="8"])'); print(r.first.inner_text().replace('\n',' | '))
    pg.locator('button[data-labor="confirm"][data-row="8"]').click(); pg.wait_for_timeout(600)
    pg.screenshot(path=S+'flows_B11_2_confirm_dialog.png')
    print(pg.locator('dialog[open]').inner_text().replace('\n',' | '))
    pg.fill('#pay-date','2026-10-12'); 
    pg.locator('dialog[open] button.btn-primary, dialog[open] button[type=submit]').last.click(); pg.wait_for_timeout(1000)
    a=all_(); l=[x for x in a['labor'] if x['_row']==8][0]; print(l)
    print([e for e in a['exec'] if e['거래번호']==l['연결거래번호']])
    pg.screenshot(path=S+'flows_B11_3_after_confirm.png')
    b.close()
