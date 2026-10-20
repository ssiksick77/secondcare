from h import *
a=all_(); l=a['labor'][0]; print(l['연결거래번호'])
e=ex(l['연결거래번호']); row=e['_row']
base={k:v for k,v in e.items() if not k.startswith('_')}
chg={'재원':'QA02','예산목':'연구재료비','금액':99999,'거래처':'다른사람','원인발생일':'2026-01-26'}
for k,v in chg.items():
    r=dict(base); r[k]=v; print('PUT',k,'->',api('PUT',f'/api/exec/{row}',{'rec':r}))
r=dict(base); r['비고']='QA 비고 수정'; r['태그']='가상태그1'; print('PUT 비고/태그 (allowed?)',api('PUT',f'/api/exec/{row}',{'rec':r})[0])
print('DELETE exec',api('DELETE',f'/api/exec/{row}',{}))
print('batch update',api('POST','/api/exec/batch',{'creates':[],'updates':[{'row':row,'rec':{**base,'금액':1}}],'deletes':[]}))
# labor edit of confirmed
print('PUT labor confirmed', api('PUT','/api/labor/2',{'rec':{k:v for k,v in l.items() if not k.startswith('_')}|{'금액':1}}))
print('DELETE labor confirmed (before evidence):',end=' ')
# don't actually delete; skip
print('skipped')
# evidence
print('evidence entry:',api('POST',f'/api/evidence/{l["연결거래번호"]}/entry',{'kind':'영수증','note':'QA 실물'}))
print('unconfirm w/ evidence:',api('POST','/api/labor/2/action',{'action':'unconfirm'}))
print('exec still?',ex(l['연결거래번호']) is not None, 'labor state',all_()['labor'][0]['상태'])
print('DELETE exec w/ evidence',api('DELETE',f'/api/exec/{row}',{}))
print('DELETE labor w/ evidence', api('DELETE','/api/labor/2',{}))
ev=all_()['evidence']; print(ev)
