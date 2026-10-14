"""xlsx 파일을 원본(source of truth)으로 사용하는 저장소 계층."""
from __future__ import annotations

import contextlib
import hashlib
import json
import uuid
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
SHEET_PEOPLE = "인원"
SHEET_SALARY = "기준급여"
SHEET_PAYEE = "지급처"
SHEET_LABOR = "인건비지급"
SHEET_LADJ = "인건비조정"
SHEET_RQ = "신청"
SHEET_ORDER = "주문"
SHEET_RATT = "신청첨부"

BUDGET_ITEMS = [
    "내부인건비(공통)", "외부인건비(공통)", "연구시설.장비비", "연구활동비",
    "연구재료비", "연구수당", "위탁연구개발비", "간접비(공통)", "발생이자",
]
PAY_METHODS = ["연구비카드", "계좌이체", "연구자선지출", "공금통장", "적립금", "기타"]
REQ_STATUS = ["대기", "집행완료", "취소"]
BUDGET_ROUNDS = ["이월", "당초"]  # 그 외에는 1,2,3... 숫자 회차

FUND_COLS = ["재원코드", "과제명", "시작일", "종료일", "비고", "인건비예산"]
# 인건비 (인건비_설계_2026-10-13.md)
PEOPLE_COLS = ["이름", "인건비구분", "입사일", "퇴사일", "이월선급", "비고"]
SALARY_COLS = ["이름", "시작월", "종료월", "월액", "비고"]
PAYEE_COLS = ["지급처코드", "지급처명", "인건비예산", "비고"]
LABOR_COLS = ["지급월", "귀속월", "이름", "지급처", "금액", "상태", "지급일", "연결거래번호", "비고"]
LADJ_COLS = ["월", "이름", "금액", "사유"]
LABOR_KINDS = ["내부", "외부"]
LABOR_STATUS = ["예정", "확정"]
LABOR_ITEM = {"내부": "내부인건비(공통)", "외부": "외부인건비(공통)"}
MONTH_COLS = {"지급월", "귀속월", "시작월", "종료월", "월"}
EXEC_COLS = ["거래번호", "관리번호", "원인발생일", "지급청구일", "지출완료일", "결의일", "재원", "예산목", "세목", "결제수단",
             "세세목", "거래처", "적요", "금액", "사용자", "태그", "비고", "상태", "증빙폴더", "증빙목록"]
EXEC_STATUS = ["발생", "청구", "보완", "완료", "결의"]  # 날짜에서 계산, '보완'만 수동. 순서: 발생→요구→(보완)→완료→결의 (2026-10-14)
LINKED_LOCKED = ["재원", "예산목", "금액", "거래처", "원인발생일"]  # 인건비·적립 연결 집행에서 잠그는 열
REQ_COLS = ["품의번호", "원인발생일", "지출예정일", "재원", "예산목", "세목", "세세목", "거래처",
            "결제수단", "적요", "금액", "태그", "품의자", "비고", "상태"]
DEP_COLS = ["일자", "거래처", "구분", "금액", "적요", "사용자", "증빙번호", "연결거래번호", "비고", "태그"]
TAG_COLS = ["태그명", "분류", "설명"]
EVID_COLS = ["거래번호", "증빙종류", "파일명", "원본파일명", "드라이브파일ID", "크기", "업로드일", "비고"]
DEP_TYPES = ["적립", "사용"]
# 신청 (신청_설계_2026-10-14.md)
REQUEST_COLS = ["신청번호", "구분", "상태", "신청인", "신청일", "관련과제", "품목", "규격", "단가", "수량", "금액", "사유",
                "희망일", "온라인코드", "상품코드", "상품링크", "결재인", "결재일", "반려사유", "주문번호", "연결품의번호",
                "첨부폴더", "첨부목록", "상세", "비고"]
ORDER_COLS = ["주문번호", "주문일", "배송일", "거래처", "주문금액", "결제금액", "적립금사용", "신청번호목록", "비고"]
RATT_COLS = ["신청번호", "파일명", "원본파일명", "드라이브파일ID", "크기", "업로드일", "비고"]
REQUEST_TYPES = ["장비", "소모품", "학회", "기타"]
REQUEST_STATUS = ["신청", "승인", "반려", "품의전환", "완료"]
REQUEST_LOCKED = ("품의전환", "완료")  # 비고만 수정 가능
# 신청 행에서 화면 수정으로 바꿀 수 없는 열 (동작·주문·첨부로만 바뀜)
REQUEST_SYSTEM = ["신청번호", "상태", "결재인", "결재일", "반려사유", "주문번호", "연결품의번호", "첨부폴더", "첨부목록"]
ORDER_VENDOR = "알파몰"
ORDER_PREFIX = "알파"
BUDGET_HEAD_ROW = 8
BUDGET_COLS = ["재원", "변경회차", "신청일자", "변경사유"] + BUDGET_ITEMS  # A~D + E~M

DATE_COLS = {"원인발생일", "지급청구일", "결의일", "지출완료일", "시작일", "종료일", "신청일자", "지출예정일", "일자", "입사일", "퇴사일", "지급일",
             "신청일", "희망일", "결재일", "주문일", "배송일", "업로드일"}
