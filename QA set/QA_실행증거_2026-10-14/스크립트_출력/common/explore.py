from ui import *
with sync_playwright() as p:
    b, c, pg = open_page(p)
    tab_exec(pg); open_add(pg)
    print("focus:", focused(pg))
    print(pg.locator("#dlg-fields").inner_text()[:800])
    print([ (el.get_attribute("name"), el.evaluate("e=>e.tagName"), el.input_value()) for el in pg.locator("#dlg-fields input, #dlg-fields select").all()])
    print(pg.locator('#dlg-fields [name="재원"] option').all_inner_texts())
    shot(pg, "explore_execform")
    b.close()
