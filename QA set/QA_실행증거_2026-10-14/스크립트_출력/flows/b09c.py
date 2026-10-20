from pw import *
from h import *
def st(tag):
    e=ex('2026-QA01-001'); print(tag,'| API:',e['상태'],e['지급청구일'],e['지출완료일'],e['결의일'])
def f(pg):
    pg.click('tr[data-kind="exec"][data-row="2"] td[data-col="재원"]'); pg.wait_for_timeout(700)
    pg.locator('#exec-drawer .xd-date[data-field="지급청구일"]').click(); pg.wait_for_timeout(400)
    pg.screenshot(path=S+'flows_B09_8_edit_claimdate.png')
    inp=pg.locator('#exec-drawer input[type="date"]'); print('inputs',inp.count())
    inp.first.fill(''); inp.first.press('Enter'); pg.wait_for_timeout(900)
    pg.screenshot(path=S+'flows_B09_9_after_clear_claim.png')
    st('after UI clear 청구일 (승인 존재)')
    print('alerts:', pg.locator('[role=alert],[role=status],.toast').all_inner_texts())
run(f)
