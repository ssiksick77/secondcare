from h import *
items=['내부인건비(공통)','외부인건비(공통)','연구시설.장비비','연구활동비','연구재료비','연구수당','위탁연구개발비','국제공동연구개발비','연구개발부담비','간접비(공통)','발생이자']
def nr(f): return requests.get(B+'/api/budget/next-round',params={'fund':f}).json()
print('next QA10 initial',nr('QA10'),'QA01',nr('QA01'),'QA09',nr('QA09'),'none',requests.get(B+'/api/budget/next-round').json())
def rec(rnd,base,date='2026-01-01'):
    d={'재원':'QA10','변경회차':rnd,'신청일자':date,'변경사유':'B01'}
    for i,it in enumerate(items): d[it]=base+i*1000
    return d
# 연구활동비 index3
def mk(rnd,act,others):
    d={'재원':'QA10','변경회차':rnd,'신청일자':'2026-01-01','변경사유':'B01'}
    for i,it in enumerate(items): d[it]=others+i*1000
    d['연구활동비']=act; return d
for rnd,act,oth in [('이월',100000,10000),('당초',900000,20000),(1,-100000,-5000)]:
    r=requests.post(B+'/api/budget',json=mk(rnd,act,oth)); print(rnd,show(r))
    print(' next',nr('QA10'))
# duplicates
for rnd in ['이월','당초',1,'1']:
    r=requests.post(B+'/api/budget',json=mk(rnd,5,5)); print('DUP',rnd,show(r))
d=all_()
print([ (b['_row'],b['변경회차'],b['연구활동비']) for b in d['budget'] if b['재원']=='QA10'])
for t in d['dashboard']['table']:
    if t['재원']=='QA10': print(t)
