import json, hashlib, subprocess, sys, time, requests, pathlib
QA = pathlib.Path("<home>/AppData/Local/Temp/claude/<session>/18367f8b-184a-424d-99ad-8ce7d7ee1121/scratchpad/qa")
BASE = "http://127.0.0.1:8814"
ORIG = pathlib.Path("<home>/Desktop/Project/01 in progress/CAIH_회계장부_2026/QA set")
def snap():
    d = requests.get(BASE + "/api/all").json()
    keys = ["funds","budget","exec","req","deposit","tags","evidence","people","salary","payee","labor","ladj","request","order","ratt"]
    body = {k: d.get(k) for k in keys}
    h = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    counts = {k: len(d.get(k) or []) for k in keys}
    return h, counts, d
def reset():
    r = subprocess.run([sys.executable, str(QA/"launch.py"), "validate", "8814", "--reset"], capture_output=True, text=True, cwd=str(QA))
    return r.stdout.strip()
