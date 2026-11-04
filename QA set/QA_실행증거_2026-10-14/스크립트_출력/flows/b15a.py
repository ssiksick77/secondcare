from h import *
def mk(item,sup,price=10000,qty=1,code='QA-SKU-X'):
    return api('POST','/api/request',{'구분':'소모품','신청인':'가상신청인1','신청일':'2026-10-14','관련과제':'QA05','품목':item,'단가':price,'수량':qty,'금액':price*qty,'부가세구분':'N','부가세액':0,'구매처':sup,'상품코드':code,'사유':'QA B-15'})
for it,sup,p in [('QA소모A1','알파몰',10000),('QA소모A2','알파몰',20000),('QA소모B1','가상문구B',30000)]:
    s,j=mk(it,sup,p); print(s, j.get('신청번호') if isinstance(j,dict) else j, j.get('상태') if isinstance(j,dict) else '')
s,j=mk('QA소모 드림','드림디포'); print('드림디포 신청:',s,j)
a=all_(); print([ (r['신청번호'],r['구매처'],r['상태']) for r in a['request'] if r['품목'].startswith('QA소모')])
