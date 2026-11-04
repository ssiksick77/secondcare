from pw2 import *
from h import *
def rq(no): return next(r for r in all_()['request'] if r['신청번호']==no)
def show(tag,no):
    r=rq(no); print(tag,no,{k:r[k] for k in ['상태','금액','결재인','결재일','비고']})
show('before','R-2026-007'); show('before','R-2026-008')
def f(pg):
    # RQ07 학회
    pg.get_by_role('tab',name='학회').first.click(); pg.wait_for_timeout(500)
    pg.locator('tr:has-text("R-2026-007")').dblclick(); pg.wait_for_timeout(800)
    pg.screenshot(path=S+'flows_B14_1_edit_rq07.png')
    pg.fill('#f-금액','15000')
    pg.click('#dlg-save'); pg.wait_for_timeout(800)
    pg.screenshot(path=S+'flows_B14_2_confirm_dialog.png')
    print('confirm:', pg.locator('dialog[open]').last.inner_text().replace('\n',' | '))
    print([b.inner_text() for b in pg.locator('dialog[open] button').all()])
    pg.locator('dialog[open] button:has-text("신청으로 되돌리기")').click(); pg.wait_for_timeout(1000)
    show('after amount edit','R-2026-007')
    print('alerts',[x for x in pg.locator('[role=alert],[role=status],.toast').all_inner_texts() if x])
    pg.screenshot(path=S+'flows_B14_3_after.png')
    # RQ08 장비 비고만
    pg.get_by_role('tab',name='장비').first.click(); pg.wait_for_timeout(500)
    pg.locator('tr:has-text("R-2026-008")').dblclick(); pg.wait_for_timeout(800)
    pg.fill('#f-비고','QA 비고만 수정')
    pg.click('#dlg-save'); pg.wait_for_timeout(1000)
    print('dialog open after save?', pg.locator('dialog[open]').count())
    show('after 비고 edit','R-2026-008')
run(f)
