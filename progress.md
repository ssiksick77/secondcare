# progress

Updated: 2026-10-20

## Goal

Move the ledger store from the xlsx file to SQLite so several users can work on one ledger, before the store code grows further. Screens and API behave the same; the existing tests pass; an xlsx export keeps the Excel view.

## Done

- d202ab6 Session 3: `app/export_xlsx.py` writes a read-only xlsx copy (old sheet order, 예산변동 header row 8 with summary rows 1-7 via `_refresh_budget_summary`, hidden 메타 sheet, values through `_write_row`). `test_db` exports, re-imports and compares `read_all` from SQLite, the re-import and the xlsx (53 checks). README section "SQLite 저장소", CLAUDE.md commands, `*.sqlite*` gitignored.
- 7ee9405 / f389f7f Session 2: every write path runs on SQLite when `LEDGER_DB` is set. `db.Workbook` / `db.Sheet` stand in for the openpyxl workbook; `_rows`, `_write_row`, `_next_row`, `_delete_row`, `_has_value`, `_meta_get/_meta_set`, `_rename_tag`, `_load` dispatch on the type; `_ensure_structure` and `_refresh_budget_summary` are skipped for SQLite. `_write_session` = one `BEGIN IMMEDIATE` transaction, `_save` backs up the committed state (`app/backup/*.sqlite`) and commits, `undo_last` restores from that backup, `meta.write_seq` replaces the file hash and feeds `/api/meta` (`store.data_stamp`). Each create/update/delete/replace writes one `changelog` row (author empty). `import_xlsx` repeats the structure fix-up until stable. Tests: `api-db` and `ui-db` run the API and UI tests on a SQLite copy (`LEDGER_TEST_MODE=db` in `tests/_env.py`), `test_db` checks backup, undo and changelog; `test_api` child output is read as UTF-8 (cp949 flake fixed).
- ef7ffc0 Session 1: `app/db.py` (schema: one table per sheet, `id` + `author` columns, `meta`, `changelog`), `app/import_xlsx.py` (xlsx -> SQLite, fills author, refuses to overwrite without `--force`), `store.read_all` split into `_raw_xlsx` / `_raw_db` / `_derive` and reads SQLite when `LEDGER_DB` is set, `tests/test_db.py` (45 checks: counts, 금액 totals, every column equal between xlsx and SQLite on the QA ledger), `db` group in `tests/run.py`.

## Done before the migration (xlsx era, kept for reference)

- 5926413 fix: startup sheet check leaked a read_only workbook handle; every save since 10-18 13:32 failed at os.replace (backups piled up, ledger mtime frozen). Regression test in tests/test_api.py. User re-entered the lost entries.
- 85f8c23 예산목 잔액 (집행 표·결의서 재원 현황) counts only budget rows with 신청일자 ≤ 원인발생일; 신청일자 required; blank → Jan 1 of ledger year on fix-up.
- 0cfa798 evidence on deposit rows (적립번호 key, same evidence API, drawer shared with exec via XD.kind, Drive 증빙관리/YYYY/적립금/거래처/번호).
- 99026bd deposit stages 발주일/결제일/수령일 → 상태 (사용 rows only), action endpoint, timeline in drawer, badge column, status filter.
- edaf8b4 vendor codes: `거래처` sheet/tab, 적립번호 = 코드-적립|사용-YYYY-NNN, auto-register unknown vendors with a unique name prefix, old numbers renumbered on fix-up.
- 4e6df73 / 462ec27 import script docs/import_소모품대장/import.py; applied to the live ledger (68 requests, 3 orders, 6 deposit rows, 알파 balance 20,400 = source). Supplier 알파몰 → 알파 (code, settings default, UI text, app/.env by user instruction).
- 2bc34c7 request numbers E/S/C/Z-YYYY-NNN (R- renumbered on fix-up with reference updates); 사유 as its own column. Live-ledger one-offs: requester names unified (19), '구 신청번호' notes removed (68).
- 2651274 order list column 구매내역 = first item + "외 n건".
- Live ledger: 거래번호 renumbered by 원인발생일 for 융합인재 (58), SDM (12), AX (6) with reference updates; scratch script renumber_fund.py (not in repo). Backups app/backup/manual_before_*.
- 741c0c8 exec 취소 status: cancel/uncancel actions with optional reason (logged in 보완이력), excluded from every total (server active_exec, client activeExec), voucher/stage actions blocked, linked execs cannot be cancelled.
- b2f86a0 evidence list syncs names from Drive (file_meta → store.evidence_sync), missing/trashed files flagged.
- cdda72f vendor name 알파 → 알파미금역점 (code 알파 stays): defaults (store.SUPPLIERS_DEFAULT, settings), ORDER_PREFIXES entry, request UI text, settings placeholder, README, import script VENDOR, app/.env REQUEST_SUPPLIERS. Live ledger renamed by a scratch script (79 cells: 집행내역·적립금·주문 거래처, 신청 구매처, 거래처 tab name; numbers, 적요, 비고, 품목 untouched). Backup app/backup/manual_before_vendorrename_20261020_134506.xlsx. No 알파 deposit evidence existed on Drive, so no Drive renames.
- e44e9ee evidence file names drop 적요 (`재원_증빙종류_금액_YYMMDD`, deposits `거래처_…`); editing 재원/금액 (deposit 거래처/금액) renames Drive files + ledger names (main.sync_evidence_names).

