from pw2 import *
def f(pg):
    pg.get_by_role('tab',name='장비').first.click(); pg.wait_for_timeout(600)
    pg.screenshot(path=S+'flows_B13_0_admin_equip.png')
    print(pg.locator('body').get_attribute('class'))
    print(pg.locator('#panel-request, #rpanel').first.inner_text()[:600])
run(f)
