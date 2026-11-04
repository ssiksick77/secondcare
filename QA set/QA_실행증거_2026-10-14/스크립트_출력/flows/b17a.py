from h import *
ids=[]
for it,p in [('QA주문품X1',60000),('QA주문품X2',40000)]:
    s,j=api('POST','/api/request',{'구분':'소모품','신청인':'가상신청인1','신청일':'2026-10-14','관련과제':'QA05','품목':it,'단가':p,'수량':1,'금액':p,'부가세구분':'N','부가세액':0,'구매처':'알파몰','상품코드':'QA-X','사유':'QA B-17'})
    print(s,j['신청번호']); ids.append(j)
for j in ids: print(api('POST',f"/api/request/{j['_row']}/action",{'action':'approve'})[1].get('상태'))
s,j=api('POST','/api/order/create',{'rows':[x['_row'] for x in ids],'extra':{'주문일':'2026-10-14','결제금액':95000,'적립금사용':'N'}})
print(s,json.dumps(j,ensure_ascii=False)[:600])
ono=j['order']['주문번호']
rows=[x['_row'] for x in ids]
# partial convert attempt via API
a=all_()['request']; m={r['신청번호']:r for r in a}
print('partial convert:',api('POST','/api/request/convert',{'rows':[ids[0]['_row']],'extra':{}}))
# mixed w/ other-order
print('convert across orders:',api('POST','/api/request/convert',{'rows':[ids[0]['_row'],m['R-2026-018']['_row']],'extra':{}}))
print('order unchanged reqs:',[(r['신청번호'],r['상태'],r['연결품의번호']) for r in all_()['request'] if r['주문번호']==ono])
print(ono)
