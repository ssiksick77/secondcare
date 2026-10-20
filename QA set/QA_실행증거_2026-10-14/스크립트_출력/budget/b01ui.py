from h import *
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000},accept_downloads=True); pg.goto(B); pg.wait_for_timeout(1500)
    pg.click('#tab-budget'); pg.click('[data-add=budget]'); pg.wait_for_timeout(400)
    print('FIELDS',[l.inner_text().replace('\n',' ')[:30] for l in pg.query_selector_all('#dlg-fields label')])
    print('DEFAULTS',pg.eval_on_selector_all('#dlg-fields input,#dlg-fields select','els=>els.map(e=>(e.name||e.id)+"="+e.value)'))
    pg.screenshot(path=SH+'B01_budget_form.png')
    # try dup: set fund QA10, round 이월
    names=pg.eval_on_selector_all('#dlg-fields input,#dlg-fields select','els=>els.map(e=>e.name||e.id)')
    print(names)
    b.close()
