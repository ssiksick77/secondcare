# ideas

Features and fixes set aside for later. Append only; never delete. Change the status when an item is done or dropped.

Format: `- [status][kind] YYYY-MM-DD: <item> — <one line of context>`
Status: `later`, `done`, `dropped`
Kind: `idea` = a new feature or screen, set aside during brainstorming. `fix` = an improvement to existing code, noticed during the work loop.

Who reads what:
- `brainstorm` reads the `[later][idea]` lines.
- The session start step reads the `[later][fix]` lines and offers at most one to the user when it fits the current task.
- `wrap-up` commits this file together with `progress.md`.

<!-- Example:
- [later][idea] 2026-10-14: export to CSV — asked for during brainstorming of the report screen; not needed for the first version
- [later][fix]  2026-10-14: date parser accepts "2026/1/5" but not "2026-1-5" — noticed while editing the report screen
-->
