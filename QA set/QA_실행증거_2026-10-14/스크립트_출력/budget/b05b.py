from h import *
from playwright.sync_api import sync_playwright
r=requests.post(B+'/api/exec',json={'재원':'QA10','예산목':'연구활동비','원인발생일':'2025-12-20','금액':1000,'적요':'B05 2025','거래처':'B05'}); print(show(r)); row=r.json()['_row']; no=r.json()['거래번호']
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.goto(B); pg.wait_for_timeout(1200)
    print('years',[o.inner_text() for o in pg.query_selector_all('#dash-year option')],'default',pg.input_value('#dash-year'))
    pg.select_option('#dash-fund','QA10')
    pg.select_option('#dash-year','2025'); pg.wait_for_timeout(300)
    print('2025:',pg.inner_text('#dash-note')); print(pg.inner_text('#dash-table')[:400])
    pg.screenshot(path=SH+'B05_2025.png',full_page=True)
    pg.select_option('#dash-year','2026'); pg.wait_for_timeout(300); print('2026:',pg.inner_text('#dash-note'))
    pg.select_option('#dash-year',''); pg.wait_for_timeout(300); print('전체:',pg.inner_text('#dash-note'))
    b.close()
print(show(requests.delete(f'{B}/api/exec/{row}',json={'expect':{'거래번호':no}})))
