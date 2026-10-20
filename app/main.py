"""센터 회계대장 관리도구 - FastAPI 서버.

실행:  python main.py   (또는 run.bat)
"""
from __future__ import annotations

import json
import logging
import os
import threading
import webbrowser
from collections import defaultdict
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
import datetime as dt

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import settings  # noqa: E402  (외부 의존 없음: LEDGER_ENV 로 설정 파일 경로 결정)
load_dotenv(settings.ENV_PATH)  # 기본 app/.env, LEDGER_ENV 가 있으면 그 파일

import ai  # noqa: E402
import drive  # noqa: E402
import store  # noqa: E402

HOST, PORT = "127.0.0.1", int(os.environ.get("LEDGER_PORT", "8791"))
STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="센터 회계대장 관리도구")
log = logging.getLogger("ledger")


@app.exception_handler(store.LedgerLocked)
async def _locked(_: Request, e: store.LedgerLocked):
    return JSONResponse({"detail": str(e)}, status_code=423)


@app.exception_handler(store.NotFound)
async def _notfound(_: Request, e: store.NotFound):
    return JSONResponse({"detail": str(e)}, status_code=404)


@app.exception_handler(ai.AIError)
async def _ai_err(_: Request, e: ai.AIError):
    return JSONResponse({"detail": str(e)}, status_code=502)


@app.exception_handler(store.TooLarge)
async def _too_large(_: Request, e: store.TooLarge):
    return JSONResponse({"detail": str(e)}, status_code=413)


@app.exception_handler(store.EvidHasFile)
async def _has_file(_: Request, e: store.EvidHasFile):
    return JSONResponse({"detail": str(e)}, status_code=409)


@app.exception_handler(ValueError)
async def _bad(_: Request, e: ValueError):
    return JSONResponse({"detail": str(e)}, status_code=400)


@app.exception_handler(Exception)
async def _unhandled(request: Request, e: Exception):
    """예상하지 못한 오류: 콘솔에 traceback 을 남기고, 화면에는 읽을 수 있는 JSON detail (500)."""
    log.error("처리 중 오류: %s %s", request.method, request.url.path, exc_info=(type(e), e, e.__traceback__))
    msg = str(e).strip() or type(e).__name__
    return JSONResponse({"detail": f"서버 오류: {msg[:300]} (콘솔 창에 자세한 내용이 있습니다)"}, status_code=500)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/labor")
def labor_page():
    """인건비 화면: 같은 페이지, 주소로 모드 전환."""
    return FileResponse(STATIC / "index.html")


@app.get("/request")
def request_page():
    """신청 화면: 같은 페이지, 주소로 모드 전환 (직접 접속은 연구원 화면)."""
    return FileResponse(STATIC / "index.html")


@app.post("/api/undo")
def undo_last(body: dict | None = None):
    """직전 저장을 되돌림 (삭제·확정 취소·상태 변경 토스트의 '되돌리기'). body.write_id 가 직전 쓰기와 다르면 거부."""
    return store.undo_last((body or {}).get("write_id"))


@app.get("/api/meta")
def meta():
    """가벼운 상태 확인: 파일 수정 시각 (다른 창·MCP 변경 감지용) + 소모품 구매처 목록·이용 가능 여부·안내 (연구원 화면은 설정 API를 쓰지 않음)."""
    import datetime as _dt
    return {"mtime": _dt.datetime.fromtimestamp(store.XLSX_PATH.stat().st_mtime).isoformat(timespec="seconds"), "write_id": store.last_write_id(),
            "exec_status_labels": store.EXEC_STATUS_LABEL, **store.supplier_meta()}


@app.middleware("http")
async def _write_id_header(request: Request, call_next):
    """쓰기 요청 뒤 직전 쓰기 ID를 헤더로 전달 (토스트 '되돌리기'가 자기 변경만 되돌리도록)."""
    response = await call_next(request)
    if request.method in ("POST", "PUT", "DELETE") and request.url.path.startswith("/api/"):
        wid = store.last_write_id()
        if wid:
            response.headers["X-Write-Id"] = wid
    return response


@app.post("/api/exec/batch")
def exec_batch(body: dict):
    """편집 모드 일괄 저장 (전부 성공 또는 전부 취소)."""
    return store.exec_batch(body.get("creates") or [], body.get("updates") or [], body.get("deletes") or [])


