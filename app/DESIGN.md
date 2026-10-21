---
name: SECONDCare (의료인공지능센터 연구비 관리 시스템)
description: 컬럼너 패드(회계 괘선지)의 규율을 화면에 옮긴 단일 서체·단일 색조의 장부 UI
colors:
  ink: "#1E2124"
  ink-2: "#5A6270"
  ink-3: "#6B7380"
  bg: "#FFFFFF"
  bg-table: "#FAFBFC"
  bg-head: "#EEF0F3"
  bg-hover: "#F3F5F8"
  bg-select: "#E9EEF8"
  rule: "#D7DBE0"
  rule-2: "#E7EAEE"
  rule-hover: "#B8BFC9"
  margin: "#1F3A93"
  alert: "#B3261E"
  alert-bg: "#FBEDEC"
  alert-deep: "#7A1710"
  ok: "#1A7F37"
  ok-bg: "#E7F4EA"
  ok-deep: "#0F5A26"
  primary: "#246BEB"
  primary-dark: "#1B55C2"
  primary-bg: "#E8EFFC"
  warn: "#8A5A00"
  warn-bg: "#FFF4D6"
  dot-idle: "#A3A9B3"
  memo-bg: "#FFFBE6"
  memo-rule: "#E3D9A6"
typography:
  headline:
    fontFamily: "Pretendard GOV, Pretendard, Malgun Gothic, Apple SD Gothic Neo, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 700
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Pretendard GOV, Pretendard, Malgun Gothic, Apple SD Gothic Neo, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 700
  figure:
    fontFamily: "Pretendard GOV, Pretendard, Malgun Gothic, Apple SD Gothic Neo, system-ui, sans-serif"
    fontSize: "19px"
    fontWeight: 700
    lineHeight: 1.25
    fontFeature: "tnum"
  body:
    fontFamily: "Pretendard GOV, Pretendard, Malgun Gothic, Apple SD Gothic Neo, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "tnum"
  label:
    fontFamily: "Pretendard GOV, Pretendard, Malgun Gothic, Apple SD Gothic Neo, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 600
rounded:
  sm: "2px"
  pill: "12px"
spacing:
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "20px"
  row: "28px"
  row-compact: "24px"
components:
  button-default:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 12px"
    height: "32px"
  button-default-hover:
    backgroundColor: "{colors.bg-hover}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.bg}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 12px"
    height: "32px"
  button-primary-hover:
    backgroundColor: "{colors.primary-dark}"
  button-ghost:
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0 12px"
    height: "32px"
  button-ghost-hover:
    backgroundColor: "{colors.bg-hover}"
  button-sm:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0 9px"
    height: "26px"
  button-compact:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0 7px"
    height: "22px"
  button-danger:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.sm}"
    padding: "0 9px"
    height: "26px"
  button-danger-hover:
    backgroundColor: "{colors.alert-bg}"
    textColor: "{colors.alert}"
  input:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "5px 8px"
    height: "32px"
  input-disabled:
    backgroundColor: "{colors.bg-head}"
    textColor: "{colors.ink-3}"
  tab:
    textColor: "{colors.ink-2}"
    typography: "{typography.label}"
    padding: "0 14px"
    height: "40px"
  tab-active:
    textColor: "{colors.ink}"
  subtab-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.bg}"
    padding: "0 14px"
    height: "32px"
  table-head:
    backgroundColor: "{colors.bg-head}"
    textColor: "{colors.ink-2}"
    typography: "{typography.label}"
    padding: "0 6px"
    height: "{spacing.row}"
  table-cell:
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    padding: "0 6px"
    height: "{spacing.row}"
  table-row-selected:
    backgroundColor: "{colors.bg-select}"
  table-row-alert:
    backgroundColor: "{colors.alert-bg}"
  summary-cell:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    padding: "8px 12px"
  chip-example:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "2px 9px"
  dialog:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "18px 22px 20px"
    width: "min(780px, 95vw)"  /* 예외: 학회 여비 계산기 #dlg-conf 는 min(1180px, 96vw) — 이동 구간 표(장소·시간대·현지 일시·KST) 때문 */
  drawer:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    padding: "12px"
    width: "min(460px, 100vw)"
---

# Design System: SECONDCare (의료인공지능센터 연구비 관리 시스템)

## Overview

**Creative North Star: "컬럼너 패드(회계 괘선지)"**

회계 담당자가 손으로 써 온 컬럼너 패드의 규율을 화면에 옮긴 시스템이다. 표가 화면의 주인이고, 그 밖의 모든 것(헤더·탭·툴바·요약 띠)은 표 위에 그어진 괘선 몇 줄에 불과하다. 흰 바탕 위에 회색 괘선이 28px 간격으로 반복되고, 금액 열 왼쪽에는 남색 세로선이 서며, 합계 행은 남색 이중선으로 닫힌다. 콘텐츠를 모두 지워도 남색 세로선·이중선·회색 괘선 격자만으로 이 앱임을 알아볼 수 있다.

