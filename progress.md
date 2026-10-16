# progress

Updated: 2026-10-16

## Goal

학회 tab review done and fixes applied (docs/점검_2026-10-16_신청_학회.md, 반영 결과 section). Next task not defined.

## Done

- 2026-10-16: 학회 tab review (4 agents) → report → user decisions D1-D7, D9 → fixes in store.py (515b121) and conf.js/request.js/app.js/index.html/style.css (bac1758). Verified with API, headless calc and Playwright tests on QA ledger copies.
- 2026-10-16: exec form prefers the filter fund over the last-used fund (commit 7a699ad).
- 2026-10-16: travel calculator accepts a fixed list of currencies with one rate per currency; detail JSON is v:2 and reads v:1 (commit on conf.js, README updated). Verified with a headless compute test and a Playwright run on a QA ledger copy.
- Adopted into the harness on 2026-10-16. The repository already existed (HEAD 914dcd0, branch main), so no baseline commit was made.
- Moved to `dev/CAIH_회계장부_2026` on 2026-10-16. Old-path references in `app/README.md` and `app/claude_desktop_config.ledger.json` updated.
- Harness files added: `CLAUDE.md`, `progress.md`, `ideas.md`, `scripts/check.sh`, `.claude/skills/*` (junctions to `dev/.claude/skills`), `.claude/agents/Explore.md` (copy).

## In progress

- (none)

## Open issues

- 학회 review leftovers (see report 반영 결과): form conflict reload button, leg Tab order, and the P3 list. D8 server role check is in ideas.md.
- checks: configured, pass. Only one step exists: `smoke` (dependency import check from `app/run.bat`). The project has no test, lint or typecheck command.
- Uncommitted before adoption: `QA set/` (untracked directory). Not committed by the harness.
- The `ledger` MCP registration in Claude Desktop and in `claude mcp` may still point at the old path. Re-register with the command in `app/README.md` if it fails.
- `CLAUDE.md` has no placeholders left. The `Correction rules` section is empty by design.

## Decisions

- 2026-10-16 (user) 학회 review: D1 transit nights by local date for air/sea legs, travel days stay KST; D2 detail changes need re-approval; D3 품의 preset 적요 "학회명 (장소, 시작~종료)", 참가자 in 비고; D4 국내외 default empty and required; D5 per-person note, no multiplication; D6 금액 row below 학회 detail fields in 학회 mode; D7 save allows 0, approve blocks 0; D9 terms "출장 구분", "학회 여비 산출 내역". D8 (server role check) deferred.
- 2026-10-16 (user): currency list is fixed (no free-text code); one rate input per currency in use, shown next to the USD rate; all rates are won per 1 unit (JPY hint says to divide a per-100 quote).
- `scripts/check.sh` uses the import check from `run.bat` as the only step, because no other check command exists in the project. Do not invent checks; add real ones when tests exist.
- Skills are linked with Windows junctions (`mklink /J`) and the agent file is copied, because symlinks need elevated permission here.

## Next action

Define the next task with the user (candidates: real check in scripts/check.sh — the Playwright/API scripts from this session are a good base, 신청 기타 탭 점검, LEDGER_HOST + role check). Before feature work, add at least one real check (for example an API smoke test with FastAPI TestClient against the QA dataset) to `scripts/check.sh`.
