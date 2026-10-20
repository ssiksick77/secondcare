from h import *
from playwright.sync_api import sync_playwright
import re
d=all_()
exp={}
for e in d['exec']: exp.setdefault(e['재원'],[0,0]); exp[e['재원']][0]+=1; exp[e['재원']][1]+=e['금액']
print('names',[(f['재원코드'],f['과제명']) for f in d['funds']])
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.goto(B); pg.wait_for_timeout(1200)
    print('fund dropdown option texts:',[o.inner_text() for o in pg.query_selector_all('[data-filter=재원][data-kind=exec] option')])
    pg.click('#tab-exec')
    for i in range(1,11):
        f='QA%02d'%i
        pg.select_option('[data-filter=재원][data-kind=exec]',f); pg.wait_for_timeout(250)
        s=pg.inner_text('#exec-sum')
        rows=pg.locator('#exec-table tbody tr').count()
        funds_in_rows=set(re.findall(r'\bQA\d\d\b',pg.inner_text('#exec-table')))
        n=int(re.search(r'(\d+)건',s).group(1)); amt=int(re.search(r'합계 ([\d,\-]+)원',s).group(1).replace(',',''))
        ok=(n,amt)==tuple(exp[f]) and funds_in_rows<={f}
        print(f,'UI',s,'exp',exp[f],'rowfunds',funds_in_rows,'OK' if ok else 'MISMATCH')
        if f in('QA01','QA02'): pg.screenshot(path=SH+f'B02_exec_{f}.png',full_page=False)
    b.close()
