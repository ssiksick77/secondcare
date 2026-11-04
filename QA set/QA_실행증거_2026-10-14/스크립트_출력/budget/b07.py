from h import *
from playwright.sync_api import sync_playwright
import re
def state(tag):
    d=all_(); t=[x for x in d['dashboard']['table'] if x['재원']=='QA01' and x['예산목']=='연구시설.장비비'][0]
    ex=[e for e in d['exec'] if e['관리번호']=='QA26JANSEP_V1_E001'][0]
    fs=sum(e['금액'] for e in d['exec'] if e['재원']=='QA01')
    print(tag,'E001금액',ex['금액'],'dash',{k:t[k] for k in('집행액','잔액','품의대기','가용잔액')},'QA01합',fs); return ex
ex=state('BEFORE'); no=ex['거래번호']; print(no)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.goto(B); pg.wait_for_timeout(1200)
    pg.click('#tab-exec'); pg.select_option('[data-filter=재원][data-kind=exec]','QA01'); pg.select_option('[data-filter=예산목][data-kind=exec]','연구시설.장비비'); pg.wait_for_timeout(400)
    print('LIST BEFORE\n',pg.inner_text('#exec-table')[:900]); print(pg.inner_text('#exec-sum'))
    row=pg.locator('#exec-table tr',has_text=no)
    row.dblclick(); pg.wait_for_timeout(500)
    print('FORM',pg.inner_text('#dlg-title'))
    pg.fill('[name=금액]','15000'); pg.screenshot(path=SH+'B07_edit_form.png')
    pg.click('#dlg-save'); pg.wait_for_timeout(900)
    print('ERR',pg.inner_text('#dlg-error') if pg.is_visible('#dlg-error') else 'none')
    print('LIST AFTER\n',pg.inner_text('#exec-table')[:900]); print(pg.inner_text('#exec-sum'))
    row=pg.locator('#exec-table tr',has_text=no); row.click(); pg.wait_for_timeout(600)
    print('DRAWER',pg.inner_text('#xd-body')[:600]); pg.screenshot(path=SH+'B07_drawer.png',full_page=True)
    pg.click('#xd-close')
    pg.click('#tab-dash'); pg.select_option('#dash-fund','QA01'); pg.wait_for_timeout(300); print('DASH',pg.inner_text('#dash-note')); pg.screenshot(path=SH+'B07_dash.png',full_page=True)
    print([l for l in pg.inner_text('#dash-table').split('\n') if '장비비' in l])
    b.close()
state('AFTER')