@app.post("/api/labor/bulk")
def labor_bulk(body: dict):
    return store.labor_bulk(body.get("rows") or [], bool(body.get("skip_dup")))


@app.post("/api/labor/{row}/action")
def labor_action(row: int, body: dict):
    return store.labor_action(row, body.get("action", ""), body.get("pay_date"), body.get("expect"))


@app.get("/api/all")
def all_data():
    data = store.read_all()
    data["dashboard"] = build_dashboard(data)
    return data


def excluded_reason(r: dict, funds: set, items) -> str:
    """예산 집계 제외 사유 (웹 isExcludedExec 와 같은 규칙): 재원 시트에 없는 재원(외부 지급처 인건비 등) 또는 BUDGET_ITEMS 밖 예산목. 집계 대상이면 ''."""
    out = []
    if r.get("재원") not in funds:
        out.append("재원 목록 밖")
    if r.get("예산목") not in items:
        out.append("예산목 목록 밖")
    return " · ".join(out)


def build_dashboard(data: dict) -> dict:
    """웹 대시보드와 같은 집계 범위: 재원 시트의 재원 × BUDGET_ITEMS 예산목만 table 에 집계.
    목록 밖 집행(전체)과 대기 품의는 excluded.exec / excluded.req 로 따로 돌려주고 합계는 excluded_total.
    monthly·vendors·unpaid_count·tag_table 은 웹과 같이 전체 집행 기준 (예산 집계만 제외)."""
    items = list(store.BUDGET_ITEMS)
    all_funds = [f["재원코드"] for f in data["funds"] if f.get("재원코드")]
    fund_set = set(all_funds)  # 재원 시트의 재원이면 '목록 밖'이 아님 (잔액 미관리 재원 포함)
    untracked = {f["재원코드"] for f in data["funds"] if f.get("재원코드") and (f.get("잔액미관리") or "").upper() == "Y"}
    funds = [f for f in all_funds if f not in untracked]  # 예산 집계 대상 = 잔액을 관리하는 재원
    pool = {f["재원코드"] for f in data["funds"] if f.get("재원코드") and (f.get("종류") or store.FUND_TYPE_DEFAULT) == store.FUND_TYPE_POOL}
    deposits = {f: 0.0 for f in funds}  # 공금: 예산변동 '입금' 합계 (예산목 구분 없음)
    for r in data["budget"]:
        if r["재원"] in pool:
            deposits[r["재원"]] += r.get("입금") or 0

    budget = {f: {i: 0.0 for i in items} for f in funds}
    for r in data["budget"]:
        if r["재원"] in budget:
            for i in items:
                budget[r["재원"]][i] += r.get(i) or 0

    spent = {f: {i: 0.0 for i in items} for f in funds}
    monthly = defaultdict(lambda: defaultdict(float))  # fund -> 'YYYY-MM' -> amt
    vendors = defaultdict(float)
    unpaid = 0
    excluded = {"exec": [], "req": []}
    for r in store.active_exec(data["exec"]):  # 취소 건은 모든 집계에서 뺀다 (2026-10-19)
        f, i = r["재원"], r["예산목"]
        why = excluded_reason(r, fund_set, items)
        if why:
            excluded["exec"].append({"거래번호": r.get("거래번호"), "원인발생일": r.get("원인발생일"), "재원": f, "예산목": i,
                                     "금액": r["금액"], "거래처": r.get("거래처"), "사유": why, "_row": r.get("_row")})
        elif f in spent:  # 잔액 미관리 재원의 집행은 예산 집계에 넣지 않는다 (집계 제외 목록에도 없음)
            spent[f][i] += r["금액"]
        if r["원인발생일"]:
            monthly[f][r["원인발생일"][:7]] += r["금액"]
        if r["거래처"]:
            vendors[r["거래처"]] += r["금액"]
        if not r["지출완료일"]:
            unpaid += 1

    pending = {f: {i: 0.0 for i in items} for f in funds}
    for r in data["req"]:
        if r["상태"] != "대기":
            continue
        why = excluded_reason(r, fund_set, items)
        if why:
            excluded["req"].append({"품의번호": r.get("품의번호"), "원인발생일": r.get("원인발생일"), "재원": r["재원"], "예산목": r["예산목"],
                                    "금액": r["금액"], "거래처": r.get("거래처"), "사유": why, "_row": r.get("_row")})
        elif r["재원"] in pending:
            pending[r["재원"]][r["예산목"]] += r["금액"]

    table = []
    for f in funds:
        if f in pool:  # 공금: 예산목 구분 없이 재원 잔액 한 줄
            b, s, p = deposits[f], sum(spent[f].values()), sum(pending[f].values())
            if b or s or p:
                table.append({"재원": f, "예산목": "(공금 잔액)", "예산현액": b, "집행액": s, "잔액": b - s,
                              "집행률": (s / b) if b else None, "품의대기": p, "가용잔액": b - s - p})
            continue
        for i in items:
            b, s, p = budget[f][i], spent[f][i], pending[f][i]
            if b == 0 and s == 0 and p == 0:
                continue
            table.append({"재원": f, "예산목": i, "예산현액": b, "집행액": s, "잔액": b - s,
                          "집행률": (s / b) if b else None, "품의대기": p, "가용잔액": b - s - p})
    # 태그 집계: 집행내역(적립 선결제 건 제외) + 적립금 사용
    linked = {r["연결거래번호"] for r in data["deposit"] if r.get("연결거래번호")}
    tag_rows = [(r["태그"], r["원인발생일"], r["금액"]) for r in store.active_exec(data["exec"]) if r["거래번호"] not in linked]
    tag_rows += [(r["태그"], r["일자"], r["금액"]) for r in data["deposit"] if r["구분"] == "사용"]  # 구분 '적립'/'사용' 외 행은 집계 제외
    tag_cat = {t["태그명"]: t["분류"] for t in data.get("tags", [])}
    tag_table = {}
    for t, d, amt in tag_rows:
        t = t or "(태그 없음)"
        e = tag_table.setdefault(t, {"태그": t, "분류": tag_cat.get(t, ""), "금액": 0.0, "건수": 0, "월별": defaultdict(float)})
        e["금액"] += amt or 0
        e["건수"] += 1
        if d:
            e["월별"][d[:7]] += amt or 0
    for e in tag_table.values():
        e["월별"] = dict(sorted(e["월별"].items()))
    return {
        "funds": funds,
        "table": table,
        "excluded": excluded,
        "excluded_total": {"exec": sum(x["금액"] or 0 for x in excluded["exec"]), "exec_count": len(excluded["exec"]),
                           "req": sum(x["금액"] or 0 for x in excluded["req"]), "req_count": len(excluded["req"])},
        "tag_table": sorted(tag_table.values(), key=lambda e: (e["분류"], e["태그"])),
        "monthly": {f: dict(sorted(m.items())) for f, m in monthly.items()},
        "vendors": sorted(vendors.items(), key=lambda x: -x[1])[:15],
        "unpaid_count": unpaid,
    }


