from h import *
a=all_()
# new order for override test using R-2026-001/002 (가상문구A) -> reproduces ORDER1 30000->28000 with deposit
m={r['신청번호']:r for r in a['request']}
s,j=api('POST','/api/order/create',{'rows':[m['R-2026-001']['_row'],m['R-2026-002']['_row']],'extra':{'주문일':'2026-10-14','결제금액':28000,'적립금사용':'Y'}})
print(s,j['order']['주문번호'],j['deposit'] and (j['deposit']['금액'],j['deposit']['적요']),j['warnings'])
rows=[m['R-2026-001']['_row'],m['R-2026-002']['_row']]
print('convert amount 29000 w/o override:',api('POST','/api/request/convert',{'rows':rows,'extra':{'금액':29000,'재원':'QA05','예산목':'연구재료비'}}))
s,j=api('POST','/api/request/convert',{'rows':rows,'extra':{'재원':'QA05','예산목':'연구재료비'}}); print('default:',s,j['req']['금액'],j['req']['거래처'],j['order'])
