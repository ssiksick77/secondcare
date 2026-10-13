---
target: static/index.html (회계대장 + /labor)
total_score: 28
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:C:\\Users\\parkj\\Desktop\\Project\\01 in progress\\CAIH_회계장부_2026\\app\\static\\index.html"
target_fingerprint: "sha256:81910d8e3b927670c50b05ef0a922cab4cd4658ac70ff6ff48afa89215d386a7"
target_path: "C:\\Users\\parkj\\Desktop\\Project\\01 in progress\\CAIH_회계장부_2026\\app\\static\\index.html"
timestamp: 2026-10-13T15-04-39Z
slug: static-index-html
---
Method: dual-agent (A: design review sub-agent · B: detector/browser sub-agent)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | 상태 점·타일·토스트는 좋음. 전역 오류 배너가 모든 탭에 떠 붉은색을 무디게 함 |
| 2 | Match System / Real World | 4 | 품의·집행·적립·귀속월·지급월 등 담당자 용어 그대로, 괘선지 은유 |
| 3 | User Control and Freedom | 2 | 삭제 되돌리기 없음(백업 파일 수동 복사 안내). 드로어 열면 금액 열이 화면 밖으로 |
| 4 | Consistency and Standards | 2 | 계획표 '부족' 붉은색, 네이티브 confirm/prompt, month 입력 미스타일, 설정 저장 버튼 2개 |
| 5 | Error Prevention | 3 | 더티 확인·연결 행 잠금·증빙 차단·잔액 경고 강함. 전월 복사 월 입력이 자유 텍스트 prompt |
| 6 | Recognition Rather Than Recall | 3 | 계획표 범례가 표 아래, 대시보드 정의문이 300자 한 줄 |
| 7 | Flexibility and Efficiency | 3 | Enter/Ctrl+Enter/저장 후 계속/날짜 버튼. 행 키보드 이동·집행 추가 단축키·월 일괄 확정 없음 |
| 8 | Aesthetic and Minimalist Design | 3 | 절제됐으나 집행 행마다 인라인 버튼 4~5개 |
| 9 | Error Recovery | 2 | 메시지는 구체적이나 실수 삭제 복구가 파일 조작 |
| 10 | Help and Documentation | 3 | 문맥 안내는 있으나 빽빽하고 구조 없음 |
| **Total** | | **28/40** | **양호(Good)** |

