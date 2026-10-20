from h import *
from playwright.sync_api import sync_playwright
d=all_()
tab=d['dashboard']['table']
print('API funds',d['dashboard']['funds'])
print('API table rows ZZ99/기타:',[t for t in tab if t['재원']=='ZZ99' or t['예산목']=='기타비목'])
print('API sum 집행(재원별 소계 제외?)',len(tab), sum(t['집행액'] for t in tab if t.get('예산목')))
print('rows 재원 set',sorted({t['재원'] for t in tab}))
print('exec total from /api/all',sum(e['금액'] or 0 for e in d['exec']), 'count',len(d['exec']))
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.goto(B); pg.wait_for_timeout(1200)
    print('NOTE',pg.inner_text('#dash-note'))
    pg.screenshot(path=SH+'B04_excluded_dash.png',full_page=True)
    pg.click('[data-act=show-excluded]'); pg.wait_for_timeout(500)
    print('EXCL LIST',pg.inner_text('#exec-table')); print(pg.inner_text('#exec-sum')); print(pg.inner_text('#alert'))
    pg.screenshot(path=SH+'B04_excluded_list.png',full_page=True)
    pg.click('#tab-dash'); pg.select_option('#dash-fund','QA09'); pg.wait_for_timeout(300); print('QA09 NOTE',pg.inner_text('#dash-note'))
    pg.select_option('#dash-fund','ZZ99') if 'ZZ99' in [o.inner_text() for o in pg.query_selector_all('#dash-fund option')] else print('ZZ99 not in dash fund dropdown')
    print('exec fund options',[o.inner_text() for o in pg.query_selector_all('[data-filter=재원][data-kind=exec] option')])
    b.close()
