from h import *
a=all_(); q=[r for r in a['req'] if '신청 R-2026-001' in (r['비고'] or '')][0]
def tot(): 
    a=all_(); return sum(e['금액'] for e in a['exec'] if e['재원']=='QA05'), sum(d['금액']*(1 if d['구분']=='적립' else -1) for d in a['deposit'] if d['거래처']=='가상문구A')
print('QA05 exec total / depA balance before:',tot(), 'req',q['품의번호'],q['금액'],q['상태'])
s,j=api('POST',f"/api/req/{q['_row']}/to-exec",{'extra':{'거래처':'가상문구A','결제수단':'적립금'}}); print(s, {k:j.get(k) for k in ['거래번호','금액','재원','예산목','결제수단','비고']} if s==200 else j)
print('after:',tot())
a=all_(); print('dep rows A:',[(d['구분'],d['금액'],d['적요']) for d in a['deposit'] if d['거래처']=='가상문구A'])
