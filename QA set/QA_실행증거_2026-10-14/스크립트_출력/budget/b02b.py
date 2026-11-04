from h import *
from playwright.sync_api import sync_playwright
import re
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.goto(B); pg.wait_for_timeout(1200)
    pg.click('#tab-exec'); pg.select_option('[data-filter=재원][data-kind=exec]','QA03'); pg.wait_for_timeout(300)
    pg.click('[data-add=exec]'); pg.wait_for_timeout(400)
    print('form fund default:',pg.input_value('#dlg-fields [name=재원]'), '| options',[o.inner_text() for o in pg.query_selector_all('#dlg-fields [name=재원] option')])
    pg.screenshot(path=SH+'B02_form_default_fund.png')
    print('form default 예산목',pg.input_value('#dlg-fields [name=예산목]'),'date',pg.input_value('#dlg-fields [name=원인발생일]'))
    for k,v in dict(예산목='연구활동비',원인발생일='2026-09-25',거래처='B02거래처',금액='1234',적요='B02 QA03 고유').items():
        el=pg.locator(f'#dlg-fields [name={k}]')
        el.select_option(v) if el.evaluate('e=>e.tagName')=='SELECT' else el.fill(v)
    pg.click('#dlg-save'); pg.wait_for_timeout(800)
    print('dlg open after save:',pg.is_visible('#dlg'),'confirm',pg.is_visible('#dlg-confirm'))
    print('QA03 view sum',pg.inner_text('#exec-sum'), 'has new row', 'B02 QA03 고유' in pg.inner_text('#exec-table'))
    pg.select_option('[data-filter=재원][data-kind=exec]','QA04'); pg.wait_for_timeout(300)
    print('QA04 view sum',pg.inner_text('#exec-sum'), 'has new row', 'B02 QA03 고유' in pg.inner_text('#exec-table'))
    pg.select_option('[data-filter=재원][data-kind=exec]','QA03'); pg.wait_for_timeout(300)
    print('QA03 again',pg.inner_text('#exec-sum'),'has new row', 'B02 QA03 고유' in pg.inner_text('#exec-table'))
    # similar names QA01/QA02 detail drawer
    pg.select_option('[data-filter=재원][data-kind=exec]','QA02'); pg.wait_for_timeout(300)
    pg.locator('#exec-table tbody tr').first.click(); pg.wait_for_timeout(500)
    print('DRAWER head',pg.inner_text('#xd-title'),'|',pg.inner_text('#xd-sub')); 
    print('has 과제명 in drawer:', '가상영상연구' in pg.inner_text('#exec-drawer'))
    pg.screenshot(path=SH+'B02_drawer_QA02.png')
    pg.click('#xd-close')
    # tab sharing: set exec fund QA05, check req & dash & budget
    pg.select_option('[data-filter=재원][data-kind=exec]','QA05')
    pg.click('#tab-req'); print('req fund after exec=QA05:',pg.input_value('[data-filter=재원][data-kind=req]'))
    pg.click('#tab-dash'); print('dash fund:',pg.input_value('#dash-fund'))
    pg.select_option('#dash-fund','QA06'); pg.click('#tab-exec'); print('exec fund after dash=QA06:',pg.input_value('[data-filter=재원][data-kind=exec]'))
    pg.click('#tab-budget'); print('budget fund:',pg.input_value('[data-filter=재원][data-kind=budget]'))
    # dashboard dropdown labels and month persistence
    print('dash fund labels',[o.inner_text() for o in pg.query_selector_all('#dash-fund option')][:3])
    # funds tab
    pg.click('#tab-funds'); pg.wait_for_timeout(300); pg.screenshot(path=SH+'B02_funds_tab.png'); print(pg.inner_text('#funds-table')[:500])
    # exec: month filter persists when fund changes?
    pg.click('#tab-exec'); pg.select_option('[data-filter=month][data-kind=exec]','03'); pg.select_option('[data-filter=재원][data-kind=exec]','QA01'); pg.wait_for_timeout(300)
    print('month after fund switch',pg.input_value('[data-filter=month][data-kind=exec]'),pg.inner_text('#exec-sum'))
    pg.select_option('[data-filter=재원][data-kind=exec]','QA02'); print('qa02',pg.input_value('[data-filter=month][data-kind=exec]'),pg.inner_text('#exec-sum'))
    # reload persistence
    pg.reload(); pg.wait_for_timeout(1200); print('after reload fund/month',pg.input_value('[data-filter=재원][data-kind=exec]'),pg.input_value('[data-filter=month][data-kind=exec]'),'tab',pg.get_attribute('#tab-exec','aria-selected'))
    b.close()
