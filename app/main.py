"""센터 회계대장 관리도구 - FastAPI 서버.

실행:  python main.py   (또는 run.bat)
"""
from __future__ import annotations

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

load_dotenv(Path(__file__).resolve().parent / ".env")

import ai  # noqa: E402
import drive  # noqa: E402
import settings  # noqa: E402
import store  # noqa: E402

HOST, PORT = "127.0.0.1", int(os.environ.get("LEDGER_PORT", "8791"))
STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="센터 회계대장 관리도구")


@app.exception_handler(store.LedgerLocked)
async def _locked(_: Request, e: store.LedgerLocked):
    return JSONResponse({"detail": str(e)}, status_code=423)


@app.exception_handler(store.NotFound)
async def _notfound(_: Request, e: store.NotFound):
    return JSONResponse({"detail": str(e)}, status_code=404)


@app.exception_handler(ai.AIError)
async def _ai_err(_: Request, e: ai.AIError):
    return JSONResponse({"detail": str(e)}, status_code=502)


@app.exception_handler(ValueError)
async def _bad(_: Request, e: ValueError):
    return JSONResponse({"detail": str(e)}, status_code=400)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/labor")
def labor_page():
    """인건비 화면: 같은 페이지, 주소로 모드 전환."""
    return FileResponse(STATIC / "index.html")


@app.post("/api/undo")
def undo_last(body: dict | None = None):
    """직전 저장을 되돌림 (삭제·확정 취소·상태 변경 토스트의 '되돌리기'). body.write_id 가 직전 쓰기와 다르면 거부."""
    return store.undo_last((body or {}).get("write_id"))


@app.get("/api/meta")
def meta():
    """가벼운 상태 확인: 파일 수정 시각 (다른 창·MCP 변경 감지용)."""
    import datetime as _dt
    return {"mtime": _dt.datetime.fromtimestamp(store.XLSX_PATH.stat().st_mtime).isoformat(timespec="seconds"), "write_id": store.last_write_id()}


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


def build_dashboard(data: dict) -> dict:
    items = list(store.BUDGET_ITEMS)
    for r in data["exec"] + data["req"]:  # 엑셀에서 직접 입력한 목록 밖 예산목도 집계에 포함
        if r["예산목"] and r["예산목"] not in items:
            items.append(r["예산목"])
    funds = [f["재원코드"] for f in data["funds"]]
    # 집행·품의에 쓰인 재원이 마스터에 없으면 함께 표시
    for r in data["exec"] + data["req"] + data["budget"]:
        if r["재원"] and r["재원"] not in funds:
            funds.append(r["재원"])

    budget = {f: {i: 0.0 for i in items} for f in funds}
    for r in data["budget"]:
        if r["재원"] in budget:
            for i in items:
                budget[r["재원"]][i] += r.get(i) or 0

    spent = {f: {i: 0.0 for i in items} for f in funds}
    monthly = defaultdict(lambda: defaultdict(float))  # fund -> 'YYYY-MM' -> amt
    vendors = defaultdict(float)
    unpaid = 0
    for r in data["exec"]:
        f, i = r["재원"], r["예산목"]
        if f in spent and i in items:
            spent[f][i] += r["금액"]
        if r["원인발생일"]:
            monthly[f][r["원인발생일"][:7]] += r["금액"]
        if r["거래처"]:
            vendors[r["거래처"]] += r["금액"]
        if not r["지출완료일"]:
            unpaid += 1

    pending = {f: {i: 0.0 for i in items} for f in funds}
    for r in data["req"]:
        if r["상태"] == "대기" and r["재원"] in pending and r["예산목"] in items:
            pending[r["재원"]][r["예산목"]] += r["금액"]

    table = []
    for f in funds:
        for i in items:
            b, s, p = budget[f][i], spent[f][i], pending[f][i]
            if b == 0 and s == 0 and p == 0:
                continue
            table.append({"재원": f, "예산목": i, "예산현액": b, "집행액": s, "잔액": b - s,
                          "집행률": (s / b) if b else None, "품의대기": p, "가용잔액": b - s - p})
    # 태그 집계: 집행내역(적립 선결제 건 제외) + 적립금 사용
    linked = {r["연결거래번호"] for r in data["deposit"] if r.get("연결거래번호")}
    tag_rows = [(r["태그"], r["원인발생일"], r["금액"]) for r in data["exec"] if r["거래번호"] not in linked]
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
        "tag_table": sorted(tag_table.values(), key=lambda e: (e["분류"], e["태그"])),
        "monthly": {f: dict(sorted(m.items())) for f, m in monthly.items()},
        "vendors": sorted(vendors.items(), key=lambda x: -x[1])[:15],
        "unpaid_count": unpaid,
    }


@app.post("/api/{kind}")
def create(kind: str, rec: dict):
    _kind(kind)
    return store.create(kind, rec)


