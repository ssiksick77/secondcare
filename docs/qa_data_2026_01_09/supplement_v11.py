"""QA26JANSEP_V1 -> V1.1 supplement (evidence, request attachments, boundary cases).

All writes go through the app's own POST handlers (FastAPI TestClient on app/main.py) with a mock Drive.
Idempotent: every step checks its own marker in the ledger first and is skipped if already present.

Required environment (set BEFORE running; nothing defaults to the real ledger):
  LEDGER_XLSX        absolute path of the ledger to supplement (a scratch copy, or this folder's qa_ledger.xlsx)
  LEDGER_ENV         this folder's qa.env (never app/.env)
  LEDGER_DRIVE_MOCK  must be 1
Optional:
  SUPPLEMENT_MOCK_DIR    mock Drive root (default: this folder/qa_drive_mock, gitignored)
  SUPPLEMENT_BACKUP_DIR  app write-backups (default: this folder/build_backups, *.xlsx gitignored)
  SUPPLEMENT_OUT         where to write regenerated dataset files. Default: this folder, but ONLY when
                         LEDGER_XLSX is this folder's qa_ledger.xlsx; otherwise regeneration is skipped
                         unless SUPPLEMENT_OUT is given (use a scratch folder for copy runs).

Usage:  python supplement_v11.py            (apply + regenerate)
        import supplement_v11; supplement_v11.integrity_checks(...)   (reused by tests; importing does not run anything)
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import struct
import sys
import zlib
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
APP = ROOT / 'app'
REAL_LEDGER = (ROOT / '의료인공지능센터_지출장부_2026.xlsx').resolve()
REAL_ENV = (APP / '.env').resolve()
QA_LEDGER = (OUT / 'qa_ledger.xlsx').resolve()
QA_PORT = 8792

RUN = 'QA26JANSEP_V1.1'
MARK = '[가상 QA26JANSEP_V1]'
MARK11 = '[가상 QA26JANSEP_V1.1]'
MGMT = 'QA26JANSEP_V11_'

# ---------- designed V1.1 inputs (independent of the app; used for expected totals) ----------
SAMEDAY = [  # two exec rows, same 원인발생일 + 재원 + 예산목 (voucher cumulative-order check)
    {'sid': 'V11-SAMEDAY-1', 'rec': {'재원': 'QA06', '예산목': '연구재료비', '원인발생일': '2026-09-22', '금액': 33000,
                                     '거래처': '가상거래처01', '적요': MARK11 + ' 같은날 1차', '관리번호': MGMT + 'SAMEDAY-1',
                                     '사용자': '가상담당자Alex', '태그': '가상태그1', '결제수단': '연구비카드', '비고': MARK11}},
    {'sid': 'V11-SAMEDAY-2', 'rec': {'재원': 'QA06', '예산목': '연구재료비', '원인발생일': '2026-09-22', '지급청구일': '2026-09-23',
                                     '금액': 44000, '거래처': '가상거래처02', '적요': MARK11 + ' 같은날 2차', '관리번호': MGMT + 'SAMEDAY-2',
                                     '사용자': '가상담당자Alex', '태그': '가상태그1', '결제수단': '계좌이체', '비고': MARK11}},
]
VAT_REQUEST = {'구분': '소모품', '신청인': '가상신청인1', '신청일': '2026-09-21', '관련과제': 'QA06',
               '품목': MARK11 + ' V11-VAT 소모품', '단가': 10000, '수량': 3, '부가세구분': 'Y',
               '구매처': '가상문구A', '상품코드': 'QA-SKU-V11', '사유': MARK11, '비고': MARK11}
VAT_EXPECT = {'금액': 33000, '부가세액': 3000}
ORDER2_CONVERT = {'재원': 'QA05', '예산목': '연구재료비', '원인발생일': '2026-07-11', '비고': MARK11 + ' ORDER2 배송완료 후 품의 전환'}
ORDER2_PAY = 70000  # designed 결제금액 of ORDER2 (V1 build_fixture) -> 품의 금액, left 대기
# evidence plan: target exec by 관리번호 (V1 scenario), steps executed in order
EVIDENCE = [
    {'sid': 'V11-EVID-E004', 'mgmt': 'QA26JANSEP_V1_E004', 'steps': [
        ('upload', '세금계산서', MARK11 + ' 세금계산서 스캔(가상)', 'qa_v11_tax_invoice.png')]},
    {'sid': 'V11-EVID-E020', 'mgmt': 'QA26JANSEP_V1_E020', 'steps': [
        ('entry', '거래명세서', MARK11 + ' 실물 보관(파일 없음)', None),
        ('upload', '카드전표', MARK11 + ' 카드전표 PDF(가상)', 'qa_v11_card_slip.pdf')]},
    {'sid': 'V11-EVID-E041', 'mgmt': 'QA26JANSEP_V1_E041', 'steps': [
        ('entry', '견적서', MARK11 + ' 항목 먼저 만든 뒤 파일 첨부', None),
        ('attach', '견적서', '', 'qa_v11_quote.png')]},
    {'sid': 'V11-EVID-E058', 'mgmt': 'QA26JANSEP_V1_E058', 'steps': [
        ('entry', '영수증', MARK11 + ' 종이 영수증 실물만', None)]},
    {'sid': 'V11-EVID-E077', 'mgmt': 'QA26JANSEP_V1_E077', 'steps': [
        ('entry', '카드전표', '', None)]},  # 비고 없는 항목 (빈 비고 경계)
]
RATT = [  # (scenario, how to find the request, file, note)
    ('V11-RATT-RQ08', 'R-2026-008', 'qa_v11_equipment_quote.pdf', MARK11 + ' 장비 견적서(가상)'),
    ('V11-RATT-VAT', 'VAT', 'qa_v11_supply_catalog.png', MARK11 + ' 소모품 상품 안내(가상)'),
]
V11_EXEC_ADD = len(SAMEDAY)
V11_COUNTS = {'exec': 2, 'req': 1, 'request': 1, 'evidence': 6, 'evidence_with_file': 3, 'evidence_without_file': 3, 'ratt': 2}


def tiny_png(rgb=(40, 120, 200)) -> bytes:
    """Valid 1x1 RGB PNG (~70 bytes)."""
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    raw = b'\x00' + bytes(rgb)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + \
        chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')


def tiny_pdf(text='QA26JANSEP_V1.1 synthetic') -> bytes:
    """Minimal one-page PDF (< 1 KB), ASCII only."""
    stream = f'BT /F1 10 Tf 20 60 Td ({text}) Tj ET'.encode()
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
            b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream',
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    out, offs = b'%PDF-1.4\n', []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f'{i} 0 obj\n'.encode() + o + b'\nendobj\n'
    xref = len(out)
    out += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode() + b''.join(f'{o:010d} 00000 n \n'.encode() for o in offs)
    out += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    return out


def file_blob(name: str):
    if name.endswith('.png'):
        return tiny_png(), 'image/png'
    return tiny_pdf(), 'application/pdf'


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def port_in_use(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0


# ---------- environment guard + app import ----------
def _setup():
    xl = os.environ.get('LEDGER_XLSX', '').strip()
    env = os.environ.get('LEDGER_ENV', '').strip()
    if not xl or not Path(xl).is_absolute():
        raise SystemExit('LEDGER_XLSX must be an absolute path (scratch copy or docs/qa_data_2026_01_09/qa_ledger.xlsx).')
    target = Path(xl).resolve()
    if target == REAL_LEDGER:
        raise SystemExit('Refusing: LEDGER_XLSX is the real ledger.')
    if not target.exists():
        raise SystemExit(f'Ledger not found: {target}')
    if not env or Path(env).resolve() != (OUT / 'qa.env').resolve():
        raise SystemExit('LEDGER_ENV must point at docs/qa_data_2026_01_09/qa.env.')
    if Path(env).resolve() == REAL_ENV:
        raise SystemExit('Refusing: LEDGER_ENV is app/.env.')
    if os.environ.get('LEDGER_DRIVE_MOCK') != '1':
        raise SystemExit('LEDGER_DRIVE_MOCK=1 is required.')
    if target == QA_LEDGER and port_in_use(QA_PORT):
        raise SystemExit(f'Port {QA_PORT} is listening (QA server may hold the QA ledger). Stop it first.')
    sys.path.insert(0, str(APP))
    import main  # noqa: E402  (reads LEDGER_ENV / LEDGER_XLSX at import)
    import store  # noqa: E402
    import drive  # noqa: E402
    assert store.XLSX_PATH.resolve() == target, (store.XLSX_PATH, target)
    drive.MOCK_DIR = Path(os.environ.get('SUPPLEMENT_MOCK_DIR') or OUT / 'qa_drive_mock').resolve()
    drive.MOCK_DIR.mkdir(parents=True, exist_ok=True)
    store.BACKUP_DIR = Path(os.environ.get('SUPPLEMENT_BACKUP_DIR') or OUT / 'build_backups').resolve()
    assert drive.mock()
    return main, store, drive, target


# ---------- apply ----------
def apply(client, store, log: list):
    def call(method, path, sid, **kw):
        r = getattr(client, method)(path, **kw)
        if r.status_code != 200:
            raise RuntimeError(f'{sid} {method.upper()} {path}: {r.status_code} {r.text}')
        entry = {'scenario_id': sid, 'method': method.upper(), 'path': path, 'status': r.status_code}
        if 'json' in kw:
            entry['body'] = deepcopy(kw['json'])
        if 'files' in kw:
            entry['multipart'] = {'files': [{'filename': f[1][0], 'bytes': len(f[1][1]), 'type': f[1][2]} for f in kw['files']],
                                  'form': deepcopy(kw.get('data') or {})}
        log.append(entry)
        return r.json()

    def all_data():
        return client.get('/api/all').json()

    done = []
    d = all_data()
    # 1) same-day exec rows
    for s in SAMEDAY:
        if any(r.get('관리번호') == s['rec']['관리번호'] for r in d['exec']):
            done.append((s['sid'], 'skip'))
            continue
        call('post', '/api/exec', s['sid'], json=s['rec'])
        done.append((s['sid'], 'added'))
    # 2) ORDER2 (delivered, not converted) -> 품의
    d = all_data()
    delivered = [o for o in d['order'] if o.get('배송일')]
    assert len(delivered) == 1, f'expected one delivered order, got {len(delivered)}'
    ono = delivered[0]['주문번호']
    members = [q for q in d['request'] if q.get('주문번호') == ono]
    if all(q.get('연결품의번호') for q in members):
        done.append(('V11-ORDER2-CONVERT', 'skip'))
    else:
        call('post', '/api/request/convert', 'V11-ORDER2-CONVERT',
             json={'rows': [q['_row'] for q in members],
                   'expects': [{'신청번호': q['신청번호']} for q in members], 'extra': dict(ORDER2_CONVERT)})
        done.append(('V11-ORDER2-CONVERT', 'added'))
    # 3) 소모품 request with 부가세구분=Y (left in 신청 state)
    d = all_data()
    if any(q.get('품목') == VAT_REQUEST['품목'] for q in d['request']):
        done.append(('V11-RQ-VAT', 'skip'))
    else:
        call('post', '/api/request', 'V11-RQ-VAT', json=dict(VAT_REQUEST))
        done.append(('V11-RQ-VAT', 'added'))
    # 4) evidence on five execs (mock Drive)
    d = all_data()
    by_mgmt = {r.get('관리번호'): r for r in d['exec'] if r.get('관리번호')}
    for plan in EVIDENCE:
        ex = by_mgmt[plan['mgmt']]
        no = ex['거래번호']
        for i, (op, kind, note, fname) in enumerate(plan['steps'], 1):
            sid = f"{plan['sid']}-{i}"
            ev = [e for e in client.get(f'/api/evidence/{no}').json()['items']]
            if op == 'entry':
                if any(e['증빙종류'] == kind for e in ev):
                    done.append((sid, 'skip'))
                    continue
                call('post', f'/api/evidence/{no}/entry', sid, json={'증빙종류': kind, '비고': note})
            elif op == 'upload':
                if any(e['증빙종류'] == kind and e['has_file'] for e in ev):
                    done.append((sid, 'skip'))
                    continue
                data, mime = file_blob(fname)
                call('post', f'/api/evidence/{no}', sid, files=[('files', (fname, data, mime))],
                     data={'kind': kind, 'date': ex['원인발생일'], 'note': note})
            elif op == 'attach':
                target = next(e for e in ev if e['증빙종류'] == kind)
                if target['has_file']:
                    done.append((sid, 'skip'))
                    continue
                data, mime = file_blob(fname)
                res = call('post', f'/api/evidence/{no}', sid, files=[('files', (fname, data, mime))],
                           data={'증빙번호': target['증빙번호'], 'date': ex['원인발생일']})
                assert res['attached'] is True
            done.append((sid, 'added'))
    # 5) request attachments (mock Drive)
    d = all_data()
    for sid, ref, fname, note in RATT:
        number = ref if ref.startswith('R-') else next(q['신청번호'] for q in d['request'] if q.get('품목') == VAT_REQUEST['품목'])
        if client.get(f'/api/ratt/{number}').json()['items']:
            done.append((sid, 'skip'))
            continue
        data, mime = file_blob(fname)
        call('post', f'/api/ratt/{number}', sid, files=[('files', (fname, data, mime))], data={'note': note})
        done.append((sid, 'added'))
    return done


# ---------- expected totals (designed inputs, not the dashboard) ----------
def expected_totals(v1: dict) -> dict:
    """V1 independent totals + designed V1.1 deltas. v1 is the original V1 expected_totals content."""
    funds = deepcopy(v1['funds'])
    fi = {(x['fund'], x['item']): {k: x[k] for k in ('budget', 'spent', 'pending')} for x in v1['fund_item']}
    monthly = {(x['fund'], x['month']): x['spent'] for x in v1['monthly']}
    for s in SAMEDAY:
        r = s['rec']
        funds[r['재원']]['spent'] += r['금액']
        fi.setdefault((r['재원'], r['예산목']), {'budget': 0, 'spent': 0, 'pending': 0})['spent'] += r['금액']
        monthly[(r['재원'], r['원인발생일'][:7])] = monthly.get((r['재원'], r['원인발생일'][:7]), 0) + r['금액']
    f, i = ORDER2_CONVERT['재원'], ORDER2_CONVERT['예산목']
    funds[f]['pending'] += ORDER2_PAY
    fi.setdefault((f, i), {'budget': 0, 'spent': 0, 'pending': 0})['pending'] += ORDER2_PAY
    for v in funds.values():
        v['balance'] = v['budget'] - v['spent']
        v['available'] = v['budget'] - v['spent'] - v['pending']
    total = {k: sum(v[k] for v in funds.values()) for k in ('budget', 'spent', 'pending', 'balance', 'available')}
    return {'dataset': RUN,
            'basis': 'V1 independently summed designed inputs + designed V1.1 additions (2 exec rows, ORDER2 품의 대기 70000); not copied from dashboard',
            'funds': funds, 'total': total,
            'fund_item': [{'fund': k[0], 'item': k[1], **v} for k, v in fi.items()],
            'monthly': [{'fund': k[0], 'month': k[1], 'spent': v} for k, v in sorted(monthly.items())],
            'deposit_balances': deepcopy(v1['deposit_balances']),
            'v1_base': deepcopy({k: v1[k] for k in ('basis', 'funds', 'fund_item', 'monthly', 'deposit_balances')})}


def v1_totals(existing: dict) -> dict:
    return existing['v1_base'] if 'v1_base' in existing else existing


# ---------- integrity checks (mirror of build_fixture.py's 579 checks + V1.1 checks) ----------
def integrity_checks(data: dict, exp: dict, store, exec_count: int, counts: dict | None = None) -> list[dict]:
    """data = GET /api/all JSON (with dashboard). exp = expected_totals content. Returns [{check, passed}]."""
    actual = {k: v for k, v in data.items() if isinstance(v, list)}
    items = list(store.BUDGET_ITEMS)
    checks = []

    def check(name, ok):
        checks.append({'check': name, 'passed': bool(ok)})

    check('at_least_100_exec', len(actual['exec']) >= 100)
    check('ten_funds', len(actual['funds']) == 10)
    check('exec_count', len(actual['exec']) == exec_count)
    for kind, key in [('funds', '재원코드'), ('exec', '거래번호'), ('req', '품의번호'), ('request', '신청번호'), ('order', '주문번호')]:
        vals = [r[key] for r in actual[kind]]
        check(kind + '_unique', len(vals) == len(set(vals)))
    funds = set(exp['funds'])
    exids = {r['거래번호'] for r in actual['exec']}
    reqids = {r['품의번호'] for r in actual['req']}
    orderids = {r['주문번호'] for r in actual['order']}
    rqids = {r['신청번호'] for r in actual['request']}
    check('fund_references', all(r['재원'] in funds for k in ['exec', 'budget', 'req'] for r in actual[k]))
    check('linked_exec_references', all(not r.get('연결거래번호') or r['연결거래번호'] in exids for k in ['labor', 'deposit'] for r in actual[k]))
    check('request_links', all((not r.get('연결품의번호') or r['연결품의번호'] in reqids) and (not r.get('주문번호') or r['주문번호'] in orderids) for r in actual['request']))
    for fund, e in exp['funds'].items():
        obs = {'budget': sum(sum(r.get(i) or 0 for i in items) for r in actual['budget'] if r['재원'] == fund),
               'spent': sum(r['금액'] for r in actual['exec'] if r['재원'] == fund),
               'pending': sum(r['금액'] for r in actual['req'] if r['재원'] == fund and r['상태'] == '대기')}
        check(fund + '_independent_totals', all(obs[k] == e[k] for k in obs))
    for x in exp['fund_item']:
        check(x['fund'] + '_' + x['item'] + '_spent',
              sum(r['금액'] for r in actual['exec'] if r['재원'] == x['fund'] and r['예산목'] == x['item']) == x['spent'])
    for k, rows in actual.items():
        for r in rows:
            for field in store.DATE_COLS:
                if field == '업로드일':
                    continue  # system timestamp (actual upload day), checked separately below
                if r.get(field):
                    check(f'{k}:{r.get("_row")}:{field}:period', '2026-01-01' <= r[field] <= '2026-09-30')
    for k in ('evidence', 'ratt'):
        for r in actual[k]:
            if r.get('업로드일'):
                check(f'{k}:{r["_row"]}:업로드일:valid_system_date', store._valid_date(r['업로드일']))
    seq = ['원인발생일', '지급청구일', '지출완료일', '결의일']
    check('exec_date_order', all(sorted([r[c] for c in seq if r.get(c)]) == [r[c] for c in seq if r.get(c)] for r in actual['exec']))
    check('QA08_exact_exhaustion', exp['funds']['QA08']['balance'] == 0)
    check('QA10_empty', exp['funds']['QA10'] == {'budget': 0, 'spent': 0, 'pending': 0, 'balance': 0, 'available': 0})
    check('no_formulas', data['meta']['formula_count'] == 0)
    check('deposit_balances', all(sum(r['금액'] * (1 if r['구분'] == '적립' else -1) for r in actual['deposit'] if r['거래처'] == v) == b
                                  for v, b in exp['deposit_balances'].items()))
    # ---- V1.1 additions ----
    ev = actual['evidence']
    check('evidence_number_format', all(r.get('증빙번호', '').startswith(r['거래번호'] + '-') and r['증빙번호'][len(r['거래번호']) + 1:].isdigit() for r in ev))
    check('evidence_number_unique', len({r['증빙번호'] for r in ev}) == len(ev))
    check('evidence_exec_references', all(r['거래번호'] in exids for r in ev))
    per = defaultdict(list)
    for r in ev:
        per[r['거래번호']].append(int(r['증빙번호'].rsplit('-', 1)[1]))
    check('evidence_number_sequence', all(sorted(v) == list(range(1, len(v) + 1)) for v in per.values()))
    check('evidence_list_sync', all(set(filter(None, (x.strip() for x in (r.get('증빙목록') or '').split(',')))) ==
                                     {e['증빙종류'] for e in ev if e['거래번호'] == r['거래번호']} for r in actual['exec']))
    check('ratt_request_references', all(r['신청번호'] in rqids for r in actual['ratt']))
    exec_by_req = {r.get('연결품의번호'): r for r in actual['exec'] if r.get('연결품의번호')}
    check('converted_exec_link_column', all(q['품의번호'] in exec_by_req for q in actual['req'] if q['상태'] == '집행완료'))
    check('link_column_references', all(r['연결품의번호'] in reqids for r in exec_by_req.values()))
    if counts:
        for k, n in counts.items():
            check(f'count_{k}', len(actual[k]) == n)
    return checks


def dashboard_by_fund(data: dict) -> dict:
    out = defaultdict(lambda: {'budget': 0, 'spent': 0, 'pending': 0, 'balance': 0, 'available': 0})
    for t in data['dashboard']['table']:
        o = out[t['재원']]
        o['budget'] += t['예산현액']; o['spent'] += t['집행액']; o['pending'] += t['품의대기']
        o['balance'] += t['잔액']; o['available'] += t['가용잔액']
    return out


# ---------- derived dataset files ----------
def v11_refs(data: dict) -> list[dict]:
    """Scenario -> app identifiers, read back from the ledger by markers (idempotent)."""
    refs = []
    ex = {r.get('관리번호'): r for r in data['exec'] if r.get('관리번호')}
    for s in SAMEDAY:
        r = ex[s['rec']['관리번호']]
        refs.append({'scenario_id': s['sid'], 'group': 'v1.1', 'kind': 'exec', 'row_at_baseline': r['_row'], 'identifier': {'거래번호': r['거래번호']}})
    for plan in EVIDENCE:
        no = ex[plan['mgmt']]['거래번호']
        for e in [e for e in data['evidence'] if e['거래번호'] == no]:
            refs.append({'scenario_id': plan['sid'], 'group': 'v1.1', 'kind': 'evidence', 'row_at_baseline': e['_row'],
                         'identifier': {'거래번호': no, '증빙번호': e['증빙번호'], '증빙종류': e['증빙종류'], 'has_file': e['has_file']}})
    q = next(r for r in data['req'] if (r.get('비고') or '').endswith(ORDER2_CONVERT['비고']))
    refs.append({'scenario_id': 'V11-ORDER2-CONVERT', 'group': 'v1.1', 'kind': 'req', 'row_at_baseline': q['_row'], 'identifier': {'품의번호': q['품의번호']}})
    rq = next(r for r in data['request'] if r.get('품목') == VAT_REQUEST['품목'])
    refs.append({'scenario_id': 'V11-RQ-VAT', 'group': 'v1.1', 'kind': 'request', 'row_at_baseline': rq['_row'], 'identifier': {'신청번호': rq['신청번호']}})
    for a in data['ratt']:
        sid = next(s for s, ref, f, n in RATT if a.get('비고') == n)
        refs.append({'scenario_id': sid, 'group': 'v1.1', 'kind': 'ratt', 'row_at_baseline': a['_row'],
                     'identifier': {'신청번호': a['신청번호'], '파일명': a['파일명']}})
    return refs


def review_table(data: dict) -> str:
    def esc(v):
        return str(v if v is not None else '').replace('|', '／').replace('\n', ' ')
    head = ['거래번호', '재원', '발생일', '예산목', '가상 거래처', '적요', '금액(원)', '상태', '증빙']
    ev = Counter(e['거래번호'] for e in data['evidence'])
    lines = ['| ' + ' | '.join(head) + ' |', '|' + '|'.join(['---'] * len(head)) + '|']
    for r in data['exec']:
        lines.append('| ' + ' | '.join(esc(c) for c in [r['거래번호'], r['재원'], r['원인발생일'], r['예산목'], r['거래처'], r['적요'],
                                                          f"{r['금액']:,.0f}", r['상태표시'], ev.get(r['거래번호']) or '']) + ' |')
    return ('# 가상 집행 전체 검토표\n\n모든 기록은 QA26JANSEP_V1(V1.1 보완 포함) 가상 데이터입니다. 앱 조회 결과이며 기대 금액은 별도 expected_totals.json을 사용합니다.\n\n'
            '상태 열은 화면 표시명(`상태표시`: 발생/청구/보완/승인/완료)입니다. 저장값과의 대응: 완료(지출완료일) → **승인**, 결의(결의일) → **완료**. 증빙 열은 증빙 항목 수(파일 없는 항목 포함)입니다.\n\n'
            + '\n'.join(lines) + '\n')


def regenerate(client, store, target: Path, out: Path, log: list):
    out.mkdir(parents=True, exist_ok=True)
    data = client.get('/api/all').json()
    actual = {k: v for k, v in data.items() if isinstance(v, list)}
    old_tot = json.loads((OUT / 'expected_totals.json').read_text(encoding='utf-8'))
    exp = expected_totals(v1_totals(old_tot))
    v = json.loads((OUT / 'validation.json').read_text(encoding='utf-8'))
    v1_counts = v.get('v1_counts') or v['counts']
    counts = {k: v1_counts[k] + (V11_COUNTS.get(k, 0)) for k in v1_counts}
    checks = integrity_checks(data, exp, store, v1_counts['exec'] + V11_EXEC_ADD, counts)
    dash = dashboard_by_fund(data)
    for f, e in exp['funds'].items():
        checks.append({'check': f'{f}_dashboard_equals_expected', 'passed': all(dash[f][k] == e[k] for k in e)})
    failed = [c['check'] for c in checks if not c['passed']]
    if failed:
        raise AssertionError(f'{len(failed)} checks failed: {failed[:20]}')
    # files
    if out.resolve() == OUT:
        shutil.copy2(target, OUT / 'synthetic_baseline.xlsx')
        base = OUT / 'synthetic_baseline.xlsx'
    else:
        base = out / 'synthetic_baseline.xlsx'
        shutil.copy2(target, base)

    def dump(name, value):
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    dump('expected_totals.json', exp)
    dump('app_readback.json', actual)
    refs = [r for r in json.loads((OUT / 'record_ids.json').read_text(encoding='utf-8')) if r.get('group') != 'v1.1']
    dump('record_ids.json', refs + v11_refs(data))
    old_log = [x for x in json.loads((OUT / 'api_input_log.json').read_text(encoding='utf-8')) if not str(x.get('scenario_id', '')).startswith('V11-')]
    prev_v11 = [x for x in json.loads((OUT / 'api_input_log.json').read_text(encoding='utf-8')) if str(x.get('scenario_id', '')).startswith('V11-')]
    dump('api_input_log.json', old_log + (log or prev_v11))
    s = json.loads((OUT / 'schema.json').read_text(encoding='utf-8'))
    s['entities'] = {k: {'sheet': x[0], 'fields': x[1], 'header_row': x[2], 'primary_key': x[3], 'identity_fields': store.IDENT_COLS.get(k, [])}
                     for k, x in store._SHEETS.items()}
    dump('schema.json', s)
    v.setdefault('v1_counts', v1_counts)
    v['counts'] = {k: len(x) for k, x in actual.items()}
    v['exec_states'] = dict(Counter(r['상태'] for r in actual['exec']))
    v['exec_state_labels'] = dict(Counter(r['상태표시'] for r in actual['exec']))
    v['request_states'] = dict(Counter(r['상태'] for r in actual['request']))
    v['supplement_v11'] = {'run_id': RUN, 'script': 'supplement_v11.py', 'checks': checks, 'check_count': len(checks),
                           'passed': True, 'api_calls': len(log or prev_v11),
                           'note': '업로드일 is the actual system upload date (outside the 1~9월 business period); excluded from the period check and validated as a date.'}
    v['baseline_sha256'] = sha(base)
    v['source_sha256'] = {n: sha(APP / n) for n in v['source_sha256']}
    dump('validation.json', v)
    (out / '거래내역_검토표.md').write_text(review_table(data), encoding='utf-8')
    return {'checks': len(checks), 'counts': v['counts'], 'exec_state_labels': v['exec_state_labels'],
            'baseline_sha256': v['baseline_sha256'], 'total': exp['total']}


def run():
    main, store, drive, target = _setup()
    from fastapi.testclient import TestClient
    before = sha(target)
    store.init_file()  # app's own structure migration (adds 집행내역 연결품의번호 etc.); backup goes to BACKUP_DIR
    client = TestClient(main.app)
    counts_before = {k: len(v) for k, v in client.get('/api/all').json().items() if isinstance(v, list)}
    log = []
    done = apply(client, store, log)
    counts_after = {k: len(v) for k, v in client.get('/api/all').json().items() if isinstance(v, list)}
    print(json.dumps({'ledger': str(target), 'sha_before': before, 'sha_after': sha(target), 'steps': done,
                      'counts_before': counts_before, 'counts_after': counts_after, 'api_calls': len(log)}, ensure_ascii=False, indent=1))
    out_env = os.environ.get('SUPPLEMENT_OUT', '').strip()
    out = Path(out_env).resolve() if out_env else (OUT if target == QA_LEDGER else None)
    if out is None:
        print('No SUPPLEMENT_OUT and not the QA ledger: dataset files not regenerated.')
        return
    print(json.dumps(regenerate(client, store, target, out, log), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    run()
