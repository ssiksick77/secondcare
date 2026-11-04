from h import *
from playwright.sync_api import sync_playwright
import csv
d=all_()
sel=[e for e in d['exec'] if e['재원']=='QA03' and (e['원인발생일'] or '')[:7]=='2026-03']
print('API filter QA03 2026-03:',len(sel),sum(e['금액'] for e in sel),[e['거래번호'] for e in sel])
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000},accept_downloads=True); pg.goto(B); pg.wait_for_timeout(1200)
    pg.click('#tab-exec'); pg.select_option('[data-filter=재원][data-kind=exec]','QA03'); pg.select_option('[data-filter=year][data-kind=exec]','2026'); pg.select_option('[data-filter=month][data-kind=exec]','03'); pg.wait_for_timeout(300)
    print('UI sum',pg.inner_text('#exec-sum'))
    with pg.expect_download() as dl: pg.click('[data-csv=exec]')
    path=Q+r'\inst_budget\dl\exec_QA03_2026-03.csv'; dl.value.save_as(path); print('file',dl.value.suggested_filename)
    rows=list(csv.reader(open(path,encoding='utf-8-sig')))
    print(rows[0]); print('data rows',len(rows)-1)
    i=rows[0].index('금액'); print('sum',sum(float(r[i]) for r in rows[1:]))
    print('CSV tx numbers',[r[0] for r in rows[1:]])
    print('상태 values',[r[rows[0].index('상태')] for r in rows[1:]])
    for r in rows[1:3]: print(r)
    # dashboard CSV QA03 2026
    pg.click('#tab-dash'); pg.select_option('#dash-fund','QA03'); pg.select_option('#dash-month','03'); pg.wait_for_timeout(300)
    with pg.expect_download() as dl: pg.click('#dash-csv')
    path2=Q+r'\inst_budget\dl\dash_QA03_2026-03.csv'; dl.value.save_as(path2); print('file',dl.value.suggested_filename)
    print(open(path2,encoding='utf-8-sig').read()[:900])
    print('UI dash table:',pg.inner_text('#dash-table')[:500])
    # all funds, month 3 dashboard csv
    pg.select_option('#dash-fund',''); pg.wait_for_timeout(300)
    with pg.expect_download() as dl: pg.click('#dash-csv')
    path3=Q+r'\inst_budget\dl\dash_ALL_2026-03.csv'; dl.value.save_as(path3); rows=list(csv.reader(open(path3,encoding='utf-8-sig'))); print('ALL csv rows',len(rows),rows[0],rows[1]); print([r for r in rows if r[1]=='' or r[1]=='소계'][:3])
    b.close()
