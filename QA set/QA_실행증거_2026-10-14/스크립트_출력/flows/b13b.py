from pw2 import *
from h import *
def rq(no): return next(r for r in all_()['request'] if r['신청번호']==no)
def f(pg):
    pg.get_by_role('tab',name='장비').first.click(); pg.wait_for_timeout(500)
    for no in ('R-2026-011','R-2026-017'):
        pg.locator(f'tr:has-text("{no}") input[type=checkbox]').check()
    pg.wait_for_timeout(300)
    pg.screenshot(path=S+'flows_B13_3_selected.png')
    print('convert btn enabled before approve?', pg.locator('button[data-rq="convert"]').is_enabled(), pg.locator('#req-sel-why').inner_text())
    pg.click('button[data-rq="approve"]'); pg.wait_for_timeout(1000)
    for no in ('R-2026-011','R-2026-017'):
        r=rq(no); print(no,r['상태'],r['결재인'],r['결재일'])
    pg.screenshot(path=S+'flows_B13_4_approved.png')
    print('alerts',[x for x in pg.locator('[role=alert],[role=status],.toast').all_inner_texts() if x])
run(f)
