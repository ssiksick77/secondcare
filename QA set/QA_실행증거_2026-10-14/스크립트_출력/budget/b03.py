from h import *
from playwright.sync_api import sync_playwright
items=['내부인건비(공통)','외부인건비(공통)','연구시설.장비비','연구활동비','연구재료비','연구수당','위탁연구개발비','국제공동연구개발비','연구개발부담비','간접비(공통)','발생이자']
d={'재원':'QA10','변경회차':2,'신청일자':'2026-01-02','변경사유':'B03 보정'}
for it in items: d[it]=0
d['연구활동비']=100000
print(show(requests.post(B+'/api/budget',json=d)))
def shot(name):
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.goto(B); pg.wait_for_timeout(1200)
        pg.select_option('#dash-fund','QA10'); pg.wait_for_timeout(400)
        print(name,'NOTE',pg.inner_text('#dash-note'))
        print(pg.inner_text('#dash-table'))
        pg.screenshot(path=SH+name,full_page=True); 
        pg.click('#tab-exec'); pg.select_option('[data-filter=재원][data-kind=exec]','QA10'); pg.wait_for_timeout(400)
        print('EXEC',pg.inner_text('#exec-table')); print(pg.inner_text('#exec-sum'))
        b.close()
e1={'재원':'QA10','예산목':'연구활동비','원인발생일':'2026-03-02','금액':100000,'적요':'B03 집행1','거래처':'B03거래처'}
r=requests.post(B+'/api/exec',json=e1); print(show(r))
shot('B20_after_first_exec.png')
e2={**e1,'원인발생일':'2026-03-05','금액':250000,'적요':'B03 집행2'}
print(show(requests.post(B+'/api/exec',json=e2)))
q={'재원':'QA10','예산목':'연구활동비','원인발생일':'2026-03-10','금액':200000,'적요':'B03 품의','거래처':'B03거래처'}
print(show(requests.post(B+'/api/req',json=q)))
shot('B03_dash.png')
for t in all_()['dashboard']['table']:
    if t['재원']=='QA10' and t['예산목']=='연구활동비': print(t)