NUM_COLS = {"금액", "인건비예산", "월액", "이월선급", "단가", "수량", "주문금액", "결제금액", "크기"} | set(BUDGET_ITEMS)
# 행 식별(동시 수정·행 밀림 감지)에 쓰는 열: 키가 없는 시트는 내용 조합
IDENT_COLS = {
    "funds": ["재원코드"], "exec": ["거래번호"], "req": ["품의번호"], "tags": ["태그명"],
    "budget": ["재원", "변경회차", "신청일자"], "deposit": ["일자", "거래처", "구분", "금액"],
    "evidence": ["거래번호", "파일명"],
    "people": ["이름"], "salary": ["이름", "시작월"], "payee": ["지급처코드"],
    "labor": ["지급월", "귀속월", "이름", "지급처"], "ladj": ["월", "이름", "금액"],
    "request": ["신청번호"], "order": ["주문번호"], "ratt": ["신청번호", "파일명"],
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


_YM = re.compile(r"^\d{4}-\d{2}$")


def _to_month(v: Any) -> str | None:
    """셀/입력값 -> 'YYYY-MM'. 날짜·일련번호면 그 달, 해석 불가하면 원문."""
    if v is None or v == "":
        return None
    if isinstance(v, (dt.datetime, dt.date, int, float)) and not isinstance(v, bool):
        d = _to_date(v)
        return d[:7] if d and _ISO.match(d) else str(v)
    s = str(v).strip()
    m = re.match(r"^(\d{4})[-./](\d{1,2})(?:[-./]\d{1,2})?$", s)
    if m:
        return f"{m[1]}-{int(m[2]):02d}"
    return s or None


def _valid_month(v: Any) -> bool:
    m = _to_month(v)
    return m is None or (bool(_YM.match(m)) and 1 <= int(m[5:]) <= 12)


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
    if col in MONTH_COLS:
        return _to_month(v)
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
    if col in MONTH_COLS:
        return _to_month(v) or ""
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

    for name, cols, widths in ((SHEET_PEOPLE, PEOPLE_COLS, (14, 10, 12, 12, 14, 30)),
                               (SHEET_SALARY, SALARY_COLS, (14, 10, 10, 14, 30)),
                               (SHEET_PAYEE, PAYEE_COLS, (14, 30, 16, 30)),
                               (SHEET_LABOR, LABOR_COLS, (10, 10, 14, 16, 14, 8, 12, 18, 30)),
                               (SHEET_LADJ, LADJ_COLS, (10, 14, 14, 30)),
                               (SHEET_RQ, REQUEST_COLS, (14, 8, 10, 10, 12, 16, 30, 20, 12, 8, 14, 30,
                                                         12, 14, 14, 30, 10, 12, 24, 18, 18, 30, 30, 20, 24)),
                               (SHEET_ORDER, ORDER_COLS, (18, 12, 12, 14, 14, 14, 10, 40, 24)),
                               (SHEET_RATT, RATT_COLS, (14, 44, 30, 36, 10, 12, 20))):
        if name not in wb.sheetnames:
            ws = wb.create_sheet(name)
            for i, c in enumerate(cols, 1):
                cell = ws.cell(1, i, c)
                cell.font, cell.fill = head_font, head_fill
                ws.column_dimensions[get_column_letter(i)].width = widths[i - 1]
            ws.freeze_panes = "A2"
            changed = True

    for sheet, col_name, width in ((SHEET_REQ, "상태", 10), (SHEET_DEP, "태그", 14), (SHEET_FUND, "인건비예산", 16),
                                   (SHEET_EXEC, "상태", 8), (SHEET_EXEC, "증빙폴더", 30), (SHEET_EXEC, "증빙목록", 30),
                                   (SHEET_EXEC, "결의일", 12), (SHEET_EXEC, "결제수단", 12)):
        ws = wb[sheet]
        heads = _headers(ws)
        if col_name not in heads:
            col = len(heads) + 1  # 후행 빈 헤더만 제거된 길이 → 중간 빈 헤더가 있어도 덮어쓰지 않음
            cell = ws.cell(1, col, col_name)
            cell.font = head_font
            ws.column_dimensions[get_column_letter(col)].width = width
            changed = True

    for name, cols in ((SHEET_RQ, REQUEST_COLS), (SHEET_ORDER, ORDER_COLS), (SHEET_RATT, RATT_COLS)):
        ws = wb[name]  # 신청 계열 시트: 나중에 추가된 열 보정
        heads = _headers(ws)
        for c in cols:
            if c not in heads:
                heads.append(c)
                ws.cell(1, len(heads), c).font = head_font
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
    return dst


def _file_hash() -> str:
    return hashlib.sha256(XLSX_PATH.read_bytes()).hexdigest()


# 직전 쓰기 기록: 되돌리기는 "그 이후 아무도 장부를 바꾸지 않았을 때"만 허용 (해시 비교)
LAST_WRITE: dict | None = None


def last_write_id() -> str | None:
    return LAST_WRITE.get("id") if LAST_WRITE else None


def undo_last(write_id: str | None = None) -> dict:
    """직전 저장 직전의 백업으로 장부를 되돌린다. 이후 다른 변경(다른 창·MCP·엑셀)이 있으면 거부.
    write_id 가 오면 그 쓰기가 아직 '직전 쓰기'일 때만 되돌린다 (오래된 토스트가 다른 변경을 되돌리지 않도록)."""
    global LAST_WRITE
    with _lock, _file_lock():
        if not LAST_WRITE or not Path(LAST_WRITE["backup"]).exists():
            raise ValueError("되돌릴 직전 변경이 없습니다.")
        if write_id and write_id != LAST_WRITE.get("id"):
            raise ValueError("그 뒤에 다른 변경이 있어 이 변경은 되돌릴 수 없습니다. 필요하면 app/backup 의 백업 파일로 복원하세요.")
        if _file_hash() != LAST_WRITE["after"]:
            raise ValueError("그 뒤에 장부가 다시 바뀌어 되돌릴 수 없습니다. 목록을 새로고침하세요.")
        _check_writable()
        tmp = XLSX_PATH.with_suffix(".tmp.xlsx")
        shutil.copy2(LAST_WRITE["backup"], tmp)
        os.replace(tmp, XLSX_PATH)
        info = {"undone": LAST_WRITE.get("label", "")}
        LAST_WRITE = None
        return info


def _check_writable():
    """엑셀 등 다른 프로그램이 파일을 점유 중인지 실제 쓰기 열기로 확인."""
    try:
        with open(XLSX_PATH, "r+b"):
            pass
    except PermissionError as e:
        hint = " (엑셀에서 열려 있음)" if XLSX_PATH.with_name("~$" + XLSX_PATH.name).exists() else ""
        raise LedgerLocked(f"장부 파일이 다른 프로그램에서 열려 있어 저장할 수 없습니다{hint}. 닫은 뒤 다시 시도하세요.") from e


def _save(wb):
    global LAST_WRITE
    _check_writable()
    backup = _backup()
    tmp = XLSX_PATH.with_suffix(".tmp.xlsx")
    try:
        wb.save(tmp)
        os.replace(tmp, XLSX_PATH)
        LAST_WRITE = {"backup": str(backup), "after": _file_hash(), "at": dt.datetime.now().isoformat(timespec="seconds"), "id": uuid.uuid4().hex[:12]}
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
            "people": _rows(wb[SHEET_PEOPLE], PEOPLE_COLS, 1, formulas),
            "salary": _rows(wb[SHEET_SALARY], SALARY_COLS, 1, formulas),
            "payee": _rows(wb[SHEET_PAYEE], PAYEE_COLS, 1, formulas),
            "labor": _rows(wb[SHEET_LABOR], LABOR_COLS, 1, formulas),
            "ladj": _rows(wb[SHEET_LADJ], LADJ_COLS, 1, formulas),
            "request": _rows(wb[SHEET_RQ], REQUEST_COLS, 1, formulas),
            "order": _rows(wb[SHEET_ORDER], ORDER_COLS, 1, formulas),
            "ratt": _rows(wb[SHEET_RATT], RATT_COLS, 1, formulas),
        }
        req_state = {r["품의번호"]: r["상태"] for r in data["req"] if r.get("품의번호")}
        for r in data["request"]:  # 연결 품의가 집행완료면 '완료' (읽을 때 계산)
            r["상태"] = request_status(r, req_state)
        for r in data["funds"]:  # 인건비예산: 빈 칸은 None (예산목 합계 사용), 숫자는 직접 입력
            r["인건비예산"] = None if r.get("인건비예산") in (None, "", 0) and not _has_value(wb[SHEET_FUND], r["_row"], "인건비예산") else r["인건비예산"]
        for r in data["payee"]:
            r["인건비예산"] = None if not _has_value(wb[SHEET_PAYEE], r["_row"], "인건비예산") else r["인건비예산"]
        for r in data["exec"]:  # 상태는 날짜에서 계산 (시트 값은 '보완' 표시용)
            r["상태"] = exec_status(r)
        data["meta"] = {
            "labor_kinds": LABOR_KINDS,
            "labor_status": LABOR_STATUS,
            "dep_types": DEP_TYPES,
            "budget_items": BUDGET_ITEMS,
            "pay_methods": PAY_METHODS,
            "req_status": REQ_STATUS,
            "request_types": REQUEST_TYPES,
            "request_status": REQUEST_STATUS,
            "file": str(XLSX_PATH),
            "mtime": dt.datetime.fromtimestamp(XLSX_PATH.stat().st_mtime).isoformat(timespec="seconds"),
            "locked": XLSX_PATH.with_name("~$" + XLSX_PATH.name).exists(),
            # 수식 셀은 값으로 읽을 수 없어 0/문자열로 취급됨 → 화면에 경고
            "formula_cells": formulas[:20],
            "formula_count": len(formulas),
        }
        return data


def _has_value(ws, row: int, col: str) -> bool:
    heads = _headers(ws)
    return col in heads and ws.cell(row, heads.index(col) + 1).value not in (None, "")


_SHEETS = {
    "people": (SHEET_PEOPLE, PEOPLE_COLS, 1, "이름"),
    "salary": (SHEET_SALARY, SALARY_COLS, 1, None),
    "payee": (SHEET_PAYEE, PAYEE_COLS, 1, "지급처코드"),
    "labor": (SHEET_LABOR, LABOR_COLS, 1, None),
    "ladj": (SHEET_LADJ, LADJ_COLS, 1, None),
    "funds": (SHEET_FUND, FUND_COLS, 1, "재원코드"),
    "exec": (SHEET_EXEC, EXEC_COLS, 1, "거래번호"),
    "req": (SHEET_REQ, REQ_COLS, 1, "품의번호"),
    "budget": (SHEET_BUDGET, BUDGET_COLS, BUDGET_HEAD_ROW, None),
    "deposit": (SHEET_DEP, DEP_COLS, 1, None),
    "tags": (SHEET_TAG, TAG_COLS, 1, "태그명"),
    "evidence": (SHEET_EVID, EVID_COLS, 1, None),
    "request": (SHEET_RQ, REQUEST_COLS, 1, "신청번호"),
    "order": (SHEET_ORDER, ORDER_COLS, 1, "주문번호"),
    "ratt": (SHEET_RATT, RATT_COLS, 1, None),
}


def request_status(rec: dict, req_state: dict) -> str:
    """신청 상태: 연결 품의가 집행완료면 '완료', 그 외에는 시트 값 (빈 값은 '신청')."""
    no = str(rec.get("연결품의번호") or "").strip()
    if no and req_state.get(no) == "집행완료":
        return "완료"
    return str(rec.get("상태") or "") or "신청"


