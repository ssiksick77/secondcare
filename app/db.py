"""SQLite 저장소 (장부 이전 1회차, 2026-10-20).

한 시트 = 한 테이블. 열 이름은 시트 머리글(한글) 그대로. 모든 테이블에 id(고유 번호)와 author(작성자 이메일)가 있다.
값 규칙 (가져오기 때 적용, 읽을 때 되돌림):
  - 빈 셀은 NULL. 숫자 열(store.NUM_COLS)은 REAL, 그 밖은 선언 없음(파이썬 값 그대로: 변경회차 1 은 1, '이월'은 '이월').
  - 날짜 열은 'YYYY-MM-DD' 문자열, 월 열은 'YYYY-MM', 부가세구분은 'Y'/'N'.
메타 시트는 meta(key, value) 테이블, 변경 기록은 changelog 테이블 (쓰기 경로는 2회차에서 연결).
"""
from __future__ import annotations

import contextlib
import datetime as dt
import os
import sqlite3
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DB_ENV = "LEDGER_DB"
DB_PATH = Path(os.environ.get(DB_ENV) or (APP_DIR.parent / "의료인공지능센터_지출장부_2026.sqlite"))

# kind -> (시트 이름, 열 목록). store 의 상수와 같게 유지한다 (import 순환을 피하려 여기서 늦게 읽는다)
AUTHOR_COL = "author"
SCHEMA_VERSION = 1


def tables() -> dict[str, tuple[str, list[str]]]:
    import store as st
    return {
        "funds": (st.SHEET_FUND, st.FUND_COLS),
        "budget": (st.SHEET_BUDGET, st.BUDGET_COLS),
        "exec": (st.SHEET_EXEC, st.EXEC_COLS),
        "req": (st.SHEET_REQ, st.REQ_COLS),
        "deposit": (st.SHEET_DEP, st.DEP_COLS),
        "vendor": (st.SHEET_VENDOR, st.VENDOR_COLS),
        "tags": (st.SHEET_TAG, st.TAG_COLS),
        "evidence": (st.SHEET_EVID, st.EVID_COLS),
        "people": (st.SHEET_PEOPLE, st.PEOPLE_COLS),
        "salary": (st.SHEET_SALARY, st.SALARY_COLS),
        "payee": (st.SHEET_PAYEE, st.PAYEE_COLS),
        "labor": (st.SHEET_LABOR, st.LABOR_COLS),
        "ladj": (st.SHEET_LADJ, st.LADJ_COLS),
        "request": (st.SHEET_RQ, st.REQUEST_COLS),
        "order": (st.SHEET_ORDER, st.ORDER_COLS),
        "ratt": (st.SHEET_RATT, st.RATT_COLS),
        "fixlog": (st.SHEET_FIXLOG, st.FIXLOG_COLS),
    }


def _q(name: str) -> str:
    """식별자 인용 (한글 열 이름, 예약어 order 등)."""
    return '"' + name.replace('"', '""') + '"'


def _col_type(col: str) -> str:
    import store as st
    return " REAL" if col in st.NUM_COLS else ""