## Design Specificity Verdict
- LLM: 이 제품만의 것. 금액 열 왼쪽 남색 마진선, 이중선 합계, 한 줄 괘선 요약 띠, 점+글자 상태, 아이콘 거의 없음. 내용을 지워도 괘선 격자로 앱을 알아볼 수 있음. 일반형으로 되돌아가는 지점: 네이티브 confirm/prompt, 영문 "Choose Files", 미스타일 month 입력, 예산 미입력 시 붉은 숫자의 벽, 일반 관리폼 같은 설정 대화상자.
- 검출기(CLI): 1건 advisory(design-system-color: index.html의 border-top rgb(0,0,0), 줄 번호 없음 → 인쇄 규칙의 검정 선으로 추정, 화면 영향 없음).
- 브라우저 검출(headless, 사용자 가시 오버레이 없음): `/`·대시보드 flat-type-hierarchy(body 13 / h2 13 / h1 15, 단계 1.15:1) — 의도된 밀도, 수용. `/labor` low-contrast 2건(#8A919C 글자: 흰 바탕 3.2:1, 머리 배경 2.8:1) — 계획표 보조 글자·재직 아님 칸의 실제 AA 미달.
- 일치: A가 지적한 보조 글자 대비 문제를 검출기도 잡음. 검출기가 잡고 A가 놓친 것: 없음(타입 단계는 의도). 거짓 양성: rgb(0,0,0) 인쇄 선.

## Overall Impression
서명이 분명한 장부 도구. 데이터 무결성 가드와 키보드 입력 리듬이 강점. 가장 큰 기회는 "불안한 순간"의 UI다: 삭제·확정 취소가 네이티브 confirm이고 되돌리기가 파일 복사 안내이며, 예산이 없을 때 대시보드가 붉은 음수로 센터장을 놀라게 한다.

## What's Working
1. 마진선·이중선·괘선 띠가 /labor까지 모든 표에 일관 적용된 시각 서명.
2. 연결 행 잠금, 증빙 있으면 삭제 차단, expect 동시성 검사, 잔액 경고, 확정 창의 결과 설명 등 무결성 중심 가드.
3. Enter 이동·Ctrl+Enter 저장·저장 후 계속·청구일/완료일 오늘 버튼의 키보드 우선 입력 흐름.

## Priority Issues
- [P1] 집행 드로어가 금액 열을 가림. body.drawer-open main padding-right(min(580px,45vw))로 표가 눌려 금액·예산목 잔액·태그가 스크롤 밖, 고정된 작업 열만 남음. 영수증과 대조할 숫자를 잃음. 수정: 드로어 열림 시 날짜 버튼·재원 열 접기 또는 거래번호·금액 좌측 고정, 최소한 .amt 유지. (/impeccable layout)
- [P1] 삭제·확정 취소가 네이티브 confirm, 되돌리기 없음. 가장 불안한 순간이 가장 덜 설계됨. 수정: 행·금액·연결 행을 보여주는 스타일 대화상자(버튼에 동사), 저장마다 이미 생기는 백업을 이용한 "되돌리기" 토스트. (/impeccable harden)
- [P1] 예산 미입력 시 대시보드가 큰 붉은 음수로 과경보. "예산 없음"은 작은 회색. 300자 정의문이 유일한 설명. 수정: 예산 0이면 "예산 미입력"(ink-2), 정의문은 접이식 "집계 기준" 또는 열 머리 툴팁. (/impeccable clarify)
- [P2] 전역 수식 오류 배너가 모든 탭에 상시 노출(인건비 포함). 수정: 헤더 한 줄 상태로 축약, 집행내역에서만 전체 표시. (/impeccable quieter)
- [P2] 시스템 밖 컨트롤: input[type=month] 미스타일, 영문 파일 버튼, /labor의 흐린 파랑 비활성 AI 버튼, 계획표 '부족' 붉은색(붉은색=경고 규칙 위반), 보조 글자 #8A919C 대비 미달. 수정: month 입력 규칙 추가, 숨은 input + "파일 선택" 버튼, 부족은 ink-2/warn, ink-3 글자용 #6B7380. (/impeccable polish)
- [P3] 계획표 범례를 표 위 안내 줄로, "인건비 관리" 라벨을 탭과 구분, 설정 저장 버튼 하나로 통합. (/impeccable clarify)

## Persona Red Flags
- Alex(숙련자): 행 ↑↓ 이동 없음, 집행 추가 단축키 없음, 지급 원장 예정 21건을 하나씩 확정, Ctrl+Enter 안내가 폼 안에만.
- Jordan(초심자): 첫 화면이 붉은 배너와 붉은 음수. 예정/확정·귀속월/지급월 구분이 회색 빽빽한 안내에만. 계획표 칸의 클릭 가능성이 범례 글자 외엔 드러나지 않음.
- 센터장(대시보드 열람): 숫자가 정의문 아래 묻히고 예산 미입력 시 붉은 음수. 차트는 만원, 표는 원. 기준일이 헤더 파일 시각에만. 인쇄 미검증.

## Minor Observations
- 품의 상태 '집행완료'가 초록이라 "잘 끝남"으로 읽힘(실제는 전환됨).
- 확정/확정 취소 버튼의 결과 설명이 title 툴팁에만 있어 터치·키보드 사용자는 못 봄.
- 푸터의 전체 장부 경로가 모든 화면에 노출(센터장에게 보여줄 때 소음·사생활).
- 계획표가 1440에서 우측 열이 잘리는데 넘침 힌트가 약함.
- 설정 대화상자가 fieldset(드라이브)과 맨 문단 제목(AI)을 섞음.

## Questions to Consider
1. 센터장은 아무것도 편집하지 않는다. 버튼·배너·수식 없는 읽기 전용 "월 보고" 화면을 따로 줘야 하지 않나?
2. 드로어에 이미 "다음 처리"가 있는데 왜 청구일=오늘·완료일=오늘 버튼이 모든 행에도 있나? 표는 읽는 장부인가, 조작판인가?
3. xlsx가 DB이고 저장마다 백업이 생기는데, 왜 "되돌리기"가 파일 복사 안내이지 제품의 가장 눈에 띄는 안전장치가 아닌가?
