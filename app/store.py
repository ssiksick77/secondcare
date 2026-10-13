"""xlsx 파일을 원본(source of truth)으로 사용하는 저장소 계층."""
from __future__ import annotations

import contextlib
import datetime as dt
import os
import re
import shutil
import threading
import time
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.utils.datetime import from_excel

APP_DIR = Path(__file__).resolve().parent
XLSX_PATH = Path(os.environ.get("LEDGER_XLSX", APP_DIR.parent / "의료인공지능센터_지출장부_2026.xlsx"))
BACKUP_DIR = APP_DIR / "backup"
BACKUP_KEEP = 30
LOCK_TIMEOUT = 15  # 초: 다른 프로세스(MCP 서버 등)가 쓰는 동안 대기

SHEET_FUND = "재원"
SHEET_BUDGET = "예산변동"
SHEET_EXEC = "집행내역"
SHEET_REQ = "품의내역"
SHEET_DEP = "적립금"
SHEET_TAG = "태그"
SHEET_EVID = "증빙"

BUDGET_ITEMS = [
    "내부인건비(공통)", "외부인건비(공통)", "연구시설.장비비", "연구활동비",
    "연구재료비", "연구수당", "위탁연구개발비", "간접비(공통)", "발생이자",
]
PAY_METHODS = ["연구비카드", "계좌이체", "연구자선지출", "공금통장", "적립금", "기타"]
REQ_STATUS = ["대기", "집행완료", "취소"]
BUDGET_ROUNDS = ["이월", "당초"]  # 그 외에는 1,2,3... 숫자 회차

FUND_COLS = ["재원코드", "과제명", "시작일", "종료일", "비고"]
EXEC_COLS = ["거래번호", "관리번호", "원인발생일", "지급청구일", "지출완료일", "재원", "예산목", "세목",
             "세세목", "거래처", "적요", "금액", "사용자", "태그", "비고", "상태", "증빙폴더", "증빙목록"]
EXEC_STATUS = ["발생", "청구", "보완", "완료"]  # 날짜에서 계산, '보완'만 수동
REQ_COLS = ["품의번호", "원인발생일", "지출예정일", "재원", "예산목", "세목", "세세목", "거래처",
            "결제수단", "적요", "금액", "태그", "품의자", "비고", "상태"]
DEP_COLS = ["일자", "거래처", "구분", "금액", "적요", "사용자", "증빙번호", "연결거래번호", "비고", "태그"]
TAG_COLS = ["태그명", "분류", "설명"]
EVID_COLS = ["거래번호", "증빙종류", "파일명", "원본파일명", "드라이브파일ID", "크기", "업로드일", "비고"]
DEP_TYPES = ["적립", "사용"]
BUDGET_HEAD_ROW = 8
BUDGET_COLS = ["재원", "변경회차", "신청일자", "변경사유"] + BUDGET_ITEMS  # A~D + E~M

DATE_COLS = {"원인발생일", "지급청구일", "지출완료일", "시작일", "종료일", "신청일자", "지출예정일", "일자"}
NUM_COLS = {"금액"} | set(BUDGET_ITEMS)
# 행 식별(동시 수정·행 밀림 감지)에 쓰는 열: 키가 없는 시트는 내용 조합
IDENT_COLS = {
    "funds": ["재원코드"], "exec": ["거래번호"], "req": ["품의번호"], "tags": ["태그명"],
    "budget": ["재원", "변경회차", "신청일자"], "deposit": ["일자", "거래처", "구분", "금액"],
    "evidence": ["거래번호", "파일명"],
}

_lock = threading.RLock()


class LedgerLocked(Exception):
    pass


class NotFound(Exception):
    pass


