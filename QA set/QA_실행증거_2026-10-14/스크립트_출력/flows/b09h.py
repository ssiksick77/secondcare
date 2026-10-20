from pw import *
def f(pg):
    for r in (3,4,5,6):
        print(r, pg.locator(f'tr[data-kind="exec"][data-row="{r}"] td.st-cell').inner_text().replace('\n',' / '))
    pg.locator('tr[data-kind="exec"][data-row="3"]').scroll_into_view_if_needed()
    pg.screenshot(path=S+'flows_B09_14_status_labels.png')
    print([t for t in pg.locator('.tiles, .tile, [data-quick]').all_inner_texts()][:10])
run(f)