# ---------- 신청 / 주문 / 신청 첨부 ----------
@app.post("/api/request/convert")
def request_convert(body: dict):
    """body: {rows: [신청 _row...], expects: [{신청번호, _snapshot?}...], extra: {품의 열..., amount_override?}} → {req, numbers, 품의번호, order}
    주문에 묶인 신청은 같은 주문의 미전환 신청 전부를 함께 (주문 1건 = 품의 1건), 금액 기본 = 주문 결제금액."""
    return store.request_convert(body.get("rows") or [], body.get("extra") or {}, body.get("expects"))


@app.post("/api/request/batch-action")
def request_batch_action(body: dict):
    """일괄 결재: body {rows: [{row, expect}], action: approve|reject|unapprove|reopen, extra: {결재인?, 결재일?, 사유?}}.
    한 번 저장 · 전부 성공 또는 전부 취소. → {action, count, items, numbers}"""
    return store.request_batch_action(body.get("rows") or [], body.get("action") or "", body.get("extra") or {})


@app.post("/api/request/{row}/action")
def request_action(row: int, body: dict):
    """body: {action: approve|reject|unapprove|reopen, extra: {결재인?, 결재일?, 사유?}, expect}"""
    return store.request_action(row, body.get("action") or "", body.get("extra") or {}, body.get("expect"))


