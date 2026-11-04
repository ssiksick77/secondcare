from h import *
from playwright.sync_api import sync_playwright
import csv,io
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000},accept_downloads=True); pg.goto(B); pg.wait_for_timeout(1500)
    pg.click('#tab-budget'); pg.click('[data-add=budget]'); pg.wait_for_timeout(400)
    pg.select_option('[name=재원]','QA10'); pg.wait_for_timeout(600)
    print('round after fund select:',pg.input_value('[name=변경회차]'))
    pg.fill('[name=변경회차]','이월'); pg.fill('[name=연구활동비]','5'); 
    pg.click('#dlg-save'); pg.wait_for_timeout(700)
    print('ERR',pg.inner_text('#dlg-error') if pg.is_visible('#dlg-error') else 'none', '| alert:',pg.inner_text('#alert') if pg.is_visible('#alert') else '')
    pg.screenshot(path=SH+'B01_dup_ui.png')
    pg.click('#dlg-cancel'); pg.wait_for_timeout(300); print('DISCARD',pg.inner_text('#dlg-confirm')); pg.click('#confirm-ok'); pg.wait_for_timeout(300)
    # dashboard QA10
    pg.click('#tab-dash'); pg.select_option('#dash-fund','QA10'); pg.wait_for_timeout(500)
    print('NOTE',pg.inner_text('#dash-note'))
    print('CARDS',pg.inner_text('#dash-cards').replace('\n',' | ')[:1500])
    pg.screenshot(path=SH+'B01_dash_QA10.png',full_page=True)
    with pg.expect_download() as d: pg.click('#dash-csv')
    path=Q+r'\inst_budget\dl\dash_QA10_B01.csv'; d.value.save_as(path); print(d.value.suggested_filename)
    print(open(path,encoding='utf-8-sig').read())
    pg.click('#tab-budget'); pg.select_option('[data-filter=재원][data-kind=budget]','QA10'); pg.wait_for_timeout(400)
    print(pg.inner_text('#budget-table'))
    b.close()
