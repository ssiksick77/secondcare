from pw import *
from h import *
e=ex('2026-QA01-001'); row=e['_row']
rec={k:v for k,v in e.items() if not k.startswith('_')}
rec.update({'지급청구일':'2026-10-14','지출완료일':'2026-10-14','결의일':''}); print('restore',api('PUT',f'/api/exec/{row}',{'rec':rec})[0])
def st(pg,tag):
    r=pg.locator('tr[data-kind="exec"][data-row="2"]')
    t=r.locator('td.st-cell').inner_text().replace('\n',' / ')
    e=ex('2026-QA01-001'); print(tag,'| UI:',t,'| API:',e['상태'],e['지급청구일'],e['지출완료일'],e['결의일'])
def f(pg):
    st(pg,'before resolve')
    pg.click('tr[data-kind="exec"][data-row="2"] td.st-cell button.next'); pg.wait_for_timeout(900)
    st(pg,'after ✓ resolve'); pg.screenshot(path=S+'flows_B09_10_resolved.png')
    print('next btn count', pg.locator('tr[data-kind="exec"][data-row="2"] td.st-cell button.next').count())
    pg.click('tr[data-kind="exec"][data-row="2"] td[data-col="재원"]'); pg.wait_for_timeout(700)
    print(pg.locator('#exec-drawer .xd-step').all_inner_texts())
    pg.screenshot(path=S+'flows_B09_11_drawer_resolved.png')
    v=pg.locator('#exec-drawer button[data-act="voucher"]'); print('voucher disabled',v.is_disabled())
    # try cancel 승인(지출완료일) while 결의 exists
    pg.locator('#exec-drawer .xd-date[data-field="지출완료일"]').click(); pg.wait_for_timeout(300)
    inp=pg.locator('#exec-drawer input[type="date"]'); inp.first.fill(''); inp.first.press('Enter'); pg.wait_for_timeout(800)
    st(pg,'after UI clear 완료일 w/ 결의'); print('alerts:', [x for x in pg.locator('[role=alert],[role=status],.toast').all_inner_texts() if x])
    # now cancel in order: 결의일 clear then 완료일 clear
    pg.locator('#exec-drawer .xd-date[data-field="결의일"]').click(); pg.wait_for_timeout(300)
    inp=pg.locator('#exec-drawer input[type="date"]'); inp.first.fill(''); inp.first.press('Enter'); pg.wait_for_timeout(800)
    st(pg,'after clear 결의일')
    pg.locator('#exec-drawer .xd-date[data-field="지출완료일"]').click(); pg.wait_for_timeout(300)
    inp=pg.locator('#exec-drawer input[type="date"]'); inp.first.fill(''); inp.first.press('Enter'); pg.wait_for_timeout(800)
    st(pg,'after clear 완료일'); 
    pg.screenshot(path=S+'flows_B09_12_back_to_claim.png')
run(f)
