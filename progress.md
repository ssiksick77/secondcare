# progress

Updated: 2026-10-20

## Goal

Two-column app frame and table polish (branch claude/dashboard-ui-improvement-4f9f95, 2026-10-20): every screen looked stretched at 1366-1920 px. The right side panel absorbs the width, and the list tables got fixed column widths. Checked by `scripts/check.sh` and the browser pane on the QA copy (port 8893, launcher `.claude/launch.json` name `qa`).

## Done

- e8a8282 Two-column frame: `.shell` > `.col` + `aside#side`; drawers (집행·적립금 상세, 신청 상세, AI) render inside the panel; side controller at the end of app.js (`setSide`, `syncSide`, rail, localStorage `ledger-side`).
- 5ca28ff Feedback round (about 30 items), all verified in the browser pane at 1366, 1536, 1600 and 1920:
  - Panel: header and tab rows full width and sticky; panel fixed below them (`--top-h` 92 px), rail on the right, body 480 px; always open from 1500 px (collapse button hidden); below that the saved state, default collapsed; `.col` margin reserves the width.
  - Dashboard: 종류 (1st) and 재원 (2nd) filters, 연도 moved to the header (`.top-year`, hidden in labor and request modes), no month filter; 12 fixed KPI cards (10 items without 연구개발부담비, 공금 잔액, MSRI placeholder) in 6 columns; fund x item table with 4 lines per fund (예산현액 / (집행액) / (예정액) / 가용잔액 double rule), 내부인건비·연구개발부담비 hidden, fixed 108 px columns; chart y-axis top = 예산현액 (0-100 %); deposit table stretched to the chart height with blank ruled rows and the total pinned at the bottom; print = A4 portrait report (`#print-report`, `reportHtml`, `@page report`): title, meta table, KPI table, 집행 현황 (thousands when more than 6 item columns), 태그 × 월 (thousands), footnote, page numbers.
  - Lists: `table-layout: fixed` with per-column widths for 집행·품의·적립·예산 tables, light vertical rules, no navy margin line, cells clip with ellipsis, folding by main width (`@container main`, tiers 1500/1300/1100/900/760), empty-row colspan fitted to visible headers (`fixEmptySpan`), scroll boxes sized from their real position (`fitWraps`), total row sticky at the box bottom, action column border instead of shadow, scroll-hint gradient removed, main bottom padding 20 px, footer removed, headers centered, 작성자 column (`authorName`), tab restore moved after the `XD` declaration (it silently failed before).
  - Menus: 집행 / 품의 / 적립; 거래처 tab merged into 적립 as a left pane next to 적립금 잔액 (no total row there); 집행전환 button → 집행.
  - 품의: 지출예정일 is the only date in the table and form; the form writes 원인발생일 = 지출예정일; old rows fall back to 원인발생일 on screen.
  - 예산: both tables uniform 104 px item columns, bold 예산현액 합계, 재원 column dropped from 변경 내역, 내부인건비·연구개발부담비 hidden, numbered rounds must net to zero except 발생이자 (server `_validate` + form pre-check + API tests).

- Merged main 3e5d95a (people tab layout, salary name column, row select) into this branch on 2026-10-20; conflicts in app.js (집행 button vs btn-ghost people button, both kept) and progress.md (this file kept).

## In progress

None. The merge into main is the next step (see Next action).

## Decisions (this task)

- Layout variant 2 (full-height right column) + collapse rail, chosen by the user from five mocks (scratchpad mock/layout.html). Then changed on feedback: panel below the header and tabs, rail on the right, 480 px, no collapse from 1500 px.
- Column folding keys on the main width (container query), not on the panel state: the panel is permanent on wide screens.
- Hidden items on screen (연구개발부담비, 내부인건비 in 예산; both in the dashboard table) stay in CSV and in totals.
- 품의 keeps the 원인발생일 field in the ledger (numbering, balance by date) but the UI shows only 지출예정일.
- Numbered budget rounds are reallocations: 발생이자 and 입금 free, everything else must sum to 0. Existing rows are not re-validated.
- The dashboard critique (app/.impeccable/critique/2026-10-20T10-29-26Z__app-static-index-html.md, 26/40) P2-P5 stay in ideas.md.

## Next action

Merge main (3e5d95a, people tab fixes) into this branch, resolve conflicts (app.js 집행전환 line, style.css near the table rules, progress.md), run `scripts/check.sh` on the merged tree, then fast-forward main and restart run.bat.

