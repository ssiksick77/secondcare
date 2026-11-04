from h import *
import json,re
from playwright.sync_api import sync_playwright
e=json.load(open(r'<home>\CAIH_회계장부_2026\QA set\expected_totals.json',encoding='utf-8'))
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.goto(B); pg.wait_for_timeout(1200)
    print('years',[o.inner_text() for o in pg.query_selector_all('#dash-year option')])
    print('months',[o.inner_text() for o in pg.query_selector_all('#dash-month option')])
    print('default year',pg.input_value('#dash-year'),'fund',pg.input_value('#dash-fund'))
    pg.select_option('#dash-fund','')
    print('ALL 2026:',pg.inner_text('#dash-note'))
    pg.screenshot(path=SH+'B04_all_2026.png',full_page=True)
    pg.select_option('#dash-year','')
    print('ALL 전체기간:',pg.inner_text('#dash-note'))
    pg.select_option('#dash-year','2026')
    tot=[0,0,0]
    for f in ['QA%02d'%i for i in range(1,11)]:
        pg.select_option('#dash-fund',f); pg.wait_for_timeout(150)
        n=pg.inner_text('#dash-note'); print(f,n)
    b.close()
