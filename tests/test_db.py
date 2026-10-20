"""SQLite 이전 검사 (1회차): xlsx -> SQLite 가져오기 뒤 read_all 결과가 xlsx 와 같은지.
QA 장부 복사본(tests/.tmp/db/)에 대해 실행한다: python -I tests/test_db.py
"""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import APP, QA_XLSX, TMP, Check, settle_xlsx  # noqa: E402

AUTHOR = "snubh.ai.center.01@gmail.com"
DUMP = ("import json, os, sys, store\n"
        "d = store.read_all()\n"
        "print(json.dumps(d, ensure_ascii=False, default=str))\n")


def read_all(env: dict) -> dict:
    pr = subprocess.run([sys.executable, "-c", DUMP], cwd=APP, env=dict(os.environ, **env, PYTHONIOENCODING="utf-8"),
                        capture_output=True, text=True, encoding="utf-8")
    if pr.returncode != 0:
        raise SystemExit(pr.stderr[-2000:])
    return json.loads(pr.stdout)


def strip(rows: list[dict]) -> list[dict]:
    """행 번호(xlsx 행 / SQLite id)는 다르므로 뺀다. 순서는 그대로 비교."""
    return [{k: v for k, v in r.items() if k not in ("_row", "_author")} for r in rows]


def main() -> int:
    ck = Check()
    d = os.path.join(TMP, "db")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    xlsx = os.path.join(d, "ledger.xlsx")
    sqlite = os.path.join(d, "ledger.sqlite")
    shutil.copyfile(QA_XLSX, xlsx)
    settle_xlsx(xlsx)  # 가져오기는 보정을 반복 적용하므로 xlsx 쪽도 같은 상태에서 비교

    pr = subprocess.run([sys.executable, "-I", "import_xlsx.py", xlsx, sqlite], cwd=APP, capture_output=True, text=True, encoding="utf-8")
    ck("가져오기 스크립트 종료 코드 0", pr.returncode == 0, pr.stderr[-500:])
    pr2 = subprocess.run([sys.executable, "-I", "import_xlsx.py", xlsx, sqlite], cwd=APP, capture_output=True, text=True, encoding="utf-8")
    ck("대상 파일이 있으면 --force 없이 거부", pr2.returncode != 0 and "--force" in (pr2.stderr + pr2.stdout), pr2.stdout[-200:])

    a = read_all({"LEDGER_XLSX": xlsx})
    b = read_all({"LEDGER_XLSX": xlsx, "LEDGER_DB": sqlite})
    kinds = [k for k in a if k != "meta"]
    for k in kinds:
        ck(f"{k}: 건수 같음 ({len(a[k])})", len(a[k]) == len(b[k]), (len(a[k]), len(b[k])))
        if a[k] and "금액" in a[k][0]:
            sa, sb = sum(r["금액"] for r in a[k]), sum(r["금액"] for r in b[k])
            ck(f"{k}: 금액 합계 같음 ({sa:,.0f})", sa == sb, (sa, sb))
        diff = [(i, x, y) for i, (x, y) in enumerate(zip(strip(a[k]), strip(b[k]))) if x != y]
        ck(f"{k}: 모든 열 값 같음", not diff, diff[:2])
    ck("SQLite 행의 _row 는 1부터 순서대로 (id)", all(r["_row"] == i + 1 for r in b["exec"] for i in [b["exec"].index(r)]))
    ck("모든 행 author = 가져오기 작성자", all(r["_author"] == AUTHOR for k in kinds for r in b[k]))
    # _locked_by 는 적립금 _row 기준으로 붙는다: 주문에 연결된 행 수가 같아야 한다
    la = [r.get("_locked_by") for r in a["deposit"]]
    lb = [r.get("_locked_by") for r in b["deposit"]]
    ck("deposit: 주문 잠금(_locked_by) 같음", la == lb, (la, lb))
    ck("meta.file 은 SQLite 경로", b["meta"]["file"].endswith("ledger.sqlite") and b["meta"]["formula_count"] == 0, b["meta"].get("file"))

    # ---- 쓰기 → 백업 파일 생성, 되돌리기 → 행 사라짐, 그 뒤 다른 변경이 있으면 거부 ----
    undo = ("import os, store, db\n"
            "n0 = len(store.read_all()['exec']); s0 = store.data_stamp()\n"
            "r = store.create('exec', {'재원': 'QA01', '예산목': '연구활동비', '원인발생일': '2026-03-05', '거래처': '검사', '금액': 7000, '적요': '되돌리기 검사'})\n"
            "assert os.path.exists(store.LAST_WRITE['backup']), store.LAST_WRITE\n"
            "assert store.data_stamp() != s0 and len(store.read_all()['exec']) == n0 + 1\n"
            "wid = store.last_write_id(); store.undo_last(wid)\n"
            "assert len(store.read_all()['exec']) == n0 and store.data_stamp() == s0, store.data_stamp()\n"
            "store.create('exec', {'재원': 'QA01', '예산목': '연구활동비', '원인발생일': '2026-03-06', '거래처': '검사', '금액': 1, '적요': 'a'})\n"
            "wid = store.last_write_id()\n"
            "store.update('tags', store.read_all()['tags'][0]['_row'], {**{k: v for k, v in store.read_all()['tags'][0].items() if not k.startswith('_')}, '설명': 'x'})\n"
            "try:\n    store.undo_last(wid); raise SystemExit('stale undo accepted')\n"
            "except ValueError:\n    pass\n"
            "con = db.connect(); acts = [r['action'] for r in con.execute('SELECT action FROM changelog ORDER BY id')]; con.close()\n"
            "assert acts == ['create', 'update'], acts\n"  # 되돌린 첫 쓰기의 기록은 백업 복원으로 함께 사라진다
            "print('ok')\n")
    pr = subprocess.run([sys.executable, "-c", undo], cwd=APP, env=dict(os.environ, LEDGER_XLSX=xlsx, LEDGER_DB=sqlite, PYTHONIOENCODING="utf-8"),
                        capture_output=True, text=True, encoding="utf-8")
    ck("쓰기 → 백업 생성, 되돌리기 동작, 오래된 되돌리기 거부, changelog 기록", pr.returncode == 0 and pr.stdout.strip().endswith("ok"), pr.stderr[-600:])
    return ck.done("db")


if __name__ == "__main__":
    sys.exit(main())