def _req_state(wb) -> dict:
    return {r["품의번호"]: r["상태"] for r in _rows(wb[SHEET_REQ], REQ_COLS) if r.get("품의번호")}


def exec_status(rec: dict) -> str:
    """발생(청구일 없음) → 청구(지급청구일) → 보완(수동) → 완료(지출완료일) → 결의(결의일). 날짜가 우선."""
    if rec.get("결의일"):
        return "결의"
    if rec.get("지출완료일"):
        return "완료"
    if rec.get("지급청구일"):
        return "보완" if str(rec.get("상태") or "") == "보완" else "청구"
    return "발생"


def _ident(kind: str, rec: dict) -> dict:
    return {c: _cell_out(c, rec.get(c)) for c in IDENT_COLS[kind]}


def _norm_cmp(c: str, v) -> str:
    v = _cell_out(c, v)
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return "" if v is None else str(v)


def _check_expect(kind: str, existing: dict, expect: dict | None):
    """클라이언트가 보던 행과 실제 행이 같은지 확인 (다른 창/MCP 에서 행이 밀리거나 내용이 바뀐 경우 감지).
    expect 에 _snapshot(행 전체)이 있으면 모든 열을 비교해 '덮어쓰기'를 막는다."""
    if not expect:
        return
    for c in IDENT_COLS[kind]:
        if c in expect and _cell_out(c, expect[c]) != existing.get(c):
            raise NotFound("다른 곳에서 장부가 바뀌어 행이 일치하지 않습니다. 새로고침 후 다시 시도하세요.")
    snap = expect.get("_snapshot")
    if isinstance(snap, dict):
        cols = _SHEETS[kind][1]
        changed = [c for c in cols if c in snap and c != "상태" and _norm_cmp(c, snap[c]) != _norm_cmp(c, existing.get(c))]
        if changed:
            raise NotFound(f"다른 곳에서 이 행의 {', '.join(changed[:3])} 이(가) 먼저 바뀌었습니다. 새로고침한 뒤 다시 수정하세요.")


def _labor_refs(wb) -> set[str]:
    return {str(r.get("연결거래번호")) for r in _rows(wb[SHEET_LABOR], LABOR_COLS) if r.get("연결거래번호")}


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
        for r in _rows(wb[SHEET_RQ], REQUEST_COLS):
            if r.get("연결품의번호"):
                refs.add(str(r["연결품의번호"]))
    elif key == "신청번호":
        for r in _rows(wb[SHEET_RATT], RATT_COLS):
            refs.add(str(r.get("신청번호") or ""))
        for r in _rows(wb[SHEET_ORDER], ORDER_COLS):
            refs.update(re.findall(r"R-\d{4}-\d+", str(r.get("신청번호목록") or "")))
        for sheet, cols in ((SHEET_REQ, REQ_COLS), (SHEET_EXEC, EXEC_COLS)):
            for r in _rows(wb[sheet], cols):
                refs.update(re.findall(r"R-\d{4}-\d+", str(r.get("비고") or "")))
    elif key == "주문번호":
        for r in _rows(wb[SHEET_RQ], REQUEST_COLS):
            refs.add(str(r.get("주문번호") or ""))
        for r in _rows(wb[SHEET_DEP], DEP_COLS):
            refs.add(str(r.get("증빙번호") or ""))
    return refs


def _assign_request_number(wb, ws, rec):
    """R-YYYY-NNN (신청일 연도, 연도별 일련번호, 참조된 번호는 재사용하지 않음)."""
    d = _to_date(rec.get("신청일")) or dt.date.today().isoformat()
    year = d[:4]
    mx = 0
    seen = [str(r.get("신청번호") or "") for r in _rows(ws, REQUEST_COLS)] + list(_number_refs(wb, "신청번호"))
    for v in seen:
        m = re.match(r"^R-(\d{4})-(\d+)$", v)
        if m and m[1] == year:
            mx = max(mx, int(m[2]))
    rec["신청번호"] = f"R-{year}-{mx + 1:03d}"


def _assign_order_number(wb, ws, rec):
    """알파-YYYYMMDD-NN (주문일별 일련번호)."""
    d = _to_date(rec.get("주문일")) or dt.date.today().isoformat()
    prefix = f"{ORDER_PREFIX}-{d.replace('-', '')}-"
    mx = 0
    seen = [str(r.get("주문번호") or "") for r in _rows(ws, ORDER_COLS)] + list(_number_refs(wb, "주문번호"))
    for v in seen:
        if v.startswith(prefix) and v[len(prefix):].isdigit():
            mx = max(mx, int(v[len(prefix):]))
    rec["주문번호"] = f"{prefix}{mx + 1:02d}"


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


def _validate_months(rec: dict, cols):
    for c in cols:
        if c in MONTH_COLS and rec.get(c) not in (None, "") and not _valid_month(rec[c]):
            raise ValueError(f"{c} 형식이 올바르지 않습니다 (YYYY-MM): {rec[c]}")
        if c in MONTH_COLS and rec.get(c) not in (None, ""):
            rec[c] = _to_month(rec[c])


def _validate(kind: str, rec: dict):
    cols = _SHEETS[kind][1]
    _validate_dates(rec, cols)
    _validate_months(rec, cols)
    if kind == "evidence":
        if not str(rec.get("거래번호") or "").strip() or not str(rec.get("파일명") or "").strip():
            raise ValueError("거래번호와 파일명은 필수입니다.")
        return
    if kind == "ratt":
        if not str(rec.get("신청번호") or "").strip() or not str(rec.get("파일명") or "").strip():
            raise ValueError("신청번호와 파일명은 필수입니다.")
        return
    if kind == "request":
        _validate_request(rec)
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
        if rec.get("결제수단") and rec["결제수단"] not in PAY_METHODS:
            raise ValueError("결제수단이 올바르지 않습니다.")
        if kind == "req":
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
    elif kind == "people":
        if not str(rec.get("이름") or "").strip():
            raise ValueError("이름은 필수입니다.")
        rec["인건비구분"] = rec.get("인건비구분") or "내부"
        if rec["인건비구분"] not in LABOR_KINDS:
            raise ValueError("인건비구분은 내부/외부 중 하나여야 합니다.")
        if rec.get("입사일") and rec.get("퇴사일") and _to_date(rec["퇴사일"]) < _to_date(rec["입사일"]):
            raise ValueError("퇴사일은 입사일 이후여야 합니다.")
    elif kind == "salary":
        if not str(rec.get("이름") or "").strip():
            raise ValueError("이름은 필수입니다.")
        if not rec.get("시작월") or not rec.get("종료월"):
            raise ValueError("시작월과 종료월은 필수입니다.")
        if rec["시작월"] > rec["종료월"]:
            raise ValueError("종료월은 시작월 이후여야 합니다.")
        if _to_num(rec.get("월액")) < 0:
            raise ValueError("월액은 0 이상이어야 합니다.")
    elif kind == "payee":
        code = str(rec.get("지급처코드") or "").strip()
        if not code:
            raise ValueError("지급처코드는 필수입니다.")
        if "-" in code:
            raise ValueError("지급처코드에는 '-'를 사용할 수 없습니다 (번호 체계와 충돌).")
    elif kind == "labor":
        if not rec.get("지급월"):
            raise ValueError("지급월은 필수입니다.")
        rec["귀속월"] = rec.get("귀속월") or rec["지급월"]
        if not str(rec.get("이름") or "").strip():
            raise ValueError("이름은 필수입니다.")
        if not str(rec.get("지급처") or "").strip():
            raise ValueError("지급처는 필수입니다.")
        if _to_num(rec.get("금액")) <= 0:
            raise ValueError("금액은 0보다 커야 합니다.")
        rec["상태"] = rec.get("상태") or "예정"
        if rec["상태"] not in LABOR_STATUS:
            raise ValueError("상태는 예정/확정 중 하나여야 합니다.")
    elif kind == "ladj":
        if not rec.get("월"):
            raise ValueError("월은 필수입니다.")
        if not str(rec.get("이름") or "").strip():
            raise ValueError("이름은 필수입니다.")
        if _to_num(rec.get("금액")) == 0:
            raise ValueError("금액은 0이 될 수 없습니다 (+ 선급, − 미지급).")