@app.get("/api/request/order-sheet/{order_row}")
def request_order_sheet(order_row: int):
    """발주서 데이터 (독자 = 공급처): {order, lines, internal, totals: {공급가합계, 부가세, 총액}, total, vat_total,
    header: {발주기관, 공급처, 배송지, 담당자}, settings: {발주처, 배송지, 담당자}(이전 이름, 호환)}.
    발주기관 = 설정 REQUEST_BUYER(우리 센터), 공급처 = 주문 구매처(order.거래처). 신청번호는 internal 에만 (적립금 정보 없음)."""
    data = store.order_sheet(order_row)
    buyer, ship, contact = settings.get("REQUEST_BUYER"), settings.get("REQUEST_SHIP_TO"), settings.get("REQUEST_CONTACT")
    data["header"] = {"발주기관": buyer, "공급처": data["order"].get("거래처") or "", "배송지": ship, "담당자": contact}
    data["settings"] = {"발주처": buyer, "배송지": ship, "담당자": contact}
    return data


@app.post("/api/order/create")
def order_create(body: dict):
    """body: {rows: [소모품 신청 _row...], expects: [...], extra: {주문일?, 구매처?(또는 거래처), vendor_override?, 결제금액?, 적립금사용?, 사용자?, 태그?, 비고?}}
    → {order, deposit, numbers, warnings: [..]} (warnings: 결제금액 > 주문금액, 적립금 잔액 음수 — 저장은 됨)"""
    return store.order_create(body.get("rows") or [], body.get("extra") or {}, body.get("expects"))


@app.post("/api/order/{row}/action")
def order_action(row: int, body: dict):
    """body: {action: deliver|undeliver|cancel, extra: {배송일?}, expect}. cancel → {cancelled, deposit_removed, deposit_missing, released}"""
    return store.order_action(row, body.get("action") or "", body.get("extra") or {}, body.get("expect"))


@app.get("/api/ratt/thumb/{file_id:path}")
def ratt_thumb(file_id: str):
    return evidence_thumb(file_id)


@app.get("/api/ratt/{number}")
def ratt_list(number: str):
    items = store.ratt_for(number)
    for it in items:
        it["url"] = drive.file_url(it["드라이브파일ID"]) if it.get("드라이브파일ID") else ""
    return {"items": items, "drive": drive.status()}


@app.post("/api/ratt/{number}")
async def ratt_upload(number: str, files: list[UploadFile] = File(...), note: str = Form(""), expect: str = Form("")):
    """여러 파일을 드라이브 신청/YYYY/신청번호 에 올리고 신청첨부 시트에 기록 (실패 시 올린 파일은 휴지통).
    규칙: 신청·반려·승인 상태만, 파일당 25MB, 신청 1건에 20개·합계 100MB (넘으면 413).
    expect (선택, JSON 문자열 {신청번호, _snapshot}): 열린 패널이 보던 행과 다르면 404 (오래된 패널에서 올리기 방지)."""
    exp = None
    if expect.strip():
        try:
            exp = json.loads(expect)
        except ValueError:
            raise HTTPException(400, "expect 형식이 올바르지 않습니다 (JSON).") from None
    store.ratt_precheck(number)  # 없는 신청·올릴 수 없는 상태는 파일을 읽기 전에 거부
    blobs = []
    for f in files:  # 크기 검사를 먼저 전부 수행 (중간 실패로 고아 파일이 생기지 않도록)
        data = await f.read()
        if len(data) > 25 * 1024 * 1024:
            raise HTTPException(413, f"{f.filename}: 25MB 를 넘습니다. 아무것도 올리지 않았습니다.")
        if not data:
            raise HTTPException(400, f"{f.filename}: 빈 파일입니다.")
        blobs.append((f, data))
    rec = store.ratt_precheck(number, len(blobs), sum(len(d) for _, d in blobs), exp if isinstance(exp, dict) else None)
    year = (rec.get("신청일") or dt.date.today().isoformat())[:4]
    folder = drive.ensure_folder([year, number], root=drive.REQUEST_ROOT)
    existing = store.ratt_names(number)
    items, uploaded = [], []
    try:
        for f, data in blobs:
            name = drive.build_request_filename(number, rec.get("품목") or "", f.filename or "", existing)
            existing.append(name)
            up = drive.upload(folder, name, data, f.content_type or "")
            uploaded.append(up["id"])
            items.append({"신청번호": number, "파일명": name, "원본파일명": f.filename or "", "드라이브파일ID": up["id"],
                          "크기": up["size"], "업로드일": dt.date.today().isoformat(), "비고": note})
        saved = store.ratt_add(items, folder["url"])
    except Exception:
        for fid in uploaded:  # 이번 요청에서 올린 파일은 되돌림(휴지통)
            try:
                drive.trash(fid)
            except Exception:
                pass
        raise
    for it in saved:
        it["url"] = drive.file_url(it["드라이브파일ID"])
    return {"items": saved, "folder": folder}


