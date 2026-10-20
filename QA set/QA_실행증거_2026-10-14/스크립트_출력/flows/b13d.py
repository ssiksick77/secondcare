from pw import *
from h import *
def f(pg):
    pg.get_by_role('tab',name='품의내역').click(); pg.wait_for_timeout(600)
    r=pg.locator('tr[data-kind="req"]:has-text("2026-QA05-003")'); print(r.inner_text().replace('\n',' | '))
    print([b.inner_text() for b in r.locator('button').all()])
    pg.screenshot(path=S+'flows_B13_7_req_tab.png')
run(f)