색은 먹색 글자와 회색 괘선의 단일 색조 위에 네 가지 의미색만 얹는다. 붉은색은 보완필요·음수·오류에만, 파랑은 기본 버튼·포커스·선택·청구중이라는 기능에만, 초록은 완료에만, 남색은 괘선과 적립에만 쓴다. 그림자는 바탕 위에 떠오르는 대화상자·드로어·토스트 세 가지에만 허용되고, 표·카드·버튼은 모두 평면이다. 둥근 모서리는 2px로, 거의 각진 종이의 모서리다.

밀도는 높다. 본문 13px, 보조 12px, 행 28px, 셀 가로 여백 6px. 숫자는 항상 표형(tabular) 숫자로 우측 정렬되어 어느 탭에서든 같은 자리에 선다. 장식·일러스트·그라데이션·아이콘 세트는 없다. 아이콘은 설정 톱니, 정렬 화살표, 닫기 X 세 개뿐이며 모두 인라인 SVG다.

**Key Characteristics:**
- 표가 주인: 괘선 격자가 빈 영역까지 채우고, 머리글·작업 열은 고정된다.
- 남색 마진선(2px)과 합계 이중선(3px double)이 시그니처.
- 단일 서체(Pretendard GOV 계열 시스템 폰트), 표형 숫자, 13/12px 두 단계.
- 붉은색은 보완필요·음수·오류 전용. 파랑은 기능색, 초록은 완료.
- 2px 모서리, 평면 바탕, 그림자는 띄우는 레이어(대화상자·드로어·토스트)에만.
- 상태 전환 120~150ms ease-out, 색·배경만 움직인다.

## Colors

먹색과 회색 괘선의 단일 색조 위에 남색·붉은색·파랑·초록이 각각 하나의 의미만 지닌다.

