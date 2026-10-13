---
version: 1
slug: "static-index-html"
primary_target: "static/index.html"
related_targets: ["static/app.js","static/style.css"]
---

# Surface brief: static/index.html (센터 회계대장 관리도구 전체 화면)

Scope: Operate. 회계 담당자가 매일 쓰는 단일 페이지 앱의 전 화면(대시보드·집행내역·품의·예산변동·적립금·태그·재원·입력 대화상자·상세 드로어·설정·AI 패널·토스트). 노트북 1366~1536과 모니터 1920 모두 대상, 모바일은 비대상.

Audience/job: 집행·품의·적립금 입력, 단계 처리, 증빙 업로드, 월 마감 자료. 센터장·PI는 대시보드 열람·인쇄. 연구원은 조회.

Constraints: 레이아웃·탭·용어·버튼 동작·키보드 흐름 유지. 애니메이션은 150ms 이하 상태 전환만. 외부 CDN 금지, 시스템 폰트. 접근성 AA, 포커스 가시성, 44px 클릭 영역(표 안 인라인 버튼은 28px 높이 허용하되 행 전체가 클릭 대상). 다크 모드 없음. 사용자 결정: 행 높이 30px 고정, "예산목 잔액" 열을 집행내역 기본 열로, 재원은 코드 글자로만 구분(재원색 없음).

## Direction contract

THESIS: 회계 담당자가 손으로 써 온 컬럼너 패드의 규율을 화면에 옮긴다. 금액과 잔액은 남색 마진 괘선 오른쪽, 항상 같은 자리에 있고, 합계는 이중선 아래 있다. 이 범주의 기본 배치(흰 카드·회색 보더·둥근 배지가 떠다니는 SaaS 어드민)를 거부하고, 표가 화면의 주인이 되는 괘선 밀도를 택한다.

OWN-WORLD: 흰 바탕 #FFFFFF, 표 안 바탕 #FAFBFC, 회색 괘선 #D7DBE0, 표 머리 #EEF0F3, 남색 마진 괘선·이중선 #1F3A93, 먹색 글자 #1E2124, 보조 글자 #5A6270. 붉은색 #B3261E는 보완필요·음수·오류 전용. 기능색 파랑 #246BEB는 기본 버튼·포커스·선택·청구중. 완료 #1A7F37, 미청구 #6B7280. 한 서체(Pretendard GOV → Pretendard → Malgun Gothic), 13px 본문, 12px 보조, 표형 숫자 우측 정렬. 행 30px, 셀 여백 6×10. 모서리 2px, 그림자 없음(드로어·대화상자만 1단 그림자). 콘텐츠를 모두 지워도 남색 세로선·이중선·회색 괘선 격자로 알아볼 수 있다.

STORY: 들어오면 표가 바로 보이고, 한 행에서 거래번호·상태·금액·예산목 잔액·증빙 수를 읽는다. 붉은 것은 보완필요와 음수뿐이므로 눈이 그리로 간다. 입력은 거래처에서 시작해 Enter로 내려가고, 저장하면 토스트에 거래번호가 뜬다. 센터장은 대시보드의 소계 이중선 행만 읽어도 재원별 잔액을 안다.

FIRST VIEWPORT (집행내역 탭, 1440×900): 상단 56px 흰 헤더(제목·파일 상태·AI·새로고침), 42px 탭 줄(활성 탭 먹색 3px 밑줄), 빠른 필터 타일 4개(한 줄, 72px), 툴바(필터·검색·CSV·집행 추가 파랑 버튼), 그 아래 표가 남은 높이를 모두 차지(머리글 고정, 작업 열 우측 고정). 열: 거래번호·상태·원인발생일·지급청구일·지출완료일·재원·예산목·세목·거래처·적요·│금액·예산목 잔액│·태그·증빙·작업. 금액 열 왼쪽 경계가 2px 남색 세로선, 하단 합계 행은 남색 이중선. 1366에서 열이 넘치면 가로 스크롤과 우측 그림자 힌트.

FORM: 컬럼너 패드(회계 괘선지), 내 순위 1위(IMPECCABLE'S PICK), 사용자가 롤 배정(노선도) 대신 선택. 팔레트는 2차 라운드 B안. seed: none (unavailable)

Signature interaction: 숫자 입력 칸을 벗어나면 표형 숫자로 정렬되고, 표의 금액·잔액 열은 어느 탭에서도 남색 선 오른쪽에 같은 폭으로 선다. 보완 표시를 누르면 행 좌측 띠와 상태 글자가 150ms 안에 붉게 켜진다.

Motion grammar: 상태 전환 120~150ms ease-out 색·배경만. 드로어·대화상자 열림 즉시(전환 없음). 토스트 180ms 아래서 위로.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Open decisions (resolved)
- 행 높이 30px 고정. 예산목 잔액 열 기본 표시. 재원색 없음.
