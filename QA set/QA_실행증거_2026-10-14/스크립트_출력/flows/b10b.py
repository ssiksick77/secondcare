from pw import *
from h import *
from b10a import dump
def f(pg):
    pg.get_by_role('tab',name='적립금').click(); pg.wait_for_timeout(600)
    pg.locator('button[data-act="dep-use"][data-vendor="신규거래처V"]').click(); pg.wait_for_timeout(500)
    pg.fill('#f-일자','2026-10-14'); pg.fill('#f-금액','100000')
    print('tag visible in new 사용 form:', pg.locator('#f-태그').is_visible())
    pg.click('#dlg-save'); pg.wait_for_timeout(1000)
    dump('after 사용(no tag)')
    # edit
    pg.locator('tr[data-kind="deposit"]:has-text("100,000"):has-text("신규거래처V") button[data-act="edit"]').click(); pg.wait_for_timeout(500)
    print('tag visible in edit form:', pg.locator('#f-태그').is_visible())
    pg.select_option('#f-태그','가상태그1'); pg.screenshot(path=S+'flows_B10_3_use_edit_tag.png')
    pg.click('#dlg-save'); pg.wait_for_timeout(1000)
    dump('after tag edit')
    pg.get_by_role('tab',name='적립금').click(); pg.screenshot(path=S+'flows_B10_4_after_use.png')
run(f)