### Primary
- **기능 파랑 (primary)** (#246BEB): 기본 버튼 배경, 포커스 링(2px outline), 캐럿·체크박스 accent, 청구중 상태 점, 빠른 필터 타일 선택 밑줄, 드롭존 활성 테두리. 장식이 아니라 "지금 여기를 누를 수 있다"는 신호에만 쓴다.
- **기능 파랑 진함 (primary-dark)** (#1B55C2): 기본 버튼 hover, 링크 글자색.
- **기능 파랑 바탕 (primary-bg)** (#E8EFFC): 텍스트 선택 하이라이트, AI 대화의 사용자 말풍선, 드롭존 활성 배경.

### Secondary
- **남색 마진선 (margin)** (#1F3A93): 금액 열 왼쪽의 2px 세로 괘선, 합계 행의 위 1px 실선과 아래 3px 이중선, AI 제안 카드 테두리·제목, 적립 상태. 이 색은 구조선이지 버튼이나 강조 배경이 아니다.

### Tertiary
- **경고 붉은색 (alert)** (#B3261E): 보완필요 상태 점·글자, 음수 금액, 오류 알림 테두리, 필수 표시(*), 잠금 상태 글자, 유효하지 않은 입력 테두리. 다른 용도로는 쓰지 않는다.
- **경고 바탕 (alert-bg)** (#FBEDEC): 보완필요 행 전체 배경, 오류 알림·토스트 배경, 삭제 버튼 hover 배경.
- **경고 깊은 글자 (alert-deep)** (#7A1710): 경고 바탕 위 본문 글자.
- **완료 초록 (ok)** (#1A7F37): 완료·집행완료 상태 점·글자, 제안 처리 완료 표시, 성공 알림 테두리.
- **완료 바탕 (ok-bg)** (#E7F4EA) / **완료 깊은 글자 (ok-deep)** (#0F5A26): 성공 알림·토스트.
- **주의 갈색 (warn)** (#8A5A00) / **주의 바탕 (warn-bg)** (#FFF4D6): 대기 상태, AI가 채운 입력 칸 배경, 주의 토스트, 대화상자 AI 메시지 경고.

### Neutral
- **먹 (ink)** (#1E2124): 본문 글자, 헤더 하단선(1px), 표 상단선(1px), 활성 탭 밑줄(2px), 대화상자 상단선(2px), 서브탭 활성 배경.
- **먹 2 (ink-2)** (#5A6270): 보조 글자, 표 머리글, 툴바 레이블, 비활성 탭, 차트 축 글자.
- **먹 3 (ink-3)** (#6B7380): 비활성 입력·버튼 글자, placeholder, 상태 점 기본색, 메모 마크. (흰 바탕 4.8:1)
- **바탕 (bg)** (#FFFFFF): 페이지·헤더·탭·대화상자·드로어 바탕.
- **표 바탕 (bg-table)** (#FAFBFC): 표 영역, 합계 행, 작업 열, 드롭존, AI 응답 말풍선.
- **머리 바탕 (bg-head)** (#EEF0F3): 표 머리글, 버튼 active, 비활성 입력.
- **hover 바탕 (bg-hover)** (#F3F5F8): 행·버튼·타일 hover.
- **선택 바탕 (bg-select)** (#E9EEF8): 선택된 행, 선택된 빠른 필터 타일.
- **괘선 (rule)** (#D7DBE0): 셀 아래선, 입력·버튼 테두리, 표 외곽선, 드로어 왼쪽선.
- **옅은 괘선 (rule-2)** (#E7EAEE): 빈 영역 괘선 반복, 요약 띠 구분선, 툴바 아래선, 차트 격자선.
- **괘선 hover (rule-hover)** (#B8BFC9): 입력·버튼 hover 테두리.
- **휴지 점 (dot-idle)** (#A3A9B3): 미청구(발생)·취소 상태 점.
- **메모 바탕 (memo-bg)** (#FFFBE6) / **메모 괘선 (memo-rule)** (#E3D9A6): 적요 칸 비고 메모 툴팁 전용(엑셀 메모 차용). 다른 곳에 쓰지 않는다.
- **주의 갈색 글자 (.warn)**: 주의·미연결 안내는 갈색(warn). 안내 글자 줄(`.toolbar-note.warn`)도 갈색이다(회색 `.toolbar-note`보다 뒤에 선언). 음수·미지급 금액은 `.neg`(붉은 700).

### Named Rules
**붉은색 전용 규칙.** 붉은색(#B3261E)은 보완필요·음수·오류·필수 표시에만 쓴다. 삭제 버튼조차 휴지 상태에서는 회색이고 hover에서만 붉어진다.

**마진선 규칙.** 금액 열은 어느 표에서든 왼쪽에 2px 남색 세로선을 지니고, 합계 행은 위 1px 실선·아래 3px 이중선으로 닫힌다. 인쇄 시 이 두 선만 검정(#000)으로 바뀌고 나머지 색은 사라진다.

**재원 무색 규칙.** 재원은 코드 글자로만 구분한다. 재원별 색을 부여하지 않는다(차트 범례의 8색 팔레트는 차트 안에서만 쓴다).

## Typography

**Display Font:** 없음 (디스플레이 크기 없음)
**Body Font:** Pretendard GOV (→ Pretendard → Malgun Gothic → Apple SD Gothic Neo → system-ui)
**Label/Mono Font:** 동일 서체. `code`도 `font: inherit`.

**Character:** 서체 하나. 굵기(400/600/700)와 두 크기(13/12px)만으로 위계를 만든다. 숫자는 문서 전체에 `font-variant-numeric: tabular-nums` + `"tnum"`이 걸려 있어 어느 열에서나 자릿수가 맞는다. 음수는 붉은 600~700.

### Hierarchy
- **Headline** (700, 15px, letter-spacing -0.01em): 헤더의 앱 이름 한 줄뿐.
- **Figure** (700, 19px, line-height 1.25): 요약 띠의 숫자. 빠른 필터 타일에서는 17px.
- **Title** (700, 13px): 섹션 h2(여백 18px 0 6px), 대화상자 h2(14px), 드로어 섹션 h3, 합계 행, 툴바 합계.
- **Body** (400, 13px, line-height 1.45): 표 셀(line-height 1.3), 입력, 버튼(600). 드로어 본문·메시지·보고서는 12.5px.
- **Label** (600, 12px): 표 머리글, 보조 설명(400, ink-2), 툴바 레이블, 작은 버튼, 상태 글자, 차트 범례.

### Named Rules
**두 크기 규칙.** 본문 13px와 보조 12px 외의 크기는 헤더 15px, 요약 숫자 19/17px, 대화상자 제목 14px, 차트 SVG 9~10px뿐이다. 새 화면은 이 안에서 고른다.

**표형 숫자 규칙.** 금액·건수·비율은 우측 정렬 표형 숫자로, `ko-KR` 천 단위 구분. 입력 칸도 blur 시 같은 서식으로 바뀐다.

## Layout

- 두 기둥 틀(2026-10-20): 헤더(52px)와 탭 줄(40px)은 전폭이고, 그 아래를 `.shell`이 왼쪽 기둥 `.col`(`main`·바닥글)과 오른쪽 기둥 `aside#side`(사이드 패널)로 나눈다. `main`은 가로 20px, 위 12px, 아래 20px 여백을 두고 남은 폭과 높이를 모두 쓴다(아래 90px은 2026-10-20 사용자 요청으로 축소; 토스트는 패널 폭만큼 비켜 서므로 자리가 필요 없다). `.col`(`main`·바닥글)의 바닥글은 2026-10-20 삭제. 대상 뷰포트는 1366~1920, 모바일 비대상(1000px 이하에서는 패널을 숨김).
- 위에서 아래로: 헤더 52px(먹색 1px 하단선) → 탭 줄 40px(활성 탭 먹색 2px 밑줄, 회색 1px 하단선) → [빠른 필터 타일 띠] → 툴바(플렉스, 간격 6×12px, 아래 옅은 괘선) → 표.
- 표 래퍼는 `max-height: calc(100vh - 290px)`. 표는 데이터 행만큼만 그리고 합계 이중선에서 끝난다(빈 괘선으로 화면을 채우지 않음, 사용자 결정 2026-10-13). 머리글은 `position: sticky; top: 0`, 작업 열은 `right: 0` 고정. 가로 넘침 시 우측 16px 그림자 힌트 그라데이션.
- 행 높이 28px(`--row`), 압축 표 24px, 두 줄 칸 표(집행내역·인건비 계획표) 36px, 편집 격자 28px(`--row`, 글자 12px) (2026-10-14 사용자 요청으로 30/26/40에서 축소). 압축 표 안 작은 버튼은 22px. 정렬: 글자 왼쪽, 숫자 오른쪽, 날짜·상태·구분·결제수단·태그·작업 가운데(`.ctr`). 셀 여백 `0 6px`(2026-10-14 사용자 요청으로 10→6). 적요 등 긴 셀은 100~260px에서 말줄임, hover 시 펼침.
- 요약 띠 `.cards`: `repeat(auto-fit, minmax(150px, 1fr))`, 간격 0, 위 먹색선·아래 괘선, 셀 사이 옅은 세로 괘선. 카드가 아니라 한 줄 괘선 표.
- 대시보드(결의) 순서: 필터 줄(합계 한 줄 텍스트) → 예산목별 가용잔액 칸 `.cards.items`(`auto-fill, minmax(200px, 1fr)`, 폭에 따라 2줄 허용; 큰 숫자 18px, 아래 12px 보조 줄과 4px 집행률 막대: 파랑 집행, 먹색-3 품의대기, 초과는 붉은색) → `.two-col.wide`(3fr 2fr: 월별 추이 차트 | 적립금 잔액 표) → 재원별·예산목별 표. 보고서 초안은 AI 드로어 상단 `details.ai-report`로 이동. 사용자 결정 2026-10-13.
- 2열 블록 `.two-col`: 1fr 1fr, 간격 20px, 1000px 이하에서 1열.
- 대화상자 폼 `.fields`: 3열 그리드, 간격 8×12px, `.wide`는 3칸, `.mid`는 2칸; 700px 이하 1열.
- 사이드 패널 `#side`: 헤더·탭 줄 아래 전체 높이(`position: sticky; top: var(--top-h)`, `--top-h` 92px)의 평면 영역. 왼쪽 1px 괘선, 그림자 없음(떠오르는 층이 아니라 기둥). 구성 = 본문 480px(`--side-w`) + 오른쪽 끝 레일 44px(`--rail-w`, 표 바탕, 세로 글자 버튼 펼치기·기본·상세·AI; 활성 보기는 오른쪽 2px 먹색 안쪽 선). 본문에는 기본 패널 `#side-home`(용도 미정 자리표시)과 드로어 세 개(집행·적립금 상세 `#exec-drawer`, 신청 상세 `#req-drawer`, AI `#ai-drawer`)가 있고 한 번에 하나만 보인다(드로어가 보이면 기본 패널은 숨김). 접힘 `body.side-collapsed`는 레일만 남긴다(45px). 상태는 localStorage `ledger-side`, 첫 방문은 1500px 미만이면 접힘. 행 클릭·AI 호출은 접힌 패널을 자동으로 펼치고, 그 드로어가 닫히면 접힘으로 돌아간다. 인쇄에서는 패널 전체를 숨긴다. 토스트는 패널 폭만큼 왼쪽으로 비켜 선다.
- 드로어: 사이드 패널 본문 안을 채우는 세로 플렉스(`.drawer`는 더 이상 fixed가 아니며 폭은 패널 폭 480px). 열 숨기기(`cols.js`, 2026-10-21, 연구비 화면의 집행·품의·적립·예산 변경 내역·대시보드 집행 현황): 열은 보임 / 스텁 / 없음 셋 중 하나다. 스텁은 10px 로 좁힌 열(머리글에 2px 세로 표시, 툴팁에 열 이름과 이유, 누르면 보임)이며 사용자가 숨긴 열·폭이 모자라 자동으로 접힌 열·기본 숨김 열(옛 상세 열 관리번호·세세목·사용자·비고)이 모두 스텁으로 남아 숨긴 열이 있다는 사실이 늘 보인다. 없음은 화면에 아예 그리지 않는 열(`hide: true`, 예산·대시보드의 내부인건비·연구개발부담비). 조작은 머리글 우클릭 메뉴와 툴바 [조회 열 관리] 팝오버(체크 목록, 고정 열은 비활성) 두 가지. 번호 열·작업 열·대시보드의 재원·항목 열은 숨길 수 없고 숨길 수 있는 열 중 하나는 늘 보인다. 선택은 sessionStorage(한 세션). 열 폭은 `COLW`(JS)가 머리글 inline width 로 주고, 표 min-width = 보이는 열 폭 합(적요 최소 180/140/160) + 스텁 10px, width 100% 라 표가 틀 폭을 늘 채우고 넘칠 때만 가로 스크롤한다. 자동 접기 단계(`COL_FOLD`): 집행 1300 미만 결제수단·예산목 잔액, 1100 미만 세목·태그·작성자, 900 미만 재원·증빙, 760 미만 예산목; 품의 1500 미만 비고·세세목·결제수단, 1300 미만 세목·품의자·작성자, 1100 미만 태그, 900 미만 재원·거래처, 760 미만 예산목; 적립 1400 미만 비고·연결거래번호, 1100 미만 사용자·작성자·증빙번호, 900 미만 상태·증빙. 날짜 열은 접지 않는다. 신청 표는 아직 CSS 접기(1100 미만 신청인·관련과제·첨부·주문번호·연결품의번호). 예전 규칙: 보조 열(재원·세목·태그·증빙·예산목 잔액·결제수단 등)을 접고, 1500px 미만에서는 예산목도 접는다. 적요는 180px 아래로 눌리지 않으며 모자라면 표 래퍼가 가로 스크롤한다.
- 툴바: 컨트롤 아랫선 정렬(`align-items: end`). 레이블 없는 안내 글자·합계·서브탭도 32px 컨트롤 높이 안에서 가운데.
- 긴 목록: 400건까지만 그리고 마지막 행에 "더 보기 (n건 남음)". 합계 행·건수·CSV는 항상 전체 기준. 검색 입력은 150ms 디바운스.
- 간격 척도: 4 / 6 / 8 / 12 / 20px. 섹션 h2 위 18px.
- 인쇄: A4 가로, 여백 12mm. 맨 위에 인쇄 전용 머리글(센터명 · 화면 · 재원 · 기간 · 출력일, 대시보드는 합계 한 줄)을 붙이고, 드로어로 접힌 열을 되살리며, 툴바·체크 버튼·출처 표시·메모 마크·넘침 그림자를 숨긴다. 집계 기준(details)은 펼쳐서 인쇄한다. 신청 화면의 머리글은 예산 숫자 없이 화면 · 연도 · 구매처 · 상태 · 출력일.
- 인쇄 (발주서·학회 산출 내역): 이름 붙은 쪽 `@page order-sheet` = **A4 세로, 여백 15mm**. 인쇄 전용 사본(`#print-sheet`/`#print-conf`)만 보이고 화면·대화상자는 숨긴다. [인쇄] 버튼이든 Ctrl+P든 발주서 대화상자가 열려 있으면 발주서로 인쇄된다(`beforeprint`). 괘선 #000, 줄은 쪽 사이에서 끊지 않고(`break-inside: avoid`), 열 머리는 쪽마다 반복, 합계(tfoot)는 마지막에 한 번(`display: table-row-group`). 쪽 머리 여백 상자에 왼쪽 "발주서 · 주문번호 …", 오른쪽 "n / N"(`counter(page)`/`counter(pages)`). 코드 칸은 줄바꿈하지 않는다. 발주서 사본은 tnum을 끈다(PDF에서 숫자·코드를 글자로 복사할 수 있게).

- 인쇄 (지출결의서, `.voucher`): 이름 붙은 쪽 `@page voucher` = **A4 세로, 여백 15mm**, 아래 가운데 여백 상자에 "k/n"(`@bottom-center`, 9pt). 인쇄 전용 사본 `#print-voucher`만 보이고(`body.printing-voucher`), [인쇄]든 Ctrl+P든 결의서 대화상자가 열려 있으면 결의서로 인쇄된다(`beforeprint`). 화면 미리보기(`#dlg-voucher`, `.vc-preview` 안에 210mm 종이)와 인쇄가 같은 규칙을 쓴다. 이 양식은 화면 토큰이 아니라 승인 시안(`.impeccable/mocks/voucher/A5_수정형.html`)의 값을 따른다: 괘선 #000(0.5pt, 표 외곽 1px, 합계 위 2px), 행 높이 **8mm 고정**(맞추려고 줄이지 않음), 셀 왼쪽 여백 3mm, 라벨 칸 폭 24mm(재원 현황 첫 열 40mm), 본문 10.5pt, 제목 22pt, 절 제목 21px, 금액 12pt 700, 숫자 우측 정렬·음수 U+2212. 증빙 5줄 + 재원 9줄 + 결의 내역 11줄(8mm × 28줄 = 224mm)이 267mm 한 쪽에 들어가도록 머리는 번호 상자 높이(16mm)로, 절 제목 여백은 위 1.7mm·아래 0.5mm·줄 높이 1로 시안(18mm 띠, 6mm/2mm)보다 좁혔다. 줄은 쪽 사이에서 끊지 않고 표 머리는 반복, 절 제목은 다음 표와 떨어지지 않는다(`break-after: avoid`). tnum은 끈다(PDF 글자 복사).
- 인쇄 (증빙 첨부 양식, `.ev-mount`): 증빙 1건 = A4 세로 1장. 이름 붙은 쪽 `@page mount` = **A4 세로, 여백 15mm, 여백 상자 없음(쪽 번호 없음)**. 인쇄 전용 사본 `#print-mount`만 보이고(`body.printing-mount`), [인쇄]든 Ctrl+P든 양식 대화상자(`#dlg-mount`, 결의서와 같은 `dlg-sheet` 틀: 미리보기 + [닫기] [인쇄], 여러 장이면 [이전] "n건 중 k번째" [다음])가 열려 있으면 지금 보이는 한 장만 인쇄된다. 시안 `.impeccable/mocks/voucher/E3_첨부양식.html`에서 두 가지를 바꿨다: **기관명 줄 없음**(표가 위 여백에서 바로 시작), **2행 거래처·적요 값 칸 같은 폭**(라벨 24mm씩, 값 66mm씩). 표는 180mm 3행: 1행 증빙번호(굵게, 칸에 다 들어가도록 글자만 10.5pt→최소 7.5pt로 줄임) | 증빙종류 | 금액("385,000원", 우측 정렬), 2행 거래처 | 적요(한 줄, 넘치면 …), 3행 비고(전체 폭). 열 격자 24·36·24·6·24·6·24·36mm. 회색 라벨 칸 24mm #F2F2F2, 행 8mm, 괘선 #000(외곽 1px, 안쪽 0.5pt), 셀 왼쪽 여백 3mm, 10.5pt. 표 아래 4mm부터 인쇄 영역 끝(282mm)까지 1px #000 빈 부착란. 화면 미리보기와 인쇄가 같은 규칙이고, 인쇄 사본은 tnum을 끈다.
- **회색 라벨 칸 규칙.** 라벨 칸 회색 바탕 #F2F2F2(`print-color-adjust: exact`)는 **인쇄하는 공문 양식(지출결의서·증빙 첨부 양식)에만** 허용한다. 화면 표·대화상자에는 쓰지 않는다(화면 머리글은 bg-head).

## Elevation & Depth

평면 시스템. 바탕 위의 깊이는 괘선의 굵기와 색(옅은 회색 → 회색 → 먹색 → 남색)으로 나타내며, 표·카드·버튼·탭에는 그림자가 없다. 그림자는 바탕 위로 "떠오르는" 세 레이어(대화상자·드로어·토스트)와, 고정된 작업 열이 내용 위에 겹친다는 사실을 알리는 좁은 안쪽 그림자 두 곳에만 쓴다.

### Shadow Vocabulary
- **띄우기 (`--shadow`)** (`box-shadow: 0 8px 24px -8px rgba(30,33,36,.28)`): dialog, .drawer, .toast.
- **고정 열 경계**: 표의 sticky 작업 열 왼쪽은 그림자 없이 1px 괘선(`border-left: 1px solid var(--rule)`)으로 구분한다 (2026-10-20 사용자, 예전 그림자 `-6px 0 8px -6px rgba(30,33,36,.22)` 폐지).
- **가로 넘침 힌트**: 폐지 (2026-10-20 사용자). 표 래퍼 우측 16px 그라데이션을 쓰지 않는다.
- **선택 밑줄** (`box-shadow: inset 0 -2px 0 var(--primary)`): 선택된 빠른 필터 타일. 그림자가 아니라 밑줄 대용.
- **대화상자 뒷막** (`rgba(30,33,36,.32)`).

### Named Rules
**떠오르는 것만 그림자 규칙.** 그림자는 바탕 평면을 벗어난 레이어(대화상자·드로어·토스트)에만 허용된다. 표·카드·버튼·입력은 괘선으로만 구분한다.

## Shapes

- 모서리 반경은 단일값 2px(`--radius`): 버튼, 입력, 대화상자, 알림, 토스트, 드롭존, 설정 그룹, 메시지 말풍선, 서브탭 묶음.
- 유일한 예외는 AI 드로어의 예시 질문 칩(12px, 알약형)과 상태 점(8px 원).
- 테두리는 1px 회색 괘선이 기본. 상단 경계만 먹색 1px(표·차트·보고서·요약 띠), 대화상자는 먹색 2px 상단선, 드로어 머리는 먹색 1px 하단선. 즉 "위쪽 먹색 선 한 줄"이 블록의 시작을 알린다.
- 드롭존은 1px 점선 괘선. 합계는 3px double 남색.
- 상태는 배지가 아니라 8px 점 + 글자(600). 둥근 배지, 채운 알약 배지는 쓰지 않는다.

## Components

### Buttons
- **Shape:** 거의 각진 모서리(2px), 1px 괘선 테두리, 600 굵기, inline-flex, 아이콘 14px 간격 6px.
- **기본 (.btn):** 흰 바탕, 먹색 글자, 가로 12px 여백, 높이 32px. hover 바탕 #F3F5F8·테두리 #B8BFC9, active 바탕 #EEF0F3. 전환 120ms ease-out(배경·테두리·글자색).
- **기본색 (.btn-primary):** 파랑 바탕·테두리, 흰 글자. hover 진한 파랑. 툴바에서 왼쪽 6px 추가 여백. 화면당 "추가/저장/전송" 류 한두 개.
- **고스트 (.btn-ghost):** 투명 바탕·테두리, hover 시 바탕만. 헤더 새로고침, 그리고 모든 대화상자의 취소·닫기 버튼(변형 하나로 통일).
- **작은 (.btn-sm):** 높이 26px, 12px 글자, 가로 9px. 표 작업 열·드로어·대화상자 보조 동작. 압축 표(`table.grid.compact`) 안에서는 22px, 가로 7px.
- **삭제 (.btn-danger):** 휴지 상태는 회색 글자(ink-2)·회색 테두리와 구분되지 않음. hover/focus에서만 붉은 글자·테두리·연한 붉은 바탕.
- **아이콘 (.btn-icon / .btn-x):** 가로 8px; 닫기는 28×28 정사각.
- **Disabled:** 투명도를 쓰지 않는다(opacity 1). 머리 바탕(bg-head)·ink-3 글자·괘선 테두리의 회색 처리, not-allowed 커서. 비활성 삭제 버튼은 hover에도 붉어지지 않는다.
- **Focus:** 공통 `:focus-visible` 2px 파랑 outline, offset 1px.

### Chips
- 상태 표시는 칩이 아니라 **점 + 글자**(.badge): 8px 원 점, 600 굵기. 발생/미청구 회색 점·ink-2 500, 청구 파랑 점, 보완 붉은 점·붉은 글자, 완료·집행완료 초록, 대기 갈색, 취소 회색, 적립 남색, 사용 갈색(#B86A00 점/#8A4F00 글자).
- AI 예시 질문 칩(.chip-ex): 12px 알약, 1px 괘선, 흰 바탕, 12px 글자, 2×9px 여백. hover 시 파랑 테두리·글자. 이 시스템에서 유일한 알약형.

### Cards / Containers
- **요약 띠 (.cards/.card):** 카드가 아니다. 위 먹색 1px·아래 괘선 1px의 한 줄 괘선 표. 셀 8×12px, 라벨 12px ink-2, 값 19px 700. 음수 값은 붉은 700. 빠른 필터 타일(.cards.quick)은 클릭 가능, hover 바탕, 선택 시 선택 바탕 + 파랑 2px 안쪽 밑줄, 값 17px.
- **표 래퍼 (.table-wrap):** 표 바탕 #FAFBFC, 1px 괘선 외곽, 위 먹색 1px, 그림자 없음.
- **차트 (.chart):** 흰 바탕, 1px 괘선, 위 먹색 1px, 여백 8/12/6px. SVG 막대, 격자선 rule-2, 축 글자 10px ink-2(#5A6270), y축 눈금은 1·2·2.5·5×10ⁿ 간격의 깔끔한 수, 범례 12px, 재원별 8색 팔레트(#246BEB #008A1E #E66B00 #8A2BE2 #0097A7 #C2185B #5D6D7E #9A6700)는 차트 안에서만. 누적선 남색, 예산현액선은 ink-2 회색 점선이고 누적 집행이 예산을 넘을 때만 붉은 점선.
- **설정 그룹 (.s-group fieldset):** 1px 괘선, 2px, 8/12/12px, legend 12px 700.
- **드롭존 (.drop):** 1px 점선 괘선, 표 바탕, 12px ink-2 중앙 정렬; 드래그 중 파랑 테두리·파랑 바탕.
- **알림 (.alert):** 8×12px, 1px 의미색 테두리, 의미색 바탕, 깊은 글자색, 12px.

### Inputs / Fields
- **Style:** 흰 바탕, 1px 괘선, 2px 모서리, 5×8px 여백, 최소 높이 32px, 13px 글자. placeholder #6B7380. 숫자 입력(.num-input)은 우측 정렬 표형 숫자.
- **Hover:** 테두리 #B8BFC9.
- **Focus:** 테두리 파랑 + 2px 파랑 outline(offset 0).
- **Error / Disabled:** `aria-invalid` 붉은 테두리, 오류 문구 12px 붉은색; disabled 머리 바탕·ink-3 글자(opacity 1). 필수 표시 `*` 붉은색, 레이블 12px ink-2 세로 배치(간격 3px). AI가 채운 칸은 주의 바탕(#FFF4D6).
- 파일 선택 버튼은 기본 버튼과 같은 28px 괘선 버튼.

### Navigation
- **상단 헤더 (.top):** 52px, 흰 바탕, 먹색 1px 하단선, 가로 20px, 간격 12px. 제목 15px 700, 파일 상태 12px ink-2(잠금 시 붉은 600), 고스트 버튼, 톱니 SVG 18px, 파랑 AI 버튼.
- **탭 (.tabs):** 40px, 600 굵기, 가로 14px, 비활성 ink-2, hover 먹색, 활성 먹색 글자 + 먹색 2px 밑줄(줄 아래선과 -1px 겹침). 배경 변화 없음.
- **서브탭 (.subtabs):** 1px 괘선으로 묶인 분할 버튼, 32px, 활성은 먹색 바탕·흰 글자. **탭 안의 두 번째 단계 보기는 모두 이 분할 버튼**으로 만든다(대시보드 예산|태그, 신청 › 소모품 신청|주문). 그 보기의 툴바 맨 왼쪽에 두고, 탭 아래에 두 번째 탭 줄을 만들지 않는다(구분을 바꿔도 내용이 밀리지 않게). 역할은 `role=tablist`/`tab`, ←/→·Home/End 이동, 고른 보기는 브라우저에 기억. 건수 배지(.tab-n, 12px 괘선 상자)는 활성 버튼 안에서 흰 글자·투명 바탕·ink-3 테두리.
- **건너뛰기 링크:** 포커스 시 좌상단 파랑 바탕 흰 글자.

### 괘선 표 (Signature Component)
`table.grid`. 셀 높이 28px(`--row`), 가로 6px, 아래 1px 괘선, nowrap, 머리글 12px 600 ink-2 머리 바탕 sticky. 금액 열(.amt)은 왼쪽 2px 남색선. 숫자 열 우측 정렬. 합계 행(tr.total) 700, 표 바탕, 위 1px·아래 3px 이중 남색선. 소계 하위 행(tr.sub)은 글자 ink-2, 숫자만 먹색. 행 hover 바탕, 선택 바탕, 보완 행은 붉은 바탕(hover #F6E2E0). 작업 열 우측 고정 + 좁은 안쪽 그림자. 정렬 가능 머리글은 10px SVG 화살표. 빈 표는 중앙 26px 여백 ink-2 문구. 부수 열(.col-minor)은 "상세 열" 토글로만 표시. 인쇄 시 괘선·마진선이 검정으로 바뀌고 hover·고정·작업 열이 사라진다.

### 소모품 주문 표 (`#order-table`)
`table.grid`를 따르는 고정 열 표(`table-layout: fixed`). 열 폭: 주문번호 128 · 주문일·배송일 56(MM/DD, 전체 날짜는 툴팁) · 구매처 84 · 주문금액 104(.amt 마진선, 700) · 결제금액 96(볼드 없음) · 적립금 60(적립금 탭과 같은 `badge 사용`) · 건수 44 · 신청번호(남는 폭, 말줄임) · 작업 168. 작업 열은 왼쪽 정렬, 첫 버튼 [발주서], 둘째 버튼([주문 취소] 또는 [배송일 지우기])은 96px 고정 폭이라 버튼 자리가 행마다 같다. 표 안 링크(배송일 [등록], 신청번호, 신청 목록의 주문번호)는 한 모양: 13px primary-dark 밑줄, 누를 자리 24px 이상, 주문번호를 담은 aria-label. 합계는 `tfoot tr.total`(합계 n건 · 주문금액 · 결제금액). 빈 표에서는 고정 열 그림자를 없앤다. 주문 생성 대화상자의 줄 표는 고정 폭 열에 품목만 말줄임(수량·금액은 항상 보임).

### 드로어 / 대화상자 / 토스트
- **드로어 (.drawer):** 우측 고정, 전체 높이, 흰 바탕, 왼쪽 1px 괘선, 띄우기 그림자, 머리 48px 먹색 1px 하단선, 본문 12px 여백 세로 간격 10px, 바닥 1px 괘선. 열림 전환 없음. 집행 상세 섹션(.xd-sec)은 옅은 괘선으로 구분, key-value 그리드 12.5px.
- **대화상자 (dialog):** min(780px, 95vw), 1px 괘선 + 먹색 2px 상단선, 2px, 띄우기 그림자, 뒷막 32% 먹색. 내용은 모두 `<form method="dialog">` 안(여백 18/22/20px), 제목 14px, 동작 줄 우측 정렬 간격 8px 위 16px. 동작 줄의 왼쪽 보조 버튼과 오른쪽 버튼 사이는 `.sp`(flex 1), 안내 글자(.toolbar-note)는 스스로 늘어난다. 취소·닫기는 고스트 버튼, 닫기(X)가 있으면 취소 버튼을 따로 두지 않는다.
- **토스트 (.toast):** 우상단 12/14px 고정, 1px 의미색 테두리(주의는 warn 갈색), 의미색 바탕, 띄우기 그림자, 12.5px, 180ms 아래서 위로 페이드인. 닫기 12px SVG.
- **출처 표시 (.origin):** 인건비·적립금에서 생긴 집행 옆 작은 괘선 글자. 바탕을 채우지 않는다(흰 바탕, 괘선 테두리, 인건비 남색·적립 갈색 글자).
- **편집 격자 상태:** 수정됨 warn-bg, 새 행 ok-bg, 삭제 표시 머리 바탕+취소선, 잠김 머리 바탕, 오류 행 alert-bg. 범례 칩도 같은 바탕.
- **계획표 범례:** 소요 일치 초록, 부족 갈색, 초과 ink-2, 미배정 ink-3, 재직 아님 머리 바탕, 확정 포함은 초록 2px 밑줄.
- **AI 메시지 (.msg):** 12.5px, 2px, 8×12px. 사용자 파랑 바탕 우측, 응답 표 바탕 + 옅은 괘선 좌측, 제안 카드는 남색 1px 테두리·남색 700 제목.

## Do's and Don'ts

### Do:
- **Do** 모든 표를 `table.grid` 규칙으로 그린다: 28px 행, 금액 열 왼쪽 2px 남색선, 합계 행 남색 이중선, 머리글 sticky.
- **Do** 숫자를 표형 숫자·우측 정렬·`ko-KR` 천 단위로 표시하고, 음수는 붉은 600~700으로 쓴다.
- **Do** 블록의 시작을 "위쪽 먹색 1px 선"으로 알린다(표·차트·요약 띠·보고서). 대화상자는 2px.
- **Do** 상태를 8px 점 + 글자로 표시하고, 상태 색은 정해진 매핑(청구 파랑·보완 붉음·완료 초록·대기 갈색·적립 남색)을 따른다.
- **Do** 상태 전환은 120~150ms ease-out으로 색·배경만 바꾸고, 드로어·대화상자는 전환 없이 즉시 연다.
- **Do** 아이콘이 필요하면 14~18px 인라인 SVG(stroke currentColor)로 넣는다.

### Don't:
- **Don't** 붉은색(#B3261E)을 보완필요·음수·오류·필수 표시 외에 쓰지 않는다. 삭제 버튼의 휴지 상태도 회색이다.
- **Don't** 표·카드·버튼·입력에 그림자를 주지 않는다. 그림자는 대화상자·드로어·토스트에만.
- **Don't** 2px 외의 모서리 반경을 쓰지 않는다(AI 예시 칩 12px과 8px 상태 점만 예외).
- **Don't** 재원별 색, 둥근 채움 배지, 그라데이션 바탕, 일러스트·로고·사진을 넣지 않는다.
- **Don't** 13/12px 외의 새 글자 크기나 두 번째 서체를 도입하지 않는다. 외부 CDN 폰트·아이콘 폰트 금지.
- **Don't** 요약 띠를 떠 있는 흰 카드로 바꾸지 않는다. 괘선 한 줄로 유지한다.
