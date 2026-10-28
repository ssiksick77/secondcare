# ideas

Features and fixes set aside for later. Append only; never delete. Change the status when an item is done or dropped.

Format: `- [status][kind] YYYY-MM-DD: <item> — <one line of context>`
Status: `later`, `done`, `dropped`
Kind: `idea` = a new feature or screen, set aside during brainstorming. `fix` = an improvement to existing code, noticed during the work loop. `sec` = a confirmed finding from a security audit; fix before `fix` items.

Who reads what:
- `brainstorm` reads the `[later][idea]` lines.
- The session start step reads the `[later][fix]` lines and offers at most one to the user when it fits the current task.
- The session start step also lists `[later][sec]` lines. Offer one of these before any `[later][fix]`.
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
- [done][idea] 2026-10-20: 허용 이메일 관리 UI(설정 화면에서 추가·삭제) — 2026-10-20 브레인스토밍 후 착수 (users 표 저장, 마스터만 조작)
- [later][idea] 2026-10-20: OpenAI 호환 경로(ai_openai.py) 도구 호출 지원 — AI 개편 1차는 Anthropic만
- [later][idea] 2026-10-20: 영수증 추출을 별도 OCR API(OCI 등)로 교체 — 사용자가 후보 조사 중
- [later][idea] 2026-10-20: 보고서 초안에서 장부 전체 전송 제거 — report_facts 만 보내면 됨
- [later][idea] 2026-10-20: 학회 여비 계산 도구 — JS 계산기를 파이썬으로 옮기거나 Node 호출
- [later][idea] 2026-10-20: 연구비 규정·혁신법 매뉴얼 문서를 근거로 집행 질문에 답변(문서 검색) — 간단한 규정은 메모로 우선 커버
- [later][idea] 2026-10-20: 승인형 쓰기(AI 작성, 사용자 승인 시 저장, author 기록) — 제안 카드 다음 단계
- [later][idea] 2026-10-20: 정해진 업무 버튼(증빙 누락 점검, 월말 마감 체크), AI 사용량 기록
- [later][idea] 2026-10-20: 연구원용 AI 도우미를 별도 에이전트로(작은 도구 세트, 탈옥해도 할 수 있는 일이 없게) — 로그인·역할 뒤
- [later][idea] 2026-10-20: 다중 PC 접속: 호스트명, HTTPS, Secure 쿠키, 콘솔에 리다이렉트 URI 추가 — 로그인 첫 버전 뒤
- [done 2026-10-20] /static/style.css·app.js 에 버전 쿼리(?v=) 없음 — 코드를 바꿔도 브라우저가 옛 CSS를 씀(결재란 이름 스타일이 안 보인 원인). index.html 링크에 파일 mtime 등을 붙일 것
- [done 2026-10-20][idea] 2026-10-20: 결의서 결재란 '담당' 칸에 거래별 작성자 이름 자동 기입 (9da4d04, 최초 로그인 이름 입력)(다른 이름과 같은 볼드+이탤릭) — SQLite author 열(이메일)은 있으나 이름 표가 없음. 로그인 작업에서 이메일→이름 매핑이 생기면 할 것. 로그인 전 새 행은 author 비어 있음
- [later][idea] 2026-10-20: 본인 이름 변경 UI(설정 화면) — 최초 로그인 이름 입력 첫 버전은 한 번만
- [later][idea] 2026-10-20: 변경 이력 화면에 작성자 이름 표시 — users 표가 생긴 뒤
- [later][idea] 2026-10-20: 채팅방 검색·정렬·내보내기 — 채팅방 1차 뒤
- [later][idea] 2026-10-20: 부적절한 사용 감지 + 마스터 계정 전송 로직 — 1차는 고지문만
- [later][idea] 2026-10-20: 연구원용 에이전트가 같은 채팅 저장소를 쓰도록 — 역할 뒤
- [later][idea] 2026-10-20: users 표에 역할 열(연구원/담당자) + 서버 역할 검사 — 허용 이메일 관리 브레인스토밍; 2026-10-16·10-20 역할 항목과 같은 작업
- [later][idea] 2026-10-20: 마스터 지정을 users 표로 옮겨 .env 의존 제거 — 허용 이메일 관리 첫 버전은 .env 계정만 마스터
- [later][idea] 2026-10-20: 담당자가 타인 이름 수정 (본인 이름 변경 UI와 함께) — 허용 이메일 관리 브레인스토밍
- [later][idea] 2026-10-20: 별도 /users 페이지: 초대 메일, 비활성 사유, 마지막 로그인 시각 — 허용 이메일 관리 첫 버전은 설정 다이얼로그 안 fieldset
- [later][idea] 2026-10-20: 허용 계정의 권한·이름 수정 UI (지금은 삭제 후 다시 추가) — 허용 계정 화면 랩업
- [later][idea] 2026-10-20: 사용자 직책(title) 표시 필드 — 권한 설계 문서 6절, 표시용이라 미룸
- [later][idea] 2026-10-20: side panel purpose (candidates: month-end to-do list of 미승인·품의대기, recent change log, fund summary); request-screen panel content for researchers — two-column frame brainstorming, first version shows a placeholder
- [later][idea] 2026-10-20: variable panel width that absorbs spare width on large monitors (mock variant 3) — two-column frame brainstorming
- [later][idea] 2026-10-20: dashboard critique P2-P5: aggregation-basis labels in summary line and headers, tag subtab toolbar (note, month, CSV of the active table), remove the table scroll box and fold item rows under fund subtotals, card denominator text and drilldown, chart as single ink bars + cumulative line + n/12 pace line — see app/.impeccable/critique/2026-10-20T10-29-26Z__app-static-index-html.md; revisit after the frame
- [later][idea] 2026-10-20: user-draggable panel width — two-column frame brainstorming
- [later][idea] 2026-10-20: MSRI dashboard card: definition pending (user: 추후 설명) — KPI card row keeps a placeholder
- [later][idea] 2026-10-20: copy 원인발생일 into empty 지출예정일 for existing 품의 rows (one-shot) — the screen falls back to 원인발생일 for now
- [later][idea] 2026-10-20: year select in the header should switch the referenced ledger (DB) per year, not only filter — user remark while moving the year select
- [later][idea] 2026-10-21: 근태변동관리 화면 (연차·재택 관리) as a fourth screen; 연구원 use it too. Entry: everyone goes to /enter after login and /enter shows only the buttons the role allows — user, during the terms discussion
- [later][idea] 2026-10-21: rename code identifiers to the terms in CLAUDE.md: `#side` → sidebar, `.drawer` → panel, `#main-tabs` → fund tabs, and consider `labor` → `payroll` (keep the /labor path) — user: later, together
- [later][idea] 2026-10-21: column hide + stub system for the 인건비 and 신청 screen tables (first version covers the 연구비 screen only) — column-hide brainstorming
- [later][idea] 2026-10-21: 연구비 critique P4 toolbar fixed layout (filters left, 합계·CSV·추가 right), 적립 top two tables 50vh height review, 상태 ✓ undo in the list — app/.impeccable/critique/2026-10-20T13-45-39Z__localhost-fund.md
