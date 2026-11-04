from playwright.sync_api import sync_playwright
import sys
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_context(viewport={'width':1500,'height':950}).new_page()
    pg.goto('http://127.0.0.1:8813/labor'); pg.wait_for_timeout(1500)
    pg.screenshot(path='../shots/flows_dbg.png')
    print([t for t in pg.locator('[role=tab]').all_inner_texts()])
    print(pg.locator('button[data-labor]').count(), pg.locator('button[data-cell]').count())
    b.close()
