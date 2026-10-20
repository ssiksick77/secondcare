from pw import *
from h import *
def f(pg):
    pg.get_by_role('tab',name='대시보드').click(); pg.wait_for_timeout(500)
    pg.locator('#sub-tags').click(); pg.wait_for_timeout(700)
    print(pg.locator('#tag-note').inner_text()); print(pg.locator('#tag-recon').inner_text())
    print(pg.locator('#panel-dash #dash-tags table').first.inner_text().replace('\n',' | ')[:800])
    pg.screenshot(path=S+'flows_B10_5_tag_dash.png')
run(f)
a=all_(); linked={d['연결거래번호'] for d in a['deposit'] if d['연결거래번호']}
for t in ['가상태그1','가상태그2','가상태그3']:
    ex_=sum(e['금액'] for e in a['exec'] if e['태그']==t and e['거래번호'] not in linked)
    dp=sum(d['금액'] for d in a['deposit'] if d['구분']=='사용' and d['태그']==t)
    print(t,'exec(non-linked)',ex_,'dep use',dp,'total',ex_+dp)
print('V balance', sum((1 if d['구분']=='적립' else -1)*d['금액'] for d in a['deposit'] if d['거래처']=='신규거래처V'))
print('exec V count', [e['거래번호'] for e in a['exec'] if e['거래처']=='신규거래처V'])
