from pw import *
from h import *
e=ex('2026-QA01-019'); row=e['_row']
def f(pg):
    pg.click(f'tr[data-kind="exec"][data-row="{row}"] td[data-col="재원"]'); pg.wait_for_timeout(700)
    pg.screenshot(path=S+'flows_B12_1_drawer_labor_linked.png')
    d=pg.locator('#exec-drawer button[data-act="del"]'); print('drawer del disabled',d.is_disabled(),d.get_attribute('title'))
    pg.locator('#exec-drawer button[data-act="edit"]').click(); pg.wait_for_timeout(600)
    for k in ['재원','예산목','금액','거래처','원인발생일','세목','태그','비고']:
        el=pg.locator(f'#f-{k}')
        print(k,'readonly' ,el.get_attribute('readonly'),'class',el.get_attribute('class'),'title',el.get_attribute('title'))
    print('dlg-error:',pg.locator('#dlg-error').inner_text())
    pg.screenshot(path=S+'flows_B12_2_edit_dialog_lock.png')
    # try changing 예산목 select
    pg.select_option('#f-예산목','연구재료비'); pg.wait_for_timeout(300)
    print('예산목 value after try:', pg.locator('#f-예산목').input_value())
    print([x for x in pg.locator('[role=alert],[role=status],.toast').all_inner_texts() if x])
    pg.fill('#f-금액','5000'); print('금액 value', pg.locator('#f-금액').input_value())
run(f)
