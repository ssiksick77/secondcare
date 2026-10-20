# progress

Updated: 2026-10-16

## Goal

보완 표시 asks a reason and logs to 보완이력. Next task not defined.

## Done

- 2026-10-18: 보완 사유 입력 + 보완이력 시트 (store/main/app.js/style, README, API +5, UI +4). UI test note: never `evaluate` a function that awaits a dialog; wrap in setTimeout (commit: `git log --grep 'fix log'`).
- 재원 '잔액 미관리' 체크 (store/main/mcp/app.js, README, API +4, UI +4 tests) (commit: `git log --grep '잔액 미관리'`).
- 학회 여비 계산기: 출장 시작일·종료일 칸(학회 기간과 분리, 비우면 구간 → 학회 기간), 이동 구간·금액 선택 사항, 학회 전후 각 1일 초과분 = 공제일수 → 일비·식비에서 제외 + 주의 문구 (commit: `git log --grep 'deduction days'`). calc tests 32.
- 재원 종류 column + 공금 single-balance rule (store/main/mcp/app.js), README section, API 12 + UI 5 new test cases (commit: `git log --grep 'fund type'`).
- 지출결의서: 결재란 4칸(담당·매니저·선임연구원·센터장, 위 직책·아래 서명), 제목 아래 이중선 제거, 행 6.5mm, 거래번호·담당자 상자 제거(거래번호는 결의 내역 첫 줄). Verified with a screenshot and a 1-page PDF on the QA ledger (commit: see `git log --grep voucher`).
- 596f351: tests/ added (calc node test, API test, Playwright UI test, runner, server helper) and registered in `scripts/check.sh`; `main.py` honors `LEDGER_NO_BROWSER`. CLAUDE.md and README document the tests.
- 66cde60 / 9a91f0b / d1d1d91: 기타 tab review (2 agents), report, fixes (type hint line, 기타 labels, 구분 change re-approves, server drops shop codes on non-소모품 rows, integer won for 단가·부가세액).
- b6a813f / bac1758 / 515b121 / 6eed4ff: 학회 tab review (4 agents), report, fixes (server enforces calculator total, calculator keyboard/print/toggle/checklist, local-date transit nights, form order and required 출장 구분, 품의 preset).
- 2e20707 / 69b851b: travel calculator accepts 12 currencies with one rate per currency; detail JSON v:2 reads v:1.
- 7a699ad: exec form prefers the filter fund over the last-used fund.
- edc60d4 / b8bf254: adopted into the dev/ harness and moved to `dev/CAIH_회계장부_2026`.

## In progress

- (none)

## Open issues

- checks: configured, pass (smoke, test: calc 32, API 38, UI 38). The test step needs node and Playwright chromium; about 2.5 minutes, so run it with a timeout above 300 s. No lint or typecheck yet.
- 공금 leftovers: labor screen's 인건비예산 fallback still sums 예산목 budgets (empty for 공금); 재원 list has no 종류 filter; existing live ledger will get 종류=국책 written on its first save after this version.
- Uncommitted before adoption and untouched: `QA set/` (untracked) and `memo.md` (deleted in the working tree, was an empty file). Decide whether to commit or restore them.
- 2026-10-19 fixed: startup sheet check leaked a read_only workbook handle and blocked every save since 10-18 13:32 (5926413). Entries made 10-18 afternoon to 10-19 morning were lost and must be re-entered by the user.
- 학회 review leftovers: form conflict [새로 불러오기] button, leg Tab order, P3 list in docs/점검_2026-10-16_신청_학회.md.
- 기타 review leftovers: P3 list in docs/점검_2026-10-16_신청_기타.md.
- Server role check (연구원/담당자) is deferred; see ideas.md.
- The `ledger` MCP registration in Claude Desktop may still point at the old path. Re-register with the command in `app/README.md` if it fails.

## Decisions

