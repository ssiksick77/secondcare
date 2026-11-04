from pw import *
from h import *
def st(tag):
    e=ex('2026-QA01-001'); print(tag,'| API:',e['상태'],e['지급청구일'],e['지출완료일'],e['결의일'])
def clear(pg,col):
    pg.reload(); pg.wait_for_timeout(1200); pg.get_by_role('tab',name='집행내역').click(); pg.wait_for_timeout(600)
    pg.click('tr[data-kind="exec"][data-row="2"] td[data-col="재원"]'); pg.wait_for_timeout(600)
    pg.locator(f'#exec-drawer .xd-date[data-field="{col}"]').click(); pg.wait_for_timeout(300)
    inp=pg.locator('#exec-drawer input[type="date"]'); inp.first.fill(''); inp.first.press('Enter'); pg.wait_for_timeout(900)
def f(pg):
    clear(pg,'결의일'); st('after clear 결의일')
    print([x for x in pg.locator('[role=alert],[role=status],.toast').all_inner_texts() if x])
    clear(pg,'지출완료일'); st('after clear 지출완료일')
    pg.screenshot(path=S+'flows_B09_12_back_to_claim.png')
    print(pg.locator('tr[data-kind="exec"][data-row="2"] td.st-cell').inner_text().replace('\n',' / '))
run(f)
