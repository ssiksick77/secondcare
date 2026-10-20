from pw import *
def f(pg):
    pg.get_by_role('tab',name='적립금').click(); pg.wait_for_timeout(600)
    pg.locator('button[data-act="dep-use"][data-vendor="가상문구A"]').click(); pg.wait_for_timeout(500)
    pg.screenshot(path=S+'flows_dbg.png')
    print(pg.evaluate('''()=>{const e=document.getElementById("f-태그");return [e.closest("label,div")?.outerHTML.slice(0,300), e.closest("[hidden]")?1:0]}'''))
run(f)
