"""ref/소모품 구매관리대장 (1).xlsx → 장부 들여오기 (2026-10-19, 사용자 결정에 따른 매핑).

    python -I docs/import_소모품대장/import.py --src "ref/소모품 구매관리대장 (1).xlsx" --dry-run
    LEDGER_XLSX=<장부> python -I docs/import_소모품대장/import.py --src ... --apply

대상 장부는 환경변수 LEDGER_XLSX (app/store.py 규칙과 같음). --apply 없이는 아무것도 쓰지 않는다.
앱의 저장 함수(store.create / request_action / order_create / update)를 그대로 써서 번호 부여·검증·백업이 앱과 같다.

매핑:
- 구입신청 → 신청(소모품, 구매처 알파몰). 신청번호는 앱이 새로 부여(R-YYYY-NNN), 원래 16자리 번호는 비고에.
  반려 → 반려(반려사유), 그 밖(승인·완료·주문) → 승인(결재인·결재일, 결재일 없으면 신청일). 완료 여부는 주문 배송일로 앱이 계산.
- 주문목록 사용 → 주문(거래처 알파몰, 적립금사용 Y) + 앱이 만드는 적립금 사용 행. 배송일은 원본에 있을 때만.
- 주문목록 적립 → 적립금 적립 행 (집행 연결 없음). 드라이브 링크·증빙번호는 비고에.
- 주문목록 즉시 + 현장구매 → 적립금 사용 행 (주문 행 없음, 발주·결제·수령 = 구매일).
- 쿠팡 주문번호 신청 → 주문 행 없이 비고에 번호만.
- 예시 데이터('(알파몰의 품목 이름 복사)', 현장구매 '가나다') 제외.
"""
import argparse
import collections
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(os.path.dirname(os.path.dirname(HERE)), "app")
sys.path.insert(0, APP)
os.environ.setdefault("IMPORT_CWD", os.getcwd())  # --src 상대 경로의 기준 (아래 chdir 전)
os.chdir(APP)  # store 가 app/.env 등을 상대 경로로 찾는다

import openpyxl  # noqa: E402

for _st in (sys.stdout, sys.stderr):  # cp949 콘솔에서 한글·기호가 깨지지 않게
    try:
        _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VENDOR, CODE = "알파", "알파"  # 사용자: 장부의 거래처 이름은 "알파"(알파미금역점)
EXAMPLE_ITEMS = {"(알파몰의 품목 이름 복사)", "가나다"}


def d(v):
    """날짜 셀 → YYYY-MM-DD (datetime·문자열 모두). 비면 ''."""
    if v in (None, ""):
        return ""
    if isinstance(v, (dt.date, dt.datetime)):
        return v.strftime("%Y-%m-%d")
    return str(v)[:10]


def n(v):
    return int(float(v)) if v not in (None, "") else 0


def s(v):
    return "" if v is None else str(v).strip()


