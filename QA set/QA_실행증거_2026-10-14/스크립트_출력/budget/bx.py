from h import *
from playwright.sync_api import sync_playwright
import re
r=requests.post(B+'/api/exec',json={'재원':'QA09','예산목':'연구재료비','원인발생일':'2026-09-23','금액':5000,'적요':'BX 예산0 집행','거래처':'BX'}); print(show(r)[0]); row=r.json()['_row']; no=r.json()['거래번호']
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.goto(B); pg.wait_for_timeout(1200)
    pg.select_option('#dash-fund','QA09'); pg.wait_for_timeout(300)
    print(pg.inner_text('#dash-note')); print(pg.inner_text('#dash-table')); print(pg.inner_text('#dash-cards').replace('\n',' | '))
    pg.screenshot(path=SH+'BX_zero_budget_item.png',full_page=True)
    pg.click('#tab-exec'); pg.select_option('[data-filter=재원][data-kind=exec]','QA09'); pg.wait_for_timeout(300); print(pg.inner_text('#exec-table')[:700])
    # subtotal sum check on dashboard all funds
    pg.click('#tab-dash'); pg.select_option('#dash-fund',''); pg.select_option('#dash-month',''); pg.wait_for_timeout(300)
    rows=[l.split('\t') for l in pg.inner_text('#dash-table').split('\n')]
    tot=[0,0,0]; 
    for l in rows:
        if len(l)>2 and l[1]=='소계':
            n=lambda s:int(s.replace(',','')) if re.fullmatch(r'-?[\d,]+',s) else 0
            tot[0]+=n(l[2]); tot[1]+=n(l[3]); tot[2]+=n(l[-1])
    print('SUM of 소계 rows 예산/집행/가용',tot); print('NOTE',pg.inner_text('#dash-note'))
    # dash month persistence across fund switch
    pg.select_option('#dash-month','03'); pg.select_option('#dash-fund','QA02'); print('dash month after fund switch:',pg.input_value('#dash-month'))
    b.close()
print(show(requests.delete(f'{B}/api/exec/{row}',json={'expect':{'거래번호':no}})))
