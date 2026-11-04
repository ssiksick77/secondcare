from h import *
from playwright.sync_api import sync_playwright
def cnt(): 
    d=all_(); return len(d['exec']), sum(e['금액'] for e in d['exec'] if e['재원']=='QA01'), sum(e['금액'] for e in d['exec'] if e['재원']=='QA08')
cases=[('dup',dict(재원='QA01',예산목='연구시설.장비비',원인발생일='2026-01-05',거래처='가상거래처02',금액='15000',적요='B08 중복')),
       ('neg',dict(재원='QA01',예산목='연구활동비',원인발생일='2026-09-20',거래처='B08음수',금액='-1',적요='B08 음수')),
       ('over',dict(재원='QA08',예산목='연구활동비',원인발생일='2026-09-20',거래처='B08초과',금액='1',적요='B08 초과'))]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1500,'height':1000}); pg.goto(B); pg.wait_for_timeout(1200)
    pg.click('#tab-exec')
    for name,c in cases:
        for mode in ('cancel','ok'):
            before=cnt()
            pg.click('[data-add=exec]'); pg.wait_for_timeout(400)
            for k,v in c.items():
                el=pg.locator(f'#dlg-fields [name={k}]')
                if el.evaluate('e=>e.tagName')=='SELECT': el.select_option(v)
                else: el.fill(v)
            pg.click('#dlg-save'); pg.wait_for_timeout(700)
            vis=pg.is_visible('#dlg-confirm')
            txt=pg.inner_text('#dlg-confirm') if vis else ''
            print(name,mode,'confirm shown:',vis,'| TEXT:',txt.replace('\n',' / '),'| err:',pg.inner_text('#dlg-error') if pg.is_visible('#dlg-error') else '-')
            if vis and mode=='cancel': pg.screenshot(path=SH+f'B08_{name}_warn.png')
            if vis:
                pg.click('#confirm-cancel' if mode=='cancel' else '#confirm-ok'); pg.wait_for_timeout(800)
            if mode=='cancel':
                print('  after cancel dialog open:',pg.is_visible('#dlg'),'counts',before,'->',cnt())
                # close form discarding
                if pg.is_visible('#dlg'):
                    pg.click('#dlg-cancel'); pg.wait_for_timeout(300)
                    if pg.is_visible('#dlg-confirm'): pg.click('#confirm-ok'); pg.wait_for_timeout(300)
            else:
                print('  after ok dialog open:',pg.is_visible('#dlg'),'counts',before,'->',cnt())
                if pg.is_visible('#dlg'):
                    pg.click('#dlg-cancel'); pg.wait_for_timeout(300)
                    if pg.is_visible('#dlg-confirm'): pg.click('#confirm-ok'); pg.wait_for_timeout(300)
    b.close()
