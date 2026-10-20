from playwright.sync_api import sync_playwright
from h import *
def open_page(p, path="/", ctx=None):
    b = p.chromium.launch()
    c = ctx or b.new_context(viewport={"width": 1500, "height": 950})
    pg = c.new_page()
    pg.on("dialog", lambda d: d.accept())
    pg.goto(B + path); pg.wait_for_load_state("networkidle")
    return b, c, pg
def shot(pg, name): 
    path = SHOTS / f"common_{name}.png"; pg.screenshot(path=str(path)); return str(path)
def tab_exec(pg):
    pg.click("#tab-exec"); pg.wait_for_timeout(300)
def open_add(pg, kind="exec"):
    pg.click(f'[data-add="{kind}"]:visible'); pg.wait_for_selector("#dlg[open]"); pg.wait_for_timeout(200)
def F(pg, k): return pg.locator(f'#dlg-fields [name="{k}"]')
def focused(pg): return pg.evaluate("document.activeElement && (document.activeElement.name || document.activeElement.id)")
def err(pg): 
    e = pg.locator("#dlg-error"); return e.inner_text() if e.is_visible() else None
def alert_text(pg):
    a = pg.locator("#alert"); return a.inner_text() if a.is_visible() else None
def toasts(pg):
    return pg.locator("#toasts .toast-msg").all_inner_texts() if pg.locator("#toasts").count() else []
def find_row(pg, no):
    pg.fill('[data-filter="q"][data-kind="exec"]', no); pg.wait_for_timeout(300)
    return pg.locator("#exec-table tbody tr", has_text=no).first
def confirm_ok(pg):
    if pg.locator("#dlg-confirm[open]").count():
        t = pg.locator("#confirm-body").inner_text(); pg.click("#confirm-ok"); pg.wait_for_timeout(600); return t
