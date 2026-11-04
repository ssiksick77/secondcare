from pw import *
def f(pg):
    b=pg.locator('tr[data-kind="exec"][data-row="2"] td.st-cell button.next')
    print(b.bounding_box(), b.evaluate('e=>{const c=getComputedStyle(e);return [c.display,c.visibility,c.opacity,getComputedStyle(e.closest("td")).display]}'))
    pg.screenshot(path=S+'flows_dbg.png')
run(f)
