from h import *
from playwright.sync_api import sync_playwright
import subprocess
def pdf(n,tx):
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.add_init_script("window.print=function(){}"); pg.goto(B); pg.wait_for_timeout(1200)
        pg.click('#tab-exec'); pg.fill('[data-filter=q][data-kind=exec]',tx); pg.wait_for_timeout(300)
        pg.locator('#exec-table tr',has_text=tx).first.click(); pg.wait_for_timeout(500)
        pg.locator('#xd-body [data-act=voucher]').click(); pg.wait_for_timeout(700)
        pg.click('#voucher-print'); pg.wait_for_timeout(300)
        out=Q+rf'\inst_budget\dl\voucher_E005_ev{n}.pdf'; pg.pdf(path=out,format='A4',prefer_css_page_size=True,print_background=True); b.close(); return out
for k in range(6):
    r=requests.post(f'{B}/api/evidence/2026-QA01-005/entry',json={'증빙종류':'영수증','비고':f'B21 증빙{k+1}'}); 
    if k in(4,5):
        print('evid',k+1,r.status_code)
        o=pdf(k+1,'2026-QA01-005'); print(subprocess.run(['pdftotext','-layout',o,'-'],capture_output=True,text=True,encoding='utf-8').stdout.count('\f')+0,'formfeeds'); 
        t=subprocess.run(['pdftotext','-layout',o,'-'],capture_output=True,text=True,encoding='utf-8').stdout
        import re; print('pagenums',re.findall(r'\d/\d',t))
