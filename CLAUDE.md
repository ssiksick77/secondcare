# CAIH_회계장부_2026

The shared rules in `../CLAUDE.md` apply here. This file holds the facts of this project only.

## Purpose

A local, single-user web app for the research-fund accountant of the 분당서울대병원 의료인공지능센터. It manages spending (집행, 품의, 예산변동, 적립금, 인건비, 신청) across several funding sources in one Excel ledger, which stays the source of truth. Evidence files go to Google Drive. An optional AI helper only suggests, and an MCP server exposes the ledger to Claude.

## Stack and structure

- Language / framework: Python 3.10+ with FastAPI and uvicorn; frontend is plain HTML/JS/CSS with no framework and no build step; openpyxl reads and writes the xlsx data store
- Package manager: pip (`app/requirements.txt`, installed by `app/setup.bat`)
- Directories:
  - `app/` — the application: `main.py` (FastAPI routes `/`, `/labor`, `/request`), `store.py` (xlsx read/write and validation), `ai.py` / `ai_openai.py` (AI helper), `drive.py` (Google Drive uploads), `mcp_server.py` (MCP server), `settings.py`, `.bat` launchers, README/PRODUCT/DESIGN docs
  - `app/static/` — frontend: `index.html`, `app.js`, `labor.js`, `edit.js`, `request.js`, `conf.js`, `style.css`
  - `app/.impeccable/` — state of the impeccable design tool (design.json, critiques, mocks, review screenshots)
  - `app/backup/` — automatic pre-save xlsx backups (gitignored)
  - `docs/` — Korean design, review and QA documents
  - `docs/qa_data_2026_01_09/` — synthetic QA dataset (QA26JANSEP) with build/install/supplement scripts
  - `QA set/` — QA hand-off copy: checklist, results, evidence, one-off evidence scripts
  - `rawdata/` — source spreadsheet the ledger was derived from
  - `ref/` — reference material and HTML prototypes
  - `의료인공지능센터_지출장부_2026.xlsx` — the live ledger (gitignored)

## Commands

- Run: `app\run.bat` (runs `python main.py` in `app/`, opens http://127.0.0.1:8791; port from `LEDGER_PORT`)
- Run against QA data: `app\run_qa.bat` (sets `LEDGER_XLSX`, `LEDGER_ENV`, `LEDGER_DRIVE_MOCK=1`, port 8792)
- Check: `scripts/check.sh` (runs: smoke — dependency import check; test — `tests/run.py`: node calculator test, API test, Playwright UI test, all against a QA ledger copy in `tests/.tmp/`; about 1 minute)
- Other: `python -I tests/run.py calc` — run one test group (`calc`, `api`, `db`, `ui`)
- Other: `python app/import_xlsx.py <ledger.xlsx> <ledger.sqlite> [--author email] [--force]` — one-shot xlsx → SQLite import (migration, 2026-10-20). `LEDGER_DB=<path>` makes `store.read_all` read SQLite; writes still go to xlsx until session 2
- Other: `app\run_mcp.bat` — starts `mcp_server.py` for Claude Desktop / Claude Code (not for double-click)
- Other: `python docs/qa_data_2026_01_09/supplement_v11.py` — idempotent QA fixture supplement; needs `LEDGER_XLSX`, `LEDGER_ENV`, `LEDGER_DRIVE_MOCK=1`
- Other: `python docs/qa_data_2026_01_09/write_checklist_results.py <runner_output.txt>` — writes QA results into the checklist docs

## Commit rule

Write commit messages in short English. First line: `<type>: <summary>` under 50 characters. Types: feat, fix, refactor, docs, chore, wip. Use `wip` only when `scripts/check.sh` did not pass; name the failing step in the body. For other types, add a body only when the reason is not clear from the summary.

## Design

- Visual direction: columnar ledger pad (회계 괘선지) — see `app/DESIGN.md`: one typeface (Pretendard GOV + system), ink-and-gray tone, 28px rule rows, navy margin line, double rule under totals, 2px corners, flat surfaces, color only for meaning (red alert, blue function, green done)
- Component library: none (vanilla HTML/JS/CSS, no CDN)
- Colors and fonts: as defined in `app/DESIGN.md` and `app/.impeccable/design.json`
- Project-specific UI rules: KRDS is a reference only, not binding (see `app/PRODUCT.md`)

## Do not

- Do not edit or commit `app/.env`, `app/google_client_secret.json`, `app/google_token.json`, `docs/qa_data_2026_01_09/qa.env` — secrets
- Do not hand-edit `app/drive_folders.json`, `app/backup/`, `app/__pycache__/`, `app/.impeccable/hook.cache.json`, `docs/qa_data_2026_01_09/qa_drive_mock/`, `docs/qa_data_2026_01_09/build_backups/` — local state
- Do not open or modify `의료인공지능센터_지출장부_2026.xlsx` or any `*.xlsx` from code changes; it is the live ledger and is gitignored. Use `app\run_qa.bat` and the QA dataset for manual testing. Automated tests use `tests/_env.py` (copies the QA ledger to `tests/.tmp/`, free port, `LEDGER_NO_BROWSER=1`); write new tests the same way
- Do not run `docs/qa_data_2026_01_09/install_fixture.py` without approval; it writes over the active ledger
- Do not run `docs/qa_data_2026_01_09/revalidate_fixture.py`; it is a one-time V1 migration
- Do not call Google Drive or the AI APIs (Anthropic, OpenAI) in checks without approval; use `LEDGER_DRIVE_MOCK=1`

## Correction rules

<!-- Add one rule per line. Format: - YYYY-MM-DD: rule -->
