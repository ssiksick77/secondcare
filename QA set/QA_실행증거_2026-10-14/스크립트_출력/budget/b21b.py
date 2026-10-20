from h import *
from playwright.sync_api import sync_playwright
import re
d=all_()
G=[("인건비",["내부인건비(공통)","외부인건비(공통)"]),("연구시설·장비비",["연구시설.장비비"]),("연구재료비",["연구재료비"]),("위탁연구개발비",["위탁연구개발비"]),("국제공동연구개발비",["국제공동연구개발비"]),("연구개발부담비",["연구개발부담비"]),("연구활동비",["연구활동비"]),("연구수당",["연구수당"]),("간접비",["간접비(공통)"])]
def indep(tx):
    t=[e for e in d['exec'] if e['거래번호']==tx][0]
    f=t['재원']; bud=lambda i:sum((b.get(i) or 0) for b in d['budget'] if b['재원']==f)
    ex=[e for e in d['exec'] if e['재원']==f and ((e['원인발생일'] or '',e['_row'])<=(t['원인발생일'] or '',t['_row']))]
    out=[]
    for lab,its in G:
        after=sum(bud(i)-sum(e['금액'] for e in ex if e['예산목']==i) for i in its)
        own=t['예산목'] in its; cur=t['금액'] if own else 0
        out.append((lab,after+cur,cur if own else None,after))
    return out,t
def run(pg,tx,tag):
    exp,t=indep(tx)
    pg.click('#tab-exec'); pg.select_option('[data-filter=재원][data-kind=exec]',t['재원']); pg.select_option('[data-filter=month][data-kind=exec]',''); pg.fill('[data-filter=q][data-kind=exec]',tx); pg.wait_for_timeout(400)
    pg.locator('#exec-table tr',has_text=tx).first.click(); pg.wait_for_timeout(500)
    btn=pg.locator('#xd-body [data-act=voucher]')
    print(tag,tx,'button count',btn.count(),'disabled',btn.first.is_disabled() if btn.count() else None,'title',btn.first.get_attribute('title') if btn.count() else None)
    return exp,t,btn
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1500,'height':1000},accept_downloads=True); pg=ctx.new_page()
    pg.add_init_script("window.__printed=0; window.print=function(){window.__printed++};")
    pg.goto(B); pg.wait_for_timeout(1200)
    # unapproved
    exp,t,btn=run(pg,'2026-QA01-001','UNAPPROVED(E001)')
    pg.screenshot(path=SH+'B21_voucher_btn_disabled.png')
    pg.hover('#xd-body [data-act=voucher]',force=True)
    pg.click('#xd-close')
    for tx in ['2026-QA01-005','2026-QA01-004']:
        exp,t,btn=run(pg,tx,'APPROVED')
        btn.click(); pg.wait_for_timeout(800)
        sheet=pg.inner_text('#voucher-sheet'); 
        pg.screenshot(path=SH+f'B21_voucher_{tx[-10:]}.png',full_page=False)
        print(sheet[:1800])
        # parse fund table rows
        rows=pg.eval_on_selector_all('#voucher-sheet table.vc-fund tbody tr','trs=>trs.map(tr=>[...tr.children].map(c=>c.innerText.trim()))')
        print('UI fund rows',rows)
        nm=lambda s:int(re.sub(r'[^\d\-]','',s.replace('−','-').replace('+','')) or 0) if s not in('-','') else None
        ok=True
        for (lab,bef,cur,aft),r in zip(exp,rows[:9]):
            ub,ua=nm(r[1]),nm(r[3]); uc=r[2]
            good=(ub==bef and ua==aft)
            if not good: ok=False; print('  MISMATCH',lab,(bef,cur,aft),r)
        print('independent calc:',exp); print('ALL LINES MATCH' if ok else 'SOME MISMATCH')
        if tx.endswith('005'):
            pg.click('#voucher-print'); pg.wait_for_timeout(500); print('print called',pg.evaluate('window.__printed'),'body class',pg.evaluate('document.body.className'))
            pg.pdf(path=Q+r'\inst_budget\dl\voucher_E005.pdf',format='A4',prefer_css_page_size=True,print_background=True)
        pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
        pg.click('#xd-close')
    b.close()
