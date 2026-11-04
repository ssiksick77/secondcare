import requests, json, subprocess, sys, os, pathlib
QA = pathlib.Path(__file__).resolve().parent.parent
B = "http://127.0.0.1:8811"
LEDGER = QA / "inst_common" / "ledger_common.xlsx"
SHOTS = QA / "shots"
def all_(): return requests.get(B + "/api/all").json()
def post(path, body): 
    r = requests.post(B + path, json=body); return r
def put(path, body): return requests.put(B + path, json=body)
def delete(path, body=None): return requests.delete(B + path, json=body)
def show(r): 
    try: j = r.json()
    except Exception: j = r.text
    return f"{r.status_code} {json.dumps(j, ensure_ascii=False)[:400]} wid={r.headers.get('X-Write-Id')}"
def launch(reset=False):
    a = [sys.executable, str(QA/"launch.py"), "common", "8811"] + (["--reset"] if reset else [])
    print(subprocess.run(a, capture_output=True, text=True, cwd=str(QA)).stdout)
def stop():
    print(subprocess.run([sys.executable, str(QA/"launch.py"), "common", "--stop"], capture_output=True, text=True, cwd=str(QA)).stdout)
def exec_by_no(no):
    return [r for r in all_()["exec"] if r["거래번호"] == no]
def expect(r):
    return {"거래번호": r["거래번호"], "_snapshot": {k: v for k, v in r.items() if not k.startswith("_")}}
EXEC_OK = {"원인발생일": "2026-10-14", "재원": "QA10", "예산목": "연구활동비", "거래처": "QA거래처", "금액": 10000, "적요": "QA common 테스트"}