def _validate_request(rec: dict):
    """신청 행 검증·기본값: 구분·상태 목록, 신청인·품목 필수, 신청일=오늘, 수량=1, 금액=단가×수량(비어 있을 때), 상세 JSON."""
    for c in REQUEST_COLS:
        if c in NUM_COLS and rec.get(c) not in (None, ""):
            _to_num(rec[c], strict=True)
    rec["구분"] = str(rec.get("구분") or "").strip()
    if rec["구분"] not in REQUEST_TYPES:
        raise ValueError(f"구분 '{rec['구분']}' 은 목록에 없습니다. 가능한 값: {', '.join(REQUEST_TYPES)}")
    rec["상태"] = str(rec.get("상태") or "").strip() or "신청"
    if rec["상태"] not in REQUEST_STATUS:
        raise ValueError(f"상태 '{rec['상태']}' 이(가) 올바르지 않습니다. 가능한 값: {', '.join(REQUEST_STATUS)}")
    for c in ("신청인", "품목"):
        rec[c] = str(rec.get(c) or "").strip()
        if not rec[c]:
            raise ValueError(f"{c}은(는) 필수입니다.")
    if not _to_date(rec.get("신청일")):
        rec["신청일"] = dt.date.today().isoformat()
    if rec.get("수량") in (None, ""):
        rec["수량"] = 1
    if _to_num(rec["수량"]) <= 0:
        raise ValueError("수량은 0보다 커야 합니다.")
    if _to_num(rec.get("단가")) < 0 or _to_num(rec.get("금액")) < 0:
        raise ValueError("단가·금액은 0 이상이어야 합니다.")
    if rec.get("금액") in (None, "") and rec.get("단가") not in (None, ""):
        rec["금액"] = _to_num(rec["단가"]) * _to_num(rec["수량"])
    d = rec.get("상세")
    if isinstance(d, (dict, list)):
        rec["상세"] = json.dumps(d, ensure_ascii=False)
    elif d not in (None, "") and str(d).strip():
        try:
            json.loads(str(d))
        except ValueError:
            raise ValueError("상세(JSON) 형식이 올바르지 않습니다.") from None
    if len(str(rec.get("상세") or "")) > 32000:
        raise ValueError("상세(JSON)가 너무 깁니다 (엑셀 셀 한도 32,000자).")


def _person(wb, name: str) -> dict:
    p = next((x for x in _rows(wb[SHEET_PEOPLE], PEOPLE_COLS) if _same_key(x["이름"], name)), None)
    if p is None:
        raise ValueError(f"'{name}' 은 인원 목록에 없습니다. 인원 탭에서 먼저 등록하세요.")
    return p


def _check_person_period(p: dict, month: str, label: str):
    if p.get("입사일") and month < p["입사일"][:7]:
        raise ValueError(f"{p['이름']}: {label} {month} 은 입사월({p['입사일'][:7]}) 이전입니다.")
    if p.get("퇴사일") and month > p["퇴사일"][:7]:
        raise ValueError(f"{p['이름']}: {label} {month} 은 퇴사월({p['퇴사일'][:7]}) 이후입니다.")


def _payee_exists(wb, code: str) -> bool:
    return any(_same_key(f["재원코드"], code) for f in _rows(wb[SHEET_FUND], FUND_COLS)) or \
        any(_same_key(p["지급처코드"], code) for p in _rows(wb[SHEET_PAYEE], PAYEE_COLS))


def _validate_labor_refs(wb, rec: dict, others: list[dict]):
    """인원·지급처 존재, 재직 기간, 같은 지급월·귀속월·이름·지급처 중복."""
    p = _person(wb, rec["이름"])
    rec["이름"] = p["이름"]
    _check_person_period(p, rec["귀속월"], "귀속월")
    if not _payee_exists(wb, rec["지급처"]):
        raise ValueError(f"지급처 '{rec['지급처']}' 는 재원·지급처 목록에 없습니다.")
    for o in others:
        if all(str(o.get(c) or "") == str(rec.get(c) or "") for c in ("지급월", "귀속월", "이름", "지급처")):
            raise ValueError(f"{rec['지급월']} {rec['이름']} · {rec['지급처']} 지급 건이 이미 있습니다 ({o['상태']} {int(o['금액'] or 0):,}원). 원장에서 금액을 수정하세요.")


def _validate_salary_refs(wb, rec: dict, others: list[dict]):
    p = _person(wb, rec["이름"])
    rec["이름"] = p["이름"]
    for o in others:
        if _same_key(o["이름"], rec["이름"]) and o["시작월"] <= rec["종료월"] and o["종료월"] >= rec["시작월"]:
            raise ValueError(f"{rec['이름']} 기준급여 적용 기간이 {o['시작월']}~{o['종료월']} 구간과 겹칩니다.")


def create(kind: str, rec: dict) -> dict:
    sheet, cols, head_row, key = _SHEETS[kind]
    if kind == "order":
        raise ValueError("주문은 신청 화면의 '주문 생성'으로 만드세요.")
    if kind == "ratt":
        raise ValueError("신청 첨부는 파일 업로드로 추가하세요.")
    if kind == "request":  # 새 신청은 항상 '신청' 상태로 시작 (결재·주문·연결·첨부는 동작으로만 기록)
        rec = dict(rec)
        for c in REQUEST_SYSTEM:
            rec[c] = ""
        rec["상태"] = "신청"
    with _write_session() as wb:
        ws = wb[sheet]
        _validate(kind, rec)
        if kind in ("exec", "req", "deposit"):
            _validate_tag(rec, wb)
        if kind == "labor":
            if rec["상태"] == "확정":
                raise ValueError("새 지급 건은 '예정'으로 추가한 뒤 원장에서 확정하세요.")
            _validate_labor_refs(wb, rec, _rows(ws, cols))
        if kind == "salary":
            _validate_salary_refs(wb, rec, _rows(ws, cols))
        if kind == "ladj":
            rec["이름"] = _person(wb, rec["이름"])["이름"]
        if kind == "payee":
            rec[key] = str(rec[key]).strip()
            if any(_same_key(f["재원코드"], rec[key]) for f in _rows(wb[SHEET_FUND], FUND_COLS)):
                raise ValueError("재원코드와 같은 지급처코드는 쓸 수 없습니다 (재원은 그대로 지급처로 사용 가능).")
        if kind == "request":
            _assign_request_number(wb, ws, rec)
        elif key and kind not in ("funds", "tags", "people", "payee"):
            _assign_number(wb, ws, cols, head_row, key, rec)
        if kind in ("funds", "tags", "people", "payee"):
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
        if kind == "request":
            _prepare_request_update(wb, existing, rec)
        if kind in ("order", "ratt"):
            # 주문·첨부 행은 비고(주문은 배송일도)만 화면에서 수정
            free = ("비고", "배송일") if kind == "order" else ("비고",)
            for c in cols:
                if c in rec and c not in free and _norm_cmp(c, rec[c]) != _norm_cmp(c, existing.get(c)):
                    raise ValueError(f"{'주문' if kind == 'order' else '첨부'} 행의 {c}은(는) 여기서 바꿀 수 없습니다. "
                                     + ("주문을 취소한 뒤 다시 만드세요." if kind == "order" else "파일을 지우고 다시 올리세요."))
            rec = {**existing, **{c: rec[c] for c in free if c in rec}}
            rec.pop("_row", None)
        if kind == "exec" and (existing["거래번호"] in _labor_refs(wb) or existing["거래번호"] in _number_refs(wb, "거래번호")):
            # 인건비 확정·적립 기록으로 생긴 행: 원본과 어긋나지 않도록 핵심 열은 잠금 (부가 정보만 수정 가능)
            for c in LINKED_LOCKED:
                if _cell_out(c, rec.get(c)) != existing.get(c):
                    raise ValueError(f"인건비·적립금과 연결된 집행이라 {c}은(는) 여기서 바꿀 수 없습니다. 원본 화면(인건비 원장 확정 취소 / 적립금)에서 처리하세요.")
        if kind in ("exec", "req", "deposit") and str(rec.get("태그") or "").strip() != str(existing.get("태그") or ""):
            _validate_tag(rec, wb)  # 태그를 바꿀 때만 검증 (기존 미등록 태그는 유지 가능)
        if kind == "budget":
            _check_budget_round(rec, [r for r in cur if r["_row"] != row])
        if kind == "labor":
            if existing["상태"] == "확정":
                raise ValueError("확정된 지급 건은 수정할 수 없습니다. 먼저 '확정 취소'를 하세요.")
            rec["상태"] = "예정"; rec["지급일"] = None; rec["연결거래번호"] = None
            _validate_labor_refs(wb, rec, [r for r in cur if r["_row"] != row])
        if kind == "salary":
            _validate_salary_refs(wb, rec, [r for r in cur if r["_row"] != row])
        if kind == "ladj":
            rec["이름"] = _person(wb, rec["이름"])["이름"]
        if kind == "people" and existing["이름"] != str(rec["이름"]).strip() and _person_usage(wb, existing["이름"]):
            raise ValueError(f"'{existing['이름']}' 은 지급·기준급여·조정 내역에서 사용 중이라 이름을 바꿀 수 없습니다.")
        if kind == "payee" and existing[key] != str(rec[key]).strip() and _payee_usage(wb, existing[key]):
            raise ValueError(f"지급처코드 '{existing[key]}' 는 지급 내역에서 사용 중이라 바꿀 수 없습니다.")
        if key:
            if kind in ("funds", "tags", "people", "payee"):
                rec[key] = str(rec[key]).strip()
                if any(_same_key(r[key], rec[key]) and r["_row"] != row for r in cur):
                    raise ValueError(f"이미 존재하는 {key}입니다 (대소문자·공백만 다른 값 포함).")
                if existing[key] != rec[key]:
                    if kind == "tags":
                        _rename_tag(wb, existing[key], rec[key])
                    elif kind == "funds" and _fund_usage(wb, existing[key]):
                        raise ValueError(f"재원코드 '{existing[key]}' 는 집행·품의·예산에서 사용 중이라 바꿀 수 없습니다.")
            else:
                rec[key] = existing[key]  # 번호는 불변
        _write_row(ws, cols, row, rec, head_row)
        if kind == "budget":
            _refresh_budget_summary(wb)
        _save(wb)
        rec["_row"] = row
        return rec


