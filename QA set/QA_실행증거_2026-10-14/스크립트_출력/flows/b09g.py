from pw import *
from h import *
def f(pg):
    pg.click('tr[data-kind="exec"][data-row="12"] td[data-col="재원"]'); pg.wait_for_timeout(600)
    pg.locator('#exec-drawer button[data-act="edit"]').click(); pg.wait_for_timeout(600)
    pg.fill('#f-결의일','2026-10-10'); pg.screenshot(path=S+'flows_B09_13_dialog.png')
    pg.locator('dialog[open] button[type=submit], dialog[open] #dlg-save').first.click(); pg.wait_for_timeout(900)
    e=ex([x for x in all_()['exec'] if x['_row']==12][0]['거래번호']); print({k:e[k] for k in ['상태','지급청구일','지출완료일','결의일']})
run(f)
