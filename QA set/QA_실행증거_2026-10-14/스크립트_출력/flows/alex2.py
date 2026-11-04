from pw import *
from h import *
def f(pg):
    pg.get_by_role('tab',name='대시보드').click(); pg.wait_for_timeout(800)
    print(pg.locator('#panel-dash').inner_text()[:700].replace('\n',' | '))
    ex_=pg.locator('text=/집계 제외/'); print('집계 제외 elems',ex_.count(), ex_.all_inner_texts()[:3])
    pg.screenshot(path=S+'flows_ALEX1_dash.png')
    if ex_.count():
        ex_.first.click(); pg.wait_for_timeout(700); pg.screenshot(path=S+'flows_ALEX1_excluded.png')
        print(pg.locator('dialog[open]').inner_text()[:800].replace('\n',' | ') if pg.locator('dialog[open]').count() else 'no dialog')
    # fund filter options
    print('fund options',pg.locator('#dash-fund option').all_inner_texts())
    pg.select_option('#dash-fund','QA01'); pg.wait_for_timeout(500)
    rows=pg.locator('#dash-table tr, #panel-dash table tr')
    print([r.inner_text().replace('\n',' ').replace('\t',' ') for r in pg.locator('#panel-dash table tbody tr').all() if '인건비' in r.inner_text()][:6])
run(f)
