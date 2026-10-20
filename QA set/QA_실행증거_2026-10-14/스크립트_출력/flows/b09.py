from pw import *
from h import *
def st(pg,tag):
    r=pg.locator('tr[data-kind="exec"][data-row="2"]')
    t=r.locator('td.st-cell').inner_text().replace('\n',' / ')
    e=ex('2026-QA01-001')
    print(tag,'| UI:',t,'| API:',e['상태'],e['지급청구일'],e['지출완료일'],e['결의일'])
def f(pg):
    st(pg,'0 발생')
    sel='tr[data-kind="exec"][data-row="2"] td.st-cell button.next'
    pg.click(sel); pg.wait_for_timeout(800); st(pg,'1 after ✓ (청구)')
    pg.screenshot(path=S+'flows_B09_1_claim.png')
    pg.click('tr[data-kind="exec"][data-row="2"] td.st-cell button[data-action="fix"]'); pg.wait_for_timeout(800); st(pg,'2 보완 표시')
    pg.screenshot(path=S+'flows_B09_2_fix.png')
    pg.click('tr[data-kind="exec"][data-row="2"] td.st-cell button[data-action="unfix"]'); pg.wait_for_timeout(800); st(pg,'3 해제')
    pg.click(sel); pg.wait_for_timeout(800); st(pg,'4 ✓ (승인=지출완료일)')
    pg.screenshot(path=S+'flows_B09_4_approved.png')
    # open drawer
    pg.click('tr[data-kind="exec"][data-row="2"] td:nth-child(3)'); pg.wait_for_timeout(800)
    pg.screenshot(path=S+'flows_B09_5_drawer_approved.png')
    v=pg.locator('#exec-drawer button[data-act="voucher"]')
    print('결의서 button count',v.count(),'disabled?',v.is_disabled() if v.count() else None, v.get_attribute('title') if v.count() else '')
    print(pg.locator('#exec-drawer').inner_text()[:900].replace('\n',' | '))
run(f)
