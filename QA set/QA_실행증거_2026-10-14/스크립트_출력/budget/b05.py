from h import *
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.goto(B); pg.wait_for_timeout(1200)
    pg.select_option('#dash-fund','QA01')
    for m in ['02','01','03','']:
        pg.select_option('#dash-month',m); pg.wait_for_timeout(300)
        print('MONTH',m,'|',pg.inner_text('#dash-note'))
        rows=pg.inner_text('#dash-table').split('\n')
        print(rows[0]); print(rows[1])
        if m=='02': pg.screenshot(path=SH+'B05_QA01_feb.png',full_page=True); print(pg.inner_text('#dash-cards')[:300].replace('\n',' | '))
        if m=='01': pg.screenshot(path=SH+'B05_QA01_jan.png',full_page=True)
    # all funds month 2
    pg.select_option('#dash-fund',''); pg.select_option('#dash-month','02'); pg.wait_for_timeout(300); print('ALL FEB',pg.inner_text('#dash-note'))
    # exec tab filter persistence from dash
    pg.click('#tab-exec'); print('exec filters after dash change: fund=',pg.input_value('[data-filter=재원][data-kind=exec]'),'month=',pg.input_value('[data-filter=month][data-kind=exec]'))
    b.close()
