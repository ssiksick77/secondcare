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
- [later][idea] 2026-10-16: 연구원/담당자 역할을 서버가 검사 — 학회 탭 점검 D8, 사용자가 보류. LEDGER_HOST(타 PC 접속) 과제와 함께 다룰 것

- [예약, 2026-10-19 사용자] 적립금도 날짜로 상태 관리: 발주일/결제일/수령일. 적립금 증빙 작업이 끝난 뒤 착수, 단계별 질문으로 범위 확정(상태 이름·전환 규칙·주문 생성 행과의 관계·표 표시).
