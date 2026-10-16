---
name: new-project
description: Create a new project directory under dev/ from _template/. Use when the user asks to start, create, or scaffold a new project, or runs /new-project.
---

# new-project

Create a new project under `dev/` from the template. Do not start feature work in this skill.

Before this skill runs, Brainstorming mode (see `dev/CLAUDE.md`) must be complete. If it is not, run it first and come back.

## Paths

Set these once at the start and use them for every path below. Do not mix relative paths.

```bash
# Walk up from the current directory until a directory holds both _template/ and .claude/skills/.
d="$(realpath "$PWD")"
while [ "$d" != "/" ] && ! { [ -d "$d/_template" ] && [ -d "$d/.claude/skills" ]; }; do
  d="$(dirname "$d")"
done
DEV="$d"
# If $DEV is "/", no dev/ root was found. Ask the user for the dev/ path.
```

This works from `dev/` itself and from any project under it. Set `NAME` and `PROJ` only after step 1 below confirms the project name:

```bash
NAME="<project name>"
PROJ="$DEV/$NAME"
```

## Steps

1. Ask the user for the project name if it is not given. Use a short, lowercase, hyphenated directory name.
2. Confirm that `$PROJ` does not exist. If it exists, stop and tell the user.
3. Copy `$DEV/_template/` to `$PROJ/`.
4. Ask the user, in one message, for the facts that fill `$PROJ/CLAUDE.md`. Do not ask again for anything Brainstorming already settled; the problem sentence is the purpose.
   - language and framework
   - package manager
   - run command, if known
   - check commands (build, test, lint), if any exist
   - visual direction and component library, if the project has a UI
   - files that must not be edited by hand
5. Fill every `<...>` placeholder in `$PROJ/CLAUDE.md` with the answers. Remove placeholder lines that do not apply. Keep the "Correction rules" section empty.
6. Fill `$PROJ/scripts/check.sh` with the check commands the user gave. Remove the example lines you do not use. Make the script executable.
   - If the user gave no check commands, leave every step commented out. The script then fails with "No checks configured". That failure is the correct state at this point. Do not add a placeholder step to make it pass.
7. Run `$PROJ/scripts/check.sh` once and record the result:
   - Checks configured and passed → note "checks: configured, pass" for `progress.md`.
   - Checks configured and failed → fix the script only if the error is in the script (a typo, a wrong path). If the project code is missing, note the failure for `progress.md`.
   - "No checks configured" → note "checks: not configured" for `progress.md`.
8. Link the shared skills and agents into the project so Claude Code finds them from inside `$PROJ`:
   ```bash
   mkdir -p "$PROJ/.claude/skills" "$PROJ/.claude/agents"
   for d in "$DEV"/.claude/skills/*/; do
     ln -s "$(realpath "$d")" "$PROJ/.claude/skills/$(basename "$d")"
   done
   for f in "$DEV"/.claude/agents/*.md; do
     ln -s "$(realpath "$f")" "$PROJ/.claude/agents/$(basename "$f")"
   done
   ```
   On Windows without symlink permission, use `mklink /J` (junction) for each skill directory and copy each agent file instead.
9. Fill `$PROJ/progress.md` and `$PROJ/ideas.md`:
   - Updated: today's date.
   - Goal: the problem sentence from Brainstorming.
   - In progress: the first-version features with their done conditions, from Brainstorming.
   - Open issues: the check result from step 7. If checks are not configured, write "checks: not configured. Add at least one step to scripts/check.sh before feature work."
   - Next action: "Add the first check to scripts/check.sh" when checks are not configured; otherwise the first feature from the list.
   - `ideas.md`: append the "later" list from Brainstorming.
10. Run `git init` in `$PROJ`. Stage the template files and the skill and agent links. Commit with the message `chore: scaffold project from template`.
11. Report to the user: the project path, the check result, the linked skills and agents, and the next action.
