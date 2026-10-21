"""신청 화면 브라우저 검사 (Playwright chromium, 헤드리스). QA 장부 복사본으로 실행: python -I tests/test_ui.py
학회 폼·여비 계산기, 기타 폼 문구, 저장·탭 전환·드로어·품의 전환 preset 을 본다."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import Server, Check  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("FAIL playwright 가 없습니다: python -m pip install playwright && python -m playwright install chromium")
    sys.exit(1)


def wait_closed(pg, sel="#dlg"):
    for _ in range(25):
        if not pg.evaluate(f"document.querySelector('{sel}').open"):
            return True
        pg.wait_for_timeout(200)
    return False


def find_row(pg, item):
    for _ in range(20):
        row = pg.evaluate(f"(DATA.request.find(r=>r['품목']==={item!r})||{{}})._row")
        if row:
            return row
        pg.wait_for_timeout(300)
    return None


def main() -> int:
    ck = Check()
    with Server("ui", extra_env={"LEDGER_AI_FAKE": "1"}) as sv, sync_playwright() as pw:  # 채팅방 검사: 모델 없이 가짜 답
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1366, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(sv.base + "/request"); pg.wait_for_timeout(800)
        pg.evaluate("sessionStorage.setItem('request-admin','1')"); pg.reload(); pg.wait_for_timeout(800)

        # ---- 학회 ----
        pg.click("#request-tabs [data-rtype='학회']"); pg.wait_for_timeout(400)
        heads = pg.evaluate("[...document.querySelectorAll('#request-table thead th')].map(t=>t.textContent.trim())")
        ck("학회 목록: 학회명 머리글, 수량 없음", "학회명" in heads and "수량" not in heads, heads)
        pg.click("button:has-text('신청 추가')"); pg.wait_for_timeout(500)
        ck("출장 구분: 필수·빈 기본값", pg.evaluate("(()=>{const s=document.getElementById('f-_국내외'); return s && s.required && s.value===''})()"))
        order = pg.evaluate("[...document.querySelectorAll('#dlg-fields label:not([hidden]) input[name], #dlg-fields label:not([hidden]) select[name]')].map(e=>e.name)")
        ck("금액 칸이 등록비 아래", order.index("금액") > order.index("_등록비"), order)
        pg.fill("#f-품목", "검사 학회"); pg.fill("#f-신청인", "검사"); pg.select_option("#f-_국내외", "국외"); pg.fill("#f-_장소", "파리"); pg.fill("#f-_등록비", "300000")
        pg.click("#req-calc-btn"); pg.wait_for_timeout(500)
        ck("계산기: 폼 장소로 국외·가등급 시작", pg.evaluate("document.querySelector('#cf-trip').value") == "intl" and pg.evaluate("document.querySelector('#cf-cgrade').value") == "가")
        pg.fill("#cf-fx", "1380"); pg.press("#cf-fx", "Enter"); pg.wait_for_timeout(200)
        ck("계산기: Enter 는 다음 칸", pg.evaluate("document.querySelector('#dlg-conf').open") and pg.evaluate("document.activeElement.id") != "cf-fx")
        pg.select_option("#cf-reg-cur", "EUR"); pg.fill("#cf-fx-EUR", "1500"); pg.select_option("#cf-trip", "dom"); pg.wait_for_timeout(200)
        ck("계산기: 국내는 시간대 열 숨김", pg.evaluate("getComputedStyle(document.querySelector('#cf-legs thead th:nth-child(5)')).display") == "none")
        pg.select_option("#cf-trip", "intl"); pg.wait_for_timeout(200)
        ck("계산기: 토글 왕복에 통화·환율 보존", pg.evaluate("document.querySelector('#cf-reg-cur').value") == "EUR" and pg.evaluate("document.querySelector('#cf-fx-EUR')?.value") in ("1500", "1,500"))
        pg.evaluate("""() => { const at=document.querySelectorAll('#cf-legbody .lg-at'), tz=document.querySelectorAll('#cf-legbody .lg-tz');
          ['2026-11-09T10:00','2026-11-09T15:00','2026-11-13T12:00','2026-11-14T07:00'].forEach((v,i)=>{at[i].value=v; at[i].dispatchEvent(new Event('input',{bubbles:true}));});
          [[1,'Europe/Paris'],[2,'Europe/Paris']].forEach(([i,z])=>{tz[i].value=z; tz[i].dispatchEvent(new Event('change',{bubbles:true}));}); }""")
        pg.fill("#cf-cs", "2026-11-10"); pg.fill("#cf-ce", "2026-11-12"); pg.fill("#cf-reg", "500"); pg.wait_for_timeout(300)
        ck("계산기: 입력 완료", not pg.evaluate("document.querySelector('#conf-apply').disabled"), pg.evaluate("[...document.querySelectorAll('.cf-todo li')].map(l=>l.textContent)"))
        pg.fill("#cf-fare", "1000"); pg.click("#conf-out input[data-doc]"); pg.wait_for_timeout(150)
        ck("계산기: 금액 입력 직후 서류 체크 유지", pg.evaluate("document.querySelector('#conf-out input[data-doc]').checked"))
        pg.evaluate("window.dispatchEvent(new Event('beforeprint'))"); pg.wait_for_timeout(100)
        ck("계산기: Ctrl+P 는 산출 내역", pg.evaluate("document.body.classList.contains('printing-conf') && document.querySelector('#print-conf').innerHTML.includes('학회 여비 산출 내역')"))
        pg.evaluate("window.dispatchEvent(new Event('afterprint'))")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        ck("계산기: 변경 후 Esc 는 확인", pg.evaluate("document.querySelector('#dlg-confirm').open") and pg.evaluate("document.querySelector('#dlg-conf').open"))
        pg.click("#dlg-confirm button:has-text('계속 입력')"); pg.wait_for_timeout(200)
        pg.focus("#cf-reg"); pg.keyboard.press("Control+Enter"); pg.wait_for_timeout(400)
        ck("계산기: Ctrl+Enter 적용·금액 잠금", not pg.evaluate("document.querySelector('#dlg-conf').open") and pg.evaluate("document.getElementById('f-금액').readOnly"))
        ck("계산기: 등록비 750,000 반영", pg.evaluate("document.getElementById('f-_등록비').value") == "750,000")
        pg.keyboard.press("Control+Enter")
        ck("학회: 저장", wait_closed(pg), pg.evaluate("document.querySelector('#dlg-error').textContent"))
        row = find_row(pg, "검사 학회")
        ck("학회: 저장 행 존재", row is not None)
        if row:
            pg.evaluate(f"openForm('request', {row})"); pg.wait_for_timeout(400); pg.click("#req-calc-btn"); pg.wait_for_timeout(400)
            ck("계산기: 다시 열면 천 단위 구분", pg.evaluate("document.querySelector('#cf-fx').value") == "1,380" and pg.evaluate("document.querySelector('#cf-fx-EUR').value") == "1,500")
            pg.keyboard.press("Escape"); pg.wait_for_timeout(200); pg.click("#dlg-cancel"); pg.wait_for_timeout(200)
            if pg.evaluate("document.querySelector('#dlg-confirm').open"):
                pg.click("#dlg-confirm button:has-text('버리')"); pg.wait_for_timeout(200)

        ck("신청 표: 사유 열", "사유" in pg.inner_text("#request-table thead"))
        pg.click("#request-tabs [data-rtype='소모품']"); pg.wait_for_timeout(300)  # 주문 보기는 담당자 모드 + 소모품 탭에서만
        pg.evaluate("switchReqSub('주문')"); pg.wait_for_timeout(500)
        ck("주문 표: 구매내역 열 (대표품목 외 n건)", "구매내역" in pg.inner_text("#order-table thead") and "외 " in pg.inner_text("#order-table tbody"), pg.inner_text("#order-table tbody")[:200])
        pg.evaluate("switchReqSub('신청')"); pg.wait_for_timeout(300)
        pg.click("#request-tabs [data-rtype='학회']"); pg.wait_for_timeout(300)
        # ---- 기타 ----
        pg.goto(sv.base + "/request"); pg.wait_for_timeout(800)
        pg.click("#request-tabs [data-rtype='기타']"); pg.wait_for_timeout(300)
        ck("기타: 연구원 안내문", "구독" in pg.inner_text(".req-researcher-note"))
        pg.click("button:has-text('신청 추가')"); pg.wait_for_timeout(400)
        ck("기타: 구분 안내 줄", pg.evaluate("!document.getElementById('req-type-note').hidden") and "구독" in pg.inner_text("#req-type-note"))
        lab = lambda k: pg.evaluate(f"document.getElementById('f-{k}').closest('label').textContent")
        ck("기타: 규격·부가세·단가 문구", "기간" in lab("규격") and "견적서가 공급가" in lab("부가세구분") and "실제 낼 금액" in lab("단가"))
        pg.select_option("#f-구분", "장비"); pg.wait_for_timeout(200)
        ck("장비: 문구 복귀", "모델" in lab("규격") and "쇼핑몰" in lab("부가세구분") and "전자제품" in pg.inner_text("#req-type-note"))
        pg.select_option("#f-구분", "기타"); pg.fill("#f-신청인", "검사"); pg.fill("#f-품목", "검사 구독"); pg.fill("#f-규격", "월 3석"); pg.fill("#f-단가", "90000"); pg.fill("#f-수량", "12"); pg.fill("#f-희망일", "2026-11-01")
        pg.keyboard.press("Control+Enter"); ck("기타: 저장", wait_closed(pg))
        pg.click("#request-tabs [data-rtype='장비']"); pg.wait_for_timeout(300); pg.click("button:has-text('신청 추가')"); pg.wait_for_timeout(300)
        pg.select_option("#f-구분", "기타"); pg.fill("#f-신청인", "검사"); pg.fill("#f-품목", "검사 수리"); pg.fill("#f-단가", "50000"); pg.keyboard.press("Control+Enter")
        wait_closed(pg); pg.wait_for_timeout(600)
        ck("다른 구분 저장 → 탭 전환", pg.evaluate("document.querySelector('#request-tabs [aria-selected=true]').dataset.rtype") == "기타")
        r0 = find_row(pg, "검사 구독")
        if r0:
            pg.evaluate(f"openReqDrawer({r0})"); pg.wait_for_timeout(1000)
            dtxt = pg.inner_text("#req-drawer")
            ck("기타 드로어: 규격/단위·첨부 안내", "규격/단위" in dtxt and "요금제" in dtxt)
            sv.call("POST", f"/api/request/{r0}/action", {"action": "approve"})
            pg.reload(); pg.wait_for_timeout(900); pg.click("#request-tabs [data-rtype='기타']"); pg.wait_for_timeout(300)
            pg.evaluate(f"convertRequests([DATA.request.find(r=>r._row==={r0})])"); pg.wait_for_timeout(500)
            ck("품의 전환 preset: 적요·지출예정일", pg.evaluate("document.getElementById('f-적요').value") == "검사 구독 (월 3석) × 12" and pg.evaluate("document.getElementById('f-지출예정일')?.value") == "2026-11-01")
        else:
            ck("기타: 저장 행 존재", False)
        # ---- 재원 종류 · 공금 (회계대장 화면) ----
        sv.call("POST", "/api/funds", {"재원코드": "GG01", "과제명": "센터 공금", "종류": "공금"})
        sv.call("POST", "/api/budget", {"재원": "GG01", "변경회차": "당초", "신청일자": "2026-01-01", "입금": 500000})
        s, r = sv.call("POST", "/api/exec", {"재원": "GG01", "예산목": "연구활동비", "원인발생일": "2026-03-02", "거래처": "검사", "금액": 120000, "적요": "공금 지출", "지출완료일": "2026-03-02"})
        pool_row = r.get("_row")
        pg.goto(sv.base + "/fund"); pg.wait_for_timeout(1200)
        pg.evaluate("openForm('funds')"); pg.wait_for_timeout(300)
        ck("재원 폼: 종류 select, 기본 국책", pg.evaluate("(()=>{const s=document.getElementById('f-종류'); return s && s.tagName==='SELECT' && s.value==='국책' && [...s.options].some(o=>o.value==='공금')})()"))
        pg.click("#dlg-cancel"); pg.wait_for_timeout(200)
        pg.evaluate("openForm('budget')"); pg.wait_for_timeout(300)
        pg.select_option("#f-재원", "GG01"); pg.wait_for_timeout(200)
        ck("예산변동 폼: 공금이면 예산목 숨김·입금 표시", pg.evaluate("document.getElementById('f-입금').closest('label').hidden === false && document.getElementById('f-연구활동비').closest('label').hidden === true"))
        other = pg.evaluate("[...document.querySelectorAll('#f-재원 option')].map(o=>o.value).find(v=>v && v!=='GG01')")
        pg.select_option("#f-재원", other); pg.wait_for_timeout(200)
        ck("예산변동 폼: 다른 재원이면 반대", pg.evaluate("document.getElementById('f-입금').closest('label').hidden === true && document.getElementById('f-연구활동비').closest('label').hidden === false"))
        pg.click("#dlg-cancel"); pg.wait_for_timeout(200)
        if pg.evaluate("document.querySelector('#dlg-confirm').open"):
            pg.click("#dlg-confirm button:has-text('버리')"); pg.wait_for_timeout(200)
        pg.evaluate("switchTab('dash'); renderDashboard()"); pg.wait_for_timeout(300)
        cards = pg.inner_text("#dash-cards"); table = pg.inner_text("#dash-table")
        ck("대시보드: 공금 카드·줄", "공금 잔액" in cards and "GG01 (공금)" in table and "380,000" in cards)
        if pool_row:
            pg.evaluate(f"openVoucher({pool_row})"); pg.wait_for_timeout(1000)
            vt = pg.inner_text("#voucher-sheet")
            tail = vt.split("재원 현황")[-1]
            ck("결의서: 공금 잔액 한 줄", "공금 잔액" in tail and "380,000" in tail and "\n합계\t" not in tail)
        # ---- 잔액 미관리 재원 ----
        sv.call("POST", "/api/funds", {"재원코드": "SRC1", "과제명": "출처 전용", "잔액미관리": "Y"})
        s, r = sv.call("POST", "/api/exec", {"재원": "SRC1", "예산목": "연구활동비", "원인발생일": "2026-03-05", "거래처": "검사", "금액": 7000, "적요": "출처 전용", "지출완료일": "2026-03-05"})
        src_row = r.get("_row")
        pg.reload(); pg.wait_for_timeout(1200)
        row = pg.evaluate("(DATA.funds.find(f=>f['재원코드']==='SRC1')||{})._row")
        pg.evaluate(f"openForm('funds', {row})"); pg.wait_for_timeout(300)
        ck("재원 폼: 잔액 미관리 체크 복원", pg.evaluate("document.getElementById('f-잔액미관리').checked"))
        pg.click("#dlg-cancel"); pg.wait_for_timeout(200)
        pg.evaluate("openForm('budget')"); pg.wait_for_timeout(300)
        ck("예산변동 폼: 미관리 재원은 목록에 없음", not pg.evaluate("[...document.querySelectorAll('#f-재원 option')].some(o=>o.value==='SRC1')"))
        pg.click("#dlg-cancel"); pg.wait_for_timeout(200)
        pg.evaluate("switchTab('dash'); renderDashboard()"); pg.wait_for_timeout(300)
        ck("대시보드: 미관리 재원 안내, 표에는 없음", "잔액 미관리 재원" in pg.inner_text("#dash-note") and "SRC1" not in pg.inner_text("#dash-table"))
        if src_row:
            pg.evaluate(f"openVoucher({src_row})"); pg.wait_for_timeout(1000)
            ck("결의서: 미관리 재원 안내 한 줄", "예산·잔액을 관리하지 않습니다" in pg.inner_text("#voucher-sheet"))
        # ---- 예산목 잔액: 예산변동 신청일자를 집행과 날짜 순으로 섞어 누적 ----
        sv.call("POST", "/api/funds", {"재원코드": "RB01", "과제명": "잔액 검사"})
        sv.call("POST", "/api/budget", {"재원": "RB01", "변경회차": "당초", "신청일자": "2026-01-01", "연구활동비": 100000})
        sv.call("POST", "/api/budget", {"재원": "RB01", "변경회차": "1", "신청일자": "2026-04-01", "연구활동비": 50000, "연구재료비": -50000})  # 숫자 회차는 예산목 사이 이동만 (합 0)
        rb = []
        for d, amt in (("2026-03-10", 30000), ("2026-04-01", 20000), ("2026-05-01", 10000)):
            s, r = sv.call("POST", "/api/exec", {"재원": "RB01", "예산목": "연구활동비", "원인발생일": d, "거래처": "검사", "금액": amt, "적요": "잔액 검사 " + d, "지출완료일": d})
            rb.append(r.get("_row"))
        pg.reload(); pg.wait_for_timeout(1200)
        bals = pg.evaluate(f"[{rb[0]}, {rb[1]}, {rb[2]}].map(n => runningBalance(DATA.exec.find(x => x._row === n)))")
        ck("예산목 잔액: 변경 전 거래는 당초 기준, 변경일 거래부터 증액 반영", bals == [70000, 100000, 90000], bals)
        pg.evaluate(f"openVoucher({rb[0]})"); pg.wait_for_timeout(1000)
        tail = pg.inner_text("#voucher-sheet").split("재원 현황")[-1]
        ck("결의서 재원 현황: 거래 시점의 예산만 반영", "70,000" in tail and "120,000" not in tail, tail[:300])
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        pg.evaluate("openForm('budget')"); pg.wait_for_timeout(300)
        ck("예산변동 폼: 신청일자 필수", pg.evaluate("document.getElementById('f-신청일자').required"))
        pg.click("#dlg-cancel"); pg.wait_for_timeout(200)
        # ---- 열 숨기기 (cols.js, 2026-10-21): 팝오버·우클릭·스텁·최소 1열·세션 기억 ----
        pg.evaluate("sessionStorage.clear(); switchTab('exec')"); pg.wait_for_timeout(400)
        ck("열: 상세 열 체크박스 없음, [조회 열 관리] 있음", not pg.query_selector("#exec-cols-all") and bool(pg.query_selector("[data-cols=exec]")))
        ck("열: 옛 상세 열(관리번호 등)은 스텁", pg.evaluate("['관리번호','세세목','사용자','비고'].every(k => document.querySelector(`#exec-table thead th[data-col='${k}']`).classList.contains('col-stub'))"))
        ck("열: 표 폭 ≥ 표 틀 폭 (빈 자리 없음)", pg.evaluate("(()=>{const t=document.querySelector('#exec-table'); return t.offsetWidth >= t.closest('.table-wrap').clientWidth - 1})()"))
        pg.click("[data-cols=exec]"); pg.wait_for_timeout(300)
        ck("열 관리 팝오버: 거래번호는 고정(비활성)", pg.evaluate("(()=>{const i=document.querySelector(\".col-pop input[data-k='거래번호']\"); return !!i && i.disabled && i.checked})()"))
        pg.click(".col-pop input[data-k='재원']"); pg.wait_for_timeout(300)
        ck("열 관리: 재원 체크 해제 → 스텁 10px", pg.evaluate("(()=>{const h=document.querySelector(\"#exec-table thead th[data-col='재원']\"); return h.classList.contains('col-stub') && h.offsetWidth === 10})()"))
        pg.click(".col-pop [data-close]"); pg.wait_for_timeout(200)
        pg.reload(); pg.wait_for_timeout(1500); pg.evaluate("switchTab('exec')"); pg.wait_for_timeout(400)
        ck("열 숨김: 새로고침 뒤 유지 (세션)", pg.evaluate("document.querySelector(\"#exec-table thead th[data-col='재원']\").classList.contains('col-stub')"))
        pg.click("#exec-table thead th.col-stub[data-col='재원']"); pg.wait_for_timeout(300)
        ck("스텁 클릭 → 열 복원", pg.evaluate("!document.querySelector(\"#exec-table thead th[data-col='재원']\").classList.contains('col-stub')"))
        pg.click("#exec-table thead th[data-col='예산목']", button="right"); pg.wait_for_timeout(300)
        ck("머리글 우클릭 → 메뉴 (이 열 숨기기)", "이 열 숨기기" in (pg.inner_text(".ctx-menu") if pg.query_selector(".ctx-menu") else ""))
        pg.click(".ctx-menu button[data-show='0']"); pg.wait_for_timeout(300)
        ck("우클릭 숨기기 → 예산목 스텁", pg.evaluate("document.querySelector(\"#exec-table thead th[data-col='예산목']\").classList.contains('col-stub')"))
        pg.evaluate("['상태','원인발생일','재원','적요','금액','증빙'].forEach(k => colToggle('exec', k, false))"); pg.wait_for_timeout(300)
        ck("열은 하나 이상 보임 (마지막 열은 숨기지 못함)", pg.evaluate("[...document.querySelectorAll('#exec-table thead th[data-col]')].filter(h => !h.classList.contains('col-stub')).length >= 2"))
        pg.evaluate("sessionStorage.clear(); switchTab('req'); renderList('req')"); pg.wait_for_timeout(400)
        ck("품의 표: 원인발생일 열 없음, 지출예정일 있음", pg.evaluate("(()=>{const ks=[...document.querySelectorAll('#req-table thead th')].map(h=>h.dataset.col); return !ks.includes('원인발생일') && ks.includes('지출예정일')})()"))
        pg.evaluate("switchTab('budget'); FILTERS.budget = {'재원': 'QA01'}; renderList('budget')"); pg.wait_for_timeout(400)
        ck("예산 변경 내역: 재원·내부인건비·연구개발부담비 열 없음", pg.evaluate("(()=>{const ks=[...document.querySelectorAll('#budget-table thead th')].map(h=>h.dataset.col); return !ks.includes('재원') && !ks.includes('내부인건비(공통)') && !ks.includes('연구개발부담비')})()"))
        pg.evaluate("switchTab('dash'); renderDashboard()"); pg.wait_for_timeout(400)
        pg.click("[data-cols=dash]"); pg.wait_for_timeout(300)
        ck("대시보드 열 관리: 재원·항목 고정, 내부인건비 없음", pg.evaluate("(()=>{const i=[...document.querySelectorAll('.col-pop input')]; return i.find(x=>x.dataset.k==='재원').disabled && i.find(x=>x.dataset.k==='항목').disabled && !i.some(x=>x.dataset.k==='내부인건비(공통)')})()"))
        pg.click(".col-pop input[data-k='발생이자']"); pg.wait_for_timeout(300)
        ck("대시보드: 발생이자 숨김 → 머리·칸 스텁", pg.evaluate("document.querySelector(\"#dash-table thead th[data-col='발생이자']\").classList.contains('col-stub') && document.querySelectorAll(\"#dash-table tbody td.col-stub[data-col='발생이자']\").length > 0"))
        pg.click(".col-pop [data-close]"); pg.evaluate("sessionStorage.clear()"); pg.wait_for_timeout(200)
        # ---- 거래처 탭 ----
        pg.evaluate("switchTab('deposit')"); pg.wait_for_timeout(300)
        ck("적립 탭 거래처 관리: 표에 코드 열", "코드" in pg.inner_text("#vendor-table thead"))
        pg.evaluate("openForm('vendor')"); pg.wait_for_timeout(300)
        pg.fill("#f-거래처명", "화면검사상사"); pg.fill("#f-코드", "화검"); pg.keyboard.press("Control+Enter"); ck("거래처 추가 저장", wait_closed(pg))
        pg.wait_for_timeout(600)
        ck("거래처 표에 새 행", "화검" in pg.inner_text("#vendor-table tbody"))
        # ---- 적립금 드로어: 증빙 등록 ----
        s, r = sv.call("POST", "/api/deposit", {"일자": "2026-03-08", "거래처": "검사상사", "구분": "사용", "금액": 9000, "적요": "드로어 검사"})
        dep_row, dep_no = r.get("_row"), r.get("적립번호")
        pg.reload(); pg.wait_for_timeout(1200)
        pg.evaluate("switchTab('deposit')"); pg.wait_for_timeout(300)
        pg.click(f"#deposit-table tbody tr[data-row='{dep_row}'] td[data-col='거래처']"); pg.wait_for_timeout(900)
        ck("적립금 행 클릭 → 드로어(적립번호·증빙)", not pg.evaluate("document.querySelector('#exec-drawer').hidden") and dep_no in pg.inner_text("#xd-title") and "증빙" in pg.inner_text("#xd-body"), (dep_no, pg.inner_text("#xd-title")))
        pg.fill("#evid-entry-form [name=kind]", "영수증"); pg.click("#evid-entry-form button[type=submit]")
        n_ = 0
        for _ in range(25):
            n_ = pg.evaluate(f"(DATA.evidence||[]).filter(e=>e['거래번호']==={dep_no!r}).length")
            if n_:
                break
            pg.wait_for_timeout(300)
        ck("적립 증빙 항목 추가 → 목록·표 개수", n_ == 1 and pg.inner_text(f"#deposit-table tbody tr[data-row='{dep_row}'] td[data-col='증빙']").strip() == "1", n_)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
        # ---- 적립금 단계 타임라인 (사용 행) ----
        pg.click(f"#deposit-table tbody tr[data-row='{dep_row}'] td[data-col='거래처']"); pg.wait_for_timeout(900)
        tl = pg.inner_text("#xd-body")
        ck("적립금 드로어: 처리 단계(발주 완료·결제 다음)", "처리 단계" in tl and pg.evaluate("document.querySelector('#xd-body .xd-step.done[data-col=발주일]') !== null && document.querySelector('#xd-body .xd-step.next[data-col=결제일]') !== null"))
        pg.click("#xd-body .xd-step.next button[data-act=dact]")
        st2 = None
        for _ in range(25):
            st2 = pg.evaluate(f"(DATA.deposit.find(x=>x._row==={dep_row})||{{}})['상태']")
            if st2 == "결제":
                break
            pg.wait_for_timeout(300)
        ck("오늘 등록 → 결제", st2 == "결제", st2)
        ck("적립금 표 상태 배지", "결제" in pg.inner_text(f"#deposit-table tbody tr[data-row='{dep_row}'] td[data-col='상태']"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
        # ---- 보완 표시 사유 입력·이력 ----
        s, r = sv.call("POST", "/api/exec", {"재원": "QA01", "예산목": "연구활동비", "원인발생일": "2026-03-06", "거래처": "검사", "금액": 5000, "적요": "보완 검사", "지급청구일": "2026-03-06"})
        fx_row = r.get("_row")
        pg.reload(); pg.wait_for_timeout(1200)
        pg.evaluate(f"setTimeout(() => execAction({fx_row}, 'fix'), 0)"); pg.wait_for_timeout(400)  # evaluate 가 대화상자 Promise 를 기다리지 않게
        ck("보완 표시: 사유 입력 대화상자", pg.evaluate("document.querySelector('#dlg-confirm').open && !document.querySelector('#confirm-input-wrap').hidden"))
        pg.click("#confirm-ok"); pg.wait_for_timeout(300)
        ck("보완 표시: 빈 사유는 막힘", pg.evaluate("document.querySelector('#dlg-confirm').open"))
        pg.fill("#confirm-input", "영수증 원본 누락"); pg.click("#confirm-ok")
        st_ = None
        for _ in range(25):  # 저장 → load() 까지 기다림 (느린 환경 대비)
            st_ = pg.evaluate(f"(DATA.exec.find(x=>x._row==={fx_row})||{{}})['상태']")
            if st_ == "보완":
                break
            pg.wait_for_timeout(300)
        ck("보완 표시: 저장됨", st_ == "보완", st_)
        pg.evaluate(f"openExecDrawer({fx_row})"); pg.wait_for_timeout(800)
        dt_ = pg.inner_text("#exec-drawer")
        ck("드로어: 보완 이력 표시", "보완·취소 이력" in dt_ and "영수증 원본 누락" in dt_)
        # ---- 집행 취소 (드로어 [취소] → 사유 선택 입력) ----
        pg.evaluate("setTimeout(() => execAction(%d, 'cancel'), 0)" % fx_row); pg.wait_for_timeout(400)
        ck("취소: 사유(선택) 대화상자", pg.evaluate("document.querySelector('#dlg-confirm').open && !document.querySelector('#confirm-input-wrap').hidden"))
        pg.click("#confirm-ok")
        st_c = None
        for _ in range(25):
            st_c = pg.evaluate(f"(DATA.exec.find(x=>x._row==={fx_row})||{{}})['상태']")
            if st_c == "취소":
                break
            pg.wait_for_timeout(300)
        ck("취소: 사유 없이도 저장, 상태 취소", st_c == "취소", st_c)
        ck("취소: 표 배지·해제 링크·흐린 행", pg.evaluate(f"(() => {{ const tr = document.querySelector('#exec-table tbody tr[data-row=\"{fx_row}\"]'); return !!tr && tr.classList.contains('row-cancel') && tr.innerText.includes('취소') && !!tr.querySelector('[data-action=uncancel]'); }})()"))
        ck("취소: 예산목 잔액 열 '-'", pg.evaluate(f"runningBalance(DATA.exec.find(x=>x._row==={fx_row})) === null"))
        ck("취소: 빠른 필터 타일", "취소" in pg.inner_text("#exec-tiles"))
        # ---- 설정 패널 메모 (AI 도우미 참고용): 추가 → 목록 → 삭제 ----
        pg.evaluate("closeExecDrawer()"); pg.wait_for_timeout(300)
        pg.click("#btn-settings"); pg.wait_for_timeout(600)
        ck("메모: 설정 패널에 빈 목록 안내", pg.evaluate("document.querySelector('#dlg-settings').open") and "메모가 없습니다" in pg.inner_text("#memo-list"))
        pg.click("#memo-add"); pg.wait_for_timeout(400)
        ck("메모: 추가 대화상자, 종류 기본 일반", pg.evaluate("document.querySelector('#dlg').open && document.querySelector('#f-종류').value === '일반' && document.querySelector('#f-작성일').value !== ''"))
        pg.fill("#f-내용", "회의비는 참석자 명단 첨부"); pg.click("#dlg-save")
        ck("메모: 저장 후 대화상자 닫힘", wait_closed(pg))
        for _ in range(20):
            if "참석자 명단" in pg.inner_text("#memo-list"):
                break
            pg.wait_for_timeout(300)
        ck("메모: 목록에 새 행 (설정 패널 열린 채 갱신)", pg.evaluate("document.querySelector('#dlg-settings').open") and "참석자 명단" in pg.inner_text("#memo-list") and "일반" in pg.inner_text("#memo-list"))
        pg.click("#memo-list [data-memo-del]"); pg.wait_for_timeout(400)
        ck("메모: 삭제 확인 문구", pg.evaluate("document.querySelector('#dlg-confirm').open") and "일반" in pg.inner_text("#confirm-body"))
        pg.click("#confirm-ok")
        for _ in range(20):
            if "메모가 없습니다" in pg.inner_text("#memo-list"):
                break
            pg.wait_for_timeout(300)
        ck("메모: 삭제 후 빈 목록", "메모가 없습니다" in pg.inner_text("#memo-list"))
        pg.click("#s-cancel"); pg.wait_for_timeout(200)
        # ---- 폼 'AI 추천·검증': 입력된 예산목은 덮어쓰지 않고 빈 칸만 채운다 (가짜 /api/ai/suggest) ----
        pg.evaluate(r"""() => { AI = { enabled: true, provider: 'test', model: 't' }; const _api = api;
          api = async (m, p, b) => p === '/api/ai/suggest' ? { '예산목': DATA.meta.budget_items[1], '세목': '검사세목', '태그': '', '근거': '검사', '경고': [] }
            : p === '/api/ai/chat' ? { answer: ['**굵게** 표:', '', '| 재원코드 | 과제명 |', '|---|---|', '| QA01 | 가상 A |', '| QA02 | 가상 B |'].join(String.fromCharCode(10)), proposals: [], calls: [{ tool: 'list_funds', input: {}, error: false }], usage: { input: 10, cached: 0, output: 5 } } : _api(m, p, b); }""")
        pg.evaluate("openForm('exec')"); pg.wait_for_timeout(400)
        pg.evaluate("document.querySelector('#f-예산목').value = DATA.meta.budget_items[0]")
        ck("추천: AI 바 표시", pg.evaluate("!document.querySelector('#dlg-ai').hidden"))
        pg.click("#dlg-suggest"); pg.wait_for_timeout(600)
        ck("추천: 입력된 예산목 유지, 빈 세목만 채움", pg.evaluate("document.querySelector('#f-예산목').value === DATA.meta.budget_items[0] && document.querySelector('#f-세목').value === '검사세목'"))
        ck("추천: 다른 추천은 안내문으로", "그대로 두었습니다" in pg.inner_text("#dlg-ai-msg"))
        pg.evaluate("document.querySelector('#f-예산목').value = ''"); pg.click("#dlg-suggest"); pg.wait_for_timeout(600)
        ck("추천: 빈 예산목은 채움", pg.evaluate("document.querySelector('#f-예산목').value === DATA.meta.budget_items[1]"))
        pg.evaluate("$('#dlg').dataset.initial = ''; $('#dlg').close()")
        # ---- 채팅방 (LEDGER_AI_FAKE=1: 모델 없이 가짜 답): 질문 → 표 렌더링·조회 줄 → 새로고침 후 이력 → 새 대화 → 삭제 → 고지문 ----
        pg.evaluate("toggleDrawer(true)"); pg.wait_for_timeout(500)
        ck("채팅: 고지문 표시", "마스터 계정으로 전송될 수 있습니다" in pg.inner_text("#ai-notice"))
        ck("채팅: 처음엔 방 없음", pg.evaluate("document.querySelector('#ai-room').options.length === 1 && document.querySelector('#ai-room').value === ''"))
        pg.fill("#ai-input", "첫 질문입니다"); pg.press("#ai-input", "Enter")
        for _ in range(30):
            if "(가짜 답변) 첫 질문입니다" in pg.inner_text("#ai-log"):
                break
            pg.wait_for_timeout(200)
        ck("채팅: 답변·마크다운 표·조회 줄", pg.evaluate("(() => { const m = document.querySelector('#ai-log .msg.assistant.md'); return !!m && m.querySelectorAll('table tbody tr').length === 1 && !m.textContent.includes('|'); })()") and "조회: list_funds()" in pg.inner_text("#ai-log"))
        ck("채팅: 방이 생기고 제목은 첫 질문", pg.evaluate("[...document.querySelector('#ai-room').options].map(o => o.textContent)") == ["첫 질문입니다 · 2"])
        pg.reload(); pg.wait_for_timeout(900)
        pg.evaluate("toggleDrawer(true)")
        for _ in range(30):
            if "(가짜 답변) 첫 질문입니다" in pg.inner_text("#ai-log"):
                break
            pg.wait_for_timeout(200)
        ck("채팅: 새로고침 뒤 이력 복원", "첫 질문입니다" in pg.inner_text("#ai-log .msg.user") and "(가짜 답변) 첫 질문입니다" in pg.inner_text("#ai-log"))
        pg.click("#ai-room-new"); pg.wait_for_timeout(200)
        ck("채팅: 새 대화는 빈 화면", pg.evaluate("document.querySelectorAll('#ai-log .msg').length === 0"))
        pg.fill("#ai-input", "둘째 질문"); pg.press("#ai-input", "Enter")
        for _ in range(30):
            if "(가짜 답변) 둘째 질문" in pg.inner_text("#ai-log"):
                break
            pg.wait_for_timeout(200)
        ck("채팅: 방 2개, 최근 방이 앞", pg.evaluate("[...document.querySelector('#ai-room').options].map(o => o.textContent)") == ["둘째 질문 · 2", "첫 질문입니다 · 2"])
        pg.click("#ai-room-keep"); pg.wait_for_timeout(500)
        ck("채팅: 보관 표시", pg.evaluate("document.querySelector('#ai-room').selectedOptions[0].textContent").startswith("[보관] ") and pg.inner_text("#ai-room-keep") == "보관 해제")
        pg.click("#ai-room-del"); pg.wait_for_timeout(300)
        ck("채팅: 삭제 확인 대화상자", pg.evaluate("document.querySelector('#dlg-confirm').open"))
        pg.click("#confirm-ok")
        for _ in range(20):
            if pg.evaluate("document.querySelector('#ai-room').options.length === 1"):
                break
            pg.wait_for_timeout(200)
        ck("채팅: 삭제 뒤 남은 방 하나가 열림", pg.evaluate("[...document.querySelector('#ai-room').options].map(o => o.textContent)") == ["첫 질문입니다 · 2"] and "(가짜 답변) 첫 질문입니다" in pg.inner_text("#ai-log"))
        # ---- 인건비 > 인원: 2단(이름 → 기준급여), 구분·월지급액 머리글, 숨기기 (2026-10-20) ----
        pg.goto(sv.base + "/labor"); pg.wait_for_timeout(1000)
        pg.click("#ltab-people"); pg.wait_for_timeout(200)
        heads = lambda t: pg.evaluate(f"[...document.querySelectorAll('#{t} thead th')].map(t=>t.textContent.trim())")
        ck("인원 머리글: 구분 (인건비구분 아님)", "구분" in heads("people-table") and "인건비구분" not in heads("people-table"), heads("people-table"))
        ck("기준급여 머리글: 월지급액", "월지급액" in heads("salary-table"), heads("salary-table"))
        ck("기준급여: 기본은 비어 있음 (안내 문구)", "이름을 누르면" in pg.inner_text("#salary-table tbody"))
        pg.click("#people-table tbody tr:has-text('가상연구원02') td:nth-child(2)"); pg.wait_for_timeout(200)
        sal = pg.evaluate("[...document.querySelectorAll('#salary-table tbody tr[data-row]')].map(r=>DATA.salary.find(s=>s._row===Number(r.dataset.row))['이름'])")
        ck("기준급여 표에 이름 열 없음 (제목에 표시)", "이름" not in heads("salary-table"), heads("salary-table"))
        ck("이름 클릭 → 그 사람 기준급여만", sal == ["가상연구원02"] and "가상연구원02" in pg.inner_text("#salary-who"), sal)
        ck("고른 행: aria-pressed·행 강조", pg.evaluate("(()=>{const tr=document.querySelector('#people-table tbody tr[aria-pressed=true]'); return !!tr && tr.classList.contains('selected') && tr.textContent.includes('가상연구원02')})()"))
        ck("이름 선택 목록 가나다순", pg.evaluate("JSON.stringify(peopleNames()) === JSON.stringify([...peopleNames()].sort((a,b)=>a.localeCompare(b,'ko')))"))
        pg.click("#people-table tbody tr:has-text('가상연구원01') button[data-labor=hide]")
        pg.wait_for_function("DATA.people.some(p => p['이름'] === '가상연구원01' && p['숨김'] === 'Y')", timeout=10000); pg.wait_for_timeout(200)
        names = lambda: pg.evaluate("[...document.querySelectorAll('#people-table tbody tr[data-row]')].map(r=>r.cells[0].textContent.replace(' (숨김)','').trim())")
        ck("숨기기 → 인원 목록에서 빠짐", names() == ["가상연구원02"], names())
        ck("숨기기 → 이름 선택 목록에서 빠짐", pg.evaluate("peopleNames()") == ["가상연구원02"] and "가상연구원01" not in pg.evaluate("[...document.querySelectorAll(\"select[data-filter='이름'] option\")].map(o=>o.value)"))
        pg.check("[data-filter=showHidden][data-kind=people]"); pg.wait_for_timeout(200)
        ck("숨긴 인원 보기 → (숨김) 표시와 함께 보임", "가상연구원01" in names() and "(숨김)" in pg.inner_text("#people-table tbody"), names())
        pg.click("#people-table tbody tr:has-text('가상연구원01') button[data-labor=hide]")
        pg.wait_for_function("DATA.people.some(p => p['이름'] === '가상연구원01' && p['숨김'] === '')", timeout=10000); pg.wait_for_timeout(200)
        pg.uncheck("[data-filter=showHidden][data-kind=people]"); pg.wait_for_timeout(200)
        ck("보이기 → 다시 목록에", sorted(names()) == ["가상연구원01", "가상연구원02"], names())
        ck("페이지 오류 없음", not errs, errs)

        # ---- 로그인: 상단 계정 표시, 로그인 화면 구조 ----
        pg.goto(sv.base + "/fund"); pg.wait_for_timeout(1000)
        ck("상단: 이름 없으면 이메일 표시", pg.inner_text("#top-user").strip() == sv.TEST_EMAIL, pg.inner_text("#top-user"))
        if sv.mode == "db":
            s, r = sv.call("POST", "/api/me/name", {"name": "검사자"})
            pg.goto(sv.base + "/fund"); pg.wait_for_timeout(1200)
            ck("상단: 이름 저장 뒤 이름 표시", s == 200 and pg.inner_text("#top-user").strip() == "검사자", pg.inner_text("#top-user"))
            if pool_row:
                pg.evaluate(f"openVoucher({pool_row})"); pg.wait_for_timeout(1000)
                cells = pg.evaluate("[...document.querySelectorAll('#voucher-sheet .vc-sign td')].map(td => td.textContent.trim())")
                ck("결의서 담당 칸: 작성자 이름", cells[:1] == ["검사자"] and "오인선" in cells, cells)
        ck("상단: 로그아웃 버튼", pg.is_visible("#btn-logout"))
        # ---- 허용 계정 관리 (설정 패널 · 마스터만) ----
        pg.evaluate("document.querySelectorAll('dialog[open]').forEach(d => d.close())")
        pg.click("#btn-settings"); pg.wait_for_timeout(800)
        ck("허용 계정: 마스터에게 묶음 표시, .env 계정은 마스터·삭제 버튼 없음",
           pg.is_visible("#s-users") and sv.TEST_EMAIL in pg.inner_text("#users-list") and "마스터" in pg.inner_text("#users-list")
           and not pg.query_selector(f"#users-list [data-user-del='{sv.TEST_EMAIL}']"), pg.inner_text("#users-list"))
        if sv.mode == "db":
            pg.fill("#users-email", "New.Person@Example.com"); pg.press("#users-email", "Enter"); pg.wait_for_timeout(600)
            ck("허용 계정: 권한 없이 추가하면 안내", "권한" in pg.inner_text("#users-msg") and "new.person" not in pg.inner_text("#users-list"), pg.inner_text("#users-msg"))
            pg.select_option("#users-role", "researcher"); pg.press("#users-email", "Enter"); pg.wait_for_timeout(800)
            ck("허용 계정: Enter 로 추가, 소문자, 권한 열, 이름 '—', 설정 패널 그대로",
               pg.evaluate("document.querySelector('#dlg-settings').open") and "new.person@example.com" in pg.inner_text("#users-list")
               and "연구원" in pg.inner_text("#users-list") and "—" in pg.inner_text("#users-list") and "추가했습니다" in pg.inner_text("#users-msg"), pg.inner_text("#users-msg"))
            ck("허용 계정: 추가 뒤 입력칸 비움", pg.evaluate("$('#users-email').value + $('#users-role').value + $('#users-name').value") == "")
            pg.fill("#users-email", "named.person@example.com"); pg.select_option("#users-role", "manager"); pg.fill("#users-name", "김관리"); pg.click("#users-add"); pg.wait_for_timeout(800)
            ck("허용 계정: 이름 포함 추가 → 이름 표시", "김관리" in pg.inner_text("#users-list") and "관리자" in pg.inner_text("#users-list"), pg.inner_text("#users-list"))
            pg.fill("#users-email", "new.person@example.com"); pg.select_option("#users-role", "staff"); pg.click("#users-add"); pg.wait_for_timeout(600)
            ck("허용 계정: 중복은 안내만", "이미" in pg.inner_text("#users-msg"), pg.inner_text("#users-msg"))
            pg.fill("#users-email", "no-at"); pg.select_option("#users-role", "staff"); pg.click("#users-add"); pg.wait_for_timeout(600)
            ck("허용 계정: 형식 오류 안내", "형식" in pg.inner_text("#users-msg"), pg.inner_text("#users-msg"))
            pg.evaluate("$('#dlg-settings').close()"); pg.reload(); pg.wait_for_timeout(1000)
            pg.click("#btn-settings"); pg.wait_for_timeout(800)
            ck("허용 계정: 새로고침 뒤에도 목록에 남음", "new.person@example.com" in pg.inner_text("#users-list"))
            pg.click("#users-list [data-user-del='new.person@example.com']"); pg.wait_for_timeout(400)
            pg.click("#dlg-confirm button:has-text('삭제')"); pg.wait_for_timeout(800)
            ck("허용 계정: 삭제 뒤 목록에서 빠짐", "new.person@example.com" not in pg.inner_text("#users-list") and "지웠습니다" in pg.inner_text("#users-msg"), pg.inner_text("#users-msg"))
            pg.click("#users-list [data-user-del='named.person@example.com']"); pg.wait_for_timeout(400)
            pg.click("#dlg-confirm button:has-text('삭제')"); pg.wait_for_timeout(800)
            ck("허용 계정: 이름 포함 계정 삭제", "named.person@example.com" not in pg.inner_text("#users-list"))
        else:
            ck("허용 계정: xlsx 는 추가 비활성 + .env 안내", pg.evaluate("document.querySelector('#users-add').disabled") and ".env" in pg.inner_text("#users-msg"))
        pg.evaluate("$('#dlg-settings').close(); ME.is_master = false; openSettings()"); pg.wait_for_timeout(800)
        ck("허용 계정: 마스터가 아니면 묶음 숨김", pg.evaluate("document.querySelector('#dlg-settings').open") and not pg.is_visible("#s-users"))
        pg.evaluate("$('#dlg-settings').close()")
        pg.goto(sv.base + "/login?err=denied&email=x%40y.z"); pg.wait_for_timeout(300)
        ck("로그인 화면: 우회 중이면 /enter 로 이동", pg.url.endswith("/enter"), pg.url)
        # ---- 메뉴 화면 (enter.html): 버튼 세 개, 신청은 담당자 모드로, 기본 화면 설정 ----
        ck("메뉴: 버튼 세 개 연구비·인건비·신청", pg.evaluate("[...document.querySelectorAll('.enter-btn')].map(a=>a.textContent.trim())") == ["연구비", "인건비", "신청"])
        ck("메뉴: 버튼마다 아이콘", pg.evaluate("document.querySelectorAll('.enter-btn svg').length") == 3)
        ck("시작 화면: 주소 /fund /labor /request", pg.evaluate("[...document.querySelectorAll('.enter-btn')].map(a=>a.getAttribute('href'))") == ["/fund", "/labor", "/request"])
        ck("메뉴: 상단 계정 표시", sv.TEST_EMAIL in pg.get_attribute("#top-user", "title"))
        pg.evaluate("sessionStorage.removeItem('request-admin')")
        pg.click(".enter-btn[data-home=request]"); pg.wait_for_timeout(1000)
        ck("시작 화면 → 신청: 담당자 모드 (연구원 아닌 계정)", pg.url.endswith("/request") and pg.evaluate("document.body.classList.contains('req-admin')"), pg.url)
        ck("헤더: 제목 링크 → /enter?menu=1 (메뉴 버튼 없음)", pg.get_attribute("h1 a.app-home", "href") == "/enter?menu=1" and not pg.query_selector("#btn-enter"))
        pg.goto(sv.base + "/"); pg.wait_for_timeout(800)
        ck("라우터: / → /enter", pg.url.endswith("/enter"), pg.url)
        pg.goto(sv.base + "/request"); pg.wait_for_timeout(800)  # 설정 검사는 앱 페이지에서
        pg.evaluate("openSettings()"); pg.wait_for_timeout(600)
        pg.select_option("#s-home-sel", "fund"); pg.wait_for_timeout(500)
        ck("설정: 기본 화면 저장됨", pg.inner_text("#s-home-msg").strip() == "저장됨", pg.inner_text("#s-home-msg"))
        pg.evaluate("$('#dlg-settings').close()")
        pg.goto(sv.base + "/enter"); pg.wait_for_timeout(1000)
        ck("기본 화면 연구비: /enter → /fund", pg.url.endswith("/fund"), pg.url)
        pg.goto(sv.base + "/enter?menu=1"); pg.wait_for_timeout(600)
        ck("기본 화면 있어도 ?menu=1 은 메뉴", pg.url.endswith("/enter?menu=1") and pg.evaluate("document.querySelectorAll('.enter-btn').length") == 3, pg.url)
        if sv.mode == "db": sv.call("POST", "/api/me/home", {"home": ""})
        else: pg.evaluate("localStorage.removeItem('ledger-home')")
        b.close()
    # 우회 없는 서버: 로그인 화면 구조 (랜드마크·h1·버튼·오류 안내)
    with Server("ui-noauth", auth_bypass=False) as sv, sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        pg.goto(sv.base + "/"); pg.wait_for_timeout(300)
        ck("로그인 화면: 미로그인 / → /login", pg.url.endswith("/login"), pg.url)
        ck("로그인 화면: lang=ko, header/main/footer, h1, 바로가기", pg.evaluate(
            "document.documentElement.lang === 'ko' && !!document.querySelector('header') && !!document.querySelector('main#main') && !!document.querySelector('footer') && !!document.querySelector('h1') && !!document.querySelector('a.skip')"))
        ck("로그인 화면: 구글 로그인 버튼 → /auth/login", pg.get_attribute("#btn-google", "href") == "/auth/login" and "Google" in pg.inner_text("#btn-google"))
        ck("로그인 화면: 오류 없을 때 알림 숨김", pg.evaluate("document.getElementById('login-alert').hidden"))
        pg.goto(sv.base + "/login?err=denied&email=x%40y.z"); pg.wait_for_timeout(300)
        ck("로그인 화면: 허용되지 않은 계정 안내 (role=alert)", pg.evaluate("!document.getElementById('login-alert').hidden && document.getElementById('login-alert').getAttribute('role') === 'alert'") and "x@y.z" in pg.inner_text("#login-alert"))
        b.close()
    return ck.done("화면")


if __name__ == "__main__":
    sys.exit(main())
