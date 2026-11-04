"""Revalidate after observed evidence-number migration; no transaction data changes."""
from pathlib import Path
import sys,json,hashlib
from copy import deepcopy
P=Path(__file__).resolve().parent; APP=P.parents[1]/'app'
sys.path.insert(0,str(APP))
import main,store
from fastapi.testclient import TestClient
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((P/'validation.json').read_text(encoding='utf-8'))
expected=json.loads((P/'app_readback.json').read_text(encoding='utf-8'))
assert not expected['evidence'] and not expected['ratt']
assert sha(store.XLSX_PATH)==v['original_sha256']
store.XLSX_PATH=P/'synthetic_baseline.xlsx'; store.BACKUP_DIR=P/'build_backups'
store.init_file()
response=TestClient(main.app).get('/api/all'); assert response.status_code==200
actual={k:x for k,x in response.json().items() if isinstance(x,list)}
assert actual==expected, 'Migration changed transaction readback'
for kind,rows in actual.items():
    if kind in store._SHEETS and kind not in ('order','ratt'):
        for row in rows:
            store._validate(kind,deepcopy(row))
v['checks'].append({'check':'evidence_number_schema_migration_and_all_record_validation','passed':True})
v['source_change_review']='Concurrent store.py change adds evidence identifiers; evidence is empty in fixture. Migrated isolated baseline with app init_file; exact readback equality and all record validation confirmed.'
v['previous_source_sha256']=v['source_sha256']
v['source_sha256']={n:sha(APP/n) for n in v['source_sha256']}
v['baseline_sha256']=sha(store.XLSX_PATH)
(P/'validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
s=json.loads((P/'schema.json').read_text(encoding='utf-8'))
s['entities']={k:{'sheet':x[0],'fields':x[1],'header_row':x[2],'primary_key':x[3],'identity_fields':store.IDENT_COLS.get(k,[])} for k,x in store._SHEETS.items()}
(P/'schema.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
print('Schema migrated; exact readback and all record validation passed.')