## Open issues

- checks on 5ca28ff: full `scripts/check.sh` passed calc, api 157, db, ai, api-db; ui and ui-db failed once on a leftover `tests/.tmp/ui` folder from an aborted run (an orphan test server held `server.log`), then passed 97/97 and 107/107 after the last app.js fix. A full run on the merged tree is still due. Before a rerun, make sure no orphan `python main.py` from an aborted run is alive (ports 8791 = live app, 8893 = QA pane must stay).
- MSRI card and the side panel 기본 tab are placeholders; the user will define them later (ideas.md).
- Printing the dashboard report was checked by rendering `#print-report` on screen, not through a real print dialog.
- The QA server on port 8893 must be restarted after `app/store.py` changes (done once for the budget rule).
- checks: pass on the merged tree 440bfce (calc 32, API 126, db 56, ai 166, api-db 155, UI 97, ui-db 107; about 7 minutes). Run with a timeout above 420 s.
- Hidden people still appear in the 계획표 and 선급·미지급 tables when they have pay or accrual that year (my call: hiding must not drop money from totals).
- Server role checks are not implemented: `role` is stored and shown only. Design doc §4 and §8 step 3 describe the checks. `extra.admin` from the request screen is still trusted.
- No UI to change an account's role or name after adding; delete and add again. Masters are `.env` only.
- krds-improve / impeccable were not run on the new fieldset; it follows the existing memo fieldset pattern (label, aria-live, button names).
- The design doc §5.3 (no-login local mode) and §6 (`users.json`) are superseded; the note at the top of the doc says so.
- Live ledger is SQLite since 2026-10-20 14:58. `의료인공지능센터_지출장부_2026.xlsx` is frozen at that moment: do not edit it by hand, it is no longer read. For an Excel view run `python app/export_xlsx.py <sqlite> <copy.xlsx>`. Backups are `app/backup/*.sqlite`. `_row` in the API is the SQLite id.
- Worktree branches claude/sqlite-migration-difficulty-9c1e10, claude/resolution-signature-names-196bd0 and claude/google-login-implementation-33c005 are merged and can be deleted.
- Static files have no version query, so a code change can show stale CSS until a hard refresh (ideas.md [later][fix] 2026-10-20).
- SQLite mode skips `_ensure_structure`, so a ledger imported from an older xlsx must be fixed up by the import (it loops the fix-up); the budget sheet summary rows 1-7 are not kept in SQLite (export must rebuild them).
- `mcp_server.py` was not run against SQLite; it only uses store functions, so it should work, but check it in session 3.
- Manual QA launcher for the browser pane (local, untracked `.claude/launch.json` → scratchpad run_manual.py): QA copy in tests/.tmp/manual, LEDGER_AI_FAKE=1, LEDGER_AUTH_BYPASS=qa@example.com, port 8795.
- Rename note for the AI tools: the brainstorm named `search_exec`; the tool is `search_ledger` (it spans 집행·신청·품의). `.claude/launch.json` (browser-pane launcher `qa-manual`) is local and untracked.
- The worktree lacks the gitignored QA ledger; it was copied by hand from the main checkout (`docs/qa_data_2026_01_09/qa_ledger.xlsx`). A fresh worktree needs the same copy before tests run. In worktree budget-tab-ui-cleanup-0e65ee an untracked `.claude/launch.json` (`qa`, port 8891, LEDGER_AUTH_BYPASS=preview@example.com, writes to the copied QA ledger) serves the browser pane.
- The `api` group fails about once in six full `check.sh` runs and passes on rerun. Captured on 2026-10-20: test '구분 변경 → 재결재' got HTTP 423 '장부 파일에 쓸 수 없습니다' (store.py PermissionError on os.replace of the xlsx copy): a Windows file-lock race (indexer/antivirus), not a code bug. If it repeats often, retry the save once in `store._save` or run the api group on SQLite only.
- checks: pass on the merged tree 2026-10-20 (smoke; test: calc 32, API 110, db 55, ai 122, api-db 120, UI 74, ui-db 76, about 7 minutes — run with a timeout above 420 s). No lint or typecheck. Two sessions running check.sh at the same time collide on tests/.tmp/ (one run fails); run checks from one session at a time.
- The app running on port 8791 must be restarted to read the new REQUEST_SUPPLIERS in app/.env.
- Live ledger follow-ups for the user: enter 배송일 for order 알파-20260703-01 (11 requests then become 완료); review auto-registered vendor codes in the 거래처 tab (codes are immutable once used in a number).
- Existing evidence files keep old-rule names (with 적요) until their exec's 재원/금액 is edited; a one-shot rename script could be offered. Folder names were fixed by [드라이브 동기화] on 2026-10-20.
- MCP `update_row` does not rename evidence files (only the web PUT route does).
- 공금 leftovers: labor screen's 인건비예산 fallback still sums 예산목 budgets; 재원 list has no 종류 filter.
- Uncommitted before adoption and untouched: `QA set/` (untracked) and `memo.md` (deleted in the working tree, was an empty file). Decide whether to commit or restore them.
- 학회 / 기타 review leftovers: P3 lists in docs/점검_2026-10-16_신청_학회.md and 점검_2026-10-16_신청_기타.md; form conflict [새로 불러오기] button; leg Tab order.
- Server role check (연구원/담당자) deferred; see ideas.md. PostgreSQL migration deferred (user: later; try SQLite first if ever).
- The `ledger` MCP registration in Claude Desktop may still point at the old path. Re-register with the command in `app/README.md` if it fails.