@app.put("/api/{kind}/{row}")
def update(kind: str, row: int, body: dict):
    """body: 레코드 자체, 또는 {"rec": {...}, "expect": {식별열: 값}} (expect 는 행 밀림 감지용)."""
    _kind(kind)
    # 신형: {"rec": {...}, "expect": {...}} / 구형(예전 화면 캐시): 레코드 자체
    rec, expect = (body.get("rec"), body.get("expect")) if isinstance(body.get("rec"), dict) else (body, None)
    return store.update(kind, row, rec, expect)


@app.delete("/api/{kind}/{row}")
def delete(kind: str, row: int, body: dict | None = None):
    if kind == "evidence":  # 경로 매칭 순서상 여기로 먼저 들어오므로 전용 처리(드라이브 휴지통 이동)로 위임
        return evidence_delete(row, body)
    _kind(kind)
    body = body or {}
    store.delete(kind, row, body.get("expect"), bool(body.get("cascade")))
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
    return {"values": vals, "status": {"enabled": ai.enabled(), "model": ai.model(), "provider": ai.provider()}}


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
    """body: {action: claim|complete|fix|unfix, expect: {...}}"""
    return store.exec_action(row, body.get("action") or "", body.get("expect"))


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


@app.get("/api/evidence/{number}")
def evidence_list(number: str):
    items = store.evidence_for(number)
    for it in items:
        it["url"] = drive.file_url(it["드라이브파일ID"]) if it.get("드라이브파일ID") else ""
    return {"items": items, "drive": drive.status()}


@app.post("/api/evidence/{number}")
async def evidence_upload(number: str, files: list[UploadFile] = File(...), kind: str = Form(""),
                          date: str = Form(""), note: str = Form("")):
    """여러 파일을 드라이브 증빙관리/YYYY/재원코드/거래번호 에 올리고 증빙 시트에 기록."""
    rec = next((r for r in store.read_all()["exec"] if r["거래번호"] == number), None)
    if rec is None:
        raise HTTPException(404, "집행 행을 찾을 수 없습니다.")
    if not kind.strip():
        raise HTTPException(400, "증빙종류를 입력하세요.")
    d = store._to_date(date) or rec["원인발생일"] or dt.date.today().isoformat()
    if not store._valid_date(d):
        raise HTTPException(400, "날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).")
    yymmdd = d[2:4] + d[5:7] + d[8:10]
    year = (rec["원인발생일"] or d)[:4]
    blobs = []
    for f in files:  # 크기 검사를 먼저 전부 수행 (중간 실패로 고아 파일이 생기지 않도록)
        data = await f.read()
        if len(data) > 25 * 1024 * 1024:
            raise HTTPException(413, f"{f.filename}: 25MB 를 넘습니다. 아무것도 올리지 않았습니다.")
        if not data:
            raise HTTPException(400, f"{f.filename}: 빈 파일입니다.")
        blobs.append((f, data))
    folder = drive.ensure_folder([year, rec["재원"], number])
    existing = store.evidence_names(number)
    items, uploaded = [], []
    try:
        for f, data in blobs:
            ext = (f.filename or "").rsplit(".", 1)[-1] if "." in (f.filename or "") else ""
            name = drive.build_filename(rec["재원"], rec["적요"] or rec["거래처"] or "", kind, rec["금액"], yymmdd, ext, existing)
            existing.append(name)
            up = drive.upload(folder, name, data, f.content_type or "")
            uploaded.append(up["id"])
            items.append({"거래번호": number, "증빙종류": kind.strip(), "파일명": name, "원본파일명": f.filename or "",
                          "드라이브파일ID": up["id"], "크기": up["size"], "업로드일": dt.date.today().isoformat(), "비고": note})
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
    return {"items": saved, "folder": folder}


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
        import openpyxl as _ox
        _names = _ox.load_workbook(store.XLSX_PATH, read_only=True).sheetnames
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
        after = set(_ox.load_workbook(store.XLSX_PATH, read_only=True).sheetnames)
        added = sorted(after - before)
        if added:
            print(f"[안내] 장부 구조를 보정했습니다: 시트 추가 {added}. 보정 전 파일은 app/backup 에 백업됨.")
    except store.LedgerLocked as e:
        print(f"[경고] {e} (구조 보정은 첫 저장 시 적용됩니다)")
    ai_state = f"사용 ({ai.provider()} / {ai.model()})" if ai.enabled() else "비활성 (우하단 설정에서 API 키 입력)"
    print(f"장부 파일: {store.XLSX_PATH}\nAI: {ai_state}\n브라우저: http://{HOST}:{PORT}  (종료: Ctrl+C)")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()
    import socket
    with socket.socket() as _s:
        if _s.connect_ex((HOST, PORT)) == 0:
            print(f"[안내] 이미 실행 중입니다 (포트 {PORT}). 브라우저 탭을 확인하세요. 이 창은 닫아도 됩니다.")
            webbrowser.open(f"http://{HOST}:{PORT}")
            raise SystemExit(0)
    print("※ 이 콘솔 창을 닫으면 앱이 종료됩니다.")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
