import json, re
from playwright.sync_api import sync_playwright
U='http://127.0.0.1:8801'
out={}
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':1536,'height':864})
    pg=ctx.new_page()
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: errs.append(m.text) if m.type=='error' else None)
    pg.goto(U); pg.wait_for_timeout(2000)
    # A1 option labels
    out['A1_dash_fund_options']=pg.locator('#dash-fund option').all_inner_texts()
    out['A1_exec_fund_options']=pg.locator('select[data-filter="재원"][data-kind="exec"] option').all_inner_texts()
    # A2 filter independence
    pg.select_option('#dash-fund','QA02'); pg.wait_for_timeout(500)
    out['A2_dash_note_QA02']=pg.locator('#dash-note').inner_text()
    pg.click('#tab-exec'); pg.wait_for_timeout(500)
    out['A2_exec_fund_after_dash_QA02']=pg.locator('select[data-filter="재원"][data-kind="exec"]').input_value()
    pg.select_option('select[data-filter="재원"][data-kind="exec"]','QA03'); pg.wait_for_timeout(500)
    out['A2_exec_sum_QA03']=pg.locator('#exec-sum').inner_text()
    out['A2_exec_rows_QA03']=pg.locator('#exec-table tbody tr').count()
    pg.click('#tab-req'); pg.wait_for_timeout(300)
    out['A2_req_fund_after_exec_QA03']=pg.locator('select[data-filter="재원"][data-kind="req"]').input_value()
    pg.click('#tab-dash'); pg.wait_for_timeout(300)
    out['A2_dash_fund_back']=pg.locator('#dash-fund').input_value()
    pg.screenshot(path='shots/main_A2_dash_QA02.png')
    # A3 form default fund when exec filter = QA03
    pg.click('#tab-exec'); pg.wait_for_timeout(300)
    pg.click('button[data-add="exec"]'); pg.wait_for_timeout(500)
    out['A3_form_title']=pg.locator('#dlg-title').inner_text()
    fields=pg.locator('#dlg-fields [name]')
    names=[fields.nth(i).get_attribute('name') for i in range(fields.count())]
    out['A3_form_field_names']=names
    fsel=pg.locator('#dlg-fields [name="재원"]')
    out['A3_form_fund_default']=fsel.input_value()
    out['A3_form_fund_options']=fsel.locator('option').all_inner_texts() if fsel.evaluate('e=>e.tagName')=='SELECT' else 'input'
    out['A3_form_date_default']=pg.locator('#dlg-fields [name="원인발생일"]').input_value()
    out['A3_focused']=pg.evaluate('document.activeElement && (document.activeElement.name||document.activeElement.id)')
    pg.screenshot(path='shots/main_A3_exec_form.png')
    # fill & save
    pg.locator('#dlg-fields [name="재원"]').select_option('QA03')
    pg.locator('#dlg-fields [name="예산목"]').select_option('연구활동비')
    pg.locator('#dlg-fields [name="거래처"]').fill('탐색거래처')
    pg.locator('#dlg-fields [name="금액"]').fill('12345')
    pg.locator('#dlg-fields [name="적요"]').fill('탐색-A3 QA03 입력')
    pg.click('#dlg-save'); pg.wait_for_timeout(1500)
    out['A3_after_save_errors']=pg.locator('#dlg-error').inner_text() if pg.locator('#dlg-error').is_visible() else ''
    out['A3_toast']=pg.locator('.toast, [role=status], #toast').all_inner_texts()
    out['A3_rows_QA03_after']=pg.locator('#exec-table tbody tr').count()
    out['A3_visible_A3_in_QA03']=pg.locator('#exec-table tbody').inner_text().count('탐색-A3')
    pg.select_option('select[data-filter="재원"][data-kind="exec"]','QA04'); pg.wait_for_timeout(400)
    out['A3_visible_A3_in_QA04']=pg.locator('#exec-table tbody').inner_text().count('탐색-A3')
    out['A3_exec_sum_QA04']=pg.locator('#exec-sum').inner_text()
    pg.screenshot(path='shots/main_A3_exec_QA04.png')
    # A4 consistency exec-sum QA01 vs dashboard
    pg.select_option('select[data-filter="재원"][data-kind="exec"]','QA01'); pg.wait_for_timeout(400)
    out['A4_exec_sum_QA01']=pg.locator('#exec-sum').inner_text()
    out['A4_exec_headers']=pg.locator('#exec-table thead th').all_inner_texts()
    first=pg.locator('#exec-table tbody tr').first
    out['A4_first_row']=first.inner_text().replace('\n',' | ')
    pg.click('#tab-dash'); pg.select_option('#dash-fund','QA01'); pg.wait_for_timeout(400)
    out['A4_dash_note_QA01']=pg.locator('#dash-note').inner_text()
    # A5 QA10
    pg.select_option('#dash-fund','QA10'); pg.wait_for_timeout(400)
    out['A5_dash_note_QA10']=pg.locator('#dash-note').inner_text()
    out['A5_cards_QA10']=pg.locator('#dash-cards').inner_text()[:300]
    out['A5_table_QA10']=pg.locator('#dash-table').inner_text()[:300]
    pg.screenshot(path='shots/main_A5_dash_QA10.png')
    # A6 reload persistence
    pg.click('#tab-exec'); pg.select_option('select[data-filter="재원"][data-kind="exec"]','QA05'); pg.wait_for_timeout(300)
    pg.reload(); pg.wait_for_timeout(2000)
    out['A6_tab_after_reload']=pg.evaluate('document.querySelector("#main-tabs [aria-selected=true]").id')
    out['A6_exec_fund_after_reload']=pg.locator('select[data-filter="재원"][data-kind="exec"]').input_value()
    out['A6_dash_fund_after_reload']=pg.locator('#dash-fund').input_value()
    # A7 month filter on exec: Feb QA01
    pg.click('#tab-exec'); pg.select_option('select[data-filter="재원"][data-kind="exec"]','QA01'); pg.select_option('select[data-filter="year"][data-kind="exec"]','2026'); pg.select_option('select[data-filter="month"][data-kind="exec"]','02'); pg.wait_for_timeout(400)
    out['A7_exec_sum_QA01_2026-02']=pg.locator('#exec-sum').inner_text()
    # switch fund keeping month
    pg.select_option('select[data-filter="재원"][data-kind="exec"]','QA02'); pg.wait_for_timeout(400)
    out['A7_month_kept_after_fund_switch']=pg.locator('select[data-filter="month"][data-kind="exec"]').input_value()
    out['A7_exec_sum_QA02_2026-02']=pg.locator('#exec-sum').inner_text()
    # A8 laptop width
    pg2=ctx.new_page(); pg2.set_viewport_size({'width':1366,'height':768}); pg2.goto(U); pg2.wait_for_timeout(1500)
    pg2.click('#tab-exec'); pg2.wait_for_timeout(500); pg2.screenshot(path='shots/main_A8_exec_1366.png')
    out['A8_horizontal_scroll_body']=pg2.evaluate('document.documentElement.scrollWidth>document.documentElement.clientWidth')
    out['errors']=errs
    b.close()
print(json.dumps(out,ensure_ascii=False,indent=1))
