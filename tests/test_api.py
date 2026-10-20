"""신청 API 규칙 검사 (학회·기타). QA 장부 복사본에 대해 실행한다: python -I tests/test_api.py"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import Server, Check  # noqa: E402


def main() -> int:
    ck = Check()
    with Server("api") as sv:
        # ---- 시트 이름 확인(시작 검사)이 장부 파일 핸들을 남기면 저장(os.replace)이 막힌다 ----
        # GC 시점에 따라 우연히 풀리므로 gc 를 끈 별도 프로세스에서 확인
        import subprocess
        xlsx = os.path.join(sv.dir, "ledger.xlsx")
        probe = ("import gc, os, shutil, store; gc.disable(); store.sheet_names(); p = str(store.XLSX_PATH); "
                 "shutil.copyfile(p, p + '.swap'); os.replace(p + '.swap', p)")
        pr = subprocess.run([sys.executable, "-c", probe], cwd=os.path.join(os.path.dirname(sv.dir), "..", "..", "app"),
                            env=dict(os.environ, LEDGER_XLSX=xlsx), capture_output=True, text=True, encoding="utf-8")
        ck("시트 이름 확인 후 장부 파일 교체 가능 (핸들 미점유)", pr.returncode == 0, pr.stderr[-300:])

        # ---- 학회: 계산 결과가 있으면 금액 = out.합계 ----
        calc = {"v": 2, "in": {"fx": 1380}, "out": {"합계": 1500000}, "합계": 1500000}
        base = {"구분": "학회", "신청인": "검사", "품목": "검사 학회", "상세": {"국내외": "국외", "시작일": "2026-11-10", "종료일": "2026-11-12", **calc}}
        s, r = sv.call("POST", "/api/request", {**base, "금액": 999})
        ck("학회: 금액≠합계 → 합계로 강제", s == 200 and r.get("금액") == 1500000, (s, r))
        conf_row = r.get("_row")
        s, r = sv.call("POST", "/api/request", {**base, "상세": {**base["상세"], "합계": 5}})
        ck("학회: 상세.합계 ≠ out.합계 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/request", {**base, "상세": {"국내외": "국내", "시작일": "2026-11-12", "종료일": "2026-11-01"}, "금액": 1})
        ck("학회: 종료일 < 시작일 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/request", {**base, "상세": "[1,2]", "금액": 1})
        ck("학회: 상세 배열 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/request", {**base, "상세": {}, "금액": 1234.5})
        ck("학회: 소수 금액 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/request", {**base, "상세": {}, "금액": 7, "단가": 10000, "수량": 3, "규격": "x"})
        ck("학회: 단가·수량·규격 정규화", s == 200 and r.get("단가") == "" and r.get("수량") == 1 and r.get("규격") == "" and r.get("금액") == 7, (s, r))
        s, r = sv.call("POST", "/api/request", {**base, "상세": {}, "금액": 0})
        zero_row = r.get("_row")
        s, r = sv.call("POST", f"/api/request/{zero_row}/action", {"action": "approve"})
        ck("학회: 0원 승인 차단", s == 400, (s, r))
        s, r = sv.call("POST", f"/api/request/{conf_row}/action", {"action": "approve"})
        ck("학회: 승인", s == 200, (s, r))
        rec = sv.rec("request", conf_row)
        import json
        d = json.loads(rec["상세"]); d["장소"] = "런던"; rec["상세"] = json.dumps(d, ensure_ascii=False)
        s, r = sv.call("PUT", f"/api/request/{conf_row}", {"rec": rec})
        ck("학회: 상세만 변경 → 재결재", s == 200 and r.get("reapproval") is True, (s, r))
        s, r = sv.call("POST", f"/api/request/{conf_row}/action", {"action": "approve"})
        rec = sv.rec("request", conf_row); rec["비고"] = "메모"
        s, r = sv.call("PUT", f"/api/request/{conf_row}", {"rec": rec})
        ck("학회: 비고만 변경 → 승인 유지", s == 200 and not r.get("reapproval"), (s, r))

        # ---- 신청번호: 구분 코드 (E 장비 / S 소모품 / C 학회 / Z 기타), 이전 R- 번호는 보정 때 바뀜 ----
        import re as _re
        s, r = sv.call("GET", "/api/all")
        ck("신청번호 보정: R- 없음, 모두 코드 모양", r["request"] and all(_re.fullmatch(r"[ESCZ]-\d{4}-\d{3}", x["신청번호"]) for x in r["request"]), [x["신청번호"] for x in r["request"]][:6])
        nums = {x["신청번호"] for x in r["request"]}
        ck("주문 신청번호목록 참조가 새 번호로", all(all(n.strip() in nums for n in (o["신청번호목록"] or "").split(",") if n.strip()) for o in r["order"]), [o["신청번호목록"] for o in r["order"]][:3])
        ck("학회 신청번호 = C-", sv.rec("request", conf_row)["신청번호"].startswith("C-2026-"), sv.rec("request", conf_row)["신청번호"])
        s, r = sv.call("POST", "/api/request", {"구분": "장비", "신청인": "검사", "품목": "번호 검사", "단가": 1000, "수량": 1})
        ck("장비 신청번호 = E-", s == 200 and r["신청번호"].startswith("E-2026-"), (s, r.get("신청번호")))
        s, r2 = sv.call("POST", "/api/request", {"구분": "소모품", "신청인": "검사", "품목": "번호 검사", "단가": 1000, "수량": 1, "온라인코드": "1234567", "구매처": "가상문구A"})
        ck("소모품 신청번호 = S-", s == 200 and r2["신청번호"].startswith("S-2026-"), (s, r2.get("신청번호")))
        # ---- 기타·장비 공통 ----
        s, r = sv.call("POST", "/api/request", {"구분": "기타", "신청인": "검사", "품목": "구독", "규격": "월 3석", "단가": 90000, "수량": 12, "온라인코드": "X1", "상품코드": "P1", "상품링크": "https://x.y"})
        ck("기타: 쇼핑몰 코드 비움·금액 = 단가×수량", s == 200 and r.get("온라인코드") == "" and r.get("상품코드") == "" and r.get("상품링크") == "" and r.get("금액") == 1080000, (s, r))
        etc_row = r.get("_row")
        s, r = sv.call("POST", "/api/request", {"구분": "기타", "신청인": "검사", "품목": "x", "단가": 1234.5, "수량": 3})
        ck("기타: 단가 소수 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/request", {"구분": "기타", "신청인": "검사", "품목": "x", "단가": 100000, "수량": 2, "부가세구분": "Y", "부가세액": 10000.7})
        ck("기타: 부가세액 소수 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/request", {"구분": "기타", "신청인": "검사", "품목": "x", "단가": 100000, "수량": 2, "부가세구분": "Y"})
        ck("기타: 부가세 Y 기본 10%", s == 200 and r.get("부가세액") == 20000 and r.get("금액") == 220000, (s, r))
        s, r = sv.call("POST", f"/api/request/{etc_row}/action", {"action": "approve"})
        rec = sv.rec("request", etc_row); rec["구분"] = "장비"
        s, r = sv.call("PUT", f"/api/request/{etc_row}", {"rec": rec})
        ck("구분 변경 → 재결재", s == 200 and r.get("reapproval") is True, (s, r))
        s, r = sv.call("POST", "/api/request", {"구분": "장비", "신청인": "검사", "품목": "x", "단가": 1000, "수량": 1, "상세": {"합계": 3}})
        ck("장비: 상세는 비움", s == 200 and r.get("상세") == "", (s, r))
        # 시스템 열은 API 로 덮어쓸 수 없다
        s, r = sv.call("POST", "/api/request", {"구분": "장비", "신청인": "검사", "품목": "x", "단가": 1000, "수량": 1, "상태": "승인", "결재인": "해커"})
        ck("시스템 열(상태·결재인) 주입 무시", s == 200 and r.get("상태") == "신청" and not r.get("결재인"), (s, r))
        # ---- 재원 종류 · 공금 ----
        s, r = sv.call("GET", "/api/all")
        ck("기존 재원 종류 = 국책", all((f.get("종류") or "") == "국책" for f in r["funds"]), [f.get("종류") for f in r["funds"]])
        s, r = sv.call("POST", "/api/funds", {"재원코드": "GG01", "과제명": "센터 공금", "종류": "공금"})
        ck("공금 재원 생성", s == 200 and r.get("종류") == "공금", (s, r))
        s, r = sv.call("POST", "/api/funds", {"재원코드": "NN01", "과제명": "종류 없음"})
        ck("종류 없으면 국책", s == 200 and r.get("종류") == "국책", (s, r))
        s, r = sv.call("POST", "/api/funds", {"재원코드": "XX01", "과제명": "x", "종류": "엉뚱"})
        ck("목록 밖 종류 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/budget", {"재원": "GG01", "변경회차": "당초", "신청일자": "2026-01-01", "연구활동비": 100})
        ck("공금에 예산목 예산 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/budget", {"재원": "GG01", "변경회차": "당초", "신청일자": "2026-01-01"})
        ck("공금 입금 없음 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/budget", {"재원": "GG01", "변경회차": "당초", "입금": 500000})
        ck("예산변동: 신청일자 없음 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/budget", {"재원": "GG01", "변경회차": "당초", "신청일자": "2026-01-01", "입금": 500000})
        ck("공금 입금 저장", s == 200 and r.get("입금") == 500000, (s, r))
        bud_row = r.get("_row")
        rec = sv.rec("budget", bud_row); rec["신청일자"] = ""
        s, r = sv.call("PUT", f"/api/budget/{bud_row}", {"rec": rec})
        ck("예산변동 수정: 신청일자 비우기 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/budget", {"재원": "NN01", "변경회차": "당초", "신청일자": "2026-01-01", "입금": 1000})
        ck("국책에 입금 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/exec", {"재원": "GG01", "예산목": "연구활동비", "원인발생일": "2026-03-02", "거래처": "검사", "금액": 120000, "적요": "공금 지출", "지출완료일": "2026-03-02"})
        ck("공금 집행 (예산목 필수 그대로)", s == 200, (s, r))
        s, r = sv.call("POST", "/api/req", {"재원": "GG01", "예산목": "연구재료비", "원인발생일": "2026-03-03", "거래처": "검사", "금액": 20000, "적요": "대기 품의"})
        ck("공금 품의", s == 200, (s, r))
        s, r = sv.call("GET", "/api/all")
        row = next((x for x in r["dashboard"]["table"] if x["재원"] == "GG01"), None)
        ck("대시보드: 공금 잔액 한 줄 = 입금 − 집행 − 대기", row is not None and row["예산목"] == "(공금 잔액)" and row["예산현액"] == 500000 and row["집행액"] == 120000 and row["가용잔액"] == 360000, row)
        ck("대시보드: 공금은 예산목 줄 없음", sum(1 for x in r["dashboard"]["table"] if x["재원"] == "GG01") == 1)
        # ---- 잔액 미관리 재원 ----
        s, r = sv.call("POST", "/api/funds", {"재원코드": "SRC1", "과제명": "출처 전용", "잔액미관리": True})
        ck("잔액 미관리 재원 생성 (체크 true → Y)", s == 200 and r.get("잔액미관리") == "Y", (s, r))
        s, r = sv.call("POST", "/api/budget", {"재원": "SRC1", "변경회차": "당초", "신청일자": "2026-01-01", "연구활동비": 1000})
        ck("미관리 재원 예산변동 → 400", s == 400, (s, r))
        # ---- 빈 신청일자 보정: 구조 보정이 장부 연도의 1월 1일로 채운다 ----
        fill = ("import openpyxl, store; wb = openpyxl.load_workbook(store.XLSX_PATH); ws = wb[store.SHEET_BUDGET]; "
                "ci = store._headers(ws, store.BUDGET_HEAD_ROW).index('신청일자') + 1; ws.cell(store.BUDGET_HEAD_ROW + 1, ci).value = None; "
                "wb.save(store.XLSX_PATH); wb.close(); store.init_file(); "
                "rows = store.read_all()['budget']; print(rows[0]['신청일자']); assert rows[0]['신청일자'] == '2026-01-01', rows[0]")
        fill_dir = os.path.join(sv.dir, "fill"); os.makedirs(fill_dir, exist_ok=True)
        import shutil
        shutil.copyfile(os.path.join(sv.dir, "ledger.xlsx"), os.path.join(fill_dir, "ledger.xlsx"))
        pr = subprocess.run([sys.executable, "-c", fill], cwd=os.path.join(os.path.dirname(sv.dir), "..", "..", "app"),
                            env=dict(os.environ, LEDGER_XLSX=os.path.join(fill_dir, "ledger.xlsx")), capture_output=True, text=True, encoding="utf-8")
        ck("빈 신청일자 → 장부 연도 1월 1일로 보정", pr.returncode == 0, pr.stderr[-300:])
        s, r = sv.call("POST", "/api/exec", {"재원": "SRC1", "예산목": "연구활동비", "원인발생일": "2026-03-05", "거래처": "검사", "금액": 7000, "적요": "출처 전용 집행"})
        ck("미관리 재원 집행은 저장됨", s == 200, (s, r))
        s, r = sv.call("GET", "/api/all")
        ck("대시보드: 미관리 재원 줄·집계 제외 모두 없음", not any(x["재원"] == "SRC1" for x in r["dashboard"]["table"]) and not any(x["재원"] == "SRC1" for x in r["dashboard"]["excluded"]["exec"]))
        # ---- 적립금 증빙: 적립번호 자동 부여, 증빙은 집행과 같은 API 로 ----
        import re
        from urllib.parse import quote
        s, r = sv.call("GET", "/api/all")
        ck("적립금: 기존 행 모두 적립번호 보정 (코드-구분-연도-NNN)", r["deposit"] and all(re.fullmatch(r"[0-9A-Za-z가-힣]{2,6}-(적립|사용)-\d{4}-\d{3}", str(x.get("적립번호") or "")) for x in r["deposit"]), [x.get("적립번호") for x in r["deposit"]][:5])
        codes = {v["거래처명"]: v["코드"] for v in r["vendor"]}
        ck("거래처 자동 등록: 가상문구A/B 코드가 서로 다름", codes.get("가상문구A") and codes.get("가상문구B") and codes["가상문구A"] != codes["가상문구B"], codes)
        # ---- 거래처 마스터 ----
        s, r = sv.call("POST", "/api/vendor", {"거래처명": "검사/상사", "코드": "검사"})
        ck("거래처 등록", s == 200 and r.get("코드") == "검사", (s, r))
        ven_row = r.get("_row")
        s, r = sv.call("POST", "/api/vendor", {"거래처명": "다른상사", "코드": "검사"})
        ck("코드 중복 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/vendor", {"거래처명": "또다른", "코드": "a-b"})
        ck("코드에 '-' → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/vendor", {"거래처명": "또다른", "코드": "x"})
        ck("코드 1자 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/deposit", {"일자": "2026-03-07", "거래처": "검사/상사", "구분": "사용", "금액": 12000, "적요": "증빙 검사"})
        dep_no, dep_row = r.get("적립번호"), r.get("_row")
        ck("적립금 추가: 코드-사용-YYYY-NNN 부여", s == 200 and re.fullmatch(r"검사-사용-2026-\d{3}", str(dep_no)), (s, r))
        s, r = sv.call("POST", "/api/deposit", {"일자": "2026-03-07", "거래처": "검사/상사", "구분": "적립", "금액": 100000})
        ck("적립 행 번호는 구분이 다르고 일련번호 따로", s == 200 and r.get("적립번호") == "검사-적립-2026-001", (s, r))
        s, r = sv.call("POST", "/api/deposit", {"일자": "2026-03-07", "거래처": "새거래처Z", "구분": "사용", "금액": 500})
        ck("미등록 거래처: 자동 코드 등록 + 안내 플래그", s == 200 and r.get("적립번호", "").startswith("새거-사용-2026-") and r.get("_vendor_registered") == "새거", (s, r))
        rec = sv.rec("vendor", ven_row); rec["코드"] = "검상"
        s, r = sv.call("PUT", f"/api/vendor/{ven_row}", {"rec": rec})
        ck("번호에 쓰인 코드 변경 → 400", s == 400, (s, r))
        s, r = sv.call("DELETE", f"/api/vendor/{ven_row}", {})
        ck("적립금에 쓰인 거래처 삭제 → 400", s == 400, (s, r))
        rec = sv.rec("deposit", dep_row); rec["적립번호"] = "적립-2026-999"; rec["비고"] = "번호 바꾸기 시도"
        s, r = sv.call("PUT", f"/api/deposit/{dep_row}", {"rec": rec})
        ck("적립금 수정: 적립번호는 불변", s == 200 and r.get("적립번호") == dep_no, (s, r))
        s, r = sv.call("POST", f"/api/evidence/{quote(dep_no)}/entry", {"증빙종류": "영수증", "비고": "실물"})
        ck("적립 증빙 항목(실물만) 추가", s == 200 and r.get("증빙번호") == f"{dep_no}-1", (s, r))
        s, r = sv.call("POST", f"/api/evidence/{quote('검사-사용-2099-001')}/entry", {"증빙종류": "영수증"})
        ck("없는 적립번호 → 404", s == 404, (s, r))
        import requests
        up = requests.post(f"{sv.base}/api/evidence/{quote(dep_no)}", data={"kind": "카드전표"}, files={"files": ("r.png", b"\x89PNG fake", "image/png")})
        upj = up.json()
        ck("적립 증빙 업로드: 증빙관리/연도/적립금/거래처/적립번호", up.status_code == 200 and upj["folder"]["id"] == f"증빙관리/2026/적립금/검사 상사/{dep_no}", (up.status_code, upj))
        ck("적립 증빙 파일명: 거래처_종류_금액_YYMMDD (적요 없음)", up.status_code == 200 and upj["items"][0]["파일명"] == "검사 상사_카드전표_12000_260307.png", upj.get("items"))
        s, r = sv.call("GET", f"/api/evidence/{quote(dep_no)}")
        ck("적립 증빙 목록 2건", s == 200 and len(r["items"]) == 2, (s, r))
        # ---- 드라이브 이름 변경·삭제 반영: 목록 조회 때 파일명을 맞추고 없는 파일은 missing ----
        fid = upj["items"][0]["드라이브파일ID"]
        sync = ("import store; r = store.evidence_sync(%r, lambda fid: {'name': 'renamed.png', 'trashed': False}); "
                "assert r['renamed'] == 1 and [x for x in r['items'] if x['드라이브파일ID'] == %r][0]['파일명'] == 'renamed.png', r; "
                "r2 = store.evidence_sync(%r, lambda fid: None); assert r2['removed'] == [%r] and not any(x.get('드라이브파일ID') for x in r2['items']), r2; "
                "left = store.evidence_for(%r); assert len(left) == 1 and not left[0]['파일명'], left") % (dep_no, fid, dep_no, upj["items"][0]["증빙번호"], dep_no)
        pr = subprocess.run([sys.executable, "-c", sync], cwd=os.path.join(os.path.dirname(sv.dir), "..", "..", "app"),
                            env=dict(os.environ, **sv.store_env, LEDGER_DRIVE_MOCK="1"), capture_output=True, text=True, encoding="utf-8")
        ck("드라이브 이름 변경 → 장부 파일명 갱신, 삭제(휴지통) → 증빙 행 삭제", pr.returncode == 0, pr.stderr[-300:])
        s, r = sv.call("POST", f"/api/evidence/{quote(dep_no)}/entry", {"증빙종류": "영수증"})
        ck("지운 증빙번호 재사용", s == 200 and r.get("증빙번호") == f"{dep_no}-2", (s, r))
        # 전체 동기화: 모의 드라이브에서 파일을 지우면 그 증빙 행이 사라진다
        up3 = requests.post(f"{sv.base}/api/evidence/{quote(dep_no)}", data={"kind": "거래명세서"}, files={"files": ("c.png", b"\x89PNG c", "image/png")}).json()
        mp = os.path.join(sv.dir, "mock", "증빙관리", "2026", "적립금", "검사 상사", dep_no, up3["items"][0]["파일명"])
        ck("동기화 준비: 모의 파일 존재", os.path.exists(mp), mp)
        os.remove(mp)
        s, r = sv.call("POST", "/api/evidence/sync-all")
        ck("드라이브 동기화: 지운 파일의 증빙 삭제", s == 200 and up3["items"][0]["증빙번호"] in r["removed"] and not r["errors"], (s, r))
        s, r = sv.call("DELETE", f"/api/deposit/{dep_row}", {})
        ck("증빙 있는 적립금 행 삭제 → 400", s == 400, (s, r))
        # ---- 옛 모양 적립번호(적립-YYYY-NNN) 보정: 새 모양으로 바꾸고 증빙 참조도 함께 ----
        fix2 = ("import openpyxl, store; wb = openpyxl.load_workbook(store.XLSX_PATH); ws = wb[store.SHEET_DEP]; "
                "h = store._headers(ws); ci = h.index(store.DEP_NO) + 1; old = ws.cell(2, ci).value; ws.cell(2, ci).value = '적립-2026-001'; "
                "we = wb[store.SHEET_EVID]; he = store._headers(we); r = we.max_row + 1; we.cell(r, he.index('거래번호') + 1).value = '적립-2026-001'; we.cell(r, he.index('증빙종류') + 1).value = '영수증'; "
                "wb.save(store.XLSX_PATH); wb.close(); store.init_file(); d = store.read_all(); new = next(x for x in d['deposit'] if x['_row'] == 2)[store.DEP_NO]; "
                "assert new != '적립-2026-001' and '-' in new, new; ev = [e for e in d['evidence'] if e['거래번호'] == new]; assert ev and not any(e['거래번호'] == '적립-2026-001' for e in d['evidence']), d['evidence'][-2:]")
        fix2_dir = os.path.join(sv.dir, "fix2"); os.makedirs(fix2_dir, exist_ok=True)
        shutil.copyfile(os.path.join(sv.dir, "ledger.xlsx"), os.path.join(fix2_dir, "ledger.xlsx"))
        pr = subprocess.run([sys.executable, "-c", fix2], cwd=os.path.join(os.path.dirname(sv.dir), "..", "..", "app"),
                            env=dict(os.environ, LEDGER_XLSX=os.path.join(fix2_dir, "ledger.xlsx")), capture_output=True, text=True, encoding="utf-8")
        ck("옛 적립번호 → 새 모양으로 바꾸고 증빙 참조 갱신", pr.returncode == 0, pr.stderr[-400:])
        # ---- 적립금 단계: 발주일/결제일/수령일 → 상태 (사용 행만) ----
        s, r = sv.call("POST", "/api/deposit", {"일자": "2026-03-09", "거래처": "검사상사", "구분": "사용", "금액": 3000, "적요": "단계 검사"})
        st_row = r.get("_row")
        ck("사용 추가: 발주일 기본값 = 일자, 상태 발주", s == 200 and r.get("발주일") == "2026-03-09" and r.get("상태") == "발주", (s, r))
        s, r = sv.call("POST", f"/api/deposit/{st_row}/action", {"action": "pay"})
        ck("결제 처리 → 결제일 오늘, 상태 결제", s == 200 and r.get("결제일") and r.get("상태") == "결제", (s, r))
        s, r = sv.call("POST", f"/api/deposit/{st_row}/action", {"action": "unpay"})
        ck("결제 취소 → 상태 발주", s == 200 and not r.get("결제일") and r.get("상태") == "발주", (s, r))
        s, r = sv.call("POST", f"/api/deposit/{st_row}/action", {"action": "receive"})
        ck("수령 처리 → 결제일도 채움, 상태 수령", s == 200 and r.get("결제일") and r.get("수령일") and r.get("상태") == "수령", (s, r))
        s, r = sv.call("POST", f"/api/deposit/{st_row}/action", {"action": "unpay"})
        ck("수령된 건의 결제 취소 → 400", s == 400, (s, r))
        rec = sv.rec("deposit", st_row); rec["발주일"] = ""
        s, r = sv.call("PUT", f"/api/deposit/{st_row}", {"rec": rec})
        ck("발주일 비우기(뒤 단계 있음) → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/deposit", {"일자": "2026-03-09", "거래처": "검사상사", "구분": "적립", "금액": 50000, "발주일": "2026-03-09"})
        dp_row = r.get("_row")
        ck("적립 행: 단계 날짜 비움, 상태 없음", s == 200 and not r.get("발주일") and not r.get("상태"), (s, r))
        s, r = sv.call("POST", f"/api/deposit/{dp_row}/action", {"action": "pay"})
        ck("적립 행 단계 처리 → 400", s == 400, (s, r))
        s, r = sv.call("GET", "/api/all")
        ck("기존 사용 행 보정: 발주일 = 일자", all(x.get("발주일") and x.get("상태") for x in r["deposit"] if x["구분"] == "사용"), [(x["일자"], x.get("발주일"), x.get("상태")) for x in r["deposit"] if x["구분"] == "사용"][:4])
        # ---- 원거래 수정 → 증빙 파일 이름 자동 변경 ----
        s, r = sv.call("POST", "/api/exec", {"재원": "QA01", "예산목": "연구활동비", "원인발생일": "2026-03-08", "거래처": "검사", "금액": 4000, "적요": "이름 검사"})
        rn_row, rn_no = r.get("_row"), r.get("거래번호")
        up2 = requests.post(f"{sv.base}/api/evidence/{quote(rn_no)}", data={"kind": "영수증"}, files={"files": ("a.png", b"\x89PNG x", "image/png")}).json()
        ck("집행 증빙 파일명: 재원_종류_금액_YYMMDD", up2["items"][0]["파일명"] == "QA01_영수증_4000_260308.png", up2.get("items"))
        rec = sv.rec("exec", rn_row); rec["금액"] = 4500; rec["적요"] = "이름 검사 (적요 변경)"
        s, r = sv.call("PUT", f"/api/exec/{rn_row}", {"rec": rec})
        s2, ev = sv.call("GET", f"/api/evidence/{quote(rn_no)}")
        ck("금액 수정 → 파일명 변경 + 드라이브(모의) 파일도 이동", s == 200 and r.get("_renamed") == 1 and ev["items"][0]["파일명"] == "QA01_영수증_4500_260308.png"
           and os.path.exists(os.path.join(sv.dir, "mock", "증빙관리", "2026", "QA01", rn_no, "QA01_영수증_4500_260308.png")), (s, r.get("_renamed"), ev.get("items")))
        # ---- 증빙 교체: 같은 증빙번호, 새 파일, 옛 파일은 휴지통 ----
        ev_row, old_id = ev["items"][0]["_row"], ev["items"][0]["드라이브파일ID"]
        dup = requests.post(f"{sv.base}/api/evidence/{quote(rn_no)}", data={"row": str(ev_row)}, files={"files": ("b.png", b"\x89PNG y", "image/png")})
        ck("파일 있는 항목에 첨부 → 409", dup.status_code == 409, dup.status_code)
        rp = requests.post(f"{sv.base}/api/evidence/{quote(rn_no)}", data={"row": str(ev_row), "replace": "1"}, files={"files": ("b.png", b"\x89PNG new", "image/png")}).json()
        s2, ev2 = sv.call("GET", f"/api/evidence/{quote(rn_no)}")
        it = ev2["items"][0]
        mock_path = os.path.join(sv.dir, "mock", "증빙관리", "2026", "QA01", rn_no, it["파일명"])
        ck("교체: 증빙번호 유지·새 파일·목록 1건", rp.get("replaced") is True and len(ev2["items"]) == 1 and it["증빙번호"] == ev["items"][0]["증빙번호"] and it["파일명"] == "QA01_영수증_4500_260308.png"
           and (it["드라이브파일ID"] != old_id or open(mock_path, "rb").read() == b"\x89PNG new"), (rp, ev2.get("items")))  # 모의 드라이브는 같은 경로 = 같은 id
        ck("교체: 옛 파일은 모의 휴지통으로 (같은 경로면 덮어씀)", old_id == it["드라이브파일ID"] or os.path.exists(os.path.join(sv.dir, "mock", "_trash", "QA01_영수증_4500_260308.png")), old_id)
        # ---- 증빙 복사: 다른 거래 폴더에 그 거래 기준 이름으로, 독립 항목 ----
        s, r = sv.call("POST", "/api/exec", {"재원": "QA02", "예산목": "연구활동비", "원인발생일": "2026-03-09", "거래처": "검사", "금액": 1200, "적요": "복사 대상"})
        cp_row, cp_no = r.get("_row"), r.get("거래번호")
        s, r = sv.call("POST", f"/api/evidence/{quote(rn_no)}/copy", {"row": ev_row, "targets": [cp_no, rn_no, "2026-없음-999"]})
        ck("복사: 대상 1건 성공, 같은 거래·없는 번호는 오류", s == 200 and len(r["copied"]) == 1 and r["copied"][0]["거래번호"] == cp_no and r["copied"][0]["파일명"] == "QA02_영수증_1200_260309.png" and len(r["errors"]) == 2, (s, r))
        ck("복사: 대상 폴더에 파일", os.path.exists(os.path.join(sv.dir, "mock", "증빙관리", "2026", "QA02", cp_no, "QA02_영수증_1200_260309.png")))
        s2, ev3 = sv.call("GET", f"/api/evidence/{quote(cp_no)}")
        ck("복사: 대상 거래의 독립 증빙 항목 (비고에 원본 번호)", s2 == 200 and len(ev3["items"]) == 1 and ev3["items"][0]["증빙번호"] == f"{cp_no}-1" and ev3["items"][0]["비고"].startswith("복사: "), ev3.get("items"))
        rec = sv.rec("exec", rn_row); rec["비고"] = "메모만"
        s, r = sv.call("PUT", f"/api/exec/{rn_row}", {"rec": rec})
        ck("이름과 무관한 수정은 파일명 그대로", s == 200 and not r.get("_renamed"), (s, r.get("_renamed")))
        # ---- 집행 취소: 집계에서 완전히 제외, 해제 가능, 연결 행은 불가 ----
        s, r = sv.call("POST", "/api/exec", {"재원": "QA01", "예산목": "연구활동비", "원인발생일": "2026-03-07", "거래처": "검사", "금액": 7777, "적요": "취소 검사", "지출완료일": "2026-03-07"})
        cx_row, cx_no = r.get("_row"), r.get("거래번호")
        s, r = sv.call("GET", "/api/all")
        before = next(x["집행액"] for x in r["dashboard"]["table"] if x["재원"] == "QA01" and x["예산목"] == "연구활동비")
        s, r = sv.call("POST", f"/api/exec/{cx_row}/action", {"action": "cancel", "extra": {"사유": "이중 결제"}})
        ck("취소 → 상태 취소", s == 200 and r.get("상태") == "취소", (s, r))
        s, r = sv.call("GET", "/api/all")
        after = next(x["집행액"] for x in r["dashboard"]["table"] if x["재원"] == "QA01" and x["예산목"] == "연구활동비")
        ck("취소 건은 대시보드 집행액에서 빠짐", after == before - 7777, (before, after))
        ck("취소 이력 기록(사유)", any(x["거래번호"] == cx_no and x["구분"] == "취소" and x["사유"] == "이중 결제" for x in r["fixlog"]), [x for x in r["fixlog"] if x["거래번호"] == cx_no])
        s, r = sv.call("POST", f"/api/exec/{cx_row}/action", {"action": "claim"})
        ck("취소 건 단계 처리 → 400", s == 400, (s, r))
        s, r = sv.call("POST", f"/api/exec/{cx_row}/action", {"action": "uncancel"})
        ck("취소 해제 → 날짜대로 상태 복귀(완료)", s == 200 and r.get("상태") == "완료", (s, r))
        s, r = sv.call("GET", "/api/all")
        ck("해제 후 집행액 복구", next(x["집행액"] for x in r["dashboard"]["table"] if x["재원"] == "QA01" and x["예산목"] == "연구활동비") == before)
        lab_ex = next((x for x in r["exec"] if x["거래번호"] in {y.get("연결거래번호") for y in r["labor"]}), None)
        if lab_ex:
            s, r2 = sv.call("POST", f"/api/exec/{lab_ex['_row']}/action", {"action": "cancel"})
            ck("인건비 연결 집행 취소 → 400", s == 400, (s, r2))
        # ---- 보완 표시 사유·이력 ----
        s, r = sv.call("POST", "/api/exec", {"재원": "QA01", "예산목": "연구활동비", "원인발생일": "2026-03-06", "거래처": "검사", "금액": 5000, "적요": "보완 검사", "지급청구일": "2026-03-06"})
        fx_row = r.get("_row"); fx_no = r.get("거래번호")
        s, r = sv.call("POST", f"/api/exec/{fx_row}/action", {"action": "fix"})
        ck("보완 표시: 사유 없으면 400", s == 400, (s, r))
        s, r = sv.call("POST", f"/api/exec/{fx_row}/action", {"action": "fix", "extra": {"사유": "영수증 원본 누락"}})
        ck("보완 표시: 사유 있으면 보완 상태", s == 200 and r.get("상태") == "보완", (s, r))
        s, r = sv.call("POST", f"/api/exec/{fx_row}/action", {"action": "unfix", "extra": {"사유": "원본 수령"}})
        ck("보완 해제", s == 200 and r.get("상태") == "청구", (s, r))
        s, r = sv.call("GET", "/api/all")
        log = [x for x in r.get("fixlog", []) if x["거래번호"] == fx_no]
        ck("보완이력: 표시·해제 2줄, 사유 보존", len(log) == 2 and log[0]["구분"] == "표시" and log[0]["사유"] == "영수증 원본 누락" and log[1]["구분"] == "해제" and log[1]["사유"] == "원본 수령", log)
        ck("보완이력: 일시 형식", all(len(str(x["일시"])) >= 16 for x in log), [x["일시"] for x in log])

        # ---- 로그인 (auth.py): 우회 서버에서는 /api/me 가 검사 이메일, 행 author 는 SQLite 모드에서만 ----
        s, r = sv.call("GET", "/api/me")
        ck("로그인: /api/me = 우회 이메일", s == 200 and r.get("email") == sv.TEST_EMAIL, (s, r))
        s, r = sv.call("POST", "/api/request", {**base, "상세": {}, "금액": 11})
        if sv.mode == "db":
            ck("로그인: 새 행 author = 로그인 이메일 (SQLite)", s == 200 and sv.row("request", r["_row"]).get("_author") == sv.TEST_EMAIL, (s, r))
        s, loc = sv.get_raw("/login")
        ck("로그인: 로그인 상태에서 /login → / 로 이동", s == 302 and loc == "/", (s, loc))

    # ---- 로그인 우회가 없는 서버: 화면은 /login 으로, API 는 401, 로그인 화면·정적 파일은 열림 ----
    with Server("api-noauth", auth_bypass=False) as sv:
        for path in ("/", "/labor", "/request"):
            s, loc = sv.get_raw(path)
            ck(f"미로그인: {path} → 302 /login", s == 302 and loc == "/login", (s, loc))
        s, r = sv.call("GET", "/api/all")
        ck("미로그인: /api/all → 401", s == 401, (s, r))
        s, r = sv.call("POST", "/api/request", {"구분": "기타", "신청인": "x", "품목": "x", "금액": 1})
        ck("미로그인: 쓰기 API → 401", s == 401, (s, r))
        s, _ = sv.get_raw("/login")
        ck("미로그인: /login 200", s == 200, s)
        s, _ = sv.get_raw("/static/style.css")
        ck("미로그인: 정적 파일 200", s == 200, s)
        s, loc = sv.get_raw("/auth/login")
        ck("미로그인: OAuth 클라이언트 없음 → /login?err=config", s == 302 and (loc or "").startswith("/login?err=config"), (s, loc))
        s, loc = sv.get_raw("/auth/callback?code=x&state=y")
        ck("미로그인: 잘못된 콜백 → /login 으로", s == 302 and (loc or "").startswith("/login?err="), (s, loc))

        # ---- 서명 쿠키로 로그인한 계정: 최초 로그인 이름 입력 (SQLite 만 묻는다) ----
        ck_ = sv.session_cookie()
        s, r = sv.call("GET", "/api/me", cookie=ck_)
        ck("쿠키 로그인: /api/me 이메일", s == 200 and r.get("email") == sv.TEST_EMAIL, (s, r))
        if sv.mode == "db":
            ck("이름 없음: needs_name, 구글 이름 미리 채움", r.get("needs_name") is True and r.get("name") == "Google Name", r)
            s, loc = sv.get_raw("/", cookie=ck_)
            ck("이름 없음: / → /welcome", s == 302 and loc == "/welcome", (s, loc))
            s, r = sv.call("GET", "/api/all", cookie=ck_)
            ck("이름 없음: API → 403", s == 403, s)
            s, _ = sv.get_raw("/welcome", cookie=ck_)
            ck("이름 없음: /welcome 200", s == 200, s)
            s, r = sv.call("POST", "/api/me/name", {"name": "   "}, cookie=ck_)
            ck("이름 저장: 빈 값 400", s == 400, (s, r))
            s, r = sv.call("POST", "/api/me/name", {"name": "가" * 21}, cookie=ck_)
            ck("이름 저장: 21자 400", s == 400, (s, r))
            s, r = sv.call("POST", "/api/me/name", {"name": "  검사  담당 "}, cookie=ck_)
            ck("이름 저장: 공백 정리", s == 200 and r.get("name") == "검사 담당", (s, r))
            s, r = sv.call("GET", "/api/me", cookie=ck_)
            ck("이름 저장 뒤: needs_name false, 이름", r.get("needs_name") is False and r.get("name") == "검사 담당", r)
            s, loc = sv.get_raw("/", cookie=ck_)
            ck("이름 저장 뒤: / 200", s == 200, (s, loc))
            s, loc = sv.get_raw("/welcome", cookie=ck_)
            ck("이름 저장 뒤: /welcome → /", s == 302 and loc == "/", (s, loc))
            s, r = sv.call("GET", "/api/all", cookie=ck_)
            ck("meta.authors 에 이름", s == 200 and r["meta"].get("authors", {}).get(sv.TEST_EMAIL) == "검사 담당", r.get("meta", {}).get("authors"))
        else:
            ck("xlsx: 이름을 묻지 않음", r.get("needs_name") is False, r)
            s, loc = sv.get_raw("/", cookie=ck_)
            ck("xlsx: / 200", s == 200, (s, loc))
        # ---- 허용 계정 관리 (/api/users): 마스터(.env)만, SQLite users 표에 저장 ----
        other = "guest@example.com"  # .env 마스터(TEST_EMAIL, OTHER_EMAIL)가 아닌 계정
        ck_o = sv.session_cookie(other)
        s, r = sv.call("GET", "/api/me", cookie=ck_o)
        ck("허용 전: 목록에 없는 계정 → 401", s == 401, (s, r))
        s, r = sv.call("GET", "/api/me", cookie=ck_)
        ck("마스터: /api/me is_master", s == 200 and r.get("is_master") is True, r)
        s, r = sv.call("GET", "/api/users", cookie=ck_)
        ck("마스터: 목록에 .env 계정이 master 로", s == 200 and [u for u in r["users"] if u["email"] == sv.TEST_EMAIL and u["master"]], r)
        s, r = sv.call("POST", "/api/users", {"email": "no-at-sign", "role": "staff"}, cookie=ck_)
        ck("추가: 형식 오류 400", s == 400 and "형식" in r.get("detail", ""), (s, r))
        s, r = sv.call("POST", "/api/users", {"email": "  ", "role": "staff"}, cookie=ck_)
        ck("추가: 빈 값 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/users", {"email": other}, cookie=ck_)
        ck("추가: 권한 없음 400", s == 400 and "권한" in r.get("detail", ""), (s, r))
        s, r = sv.call("POST", "/api/users", {"email": other, "role": "boss"}, cookie=ck_)
        ck("추가: 모르는 권한 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/users", {"email": other, "role": "staff", "name": "x" * 21}, cookie=ck_)
        ck("추가: 이름 21자 400", s == 400 and "20자" in r.get("detail", ""), (s, r))
        ck("마스터: /api/me role=master", sv.call("GET", "/api/me", cookie=ck_)[1].get("role") == "master")
        if sv.mode == "db":
            s, r = sv.call("POST", "/api/users", {"email": "  " + other.title() + " ", "role": "Researcher"}, cookie=ck_)
            ck("추가: 소문자 정규화, added", s == 200 and r.get("email") == other and r.get("added") is True, (s, r))
            s, r = sv.call("POST", "/api/users", {"email": other, "role": "staff"}, cookie=ck_)
            ck("추가: 중복은 200 + 안내", s == 200 and r.get("added") is False and r.get("message"), (s, r))
            s, r = sv.call("POST", "/api/users", {"email": sv.TEST_EMAIL, "role": "staff"}, cookie=ck_)
            ck("추가: 마스터 계정은 안내만", s == 200 and r.get("added") is False, (s, r))
            s, r = sv.call("GET", "/api/users", cookie=ck_)
            row = next((u for u in r["users"] if u["email"] == other), None)
            ck("목록: 추가한 계정, 역할, 이름 없음, 추가자", row and row["role"] == "researcher" and row["name"] == "" and row["added_by"] == sv.TEST_EMAIL and not row["master"], r)
            ck("목록: 마스터 행 role=master", [u for u in r["users"] if u["master"] and u["role"] == "master"], r)
            s, r = sv.call("GET", "/api/me", cookie=ck_o)
            ck("허용 뒤: 로그인됨, 이름 입력 필요, 마스터 아님, 역할", s == 200 and r.get("needs_name") is True and r.get("is_master") is False and r.get("role") == "researcher", (s, r))
            # 이름을 같이 준 계정은 처음 로그인 때 이름을 묻지 않는다
            named = "named@example.com"
            s, r = sv.call("POST", "/api/users", {"email": named, "role": "manager", "name": "  센터  장 "}, cookie=ck_)
            ck("추가: 이름 포함 (공백 정리)", s == 200 and r.get("added") is True, (s, r))
            s, r = sv.call("GET", "/api/me", cookie=sv.session_cookie(named))
            ck("이름 포함 계정: 이름 입력 건너뜀, 이름·역할", s == 200 and r.get("needs_name") is False and r.get("name") == "센터 장" and r.get("role") == "manager", (s, r))
            s, r = sv.call("DELETE", f"/api/users/{named}", cookie=ck_)
            ck("이름 포함 계정 삭제", s == 200, (s, r))
            s, r = sv.call("POST", "/api/me/name", {"name": "다른 사람"}, cookie=ck_o)
            ck("허용 뒤: 이름 저장", s == 200, (s, r))
            s, r = sv.call("GET", "/api/users", cookie=ck_o)
            ck("비마스터: 목록 403", s == 403, (s, r))
            s, r = sv.call("POST", "/api/users", {"email": "x@example.com"}, cookie=ck_o)
            ck("비마스터: 추가 403", s == 403, (s, r))
            s, r = sv.call("DELETE", f"/api/users/{sv.TEST_EMAIL}", cookie=ck_o)
            ck("비마스터: 삭제 403", s == 403, (s, r))
            s, r = sv.call("GET", "/api/users", cookie=ck_)
            row = next((u for u in r["users"] if u["email"] == other), None)
            ck("목록: 로그인 뒤 이름 표시", row and row["name"] == "다른 사람", r)
            s, r = sv.call("DELETE", f"/api/users/{sv.TEST_EMAIL}", cookie=ck_)
            ck("삭제: 마스터·본인 거부 400", s == 400, (s, r))
            s, r = sv.call("DELETE", "/api/users/nobody@example.com", cookie=ck_)
            ck("삭제: 목록에 없음 400", s == 400, (s, r))
            s, r = sv.call("DELETE", f"/api/users/{other}", cookie=ck_)
            ck("삭제: 200", s == 200 and r.get("removed") is True, (s, r))
            s, r = sv.call("GET", "/api/me", cookie=ck_o)
            ck("삭제 뒤: 다음 요청부터 401", s == 401, (s, r))
            s, r = sv.call("GET", "/api/all", cookie=ck_)
            ck("삭제 뒤: 이름은 meta.authors 에 남음", r["meta"].get("authors", {}).get(other) == "다른 사람", r.get("meta", {}).get("authors"))
            s, r = sv.call("GET", "/api/users", cookie=ck_)
            ck("삭제 뒤: 목록에서 빠짐", not [u for u in r["users"] if u["email"] == other], r)
        else:
            s, r = sv.call("POST", "/api/users", {"email": other, "role": "staff"}, cookie=ck_)
            ck("xlsx: 추가 400 (.env 안내)", s == 400 and ".env" in r.get("detail", ""), (s, r))
        s, r = sv.call("GET", "/api/me", cookie="ledger_session=abc.def")
        ck("위조 쿠키 → 401", s == 401, (s, r))
    return ck.done("API")


if __name__ == "__main__":
    sys.exit(main())
