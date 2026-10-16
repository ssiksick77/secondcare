---
name: adopt-project
description: Bring an existing codebase under the dev/ harness without changing its code. Use when the user points at a directory that already has files (inside dev/ or elsewhere) and asks to add it as a project, set it up, or bring it into dev/. For an empty new project use new-project instead.
---

# adopt-project

Add the harness files to a project that already exists. Do not change the project's code, and do not lose any work that is already there. Brainstorming is not required; the project already has a direction.

## Paths

Find the dev/ root the same way as `new-project` (walk up from the current directory until a directory holds both `_template/` and `.claude/skills/`). Then set:

```bash
SRC="<the directory the user named>"          # where the files are now
NAME="$(basename "$SRC")"                      # or a name the user gives
PROJ="$DEV/$NAME"
```

## Steps

1. Confirm `$SRC` exists and holds files. If it is empty, stop and tell the user to use `new-project`.
2. If `$SRC` is not under `$DEV`, ask the user once: move it to `$PROJ`, or leave it where it is? If it stays outside `dev/`, `$PROJ` is `$SRC`, and `dev/CLAUDE.md` does not apply there automatically. Tell the user that the shared rules then live only in the links you create in step 7.
3. Secure the existing work before you add anything:
   - If `$PROJ` is not a git repository: run `git init`, stage everything, and commit with the message `chore: baseline before harness`. This commit records the user's work exactly as found. Do not run checks first; there are none yet.
   - If `$PROJ` is a git repository with a clean tree: do nothing.
   - If `$PROJ` is a git repository with uncommitted changes: do not commit them. Record the changed files for `progress.md` ("uncommitted before adoption") and continue. The harness files you add in step 5 go in their own commit.
4. Map the project with the `Explore` agent. Ask it for: language and framework, package manager, the directory layout with one line per directory, the entry point, and every check-like command it finds (in `package.json` scripts, `pyproject.toml`, `Makefile`, `justfile`, CI config, or a README). Read only the files it names.
5. Add the harness files. Never overwrite a file that exists:
   - `CLAUDE.md` missing → copy `_template/CLAUDE.md` and fill it from step 4. Leave `<...>` placeholders only where the map gave no answer.
   - `CLAUDE.md` exists → keep it. Append the template sections it lacks (`Commands`, `Commit rule`, `Design`, `Do not`, `Correction rules`), filled from step 4. Do not reorder or rewrite existing text.
   - `progress.md`, `ideas.md` missing → copy from `_template/`.
   - `scripts/check.sh` missing → copy from `_template/` and fill it with the check commands found in step 4, as `run_step` lines. Do not invent commands. If none were found, leave every step commented out; the script then fails with "No checks configured", which is the correct state.
   - `scripts/check.sh` exists → keep it. Tell the user what the template version adds (the no-checks guard, `run_step`) and let them decide.
6. Run `scripts/check.sh` once and record the result as `new-project` step 7 does. A failing check is information, not something to fix in this skill.
7. Link the shared skills and agents into `$PROJ/.claude/`, as `new-project` step 8 does.
8. Ask the user one question: what is the next task? Use the answer as the Goal. If they do not know yet, set the Goal to "Adopted into the harness; first task not defined" and the Next action to "Define the first task with the user".
9. Fill `progress.md`:
   - Updated: today's date.
   - Goal: from step 8.
   - Done: "Adopted into the harness" with the baseline commit hash from step 3, if one was made.
   - Open issues: the check result from step 6; uncommitted files from step 3, if any; every placeholder still left in `CLAUDE.md`.
   - Next action: "Add the first check to scripts/check.sh" when checks are not configured; otherwise the first step of the Goal.
10. Commit only the files this skill added or changed (`CLAUDE.md`, `progress.md`, `ideas.md`, `scripts/check.sh`, `.claude/`), staged by name, with the message `chore: add harness files`. Do not stage the user's uncommitted changes from step 3.
11. Report to the user: the project path, the baseline commit if made, the check result, the placeholders left in `CLAUDE.md`, and the next action.
