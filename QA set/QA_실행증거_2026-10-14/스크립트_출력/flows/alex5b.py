from pw2 import *
from h import *
def f(pg):
    for tag in ['ZZ','lc','sp','ko']:
        pg.reload(); pg.wait_for_timeout(1200)
        pg.get_by_role('tab',name='장비').first.click(); pg.wait_for_timeout(500)
        pg.locator(f'tr:has-text("QA관련과제-{tag}") input[type=checkbox]').check()
        pg.click('button[data-rq="convert"]'); pg.wait_for_timeout(800)
        print(tag,'-> convert form 재원:',repr(pg.locator('#f-재원').input_value()))
        if tag=='ZZ':
            pg.screenshot(path=S+'flows_ALEX3_free_project_convert.png')
            pg.select_option('#f-예산목','연구활동비')
            pg.click('#dlg-save'); pg.wait_for_timeout(800); print('   save w/o 재원 err:',pg.locator('#dlg-error').inner_text())
            pg.screenshot(path=S+'flows_ALEX3_free_project_err.png')
run(f)
