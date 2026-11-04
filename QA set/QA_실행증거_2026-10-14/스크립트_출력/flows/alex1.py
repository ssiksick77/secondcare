from h import *
# external payee
print('payee:',api('POST','/api/payee',{'지급처코드':'EXTA','지급처명':'외부기관A(위탁)','비고':'QA'}))
print(all_()['payee'])
s,j=api('POST','/api/labor',{'이름':'가상연구원02','지급처':'EXTA','지급월':'2026-10','귀속월':'2026-10','금액':50000,'상태':'예정'}); print('labor ext',s,j)
row=j['_row']
print('confirm',api('POST',f'/api/labor/{row}/action',{'action':'confirm','pay_date':'2026-10-12'}))
a=all_(); print([ (e['거래번호'],e['재원'],e['예산목'],e['금액']) for e in a['exec'] if e['재원']=='EXTA'])
d=a['dashboard']; print(d.keys())
print({k:v for k,v in d.items() if k not in('table','funds','monthly')})
