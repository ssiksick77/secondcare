"""신청 API 규칙 검사 (학회·기타). QA 장부 복사본에 대해 실행한다: python -I tests/test_api.py"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import Server, Check  # noqa: E402


def main() -> int:
    ck = Check()
    with Server("api") as sv:
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
        s, r = sv.call("POST", "/api/budget", {"재원": "GG01", "변경회차": "당초", "연구활동비": 100})
        ck("공금에 예산목 예산 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/budget", {"재원": "GG01", "변경회차": "당초"})
        ck("공금 입금 없음 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/budget", {"재원": "GG01", "변경회차": "당초", "입금": 500000})
        ck("공금 입금 저장", s == 200 and r.get("입금") == 500000, (s, r))
        s, r = sv.call("POST", "/api/budget", {"재원": "NN01", "변경회차": "당초", "입금": 1000})
        ck("국책에 입금 → 400", s == 400, (s, r))
        s, r = sv.call("POST", "/api/exec", {"재원": "GG01", "예산목": "연구활동비", "원인발생일": "2026-03-02", "거래처": "검사", "금액": 120000, "적요": "공금 지출", "지출완료일": "2026-03-02"})
        ck("공금 집행 (예산목 필수 그대로)", s == 200, (s, r))
        s, r = sv.call("POST", "/api/req", {"재원": "GG01", "예산목": "연구재료비", "원인발생일": "2026-03-03", "거래처": "검사", "금액": 20000, "적요": "대기 품의"})
        ck("공금 품의", s == 200, (s, r))
        s, r = sv.call("GET", "/api/all")
        row = next((x for x in r["dashboard"]["table"] if x["재원"] == "GG01"), None)
        ck("대시보드: 공금 잔액 한 줄 = 입금 − 집행 − 대기", row is not None and row["예산목"] == "(공금 잔액)" and row["예산현액"] == 500000 and row["집행액"] == 120000 and row["가용잔액"] == 360000, row)
        ck("대시보드: 공금은 예산목 줄 없음", sum(1 for x in r["dashboard"]["table"] if x["재원"] == "GG01") == 1)
    return ck.done("API")


if __name__ == "__main__":
    sys.exit(main())
