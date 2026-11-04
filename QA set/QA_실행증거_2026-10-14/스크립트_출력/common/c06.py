from ui import *
Q = '[data-filter="q"][data-kind="exec"]'
def rows(pg):
    trs = pg.locator("#exec-table tbody tr")
    out = []
    for i in range(trs.count()):
        t = trs.nth(i).inner_text()
        out.append(t.split("\t")[0].strip())
    return out
def summ(pg): return pg.locator("#exec-sum").inner_text()
d = all_()
def api_count(pred): return len([r for r in d["exec"] if pred(r)])
with sync_playwright() as p:
    b, c, pg = open_page(p); tab_exec(pg)
    print("initial", len(rows(pg)), summ(pg))
    for q in ["150,000", "150000", "11,000", "11000", "100,000", "100000", "1,000", "1000"]:
        pg.fill(Q, q); pg.wait_for_timeout(400); r = rows(pg); print(f"q={q!r}: n={len(r)} sum={summ(pg)!r} first={r[:4]}")
    print("api: 금액==150000:", api_count(lambda r: r['금액'] == 150000), " 금액==11000:", api_count(lambda r: r['금액'] == 11000), " 금액==100000:", api_count(lambda r: r['금액']==100000))
    pg.fill(Q, "150,000"); pg.wait_for_timeout(300); shot(pg, "C-06_search_150000")
    # combination
    pg.fill(Q, ""); pg.select_option('[data-filter="재원"][data-kind="exec"]', "QA01"); pg.select_option('[data-filter="year"][data-kind="exec"]', "2026"); pg.select_option('[data-filter="month"][data-kind="exec"]', "03"); pg.wait_for_timeout(400)
    r = rows(pg); exp = [x["거래번호"] for x in d["exec"] if x["재원"] == "QA01" and x["원인발생일"][:7] == "2026-03"]
    print("QA01+2026-03 UI:", sorted(r), "\n  API expected:", sorted(exp), "match:", sorted(r) == sorted(exp)); shot(pg, "C-06_combo")
    pg.fill(Q, "11,000"); pg.wait_for_timeout(300); r = rows(pg); print("QA01+03 + '11,000':", r)
    pg.fill(Q, "존재하지않는검색어ZZZ"); pg.wait_for_timeout(400); r = rows(pg); print("empty search rows:", r, "sum:", summ(pg)); shot(pg, "C-06_empty")
    print("table text:", pg.locator("#exec-table").inner_text()[:200].replace("\n", " | "))
    # reset
    pg.fill(Q, ""); 
    for k in ["재원", "year", "month"]: pg.select_option(f'[data-filter="{k}"][data-kind="exec"]', "")
    pg.wait_for_timeout(400); print("after reset:", len(rows(pg)), summ(pg), "api total", len(d["exec"]))
    # does filter persist after tab switch / reload?
    pg.select_option('[data-filter="재원"][data-kind="exec"]', "QA02"); pg.wait_for_timeout(200); pg.click("#tab-dash"); pg.wait_for_timeout(200); tab_exec(pg)
    print("after tab switch, 재원 filter:", pg.locator('[data-filter="재원"][data-kind="exec"]').input_value(), len(rows(pg)))
    # month filter only (no year)
    pg.select_option('[data-filter="재원"][data-kind="exec"]', ""); pg.select_option('[data-filter="month"][data-kind="exec"]', "09"); pg.wait_for_timeout(300)
    print("month=09 only:", len(rows(pg)), "api:", api_count(lambda r: r['원인발생일'][5:7]=='09'))
    # search on 거래번호 partial, tag
    pg.select_option('[data-filter="month"][data-kind="exec"]', ""); pg.fill(Q, "가상태그2"); pg.wait_for_timeout(300); print("tag search:", len(rows(pg)), "api:", api_count(lambda r: r['태그']=='가상태그2'))
    pg.fill(Q, "-500"); pg.wait_for_timeout(300); print("'-500' search:", rows(pg)[:5])
    b.close()