def _prepare_request_update(wb, existing: dict, rec: dict):
    """신청 수정: 시스템 열은 기존 값 유지, 품의전환·완료는 비고만, 주문에 묶이면 금액 관련 열 잠금, 단가·수량이 바뀌면 금액 재계산."""
    status = request_status(existing, _req_state(wb))
    if status in REQUEST_LOCKED:
        for c in REQUEST_COLS:
            if c in rec and c != "비고" and c not in REQUEST_SYSTEM and _norm_cmp(c, rec[c]) != _norm_cmp(c, existing.get(c)):
                raise ValueError(f"'{status}' 상태의 신청은 비고만 수정할 수 있습니다 ({c} 변경 불가).")
    if existing.get("주문번호"):
        for c in ("구분", "단가", "수량", "금액"):
            if c in rec and _norm_cmp(c, rec[c]) != _norm_cmp(c, existing.get(c)):
                raise ValueError(f"주문 {existing['주문번호']} 에 묶인 신청이라 {c}을(를) 바꿀 수 없습니다. 주문을 먼저 취소하세요.")
    for c in REQUEST_SYSTEM:
        rec[c] = existing.get(c)
    if rec["구분"] != "학회" and rec.get("단가") not in (None, "") and _norm_cmp("금액", rec.get("금액")) == _norm_cmp("금액", existing.get("금액")) \
            and (_norm_cmp("단가", rec.get("단가")) != _norm_cmp("단가", existing.get("단가")) or _norm_cmp("수량", rec.get("수량")) != _norm_cmp("수량", existing.get("수량"))):
        rec["금액"] = _to_num(rec["단가"]) * _to_num(rec["수량"])


def delete(kind: str, row: int, expect: dict | None = None, cascade: bool = False) -> dict:
    """행 삭제. 반환: {"trash": [드라이브파일ID...]} (신청을 첨부와 함께 지운 경우 휴지통으로 보낼 파일)."""
    sheet, cols, head_row, key = _SHEETS[kind]
    out = {"trash": []}
    if kind == "order":
        raise ValueError("주문은 삭제 대신 '주문 취소'를 사용하세요 (연결 신청·적립금 사용 기록을 함께 정리).")
    if kind == "ratt":
        raise ValueError("신청 첨부는 첨부 목록에서 삭제하세요.")
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
        if kind == "exec" and existing["거래번호"] in _labor_refs(wb):
            raise ValueError("인건비 지급 확정으로 생긴 집행입니다. 인건비 원장에서 '확정 취소' 또는 삭제로 처리하세요.")
        if kind == "people" and _person_usage(wb, existing["이름"]):
            raise ValueError(f"'{existing['이름']}' 은 지급·기준급여·조정 내역에서 사용 중이라 삭제할 수 없습니다.")
        if kind == "payee" and _payee_usage(wb, existing["지급처코드"]):
            raise ValueError(f"지급처코드 '{existing['지급처코드']}' 는 지급 내역에서 사용 중이라 삭제할 수 없습니다.")
        if kind == "funds" and _payee_usage(wb, existing["재원코드"]):
            raise ValueError(f"재원코드 '{existing['재원코드']}' 는 인건비 지급 내역에서 사용 중이라 삭제할 수 없습니다.")
        if kind == "labor" and existing.get("연결거래번호"):
            _remove_labor_exec(wb, existing["연결거래번호"])
        if kind == "request":
            status = request_status(existing, _req_state(wb))
            if status in REQUEST_LOCKED:
                raise ValueError(f"'{status}' 상태의 신청은 삭제할 수 없습니다. 연결 품의 {existing.get('연결품의번호') or ''} 를 먼저 정리하세요.")
            if existing.get("주문번호"):
                raise ValueError(f"주문 {existing['주문번호']} 에 묶인 신청입니다. 주문을 먼저 취소하세요.")
            ws_at = wb[SHEET_RATT]
            atts = [a for a in _rows(ws_at, RATT_COLS) if a["신청번호"] == existing["신청번호"]]
            if atts and not cascade:
                raise ValueError(f"첨부 {len(atts)}건이 있습니다. '첨부도 함께 삭제'를 선택하거나 첨부를 먼저 지우세요.")
            for a in sorted(atts, key=lambda a: -a["_row"]):
                _delete_row(ws_at, a["_row"])
                if a.get("드라이브파일ID"):
                    out["trash"].append(a["드라이브파일ID"])
        if kind == "req" and existing.get("품의번호"):
            # 신청에서 전환된 품의를 지우면 신청은 '승인'으로 되돌림 (다시 전환 가능)
            ws_rq = wb[SHEET_RQ]
            for q in _rows(ws_rq, REQUEST_COLS):
                if q.get("연결품의번호") == existing["품의번호"]:
                    q.update({"상태": "승인", "연결품의번호": ""})
                    _write_row(ws_rq, REQUEST_COLS, q["_row"], q)
        _delete_row(ws, row)
        if kind == "budget":
            _refresh_budget_summary(wb)
        _save(wb)
        return out


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
        for c in ("원인발생일", "재원", "예산목", "세목", "세세목", "거래처", "적요", "금액", "태그", "결제수단"):
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


def _person_usage(wb, name: str) -> int:
    return sum(1 for r in _rows(wb[SHEET_LABOR], LABOR_COLS) if _same_key(r["이름"], name)) \
        + sum(1 for r in _rows(wb[SHEET_SALARY], SALARY_COLS) if _same_key(r["이름"], name)) \
        + sum(1 for r in _rows(wb[SHEET_LADJ], LADJ_COLS) if _same_key(r["이름"], name))


def _payee_usage(wb, code: str) -> int:
    return sum(1 for r in _rows(wb[SHEET_LABOR], LABOR_COLS) if _same_key(r["지급처"], code))


def _remove_labor_exec(wb, number: str):
    """확정 취소·삭제 시 연결 집행 행 제거. 증빙이 붙어 있으면 차단."""
    ws_ex = wb[SHEET_EXEC]
    ex = next((x for x in _rows(ws_ex, EXEC_COLS) if x["거래번호"] == number), None)
    if ex is None:
        return
    if any(e["거래번호"] == number for e in _rows(wb[SHEET_EVID], EVID_COLS)):
        raise ValueError(f"집행 {number} 에 증빙이 등록되어 있어 취소할 수 없습니다. 증빙을 먼저 지우세요.")
    _delete_row(ws_ex, ex["_row"])