## Decisions

- 2026-10-20 (user) Allowed-account management: store in the SQLite `users` table (option 2 of 3), only master accounts (`.env` `LEDGER_ALLOWED_EMAILS`) may manage; on add set a role (required) and a name (optional) per `docs/권한_설계_2026-10-20.md`. My calls: fieldset inside the settings dialog (not a separate page); delete keeps the row and name; allow check runs in the middleware on every request so removal needs no restart; xlsx mode uses `.env` only; a master-given name skips the first-login prompt; re-adding an allowed account changes nothing; no title field; pre-existing allowed rows default to `staff`.
- 2026-10-20 (user) Allowed-email management: store the allow-list in the SQLite `users` table (approach 2 of 3; `.env` emails stay as bootstrap masters that cannot be removed), and only master accounts (now: the `.env` emails) may manage it. Rejected: `.env`-only text field (no names, no room for roles); a separate `/users` page (too big now). My calls: removing keeps the users row and name (author names on ledger rows stay readable) and only clears allowed; the middleware checks the allow-list on every request so removal needs no restart; master is derived from `.env` only, no role column yet; xlsx mode uses the `.env` list only.
- 2026-10-20 (user) First-login name entry instead of an email-to-name map in .env: ask once, no change UI yet; the imported author (snubh.ai.center.01@gmail.com) is asked like everyone else. My calls: `users` table in SQLite, prefill from the Google profile, xlsx mode skips the prompt, voucher 담당 cell reads the row author.
- 2026-10-20 (user) 결의서 결재란 이름: 매니저 오인선, 선임연구원 이진영, 센터장 류지원 with small '직무대행' above the name, bold italic; 담당 cell stays empty until login gives an email-to-name map (per-transaction author, not a fixed setting). My calls: name 11pt, tag 6.5pt with -0.2mm tracking inside the name width.
- 2026-10-16 (user) 여비 계산기: 기본 정보 외 필수 없음; 출장 기간과 학회 기간 별도 입력; 학회 전후 각 1일만 인정, 초과 출장일은 공제일수로 일비·식비에서 자동 제외(숙박은 그대로, my choice since the user named 일비/식비 only).
- 2026-10-20 (user) 재원 종류 연구지원 신설, 지급처명에 '연구지원'이 든 지급처를 정식 재원으로 이동, 코드의 앞 '연구' 삭제, 기존 거래 코드명 수정; 기본 정렬 국책-교육-원내-위탁-연구지원-기타 (공금 위치는 말하지 않아 기타 앞에 둠). My calls: 잔액미관리=Y, 과제명=옛 지급처명.
- 2026-10-16 (user) 재원 종류: list 국책/원내/위탁/교육/공금/기타; 공금 deposits go through 예산변동 (no per-예산목 split), 예산목 stays required on 집행/품의/신청, existing funds default to 국책 and the user edits them later.
- 2026-10-16 (user) 지출결의서 결재란: 담당 / 매니저 / 선임연구원 / 센터장 4칸, 위 직책·아래 서명. Row height 6.5mm and blank name cells were my choice (user did not answer).
- 2026-10-16 (user) request types: 장비 = 전자제품, 소모품 = 알파·드림디포 purchases, 학회, everything else = 기타. D2-D6 of the 기타 review were taken as proposed because the user gave no answer.
- 2026-10-16 (user) 학회 review: transit nights by local date for air/sea legs, travel days stay KST; detail changes need re-approval; 품의 preset "학회명 (장소, 시작~종료)" with 참가자 in 비고; 출장 구분 required with no default; per-person note; 금액 row below 학회 fields; 0원 saves but cannot be approved; terms "출장 구분", "학회 여비 산출 내역". Server role check deferred.
- 2026-10-16 (user): currency list is fixed; one rate input per currency in use; all rates are won per 1 unit.
- Skills are linked with Windows junctions and the agent file is copied, because symlinks need elevated permission here.
- 2026-10-19 (user) 예산목 잔액(집행내역 표·결의서 재원 현황): 예산변동을 신청일자 기준으로 집행과 날짜 순으로 섞어 누적. 신청일자 필수, 빈 값은 장부 연도 1월 1일. My calls: same-day budget change applies first; ledger year = earliest 원인발생일/신청일자, else this year. 폼 경고·대시보드 가용잔액은 전체 예산현액 기준 그대로.
- 2026-10-19 PostgreSQL 이전은 보류 (user: later). 신호가 생기면 SQLite 먼저 검토.
- 2026-10-19 (user) 적립금 증빙: 모든 적립금 행에 증빙 허용, 드라이브 `증빙관리/YYYY/적립금/거래처명/적립번호`. My calls: 적립금 행에 증빙목록·증빙폴더 열 없음, 연결 집행이 있는 적립 행도 자체 증빙, 증빙 있는 적립금 행 삭제 금지, MCP 적립 증빙 도구 없음.
- 2026-10-19 (user) 적립금 단계 발주일/결제일/수령일, 집행 패널 방식 그대로. My calls: 사용 행만, 상태 저장+날짜에서 재계산, 새/기존 사용 행은 발주일=일자, 뒤 단계 있으면 앞 단계 비우기 금지, 주문 생성 행도 같은 패널에서 수정.
- 2026-10-19 (user) 적립번호 = 거래처코드-적립|사용-YYYY-NNN, 코드는 `거래처` 시트/탭. 코드 2~6자, 번호에 쓰이면 불변; 미등록 거래처는 저장 허용 + 자동 등록(겹치면 길게) + 안내; 주문번호 앞자리도 코드 우선.
- 2026-10-19 (user) 소모품 구매관리대장 들여오기: 거래처 '알파'(코드 알파), 구매처 목록 알파,드림디포분당정자점(.env), 신청번호는 앱이 부여, 반려 건은 주문에 묶지 않음, 0703-01 배송일은 사용자 입력, 쿠팡 1건은 '기타'. 신청인 이름 통일, '구 신청번호' 비고 삭제.
- 2026-10-19 (user) 신청번호 = E/S/C/Z-YYYY-NNN (구분·연도별), 사유 별도 열, 주문 표 구매내역. My call: 구분을 바꿔도 번호 유지; 드라이브 첨부 폴더명은 그대로.
- 2026-10-19 (user) 거래번호 재부여(융합인재·SDM·AX)는 원인발생일 순, 같은 날은 행 순.
- 2026-10-19 (user) 집행 '취소': 사유 선택, 집계에서 완전히 제외. My calls: 보완처럼 수동 상태, 보완이력에 취소/취소해제 기록, 연결 집행 취소 불가, 취소 건 결의서·단계 처리 불가, 표는 흐리게+금액 취소선.
- 2026-10-19 (user) 드라이브에서 바꾼 증빙 이름을 조회 때 장부에 반영, 원래 이름은 남기지 않음. 없거나 휴지통이면 missing 표시만.
- 2026-10-20 (user) 증빙 파일명에서 적요 제거(짧게, 내부 메모 노출 방지); 재원·거래처·금액 수정 시 자동 변경. 거절된 대안: 증빙번호+거래처, 분류 접두. My calls: MCP update_row 는 이름 변경 안 함, 기존 파일은 수정 전까지 옛 이름.
- 2026-10-20 (user) 증빙 교체([교체] 버튼, replace=1, 옛 파일 휴지통) 9ff0690; 드라이브가 기준: 지운(휴지통) 파일의 증빙 행은 조회·[드라이브 동기화] 때 장부에서 삭제, 폴더 이름은 현재 번호로 수정(drive.fix_folder_name) b6d17cf; 증빙번호는 지운 번호 재사용(베타, 메타 최고값 폐기). 실제 장부에 동기화 1회 실행: AX 증빙 8건 삭제(사용자가 일부러 지움), 폴더 3개 이름 수정, 백업 manual_before_drivesync_*. drive.file 권한이라 직접 넣은 파일은 못 봄(README).
- 2026-10-20 (user) 증빙 업로드 시 원본파일명 보존 안 함(열은 남기되 빈 값), 실제 장부의 기존 값 9건 비움(백업 manual_before_origname_*). 신청 첨부는 그대로.
- 2026-10-20 (user) 거래처 이름 알파 → 알파미금역점, 코드는 알파 유지. My calls: 적립번호·주문번호·메타 키·적요·비고·품목명은 그대로, 거래처 탭 비고는 "이전 이름 알파 (코드 알파)".
- 2026-10-20 Session 3 (my calls): keep the API field name `_row` (it already holds the SQLite id; renaming touches every JS file and MCP docstring for no behaviour change); the export rebuilds the budget summary and 메타 sheet instead of copying the old file; `export_xlsx.py` refuses to overwrite without `--force`.
- 2026-10-20 Session 2 (my calls): keep the openpyxl-shaped write code and put a SQLite adapter under it instead of rewriting 60 functions; one transaction per write session; backup = SQLite backup API of the committed state taken inside `_save` before commit; undo = restore from that backup; change detection = `meta.write_seq` (WAL makes file mtime unreliable); changelog rows per row action, create-then-write logs once.
- 2026-10-20 SQLite schema (my calls): one table per sheet with the Korean headers as column names; empty cells NULL, numeric columns REAL, other columns untyped so 변경회차 keeps int vs text; dates as 'YYYY-MM-DD' text; `_row` carries the SQLite id so screens work unchanged until the frontend is renamed; `author` stores the email only (name mapping comes with login).
- 2026-10-20 (user) SQLite migration, multi-user. Target: 3 (several accountants + researchers filing requests), external access, centre Linux server later, tunnel from a centre PC first. Login = Google, allow-list of emails managed by the accountant, first accountant in app/.env. Roles, login, external access, deployment are all later; the migration only adds stable ids and an author column. Existing rows get author 안윤아 (snubh.ai.center.01@gmail.com). SQLite before PostgreSQL (2026-10-19 decision kept).
- 2026-10-20 (user) 한 문서(사전결재안 등)를 여러 거래의 증빙으로: 증빙 행 [복사] → 거래번호 여러 개 → 그 거래 폴더로 drive.copy(그 거래 기준 이름), 독립 증빙 항목(비고 '복사: 원본'). 연결(공유 파일)·드라이브 바로가기 방식은 사용자가 거절. POST /api/evidence/{번호}/copy.
- 2026-10-20 (user) Google login: full lock (every screen and API), allow-list in `.env` only (management UI later), web-application OAuth client with `LEDGER_OAUTH_REDIRECT` as a setting so a later host name is a config change. My calls: xlsx mode locks the same but records no author; MCP server is unaffected (no HTTP) and uses author `mcp`; cookie 30 days; tests bypass auth with a fixed email and never call Google.

