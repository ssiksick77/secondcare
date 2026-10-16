---
name: wrap-up
description: Commit the task's changes and update progress.md so the next session can resume. Use when a blocker stops the work, when the user ends the session or asks to wrap up or save progress, when the user runs /wrap-up, or when the user answers yes to "Update progress.md now?".
---

# wrap-up

Leave the project in a state that a new session can resume from `progress.md` alone. The order matters: commit code first, then write the record with the commit hash, then commit the record.

## Steps

1. Run `scripts/check.sh`. Note the result (pass, fail with the failing step, or "No checks configured"). Do not fix failures in this skill; record them.
2. Run `git status`, `git diff --stat`, and `git diff --cached --stat`. Separate the changes into two groups:
   - changes made by this task,
   - changes that were already there when the session started, unstaged or staged (see the note taken at session start).
3. Commit the task's changes only. Leave `progress.md` and `ideas.md` out of this commit.
   - Stage the task's files by name. Run `git diff --cached` and read the whole diff. Every change in it must be from this task.
   - If the diff holds a change from the other group and you cannot split it safely, do not commit. Record in step 5 which changes are waiting and why.
   - If the check passed, use the commit rule in `<project>/CLAUDE.md`.
   - If the check failed or no checks are configured, use the prefix `wip:` and name the failing step, or "no checks configured", in the body.
   - If this task has no uncommitted changes (the work loop already committed them), skip this step.
4. Note the hash to reference: the commit from step 3, or, if step 3 was skipped, the latest commit from this task in `git log`.
5. Rewrite `progress.md`. Follow the writing rules in `dev/CLAUDE.md`:
   - Updated: today's date.
   - Goal: the current task. Keep it if it did not change.
   - Done: finished steps, each with the commit hash from step 4 or an earlier hash. Keep only the steps since the current Goal started. When the Goal changes, clear the old Done section; `git log` holds the history.
   - In progress: started steps that are not complete.
   - Open issues: the check result from step 1, blockers, uncertainties. Say what is missing. If files from before the session are still uncommitted, list them here.
   - Decisions: choices that affect later work, with the reason.
   - Next action: one concrete step.
6. If `progress.md` or `ideas.md` changed, commit them together with the message `docs: update progress`. If neither changed, skip the commit.
7. Report to the user in three lines: the check result, the commits made (hashes), and the next action.