def labor_action(row: int, action: str, pay_date: str | None = None, expect: dict | None = None) -> dict:
    """confirm: 예정 → 확정 + 집행내역 1행 생성. unconfirm: 확정 → 예정 + 연결 집행 삭제."""
    with _write_session() as wb:
        ws = wb[SHEET_LABOR]
        rec = next((x for x in _rows(ws, LABOR_COLS) if x["_row"] == row), None)
        if rec is None:
            raise NotFound("지급 행을 찾을 수 없습니다. 목록을 새로고침하세요.")
        _check_expect("labor", rec, expect)
        if action == "confirm":
            if rec["상태"] == "확정":
                raise ValueError("이미 확정된 건입니다.")
            d = _to_date(pay_date) or dt.date.today().isoformat()
            if not _valid_date(d):
                raise ValueError(f"지급일이 올바르지 않습니다: {pay_date}")
            p = _person(wb, rec["이름"])
            ex = {c: "" for c in EXEC_COLS}
            ex.update({"원인발생일": d, "지급청구일": d, "결의일": d, "지출완료일": d, "재원": rec["지급처"], "결제수단": "계좌이체",
                       "예산목": LABOR_ITEM.get(p.get("인건비구분") or "내부", LABOR_ITEM["내부"]),
                       "세목": "인건비", "거래처": rec["이름"], "금액": rec["금액"],
                       "적요": f"인건비 {rec['이름']} {int(rec['귀속월'][5:])}월분" + (f" (지급월 {rec['지급월']})" if rec["지급월"] != rec["귀속월"] else ""),
                       "비고": (f"인건비 지급" + (f" / {rec['비고']}" if rec.get("비고") else ""))})
            _validate("exec", ex)
            ws_ex = wb[SHEET_EXEC]
            _assign_number(wb, ws_ex, EXEC_COLS, 1, "거래번호", ex)
            _write_row(ws_ex, EXEC_COLS, _next_row(ws_ex), ex)
            rec.update({"상태": "확정", "지급일": d, "연결거래번호": ex["거래번호"]})
        elif action == "unconfirm":
            if rec["상태"] != "확정":
                raise ValueError("확정된 건만 취소할 수 있습니다.")
            if rec.get("연결거래번호"):
                _remove_labor_exec(wb, rec["연결거래번호"])
            rec.update({"상태": "예정", "지급일": None, "연결거래번호": None})
        else:
            raise ValueError(f"알 수 없는 동작: {action}")
        _write_row(ws, LABOR_COLS, row, rec)
        _save(wb)
        return rec


def labor_bulk(rows: list[dict], skip_dup: bool = False) -> dict:
    """여러 예정 건을 한 번에 추가 (기간 일괄 생성·전월 복사). 하나라도 오류면 전부 취소."""
    if not rows:
        raise ValueError("추가할 지급 건이 없습니다.")
    if len(rows) > 1200:
        raise ValueError("한 번에 1,200건까지만 추가할 수 있습니다.")
    with _write_session() as wb:
        ws = wb[SHEET_LABOR]
        existing = _rows(ws, LABOR_COLS)
        created, skipped = [], []
        for raw in rows:
            rec = {c: raw.get(c, "") for c in LABOR_COLS}
            rec["상태"] = "예정"; rec["지급일"] = None; rec["연결거래번호"] = None
            _validate("labor", rec)
            try:
                _validate_labor_refs(wb, rec, existing + created)
            except ValueError as e:
                if skip_dup and "이미 있습니다" in str(e):
                    skipped.append(f"{rec['지급월']} {rec['이름']} {rec['지급처']}")
                    continue
                raise
            created.append(rec)
        if not created:
            raise ValueError("추가할 건이 없습니다." + (f" (중복 {len(skipped)}건 건너뜀)" if skipped else ""))
        r = _next_row(ws)
        for rec in created:
            _write_row(ws, LABOR_COLS, r, rec); r += 1
        _save(wb)
        return {"created": len(created), "skipped": skipped}


def exec_batch(creates: list[dict], updates: list[dict], deletes: list[dict]) -> dict:
    """집행내역 편집 모드 일괄 저장: 전부 검증한 뒤 한 번에 쓴다 (하나라도 오류면 아무것도 저장하지 않음).
    updates: [{row, rec, expect}], deletes: [{row, expect}], creates: [rec]. 오류 메시지는 '행 <거래번호|새 행 N>: ...' 형식."""
    if len(creates) + len(updates) + len(deletes) == 0:
        raise ValueError("저장할 변경이 없습니다.")
    if len(creates) + len(updates) + len(deletes) > 2000:
        raise ValueError("한 번에 2,000건까지만 저장할 수 있습니다.")
    with _write_session() as wb:
        ws = wb[SHEET_EXEC]
        cur = _rows(ws, EXEC_COLS)
        by_row = {r["_row"]: r for r in cur}
        linked = _labor_refs(wb) | _number_refs(wb, "거래번호")
        evid_nos = {e["거래번호"] for e in _rows(wb[SHEET_EVID], EVID_COLS)}
        prepared_u, prepared_d, prepared_c = [], [], []
        for u in updates:
            ex = by_row.get(int(u.get("row", 0)))
            if ex is None:
                raise NotFound(f"행 {u.get('row')}: 행을 찾을 수 없습니다. 편집 모드를 닫고 새로고침하세요.")
            tag = f"행 {ex['거래번호']}"
            try:
                _check_expect("exec", ex, u.get("expect"))
                rec = {c: ex.get(c) for c in EXEC_COLS}
                rec.update({c: v for c, v in (u.get("rec") or {}).items() if c in EXEC_COLS})
                rec["거래번호"] = ex["거래번호"]
                rec["상태"] = "보완" if str(rec.get("상태") or "") == "보완" else ex.get("상태")
                _validate("exec", rec)
                if ex["거래번호"] in linked:
                    for c in LINKED_LOCKED:
                        if _cell_out(c, rec.get(c)) != ex.get(c):
                            raise ValueError(f"인건비·적립금과 연결된 집행이라 {c}은(는) 바꿀 수 없습니다.")
                if str(rec.get("태그") or "").strip() != str(ex.get("태그") or ""):
                    _validate_tag(rec, wb)
            except (ValueError, NotFound) as e:
                raise type(e)(f"{tag}: {e}") from None
            prepared_u.append((ex["_row"], rec))
        for d in deletes:
            ex = by_row.get(int(d.get("row", 0)))
            if ex is None:
                raise NotFound(f"행 {d.get('row')}: 행을 찾을 수 없습니다. 편집 모드를 닫고 새로고침하세요.")
            tag = f"행 {ex['거래번호']}"
            try:
                _check_expect("exec", ex, d.get("expect"))
                if ex["거래번호"] in linked:
                    raise ValueError("인건비·적립금과 연결된 집행은 원본 화면에서 처리하세요.")
                if ex["거래번호"] in evid_nos:
                    raise ValueError("증빙이 등록된 집행입니다. 증빙을 먼저 지우세요.")
            except (ValueError, NotFound) as e:
                raise type(e)(f"{tag}: {e}") from None
            prepared_d.append(ex["_row"])
        for i, c in enumerate(creates, 1):
            rec = {col: "" for col in EXEC_COLS}
            rec.update({k: v for k, v in (c or {}).items() if k in EXEC_COLS})
            rec["거래번호"] = ""; rec["증빙폴더"] = ""; rec["증빙목록"] = ""
            try:
                _validate("exec", rec)
                _validate_tag(rec, wb)
            except ValueError as e:
                raise ValueError(f"새 행 {i}: {e}") from None
            prepared_c.append(rec)
        # 적용: 수정 → 추가(번호 부여) → 삭제(아래 행부터)
        for row, rec in prepared_u:
            _write_row(ws, EXEC_COLS, row, rec)
        numbers = []
        for rec in prepared_c:
            _assign_number(wb, ws, EXEC_COLS, 1, "거래번호", rec)
            _write_row(ws, EXEC_COLS, _next_row(ws), rec)
            numbers.append(rec["거래번호"])
        for row in sorted(prepared_d, reverse=True):
            _delete_row(ws, row)
        _save(wb)
        return {"updated": len(prepared_u), "created": numbers, "deleted": len(prepared_d)}


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
    """집행 행의 단계 처리. action: claim(지급청구일=오늘) | resolve(결의일=오늘) | unresolve | complete(지출완료일=오늘) | uncomplete | fix(보완) | unfix"""
    with _write_session() as wb:
        ws = wb[SHEET_EXEC]
        rec = next((x for x in _rows(ws, EXEC_COLS) if x["_row"] == row), None)
        if rec is None:
            raise NotFound("행을 찾을 수 없습니다. 목록을 새로고침하세요.")
        _check_expect("exec", rec, expect)
        today = dt.date.today().isoformat()
        if action == "claim":
            if rec.get("지출완료일") or rec.get("결의일"):
                raise ValueError("이미 완료·결의된 건입니다. 뒤 단계를 취소한 뒤 청구일을 바꾸세요.")
            rec["지급청구일"] = today
        elif action == "uncomplete":
            if rec.get("결의일"):
                raise ValueError("결의된 건은 먼저 결의를 취소하세요.")
            rec["지출완료일"] = ""
        elif action == "complete":
            if rec.get("결의일"):
                raise ValueError("이미 결의된 건입니다.")
            rec["지출완료일"] = today
            if not rec.get("지급청구일"):
                rec["지급청구일"] = today
        elif action == "resolve":  # 결의 (마지막 단계). 비어 있는 앞 단계 날짜는 같은 날로 채움
            rec["결의일"] = today
            if not rec.get("지급청구일"):
                rec["지급청구일"] = today
            if not rec.get("지출완료일"):
                rec["지출완료일"] = today
        elif action == "unresolve":
            rec["결의일"] = ""
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