# ---------- 값 변환 ----------
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _to_date(v: Any) -> str | None:
    """셀/입력값 -> 'YYYY-MM-DD'. 해석 불가하면 원문 문자열(검증 단계에서 거부)."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, dt.datetime):
        return v.date().isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, (int, float)):  # 엑셀 일련번호
        try:
            return from_excel(v).date().isoformat()
        except Exception:
            return str(v)
    s = str(v).strip()
    m = re.match(r"^(\d{4})[-./](\d{1,2})[-./](\d{1,2})$", s)
    if not m:
        m = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
    if m:
        try:
            return dt.date(int(m[1]), int(m[2]), int(m[3])).isoformat()
        except ValueError:
            return s
    return s or None


def _valid_date(v: Any) -> bool:
    d = _to_date(v)
    if d is None:
        return True
    if not _ISO.match(d):
        return False
    try:
        dt.date.fromisoformat(d)
        return True
    except ValueError:
        return False


def _is_formula(v: Any) -> bool:
    return isinstance(v, str) and v.startswith("=")


def _to_num(v: Any, strict: bool = False) -> float:
    """셀/입력값 -> 숫자. strict=True 면 해석 불가 시 ValueError, 아니면 0."""
    if v is None or v == "":
        return 0
    if isinstance(v, bool):
        if strict:
            raise ValueError("금액이 올바르지 않습니다.")
        return 0
    if isinstance(v, (int, float)):
        return v
    s = re.sub(r"[,\s원]", "", str(v))
    try:
        return float(s)
    except ValueError:
        if strict:
            raise ValueError(f"금액 '{v}' 을(를) 숫자로 해석할 수 없습니다.")
        return 0


def _cell_in(col: str, v: Any) -> Any:
    """API 값 -> 셀 값"""
    if v is None or v == "":
        return None
    if col in DATE_COLS:
        d = _to_date(v)
        if d and _ISO.match(d):
            return dt.date.fromisoformat(d)
        return d
    if col in NUM_COLS:
        n = _to_num(v, strict=True)
        return int(n) if float(n).is_integer() else n
    if col == "변경회차":
        s = str(v).strip()
        return int(s) if s.isdigit() else s
    return str(v) if not isinstance(v, str) else v


def _cell_out(col: str, v: Any) -> Any:
    if col in DATE_COLS:
        return _to_date(v)
    if col in NUM_COLS:
        return _to_num(v)
    if v is None:
        return ""
    if isinstance(v, (dt.date, dt.datetime)):
        return _to_date(v)
    return str(v) if not isinstance(v, (int, float)) else v


# ---------- 파일 잠금 (프로세스 간: 웹앱 ↔ MCP 서버) ----------
@contextlib.contextmanager
def _file_lock():
    """장부 옆 .lock 파일로 배타 잠금. Windows 는 msvcrt, 그 외는 fcntl."""
    lock_path = XLSX_PATH.with_suffix(XLSX_PATH.suffix + ".lock")
    fh = open(lock_path, "a+b")
    deadline = time.monotonic() + LOCK_TIMEOUT
    try:
        if os.name == "nt":
            import msvcrt
            while True:
                try:
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise LedgerLocked("다른 프로그램(MCP 서버 등)이 장부를 쓰는 중입니다. 잠시 후 다시 시도하세요.")
                    time.sleep(0.2)
        else:
            import fcntl
            while True:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise LedgerLocked("다른 프로그램(MCP 서버 등)이 장부를 쓰는 중입니다. 잠시 후 다시 시도하세요.")
                    time.sleep(0.2)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        fh.close()


@contextlib.contextmanager
def _write_session():
    """쓰기 작업 공통: 스레드 잠금 + 파일 잠금 + 워크북 로드/구조 보정."""
    with _lock, _file_lock():
        wb = _load()
        _ensure_structure(wb)
        yield wb


# ---------- 워크북 로드 / 저장 ----------
def _load():
    if not XLSX_PATH.exists():
        raise FileNotFoundError(f"장부 파일 없음: {XLSX_PATH}")
    return openpyxl.load_workbook(XLSX_PATH)


def _ensure_structure(wb) -> bool:
    """필요한 시트/열이 없으면 추가. 변경 여부 반환."""
    changed = False
    head_font = Font(bold=True)
    head_fill = PatternFill("solid", fgColor="E8EEF8")

    if SHEET_FUND not in wb.sheetnames:
        ws = wb.create_sheet(SHEET_FUND, 1)
        for i, c in enumerate(FUND_COLS, 1):
            cell = ws.cell(1, i, c)
            cell.font, cell.fill = head_font, head_fill
        for col, w in zip("ABCDE", (14, 40, 12, 12, 30)):
            ws.column_dimensions[col].width = w
        ws.freeze_panes = "A2"
        changed = True

    if SHEET_DEP not in wb.sheetnames:
        ws = wb.create_sheet(SHEET_DEP)
        for i, c in enumerate(DEP_COLS, 1):
            cell = ws.cell(1, i, c)
            cell.font, cell.fill = head_font, head_fill
        for col, w in zip("ABCDEFGHIJ", (12, 20, 8, 14, 30, 10, 16, 18, 24, 14)):
            ws.column_dimensions[col].width = w
        ws.freeze_panes = "A2"
        changed = True

    if SHEET_TAG not in wb.sheetnames:
        ws = wb.create_sheet(SHEET_TAG)
        for i, c in enumerate(TAG_COLS, 1):
            cell = ws.cell(1, i, c)
            cell.font, cell.fill = head_font, head_fill
        for col, w in zip("ABC", (18, 14, 40)):
            ws.column_dimensions[col].width = w
        ws.freeze_panes = "A2"
        changed = True

    if SHEET_EVID not in wb.sheetnames:
        ws = wb.create_sheet(SHEET_EVID)
        for i, c in enumerate(EVID_COLS, 1):
            cell = ws.cell(1, i, c)
            cell.font, cell.fill = head_font, head_fill
        for col, w in zip("ABCDEFGH", (18, 14, 44, 30, 36, 10, 12, 20)):
            ws.column_dimensions[col].width = w
        ws.freeze_panes = "A2"
        changed = True

    for sheet, col_name, width in ((SHEET_REQ, "상태", 10), (SHEET_DEP, "태그", 14),
                                   (SHEET_EXEC, "상태", 8), (SHEET_EXEC, "증빙폴더", 30), (SHEET_EXEC, "증빙목록", 30)):
        ws = wb[sheet]
        heads = _headers(ws)
        if col_name not in heads:
            col = len(heads) + 1  # 후행 빈 헤더만 제거된 길이 → 중간 빈 헤더가 있어도 덮어쓰지 않음
            cell = ws.cell(1, col, col_name)
            cell.font = head_font
            ws.column_dimensions[get_column_letter(col)].width = width
            changed = True

    for name in (SHEET_EXEC, SHEET_REQ):
        ws = wb[name]
        a2 = ws.cell(2, 1).value
        if isinstance(a2, str) and a2.startswith("YYYY-") and all(
            ws.cell(2, i).value in (None, "") for i in range(2, ws.max_column + 1)
        ):
            ws.cell(2, 1).value = None
            changed = True
        if ws.freeze_panes != "A2":
            ws.freeze_panes = "A2"
            changed = True

    ws = wb[SHEET_BUDGET]
    for i, c in enumerate(BUDGET_COLS, 1):
        if ws.cell(BUDGET_HEAD_ROW, i).value != c:
            ws.cell(BUDGET_HEAD_ROW, i, c).font = head_font
            changed = True
    return changed


def _backup():
    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dst = BACKUP_DIR / f"{XLSX_PATH.stem}_{stamp}.xlsx"
    shutil.copy2(XLSX_PATH, dst)
    olds = sorted(BACKUP_DIR.glob(f"{XLSX_PATH.stem}_*.xlsx"))
    for p in olds[:-BACKUP_KEEP]:
        p.unlink(missing_ok=True)


def _check_writable():
    """엑셀 등 다른 프로그램이 파일을 점유 중인지 실제 쓰기 열기로 확인."""
    try:
        with open(XLSX_PATH, "r+b"):
            pass
    except PermissionError as e:
        hint = " (엑셀에서 열려 있음)" if XLSX_PATH.with_name("~$" + XLSX_PATH.name).exists() else ""
        raise LedgerLocked(f"장부 파일이 다른 프로그램에서 열려 있어 저장할 수 없습니다{hint}. 닫은 뒤 다시 시도하세요.") from e


def _save(wb):
    _check_writable()
    _backup()
    tmp = XLSX_PATH.with_suffix(".tmp.xlsx")
    try:
        wb.save(tmp)
        os.replace(tmp, XLSX_PATH)
    except PermissionError as e:
        tmp.unlink(missing_ok=True)
        raise LedgerLocked("장부 파일에 쓸 수 없습니다. 다른 프로그램에서 열려 있는지 확인하세요.") from e


def _headers(ws, row=1) -> list[str]:
    heads = []
    for i in range(1, ws.max_column + 1):
        v = ws.cell(row, i).value
        heads.append(str(v).strip() if v not in (None, "") else "")
    while heads and not heads[-1]:
        heads.pop()
    return heads


def _rows(ws, cols: list[str], head_row=1, formulas: list | None = None) -> list[dict]:
    heads = _headers(ws, head_row)
    idx = {h: i + 1 for i, h in enumerate(heads) if h}
    out = []
    for r in range(head_row + 1, ws.max_row + 1):
        if all(ws.cell(r, i).value in (None, "") for i in idx.values()):
            continue
        rec = {"_row": r}
        for c in cols:
            if c in idx:
                raw = ws.cell(r, idx[c]).value
                if formulas is not None and (c in NUM_COLS or c in DATE_COLS) and _is_formula(raw):
                    formulas.append(f"{ws.title}!{get_column_letter(idx[c])}{r}")
                rec[c] = _cell_out(c, raw)
            else:
                rec[c] = 0 if c in NUM_COLS else ""
        out.append(rec)
    return out


def _write_row(ws, cols: list[str], r: int, rec: dict, head_row=1):
    heads = _headers(ws, head_row)
    idx = {h: i + 1 for i, h in enumerate(heads) if h}
    for c in cols:
        if c not in idx or c not in rec:
            continue
        cell = ws.cell(r, idx[c])
        cell.value = _cell_in(c, rec[c])  # None 도 대입해 '비우기'가 저장되게 함
        if c in DATE_COLS:
            cell.number_format = "yyyy-mm-dd"
        elif c in NUM_COLS:
            cell.number_format = "#,##0"
        if c in ("적요", "비고", "변경사유"):
            cell.alignment = Alignment(wrap_text=False)


def _next_row(ws, head_row=1) -> int:
    r = ws.max_row
    while r > head_row and all(ws.cell(r, i).value in (None, "") for i in range(1, ws.max_column + 1)):
        r -= 1
    return r + 1


def _delete_row(ws, r: int):
    ws.delete_rows(r, 1)


# ---------- 공개 API ----------
def init_file():
    with _lock, _file_lock():
        wb = _load()
        if _ensure_structure(wb):
            _save(wb)


def read_all() -> dict:
    with _lock:
        wb = _load()
        _ensure_structure(wb)  # 메모리 상 보정 (저장은 쓰기 시)
        formulas: list[str] = []
        data = {
            "funds": _rows(wb[SHEET_FUND], FUND_COLS, 1, formulas),
            "budget": _rows(wb[SHEET_BUDGET], BUDGET_COLS, BUDGET_HEAD_ROW, formulas),
            "exec": _rows(wb[SHEET_EXEC], EXEC_COLS, 1, formulas),
            "req": _rows(wb[SHEET_REQ], REQ_COLS, 1, formulas),
            "deposit": _rows(wb[SHEET_DEP], DEP_COLS, 1, formulas),
            "tags": _rows(wb[SHEET_TAG], TAG_COLS, 1, formulas),
            "evidence": _rows(wb[SHEET_EVID], EVID_COLS, 1, formulas),
        }
        for r in data["exec"]:  # 상태는 날짜에서 계산 (시트 값은 '보완' 표시용)
            r["상태"] = exec_status(r)
        data["meta"] = {
            "dep_types": DEP_TYPES,
            "budget_items": BUDGET_ITEMS,
            "pay_methods": PAY_METHODS,
            "req_status": REQ_STATUS,
            "file": str(XLSX_PATH),
            "mtime": dt.datetime.fromtimestamp(XLSX_PATH.stat().st_mtime).isoformat(timespec="seconds"),
            "locked": XLSX_PATH.with_name("~$" + XLSX_PATH.name).exists(),
            # 수식 셀은 값으로 읽을 수 없어 0/문자열로 취급됨 → 화면에 경고
            "formula_cells": formulas[:20],
            "formula_count": len(formulas),
        }
        return data


_SHEETS = {
    "funds": (SHEET_FUND, FUND_COLS, 1, "재원코드"),
    "exec": (SHEET_EXEC, EXEC_COLS, 1, "거래번호"),
    "req": (SHEET_REQ, REQ_COLS, 1, "품의번호"),
    "budget": (SHEET_BUDGET, BUDGET_COLS, BUDGET_HEAD_ROW, None),
    "deposit": (SHEET_DEP, DEP_COLS, 1, None),
    "tags": (SHEET_TAG, TAG_COLS, 1, "태그명"),
    "evidence": (SHEET_EVID, EVID_COLS, 1, None),
}


def exec_status(rec: dict) -> str:
    """발생(청구일 없음) → 청구(지급청구일) → 보완(수동) → 완료(지출완료일). 날짜가 우선."""
    if rec.get("지출완료일"):
        return "완료"
    if rec.get("지급청구일"):
        return "보완" if str(rec.get("상태") or "") == "보완" else "청구"
    return "발생"


def _ident(kind: str, rec: dict) -> dict:
    return {c: _cell_out(c, rec.get(c)) for c in IDENT_COLS[kind]}


def _check_expect(kind: str, existing: dict, expect: dict | None):
    """클라이언트가 보던 행과 실제 행이 같은지 확인 (다른 창/MCP 에서 행이 밀린 경우 감지)."""
    if not expect:
        return
    for c in IDENT_COLS[kind]:
        if c in expect and _cell_out(c, expect[c]) != existing.get(c):
            raise NotFound("다른 곳에서 장부가 바뀌어 행이 일치하지 않습니다. 새로고침 후 다시 시도하세요.")


def _number_refs(wb, key: str) -> set[str]:
    """시트 밖에서 참조되는 번호 (삭제된 번호가 재사용되지 않도록)."""
    refs = set()
    if key == "거래번호":
        for r in _rows(wb[SHEET_DEP], DEP_COLS):
            if r.get("연결거래번호"):
                refs.add(str(r["연결거래번호"]))
    elif key == "품의번호":
        for r in _rows(wb[SHEET_EXEC], EXEC_COLS):
            m = re.search(r"품의 (\d{4}-.+?-\d+)", str(r.get("비고") or ""))
            if m:
                refs.add(m[1])
    return refs


def _assign_number(wb, ws, cols, head_row, key, rec):
    """YYYY-재원코드-NNN 자동 부여 (재원별·연도별 일련번호, 참조된 번호는 재사용하지 않음)."""
    fund = str(rec.get("재원") or "").strip()
    d = _to_date(rec.get("원인발생일")) or dt.date.today().isoformat()
    year = d[:4]
    prefix = f"{year}-{fund}-"
    mx = 0
    seen = [str(row.get(key) or "") for row in _rows(ws, cols, head_row)] + list(_number_refs(wb, key))
    for v in seen:
        if v.startswith(prefix):
            m = re.match(r"^(\d{4})-(.+)-(\d+)$", v)
            if m and m[2] == fund and m[1] == year:
                mx = max(mx, int(m[3]))
    rec[key] = f"{prefix}{mx + 1:03d}"


def _same_key(a, b) -> bool:
    return str(a or "").strip().casefold() == str(b or "").strip().casefold()


def _check_budget_round(rec: dict, others: list[dict]):
    """같은 재원의 '이월'·'당초'는 1건만, 숫자 회차는 중복 금지."""
    rnd = str(rec.get("변경회차") or "").strip()
    fund = str(rec.get("재원") or "").strip()
    for r in others:
        if r["재원"] == fund and str(r["변경회차"]).strip() == rnd:
            what = f"'{rnd}'" if rnd in BUDGET_ROUNDS else f"{rnd}회차"
            raise ValueError(f"재원 {fund} 의 {what} 예산이 이미 있습니다. 기존 행을 수정하거나 다른 회차를 쓰세요.")


def next_budget_round(fund: str) -> str:
    """해당 재원의 다음 변경 회차 번호 (당초 없으면 '당초')."""
    rows = [r for r in read_all()["budget"] if r["재원"] == fund]
    if not any(str(r["변경회차"]) == "당초" for r in rows):
        return "당초"
    nums = [int(str(r["변경회차"])) for r in rows if str(r["변경회차"]).isdigit()]
    return str(max(nums) + 1 if nums else 1)


def _validate_tag(rec: dict, wb):
    """태그는 태그 마스터에 있는 값 1개만 허용 (마스터가 비어 있으면 자유 입력)."""
    t = str(rec.get("태그") or "").strip()
    rec["태그"] = t
    if not t:
        return
    names = {r["태그명"] for r in _rows(wb[SHEET_TAG], TAG_COLS)}
    if names and t not in names:
        raise ValueError(f"'{t}' 는 태그 목록에 없습니다. 태그 탭에서 먼저 등록하세요.")


def _validate_dates(rec: dict, cols):
    for c in cols:
        if c in DATE_COLS and rec.get(c) not in (None, "") and not _valid_date(rec[c]):
            raise ValueError(f"{c} 형식이 올바르지 않습니다 (YYYY-MM-DD): {rec[c]}")


def _validate(kind: str, rec: dict):
    cols = _SHEETS[kind][1]
    _validate_dates(rec, cols)
    if kind == "evidence":
        if not str(rec.get("거래번호") or "").strip() or not str(rec.get("파일명") or "").strip():
            raise ValueError("거래번호와 파일명은 필수입니다.")
        return
    if kind == "exec":
        rec["상태"] = exec_status(rec)  # 날짜 우선, '보완'만 유지
    for c in cols:
        if c in NUM_COLS and rec.get(c) not in (None, ""):
            _to_num(rec[c], strict=True)
    if kind == "tags":
        if not str(rec.get("태그명") or "").strip():
            raise ValueError("태그명은 필수입니다.")
        if "," in str(rec["태그명"]):
            raise ValueError("태그명에는 쉼표를 쓸 수 없습니다.")
    elif kind == "funds":
        if not str(rec.get("재원코드") or "").strip():
            raise ValueError("재원코드는 필수입니다.")
        if "-" in str(rec["재원코드"]):
            raise ValueError("재원코드에는 '-'를 사용할 수 없습니다 (번호 체계와 충돌).")
    elif kind in ("exec", "req"):
        if not str(rec.get("재원") or "").strip():
            raise ValueError("재원은 필수입니다.")
        if rec.get("예산목") not in BUDGET_ITEMS:
            raise ValueError(f"예산목 '{rec.get('예산목') or ''}' 은 목록에 없습니다. 가능한 값: {', '.join(BUDGET_ITEMS)}")
        if not _to_date(rec.get("원인발생일")):
            raise ValueError("원인발생일은 필수입니다.")
        if _to_num(rec.get("금액")) == 0:
            raise ValueError("금액은 0이 될 수 없습니다.")
        if kind == "req":
            if rec.get("결제수단") and rec["결제수단"] not in PAY_METHODS:
                raise ValueError("결제수단이 올바르지 않습니다.")
            rec["상태"] = rec.get("상태") or "대기"
            if rec["상태"] not in REQ_STATUS:
                raise ValueError("상태가 올바르지 않습니다.")
    elif kind == "deposit":
        if not _to_date(rec.get("일자")):
            raise ValueError("일자는 필수입니다.")
        if not str(rec.get("거래처") or "").strip():
            raise ValueError("거래처는 필수입니다.")
        if rec.get("구분") not in DEP_TYPES:
            raise ValueError("구분은 적립/사용 중 하나여야 합니다.")
        if _to_num(rec.get("금액")) <= 0:
            raise ValueError("금액은 0보다 커야 합니다.")
    elif kind == "budget":
        if not str(rec.get("재원") or "").strip():
            raise ValueError("재원은 필수입니다.")
        rnd = str(rec.get("변경회차") or "").strip()
        if not (rnd in BUDGET_ROUNDS or rnd.isdigit()):
            raise ValueError("변경회차는 '이월', '당초' 또는 숫자여야 합니다.")


def create(kind: str, rec: dict) -> dict:
    sheet, cols, head_row, key = _SHEETS[kind]
    with _write_session() as wb:
        ws = wb[sheet]
        _validate(kind, rec)
        if kind in ("exec", "req", "deposit"):
            _validate_tag(rec, wb)
        if key and kind not in ("funds", "tags"):
            _assign_number(wb, ws, cols, head_row, key, rec)
        if kind in ("funds", "tags"):
            rec[key] = str(rec[key]).strip()
            if any(_same_key(r[key], rec[key]) for r in _rows(ws, cols)):
                raise ValueError(f"이미 존재하는 {key}입니다 (대소문자·공백만 다른 값 포함).")
        if kind == "budget":
            _check_budget_round(rec, _rows(ws, cols, head_row))
        if kind == "deposit" and rec.get("구분") == "적립" and rec.pop("_record_exec", False):
            ex = {c: "" for c in EXEC_COLS}
            ex.update({"원인발생일": rec["일자"], "재원": rec.get("_재원"), "예산목": rec.get("_예산목"),
                       "세목": rec.get("_세목") or "", "거래처": rec["거래처"], "금액": rec["금액"],
                       "사용자": rec.get("사용자") or "", "태그": rec.get("_태그") or ("적립금" if any(t["태그명"] == "적립금" for t in _rows(wb[SHEET_TAG], TAG_COLS)) else ""),
                       "적요": rec.get("적요") or f"{rec['거래처']} 적립금 선결제",
                       "비고": "적립금 적립"})
            _validate("exec", ex)
            _validate_tag(ex, wb)
            ws_ex = wb[SHEET_EXEC]
            _assign_number(wb, ws_ex, EXEC_COLS, 1, "거래번호", ex)
            _write_row(ws_ex, EXEC_COLS, _next_row(ws_ex), ex)
            rec["연결거래번호"] = ex["거래번호"]
        rec = {k: v for k, v in rec.items() if not k.startswith("_")}
        r = _next_row(ws, head_row)
        _write_row(ws, cols, r, rec, head_row)
        if kind == "budget":
            _refresh_budget_summary(wb)
        _save(wb)
        rec["_row"] = r
        return rec


def update(kind: str, row: int, rec: dict, expect: dict | None = None) -> dict:
    sheet, cols, head_row, key = _SHEETS[kind]
    with _write_session() as wb:
        ws = wb[sheet]
        if row <= head_row or row > ws.max_row:
            raise NotFound("행을 찾을 수 없습니다. 목록을 새로고침하세요.")
        _validate(kind, rec)
        rec = {k: v for k, v in rec.items() if not k.startswith("_")}
        cur = _rows(ws, cols, head_row)
        existing = next((x for x in cur if x["_row"] == row), None)
        if existing is None:
            raise NotFound("행을 찾을 수 없습니다. 목록을 새로고침하세요.")
        _check_expect(kind, existing, expect)
        if kind in ("exec", "req", "deposit") and str(rec.get("태그") or "").strip() != str(existing.get("태그") or ""):
            _validate_tag(rec, wb)  # 태그를 바꿀 때만 검증 (기존 미등록 태그는 유지 가능)
        if kind == "budget":
            _check_budget_round(rec, [r for r in cur if r["_row"] != row])
        if key:
            if kind in ("funds", "tags"):
                rec[key] = str(rec[key]).strip()
                if any(_same_key(r[key], rec[key]) and r["_row"] != row for r in cur):
                    raise ValueError(f"이미 존재하는 {key}입니다 (대소문자·공백만 다른 값 포함).")
                if existing[key] != rec[key]:
                    if kind == "tags":
                        _rename_tag(wb, existing[key], rec[key])
                    elif _fund_usage(wb, existing[key]):
                        raise ValueError(f"재원코드 '{existing[key]}' 는 집행·품의·예산에서 사용 중이라 바꿀 수 없습니다.")
            else:
                rec[key] = existing[key]  # 번호는 불변
        _write_row(ws, cols, row, rec, head_row)
        if kind == "budget":
            _refresh_budget_summary(wb)
        _save(wb)
        rec["_row"] = row
        return rec


def delete(kind: str, row: int, expect: dict | None = None, cascade: bool = False):
    sheet, cols, head_row, key = _SHEETS[kind]
    with _write_session() as wb:
        ws = wb[sheet]
        if row <= head_row or row > ws.max_row:
            raise NotFound("행을 찾을 수 없습니다.")
        existing = next((x for x in _rows(ws, cols, head_row) if x["_row"] == row), None)
        if existing is None:
            raise NotFound("행을 찾을 수 없습니다. 목록을 새로고침하세요.")
        _check_expect(kind, existing, expect)
        if kind == "tags":
            n = _tag_usage(wb, existing["태그명"])
            if n:
                raise ValueError(f"'{existing['태그명']}' 태그를 쓰는 행이 {n}건 있습니다. 먼저 해당 행의 태그를 바꾸거나 태그명을 수정하세요.")
        if kind == "funds" and _fund_usage(wb, existing["재원코드"]):
            raise ValueError(f"재원코드 '{existing['재원코드']}' 는 집행·품의·예산에서 사용 중이라 삭제할 수 없습니다.")
        if kind == "req" and existing.get("상태") == "집행완료":
            raise ValueError("집행으로 전환된 품의는 삭제할 수 없습니다 (감사 추적). 상태를 '취소'로 바꾸거나 연결 집행을 먼저 정리하세요.")
        if kind == "deposit" and existing.get("연결거래번호"):
            if cascade:
                ws_ex = wb[SHEET_EXEC]
                ex = next((x for x in _rows(ws_ex, EXEC_COLS) if x["거래번호"] == existing["연결거래번호"]), None)
                if ex is not None:
                    _delete_row(ws_ex, ex["_row"])
            else:
                raise ValueError(f"연결된 집행 {existing['연결거래번호']} 이 있습니다. '연결 집행도 함께 삭제'를 선택하거나 집행을 먼저 정리하세요.")
        if kind == "exec" and existing["거래번호"] in _number_refs(wb, "거래번호"):
            raise ValueError("적립금 적립과 연결된 집행입니다. 적립금 탭에서 해당 적립 행을 먼저 처리하세요.")
        _delete_row(ws, row)
        if kind == "budget":
            _refresh_budget_summary(wb)
        _save(wb)


def req_to_exec(row: int, extra: dict, expect: dict | None = None) -> dict:
    """품의 행을 집행내역으로 복사하고 품의 상태를 '집행완료'로 변경."""
    with _write_session() as wb:
        ws_req, ws_exec = wb[SHEET_REQ], wb[SHEET_EXEC]
        req = next((x for x in _rows(ws_req, REQ_COLS) if x["_row"] == row), None)
        if req is None:
            raise NotFound("품의 행을 찾을 수 없습니다.")
        _check_expect("req", req, expect)
        if req["상태"] != "대기":
            raise ValueError(f"상태가 '{req['상태']}' 인 품의는 전환할 수 없습니다 (대기만 가능).")
        rec = {c: "" for c in EXEC_COLS}
        for c in ("원인발생일", "재원", "예산목", "세목", "세세목", "거래처", "적요", "금액", "태그"):
            rec[c] = req.get(c)
        rec["사용자"] = req.get("품의자")
        rec["비고"] = f"품의 {req['품의번호']}" + (f" / {req['비고']}" if req.get("비고") else "")
        rec.update({k: v for k, v in extra.items() if k in EXEC_COLS})
        _validate("exec", rec)
        _assign_number(wb, ws_exec, EXEC_COLS, 1, "거래번호", rec)
        r = _next_row(ws_exec)
        _write_row(ws_exec, EXEC_COLS, r, rec)
        req["상태"] = "집행완료"
        _write_row(ws_req, REQ_COLS, row, req)
        _save(wb)
        rec["_row"] = r
        return rec


def _rename_tag(wb, old: str, new: str):
    """태그명 변경 시 집행·품의·적립금의 태그 값을 함께 바꾼다."""
    for sheet in (SHEET_EXEC, SHEET_REQ, SHEET_DEP):
        ws = wb[sheet]
        heads = _headers(ws)
        if "태그" not in heads:
            continue
        ci = heads.index("태그") + 1
        for r in range(2, ws.max_row + 1):
            if ws.cell(r, ci).value == old:
                ws.cell(r, ci).value = new


def _tag_usage(wb, tag: str) -> int:
    n = 0
    for sheet, cols in ((SHEET_EXEC, EXEC_COLS), (SHEET_REQ, REQ_COLS), (SHEET_DEP, DEP_COLS)):
        for r in _rows(wb[sheet], cols):
            if tag in [t.strip() for t in str(r.get("태그") or "").split(",")]:
                n += 1
    return n


def tag_usage(tag: str) -> int:
    """태그를 쓰는 행 수 (쉼표로 묶인 옛 태그 포함)."""
    with _lock:
        return _tag_usage(_load(), tag)


def _fund_usage(wb, code: str) -> int:
    n = 0
    for sheet, cols, head in ((SHEET_EXEC, EXEC_COLS, 1), (SHEET_REQ, REQ_COLS, 1), (SHEET_BUDGET, BUDGET_COLS, BUDGET_HEAD_ROW)):
        n += sum(1 for r in _rows(wb[sheet], cols, head) if r.get("재원") == code)
    return n


def _refresh_budget_summary(wb):
    """예산변동 1~7행 요약(전체 재원 합계)을 갱신."""
    ws = wb[SHEET_BUDGET]
    rows = _rows(ws, BUDGET_COLS, BUDGET_HEAD_ROW)
    sums = {"이월금": [0] * 9, "당초액": [0] * 9, "변경액": [0] * 9}
    for r in rows:
        rnd = str(r["변경회차"])
        key = "이월금" if rnd == "이월" else "당초액" if rnd == "당초" else "변경액"
        for i, item in enumerate(BUDGET_ITEMS):
            sums[key][i] += _to_num(r.get(item))
    label_row = {"이월금": 4, "당초액": 5, "변경액": 6}
    for key, rr in label_row.items():
        for i in range(9):
            c = ws.cell(rr, 5 + i, sums[key][i] or None)
            c.number_format = "#,##0"
    for i in range(9):
        c = ws.cell(7, 5 + i, (sums["이월금"][i] + sums["당초액"][i] + sums["변경액"][i]) or None)
        c.number_format = "#,##0"
    ws.cell(1, 2, "※ 전체 재원 합계 (앱 자동 갱신)")


# ---------- 증빙 / 상태 ----------
def exec_action(row: int, action: str, expect: dict | None = None) -> dict:
    """집행 행의 단계 처리. action: claim(지급청구일=오늘) | complete(지출완료일=오늘) | fix(보완) | unfix(보완 해제)"""
    with _write_session() as wb:
        ws = wb[SHEET_EXEC]
        rec = next((x for x in _rows(ws, EXEC_COLS) if x["_row"] == row), None)
        if rec is None:
            raise NotFound("행을 찾을 수 없습니다. 목록을 새로고침하세요.")
        _check_expect("exec", rec, expect)
        today = dt.date.today().isoformat()
        if action == "claim":
            if rec.get("지출완료일"):
                raise ValueError("이미 지출완료된 건입니다. 완료를 취소한 뒤 청구일을 바꾸세요.")
            rec["지급청구일"] = today
        elif action == "uncomplete":
            rec["지출완료일"] = ""
        elif action == "complete":
            rec["지출완료일"] = today
            if not rec.get("지급청구일"):
                rec["지급청구일"] = today
        elif action == "fix":
            if not rec.get("지급청구일"):
                raise ValueError("지급청구일이 등록된 뒤에 보완을 표시할 수 있습니다.")
            rec["상태"] = "보완"
        elif action == "unfix":
            rec["상태"] = "청구"
        else:
            raise ValueError("알 수 없는 동작입니다.")
        rec["상태"] = exec_status(rec)
        _write_row(ws, EXEC_COLS, row, rec)
        _save(wb)
        return rec


def evidence_for(number: str) -> list[dict]:
    with _lock:
        return [r for r in _rows(_load()[SHEET_EVID], EVID_COLS) if r["거래번호"] == number]


def _sync_exec_evidence(wb, number: str, folder_url: str | None = None):
    """집행내역의 증빙목록(종류 요약)·증빙폴더 열을 증빙 시트 기준으로 갱신."""
    ws = wb[SHEET_EXEC]
    rec = next((x for x in _rows(ws, EXEC_COLS) if x["거래번호"] == number), None)
    if rec is None:
        return
    kinds = []
    for e in _rows(wb[SHEET_EVID], EVID_COLS):
        if e["거래번호"] == number and e["증빙종류"] and e["증빙종류"] not in kinds:
            kinds.append(e["증빙종류"])
    rec["증빙목록"] = ", ".join(kinds)
    if folder_url:
        rec["증빙폴더"] = folder_url
    _write_row(ws, EXEC_COLS, rec["_row"], rec)


def evidence_add(items: list[dict], folder_url: str | None = None) -> list[dict]:
    """증빙 시트에 여러 행 추가 후 집행내역 요약 갱신. items 는 EVID_COLS 키를 가진 dict 목록."""
    with _write_session() as wb:
        ws = wb[SHEET_EVID]
        out = []
        for it in items:
            _validate("evidence", it)
            r = _next_row(ws)
            _write_row(ws, EVID_COLS, r, it)
            it["_row"] = r
            out.append(it)
        for number in {it["거래번호"] for it in items}:
            _sync_exec_evidence(wb, number, folder_url)
        _save(wb)
        return out


def evidence_delete(row: int, expect: dict | None = None) -> dict:
    """증빙 행 삭제 후 집행내역 요약 갱신. 삭제된 행(드라이브파일ID 포함) 반환."""
    with _write_session() as wb:
        ws = wb[SHEET_EVID]
        rec = next((x for x in _rows(ws, EVID_COLS) if x["_row"] == row), None)
        if rec is None:
            raise NotFound("증빙 행을 찾을 수 없습니다.")
        _check_expect("evidence", rec, expect)
        _delete_row(ws, row)
        _sync_exec_evidence(wb, rec["거래번호"])
        _save(wb)
        return rec


def evidence_names(number: str) -> list[str]:
    """같은 건의 기존 파일명 (중복 번호 부여용)."""
    return [e["파일명"] for e in evidence_for(number)]
