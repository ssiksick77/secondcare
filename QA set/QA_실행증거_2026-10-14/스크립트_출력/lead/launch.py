"""Create an isolated instance from baseline and start the server in the background.
usage: python launch.py <name> <port> [--reset]
  creates qa/inst_<name>/ledger_<name>.xlsx from qa/baseline.xlsx (copies fresh when --reset or missing)
  writes qa/inst_<name>/pid, log in qa/inst_<name>/server.log
stop:  python launch.py <name> --stop
"""
import os, sys, shutil, subprocess, time, pathlib, urllib.request
QA = pathlib.Path(__file__).resolve().parent
name = sys.argv[1]
inst = QA / f"inst_{name}"; inst.mkdir(exist_ok=True)
pidf = inst / "pid"
def stop():
    if pidf.exists():
        pid = pidf.read_text().strip()
        subprocess.run(["taskkill", "/PID", pid, "/F", "/T"], capture_output=True)
        pidf.unlink()
        print("stopped", pid)
if "--stop" in sys.argv:
    stop(); sys.exit()
port = sys.argv[2]
ledger = inst / f"ledger_{name}.xlsx"
stop()
if "--reset" in sys.argv or not ledger.exists():
    for p in inst.glob("ledger_*"):
        p.unlink()
    shutil.copy2(QA / "baseline.xlsx", ledger)
    print("ledger reset from baseline")
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
log = open(inst / "server.log", "ab")
p = subprocess.Popen([sys.executable, str(QA / "app" / "runner.py"), str(ledger), port],
                     cwd=str(QA / "app"), stdout=log, stderr=subprocess.STDOUT, env=env,
                     creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
pidf.write_text(str(p.pid))
for _ in range(60):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/meta", timeout=1).read()
        print(f"up: http://127.0.0.1:{port} pid={p.pid} ledger={ledger}")
        break
    except Exception:
        time.sleep(0.5)
else:
    print("FAILED to start; see", inst / "server.log")
