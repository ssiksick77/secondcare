---
name: brainstorm
description: Turn an idea into a checkable request before any code is written. Use at the start of a new project, when a task adds a new screen, command, or data structure, when the user runs /brainstorm or asks to brainstorm, or when the user agrees to brainstorm an idea-level remark. Entry rules are in dev/CLAUDE.md.
---

# brainstorm

Brainstorming turns an idea into a request. The "Clarify the request" step in `dev/CLAUDE.md` removes guesses from a request that already exists. When this skill runs, it replaces that step.

## Rules in the mode

- Read the `[later][idea]` lines in `ideas.md` first, when the file exists. Bring up the ones that relate to the current topic.

- Do not write code and do not commit. The only files you may edit are `progress.md` and `ideas.md`.
- Start from the problem: what is inconvenient now, and how does the user do it today? If the user already explained this, restate it in one line instead of asking again. Discuss solutions only after that.
- Widen, then narrow. Offer two or three different approaches with their trade-offs. When the user picks one or combines them, narrow the details in that direction.
- Cut the scope. Split the feature list into "first version" and "later". Keep the first version small enough to finish in one session.
- Make each feature checkable. For every first-version feature, write one line: how we know it is done. If that line cannot be written, the feature is still unclear; ask more.
- Ask step by step: one question, or a small related set, per message. Ask only when the answer changes the scope or a done condition. Decide the rest yourself and say so.

## Leave the mode

Leave when all three exist and the user confirms them:
- the problem, in one sentence,
- the first-version feature list, each with its done condition,
- the "later" list.

Then record:
- `progress.md`: Goal = the problem sentence. In progress = the first-version features with their done conditions. Decisions = the chosen approach and why. If the Goal changed, clear the old Done section (see `wrap-up`).
- `ideas.md`: append every "later" item as a `[later][idea]` line with the date and one line of context. Never delete from this file; change the status to `done` or `dropped` instead.

Then branch:
- New project: the project directory does not exist yet. Keep the three results in the conversation and run the skill `new-project`, which writes them.
- Existing project: write the records above, then start the work loop directly.

Do not repeat the Clarify step in either case.
