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
- [later][idea] 2026-10-20: OpenAI 호환 경로(ai_openai.py) 도구 호출 지원 — AI 개편 1차는 Anthropic만
- [later][idea] 2026-10-20: 영수증 추출을 별도 OCR API(OCI 등)로 교체 — 사용자가 후보 조사 중
- [later][idea] 2026-10-20: 보고서 초안에서 장부 전체 전송 제거 — report_facts 만 보내면 됨
- [later][idea] 2026-10-20: 학회 여비 계산 도구 — JS 계산기를 파이썬으로 옮기거나 Node 호출
- [later][idea] 2026-10-20: 연구비 규정·혁신법 매뉴얼 문서를 근거로 집행 질문에 답변(문서 검색) — 간단한 규정은 메모로 우선 커버
- [later][idea] 2026-10-20: 승인형 쓰기(AI 작성, 사용자 승인 시 저장, author 기록) — 제안 카드 다음 단계
- [later][idea] 2026-10-20: 정해진 업무 버튼(증빙 누락 점검, 월말 마감 체크), AI 사용량 기록
- [later][idea] 2026-10-20: 연구원용 AI 도우미를 별도 에이전트로(작은 도구 세트, 탈옥해도 할 수 있는 일이 없게) — 로그인·역할 뒤
- [later][idea] 2026-10-20: 허용 이메일 관리 UI(설정 화면에서 추가·삭제) — 로그인 첫 버전은 .env 만; 브레인스토밍에서 미룸
- [later][idea] 2026-10-20: 다중 PC 접속: 호스트명, HTTPS, Secure 쿠키, 콘솔에 리다이렉트 URI 추가 — 로그인 첫 버전 뒤
- [later][fix] 2026-10-20: /static/style.css·app.js 에 버전 쿼리(?v=) 없음 — 코드를 바꿔도 브라우저가 옛 CSS를 씀(결재란 이름 스타일이 안 보인 원인). index.html 링크에 파일 mtime 등을 붙일 것
- [done 2026-10-20][idea] 2026-10-20: 결의서 결재란 '담당' 칸에 거래별 작성자 이름 자동 기입 (9da4d04, 최초 로그인 이름 입력)(다른 이름과 같은 볼드+이탤릭) — SQLite author 열(이메일)은 있으나 이름 표가 없음. 로그인 작업에서 이메일→이름 매핑이 생기면 할 것. 로그인 전 새 행은 author 비어 있음
- [later][idea] 2026-10-20: 본인 이름 변경 UI(설정 화면) — 최초 로그인 이름 입력 첫 버전은 한 번만
- [later][idea] 2026-10-20: 변경 이력 화면에 작성자 이름 표시 — users 표가 생긴 뒤