# ---------- 신청 (신청_설계_2026-10-14.md) ----------
def _find_row(ws, cols, row: int, label: str) -> dict:
    rec = next((x for x in _rows(ws, cols) if x["_row"] == row), None)
    if rec is None:
        raise NotFound(f"{label} 행을 찾을 수 없습니다. 목록을 새로고침하세요.")
    return rec


def request_action(row: int, action: str, extra: dict | None = None, expect: dict | None = None) -> dict:
    """신청 결재. approve(신청·반려→승인) | reject(사유 필수 → 반려) | unapprove(승인→신청) | reopen(반려→신청)."""
    extra = extra or {}
    with _write_session() as wb:
        ws = wb[SHEET_RQ]
        rec = _find_row(ws, REQUEST_COLS, row, "신청")
        _check_expect("request", rec, expect)
        state = _req_state(wb)
        status = request_status(rec, state)
        who = str(extra.get("결재인") or "").strip() or "담당자"
        when = _to_date(extra.get("결재일")) or dt.date.today().isoformat()
        if not _valid_date(when):
            raise ValueError(f"결재일 형식이 올바르지 않습니다 (YYYY-MM-DD): {extra.get('결재일')}")
        if action == "approve":
            if status not in ("신청", "반려"):
                raise ValueError(f"'{status}' 상태의 신청은 승인할 수 없습니다 (신청·반려만 가능).")
            rec.update({"상태": "승인", "결재인": who, "결재일": when, "반려사유": ""})
        elif action == "reject":
            reason = str(extra.get("사유") or extra.get("반려사유") or "").strip()
            if not reason:
                raise ValueError("반려 사유를 입력하세요.")
            if status not in ("신청", "승인"):
                raise ValueError(f"'{status}' 상태의 신청은 반려할 수 없습니다.")
            if rec.get("주문번호"):
                raise ValueError(f"주문 {rec['주문번호']} 에 묶인 신청입니다. 주문을 먼저 취소하세요.")
            rec.update({"상태": "반려", "결재인": who, "결재일": when, "반려사유": reason})
        elif action == "unapprove":
            if status in REQUEST_LOCKED:
                raise ValueError("품의로 전환된 신청은 승인을 취소할 수 없습니다. 연결 품의를 먼저 삭제하세요.")
            if status != "승인":
                raise ValueError("승인된 신청만 승인 취소할 수 있습니다.")
            if rec.get("주문번호"):
                raise ValueError(f"주문 {rec['주문번호']} 에 묶인 신청입니다. 주문을 먼저 취소하세요.")
            rec.update({"상태": "신청", "결재인": "", "결재일": ""})
        elif action == "reopen":
            if status != "반려":
                raise ValueError("반려된 신청만 다시 신청 상태로 돌릴 수 있습니다.")
            rec.update({"상태": "신청", "결재인": "", "결재일": ""})  # 반려사유는 이력으로 남김 (승인 시 비움)
        else:
            raise ValueError(f"알 수 없는 동작: {action}")
        _write_row(ws, REQUEST_COLS, row, rec)
        _save(wb)
        rec["상태"] = request_status(rec, state)
        return rec


def _pick_requests(ws, rows: list, expects: list | None) -> list[dict]:
    if not rows:
        raise ValueError("신청을 1건 이상 선택하세요.")
    rows = [int(r) for r in rows]
    if len(set(rows)) != len(rows):
        raise ValueError("같은 신청이 중복 선택되었습니다.")
    cur = {r["_row"]: r for r in _rows(ws, REQUEST_COLS)}
    picked = []
    for i, row in enumerate(rows):
        rec = cur.get(row)
        if rec is None:
            raise NotFound(f"행 {row}: 신청을 찾을 수 없습니다. 목록을 새로고침하세요.")
        exp = expects[i] if expects and i < len(expects) else None
        try:
            _check_expect("request", rec, exp)
        except NotFound as e:
            raise NotFound(f"{rec['신청번호']}: {e}") from None
        picked.append(rec)
    return picked


def request_convert(rows: list, extra: dict | None = None, expects: list | None = None) -> dict:
    """승인된 신청 여러 건 → 품의 1건 (한 번에 저장). 신청은 품의전환 + 연결품의번호 기록."""
    extra = extra or {}
    with _write_session() as wb:
        ws = wb[SHEET_RQ]
        picked = _pick_requests(ws, rows, expects)
        state = _req_state(wb)
        for q in picked:
            st = request_status(q, state)
            if st != "승인" or q.get("연결품의번호"):
                raise ValueError(f"{q['신청번호']}: '{st}' 상태라 품의로 전환할 수 없습니다 (승인된 신청만 가능).")
        numbers = [q["신청번호"] for q in picked]
        items = [q["품목"] for q in picked]
        names = list(dict.fromkeys(q["신청인"] for q in picked if q.get("신청인")))
        summary = ", ".join(items) if len(items) <= 3 else ", ".join(items[:3]) + f" 외 {len(items) - 3}건"
        orders = {q.get("주문번호") or "" for q in picked}
        vendor = ""
        if len(orders) == 1 and next(iter(orders)):  # 한 주문 묶음이면 주문 거래처를 기본값으로
            o = next((x for x in _rows(wb[SHEET_ORDER], ORDER_COLS) if x["주문번호"] == next(iter(orders))), None)
            vendor = (o or {}).get("거래처") or ""
        rec = {c: "" for c in REQ_COLS}
        rec.update({c: v for c, v in extra.items() if c in REQ_COLS and c not in ("품의번호", "상태", "비고")})
        rec["원인발생일"] = _to_date(extra.get("원인발생일")) or dt.date.today().isoformat()
        rec["적요"] = str(extra.get("적요") or "").strip() or summary
        rec["금액"] = extra.get("금액") if extra.get("금액") not in (None, "") else sum(_to_num(q.get("금액")) for q in picked)
        rec["품의자"] = str(extra.get("품의자") or "").strip() or ", ".join(names)
        rec["거래처"] = str(extra.get("거래처") or "").strip() or vendor
        rec["비고"] = f"신청 {', '.join(numbers)}" + (f" / {extra['비고']}" if str(extra.get("비고") or "").strip() else "")
        rec["상태"] = "대기"
        _validate("req", rec)
        _validate_tag(rec, wb)
        ws_req = wb[SHEET_REQ]
        _assign_number(wb, ws_req, REQ_COLS, 1, "품의번호", rec)
        r = _next_row(ws_req)
        _write_row(ws_req, REQ_COLS, r, rec)
        for q in picked:
            q.update({"상태": "품의전환", "연결품의번호": rec["품의번호"]})
            _write_row(ws, REQUEST_COLS, q["_row"], q)
        _save(wb)
        rec["_row"] = r
        return {"req": rec, "numbers": numbers, "품의번호": rec["품의번호"]}


def _yes(v) -> bool:
    return v is True or str(v or "").strip().upper() in ("Y", "1", "TRUE", "예", "YES")


