# progress

Updated: 2026-10-16

## Goal

Adopted into the harness; first task not defined.

## Done

- Adopted into the harness on 2026-10-16. The repository already existed (HEAD 914dcd0, branch main), so no baseline commit was made.
- Moved to `dev/CAIH_회계장부_2026` on 2026-10-16. Old-path references in `app/README.md` and `app/claude_desktop_config.ledger.json` updated.
- Harness files added: `CLAUDE.md`, `progress.md`, `ideas.md`, `scripts/check.sh`, `.claude/skills/*` (junctions to `dev/.claude/skills`), `.claude/agents/Explore.md` (copy).

## In progress

- (none)

## Open issues

- checks: configured, pass. Only one step exists: `smoke` (dependency import check from `app/run.bat`). The project has no test, lint or typecheck command.
- Uncommitted before adoption: `QA set/` (untracked directory). Not committed by the harness.
- The `ledger` MCP registration in Claude Desktop and in `claude mcp` may still point at the old path. Re-register with the command in `app/README.md` if it fails.
- `CLAUDE.md` has no placeholders left. The `Correction rules` section is empty by design.

## Decisions

- `scripts/check.sh` uses the import check from `run.bat` as the only step, because no other check command exists in the project. Do not invent checks; add real ones when tests exist.
- Skills are linked with Windows junctions (`mklink /J`) and the agent file is copied, because symlinks need elevated permission here.

## Next action

Define the first task with the user. Before feature work, add at least one real check (for example an API smoke test with FastAPI TestClient against the QA dataset) to `scripts/check.sh`.