def ratt_delete(row: int, body: dict | None = None):
    """body: {expect, extra: {admin?}} — 승인된 신청의 첨부는 admin=true(담당자 화면)일 때만. admin 은 화면 구분이며 보안 장치가 아님."""
    body = body or {}
    rec = store.ratt_delete(row, body.get("expect"), bool((body.get("extra") or {}).get("admin")))
    try:
        drive.trash(rec.get("드라이브파일ID") or "")
    except drive.DriveError as e:
        return {"ok": True, "warning": f"장부에서는 지웠지만 드라이브 휴지통 이동 실패: {e}"}
    return {"ok": True}


@app.post("/api/{kind}")
def create(kind: str, rec: dict):
    _kind(kind)
    if kind in ("order", "ratt"):
        raise HTTPException(400, "주문은 '주문 생성'(/api/order/create), 첨부는 파일 업로드로 추가하세요.")
    return store.create(kind, rec)


@app.put("/api/{kind}/{row}")
def update(kind: str, row: int, body: dict):
    """body: 레코드 자체, 또는 {"rec": {...}, "expect": {식별열: 값}, "extra": {...}} (expect 는 행 밀림 감지용).
    신청: extra.keep_approval=true 면 승인된 신청의 품목·금액 등을 바꿔도 승인 유지, 아니면 '신청'으로 되돌리고 결과에 reapproval: true."""
    _kind(kind)
    # 신형: {"rec": {...}, "expect": {...}, "extra": {...}} / 구형(예전 화면 캐시): 레코드 자체
    if isinstance(body.get("rec"), dict):
        rec, expect, extra = body.get("rec"), body.get("expect"), body.get("extra")
    else:
        rec, expect, extra = body, None, None
    return store.update(kind, row, rec, expect, extra if isinstance(extra, dict) else None)


@app.delete("/api/{kind}/{row}")
def delete(kind: str, row: int, body: dict | None = None):
    if kind == "evidence":  # 경로 매칭 순서상 여기로 먼저 들어오므로 전용 처리(드라이브 휴지통 이동)로 위임
        return evidence_delete(row, body)
    if kind == "ratt":  # 신청 첨부도 같은 방식
        return ratt_delete(row, body)
    _kind(kind)
    body = body or {}
    res = store.delete(kind, row, body.get("expect"), bool(body.get("cascade"))) or {}
    failed = 0
    for fid in res.get("trash") or []:  # 신청을 첨부와 함께 지운 경우 드라이브 파일도 휴지통으로
        try:
            drive.trash(fid)
        except Exception:
            failed += 1
    if failed:
        return {"ok": True, "warning": f"장부에서는 지웠지만 첨부 {failed}건의 드라이브 휴지통 이동 실패"}
    return {"ok": True}


@app.get("/api/budget/next-round")
def budget_next_round(fund: str = ""):
    return {"round": store.next_budget_round(fund) if fund else "당초"}


@app.post("/api/req/{row}/to-exec")
def req_to_exec(row: int, body: dict):
    return store.req_to_exec(row, body.get("extra") or {}, body.get("expect"))


# ---------- AI ----------
@app.get("/api/ai/status")
def ai_status():
    return {"enabled": ai.enabled(), "model": ai.model(), "provider": ai.provider()}


# ---------- 설정 (관리 패널) ----------
@app.get("/api/settings")
def get_settings():
    return {"values": settings.masked()}


@app.put("/api/settings")
def put_settings(body: dict):
    vals = settings.save(body or {})
    return {"values": vals, "status": {"enabled": ai.enabled(), "model": ai.model(), "provider": ai.provider()},
            "request": store.supplier_meta()}


