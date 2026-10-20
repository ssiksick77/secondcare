from pw import *
def f(pg):
    pg.click('tr[data-kind="exec"][data-row="12"] td[data-col="재원"]'); pg.wait_for_timeout(700)
    print('row12 status cell:',pg.locator('tr[data-kind="exec"][data-row="12"] td.st-cell').inner_text().replace('\n',' / '))
    v=pg.locator('#exec-drawer button[data-act="voucher"]'); print('voucher disabled',v.is_disabled(),v.get_attribute('title'))
    print(pg.locator('#exec-drawer .xd-step').all_inner_texts())
    pg.screenshot(path=S+'flows_B09_15_resolve_only_dates_empty.png')
run(f)
