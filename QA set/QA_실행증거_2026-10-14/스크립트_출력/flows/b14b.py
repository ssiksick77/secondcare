from h import *
def rq(no): return next(r for r in all_()['request'] if r['신청번호']==no)
r=rq('R-2026-008'); row=r['_row']; rec={k:v for k,v in r.items() if not k.startswith('_')}
x=dict(rec); x['단가']=12000; x['금액']=12000
s,j=api('PUT',f'/api/request/{row}',{'rec':x,'extra':{'keep_approval':True}}); print('keep_approval:',s,j.get('상태'),j.get('reapproval'),j.get('결재인'),j.get('금액'))
x=dict(rec); x['단가']=13000; x['금액']=13000
s,j=api('PUT',f'/api/request/{row}',{'rec':x}); print('amount w/o keep:',s,j.get('상태'),j.get('reapproval'),repr(j.get('결재인')),j.get('결재일'))
print('approve again',api('POST',f'/api/request/{row}/action',{'action':'approve'})[1].get('상태'))
x=dict(rec); x['단가']=13000;x['금액']=13000; x['사유']='사유만 변경'; x['규격']='규격변경'
s,j=api('PUT',f'/api/request/{row}',{'rec':x}); print('사유+규격 change:',s,j.get('상태'),j.get('reapproval'))