@app.post("/api/settings/test")
def test_settings(body: dict | None = None):
    """body 에 후보 설정값이 오면 저장하지 않고 임시 적용해 테스트한다 (성공 시 클라이언트가 저장)."""
    body = body or {}
    saved = {k: os.environ.get(k) for k in settings.FIELDS}
    try:
        for k, v in body.items():
            if k not in settings.FIELDS:
                continue
            v = str(v or "").strip()
            if settings.FIELDS[k][1] and v in ("", "__clear__"):
                continue  # 비밀값은 비우면 기존 유지
            os.environ[k] = v
        return {"ok": True, "message": ai.test_connection()}
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@app.post("/api/ai/chat")
def ai_chat(body: dict):
    return ai.chat(body.get("messages") or [], int(body.get("turn") or 0))


@app.get("/readme")
def readme():
    """사용 안내(README)를 브라우저에서 읽을 수 있게 제공."""
    from fastapi.responses import HTMLResponse
    import html as _html
    md = (Path(__file__).resolve().parent / "README.md").read_text(encoding="utf-8")
    body = _html.escape(md)
    return HTMLResponse(f"""<!doctype html><html lang=ko><head><meta charset=utf-8><title>사용 안내</title>
<style>body{{font-family:Pretendard,'Malgun Gothic',sans-serif;max-width:900px;margin:30px auto;padding:0 20px;line-height:1.6}}pre{{white-space:pre-wrap;font:inherit}}</style></head>
<body><p><a href="/">← 앱으로</a></p><pre id="md">{body}</pre>
<script>const el=document.getElementById('md');const h=location.hash.slice(1);if(h){{const i=el.textContent.indexOf('드라이브 OAuth');}}</script></body></html>""")


@app.post("/api/ai/extract")
async def ai_extract(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "파일이 너무 큽니다 (20MB 이하).")
    return ai.extract_receipt(data, file.content_type or "")


@app.post("/api/ai/suggest")
def ai_suggest(body: dict):
    return ai.suggest(body.get("rec") or {}, body.get("kind") or "exec")


@app.post("/api/ai/report")
def ai_report(body: dict):
    return {"report": ai.report(body.get("fund") or "", body.get("year") or "", body.get("month") or "", body.get("style") or "monthly")}


# ---------- 집행 단계 처리 / 증빙 ----------
@app.exception_handler(drive.DriveError)
async def _drive_err(_: Request, e: drive.DriveError):
    return JSONResponse({"detail": str(e)}, status_code=502)


@app.post("/api/exec/{row}/action")
def exec_action(row: int, body: dict):
    """body: {action: claim|complete|fix|unfix, expect: {...}, extra: {사유}} — fix 는 extra.사유 필수, fix·unfix 는 보완이력에 기록"""
    return store.exec_action(row, body.get("action") or "", body.get("expect"), body.get("extra") if isinstance(body.get("extra"), dict) else None)


@app.post("/api/deposit/{row}/action")
def deposit_action(row: int, body: dict):
    """body: {action: order|pay|receive|unorder|unpay|unreceive, expect: {...}} — 적립금 사용 행의 발주·결제·수령 단계"""
    return store.deposit_action(row, body.get("action") or "", body.get("expect"))


@app.get("/api/drive/status")
def drive_status():
    return drive.status()


@app.post("/api/drive/client-secret")
async def drive_client_secret(file: UploadFile = File(...)):
    drive.save_client_secret(await file.read())
    return drive.status()


@app.post("/api/drive/connect")
def drive_connect():
    return drive.connect()


@app.post("/api/drive/disconnect")
def drive_disconnect():
    return drive.disconnect()


@app.get("/api/evidence/thumb/{file_id:path}")
def evidence_thumb(file_id: str):
    """증빙 이미지 썸네일. 모의 모드는 로컬 파일, 드라이브는 thumbnailLink. 이미지 아님·오류는 204 (화면은 확장자 칩)."""
    from fastapi.responses import Response
    try:
        got = drive.thumbnail(file_id)
    except Exception:
        got = None
    if not got:
        return Response(status_code=204)
    data, mime = got
    return Response(content=data, media_type=mime, headers={"Cache-Control": "private, max-age=86400"})


