"""SQLite 장부 -> xlsx 내보내기 (장부 이전 3회차, 2026-10-20).

    python export_xlsx.py <장부.sqlite> <내보낼.xlsx> [--force]

- 시트·열은 store 의 상수(이전 xlsx 장부와 같은 이름·순서). 예산변동은 8행 머리글과 1~7행 요약, 메타는 숨김 시트.
- 값은 store._write_row 로 쓴다 (날짜·숫자 서식, 수식 주입 방지 규칙이 xlsx 쓰기와 같다).
- 읽기 전용 사본이다: 이 파일을 고쳐도 SQLite 에는 반영되지 않는다. 다시 들여오려면 import_xlsx.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for _st in (sys.stdout, sys.stderr):
    try:
        _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import openpyxl  # noqa: E402
from openpyxl.styles import Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

import db  # noqa: E402
import store  # noqa: E402

# 시트 순서: 이전 장부와 같게 (인건비 → 재원·집행·품의·예산변동 → 적립금·거래처·태그·증빙·보완이력 → 신청·주문·첨부 → 메타)
SHEET_ORDER = ["people", "salary", "payee", "labor", "ladj", "funds", "exec", "req", "budget",
               "deposit", "vendor", "tags", "evidence", "fixlog", "request", "order", "ratt"]
WIDTH_DEFAULT = 13
BUDGET_LABELS = {4: "이월금", 5: "당초액", 6: "변경액", 7: "합계"}


def _new_workbook() -> openpyxl.Workbook:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    head_font = Font(bold=True)
    head_fill = PatternFill("solid", fgColor="E8EEF8")
    tabs = db.tables()
    for kind in SHEET_ORDER:
        sheet, cols = tabs[kind]
        ws = wb.create_sheet(sheet)
        head = store.BUDGET_HEAD_ROW if kind == "budget" else 1
        for i, c in enumerate(cols, 1):
            cell = ws.cell(head, i, c)
            cell.font, cell.fill = head_font, head_fill
            ws.column_dimensions[get_column_letter(i)].width = WIDTH_DEFAULT
        ws.freeze_panes = f"A{head + 1}"
        if kind == "budget":
            for r, label in BUDGET_LABELS.items():
                ws.cell(r, 1, label).font = head_font
    return wb


def run(sqlite: Path, xlsx: Path, force: bool = False) -> dict:
    if not sqlite.exists():
        raise SystemExit(f"SQLite 장부 없음: {sqlite}")
    if xlsx.exists() and not force:
        raise SystemExit(f"대상 파일이 이미 있습니다: {xlsx} (--force 로 덮어쓰기)")
    wb = _new_workbook()
    summary = {}
    with db.session(sqlite) as con:
        tabs = db.tables()
        for kind in SHEET_ORDER:
            sheet, cols = tabs[kind]
            ws = wb[sheet]
            head = store.BUDGET_HEAD_ROW if kind == "budget" else 1
            rows = db.read_rows(con, kind)
            for i, rec in enumerate(rows, 1):
                # 숫자 열의 NULL 은 빈 셀로 (read_rows 는 0 으로 돌려주므로 원본 NULL 여부를 다시 본다)
                raw = con.execute(f"SELECT {', '.join(db._q(c) for c in cols)} FROM {db._q(kind)} WHERE id = ?", (rec["_row"],)).fetchone()
                vals = {c: raw[c] for c in cols}
                store._write_row(ws, cols, head + i, vals, head)
            summary[kind] = len(rows)
        meta = con.execute("SELECT key, value FROM meta WHERE key NOT IN ('schema_version', 'imported_from', 'imported_at', 'write_seq') ORDER BY key").fetchall()
    ws = store._meta_ws(wb, create=True)
    for i, (k, v) in enumerate(meta, 2):
        ws.cell(i, 1, k)
        ws.cell(i, 2, v)
    store._refresh_budget_summary(wb)
    xlsx.parent.mkdir(parents=True, exist_ok=True)
    wb.save(xlsx)
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sqlite", type=Path)
    ap.add_argument("xlsx", type=Path)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    s = run(a.sqlite, a.xlsx, a.force)
    for kind, n in s.items():
        print(f"{kind:9s} {n:5d} 건")
    print(f"완료: {a.xlsx}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
