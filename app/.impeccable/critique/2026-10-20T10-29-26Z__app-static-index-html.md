---
target: "대시보드 (app/static/index.html #panel-dash)"
total_score: 26
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 5
target_identity: "file:C:\\Users\\parkj\\Desktop\\Project\\dev\\CAIH_회계장부_2026\\.claude\\worktrees\\dashboard-ui-improvement-4f9f95\\app\\static\\index.html"
target_fingerprint: "sha256:4fead5ca2b2d07c0969310894bfd7d143c0add100b1cdb184cc508a4020c247c"
target_path: "C:\\Users\\parkj\\Desktop\\Project\\dev\\CAIH_회계장부_2026\\.claude\\worktrees\\dashboard-ui-improvement-4f9f95\\app\\static\\index.html"
timestamp: 2026-10-20T10-29-26Z
slug: app-static-index-html
---
# 대시보드 critique 2026-10-20 (dual-agent)

## 휴리스틱 점수 26/40
1 상태 가시성 3 · 2 현실 일치 3 · 3 통제 2 · 4 일관성 2 · 5 오류 예방 3 · 6 재인 2 · 7 효율 2 · 8 미학 3 · 9 복구 3 · 10 도움말 3

## 디자인 특정성
장부(괘선 요약 띠, 남색 이중선·마진선, 화면의 집계 기준·태그 조정식)는 특정적. 월별 집행 추이 차트(재원 9색 누적 막대)는 범용적이며 예산선이 숨어 결론이 없음. 카드 4px 집행률 막대는 2~8%에서 보이지 않음.
디텍터: CLI advisory 2 (low-contrast #6B7380/#EEF0F3 4.2:1, border-top #000), in-page tiny-text 10px SVG 차트 캡션, flat-type-hierarchy(의도). 표 4개 caption/aria-label 없음.

## 우선 문제
- P1 가로로 늘려진 구성(사용자 지적): 카드 auto-fill minmax(200px) → 6+5/7+4, 표 전폭 9열, 차트 3fr + 적립금 표 96px. 제안: 본문 최대 폭 ~1280px, 카드 6열 고정, 표 width auto + 숫자 열 고정 폭, 차트 고정 폭 + 적립금·대기 목록 묶음.
- P2 집계 기준 세 가지 혼재(카드·집행률 전체 / 집행액 필터 / 품의대기 날짜 무관). 제안: 라벨에 기준 표기, 요약 줄 두 묶음, 집계 기준 한 줄당 정의 1개.
- P3 태그 서브탭에서 툴바(요약 줄·월·CSV)가 예산 보기의 것. 제안: 서브탭별 요약 줄, 월 비활성 또는 적용, CSV 활성 표 저장.
- P4 표 이중 스크롤(max-height 510px), 0 행 절반. 제안: 대시보드 표 박스 스크롤 제거, 소계 기본 + 재원 행 펼치기, 0은 -.
- P5 카드 분모 title 전용, 드릴다운 없음, 차트 결론 없음. 제안: 보조 줄 "집행 a / b · %", 카드 → 집행내역 예산목 필터 버튼, 차트 먹색 단일 막대 + 누적선 + n/12 기대선.

## 페르소나 레드플래그
회계 담당자: 태그 보기 CSV 오저장, "미승인" 용어, 남은 일 목록 없음. 센터장: 카드 숫자 비슷해 우선순위 없음, 표 100행+ 소계만 보기 없음, 차트 범례 9색.

## 사소한 관찰
1366px 요약 줄 2줄(툴바 68px); SVG 9~10px; 빈 달 vs 0 달 동일; 적립금 10곳 제한 링크 없음; 태그×월 표 1366px 꽉 참; defs summary 12px 묻힘; "0.0%" 반복; 표 caption 없음.

## 도발적 질문
1 첫 줄은 가용잔액이 아니라 기대 집행 대비 편차? 2 카드 축 토글(재원별|예산목별)이 예산|태그 서브탭보다 먼저? 3 "월말 결산 장부 1쪽"으로 재정의하면 차트 빠지고 미승인·품의대기 목록 들어오는가?