def read_source(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    def rows(name):
        ws = wb[name]
        it = ws.iter_rows(values_only=True)
        head = [s(h) for h in next(it)]
        out = []
        for r in it:
            rec = {h: (r[i] if i < len(r) else None) for i, h in enumerate(head) if h}  # 짧은 행도 모든 열 키를 가진다
            out.append(rec)
        return out
    req = [r for r in rows("구입신청") if s(r.get("신청번호")) and s(r.get("품목")) not in EXAMPLE_ITEMS]
    orders = [r for r in rows("주문목록") if s(r.get("구분"))]
    onsite = [r for r in rows("현장구매") if s(r.get("품목")) and s(r.get("품목")) not in EXAMPLE_ITEMS]
    wb.close()
    return req, orders, onsite


def plan(req, orders, onsite):
    """원본 → 앱 호출 계획. 쓰기 없이 계산만."""
    p = {"requests": [], "approve": [], "reject": [], "orders": [], "deposits": []}
    order_nos = {s(o["주문번호"]) for o in orders if s(o["구분"]) == "사용"}
    for r in sorted(req, key=lambda x: (d(x["신청일"]), s(x["신청번호"]))):
        no = s(r["주문번호"])
        note = f"구 신청번호 {s(r['신청번호'])}"
        if no and no not in order_nos:
            note += f" · 주문 {no}"  # 쿠팡 등 알파몰 주문이 아닌 것: 주문 행 없이 비고에
        rec = {"구분": "소모품", "신청인": s(r["신청인"]), "신청일": d(r["신청일"]), "품목": s(r["품목"]),
               "단가": n(r["단가"]), "수량": n(r["수량"]) or 1, "사유": s(r["사유"]), "온라인코드": s(r["온라인코드"]),
               "상품코드": s(r["상품코드"]), "구매처": VENDOR, "비고": note}
        if not rec["온라인코드"] and not rec["상품코드"]:
            # 알파몰 코드가 없는 건(쿠팡 등 다른 곳 구매) → '기타' 신청. 품목 안의 주소는 상품링크로
            import re
            m = re.search(r"https?://\S+", rec["품목"])
            # 서버가 기타 행의 상품링크는 비우므로 링크는 비고에 둔다
            rec.update({"구분": "기타", "구매처": "", "품목": re.sub(r"\s*\(?https?://\S+\)?", "", rec["품목"]).strip(),
                        "비고": rec["비고"] + (f" · 링크 {m[0].rstrip(')')}" if m else "")})
        rec["금액"] = rec["단가"] * rec["수량"]
        st = s(r["상태"])
        act = ("reject", {"결재인": s(r["결재인"]) or "담당자", "결재일": d(r["결재일"]) or rec["신청일"], "사유": s(r["반려사유"]) or "반려 (원본 사유 없음)"}) if st == "반려" \
            else ("approve", {"결재인": s(r["결재인"]) or "담당자", "결재일": d(r["결재일"]) or rec["신청일"]})
        grouped = no in order_nos and st != "반려"  # 반려 건은 주문에 묶지 않는다 (원본에 주문번호가 남아 있어도)
        if no in order_nos and st == "반려":
            rec["비고"] += f" · 원본 주문번호 {no} (반려 건이라 주문에 묶지 않음)"
        p["requests"].append({"rec": rec, "action": act, "order": no if grouped else ""})
    for o in sorted(orders, key=lambda x: d(x["주문일"])):
        kind, no = s(o["구분"]), s(o["주문번호"])
        link = s(o["링크"]); evno = s(o["증빙번호"])
        memo = " · ".join(x for x in [s(o["비고"]), f"증빙번호 {evno}" if evno else "", f"증빙 {link}" if link else ""] if x)
        if kind == "적립":
            p["deposits"].append({"일자": d(o["주문일"]), "거래처": VENDOR, "구분": "적립", "금액": n(o["결제금액"]) or n(o["주문금액"]), "적요": s(o["비고"]) or "적립금 적립", "비고": memo})
        elif kind == "사용":
            p["orders"].append({"주문번호": no, "주문일": d(o["주문일"]), "배송일": d(o["배송일"]), "결제금액": n(o["결제금액"]), "비고": memo})
        elif kind == "즉시":
            src = next((x for x in onsite if n(x["금액"]) == (n(o["결제금액"]) or n(o["주문금액"]))), None)
            item = s(src["품목"]) if src else "현장구매"
            day = d(o["주문일"]) or (d(src["구매일"]) if src else "")
            p["deposits"].append({"일자": day, "거래처": VENDOR, "구분": "사용", "금액": n(o["결제금액"]) or n(o["주문금액"]), "적요": f"현장구매 {item}",
                                  "사용자": s(src["구매자"]) if src else "", "증빙번호": no, "발주일": day, "결제일": day, "수령일": d(src["배송일"]) if src and d(src["배송일"]) else day, "비고": memo})
    return p


def show(p):
    print(f"신청 {len(p['requests'])}건 (승인 {sum(1 for r in p['requests'] if r['action'][0] == 'approve')} · 반려 {sum(1 for r in p['requests'] if r['action'][0] == 'reject')})")
    by = collections.Counter(r["order"] for r in p["requests"])
    for o in p["orders"]:
        print(f"  주문 {o['주문번호']} {o['주문일']} 결제 {o['결제금액']:,} 배송일 {o['배송일'] or '-'} ← 신청 {by.get(o['주문번호'], 0)}건")
    print(f"  주문 없음 {by.get('', 0)}건")
    for x in p["deposits"]:
        print(f"  적립금 {x['구분']} {x['일자']} {x['금액']:,} {x['적요']}")


def apply(p):
    import store
    print("장부:", store.XLSX_PATH)
    vendors = store.read_all()["vendor"]
    same_code = next((v for v in vendors if str(v["코드"]).strip().casefold() == CODE.casefold()), None)
    if same_code and same_code["거래처명"] != VENDOR:
        # 같은 코드로 다른 이름(예: 알파미금역점)이 등록돼 있으면 이름을 VENDOR 로 맞춘다 (사용자 결정 2026-10-19: 거래처 이름은 '알파')
        memo = " · ".join(x for x in [str(same_code.get("비고") or ""), f"이전 이름 {same_code['거래처명']}"] if x)
        store.update("vendor", same_code["_row"], {"거래처명": VENDOR, "코드": CODE, "비고": memo})
        print(f"  거래처 이름 수정: {same_code['거래처명']} → {VENDOR}")
    elif not any(v["거래처명"] == VENDOR for v in vendors):
        store.create("vendor", {"거래처명": VENDOR, "코드": CODE, "비고": "소모품 대장 들여오기"})
    created = {}  # 주문번호 → [신청 행]
    for item in p["requests"]:
        rec = store.create("request", item["rec"])
        act, extra = item["action"]
        store.request_action(rec["_row"], act, extra)
        created.setdefault(item["order"], []).append(rec["_row"])
    for x in [x for x in p["deposits"] if x["구분"] == "적립"]:
        store.create("deposit", x)
    # 주문(→ 적립금 사용 행)과 현장구매 사용 행을 날짜 순으로 처리해 적립번호가 시간 순이 되게
    events = [("order", o["주문일"], o) for o in p["orders"]] + [("deposit", x["일자"], x) for x in p["deposits"] if x["구분"] == "사용"]
    for kind, _, o in sorted(events, key=lambda e: e[1]):
        if kind == "deposit":
            store.create("deposit", o); continue
        rows = created.get(o["주문번호"], [])
        if not rows:
            print("  [건너뜀] 신청이 없는 주문", o["주문번호"]); continue
        res = store.order_create(rows, {"주문일": o["주문일"], "결제금액": o["결제금액"], "적립금사용": "Y", "비고": o["비고"]})
        got = res["order"]["주문번호"] if isinstance(res, dict) and "order" in res else None
        for w in (res.get("warnings") or []) if isinstance(res, dict) else []:
            print("  [경고]", w)
        if got and got != o["주문번호"]:
            print(f"  [주의] 주문번호가 원본과 다름: {o['주문번호']} → {got}")
        no = got or o["주문번호"]
        if o["배송일"]:
            orow = next(r for r in store.read_all()["order"] if r["주문번호"] == no)
            store.update("order", orow["_row"], {"배송일": o["배송일"]})
        dep = next((r for r in store.read_all()["deposit"] if r.get("증빙번호") == no and r["구분"] == "사용"), None)
        if dep:
            upd = {k: v for k, v in dep.items() if not k.startswith("_")}
            upd.update({"비고": o["비고"], "결제일": o["주문일"], "수령일": o["배송일"] or ""})
            store.update("deposit", dep["_row"], upd)
    # 이전에 "알파몰"로 적힌 구매처·거래처는 "알파"로 (사용자 결정 2026-10-19). 번호·잠금과 무관한 이름 칸만 바꾼다
    import openpyxl as _ox
    wb = _ox.load_workbook(store.XLSX_PATH)
    n_fix = 0
    for sheet, col in ((store.SHEET_RQ, "구매처"), (store.SHEET_ORDER, "거래처"), (store.SHEET_DEP, "거래처")):
        ws = wb[sheet]; heads = store._headers(ws)
        if col not in heads:
            continue
        ci = heads.index(col) + 1
        for r in range(2, ws.max_row + 1):
            if str(ws.cell(r, ci).value or "").strip() == "알파몰":
                ws.cell(r, ci).value = VENDOR; n_fix += 1
    if n_fix:
        wb.save(store.XLSX_PATH); print(f"  '알파몰' → '{VENDOR}' 이름 수정 {n_fix}칸")
    wb.close()
    print("완료")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--apply", action="store_true", help="실제로 쓴다 (없으면 미리보기)")
    a = ap.parse_args()
    src = os.path.abspath(os.path.join(os.environ.get("IMPORT_CWD") or os.getcwd(), a.src)) if not os.path.isabs(a.src) else a.src
    p = plan(*read_source(src))
    show(p)
    if a.apply:
        apply(p)
    else:
        print("(미리보기 — --apply 를 주면 LEDGER_XLSX 장부에 씁니다)")
