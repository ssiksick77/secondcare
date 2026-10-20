from pw import *
def f(pg):
    pg.get_by_role('tab',name='대시보드').click(); pg.wait_for_timeout(500)
    print(pg.locator('#panel-dash').inner_text().split('집계 제외')[0][-200:].replace('\n',' | '))
    pg.locator('#sub-tags').click(); pg.wait_for_timeout(700)
    print(pg.locator('#tag-recon').inner_text())
run(f)
