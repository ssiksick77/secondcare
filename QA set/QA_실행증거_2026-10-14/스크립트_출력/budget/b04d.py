from h import *
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.goto(B); pg.wait_for_timeout(1200)
    pg.select_option('#dash-fund','ZZ99'); pg.wait_for_timeout(300)
    print('ZZ99 NOTE',pg.inner_text('#dash-note')); print(pg.inner_text('#dash-table')[:600]); print(pg.inner_text('#dash-cards')[:300])
    pg.screenshot(path=SH+'B04_ZZ99_dash.png',full_page=True)
    pg.select_option('#dash-fund','')
    print(pg.inner_text('#dash-table')[-700:])
    b.close()
