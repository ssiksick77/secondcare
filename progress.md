# progress

Updated: 2026-10-16

## Goal

지출결의서 form updated (결재란, no title rule, 6.5mm rows). Next task not defined.

## Done

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

- checks: configured, pass (smoke, test). The test step needs node and Playwright chromium on the machine; it takes about 1 minute. No lint or typecheck yet.
- Uncommitted before adoption and untouched: `QA set/` (untracked) and `memo.md` (deleted in the working tree, was an empty file). Decide whether to commit or restore them.
- 학회 review leftovers: form conflict [새로 불러오기] button, leg Tab order, P3 list in docs/점검_2026-10-16_신청_학회.md.
- 기타 review leftovers: P3 list in docs/점검_2026-10-16_신청_기타.md.
- Server role check (연구원/담당자) is deferred; see ideas.md.
- The `ledger` MCP registration in Claude Desktop may still point at the old path. Re-register with the command in `app/README.md` if it fails.

## Decisions

- 2026-10-16 (user) 지출결의서 결재란: 담당 / 매니저 / 선임연구원 / 센터장 4칸, 위 직책·아래 서명. Row height 6.5mm and blank name cells were my choice (user did not answer).
- 2026-10-16 (user) request types: 장비 = 전자제품, 소모품 = 알파몰·드림디포 purchases, 학회, everything else = 기타. D2-D6 of the 기타 review were taken as proposed because the user gave no answer.
- 2026-10-16 (user) 학회 review: transit nights by local date for air/sea legs, travel days stay KST; detail changes need re-approval; 품의 preset "학회명 (장소, 시작~종료)" with 참가자 in 비고; 출장 구분 required with no default; per-person note; 금액 row below 학회 fields; 0원 saves but cannot be approved; terms "출장 구분", "학회 여비 산출 내역". Server role check deferred.
- 2026-10-16 (user): currency list is fixed; one rate input per currency in use; all rates are won per 1 unit.
- `scripts/check.sh` uses the import check from `run.bat` as the only step, because no other check command exists. Add real checks before feature work.
- Skills are linked with Windows junctions and the agent file is copied, because symlinks need elevated permission here.

## Next action

Pick the next feature with the user: LEDGER_HOST + server role check, or the 학회·기타 review leftovers. Extend tests/ with each change (a voucher render test is a good candidate).
