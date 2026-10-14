"""Deterministic synthetic fixture. Builds an isolated app database; never submits invalid cases.
Run with the app's Python dependencies. install_fixture.py performs guarded deployment separately.
"""
from pathlib import Path
import sys, os, json, hashlib, shutil, datetime as dt
from collections import defaultdict, Counter
from copy import deepcopy

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
APP = ROOT / 'app'
sys.path.insert(0, str(APP))
import main
import store
from fastapi.testclient import TestClient
from openpyxl import Workbook

RUN = 'QA26JANSEP_V1'
MARK = '[가상 QA26JANSEP_V1]'
STAGE = OUT / 'synthetic_baseline.xlsx'
def dump(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def build():
    if (OUT/'installed.json').exists():
        raise SystemExit('Already installed; build refused. Use documented snapshot restoration, not append.')
    target = store.XLSX_PATH.resolve()
    if not target.is_relative_to(ROOT.resolve()):
        raise SystemExit('Configured ledger is outside the named project; no mutation allowed.')
    original_hash = sha(target)
    # Empty application-native database. No original cells, comments, properties or data are copied.
    wb = Workbook(); wb.remove(wb.active)
    for kind, (sheet, cols, head, key) in store._SHEETS.items():
        ws=wb.create_sheet(sheet)
        for c, name in enumerate(cols,1): ws.cell(head,c,name)
        ws.freeze_panes=f'A{head+1}'
    wb.save(STAGE)
    store.XLSX_PATH=STAGE
    store.BACKUP_DIR=OUT/'build_backups'
    os.environ['REQUEST_SUPPLIERS']='가상문구A,가상문구B'
    os.environ['REQUEST_SUPPLIERS_OFF']=''
    client=TestClient(main.app)
    calls=[]; refs=[]; grouped={'basic':[], 'valid_boundary':[]}
    expected_exec=[]; expected_budget=[]; expected_req=[]; expected_dep=[]
    def call(path, body, sid, group='basic'):
        response=client.post(path,json=deepcopy(body))
        if response.status_code!=200:
            raise RuntimeError(f'{sid} {path}: {response.status_code} {response.text}')
        value=response.json()
        calls.append({'scenario_id':sid,'method':'POST','path':path,'body':deepcopy(body),'status':response.status_code})
        return value
    def add(kind, rec, sid, group='basic'):
        result=call('/api/'+kind,rec,sid,group)
        keys=store.IDENT_COLS.get(kind,[])
        ident={k:result.get(k) for k in keys}
        refs.append({'scenario_id':sid,'group':group,'kind':kind,'row_at_baseline':result['_row'],'identifier':ident})
        grouped[group].append({'scenario_id':sid,'kind':kind,'input':deepcopy(rec),'identifier':ident})
        return result
    def ex(rec,sid,group='basic'):
        result=add('exec',rec,sid,group)
        expected_exec.append(deepcopy(rec)); return result
    items=list(store.BUDGET_ITEMS)
    for i in range(1,11):
        name=f'{MARK} 가상과제 {i:02}'
        if i in (1,2): name=f'{MARK} 가상영상연구 {"A" if i==1 else "A-후속"}'
        add('funds',{'재원코드':f'QA{i:02}','과제명':name,'시작일':'2026-01-01','종료일':'2026-09-30','비고':MARK},f'F{i:02}')
    for i in range(1,4): add('tags',{'태그명':f'가상태그{i}','분류':'가상분류','설명':MARK},f'T{i:02}')
    for i in range(1,10):
        rec={'재원':f'QA{i:02}','변경회차':'당초','신청일자':'2026-01-01','변경사유':MARK}
        rec.update({x:(i*1000000 if i<=7 else 0) for x in items})
        if i==8: rec['연구활동비']=300000
        if i==9: rec['연구활동비']=100000
        add('budget',rec,f'BUD{i:02}'); expected_budget.append(rec)
    for rnd,amt,date in [('이월',100000,'2026-01-01'),('1',-50000,'2026-06-01')]:
        rec={'재원':'QA01','변경회차':rnd,'신청일자':date,'변경사유':MARK,'연구활동비':amt}
        add('budget',rec,f'BUD01-{rnd}'); expected_budget.append(rec)
    serial=0
    choices=['연구활동비','연구재료비','연구시설.장비비','국제공동연구개발비','연구개발부담비','간접비(공통)']
    for fund in range(1,8):
        for month in range(1,10):
            for j in range(2):
                serial+=1; sid=f'E{serial:03}'
                day=5 if j==0 else 15
                date=f'2026-{month:02}-{day:02}'
                rec={'재원':f'QA{fund:02}','예산목':choices[(month+j+fund)%len(choices)],'원인발생일':date,
                     '금액':fund*10000+month*1000+j*500,'거래처':f'가상거래처{(fund+j)%5+1:02}',
                     '적요':f'{MARK} {sid} 반복 {month}월 {j+1}차','관리번호':RUN+'_'+sid,
                     '사용자':'가상담당자Alex','태그':f'가상태그{fund%3+1}',
                     '결제수단':['연구비카드','계좌이체','연구자선지출'][j%3],'비고':MARK}
                state=(serial-1)%5
                if state>=1: rec['지급청구일']=f'2026-{month:02}-{day+1:02}'
                if state==2: rec['상태']='보완'
                if state>=3: rec['지출완료일']=f'2026-{month:02}-{day+2:02}'
                if state==4: rec['결의일']=f'2026-{month:02}-{day+3:02}'
                ex(rec,sid)
    for sid,amt,date in [('V-EXHAUST-A',100000,'2026-01-01'),('V-EXHAUST-B',200000,'2026-09-30')]:
        ex({'재원':'QA08','예산목':'연구활동비','원인발생일':date,'금액':amt,'적요':f'{MARK} {sid}','거래처':'가상정확소진업체'},sid,'valid_boundary')
    ex({'재원':'QA09','예산목':'연구활동비','원인발생일':'2026-01-01','금액':1},'V-MINIMAL','valid_boundary')
    ex({'재원':'QA09','예산목':'연구활동비','원인발생일':'2026-09-30','금액':1,'적요':MARK+' 기간끝 1원'},'V-LASTDAY','valid_boundary')
    ex({'재원':'QA09','예산목':'연구활동비','원인발생일':'2026-06-15','금액':1,'적요':MARK+' 긴글','비고':MARK+'가'*(32767-len(MARK))},'V-TEXT32767','valid_boundary')
    for p in range(1,3):
        name=f'가상연구원{p:02}'
        add('people',{'이름':name,'인건비구분':'내부' if p==1 else '외부','입사일':'2026-01-01','비고':MARK},f'PERSON{p}')
        add('salary',{'이름':name,'시작월':'2026-01','종료월':'2026-09','월액':100000*p},f'SALARY{p}')
        for m in range(1,10):
            sid=f'L{p}-{m:02}'; amount=100000*p; fund=f'QA{p:02}'
            rec={'이름':name,'지급월':f'2026-{m:02}','귀속월':f'2026-{m:02}','지급처':fund,'금액':amount,'비고':MARK+' '+sid}
            r=add('labor',rec,sid)
            if m<=6:
                day=f'2026-{m:02}-25'
                result=call(f'/api/labor/{r["_row"]}/action',{'action':'confirm','pay_date':day},sid+'-CONFIRM')
                expected_exec.append({'재원':fund,'예산목':'내부인건비(공통)' if p==1 else '외부인건비(공통)','금액':amount,'원인발생일':day})
                refs.append({'scenario_id':sid+'-CONFIRM','group':'basic','kind':'exec','identifier':{'거래번호':result['연결거래번호']}})
    for v in range(2):
        vendor=['가상문구A','가상문구B'][v]; fund=f'QA{v+3:02}'
        rec={'일자':'2026-01-02','거래처':vendor,'구분':'적립','금액':500000,'적요':MARK+' 선결제','비고':MARK,
             '_record_exec':True,'_재원':fund,'_예산목':'연구활동비'}
        add('deposit',rec,f'DEP{v+1}'); expected_dep.append({'거래처':vendor,'구분':'적립','금액':500000})
        expected_exec.append({'재원':fund,'예산목':'연구활동비','금액':500000,'원인발생일':'2026-01-02'})
        use={'일자':'2026-02-02','거래처':vendor,'구분':'사용','금액':100000,'적요':MARK+' 수기사용','태그':'가상태그1','비고':MARK}
        add('deposit',use,f'USE{v+1}'); expected_dep.append(use)
    for n in range(1,8):
        rec={'재원':f'QA{n:02}','예산목':'연구활동비','원인발생일':'2026-08-01','지출예정일':'2026-09-15','금액':n*20000,'상태':'대기','적요':MARK+f' 품의{n}','품의자':'가상담당자Alex','거래처':f'가상품의업체{n}'}
        result=add('req',rec,f'P{n:02}')
        if n==1:
            call(f'/api/req/{result["_row"]}/to-exec',{'extra':{}},'P01-CONVERT')
            expected_exec.append({**rec}); rec={**rec,'상태':'집행완료'}
        expected_req.append(rec)
    requests=[]
    for n in range(1,13):
        typ='소모품' if n<=4 else ['장비','기타','학회'][(n-5)%3]
        rec={'구분':typ,'신청인':f'가상신청인{n%3+1}','신청일':'2026-07-01','관련과제':'QA05','품목':MARK+f' 신청품목{n:02}',
             '단가':10000,'수량':n if n<=4 else 1,'금액':10000,'사유':MARK,'비고':MARK}
        if n<=4: rec.update({'구매처':'가상문구A' if n<=2 else '가상문구B','상품코드':f'QA-SKU-{n:02}'})
        if n==5: rec.update({'부가세구분':'Y','부가세액':1000})
        r=add('request',rec,f'RQ{n:02}'); requests.append(r)
        if n<=8:
            call(f'/api/request/{r["_row"]}/action',{'action':'approve','extra':{'결재인':'가상결재자','결재일':'2026-07-02'}},f'RQ{n:02}-APPROVE')
        elif n==9:
            call(f'/api/request/{r["_row"]}/action',{'action':'reject','extra':{'결재인':'가상결재자','결재일':'2026-07-02','사유':MARK+' 사양확인'}},'RQ09-REJECT')
    for j, pay in enumerate([28000,70000]):
        rows=[r['_row'] for r in requests[j*2:j*2+2]]
        order=call('/api/order/create',{'rows':rows,'extra':{'주문일':'2026-07-03','결제금액':pay,'적립금사용':'Y','사용자':'가상담당자Alex','태그':'가상태그2','비고':MARK}},f'ORDER{j+1}')
        expected_dep.append({'거래처':['가상문구A','가상문구B'][j],'구분':'사용','금액':pay})
        refs.append({'scenario_id':f'ORDER{j+1}','group':'basic','kind':'order','identifier':{'주문번호':order['order']['주문번호']},'row_at_baseline':order['order']['_row']})
        if j==1: call(f'/api/order/{order["order"]["_row"]}/action',{'action':'deliver','extra':{'배송일':'2026-07-10'}},'ORDER2-DELIVER')
    conv=call('/api/request/convert',{'rows':[requests[4]['_row'],requests[5]['_row']],'extra':{'재원':'QA05','예산목':'연구활동비','원인발생일':'2026-07-04','비고':MARK}},'RQ05-06-CONVERT')
    call(f'/api/req/{conv["req"]["_row"]}/to-exec',{'extra':{}},'RQ05-06-EXEC')
    expected_exec.append({'재원':'QA05','예산목':'연구활동비','금액':21000,'원인발생일':'2026-07-04'})
    expected_req.append({'재원':'QA05','예산목':'연구활동비','금액':21000,'상태':'집행완료'})
    boundaries=[('V-UNITMAX',{'구분':'장비','단가':10**12,'수량':1}),('V-QTYMAX',{'구분':'장비','단가':1,'수량':1000000}),('V-AMOUNTMAX',{'구분':'장비','단가':10**12,'수량':1000}),('V-CONFZERO',{'구분':'학회','단가':0,'금액':0,'수량':1})]
    for sid,fields in boundaries:
        add('request',{'신청인':'가상경계신청인','신청일':'2026-09-30','품목':MARK+' '+sid,'관련과제':'QA09','비고':MARK,**fields},sid,'valid_boundary')
    data=client.get('/api/all').json()
    actual={k:v for k,v in data.items() if isinstance(v,list)}
    summary={f'QA{i:02}':{'budget':0,'spent':0,'pending':0} for i in range(1,11)}
    by_item=defaultdict(lambda:{'budget':0,'spent':0,'pending':0})
    monthly=defaultdict(int)
    for r in expected_budget:
        for item in items:
            value=r.get(item,0); summary[r['재원']]['budget']+=value; by_item[(r['재원'],item)]['budget']+=value
    for r in expected_exec:
        summary[r['재원']]['spent']+=r['금액']; by_item[(r['재원'],r['예산목'])]['spent']+=r['금액']; monthly[(r['재원'],r['원인발생일'][:7])]+=r['금액']
    for r in expected_req:
        if r['상태']=='대기': summary[r['재원']]['pending']+=r['금액']; by_item[(r['재원'],r['예산목'])]['pending']+=r['금액']
    for value in summary.values(): value.update({'balance':value['budget']-value['spent'],'available':value['budget']-value['spent']-value['pending']})
    checks=[]
    def check(name,ok):
        checks.append({'check':name,'passed':bool(ok)})
        if not ok: raise AssertionError(name)
    check('at_least_100_exec',len(actual['exec'])>=100)
    check('ten_funds',len(actual['funds'])==10)
    check('exec_count',len(actual['exec'])==len(expected_exec))
    for kind,key in [('funds','재원코드'),('exec','거래번호'),('req','품의번호'),('request','신청번호'),('order','주문번호')]:
        vals=[r[key] for r in actual[kind]]; check(kind+'_unique',len(vals)==len(set(vals)))
    funds=set(summary); exids={r['거래번호'] for r in actual['exec']}; reqids={r['품의번호'] for r in actual['req']}; orderids={r['주문번호'] for r in actual['order']}
    check('fund_references',all(r['재원'] in funds for k in ['exec','budget','req'] for r in actual[k]))
    check('linked_exec_references',all(not r.get('연결거래번호') or r['연결거래번호'] in exids for k in ['labor','deposit'] for r in actual[k]))
    check('request_links',all((not r.get('연결품의번호') or r['연결품의번호'] in reqids) and (not r.get('주문번호') or r['주문번호'] in orderids) for r in actual['request']))
    for fund,exp in summary.items():
        obs={'budget':sum(sum(r.get(i) or 0 for i in items) for r in actual['budget'] if r['재원']==fund),'spent':sum(r['금액'] for r in actual['exec'] if r['재원']==fund),'pending':sum(r['금액'] for r in actual['req'] if r['재원']==fund and r['상태']=='대기')}
        check(fund+'_independent_totals',all(obs[k]==exp[k] for k in obs))
    for (fund,item),exp in by_item.items():
        check(fund+'_'+item+'_spent',sum(r['금액'] for r in actual['exec'] if r['재원']==fund and r['예산목']==item)==exp['spent'])
    for k,rows in actual.items():
        for r in rows:
            for field in store.DATE_COLS:
                if r.get(field): check(f'{k}:{r.get("_row")}:{field}:period','2026-01-01'<=r[field]<='2026-09-30')
    check('exec_date_order',all(sorted([r[c] for c in ['원인발생일','지급청구일','지출완료일','결의일'] if r.get(c)])==[r[c] for c in ['원인발생일','지급청구일','지출완료일','결의일'] if r.get(c)] for r in actual['exec']))
    check('QA08_exact_exhaustion',summary['QA08']['balance']==0)
    check('QA10_empty',summary['QA10']=={'budget':0,'spent':0,'pending':0,'balance':0,'available':0})
    check('no_formulas',data['meta']['formula_count']==0)
    check('original_untouched',sha(target)==original_hash)
    # Persist schema and all accepted inputs, independent expectations, IDs and readback separately.
    dump('schema.json',{'source':'app/store.py _SHEETS, DATE_COLS, NUM_COLS; input form app/static/app.js','entities':{k:{'sheet':v[0],'fields':v[1],'header_row':v[2],'primary_key':v[3],'identity_fields':store.IDENT_COLS.get(k,[])} for k,v in store._SHEETS.items()},'date_fields':sorted(store.DATE_COLS),'number_fields':sorted(store.NUM_COLS),'budget_items':items,'payment_methods':store.PAY_METHODS})
    dump('basic_inputs.json',grouped['basic']); dump('valid_boundary_inputs.json',grouped['valid_boundary'])
    dump('api_input_log.json',calls); dump('record_ids.json',refs); dump('app_readback.json',actual)
    balances={v:sum(r['금액']*(1 if r['구분']=='적립' else -1) for r in expected_dep if r['거래처']==v) for v in ['가상문구A','가상문구B']}
    check('deposit_balances',all(sum(r['금액']*(1 if r['구분']=='적립' else -1) for r in actual['deposit'] if r['거래처']==v)==b for v,b in balances.items()))
    dump('expected_totals.json',{'basis':'Independently summed designed inputs; not copied from dashboard','funds':summary,'fund_item':[{'fund':k[0],'item':k[1],**v} for k,v in by_item.items()],'monthly':[{'fund':k[0],'month':k[1],'spent':v} for k,v in sorted(monthly.items())],'deposit_balances':balances})
    base={'재원':'QA01','예산목':'연구활동비','원인발생일':'2026-09-20','금액':10000,'적요':MARK+' 오류검증','거래처':'가상오류거래처'}
    rq={'구분':'장비','신청인':'가상오류신청인','신청일':'2026-09-20','품목':MARK+' 오류검증','단가':10000,'수량':1}
    errors=[]
    def err(sid,kind,body,reason,ids,basis='R1 및 현재 서버 검증 규칙'):
        errors.append({'scenario_id':sid,'method':'POST','path':'/api/'+kind,'body':body,'intentional_issue':reason,'expected':'거부; 기존 기록과 합계 유지','checklist_ids':ids,'basis':basis,'submitted':False})
    for sid,change,reason in [('X01',{'재원':''},'필수 재원 누락'),('X02',{'금액':'abc'},'금액 형식 오류'),('X03',{'원인발생일':'2026-02-30'},'실재하지 않는 날짜'),('X04',{'금액':0},'집행 0원'),('X05',{'예산목':'가상없는예산목'},'목록 밖 예산목'),('X06',{'결제수단':'가상잘못된수단'},'목록 밖 결제수단'),('X07',{'태그':'가상없는태그'},'등록되지 않은 태그')]: err(sid,'exec',{**base,**change},reason,['C-01','C-02'])
    err('X08','funds',{'재원코드':'QA01','과제명':MARK+' 중복'},'재원 고유값 중복',['B-02'])
    err('X09','budget',{'재원':'QA01','변경회차':'당초','신청일자':'2026-01-01','연구활동비':1},'동일 재원 당초 중복',['B-01'])
    for sid,change,reason in [('X10',{'단가':0},'단가 하한 미만'),('X11',{'단가':10**12+1},'단가 상한 초과'),('X12',{'수량':0},'수량 하한 미만'),('X13',{'수량':1.5},'수량 비정수'),('X14',{'수량':1000001},'수량 상한 초과'),('X15',{'단가':'1e400'},'무한대 금액'),('X16',{'신청인':''},'필수 신청인 누락'),('X17',{'품목':'가' * 32768},'텍스트 한도 초과')]: err(sid,'request',{**rq,**change},reason,['C-01','C-03'])
    err('X18','labor',{'이름':'가상미등록인원','지급처':'QA01','지급월':'2026-09','귀속월':'2026-09','금액':10000},'존재하지 않는 인원 참조',['B-11'])
    dump('invalid_cases_NOT_SUBMITTED.json',errors)
    warnings=[{'scenario_id':'W01','path':'/api/exec','body':{**base,'금액':-1},'expected':'UI 경고 후 확인 시 저장 가능; API 자체 경고 보장은 별도 확인','checklist_ids':['B-08'],'submitted':False},
              {'scenario_id':'W02','path':'/api/exec','body':{**base,'재원':'QA08','금액':1},'expected':'잔액 0원 재원에서 초과 경고. 무조건 거부로 판정하지 않음','checklist_ids':['B-08'],'submitted':False},
              {'scenario_id':'W03','path':'/api/exec','body':{**base,'원인발생일':'2026-10-01'},'expected':'대상 기간 밖; 과제기간 제한 업무 규칙 미확정. 제출하지 않음','checklist_ids':['B-05'],'submitted':False},
              {'scenario_id':'W04','path':'/api/exec','body':{**base,'재원':'QA_UNKNOWN'},'expected':'미등록 재원 처리 기준 확인 필요. 서버의 재원 목록 검사가 명시되지 않아 오류로 확정하지 않음','checklist_ids':['B-04'],'submitted':False},
              {'scenario_id':'W05','path':'/api/exec','body':{k:v for k,v in actual['exec'][0].items() if not k.startswith('_') and k not in ('거래번호','상태')},'expected':'같은 날·거래처·금액 UI 중복 경고; 확인 시 저장 허용','checklist_ids':['B-08'],'submitted':False}]
    dump('warning_cases_NOT_SUBMITTED.json',warnings)
    result={'run_id':RUN,'as_of':'2026-09-30','period':['2026-01-01','2026-09-30'],'counts':{k:len(v) for k,v in actual.items()},'exec_states':dict(Counter(r['상태'] for r in actual['exec'])),'request_states':dict(Counter(r['상태'] for r in actual['request'])),'checks':checks,'passed':all(x['passed'] for x in checks),'api_calls':len(calls),'invalid_submitted':0,'warning_submitted':0,'baseline_sha256':sha(STAGE),'target_path':str(target),'original_sha256':original_hash,'source_sha256':{n:sha(APP/n) for n in ['store.py','main.py','static/app.js']}}
    dump('validation.json',result)
    print(json.dumps({k:result[k] for k in ['counts','exec_states','request_states','passed','api_calls']},ensure_ascii=False))
    print('checks',len(checks),'total_spent',sum(x['spent'] for x in summary.values()))

if __name__=='__main__': build()
