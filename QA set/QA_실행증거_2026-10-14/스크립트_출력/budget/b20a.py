from h import *
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.goto(B)
    pg.wait_for_timeout(1500)
    print([o.inner_text() for o in pg.query_selector_all('#dash-fund option')])
    pg.select_option('#dash-fund','QA10'); pg.wait_for_timeout(500)
    print('NOTE',pg.inner_text('#dash-note'))
    print('CARDS',pg.inner_text('#dash-cards')[:400])
    print('TABLE',pg.inner_text('#dash-table'))
    pg.screenshot(path=SH+'B20_dash_initial.png',full_page=True)
    pg.click('#tab-exec'); pg.select_option('[data-filter=재원][data-kind=exec]','QA10'); pg.wait_for_timeout(500)
    print('EXEC',pg.inner_text('#exec-table')[:300],'|',pg.inner_text('#exec-sum'))
    pg.screenshot(path=SH+'B20_exec_initial.png',full_page=True)
    pg.click('#tab-budget'); pg.select_option('[data-filter=재원][data-kind=budget]','QA10'); pg.wait_for_timeout(500)
    print('BUD',pg.inner_text('#panel-budget'))
    pg.screenshot(path=SH+'B20_budget_initial.png',full_page=True)
    b.close()