## In progress

SQLite migration, first version (brainstormed 2026-10-20). Done conditions:
- Store on SQLite: calc 32, API 95, UI 56 tests pass; screen and API behaviour unchanged. (done: api-db 95, ui-db 56 pass)
- Every record has a stable id: API and frontend address records by id, not by row number. (done in substance: `_row` carries the SQLite id; the field name stays `_row`, see Decisions)
- One-shot import script xlsx -> SQLite: on the QA ledger, every sheet's row count and amount totals equal the source. (done ef7ffc0)
- Export SQLite -> xlsx: the exported file opens in Excel with the same sheets and columns as the current ledger. (done d202ab6; opened only by openpyxl, not by Excel)
- Backup and undo on SQLite: a backup file exists before each write; undo works. (done f389f7f)
- Runs on Linux: `python main.py` starts without the .bat files. (verified by code reading only: the .bat files are wrappers, the lock uses fcntl on posix; no Linux machine here)
- Change log has an author column (email); the import fills existing rows with 안윤아 (snubh.ai.center.01@gmail.com). (done; writes log with an empty author until login)

Session order: (1) schema + import + read_all — done, (2) write paths — done, (3) export, docs — done. Left: MCP server check against SQLite, PRODUCT.md wording ("엑셀 파일이 원본"), switching the live ledger (user decision).

## Open issues

- Migration state: with `LEDGER_DB` set the app reads and writes SQLite only; the xlsx is not updated (use `export_xlsx.py` for a copy). `_row` in the API is the SQLite id. The live ledger has not been imported; switching `app/.env` to `LEDGER_DB` is the user's call (import once, then stop editing the xlsx by hand).
- SQLite mode skips `_ensure_structure`, so a ledger imported from an older xlsx must be fixed up by the import (it loops the fix-up); the budget sheet summary rows 1-7 are not kept in SQLite (export must rebuild them).
- `mcp_server.py` was not run against SQLite; it only uses store functions, so it should work, but check it in session 3.
- The worktree lacks the gitignored QA ledger; it was copied by hand from the main checkout (`docs/qa_data_2026_01_09/qa_ledger.xlsx`). A fresh worktree needs the same copy before tests run.
- The `api` group failed once inside a full `check.sh` run (detail lost) and passed on every rerun and on the next two full runs; cause unknown, possibly a port or lock timing issue. If it repeats, save the output (`bash scripts/check.sh > tests/.tmp/check_out.txt 2>&1`) and read the FAIL line.
- checks: pass (smoke; test: calc 32, API 95, db 46, api-db 95, UI 56, ui-db 56, about 5 minutes — run with a timeout above 300 s). No lint or typecheck. Two sessions running check.sh at the same time collide on tests/.tmp/ (one run fails); run checks from one session at a time.
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

- 2026-10-16 (user) 여비 계산기: 기본 정보 외 필수 없음; 출장 기간과 학회 기간 별도 입력; 학회 전후 각 1일만 인정, 초과 출장일은 공제일수로 일비·식비에서 자동 제외(숙박은 그대로, my choice since the user named 일비/식비 only).
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

## Next action

Ask the user whether to switch the live ledger now: import `의료인공지능센터_지출장부_2026.xlsx` to SQLite (`import_xlsx.py`), set `LEDGER_DB` in `app/.env`, restart the app and MCP, and keep the xlsx as a read-only export. Before that, run `mcp_server.py` once against a SQLite QA copy. Then merge branch claude/sqlite-migration-difficulty-9c1e10 into main.

Previous candidates: Candidates: one-shot rename of existing evidence files to the new rule (needs Drive connected), LEDGER_HOST + server role check, 학회·기타 review leftovers.
