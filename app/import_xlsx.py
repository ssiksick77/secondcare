"""xlsx 장부 -> SQLite 1회 가져오기 (장부 이전 1회차, 2026-10-20).

    python import_xlsx.py <장부.xlsx> <장부.sqlite> [--author 이메일] [--force]

- 시트 구조 보정(store._ensure_structure)을 메모리에서 적용한 뒤 읽는다. xlsx 파일은 바꾸지 않는다.
- 모든 행의 author 를 --author 로 채운다 (기본: 안윤아 snubh.ai.center.01@gmail.com, 사용자 결정 2026-10-20).
- 메타 시트는 meta 테이블로. 대상 파일이 이미 있으면 --force 없이는 멈춘다.
- 끝나면 시트별 건수와 금액 합계를 찍는다. 수식 셀이 있으면 경고한다 (값으로 읽지 못해 0/문자열로 들어간다).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for _st in (sys.stdout, sys.stderr):  # cp949 콘솔에서 한글이 깨지지 않게
    try:
        _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import openpyxl  # noqa: E402

import db  # noqa: E402
import store  # noqa: E402

DEFAULT_AUTHOR = "snubh.ai.center.01@gmail.com"  # 안윤아


def load_sheets(xlsx: Path) -> tuple[dict[str, list[dict]], dict, list[str]]:
    """{kind: rows}, {meta key: value}, formulas. 행은 store._rows 결과 (_row = 시트 행 번호)."""
    wb = openpyxl.load_workbook(xlsx)
    store._ensure_structure(wb)
    formulas: list[str] = []
    data = {}
    for kind, (sheet, cols) in db.tables().items():
        if sheet not in wb.sheetnames:
            data[kind] = []
            continue
        head = store.BUDGET_HEAD_ROW if kind == "budget" else 1
        rows = store._rows(wb[sheet], cols, head, formulas)
        if kind in db.NULLABLE_NUM:  # 빈 칸과 0 을 구분 (store.read_all 의 _has_value 규칙)
            ws = wb[sheet]
            for r in rows:
                for c in db.NULLABLE_NUM[kind]:
                    if not store._has_value(ws, r["_row"], c):
                        r[c] = None
        data[kind] = rows
    meta = {}
    ws = store._meta_ws(wb)
    if ws is not None:
        for r in range(2, ws.max_row + 1):
            k = str(ws.cell(r, 1).value or "").strip()
            if k:
                meta[k] = ws.cell(r, 2).value
    wb.close()
    return data, meta, formulas


def run(xlsx: Path, sqlite: Path, author: str, force: bool = False) -> dict:
    if not xlsx.exists():
        raise SystemExit(f"장부 파일 없음: {xlsx}")
    if sqlite.exists():
        if not force:
            raise SystemExit(f"대상 파일이 이미 있습니다: {sqlite} (--force 로 덮어쓰기)")
        sqlite.unlink()
        for suf in ("-wal", "-shm"):
            Path(str(sqlite) + suf).unlink(missing_ok=True)
    data, meta, formulas = load_sheets(xlsx)
    summary = {}
    with db.session(sqlite) as con:
        db.create_schema(con)
        for kind, rows in data.items():
            db.insert_rows(con, kind, rows, author)
            amt = sum(float(r.get("금액") or 0) for r in rows) if rows and "금액" in rows[0] else None
            summary[kind] = {"rows": len(rows), "amount": amt}
        for k, v in meta.items():
            db.meta_set(con, k, v)
        db.meta_set(con, "imported_from", str(xlsx))
        db.meta_set(con, "imported_at", db.dt.datetime.now().isoformat(timespec="seconds"))
    summary["_formulas"] = formulas
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xlsx", type=Path)
    ap.add_argument("sqlite", type=Path)
    ap.add_argument("--author", default=DEFAULT_AUTHOR)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    s = run(a.xlsx, a.sqlite, a.author, a.force)
    for kind, v in s.items():
        if kind.startswith("_"):
            continue
        amt = f"  금액 합계 {v['amount']:,.0f}" if v["amount"] is not None else ""
        print(f"{kind:9s} {v['rows']:5d} 건{amt}")
    if s["_formulas"]:
        print(f"[경고] 수식 셀 {len(s['_formulas'])}개: 값으로 읽지 못함 → {', '.join(s['_formulas'][:10])}")
    print(f"완료: {a.sqlite}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
