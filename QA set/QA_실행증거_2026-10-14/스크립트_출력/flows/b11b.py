from h import *
print(json.dumps(json.load(open("C:/Users/parkj/Desktop/Project/01 in progress/CAIH_회계장부_2026/QA set/invalid_cases_NOT_SUBMITTED.json",encoding='utf-8'))[17],ensure_ascii=False)[:500])
n0=len(all_()['labor'])
body={"이름":"등록안된인원","지급처":"QA01","지급월":"2026-09","귀속월":"2026-09","금액":10000,"상태":"예정"}
print('X18 POST', api('POST','/api/labor',body), 'count delta', len(all_()['labor'])-n0)
# unconfirm via UI later. First: confirm w/o pay_date
print('confirm row 9 no date (default today?):', api('POST','/api/labor/9/action',{'action':'confirm'}))
print('confirm row 9 again:', api('POST','/api/labor/9/action',{'action':'confirm','pay_date':'2026-10-13'}))
print('bad date:', api('POST','/api/labor/10/action',{'action':'confirm','pay_date':'2026-13-45'}))
print('confirm L2-07 外部:', api('POST','/api/labor/17/action',{'action':'confirm','pay_date':'2026-10-12'}))
a=all_(); print([ (e['거래번호'],e['재원'],e['예산목'],e['거래처'],e['금액'],e['결제수단'],e['원인발생일'],e['지급청구일'],e['지출완료일'],e['결의일'],e['적요']) for e in a['exec'] if e['세목']=='인건비' and e['원인발생일']>='2026-10-01'])