@app.get("/api/evidence/{number}")
def evidence_list(number: str):
    """증빙 목록. 드라이브가 연결돼 있으면 파일의 현재 이름을 반영하고(바뀌면 장부도 수정) 없는 파일은 missing 으로 표시."""
    st = drive.status()
    items = store.evidence_sync(number, drive.file_meta) if (st.get("connected") or st.get("mock")) else store.evidence_for(number)
    for it in items:
        it["url"] = drive.file_url(it["드라이브파일ID"]) if it.get("드라이브파일ID") else ""
    return {"items": items, "drive": drive.status()}


@app.post("/api/evidence/{number}/entry")
def evidence_entry(number: str, body: dict):
    """파일 없이 증빙 항목(실물만)을 만든다. body: {증빙종류, 비고}. 증빙번호를 부여하고 드라이브는 건드리지 않음."""
    kind = body.get("증빙종류") if body.get("증빙종류") is not None else body.get("kind")
    note = body.get("비고") if body.get("비고") is not None else body.get("note")
    return store.evidence_entry(number, str(kind or ""), str(note or ""))


@app.post("/api/evidence/{number}")
async def evidence_upload(number: str, files: list[UploadFile] = File(...), kind: str = Form(""),
                          date: str = Form(""), note: str = Form(""), row: str = Form(""),
                          evno: str = Form("", alias="증빙번호")):
    """여러 파일을 드라이브에 올리고 증빙 시트에 기록. 집행(거래번호)은 증빙관리/YYYY/재원코드/거래번호,
    적립금(적립번호)은 증빙관리/YYYY/적립금/거래처명/적립번호 (사용자 결정 2026-10-19).
    row(증빙 시트 행) 또는 증빙번호를 주면 그 '실물만' 항목에 파일 1개를 첨부한다 (증빙번호·증빙종류·비고 유지, 이미 파일이 있으면 409)."""
    subj = store.evidence_subject(number)
    if subj is None:
        raise HTTPException(404, "집행 또는 적립금 행을 찾을 수 없습니다.")
    rec, is_dep = subj["rec"], subj["kind"] == "deposit"
    # 폴더·파일명 재료: 집행은 재원·적요·원인발생일, 적립금은 거래처·적요(없으면 구분)·일자
    base_date = rec["일자"] if is_dep else rec["원인발생일"]
    name_head = rec["거래처"] if is_dep else rec["재원"]
    summary = (rec["적요"] or rec["구분"]) if is_dep else (rec["적요"] or rec["거래처"] or "")
    target = None
    if row.strip() or evno.strip():
        if row.strip() and not row.strip().isdigit():
            raise HTTPException(400, "row 는 숫자여야 합니다.")
        target = next((e for e in store.evidence_for(number)
                       if (not row.strip() or e["_row"] == int(row)) and (not evno.strip() or e["증빙번호"] == evno.strip())), None)
        if target is None:
            raise HTTPException(404, "첨부할 증빙 항목을 찾을 수 없습니다. 새로고침 후 다시 시도하세요.")
        if target["has_file"]:
            raise HTTPException(409, f"증빙 {target['증빙번호']} 에는 이미 파일이 있습니다. 새 파일은 [업로드]로 따로 올리세요.")
        if len(files) != 1:
            raise HTTPException(400, "증빙 항목 하나에는 파일 1개만 첨부할 수 있습니다.")
        kind = target["증빙종류"] or kind
    if not kind.strip():
        raise HTTPException(400, "증빙종류를 입력하세요.")
    d = store._to_date(date) or base_date or dt.date.today().isoformat()
    if not store._valid_date(d):
        raise HTTPException(400, "날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).")
    yymmdd = d[2:4] + d[5:7] + d[8:10]
    year = (base_date or d)[:4]
    blobs = []
    for f in files:  # 크기 검사를 먼저 전부 수행 (중간 실패로 고아 파일이 생기지 않도록)
        data = await f.read()
        if len(data) > 25 * 1024 * 1024:
            raise HTTPException(413, f"{f.filename}: 25MB 를 넘습니다. 아무것도 올리지 않았습니다.")
        if not data:
            raise HTTPException(400, f"{f.filename}: 빈 파일입니다.")
        blobs.append((f, data))
    folder = drive.ensure_folder([year, "적립금", drive.safe_part(rec["거래처"]), number] if is_dep else [year, rec["재원"], number])
    existing = store.evidence_names(number)
    items, uploaded = [], []
    try:
        for f, data in blobs:
            ext = (f.filename or "").rsplit(".", 1)[-1] if "." in (f.filename or "") else ""
            name = drive.build_filename(name_head, summary, kind, rec["금액"], yymmdd, ext, existing)
            existing.append(name)
            up = drive.upload(folder, name, data, f.content_type or "")
            uploaded.append(up["id"])
            items.append({"거래번호": number, "증빙종류": kind.strip(), "파일명": name, "원본파일명": f.filename or "",
                          "드라이브파일ID": up["id"], "크기": up["size"], "업로드일": dt.date.today().isoformat(), "비고": note})
        if target is not None:  # 실물만 항목에 첨부: 파일 열만 채움 (증빙번호·종류·비고 유지)
            saved = [store.evidence_attach(target["_row"], {c: items[0][c] for c in store.EVID_FILE_COLS},
                                           {"거래번호": number, "증빙번호": target["증빙번호"]}, folder["url"])]
        else:
            saved = store.evidence_add(items, folder["url"])
    except Exception:
        for fid in uploaded:  # 이번 요청에서 올린 파일은 되돌림(휴지통)
            try:
                drive.trash(fid)
            except Exception:
                pass
        raise
    for it in saved:
        it["url"] = drive.file_url(it["드라이브파일ID"])
        it["has_file"] = True
    return {"items": saved, "folder": folder, "attached": target is not None}


