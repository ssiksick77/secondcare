from pw2 import *
from h import *
def f(pg):
    pg.get_by_role('tab',name='소모품').first.click(); pg.wait_for_timeout(500)
    pg.locator('tr:has-text("R-2026-021") input[type=checkbox]').check(); pg.wait_for_timeout(300)
    cv=pg.locator('button[data-rq="convert"]'); cv.click(); pg.wait_for_timeout(1000)
    print('dialogs open',pg.locator('dialog[open]').count())
    print('alerts',[x for x in pg.locator('[role=alert],[role=status],.toast').all_inner_texts() if x])
    pg.screenshot(path=S+'flows_B17_1b_partial_click.png')
run(f)