def connect(path: Path | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(str(path or DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con


def create_schema(con: sqlite3.Connection):
    """테이블이 없으면 만든다. 있는 테이블은 건드리지 않는다."""
    for kind, (_sheet, cols) in tables().items():
        body = ", ".join(f"{_q(c)}{_col_type(c)}" for c in cols)
        con.execute(f"CREATE TABLE IF NOT EXISTS {_q(kind)} (id INTEGER PRIMARY KEY AUTOINCREMENT, {body}, {AUTHOR_COL} TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value)")
    con.execute("CREATE TABLE IF NOT EXISTS changelog (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, "
                f"{AUTHOR_COL} TEXT, kind TEXT NOT NULL, row_id INTEGER, action TEXT NOT NULL, detail TEXT)")
    con.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)", (SCHEMA_VERSION,))
    con.commit()


@contextlib.contextmanager
def session(path: Path | None = None):
    con = connect(path)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _in(col: str, v):
    """읽은 셀 값(store._cell_out 결과) -> DB 값. 빈 값은 NULL."""
    if v is None or v == "":
        return None
    return v


def insert_rows(con: sqlite3.Connection, kind: str, rows: list[dict], author: str | None) -> list[int]:
    """행 목록을 넣고 id 목록을 돌려준다. rows 의 '_'로 시작하는 키는 무시."""
    cols = tables()[kind][1]
    sql = f"INSERT INTO {_q(kind)} ({', '.join(_q(c) for c in cols)}, {AUTHOR_COL}) VALUES ({', '.join('?' * (len(cols) + 1))})"
    ids = []
    for r in rows:
        cur = con.execute(sql, [_in(c, r.get(c)) for c in cols] + [author])
        ids.append(cur.lastrowid)
    return ids


def _out(col: str, v, none_num: bool):
    """DB 값 -> API 값 (store._cell_out 과 같은 모양). 숫자 열의 NULL 은 0 (none_num=True 면 None 유지)."""
    import store as st
    if v is None:
        if col in st.NUM_COLS:
            return None if none_num else 0
        if col in st.DATE_COLS:  # store._to_date(None) 과 같게
            return None
        return "" if col != "부가세구분" else "N"
    if col in st.NUM_COLS:
        return int(v) if float(v).is_integer() else v
    return v


# 숫자 열 중 '비어 있음'과 0 을 구분해 읽는 열 (store.read_all 의 _has_value 와 같음)
NULLABLE_NUM = {"funds": {"인건비예산"}, "payee": {"인건비예산"}}


def read_rows(con: sqlite3.Connection, kind: str) -> list[dict]:
    cols = tables()[kind][1]
    nullable = NULLABLE_NUM.get(kind, set())
    out = []
    for row in con.execute(f"SELECT id, {', '.join(_q(c) for c in cols)}, {AUTHOR_COL} FROM {_q(kind)} ORDER BY id"):
        rec = {"_row": row["id"]}
        for c in cols:
            rec[c] = _out(c, row[c], c in nullable)
        rec["_author"] = row[AUTHOR_COL] or ""
        out.append(rec)
    return out


def meta_get(con: sqlite3.Connection, key: str):
    r = con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return None if r is None else r[0]


def meta_set(con: sqlite3.Connection, key: str, value):
    con.execute("INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))


def log_change(con: sqlite3.Connection, kind: str, row_id: int | None, action: str, author: str | None, detail: str = ""):
    con.execute("INSERT INTO changelog (at, author, kind, row_id, action, detail) VALUES (?, ?, ?, ?, ?, ?)",
                (dt.datetime.now().isoformat(timespec="seconds"), author, kind, row_id, action, detail))


def file_mtime(path: Path | None = None) -> str:
    p = path or DB_PATH
    return dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds") if p.exists() else ""


# ---------- 워크북 어댑터 (store 의 쓰기 경로가 openpyxl 워크북 대신 쓴다, 2회차 2026-10-20) ----------
class Sheet:
    """시트 하나 = 테이블 하나. 행 번호 자리에 id 를 쓴다."""

    def __init__(self, con: sqlite3.Connection, kind: str, title: str, cols: list[str], author: str | None):
        self.con, self.kind, self.title, self.cols, self.author = con, kind, title, cols, author

    @property
    def max_row(self) -> int:
        r = self.con.execute(f"SELECT MAX(id) FROM {_q(self.kind)}").fetchone()[0]
        return int(r or 0)

    def rows(self) -> list[dict]:
        return read_rows(self.con, self.kind)

    def exists(self, row_id: int) -> bool:
        return self.con.execute(f"SELECT 1 FROM {_q(self.kind)} WHERE id = ?", (row_id,)).fetchone() is not None

    def new_row(self) -> int:
        cur = self.con.execute(f"INSERT INTO {_q(self.kind)} ({AUTHOR_COL}) VALUES (?)", (self.author,))
        return cur.lastrowid

    def write(self, row_id: int, values: dict):
        """values: {열: DB 값}. 없는 열은 건드리지 않는다. 행이 없으면 ValueError."""
        if not values:
            return
        sets = ", ".join(f"{_q(c)} = ?" for c in values)
        cur = self.con.execute(f"UPDATE {_q(self.kind)} SET {sets}, {AUTHOR_COL} = COALESCE(?, {AUTHOR_COL}) WHERE id = ?",
                               [*values.values(), self.author, row_id])
        if cur.rowcount != 1:
            raise ValueError(f"{self.title} 행 {row_id} 이 없습니다.")

    def delete(self, row_id: int):
        self.con.execute(f"DELETE FROM {_q(self.kind)} WHERE id = ?", (row_id,))

    def has_value(self, row_id: int, col: str) -> bool:
        if col not in self.cols:
            return False
        r = self.con.execute(f"SELECT {_q(col)} IS NOT NULL FROM {_q(self.kind)} WHERE id = ?", (row_id,)).fetchone()
        return bool(r and r[0])

    def replace_value(self, col: str, old, new) -> int:
        cur = self.con.execute(f"UPDATE {_q(self.kind)} SET {_q(col)} = ? WHERE {_q(col)} = ?", (new, old))
        return cur.rowcount


class Workbook:
    """store 의 쓰기 함수가 받는 wb 자리. wb[시트이름] -> Sheet, wb.sheetnames."""

    def __init__(self, con: sqlite3.Connection, author: str | None = None):
        self.con, self.author = con, author
        self._by_title = {sheet: (kind, cols) for kind, (sheet, cols) in tables().items()}
        self._sheets: dict[str, Sheet] = {}

    @property
    def sheetnames(self) -> list[str]:
        return list(self._by_title)

    def __contains__(self, title: str) -> bool:
        return title in self._by_title

    def __getitem__(self, title: str) -> Sheet:
        if title not in self._sheets:
            kind, cols = self._by_title[title]
            self._sheets[title] = Sheet(self.con, kind, title, cols, self.author)
        return self._sheets[title]


def backup_to(path: Path, src_path: Path | None = None):
    """커밋된 상태를 path 로 복사 (WAL 포함). 쓰기 중인 연결과 별개의 연결로 읽는다."""
    src = sqlite3.connect(str(src_path or DB_PATH))
    dst = sqlite3.connect(str(path))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def restore_from(path: Path, dst_path: Path | None = None):
    """백업 파일의 내용으로 DB 를 통째로 덮는다 (온라인 복원)."""
    src = sqlite3.connect(str(path))
    dst = sqlite3.connect(str(dst_path or DB_PATH))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def write_seq(path: Path | None = None) -> int:
    con = sqlite3.connect(str(path or DB_PATH))
    try:
        r = con.execute("SELECT value FROM meta WHERE key = 'write_seq'").fetchone()
        return int(r[0]) if r and r[0] is not None else 0
    finally:
        con.close()