@app.delete("/api/evidence/{row}")
def evidence_delete(row: int, body: dict | None = None):
    rec = store.evidence_delete(row, (body or {}).get("expect"))
    try:
        drive.trash(rec.get("드라이브파일ID") or "")
    except drive.DriveError as e:
        return {"ok": True, "warning": f"장부에서는 지웠지만 드라이브 휴지통 이동 실패: {e}"}
    return {"ok": True}


def _kind(kind: str):
    if kind not in store._SHEETS:
        raise HTTPException(404, "unknown kind")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    if not store.XLSX_PATH.exists():
        print(f"[오류] 장부 파일을 찾을 수 없습니다: {store.XLSX_PATH}\n"
              "  → 파일을 app 폴더의 상위 폴더에 두거나 .env 의 LEDGER_XLSX 에 경로를 지정하세요.")
        input("아무 키나 누르면 종료합니다...")
        raise SystemExit(1)
    try:
        _names = store.sheet_names()
        missing = [s for s in (store.SHEET_BUDGET, store.SHEET_EXEC, store.SHEET_REQ) if s not in _names]
        if missing:
            print(f"[오류] 장부에 필수 시트가 없습니다: {', '.join(missing)}\n  → 센터 지출장부 양식 파일인지 확인하세요.")
            input("아무 키나 누르면 종료합니다...")
            raise SystemExit(1)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[오류] 장부 파일을 열 수 없습니다: {e}")
        input("아무 키나 누르면 종료합니다...")
        raise SystemExit(1)
    try:
        before = set(_names)
        store.init_file()
        after = set(store.sheet_names())
        added = sorted(after - before)
        if added:
            print(f"[안내] 장부 구조를 보정했습니다: 시트 추가 {added}. 보정 전 파일은 app/backup 에 백업됨.")
    except store.LedgerLocked as e:
        print(f"[경고] {e} (구조 보정은 첫 저장 시 적용됩니다)")
    ai_state = f"사용 ({ai.provider()} / {ai.model()})" if ai.enabled() else "비활성 (우하단 설정에서 API 키 입력)"
    print(f"장부 파일: {store.XLSX_PATH}\nAI: {ai_state}\n브라우저: http://{HOST}:{PORT}  (종료: Ctrl+C)")
    if not os.environ.get("LEDGER_NO_BROWSER"):  # 테스트(tests/)·자동 실행에서는 브라우저를 열지 않음
        threading.Timer(1.0, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()
    import socket
    with socket.socket() as _s:
        if _s.connect_ex((HOST, PORT)) == 0:
            print(f"[안내] 이미 실행 중입니다 (포트 {PORT}). 브라우저 탭을 확인하세요. 이 창은 닫아도 됩니다.")
            if not os.environ.get("LEDGER_NO_BROWSER"):
                webbrowser.open(f"http://{HOST}:{PORT}")
            raise SystemExit(0)
    print("※ 이 콘솔 창을 닫으면 앱이 종료됩니다.")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
