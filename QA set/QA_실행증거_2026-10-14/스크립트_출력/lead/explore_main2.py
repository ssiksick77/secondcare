import json
from playwright.sync_api import sync_playwright
U='http://127.0.0.1:8801'
out={}
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1536,'height':864})
    pg.goto(U); pg.wait_for_timeout(1500)
    pg.click('#tab-exec'); pg.select_option('select[data-filter="재원"][data-kind="exec"]','QA01'); pg.wait_for_timeout(400)
    # click a row with 완료/결의 state (E004/E005) - search 'E004'
    pg.fill('input[data-filter="q"][data-kind="exec"]','E004'); pg.wait_for_timeout(400)
    out['rows_E004']=pg.locator('#exec-table tbody tr').count()
    pg.locator('#exec-table tbody tr').first.click(); pg.wait_for_timeout(800)
    panel=pg.locator('#exec-detail, .detail, aside[aria-label], #detail-panel')
    # find the visible panel generically
    txt=pg.evaluate('''()=>{const c=[...document.querySelectorAll("aside,section,div")].filter(e=>e.offsetWidth>400&&e.offsetWidth<700&&e.innerText.includes("처리 단계"));return c.length?c[0].innerText.slice(0,1500):"(no panel found)"}''')
    out['detail_panel_text']=txt
    out['detail_has_project_name']='가상영상연구 A' in txt
    pg.screenshot(path='shots/main_B_detail_E004.png')
    # voucher
    vb=pg.locator('button:has-text("결의서")')
    out['voucher_btn_count']=vb.count()
    if vb.count():
        out['voucher_btn_disabled']=vb.first.is_disabled(); out['voucher_btn_title']=vb.first.get_attribute('title')
        if not vb.first.is_disabled():
            vb.first.click(); pg.wait_for_timeout(800)
            vt=pg.locator('#dlg-voucher').inner_text()
            out['voucher_text_head']=vt[:900]
            pg.screenshot(path='shots/main_B_voucher_E004.png')
            pg.keyboard.press('Escape')
    # exec table similar-name check: hover title on 재원 cell?
    pg.fill('input[data-filter="q"][data-kind="exec"]',''); pg.wait_for_timeout(300)
    cell=pg.locator('#exec-table tbody tr').first.locator('td').nth(4)
    out['fund_cell_text']=cell.inner_text(); out['fund_cell_title']=cell.get_attribute('title')
    # 재원 탭
    pg.click('#tab-funds'); pg.wait_for_timeout(400)
    out['funds_tab_text']=pg.locator('#funds-table').inner_text()[:600]
    pg.screenshot(path='shots/main_B_funds_tab.png')
    # 신청 담당자 화면 관련과제 옵션
    pg.click('header button:has-text("신청")'); pg.wait_for_timeout(1200)
    out['request_project_filter_options']=pg.locator('select[data-filter="관련과제"] option').all_inner_texts()
    pg.click('button[data-add="request"]'); pg.wait_for_timeout(600)
    rp=pg.locator('#dlg-fields [name="관련과제"]')
    out['request_form_project_field']=rp.evaluate('e=>e.tagName+" list="+(e.getAttribute("list")||"")') if rp.count() else 'none'
    if rp.count() and rp.get_attribute('list'):
        out['request_form_project_datalist']=pg.locator('#'+rp.get_attribute('list')+' option').evaluate_all('os=>os.map(o=>o.value+"|"+o.label)')
    pg.screenshot(path='shots/main_B_request_form.png')
    b.close()
print(json.dumps(out,ensure_ascii=False,indent=1))
