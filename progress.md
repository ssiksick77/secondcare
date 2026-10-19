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

## Next action

Pick the next feature with the user: LEDGER_HOST + server role check, or the 학회·기타 review leftovers. Extend tests/ with each change (a voucher render test is a good candidate).