- 2026-10-20 (user) AI helper overhaul: hybrid C = small summary in the system prompt + read tools (not full ledger, not summary only); one tool module for MCP and the in-app agent; memo store by target kind (재원·거래처·일반), user edits, AI proposes and the user approves; fx_rate tool in the first version; OpenAI tool calling, receipt OCR (OCI candidate), report, travel calculator, rule-document answers all later. Accountant-role version first; the researcher version is a separate agent with its own smaller tool set (restriction by tool availability, not by prompt). My calls: memo UI in the settings panel; frankfurter.app for rates; tool loop cap stays 6; chat shows one line per tool call under the answer.

- 2026-10-20 (user) Staff tab: 기타 is confirmed as 외부인건비(공통); 가나다 sort applies to people names only ("일단 인원 이름만"). My calls: rename labels only, not storage columns; 숨김 as a Y column like 잔액미관리; hidden people stay in plan and prepaid tables.
- 2026-10-20 (user) AI chat rooms: server storage (not browser), separate file `app/chats.sqlite` (not the ledger DB: no backup/undo/export mixing), rooms per login email, 7-day auto-delete unless kept, model gets the last 40 messages, past proposal cards act only within their turn, xlsx mode not considered (owner falls back to `local`), notice that misuse may be forwarded to the master account (notice only; detection later). My calls: purge on startup and on list, by last message; title = first question (30 chars), renamable; room list at the top of the panel; delete is permanent.
