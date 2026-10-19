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
                            env=dict(os.environ, LEDGER_XLSX=xlsx), capture_output=True, text=True)
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
                            env=dict(os.environ, LEDGER_XLSX=os.path.join(fill_dir, "ledger.xlsx")), capture_output=True, text=True)
        ck("빈 신청일자 → 장부 연도 1월 1일로 보정", pr.returncode == 0, pr.stderr[-300:])
        s, r = sv.call("POST", "/api/exec", {"재원": "SRC1", "예산목": "연구활동비", "원인발생일": "2026-03-05", "거래처": "검사", "금액": 7000, "적요": "출처 전용 집행"})
        ck("미관리 재원 집행은 저장됨", s == 200, (s, r))
        s, r = sv.call("GET", "/api/all")
        ck("대시보드: 미관리 재원 줄·집계 제외 모두 없음", not any(x["재원"] == "SRC1" for x in r["dashboard"]["table"]) and not any(x["재원"] == "SRC1" for x in r["dashboard"]["excluded"]["exec"]))
        # ---- 적립금 증빙: 적립번호 자동 부여, 증빙은 집행과 같은 API 로 ----
        import re
        from urllib.parse import quote
        s, r = sv.call("GET", "/api/all")
        ck("적립금: 기존 행 모두 적립번호 보정", r["deposit"] and all(re.fullmatch(r"적립-\d{4}-\d{3}", str(x.get("적립번호") or "")) for x in r["deposit"]), [x.get("적립번호") for x in r["deposit"]][:5])
        s, r = sv.call("POST", "/api/deposit", {"일자": "2026-03-07", "거래처": "검사/상사", "구분": "사용", "금액": 12000, "적요": "증빙 검사"})
        dep_no, dep_row = r.get("적립번호"), r.get("_row")
        ck("적립금 추가: 적립-YYYY-NNN 부여", s == 200 and re.fullmatch(r"적립-2026-\d{3}", str(dep_no)), (s, r))
        rec = sv.rec("deposit", dep_row); rec["적립번호"] = "적립-2026-999"; rec["비고"] = "번호 바꾸기 시도"
        s, r = sv.call("PUT", f"/api/deposit/{dep_row}", {"rec": rec})
        ck("적립금 수정: 적립번호는 불변", s == 200 and r.get("적립번호") == dep_no, (s, r))
        s, r = sv.call("POST", f"/api/evidence/{quote(dep_no)}/entry", {"증빙종류": "영수증", "비고": "실물"})
        ck("적립 증빙 항목(실물만) 추가", s == 200 and r.get("증빙번호") == f"{dep_no}-1", (s, r))
        s, r = sv.call("POST", f"/api/evidence/{quote('적립-2099-001')}/entry", {"증빙종류": "영수증"})
        ck("없는 적립번호 → 404", s == 404, (s, r))
        import requests
        up = requests.post(f"{sv.base}/api/evidence/{quote(dep_no)}", data={"kind": "카드전표"}, files={"files": ("r.png", b"\x89PNG fake", "image/png")})
        upj = up.json()
        ck("적립 증빙 업로드: 증빙관리/연도/적립금/거래처/적립번호", up.status_code == 200 and upj["folder"]["id"] == f"증빙관리/2026/적립금/검사 상사/{dep_no}", (up.status_code, upj))
        ck("적립 증빙 파일명: 거래처_적요_종류_금액_YYMMDD", up.status_code == 200 and upj["items"][0]["파일명"] == "검사 상사_증빙 검사_카드전표_12000_260307.png", upj.get("items"))
        s, r = sv.call("GET", f"/api/evidence/{quote(dep_no)}")
        ck("적립 증빙 목록 2건", s == 200 and len(r["items"]) == 2, (s, r))
        s, r = sv.call("DELETE", f"/api/deposit/{dep_row}", {})
        ck("증빙 있는 적립금 행 삭제 → 400", s == 400, (s, r))
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
    return ck.done("API")


if __name__ == "__main__":
    sys.exit(main())