- 2026-10-16 (user) 여비 계산기: 기본 정보 외 필수 없음; 출장 기간과 학회 기간 별도 입력; 학회 전후 각 1일만 인정, 초과 출장일은 공제일수로 일비·식비에서 자동 제외(숙박은 그대로, my choice since the user named 일비/식비 only).
- 2026-10-16 (user) 재원 종류: list 국책/원내/위탁/교육/공금/기타; 공금 deposits go through 예산변동 (no per-예산목 split), 예산목 stays required on 집행/품의/신청, existing funds default to 국책 and the user edits them later.
- 2026-10-16 (user) 지출결의서 결재란: 담당 / 매니저 / 선임연구원 / 센터장 4칸, 위 직책·아래 서명. Row height 6.5mm and blank name cells were my choice (user did not answer).
- 2026-10-16 (user) request types: 장비 = 전자제품, 소모품 = 알파몰·드림디포 purchases, 학회, everything else = 기타. D2-D6 of the 기타 review were taken as proposed because the user gave no answer.
- 2026-10-16 (user) 학회 review: transit nights by local date for air/sea legs, travel days stay KST; detail changes need re-approval; 품의 preset "학회명 (장소, 시작~종료)" with 참가자 in 비고; 출장 구분 required with no default; per-person note; 금액 row below 학회 fields; 0원 saves but cannot be approved; terms "출장 구분", "학회 여비 산출 내역". Server role check deferred.
- 2026-10-16 (user): currency list is fixed; one rate input per currency in use; all rates are won per 1 unit.
- `scripts/check.sh` uses the import check from `run.bat` as the only step, because no other check command exists. Add real checks before feature work.
- Skills are linked with Windows junctions and the agent file is copied, because symlinks need elevated permission here.
- 2026-10-19 (user) 예산목 잔액(집행내역 표·결의서 재원 현황): 예산변동을 신청일자 기준으로 집행과 날짜 순으로 섞어 누적 (이월+당초 − 1차 변경일까지 사용액 + 1차 변경액 …). 신청일자는 필수, 빈 값은 장부 연도 1월 1일로 보정. My calls: same-day budget change applies before that day's transactions; ledger year = earliest 원인발생일/신청일자, else this year. 폼 경고·대시보드 가용잔액은 전체 예산현액 기준 그대로.
- 2026-10-19 PostgreSQL 이전은 보류 (user: later). 신호가 생기면 SQLite 먼저 검토.
- 2026-10-19 (user) 적립금 증빙: 모든 적립금 행(적립·사용·주문 생성 행 포함)에 증빙 허용. 번호 `적립-YYYY-NNN`(my proposal, accepted), 드라이브 `증빙관리/YYYY/적립금/거래처명/적립번호` (user chose this path). My calls: 적립금 행에 증빙목록·증빙폴더 열은 두지 않음(화면은 증빙 시트에서 집계), 연결 집행이 있는 적립 행도 자체 증빙을 가짐(드로어에 연결 집행 증빙 수만 표시), 증빙 있는 적립금 행 삭제 금지, MCP 적립 증빙 도구 없음.
- 2026-10-19 (user) 적립금 단계: 발주일/결제일/수령일, 집행 패널 방식 그대로 (user opted out of questions). My calls: 사용 행만 단계(적립 행은 없음), 상태 열 저장+날짜에서 재계산(대기/발주/결제/수령), 새 사용 행·이전 장부 사용 행은 발주일=일자로 시작, 뒤 단계 있으면 앞 단계 비우기 금지, 주문 생성 행도 같은 패널에서 날짜 수정, MCP add_deposit 에 날짜 3개 선택 인자.
- 2026-10-19 (user) 적립번호 = 거래처코드-적립|사용-YYYY-NNN; 거래처 코드는 새 `거래처` 시트/탭에서 지정. My calls (user agreed): 코드 한글·영문·숫자 2~6자, 번호에 쓰이면 불변; 미등록 거래처는 저장 허용 + 이름 앞 글자로 자동 등록(겹치면 길게) + 안내; 주문번호 앞자리도 코드 우선; 옛 모양 번호는 보정 때 재부여하고 증빙 참조 갱신.
- 2026-10-19 (user) 소모품 구매관리대장(ref) 들여오기 완료 — docs/import_소모품대장/import.py 로 실제 장부에 적용(백업 app/backup/manual_before_import_20261019_195215.xlsx). 거래처 이름은 '알파'(코드 알파, 이전 등록명 알파미금역점은 비고), 구매처 기본 목록·app/.env REQUEST_SUPPLIERS 를 알파몰→알파로(사용자 지시). 신청번호는 앱이 새로 부여, 반려 건은 주문에 묶지 않음, 0703-01 배송일은 사용자가 직접 입력 예정. 쿠팡 멀티탭 1건은 '기타' 신청.
- 2026-10-19 (user) 들여오기 후속: 구매처 목록 알파,드림디포분당정자점(.env); 신청인 이름 통일(JIN PARK→박진용, eye…→이은희, seri oh→오세리, Haeun Kim→김하은, 실제 장부 19건, 백업 manual_before_namefix_*); 신청 비고의 '구 신청번호' 삭제; 신청 표 사유는 별도 열; 신청번호 = 구분 코드 E/S/C/Z-YYYY-NNN (구분·연도별 일련, R- 번호는 보정 때 재부여 + 주문·첨부·비고 참조 갱신, 드라이브 첨부 폴더명은 그대로); 주문 표 '신청번호' 열 → '구매내역'(첫 품목 외 n건).
- 2026-10-19 (user) 실제 장부 집행내역 융합인재·SDM·AX 거래번호를 원인발생일 순으로 재부여(58+12+6건, 적립금·인건비 연결·증빙·메타 참조 13곳 갱신, 백업 manual_before_renumber_융합인재_*). 드라이브 증빙 폴더 이름(옛 번호)은 그대로.
- 2026-10-19 (user) 집행 '취소' 상태: 사유 선택, 집계에서 완전히 제외(user). My calls: 보완처럼 수동 상태(exec_status 가 시트 '취소' 유지), cancel/uncancel 액션 + 보완이력 시트에 취소/취소해제 기록, 연결 집행(인건비·적립금) 취소 불가, 취소 건 결의서·단계 처리 불가, 표는 흐리게+금액 취소선, 빠른 필터 '취소'.

## Next action

Done 2026-10-19: 적립금 증빙, 적립금 단계, 거래처 코드. Next with the user: LEDGER_HOST + server role check, or the 학회·기타 review leftovers. Extend tests/ with each change (a voucher render test is a good candidate).
