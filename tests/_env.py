"""검사용 서버 도우미. QA 장부(docs/qa_data_2026_01_09/qa_ledger.xlsx)를 tests/.tmp/ 에 복사해
빈 포트로 app/main.py 를 띄우고, 끝나면 내린다. 실제 장부는 건드리지 않는다.

사용:
    with Server("api") as sv:
        status, body = sv.call("POST", "/api/request", {...})
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

# python -I 는 PYTHONIOENCODING 을 무시하므로 출력 인코딩을 직접 고정 (한글·기호가 cp949 콘솔에서 깨지지 않게)
for _st in (sys.stdout, sys.stderr):
    try:
        _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
QA_DIR = os.path.join(ROOT, "docs", "qa_data_2026_01_09")
QA_XLSX = os.path.join(QA_DIR, "qa_ledger.xlsx")
TMP = os.path.join(ROOT, "tests", ".tmp")


SETTLE = ("import openpyxl, store\n"
          "wb = openpyxl.load_workbook(store.XLSX_PATH)\n"
          "for _ in range(5):\n"
          "    if not store._ensure_structure(wb): break\n"
          "wb.save(store.XLSX_PATH)\n")


def settle_xlsx(xlsx: str):
    """xlsx 장부 복사본에 구조 보정을 끝까지 적용해 저장 (서버가 첫 저장 때 하는 일과 같은 상태로)."""
    pr = subprocess.run([sys.executable, "-c", SETTLE], cwd=APP, env=dict(os.environ, LEDGER_XLSX=xlsx),
                        capture_output=True, text=True, encoding="utf-8")
    if pr.returncode != 0:
        raise SystemExit(f"xlsx 구조 보정 실패: {pr.stderr[-500:]}")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    TEST_EMAIL = "test@example.com"  # LEDGER_AUTH_BYPASS: 검사 서버는 이 이메일로 로그인한 것으로 본다 (구글 호출 없음)

    def __init__(self, name: str, auth_bypass: bool = True):
        self.name = name
        self.auth_bypass = auth_bypass
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.dir = os.path.join(TMP, name)
        self.proc = None

    def __enter__(self):
        if not os.path.exists(QA_XLSX):
            raise SystemExit(f"QA 장부가 없습니다: {QA_XLSX}")
        shutil.rmtree(self.dir, ignore_errors=True)
        os.makedirs(self.dir)
        xlsx = os.path.join(self.dir, "ledger.xlsx")
        shutil.copyfile(QA_XLSX, xlsx)
        # 저장소 종류: LEDGER_TEST_MODE=db 면 QA 장부를 SQLite 로 가져와 그 파일로 서버를 띄운다 (SQLite 이전 검사). 기본은 xlsx
        self.mode = os.environ.get("LEDGER_TEST_MODE", "xlsx")
        self.store_env = {"LEDGER_XLSX": xlsx}
        if self.mode == "db":
            settle_xlsx(xlsx)  # xlsx 보정 로직을 직접 검사하는 probe 가 xlsx 모드와 같은 구조를 보도록
            sqlite = os.path.join(self.dir, "ledger.sqlite")
            pr = subprocess.run([sys.executable, "-I", "import_xlsx.py", xlsx, sqlite], cwd=APP, capture_output=True, text=True, encoding="utf-8")
            if pr.returncode != 0:
                raise SystemExit(f"SQLite 가져오기 실패: {pr.stderr[-500:]}")
            self.store_env["LEDGER_DB"] = sqlite
        env = dict(os.environ, **self.store_env, LEDGER_ENV=os.path.join(QA_DIR, "qa.env"), LEDGER_DRIVE_MOCK="1",
                   LEDGER_DRIVE_MOCK_DIR=os.path.join(self.dir, "mock"), LEDGER_PORT=str(self.port), LEDGER_NO_BROWSER="1",
                   PYTHONIOENCODING="utf-8")
        env.pop("LEDGER_AUTH_BYPASS", None)
        if self.auth_bypass:
            env["LEDGER_AUTH_BYPASS"] = self.TEST_EMAIL
        self.log = open(os.path.join(self.dir, "server.log"), "w", encoding="utf-8")
        self.proc = subprocess.Popen([sys.executable, "main.py"], cwd=APP, env=env, stdout=self.log, stderr=subprocess.STDOUT)
        for _ in range(60):
            try:
                urllib.request.urlopen(self.base + "/api/all", timeout=1)
                return self
            except urllib.error.HTTPError:
                return self  # 응답이 왔으면 서버는 떠 있다 (로그인 우회 없는 서버는 401)
            except Exception:
                if self.proc.poll() is not None:
                    break
                time.sleep(0.5)
        self.__exit__(None, None, None)
        raise SystemExit(f"서버가 뜨지 않았습니다. 로그: {os.path.join(self.dir, 'server.log')}")

    def __exit__(self, *a):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.log.close()

    def call(self, method: str, path: str, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, method=method, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, raw.decode("utf-8", "replace")

    def get_raw(self, path: str):
        """리다이렉트를 따라가지 않고 (상태, Location 헤더) 반환 (로그인 화면 이동 검사용)."""
        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            with opener.open(self.base + path, timeout=5) as r:
                return r.status, r.headers.get("Location")
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Location")

    def row(self, kind: str, row: int) -> dict:
        s, r = self.call("GET", "/api/all")
        return next(x for x in r[kind] if x["_row"] == row)

    def rec(self, kind: str, row: int) -> dict:
        return {k: v for k, v in self.row(kind, row).items() if not k.startswith("_")}


class Check:
    """assert 대신 쓰는 누적 검사. 실패해도 계속 진행하고 마지막에 한꺼번에 보고한다."""

    def __init__(self):
        self.fails = []
        self.n = 0

    def __call__(self, name: str, cond, detail=""):
        self.n += 1
        mark = "ok  " if cond else "FAIL"
        print(f"  {mark} {name}{'' if cond else '  ' + str(detail)}")
        if not cond:
            self.fails.append(name)

    def done(self, title: str) -> int:
        print(f"{title}: {self.n - len(self.fails)}/{self.n} 통과" + (f", 실패: {', '.join(self.fails)}" if self.fails else ""))
        return 1 if self.fails else 0
