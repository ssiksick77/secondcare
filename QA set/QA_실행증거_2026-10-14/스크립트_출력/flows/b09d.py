from h import *
e=ex('2026-QA01-001'); row=e['_row']
rec={k:v for k,v in e.items() if not k.startswith('_')}
# (a) API clear 청구일 while 완료일 exists
r=dict(rec); r['지급청구일']=''
print('PUT clear 청구일 w/ 완료일:',api('PUT',f'/api/exec/{row}',{'rec':r}))
e2=ex('2026-QA01-001'); print('   now:',e2['상태'],e2['지급청구일'],e2['지출완료일'],e2['결의일'])
# restore
r=dict(rec); r['지급청구일']=rec['지급청구일']
print('restore',api('PUT',f'/api/exec/{row}',{'rec':r})[0])
# (b) API: set 결의일 with 지출완료일 empty
r=dict(rec); r['지출완료일']=''; r['결의일']='2026-10-14'
print('PUT 결의일 w/o 완료일:',api('PUT',f'/api/exec/{row}',{'rec':r}))
e2=ex('2026-QA01-001'); print('   now:',e2['상태'],e2['지급청구일'],e2['지출완료일'],e2['결의일'])
