"""Install verified fixture with non-rotating original backups and conflict checks."""
from pathlib import Path
import sys, json, hashlib, shutil, os
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]; APP=ROOT/'app'
sys.path.insert(0,str(APP))
import main, store, settings
from fastapi.testclient import TestClient
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value): (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def install():
    validation=json.loads((OUT/'validation.json').read_text(encoding='utf-8'))
    stage=OUT/'synthetic_baseline.xlsx'
    target=store.XLSX_PATH.resolve()
    if (OUT/'installed.json').exists():
        m=json.loads((OUT/'installed.json').read_text(encoding='utf-8'))
        if sha(target)==m['installed_sha256']:
            print('Already installed; no changes.'); return
        raise SystemExit('Installation exists and active data changed. Refusing overwrite; use explicit restoration workflow.')
    assert validation['passed'] and sha(stage)==validation['baseline_sha256']
    assert target.is_relative_to(ROOT.resolve()) and str(target)==validation['target_path']
    assert sha(target)==validation['original_sha256'], 'Original changed after planning; do not overwrite.'
    for name,digest in validation['source_sha256'].items(): assert sha(APP/name)==digest, 'App code changed; regenerate.'
    backup=APP/'backup'/('QA_ORIGINAL_'+validation['run_id'])
    backup.mkdir(parents=True,exist_ok=True)
    original=backup/'original_ledger.xlsx'; env=backup/'original.env'
    env_exists=settings.ENV_PATH.exists()
    manifest={'run_id':validation['run_id'],'target':str(target),'original_backup':str(original),'env_backup':str(env) if env_exists else None,
              'original_sha256':validation['original_sha256'],'baseline':str(stage),'installed_sha256':sha(stage),'counts':validation['counts'],
              'delivery':'Application POST handlers wrote isolated native workbook; verified workbook installed at active configured path; GET /api/all readback verified. No browser input claimed.',
              'supplier_setting_change':'Append fictional suppliers; preserve existing suppliers. Other settings unchanged.'}
    with store._lock, store._file_lock():
        assert sha(target)==validation['original_sha256']
        if original.exists(): assert sha(original)==validation['original_sha256']
        else: shutil.copy2(target,original)
        assert sha(original)==sha(target), 'Backup verification failed'
        if env_exists:
            if env.exists(): assert sha(env)==sha(settings.ENV_PATH), 'Existing settings backup mismatch'
            else: shutil.copy2(settings.ENV_PATH,env)
            manifest['env_original_sha256']=sha(env)
        vals=[x.strip() for x in settings.get('REQUEST_SUPPLIERS').split(',') if x.strip()]
        for value in ['가상문구A','가상문구B']:
            if value not in vals: vals.append(value)
        temp=target.with_name('qa_verified_install.tmp.xlsx')
        shutil.copy2(stage,temp)
        try:
            settings.save({'REQUEST_SUPPLIERS':','.join(vals)})
            os.replace(temp,target)
            assert sha(target)==manifest['installed_sha256']
        except Exception:
            if env_exists: shutil.copy2(env,settings.ENV_PATH)
            raise
    actual=TestClient(main.app).get('/api/all')
    assert actual.status_code==200
    data=actual.json()
    expected=json.loads((OUT/'app_readback.json').read_text(encoding='utf-8'))
    assert {k:v for k,v in data.items() if isinstance(v,list)}==expected, 'Installed API readback mismatch'
    manifest['readback_verified']=True
    manifest['env_installed_sha256']=sha(settings.ENV_PATH)
    write('installed.json',manifest)
    print(json.dumps({'installed':True,'counts':manifest['counts'],'backup':str(original),'readback_verified':True},ensure_ascii=False))

if __name__=='__main__': install()
