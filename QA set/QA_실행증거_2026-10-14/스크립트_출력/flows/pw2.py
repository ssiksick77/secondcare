from playwright.sync_api import sync_playwright
import sys
sys.stdout.reconfigure(encoding='utf-8')
S='../shots/'
def run(fn, admin=True):
    with sync_playwright() as p:
        b=p.chromium.launch(); c=b.new_context(viewport={'width':1500,'height':950}); pg=c.new_page()
        pg.on('dialog', lambda d: d.accept())
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('http://127.0.0.1:8813/'); pg.wait_for_timeout(1200)
        if admin:
            pg.get_by_role('button',name='신청',exact=True).click(); pg.wait_for_timeout(1200)
        try: fn(pg)
        finally:
            if errs: print('PAGEERRORS',errs)
            b.close()