def order_create(rows: list, extra: dict | None = None, expects: list | None = None) -> dict:
    """승인된 소모품 신청 묶음 → 주문 1건. 적립금사용=Y 면 적립금 '사용' 1행도 함께 기록."""
    extra = extra or {}
    with _write_session() as wb:
        ws = wb[SHEET_RQ]
        picked = _pick_requests(ws, rows, expects)
        state = _req_state(wb)
        for q in picked:
            st = request_status(q, state)
            if q["구분"] != "소모품":
                raise ValueError(f"{q['신청번호']}: 소모품 신청만 주문으로 묶을 수 있습니다.")
            if st != "승인" or q.get("연결품의번호"):
                raise ValueError(f"{q['신청번호']}: '{st}' 상태라 주문할 수 없습니다 (승인된 신청만 가능).")
            if q.get("주문번호"):
                raise ValueError(f"{q['신청번호']}: 이미 주문 {q['주문번호']} 에 묶여 있습니다.")
        d = _to_date(extra.get("주문일")) or dt.date.today().isoformat()
        if not _valid_date(d):
            raise ValueError(f"주문일 형식이 올바르지 않습니다 (YYYY-MM-DD): {extra.get('주문일')}")
        total = sum(_to_num(q.get("금액")) for q in picked)
        pay = _to_num(extra.get("결제금액"), strict=True) if extra.get("결제금액") not in (None, "") else total
        if pay < 0:
            raise ValueError("결제금액은 0 이상이어야 합니다.")
        use = _yes(extra.get("적립금사용"))
        order = {"주문번호": "", "주문일": d, "배송일": "", "거래처": str(extra.get("거래처") or "").strip() or ORDER_VENDOR,
                 "주문금액": total, "결제금액": pay, "적립금사용": "Y" if use else "N",
                 "신청번호목록": ", ".join(q["신청번호"] for q in picked), "비고": str(extra.get("비고") or "")}
        ws_o = wb[SHEET_ORDER]
        _assign_order_number(wb, ws_o, order)
        dep = None
        if use:
            dep = {c: "" for c in DEP_COLS}
            dep.update({"일자": d, "거래처": order["거래처"], "구분": "사용", "금액": pay,
                        "적요": f"소모품 주문 {order['주문번호']}", "증빙번호": order["주문번호"],
                        "사용자": str(extra.get("사용자") or ""), "태그": str(extra.get("태그") or "")})
            _validate("deposit", dep)
            _validate_tag(dep, wb)
            ws_d = wb[SHEET_DEP]
            dep["_row"] = _next_row(ws_d)
            _write_row(ws_d, DEP_COLS, dep["_row"], dep)
        r = _next_row(ws_o)
        _write_row(ws_o, ORDER_COLS, r, order)
        for q in picked:
            q["주문번호"] = order["주문번호"]
            _write_row(ws, REQUEST_COLS, q["_row"], q)
        _save(wb)
        order["_row"] = r
        return {"order": order, "deposit": dep, "numbers": [q["신청번호"] for q in picked]}


def order_action(row: int, action: str, extra: dict | None = None, expect: dict | None = None) -> dict:
    """주문 처리. deliver(배송일=오늘/지정) | undeliver(배송일 비움) | cancel(배송 전만: 신청 주문번호 해제·적립금 사용 행 삭제·주문 삭제)."""
    extra = extra or {}
    with _write_session() as wb:
        ws = wb[SHEET_ORDER]
        order = _find_row(ws, ORDER_COLS, row, "주문")
        _check_expect("order", order, expect)
        no = order["주문번호"]
        result = {"order": order}
        if action == "deliver":
            d = _to_date(extra.get("배송일")) or dt.date.today().isoformat()
            if not _valid_date(d):
                raise ValueError(f"배송일 형식이 올바르지 않습니다 (YYYY-MM-DD): {extra.get('배송일')}")
            order["배송일"] = d
            _write_row(ws, ORDER_COLS, row, order)
        elif action == "undeliver":
            order["배송일"] = ""
            _write_row(ws, ORDER_COLS, row, order)
        elif action == "cancel":
            if order.get("배송일"):
                raise ValueError("배송된 주문은 취소할 수 없습니다. 배송일을 먼저 비우세요.")
            ws_rq = wb[SHEET_RQ]
            linked = [q for q in _rows(ws_rq, REQUEST_COLS) if q.get("주문번호") == no]
            conv = [q["신청번호"] for q in linked if q.get("연결품의번호")]
            if conv:
                raise ValueError(f"품의로 전환된 신청({', '.join(conv)})이 있어 주문을 취소할 수 없습니다. 연결 품의를 먼저 삭제하세요.")
            for q in linked:
                q["주문번호"] = ""
                _write_row(ws_rq, REQUEST_COLS, q["_row"], q)
            ws_d = wb[SHEET_DEP]
            dep = next((x for x in _rows(ws_d, DEP_COLS) if x["구분"] == "사용" and x.get("증빙번호") == no), None)
            if dep is not None:
                _delete_row(ws_d, dep["_row"])
            _delete_row(ws, row)
            result.update({"cancelled": True, "deposit_removed": dep is not None, "released": [q["신청번호"] for q in linked]})
        else:
            raise ValueError(f"알 수 없는 동작: {action}")
        _save(wb)
        return result


def order_sheet(row: int) -> dict:
    """발주서용: 주문 행 + 묶인 신청 줄 (순번·온라인코드·상품코드·품목·규격·수량·단가·금액·신청번호·신청인·상품링크·관련과제)."""
    with _lock:
        wb = _load()
        _ensure_structure(wb)
        order = _find_row(wb[SHEET_ORDER], ORDER_COLS, row, "주문")
        listed = [n.strip() for n in str(order.get("신청번호목록") or "").split(",") if n.strip()]
        reqs = [q for q in _rows(wb[SHEET_RQ], REQUEST_COLS) if q.get("주문번호") == order["주문번호"]]
        reqs.sort(key=lambda q: listed.index(q["신청번호"]) if q["신청번호"] in listed else len(listed))
        lines = [{"순번": i, **{c: q.get(c) for c in ("온라인코드", "상품코드", "품목", "규격", "수량", "단가", "금액",
                                                   "신청번호", "신청인", "상품링크", "관련과제")}}
                 for i, q in enumerate(reqs, 1)]
        return {"order": order, "lines": lines, "total": sum(_to_num(x["금액"]) for x in lines)}


def ratt_for(number: str) -> list[dict]:
    with _lock:
        wb = _load()
        _ensure_structure(wb)
        return [r for r in _rows(wb[SHEET_RATT], RATT_COLS) if r["신청번호"] == number]


def ratt_names(number: str) -> list[str]:
    """같은 신청의 기존 파일명 (중복 번호 부여용)."""
    return [e["파일명"] for e in ratt_for(number)]


def _sync_request_attach(wb, number: str, folder_url: str | None = None):
    """신청의 첨부목록(원본 파일명 나열)·첨부폴더 열을 신청첨부 시트 기준으로 갱신."""
    ws = wb[SHEET_RQ]
    rec = next((x for x in _rows(ws, REQUEST_COLS) if x["신청번호"] == number), None)
    if rec is None:
        return
    names = [a["원본파일명"] or a["파일명"] for a in _rows(wb[SHEET_RATT], RATT_COLS) if a["신청번호"] == number]
    rec["첨부목록"] = ", ".join(names)[:32000]
    if folder_url:
        rec["첨부폴더"] = folder_url
    _write_row(ws, REQUEST_COLS, rec["_row"], rec)


def ratt_add(items: list[dict], folder_url: str | None = None) -> list[dict]:
    """신청첨부 시트에 여러 행 추가 후 신청 요약 갱신. items 는 RATT_COLS 키를 가진 dict 목록."""
    with _write_session() as wb:
        ws = wb[SHEET_RATT]
        known = {q["신청번호"] for q in _rows(wb[SHEET_RQ], REQUEST_COLS)}
        out = []
        for it in items:
            _validate("ratt", it)
            if it["신청번호"] not in known:
                raise NotFound(f"신청 {it['신청번호']} 을(를) 찾을 수 없습니다.")
            r = _next_row(ws)
            _write_row(ws, RATT_COLS, r, it)
            it["_row"] = r
            out.append(it)
        for number in {it["신청번호"] for it in items}:
            _sync_request_attach(wb, number, folder_url)
        _save(wb)
        return out


def ratt_delete(row: int, expect: dict | None = None) -> dict:
    """신청첨부 행 삭제 후 신청 요약 갱신. 삭제된 행(드라이브파일ID 포함) 반환."""
    with _write_session() as wb:
        ws = wb[SHEET_RATT]
        rec = _find_row(ws, RATT_COLS, row, "첨부")
        _check_expect("ratt", rec, expect)
        _delete_row(ws, row)
        _sync_request_attach(wb, rec["신청번호"])
        _save(wb)
        return rec
