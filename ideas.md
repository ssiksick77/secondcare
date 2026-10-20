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

- [done 2026-10-19] 적립금 단계 발주일/결제일/수령일 — 커밋 참조 (feat: deposit stages).
- [later][idea] 2026-10-20: 구글 로그인 + 담당자가 관리하는 허용 이메일 목록(첫 담당자는 app/.env) — SQLite 이전 브레인스토밍; 외부 접속 전에 필요
- [later][idea] 2026-10-20: 연구원/담당자 역할 검사 — 2026-10-16 항목과 같은 작업; 로그인 뒤에
- [later][idea] 2026-10-20: 센터 리눅스 서버 배포, 처음엔 센터 PC + 터널(Cloudflare Tunnel 등), 외부 접속 — SQLite 이전 뒤
- [later][idea] 2026-10-20: 구글 OAuth 테스트 모드 100명 한도 확인, 프로덕션 전환 시 드라이브 범위 심사 — 로그인 작업 때
- [later][idea] 2026-10-20: 드라이브 토큰을 공용 계정 하나로 할지 사용자별로 할지 — 다중 사용자 뒤
- [done 2026-10-20][fix] tests/test_api.py 의 subprocess.run(text=True) 4곳이 자식 stderr 를 cp949 로 읽어 한글이 있으면 UnicodeDecodeError 로 검사가 중단됨 (간헐) — encoding='utf-8' 지정 필요. SQLite 이전 1회차 중 발견
- [later][idea] 2026-10-20: 허용 이메일 관리 UI(설정 화면에서 추가·삭제) — 로그인 첫 버전은 .env 만; 브레인스토밍에서 미룸
- [later][idea] 2026-10-20: 다중 PC 접속: 호스트명, HTTPS, Secure 쿠키, 콘솔에 리다이렉트 URI 추가 — 로그인 첫 버전 뒤
