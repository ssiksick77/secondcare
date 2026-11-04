/* 학회 여비 계산기 (신청 › 학회) — request.js 다음에 로드.
   ref/학회여비계산기V2.html 의 규정값·산식을 옮겨 새로 작성 (코드 이식 아님). 사용자 결정:
   - 관용(공용)차량 항목 제외
   - 이동 구간은 출발·도착마다 장소·시간대·현지 일시를 받고 UTC 순간으로 환산한다.
     기내박·여행일수는 한국 시각(KST) 기준으로 센다.
   저장: 신청 '상세' JSON 에 {v:2, in:{…}, out:{합계, …}} 를 넣고 맨 위 '합계'도 같이 둔다(request.js 금액 잠금 규칙).
   v:2 — 금액 통화는 코드(KRW/USD/EUR…), in.fxs 에 통화별 환율(원/1단위). v:1(₩/$ 기호, fx 만)은 읽을 때 변환한다.
   공개: openConfCalc(opts) · confFormInit(det, opts) · confCalcValue() · confDrawerKv(det, kv) · window.ConfCalc(순수 함수, 테스트용) */
"use strict";
(function () {

// ---------- 규정 (공무원 여비 규정 별표2·별표4. 개정 시 이 객체만 고친다) ----------
const REG = {
  title: "공무원 여비 규정", no: "대통령령 제36492호", effective: "2026.7.1. 시행",
  intl: {
    "1na": { name: "차관급 상당 (별표1 제1호나목)", rare: true, ilbi: 50, lodge: { 가: 389, 나: 289, 다: 215, 라: 161 }, meal: { 가: 160, 나: 117, 다: 87, 라: 73 } },
    "1da": { name: "1급·부총장·학장 등 (별표1 제1호다목)", rare: true, ilbi: 40, lodge: { 가: 282, 나: 207, 다: 162, 라: 108 }, meal: { 가: 133, 나: 99, 다: 72, 라: 61 } },
    "1ra": { name: "교수·부교수 (별표1 제1호라목)", ilbi: 35, lodge: { 가: 223, 나: 160, 다: 130, 라: 85 }, meal: { 가: 107, 나: 78, 다: 58, 라: 49 } },
    "2": { name: "조교수·참여연구원·전임의 등 (별표1 제2호)", ilbi: 30, lodge: { 가: 176, 나: 137, 다: 106, 라: 81 }, meal: { 가: 81, 나: 59, 다: 44, 라: 37 } },
  },
  dom: {
    "1": { name: "교수·부교수 (제1호, 숙박 실비)", ilbi: 25000, meal: 25000, lodgeCap: false },
    "2": { name: "조교수·참여연구원·전임의 등 (제2호, 숙박 상한)", ilbi: 25000, meal: 25000, lodgeCap: true },
  },
  regions: [{ cap: 100000, name: "서울특별시" }, { cap: 80000, name: "광역시" }, { cap: 70000, name: "그 밖의 지역" }],
  stay: [[15, 1], [30, 0.9], [60, 0.8], [Infinity, 0.7]],  // 제17조: 현지 도착 다음 날부터 센 일수별 일비 비율
  mealPerDay: 3,           // 1끼 = 1일 식비의 1/3
  settleDays: 14,          // 제8조의2: 여행을 마친 다음 날부터 2주 이내 정산
  transitModes: ["항공", "선박"],  // 제16조: 숙박 박수에서 빼는 이동수단
  modes: ["항공", "철도", "선박", "자동차"],
  docs: {
    intl: {
      "참석 전": ["학회 초청 내역(메일 등)", "학회 일정표 또는 팜플렛", "채택 논문(초록)", "출장신청서(사전 결재안)", "등록비 청구서(인보이스)", "등록비 결제 영수증", "e-티켓", "운임 결제 영수증"],
      "참석 후": ["출입국사실확인서", "탑승확인서(보딩패스)", "학회 리플렛·이름표(네임텍 원본)", "숙박비 청구서(인보이스) 및 영수증", "출장 보고서"],
    },
    dom: {
      "국내 출장 제출 서류": ["출장신청서(사전 결재)", "출장 보고서", "교통비 영수증", "학회 등록 증빙(등록비 영수증·참가확인서)", "학회 일정표·리플렛", "숙박비 영수증(숙박 시)"],
    },
  },
  disclaimer: "본 계산은 참고용이며, 실제 지급액은 과제별 지급기준과 연구비 관리기관의 정산 결과에 따릅니다. 여비를 중복 신청(병원/원내/위탁)하면 환수 대상이며, 거짓·부정 수령 시 수령액의 5배가 가산 징수됩니다(공무원 여비 규정 제31조). 숙박비·운임은 신용카드(정부구매카드) 결제가 원칙입니다.",
};
REG.basis = `${REG.title}(${REG.no}, ${REG.effective})`;
const KST_NOTE = "기내박은 각 구간의 현지 날짜가 바뀐 횟수(항공·선박)로, 여행일수는 첫 출발부터 마지막 도착까지의 한국 날짜 수로 셉니다. 현지 출발·도착 일시를 시간대로 환산해 계산합니다.";

// 별표4 비고2 — 국가·도시별 등급 (가등급은 도시 단위)
const CITY_GRADE = {};
{
  const put = (g, arr) => arr.forEach(n => { CITY_GRADE[n] = g; });
  put("가", ["도쿄", "뉴욕", "런던", "로스앤젤레스", "로스엔젤레스", "모스크바", "샌프란시스코", "워싱턴D.C.", "워싱턴", "파리", "홍콩", "제네바", "싱가포르"]);
  put("나", ["베이징", "사모아", "오스트레일리아", "호주", "인도", "일본", "카자흐스탄", "쿡제도", "타이완", "대만", "파푸아뉴기니",
    "멕시코", "미국", "바베이도스", "세인트루시아", "세인트빈센트그레나딘", "세인트키츠네비스", "아이티", "앤티가바부다", "자메이카", "캐나다", "트리니다드토바고",
    "그리스", "네덜란드", "노르웨이", "덴마크", "독일", "러시아", "룩셈부르크", "벨기에", "사이프러스", "키프로스", "스웨덴", "스위스", "스페인", "아이슬란드", "아일랜드", "영국", "오스트리아", "이탈리아", "포르투갈", "프랑스", "핀란드", "헝가리",
    "가나", "가봉", "남수단", "남아프리카공화국", "리비아", "모로코", "바레인", "사우디아라비아", "세이셸", "아랍에미리트", "앙골라", "에티오피아", "오만", "우간다", "이스라엘", "이집트", "적도기니", "카타르", "코트디부아르", "콩고민주공화국", "쿠웨이트"]);
  put("다", ["뉴질랜드", "니우에", "마셜군도", "말레이시아", "방글라데시", "브루나이", "아제르바이잔", "인도네시아", "중국", "키르기스스탄", "키르키즈공화국", "태국", "타이", "튀르키예", "터키", "투르크메니스탄", "파키스탄", "피지",
    "가이아나", "과테말라", "도미니카공화국", "베네수엘라", "벨리즈", "브라질", "아르헨티나", "에콰도르", "우루과이", "칠레", "코스타리카", "파나마",
    "라트비아", "루마니아", "리투아니아", "몬테네그로", "불가리아", "세르비아", "슬로바키아", "슬로베니아", "에스토니아", "우크라이나", "체코", "크로아티아", "폴란드",
    "기니", "나이지리아", "니제르", "라이베리아", "레바논", "르완다", "말리", "모리셔스", "모잠비크", "보츠와나", "부르키나파소", "상투메프린시페", "세네갈", "수단", "에스와티니", "스와질란드", "시에라리온", "아프가니스탄", "알제리", "요르단", "이라크", "잠비아", "중앙아프리카공화국", "카메룬", "케냐", "탄자니아"]);
  put("라", ["네팔", "동티모르", "라오스", "몽골", "미얀마", "미크로네시아", "베트남", "스리랑카", "우즈베키스탄", "캄보디아", "타지키스탄", "통가", "필리핀",
    "니카라과", "볼리비아", "수리남", "엘살바도르", "온두라스", "콜롬비아", "파라과이", "페루",
    "마케도니아", "북마케도니아", "몰도바", "벨라루스", "보스니아헤르체고비나", "보스니아헤르체코비나", "알바니아",
    "감비아", "기니비사우", "나미비아", "레소토", "마다가스카르", "말라위", "모리타니", "소말리아", "예멘", "이란", "짐바브웨", "튀니지"]);
}
const CITY_HINT = "가등급은 도시 이름으로, 그 밖에는 국가 이름으로 검색하세요.";

// ---------- 시간대 ----------
const KST = "Asia/Seoul", TZ_OTHER = "__other";
const TZ_GROUPS = [
  ["한국·아시아", [[KST, "서울·인천 (한국)"], ["Asia/Tokyo", "도쿄·오사카"], ["Asia/Shanghai", "베이징·상하이"], ["Asia/Hong_Kong", "홍콩"], ["Asia/Taipei", "타이베이"], ["Asia/Singapore", "싱가포르"],
    ["Asia/Kuala_Lumpur", "쿠알라룸푸르"], ["Asia/Bangkok", "방콕"], ["Asia/Ho_Chi_Minh", "하노이·호찌민"], ["Asia/Manila", "마닐라"], ["Asia/Jakarta", "자카르타"], ["Asia/Kolkata", "인도"], ["Asia/Dubai", "두바이"]]],
  ["유럽", [["Europe/London", "런던·더블린·리스본"], ["Europe/Paris", "파리·브뤼셀"], ["Europe/Berlin", "베를린·뮌헨"], ["Europe/Amsterdam", "암스테르담"], ["Europe/Madrid", "마드리드·바르셀로나"],
    ["Europe/Rome", "로마·밀라노"], ["Europe/Vienna", "빈·프라하"], ["Europe/Zurich", "취리히·제네바"], ["Europe/Stockholm", "스톡홀름·코펜하겐"], ["Europe/Helsinki", "헬싱키"], ["Europe/Istanbul", "이스탄불"]]],
  ["미주", [["America/New_York", "뉴욕·보스턴·워싱턴 (동부)"], ["America/Toronto", "토론토·몬트리올"], ["America/Chicago", "시카고·휴스턴 (중부)"], ["America/Denver", "덴버 (산악)"], ["America/Phoenix", "피닉스"],
    ["America/Los_Angeles", "LA·샌프란시스코·시애틀 (서부)"], ["America/Vancouver", "밴쿠버"], ["Pacific/Honolulu", "호놀룰루"], ["America/Mexico_City", "멕시코시티"], ["America/Sao_Paulo", "상파울루"]]],
  ["오세아니아", [["Australia/Sydney", "시드니·멜버른"], ["Australia/Brisbane", "브리즈번"], ["Australia/Perth", "퍼스"], ["Pacific/Auckland", "오클랜드"]]],
];
const TZ_LIST = TZ_GROUPS.flatMap(([, l]) => l.map(([z]) => z));
const TZ_LABEL = Object.fromEntries(TZ_GROUPS.flatMap(([, l]) => l));
// 장소 글자로 시간대 추정 (사용자가 시간대를 직접 고르지 않았을 때만 적용)
const PLACE_TZ = Object.entries({
  [KST]: ["서울", "인천", "김포", "부산", "대구", "대전", "광주", "제주", "한국", "ICN", "GMP"], "Asia/Tokyo": ["도쿄", "오사카", "교토", "후쿠오카", "삿포로", "나고야", "일본"],
  "Asia/Shanghai": ["베이징", "상하이", "광저우", "선전", "중국"], "Asia/Hong_Kong": ["홍콩"], "Asia/Taipei": ["타이베이", "대만", "타이완"], "Asia/Singapore": ["싱가포르"],
  "Asia/Kuala_Lumpur": ["쿠알라룸푸르", "말레이시아"], "Asia/Bangkok": ["방콕", "태국"], "Asia/Ho_Chi_Minh": ["하노이", "호찌민", "다낭", "베트남"], "Asia/Manila": ["마닐라", "필리핀"],
  "Asia/Jakarta": ["자카르타", "인도네시아"], "Asia/Kolkata": ["뉴델리", "뭄바이", "벵갈루루", "인도"], "Asia/Dubai": ["두바이", "아랍에미리트"],
  "Europe/London": ["런던", "영국", "더블린", "아일랜드", "리스본", "포르투갈"], "Europe/Paris": ["파리", "프랑스", "브뤼셀", "벨기에"], "Europe/Berlin": ["베를린", "뮌헨", "프랑크푸르트", "독일"],
  "Europe/Amsterdam": ["암스테르담", "네덜란드"], "Europe/Madrid": ["마드리드", "바르셀로나", "스페인"], "Europe/Rome": ["로마", "밀라노", "이탈리아"], "Europe/Vienna": ["빈", "오스트리아", "프라하", "체코"],
  "Europe/Zurich": ["취리히", "제네바", "스위스", "바젤"], "Europe/Stockholm": ["스톡홀름", "스웨덴", "코펜하겐", "덴마크", "오슬로", "노르웨이"], "Europe/Helsinki": ["헬싱키", "핀란드"], "Europe/Istanbul": ["이스탄불", "튀르키예", "터키"],
  "America/New_York": ["뉴욕", "보스턴", "워싱턴", "필라델피아", "애틀랜타", "마이애미", "올랜도", "볼티모어"], "America/Toronto": ["토론토", "몬트리올", "오타와"],
  "America/Chicago": ["시카고", "휴스턴", "댈러스", "뉴올리언스", "미니애폴리스"], "America/Denver": ["덴버", "솔트레이크"], "America/Phoenix": ["피닉스"],
  "America/Los_Angeles": ["로스앤젤레스", "로스엔젤레스", "LA", "샌프란시스코", "샌디에이고", "시애틀", "라스베이거스", "새너제이", "포틀랜드"], "America/Vancouver": ["밴쿠버"],
  "Pacific/Honolulu": ["호놀룰루", "하와이"], "America/Mexico_City": ["멕시코시티", "멕시코"], "America/Sao_Paulo": ["상파울루", "리우데자네이루", "브라질"],
  "Australia/Sydney": ["시드니", "멜버른", "캔버라"], "Australia/Brisbane": ["브리즈번"], "Australia/Perth": ["퍼스"], "Pacific/Auckland": ["오클랜드", "웰링턴", "뉴질랜드"],
}).flatMap(([z, names]) => names.map(n => [n, z])).sort((a, b) => b[0].length - a[0].length);
function placeTz(place) {
  const s = String(place || "").trim(); if (!s) return "";
  const up = s.toUpperCase();
  const hit = PLACE_TZ.find(([n]) => /^[A-Z]+$/.test(n) ? new RegExp(`\\b${n}\\b`).test(up) : s.includes(n));
  return hit ? hit[1] : "";
}

// ---------- 현지 일시 → UTC (Intl.DateTimeFormat 만 사용) ----------
const DTF = {};
function dtf(tz) {
  if (!DTF[tz]) DTF[tz] = new Intl.DateTimeFormat("en-US", { timeZone: tz, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
  return DTF[tz];
}
function validTz(tz) { if (!tz || typeof tz !== "string") return false; try { dtf(tz); return true; } catch { return false; } }
// 순간(ms) → 그 시간대의 벽시계 시각을 UTC 로 읽은 ms
function wallMs(tz, ms) {
  const p = {}; dtf(tz).formatToParts(new Date(ms)).forEach(x => { if (x.type !== "literal") p[x.type] = Number(x.value); });
  return Date.UTC(p.year, p.month - 1, p.day, p.hour % 24, p.minute, p.second);
}
const offsetMs = (tz, ms) => wallMs(tz, ms) - ms;
function parseLocal(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(String(s || "")); if (!m) return null;
  const v = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]);
  return Number.isFinite(v) ? v : null;
}
// 반복 보정: t = 현지값 − offset(t). 서머타임 시작으로 없는 시각이면 진동하므로 뒤쪽(시계를 앞당긴 쪽)을 택하고 exact=false
function resolveLocal(local, tz) {
  const naive = parseLocal(local); if (naive == null || !validTz(tz)) return null;
  let t = naive - offsetMs(tz, naive), prev = null;
  for (let i = 0; i < 4; i++) {
    const n = naive - offsetMs(tz, t);
    if (n === t) break;
    prev = t; t = n;
  }
  let exact = wallMs(tz, t) === naive;
  if (!exact && prev != null) t = Math.max(t, prev);
  exact = wallMs(tz, t) === naive;
  return { ms: t, exact };
}
const localToUtc = (local, tz) => resolveLocal(local, tz)?.ms ?? null;
const pad2 = n => String(n).padStart(2, "0");
function wallStr(tz, ms) { const d = new Date(wallMs(tz, ms)); return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())} ${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())}`; }
const kstDay = ms => Math.floor(wallMs(KST, ms) / 864e5);
const localDay = (tz, ms) => Math.floor(wallMs(tz, ms) / 864e5);  // 그 시간대의 날짜 번호 (기내박: 현지 날짜 기준, 사용자 결정 2026-10-16)
const kstStr = ms => wallStr(KST, ms);
function utcOffsetLabel(tz, ms) { const m = Math.round(offsetMs(tz, ms) / 6e4), s = m < 0 ? "−" : "+", a = Math.abs(m); return `UTC${s}${a / 60 | 0}${a % 60 ? ":" + pad2(a % 60) : ""}`; }

// ---------- 날짜·금액 ----------
const dnum = s => { const p = String(s).split("-").map(Number); return Date.UTC(p[0], p[1] - 1, p[2]) / 864e5; };
const dstr = n => new Date(n * 864e5).toISOString().slice(0, 10);
const won = n => Math.floor(n + 1e-6);  // 원 미만 절사
const fmtN = n => Number(n).toLocaleString("ko-KR");
const fmtW = n => fmtN(n) + "원";
const fmtD = n => "$" + (Math.round(n * 100) / 100).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
// 결제 통화 고정 목록 (사용자 결정 2026-10-16). 환율은 모두 원/1단위 기준. USD 환율은 지급기준표(별표4) 환산에도 쓴다.
const CURRENCIES = [["KRW", "₩", "원"], ["USD", "$", "미국 달러"], ["EUR", "€", "유로"], ["JPY", "¥", "일본 엔"], ["GBP", "£", "영국 파운드"], ["CNY", "CN¥", "중국 위안"],
  ["CHF", "CHF", "스위스 프랑"], ["SGD", "S$", "싱가포르 달러"], ["HKD", "HK$", "홍콩 달러"], ["TWD", "NT$", "대만 달러"], ["AUD", "A$", "호주 달러"], ["CAD", "C$", "캐나다 달러"]];
const CUR_SYM = Object.fromEntries(CURRENCIES.map(([c, s]) => [c, s]));
const CUR_NAME = Object.fromEntries(CURRENCIES.map(([c, , n]) => [c, n]));
const curCode = v => v === "$" ? "USD" : (!v || v === "₩" || !CUR_SYM[v]) ? "KRW" : v;  // v:1 기호 호환
const fmtC = (n, code) => (CUR_SYM[code] || code) + (Math.round(n * 100) / 100).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
const stayFactor = k => { for (const [lim, f] of REG.stay) if (k <= lim) return f; return 1; };
const NOTE_LABEL = { info: "안내", warn: "주의", danger: "중요", ok: "확인" };

// ---------- 계산 (DOM 무관) ----------
function defaultInputs() {
  return {
    tripType: "intl", grade: "2", showAll: false, citySearch: "", cityGrade: "나", region: 100000, fx: 0, fxs: {}, fxDate: "", ts: "", te: "", cs: "", ce: "",
    legs: [
      { mode: "항공", meal: 0, dep: { place: "인천", tz: KST, at: "" }, arr: { place: "", tz: "", at: "" } },
      { mode: "항공", meal: 0, dep: { place: "", tz: "", at: "" }, arr: { place: "인천", tz: KST, at: "" } },
    ],
    transitManual: null, fare: 0, fareCur: "KRW", lodgePaid: 0, lodgeCur: "KRW", confMeals: 0,
    regFee: 0, regCur: "KRW", printFee: 0, printCur: "KRW", etcFee: 0, etcCur: "KRW", extFund: 0, extCur: "KRW", docs: {},
  };
}
const nz = v => { const n = Number(v); return Number.isFinite(n) && n > 0 ? n : 0; };

function compute(raw) {
  const inp = { ...defaultInputs(), ...(raw || {}) };
  const intl = inp.tripType !== "dom";
  const missing = [], errors = [], dateNotes = [], legNotes = [];
  const miss = (id, msg) => missing.push({ id, msg });
  const err = (id, msg) => errors.push({ id, msg });
  const fx = intl ? nz(inp.fx) : 1;
  if (intl && !(fx > 0)) miss("cf-fx", "적용 환율");
  // 결제 통화별 환율: KRW=1, USD=fx(지급기준 환율과 동일), 그 외는 inp.fxs[코드]
  const MONEY_KEYS = ["fareCur", "lodgeCur", "regCur", "printCur", "etcCur", "extCur"];
  const cur = k => intl ? curCode(inp[k]) : "KRW";
  const fxs = inp.fxs && typeof inp.fxs === "object" ? inp.fxs : {};
  const rateOf = code => code === "KRW" ? 1 : code === "USD" ? fx : nz(fxs[code]);
  if (intl) MONEY_KEYS.forEach(k => { const raw = inp[k]; if (raw && raw !== "₩" && raw !== "$" && !CUR_SYM[raw]) err(`cf-${k.replace("Cur", "")}-cur`, `결제 통화 '${raw}'는 목록에 없습니다. 통화를 다시 고르세요.`); });
  const usedCurs = [...new Set(MONEY_KEYS.map(cur).filter(c => c !== "KRW" && c !== "USD"))];
  usedCurs.forEach(c => { if (!(rateOf(c) > 0)) miss("cf-fx-" + c, `${c} 환율`); });
  if (intl && !["가", "나", "다", "라"].includes(inp.cityGrade)) miss("cf-cgrade", "도시 등급");

  // 이동 구간: 현지 일시 → UTC → 한국 날짜
  let autoNights = 0, inflight = 0; const basis = [], legs = [];
  (inp.legs || []).forEach((l, i) => {
    const n = i + 1, meal = nz(l.meal), mode = REG.modes.includes(l.mode) ? l.mode : REG.modes[0];
    inflight += meal;
    const info = { n, mode, meal, dep: { ...(l.dep || {}) }, arr: { ...(l.arr || {}) }, nights: 0, ok: false };
    legs.push(info);
    const ends = [["dep", "출발"], ["arr", "도착"]];
    if (!ends.some(([k]) => info[k].at)) return;  // 빈 구간은 무시
    let bad = false;
    ends.forEach(([k, label]) => {
      const e = info[k];
      if (!e.at) { miss(`leg-${i}-${k}-at`, `구간 ${n} ${label} 일시`); bad = true; return; }
      if (!intl) e.tz = KST;  // 국내 출장은 한국 시각으로만 (국외에서 바꾼 시간대가 남아 있어도 무시)
      if (!validTz(e.tz)) { err(`leg-${i}-${k}-tz`, `구간 ${n} ${label} 시간대${e.tz ? ` '${e.tz}'` : ""}가 올바르지 않습니다 (IANA 이름, 예: Europe/Paris).`); bad = true; return; }
      const r = resolveLocal(e.at, e.tz);
      if (!r) { err(`leg-${i}-${k}-at`, `구간 ${n} ${label} 일시 형식이 올바르지 않습니다.`); bad = true; return; }
      e.ms = r.ms; e.kst = kstStr(r.ms); e.local = wallStr(e.tz, r.ms); e.off = utcOffsetLabel(e.tz, r.ms);
      if (!r.exact) legNotes.push({ type: "warn", text: `구간 ${n} ${label}: ${e.at.replace("T", " ")}은(는) 서머타임 시작으로 ${e.tz}에 없는 시각이라 ${e.local}로 보정했습니다.` });
    });
    if (bad) return;
    info.ok = true;
    if (info.arr.ms <= info.dep.ms) {
      info.order = true;
      legNotes.push({ type: "warn", text: `구간 ${n}: 시간대를 환산하면 도착(한국 ${info.arr.kst})이 출발(한국 ${info.dep.kst})보다 빠르거나 같습니다. 일시와 시간대를 확인하세요. 이 구간의 기내박은 0박으로 계산했습니다.` });
      return;
    }
    const prev = legs.slice(0, -1).reverse().find(x => x.ok && !x.order);
    if (prev && info.dep.ms < prev.arr.ms) legNotes.push({ type: "warn", text: `구간 ${n} 출발(한국 ${info.dep.kst})이 구간 ${prev.n} 도착(한국 ${prev.arr.kst})보다 빠릅니다. 구간 순서와 일시를 확인하세요.` });
    const diff = localDay(info.arr.tz, info.arr.ms) - localDay(info.dep.tz, info.dep.ms);  // 현지 날짜 변경 수 (미주 서향 귀국편도 실제 기내 밤 수와 같음)
    if (diff > 0) {
      if (REG.transitModes.includes(mode)) { info.nights = diff; autoNights += diff; basis.push(`구간 ${n} ${diff}박`); }
      else legNotes.push({ type: "info", text: `구간 ${n}(${mode}): 숙박 박수에서 빼는 것은 항공·선박 이동뿐이므로 차감하지 않았습니다(제16조).` });
    }
  });
  const okLegs = legs.filter(l => l.ok);
  // 출장 기간 (2026-10-16 사용자 결정): 기본 정보의 출장 시작일·종료일을 우선 쓴다. 비어 있으면 이동 구간(한국 날짜)에서, 그것도 없으면 학회 기간에서 유도.
  // 기본 정보 외(이동 구간·금액 칸)는 필수가 아니다. 이동 구간은 기내박 계산과 출장 기간 검산에만 쓴다.
  let D = 0, tsN = null, teN = null, arrivalN = null, legsFallback = "";
  let legTs = null, legTe = null;
  if (okLegs.length) {
    const first = Math.min(...okLegs.map(l => l.dep.ms)), last = Math.max(...okLegs.map(l => l.arr.ms));
    legTs = kstDay(first); legTe = kstDay(last);
    if (legTe < legTs) err("cf-legs", "마지막 도착이 첫 출발보다 빠릅니다. 이동 구간을 확인하세요.");
  }
  const hasTrip = inp.ts && inp.te;
  if (hasTrip && dnum(inp.te) < dnum(inp.ts)) err("cf-te", "출장 종료일이 시작일보다 빠릅니다.");
  else if (hasTrip) {
    tsN = dnum(inp.ts); teN = dnum(inp.te); D = teN - tsN + 1;
    if (legTs != null && legTe >= legTs && (legTs !== tsN || legTe !== teN)) dateNotes.push({ type: "warn", text: `이동 구간으로 계산한 출장 기간(한국 날짜 ${dstr(legTs)} ~ ${dstr(legTe)})이 입력한 출장 기간(${inp.ts} ~ ${inp.te})과 다릅니다. 일수는 입력한 출장 기간으로 셉니다.` });
  } else if (inp.ts || inp.te) {
    miss(inp.ts ? "cf-te" : "cf-ts", "출장 " + (inp.ts ? "종료일" : "시작일"));
  } else if (legTs != null && legTe >= legTs) {
    tsN = legTs; teN = legTe; D = teN - tsN + 1;
    legsFallback = `출장 기간을 비워 이동 구간의 한국 날짜(${dstr(tsN)} ~ ${dstr(teN)}, ${D}일)로 셌습니다.`;
  } else if (inp.cs && inp.ce && dnum(inp.ce) >= dnum(inp.cs)) {
    tsN = dnum(inp.cs); teN = dnum(inp.ce); D = teN - tsN + 1;
    legsFallback = `출장 기간과 이동 구간이 없어 학회 기간(${inp.cs} ~ ${inp.ce}, ${D}일)을 출장 기간으로 보고 기내박 0박으로 계산했습니다.`;
  } else {
    legsFallback = "출장 기간·이동 구간·학회 기간이 없어 일수·박수를 0으로 두고 입력한 금액만 합산했습니다.";
  }
  if (D > 0) {
    const a0 = okLegs.length && !okLegs[0].order ? kstDay(okLegs[0].arr.ms) : null;  // 첫 구간 도착일(한국 날짜) = 현지 도착일
    arrivalN = a0 != null && a0 >= tsN && a0 <= teN ? a0 : tsN;
  }
  const ts = tsN != null ? dstr(tsN) : "", te = teN != null && D ? dstr(teN) : "";
  let confDays = 0, cutPre = 0, cutPost = 0; const { cs, ce } = inp;
  if (cs && ce) {
    if (dnum(ce) < dnum(cs)) err("cf-ce", "학회 종료일이 시작일보다 빠릅니다.");
    else {
      confDays = dnum(ce) - dnum(cs) + 1;
      if (D > 0) {
        const pre = dnum(cs) - tsN, post = teN - dnum(ce);
        if (pre < 0 || post < 0) dateNotes.push({ type: "warn", text: `학회 기간(${cs} ~ ${ce})이 출장 기간(${ts} ~ ${te}) 밖으로 나갑니다. 날짜를 확인하세요.` });
        else if (pre > 1 || post > 1) {
          cutPre = Math.max(0, pre - 1); cutPost = Math.max(0, post - 1);
          dateNotes.push({ type: "warn", text: `학회 전후로 각 1일씩만 출장으로 인정됩니다. 학회 앞 ${pre}일, 뒤 ${post}일 중 ${cutPre + cutPost}일을 공제일수로 보아 일비·식비에서 뺐습니다 (초과분을 인정받으려면 항공 스케줄표 등 소명 증빙이 필요합니다).` });
        }
      }
    }
  }
  const cutDays = cutPre + cutPost, Dpay = Math.max(0, D - cutDays);  // 일비·식비 지급 일수 = 출장일수 − 공제일수
  const payFrom = tsN != null ? tsN + cutPre : null, payTo = teN != null ? teN - cutPost : null;  // 인정 출장일 범위
  if (legsFallback) dateNotes.push({ type: "info", text: legsFallback });
  const tm = inp.transitManual;
  const transitNights = tm === null || tm === "" || tm === undefined || !Number.isFinite(Number(tm)) ? autoNights : Math.max(0, Math.floor(Number(tm)));
  const rawNights = Math.max(0, D - 1), nights = Math.max(0, rawNights - transitNights);

  // 지급기준
  const table = intl ? REG.intl : REG.dom;
  const g = table[inp.grade] || table["2"];
  const c = inp.cityGrade || "나";
  const ilbiDay = g.ilbi, mealDay = intl ? g.meal[c] : g.meal;
  const region = REG.regions.find(r => r.cap === Number(inp.region)) || REG.regions[0];
  const capNight = intl ? g.lodge[c] : (g.lodgeCap ? region.cap : null);
  const fxTxt = fmtN(fx);
  const pay = (v, k) => won(nz(v) * rateOf(cur(k)));
  const payTxt = (v, k, base) => (cur(k) !== "KRW" && nz(v) > 0) ? `${fmtC(nz(v), cur(k))} × 환율 ${fmtN(rateOf(cur(k)))}` : base;

  // 일비: 현지 도착 다음 날부터 세어 15일을 넘는 날은 감액(제17조)
  let ilbiSum = 0, reduced = 0;
  if (Dpay > 0) for (let d = payFrom; d <= payTo; d++) { const f = stayFactor(d - arrivalN); if (f < 1) reduced++; ilbiSum += ilbiDay * f; }
  const ilbiW = won(ilbiSum * fx);
  // 식비: 일수 × 정액 − 제공 식사 끼니 × (1일 식비 ÷ 3)
  const confMeals = nz(inp.confMeals), mealsCut = inflight + confMeals;
  const mealGross = Dpay * mealDay, mealDeduct = Math.min(mealGross, mealsCut * mealDay / REG.mealPerDay), mealSum = mealGross - mealDeduct;
  const mealW = won(mealSum * fx);
  // 숙박비: 결제액과 상한(1박 상한 × 인정 박수) 중 적은 금액
  const lodgePaidW = pay(inp.lodgePaid, "lodgeCur");
  const capW = capNight === null ? null : won(capNight * nights * fx);
  const capTxt = capNight === null ? "" : (intl ? `${nights}박 × ${fmtD(capNight)} × 환율 ${fxTxt}` : `${nights}박 × ${fmtN(capNight)}원`);
  let lodgeW, lodgeNote;
  if (capW === null) { lodgeW = lodgePaidW; lodgeNote = { type: "ok", text: "국내 제1호: 숙박비는 실비 전액이 지급됩니다(영수증 필수)." }; }
  else {
    lodgeW = Math.min(lodgePaidW, capW);
    if (lodgePaidW <= 0) lodgeNote = { type: "info", text: `숙박비 상한: ${fmtW(capW)} (${capTxt}). 결제액을 입력하면 지급액을 계산합니다.` };
    else if (nights <= 0) lodgeNote = { type: "warn", text: `인정 숙박 박수가 0박이라 숙박비 결제액 ${fmtW(lodgePaidW)}을 반영하지 않았습니다. 실제로 숙박했다면 이동 구간 일시와 기내박을 확인하세요.` };
    else if (lodgePaidW <= capW) lodgeNote = { type: "ok", text: `결제액 ${fmtW(lodgePaidW)}이 상한 ${fmtW(capW)} 이내이므로 전액 지급됩니다.` };
    else lodgeNote = { type: "warn", text: `결제액 ${fmtW(lodgePaidW)} 중 상한 ${fmtW(capW)}까지만 반영했습니다(초과분 ${fmtW(lodgePaidW - capW)}). 상한을 넘은 금액의 지급 가능 여부는 연구비 담당자에게 문의하세요.` };
  }
  const fareW = pay(inp.fare, "fareCur"), regW = pay(inp.regFee, "regCur"), printW = pay(inp.printFee, "printCur"), etcW = pay(inp.etcFee, "etcCur"), extW = pay(inp.extFund, "extCur");
  const travelW = fareW + ilbiW + lodgeW + mealW, sideW = regW + printW + etcW;
  const grandW = Math.max(0, travelW + sideW - extW);

  const redTxt = reduced ? ` (장기체재 감액 ${reduced}일 반영)` : "";
  const dayTxt = cutDays ? `(${D}일 − 공제 ${cutDays}일 = ${Dpay}일)` : `${D}일`;  // 공제일수 = 학회 전후 각 1일을 넘는 출장일
  const lines = [
    { kind: "travel", k: "운임 (실비)", amt: fareW, f: payTxt(inp.fare, "fareCur", "E-티켓·영수증 금액"), law: "실제 결제한 운임" },
    { kind: "travel", k: intl ? "일비 (현지 교통비 등)" : "일비", amt: ilbiW, f: intl ? `${fmtD(ilbiDay)} × ${dayTxt}${redTxt} = ${fmtD(ilbiSum)} × 환율 ${fxTxt}` : `${fmtN(ilbiDay)}원 × ${dayTxt}${redTxt}`, law: cutDays ? "인정 출장일(학회 전후 각 1일까지)만 정액 지급" : "여행일수만큼 정액 지급" },
    { kind: "travel", k: "숙박비 (실비, 상한 이내)", amt: lodgeW,
      f: (capW === null ? `실비 전액 (${nights}박)` : `인정 ${nights}박 (총 ${rawNights}박 − 기내박 ${transitNights}박), 상한 ${fmtW(capW)}`) + (cur("lodgeCur") !== "KRW" && nz(inp.lodgePaid) > 0 ? ` / 결제액 ${fmtC(nz(inp.lodgePaid), cur("lodgeCur"))} × 환율 ${fmtN(rateOf(cur("lodgeCur")))}` : ""),
      law: "결제액과 상한액 중 적은 금액" },
    { kind: "travel", k: "식비", amt: mealW,
      f: intl ? `${fmtD(mealDay)} × ${dayTxt} − ${mealsCut}끼 × ${fmtD(mealDay / REG.mealPerDay)} = ${fmtD(mealSum)} × 환율 ${fxTxt}` : `${fmtN(mealDay)}원 × ${dayTxt} − ${mealsCut}끼 × (${fmtN(mealDay)}원 ÷ ${REG.mealPerDay})`,
      law: "여행일수만큼 정액, 제공받은 식사는 1끼당 1/3 차감" },
    { kind: "sub", k: "여비 소계", amt: travelW, f: "" },
    { kind: "side", k: "학회 등록비", amt: regW, f: payTxt(inp.regFee, "regCur", "") },
    { kind: "side", k: "논문 인쇄비(게재료)", amt: printW, f: payTxt(inp.printFee, "printCur", "") },
    { kind: "side", k: "기타 부대비", amt: etcW, f: payTxt(inp.etcFee, "etcCur", "") },
  ];
  if (extW > 0) lines.push({ kind: "ext", k: "외부 지원금·주최측 제공액 차감", amt: -extW, f: payTxt(inp.extFund, "extCur", ""), law: "다른 곳에서 받은 여비는 빼고 지급 (제28조)" });
  lines.push({ kind: "total", k: "총 지급 예상액", amt: grandW, f: "항목별 원 미만 절사" });

  const notes = [];
  if (extW > travelW + sideW) notes.push({ type: "info", text: `외부 지원금 ${fmtW(extW)}이 산출액 ${fmtW(travelW + sideW)}보다 커서 총액은 0원입니다(항목 합계는 음수). 초과분은 지급하지 않습니다.` });
  if (Dpay > 0 && mealsCut > Dpay * REG.mealPerDay) notes.push({ type: "warn", text: `제공받은 식사 ${mealsCut}끼가 인정 출장 ${Dpay}일의 최대 끼니 수(${Dpay * REG.mealPerDay}끼)보다 많습니다. 입력을 확인하세요.` });
  if (mealsCut > 0) notes.push({ type: "info", text: `기내식 ${inflight}끼와 학회 제공 ${confMeals}끼를 반영해 식비에서 ${intl ? fmtD(mealDeduct) + " (" + fmtW(won(mealDeduct * fx)) + ")" : fmtW(won(mealDeduct))}을 차감했습니다.` });
  if (reduced > 0) notes.push({ type: "warn", text: `같은 지역에 오래 머무는 경우 현지 도착 다음 날(${dstr(arrivalN + 1)})부터 세어 15일을 넘는 ${reduced}일은 일비가 10~30% 감액됩니다(제17조). 숙박비와 식비는 감액하지 않았습니다.` });
  if (extW > 0 && travelW + sideW - extW < 0) notes.push({ type: "warn", text: "외부 지원금이 산출액보다 커서 총 지급 예상액을 0원으로 표시했습니다." });
  if (intl) notes.push({ type: "info", text: "항공권은 직급별 좌석 등급 기준이 있으나(별표3) 국책 재원 특성상 일반석(이코노미) 이용이 권고됩니다. 상위 등급 좌석을 이용하면 사유와 근거 자료를 확보하세요. 공적 항공마일리지는 우선 사용해야 합니다." });
  else notes.push({ type: "info", text: "자가용 이용 시 원칙은 철도·버스 운임 기준으로 지급하며, 부득이한 사유가 있으면 연료비·통행료 지급이 가능합니다(별표2 비고4). 같은 시·군 안 또는 12km 미만 출장은 이 계산의 대상이 아니며 정액만 지급됩니다(제18조)." });
  notes.push({ type: "danger", text: "병원/원내/위탁 여비의 중복 신청은 금지됩니다. 적발 시 환수되며 부정 수령 시 5배가 가산 징수됩니다." });
  const deadline = D > 0 ? dstr(teN + REG.settleDays) : "";
  const allNotes = [...dateNotes, ...legNotes, lodgeNote, ...notes];
  if (deadline) allNotes.push({ type: "info", text: `정산 신청 기한: 여행을 마친 다음 날부터 2주 이내 (${deadline}까지)` });

  const dkey = intl ? "intl" : "dom", checked = inp.docs || {};
  const docs = Object.keys(REG.docs[dkey]).map(sec => ({ sec, items: REG.docs[dkey][sec].map(t => ({ t, c: !!checked[dkey + "|" + t] })) }));
  const matched = intl && inp.citySearch && CITY_GRADE[inp.citySearch] === inp.cityGrade ? inp.citySearch : "";
  const gradeTxt = intl ? `${c}등급${matched ? ` (${matched})` : ""}` : `${region.name} (${g.lodgeCap ? `상한 ${fmtN(region.cap)}원/박` : "숙박 실비"})`;
  const meta = [
    ["출장 구분", intl ? "국외" : "국내"], ["직급(여비지급) 구분", g.name], [intl ? "도시 등급" : "숙박 지역", gradeTxt],
    ...(intl ? [["적용 환율(원/USD)", fxTxt + (inp.fxDate ? ` (기준일 ${inp.fxDate})` : "")]] : []),
    ...(intl && usedCurs.length ? [["결제 통화 환율", usedCurs.map(c => `${c} ${fmtN(rateOf(c))}`).join(" · ")]] : []),
    ["출장 기간", `${ts || "-"} ~ ${te || "-"} (${D}일${cutDays ? ` · 공제 ${cutDays}일 → 일비·식비 ${Dpay}일` : ""})`],
    ["학회 기간", `${cs || "-"} ~ ${ce || "-"}${confDays ? ` (${confDays}일)` : ""}`],
    ["숙박 박수", `총 ${rawNights}박 − 기내박 ${transitNights}박${tm != null && tm !== "" ? " (직접 입력)" : ""} = 인정 ${nights}박`],
    ["식비 차감", `기내식 ${inflight}끼 + 학회 제공 ${confMeals}끼`],
    ["금액 처리", "항목별 원 미만 절사"],
  ];
  const legRows = legs.filter(l => l.ok).map(l => ({ n: l.n, mode: l.mode, meal: l.meal, nights: l.nights, order: !!l.order,
    dep: { place: l.dep.place || "", tz: l.dep.tz, local: l.dep.local, off: l.dep.off, kst: l.dep.kst }, arr: { place: l.arr.place || "", tz: l.arr.tz, local: l.arr.local, off: l.arr.off, kst: l.arr.kst } }));
  return {
    intl, blocked: missing.length > 0 || errors.length > 0, missing, errors,
    D, Dpay, cutDays, ts, te, confDays, rawNights, nights, transitNights, autoNights, basis, inflight, confMeals, mealsCut, reduced, fx, fxTable: Object.fromEntries(["USD", ...usedCurs].map(c => [c, rateOf(c)])),
    ilbiDay, mealDay, capNight, capW, lodgePaidW, legs, legRows, lines, notes: allNotes, docs, meta, gradeTxt,
    fareW, ilbiW, lodgeW, mealW, regW, printW, etcW, extW, travelW, sideW, grandW, deadline,
  };
}
// 상세 JSON 의 out (저장·드로어·인쇄용 요약)
function outOf(res, inp) {
  return {
    합계: res.grandW, 여비: res.travelW, 부대비: res.sideW, 외부지원: res.extW, 일수: res.D, 공제일수: res.cutDays, 지급일수: res.Dpay, 박수: res.nights, 총박수: res.rawNights, 기내박: res.transitNights,
    등급: res.intl ? (inp.cityGrade || "나") + "등급" : res.gradeTxt, 구분: res.intl ? "국외" : "국내", 환율: res.intl ? res.fx : null, 환율표: res.intl ? res.fxTable : null, 환율기준일: res.intl ? (inp.fxDate || "") : "",
    기준: "KST", 기간: [res.ts, res.te], 등록비: res.regW,
    lines: res.lines.map(l => ({ kind: l.kind, k: l.k, f: l.f || "", law: l.law || "", amt: l.amt })),
    legs: res.legRows, meta: res.meta, notes: res.notes, docs: res.docs, basis: REG.basis, 계산일: today(),
  };
}

// ---------- 화면 ----------
const CF = { mode: "edit", ctx: {}, res: null, inp: null, saved: null, docs: {}, fxKeep: {}, initial: "" };
const dlg = () => $("#dlg-conf");
const val = id => $("#" + id)?.value ?? "";
const numVal = id => nz(String(val(id)).replace(/[,\s원$]/g, ""));
const curSel = (id, label) => `<select id="${id}" class="cf-cur" aria-label="${esc(label)} 통화">${CURRENCIES.map(([c]) => `<option value="${c}">${c === "KRW" ? "₩" : c}</option>`).join("")}</select>`;
const lab = (text, hint) => `<span class="lab">${esc(text)}${hint ? ` <small>(${esc(hint)})</small>` : ""}</span>`;
const money = (id, label, hint) => `<label for="${id}">${lab(label, hint)}<span class="cf-money"><input type="text" id="${id}" class="num-input" inputmode="decimal" placeholder="0" autocomplete="off">${curSel(id + "-cur", label)}</span></label>`;
function tzOptions() {
  return TZ_GROUPS.map(([g, list]) => `<optgroup label="${esc(g)}">${list.map(([z, l]) => `<option value="${z}">${esc(l)} · ${z}</option>`).join("")}</optgroup>`).join("")
    + `<option value="${TZ_OTHER}">기타 (IANA 이름 직접 입력)</option>`;
}

function buildShell() {
  const d = dlg(); if (d.dataset.built) return;
  d.dataset.built = "1";
  $("#conf-basis").textContent = `근거: ${REG.basis} · 과제별 지급기준이 따로 있으면 그 기준이 우선합니다. ${KST_NOTE.split(".")[0]}. 여비는 신청인 1인 기준입니다.`;
  $("#conf-in").innerHTML = `
    <fieldset class="cf-fs" id="cf-fs">
    <section class="cf-sec" aria-labelledby="cf-h1">
      <h3 id="cf-h1">기본 정보</h3>
      <div class="fields">
        <label for="cf-trip">출장 구분<select id="cf-trip"><option value="intl">국외</option><option value="dom">국내</option></select></label>
        <label for="cf-grade" class="mid">직급(여비지급) 구분<select id="cf-grade"></select></label>
        <label class="chk wide cf-intl" for="cf-showall"><input type="checkbox" id="cf-showall"> 차관급·1급 상당 직급도 표시 (해당자만 선택)</label>
        <label for="cf-city" class="cf-intl">${lab("국가·도시 검색", "등급 자동 선택")}<input type="text" id="cf-city" list="cf-citylist" placeholder="예: 미국, 도쿄, 싱가포르" autocomplete="off"></label>
        <label for="cf-cgrade" class="cf-intl">${lab("도시 등급", "숙박비 상한·식비 기준")}<select id="cf-cgrade"><option value="">(선택)</option><option value="가">가 등급 (도쿄·뉴욕·런던·파리·싱가포르 등 도시)</option><option value="나">나 등급 (미국·일본·독일·영국·호주 등)</option><option value="다">다 등급 (중국·태국·말레이시아·브라질 등)</option><option value="라">라 등급 (베트남·필리핀·몽골·페루 등)</option></select></label>
        <label for="cf-region" class="cf-dom">숙박 지역 (국내)<select id="cf-region">${REG.regions.map(r => `<option value="${r.cap}">${esc(r.name)} (상한 ${fmtN(r.cap)}원/박)</option>`).join("")}</select></label>
        <p class="toolbar-note cf-intl" id="cf-city-hint" aria-live="polite"></p>
        <label for="cf-fx" class="cf-intl">적용 환율 (원/USD)<input type="text" id="cf-fx" class="num-input" inputmode="decimal" placeholder="예: 1380" autocomplete="off"></label>
        <label for="cf-fxdate" class="cf-intl">${lab("환율 기준일", "선택")}<input type="date" id="cf-fxdate"></label>
        <div id="cf-fxs" class="cf-intl"></div>
        <p class="toolbar-note cf-intl">지급기준표가 미국 달러 기준입니다. 실제 결제일의 기준환율을 입력하세요. 다른 통화로 결제한 금액은 그 통화를 고르면 환율 칸이 추가됩니다(모두 원/1단위 기준. 100엔 단위 고시 환율은 100으로 나눠 입력).</p>
        <label for="cf-ts">${lab("출장 시작일", "비우면 이동 구간·학회 기간에서")}<input type="date" id="cf-ts"></label>
        <label for="cf-te">출장 종료일<input type="date" id="cf-te"></label>
        <label for="cf-cs">학회 시작일<input type="date" id="cf-cs"></label>
        <label for="cf-ce">학회 종료일<input type="date" id="cf-ce"></label>
        <p class="toolbar-note wide">출장은 학회 전후로 각 1일까지만 인정됩니다. 더 길면 주의 문구가 붙고 소명 증빙이 필요합니다.</p>
      </div>
    </section>
    <section class="cf-sec" aria-labelledby="cf-h2">
      <h3 id="cf-h2">이동 구간</h3>
      <p class="toolbar-note cf-intl">출발·도착을 각각 현지 시각과 시간대로 입력하면 한국 시각으로 환산합니다. 날짜는 2026-10-04 10:00 처럼 직접 입력할 수 있습니다.</p>
      <div class="table-wrap cf-legwrap"><table class="grid compact cf-legs" id="cf-legs">
        <thead><tr><th scope="col" class="ctr">구간</th><th scope="col">수단</th><th scope="col"><span class="sr-only">출발·도착</span></th><th scope="col">장소</th><th scope="col">시간대</th><th scope="col">현지 일시</th><th scope="col">한국 시각 (KST)</th><th scope="col" class="num">기내박</th><th scope="col" class="num">기내식(끼)</th><th scope="col"><span class="sr-only">작업</span></th></tr></thead>
        <tbody id="cf-legbody"></tbody>
      </table></div>
      <div class="cf-row"><button type="button" class="btn btn-sm" id="cf-addleg">구간 추가</button><span class="toolbar-note">${esc(KST_NOTE)}</span></div>
      <div class="fields">
        ${money("cf-fare", "운임 합계", "실비·결제액")}
        <label for="cf-transit">${lab("기내박 직접 입력", "비우면 자동 계산")}<input type="text" id="cf-transit" class="num-input" inputmode="numeric" placeholder="자동" autocomplete="off"></label>
        <p class="toolbar-note" id="cf-transit-hint"></p>
      </div>
    </section>
    <section class="cf-sec" aria-labelledby="cf-h3">
      <h3 id="cf-h3">숙박비 · 식비 · 부대비용</h3>
      <div class="fields">
        ${money("cf-lodge", "숙박비 총 결제액", "인보이스·영수증")}
        <label for="cf-confmeals">학회(주최측) 제공 식사 (끼)<input type="text" id="cf-confmeals" class="num-input" inputmode="numeric" placeholder="0" autocomplete="off"></label>
        <label for="cf-inflight">${lab("기내식 합계", "구간에서 자동")}<input type="text" id="cf-inflight" readonly tabindex="-1"></label>
        ${money("cf-reg", "학회 등록비")}
        ${money("cf-print", "논문 인쇄비(게재료)")}
        ${money("cf-etc", "기타", "초록집 등")}
        ${money("cf-ext", "외부 지원금·주최측 제공액", "있을 때만")}
        <p class="toolbar-note mid">학회 여행 지원금(travel grant) 등 다른 곳에서 여비를 받았다면 그 금액만큼 빼고 지급됩니다(제28조). 등록비는 청구서(인보이스)와 결제 영수증이 필요합니다.</p>
      </div>
    </section>
    </fieldset>
    <datalist id="cf-citylist">${Object.keys(CITY_GRADE).sort((a, b) => a.localeCompare(b, "ko")).map(n => `<option value="${esc(n)}" label="${esc(n)} (${CITY_GRADE[n]}등급)">`).join("")}</datalist>`;
  const box = $("#conf-in");
  box.addEventListener("input", onInput);
  box.addEventListener("change", onInput);
  $("#cf-legbody").addEventListener("click", e => {
    const b = e.target.closest("[data-legdel]"); if (!b || CF.mode !== "edit") return;
    const tr = b.closest("tr"); const i = Number(tr.dataset.leg);
    $$(`#cf-legbody tr[data-leg="${i}"]`).forEach(x => x.remove()); relabelLegs(); update();
    ($("#cf-legbody [data-legdel]") || $("#cf-addleg")).focus();
  });
  $("#cf-addleg").addEventListener("click", () => {
    const legs = readLegs(), last = legs[legs.length - 1];
    addLeg({ mode: "항공", meal: 0, dep: { place: last?.arr.place || "", tz: last?.arr.tz || "", at: "" }, arr: { place: "", tz: "", at: "" } });
    relabelLegs(); update(); $$("#cf-legbody tr").slice(-2)[0]?.querySelector(".lg-place")?.focus();
  });
  $("#conf-out").addEventListener("change", e => {
    const cb = e.target.closest("input[data-doc]"); if (!cb || CF.mode !== "edit") return;
    if (cb.checked) CF.docs[cb.dataset.doc] = true; else delete CF.docs[cb.dataset.doc];
    // 다시 그리지 않는다: 체크 상태는 CF.docs 에만 두고 적용·인쇄 때 readInputs 로 읽는다 (다시 그리면 포커스·연속 클릭을 잃음)
  });
  $("#conf-out").addEventListener("click", e => {
    const b = e.target.closest("[data-focus]"); if (!b) return;
    const id = b.dataset.focus;
    const el = id === "cf-legs" ? $("#cf-legbody .lg-at") : id.startsWith("leg-") ? legField(id) : $("#" + id);
    if (el) { el.focus(); el.scrollIntoView?.({ block: "center" }); }
  });
}

// 미입력 id "leg-<j>-<dep|arr>-<at|tz>" → 그 칸 (j 는 표 순서)
function legField(id) {
  const m = /^leg-(\d+)-(dep|arr)-(at|tz)$/.exec(id); if (!m) return null;
  const tr = $$("#cf-legbody tr.cf-dep")[Number(m[1])]; if (!tr) return null;
  const i = tr.dataset.leg, cls = m[3] === "at" ? ".lg-at" : ".lg-tz";
  const el = $(`#cf-legbody tr[data-leg="${i}"] ${cls}[data-end="${m[2]}"]`);
  if (cls === ".lg-tz" && el && el.value === TZ_OTHER) { const o = el.parentElement.querySelector(".lg-tzo"); if (o && !o.hidden) return o; }
  return el;
}
function endCells(i, k, e) {
  const label = k === "dep" ? "출발" : "도착", n = i + 1;
  const known = TZ_LIST.includes(e.tz), other = e.tz && !known;
  return `<td class="cf-end">${label}</td>
    <td><input type="text" class="lg-place" data-end="${k}" value="${esc(e.place || "")}" placeholder="도시·국가" aria-label="구간 ${n} ${label} 장소" autocomplete="off"></td>
    <td><select class="lg-tz" data-end="${k}" aria-label="구간 ${n} ${label} 시간대"${e.tz ? ' data-manual="1"' : ""}><option value="">(시간대 선택)</option>${tzOptions()}</select>
      <input type="text" class="lg-tzo" data-end="${k}" value="${other ? esc(e.tz) : ""}" placeholder="예: Europe/Lisbon" aria-label="구간 ${n} ${label} 시간대 IANA 이름" autocomplete="off" spellcheck="false"${other ? "" : " hidden"}></td>
    <td><input type="datetime-local" class="lg-at" data-end="${k}" value="${esc(e.at || "")}" aria-label="구간 ${n} ${label} 현지 일시"></td>
    <td class="cf-kst" data-kst="${k}"></td>`;
}
function addLeg(l) {
  const i = $$("#cf-legbody tr[data-leg]").reduce((m, tr) => Math.max(m, Number(tr.dataset.leg) + 1), 0);
  const tb = $("#cf-legbody");
  tb.insertAdjacentHTML("beforeend", `<tr data-leg="${i}" class="cf-dep">
      <th scope="rowgroup" rowspan="2" class="ctr cf-n"></th>
      <td rowspan="2"><select class="lg-mode">${REG.modes.map(m => `<option${m === l.mode ? " selected" : ""}>${m}</option>`).join("")}</select></td>
      ${endCells(i, "dep", l.dep || {})}
      <td rowspan="2" class="num cf-nights"></td>
      <td rowspan="2" class="num"><input type="text" class="lg-meal num-input" inputmode="numeric" value="${nz(l.meal) || ""}" placeholder="0" autocomplete="off"></td>
      <td rowspan="2" class="ctr"><button type="button" class="btn btn-sm btn-danger" data-legdel>삭제</button></td>
    </tr><tr data-leg="${i}" class="cf-arr">${endCells(i, "arr", l.arr || {})}</tr>`);
  $$(`#cf-legbody tr[data-leg="${i}"] .lg-tz`).forEach(sel => {
    const k = sel.dataset.end, tz = (l[k] || {}).tz || "";
    sel.value = !tz ? "" : TZ_LIST.includes(tz) ? tz : TZ_OTHER;
  });
}
function relabelLegs() {
  const firsts = $$("#cf-legbody tr.cf-dep");
  firsts.forEach((tr, j) => {
    const n = j + 1, i = tr.dataset.leg;
    tr.querySelector(".cf-n").textContent = n;
    tr.querySelector(".lg-mode").setAttribute("aria-label", `구간 ${n} 이동수단`);
    tr.querySelector(".lg-meal").setAttribute("aria-label", `구간 ${n} 기내식 끼니 수`);
    tr.querySelector("[data-legdel]").setAttribute("aria-label", `구간 ${n} 삭제`);
    $$(`#cf-legbody tr[data-leg="${i}"] [aria-label]`).forEach(el => { el.setAttribute("aria-label", el.getAttribute("aria-label").replace(/^구간 \d+/, `구간 ${n}`)); });
  });
}
function readEnd(i, k) {
  const q = s => $(`#cf-legbody tr[data-leg="${i}"] ${s}[data-end="${k}"]`);
  const sel = q(".lg-tz").value;
  return { place: q(".lg-place").value.trim(), tz: sel === TZ_OTHER ? q(".lg-tzo").value.trim() : sel, at: q(".lg-at").value };
}
function readLegs() {
  return $$("#cf-legbody tr.cf-dep").map(tr => {
    const i = tr.dataset.leg;
    return { mode: tr.querySelector(".lg-mode").value, meal: nz(String(tr.querySelector(".lg-meal").value).replace(/[,\s]/g, "")), dep: readEnd(i, "dep"), arr: readEnd(i, "arr") };
  });
}

function refreshGrades(want) {
  const intl = val("cf-trip") !== "dom", src = intl ? REG.intl : REG.dom, sel = $("#cf-grade");
  if (intl && src[want]?.rare) $("#cf-showall").checked = true;
  const all = $("#cf-showall").checked;
  sel.innerHTML = Object.entries(src).filter(([, g]) => !g.rare || all).map(([k, g]) => `<option value="${k}">${esc(g.name)}</option>`).join("");
  sel.value = [...sel.options].some(o => o.value === want) ? want : (intl && want !== "2" ? "1ra" : "2");
}
const mapGrade = (prev, to) => to === "intl" ? (prev === "1" ? "1ra" : prev === "2" ? "2" : prev) : (prev === "2" ? "2" : "1");
function syncTrip() {
  const intl = val("cf-trip") !== "dom";
  $$("#conf-in .cf-intl").forEach(el => { el.hidden = !intl; });
  $$("#conf-in .cf-dom").forEach(el => { el.hidden = intl; });
  $$("#conf-in .cf-cur").forEach(s => { s.hidden = !intl; });  // 값은 보존: 국내로 갔다가 돌아와도 통화·환율이 남는다 (compute 가 국내에서는 KRW 로 계산)
  $("#cf-legs")?.classList.toggle("cf-domestic", !intl);  // 국내: 시간대·한국 시각·기내박 열 숨김 (compute 가 KST 로 고정)
  syncFxRows();
}
// 사용 중인 결제 통화(KRW·USD 제외)마다 환율 칸을 하나씩 둔다 (사용자 결정: 통화별 한 번만 입력)
function syncFxRows(rates) {
  const box = $("#cf-fxs"); if (!box) return;
  const intl = val("cf-trip") !== "dom";
  $$("#cf-fxs input").forEach(i => { CF.fxKeep[i.dataset.cur] = i.value; });  // 칸이 사라져도 값은 기억 (토글 왕복·통화 변경 복원)
  if (rates) Object.entries(rates).forEach(([c, v]) => { if (v) CF.fxKeep[c] = fmtN(v); });
  const used = intl ? [...new Set($$("#conf-in .cf-cur").map(s => s.value).filter(c => c !== "KRW" && c !== "USD"))] : [];
  box.innerHTML = used.map(c => `<label for="cf-fx-${c}">${lab(`적용 환율 (원/${c})`, CUR_NAME[c] || "")}<input type="text" id="cf-fx-${c}" class="num-input cf-fx-cur" data-cur="${c}" inputmode="decimal" placeholder="예: 1500" autocomplete="off"></label>`).join("");
  used.forEach(c => { const v = CF.fxKeep[c]; if (v) $("#cf-fx-" + c).value = String(v); });
  box.hidden = !used.length;
}
const readFxs = () => Object.fromEntries($$("#cf-fxs input").map(i => [i.dataset.cur, numVal(i.id)]).filter(([, v]) => v > 0));
function cityHint() {
  const q = val("cf-city").trim(), g = CITY_GRADE[q];
  $("#cf-city-hint").textContent = !q ? CITY_HINT : g ? `${q}: ${g}등급을 적용했습니다.` : "목록에 없습니다. 등급을 직접 선택하세요. 지급표에 없는 국가는 가장 가까운 국가의 등급을 적용합니다(별표4 비고3).";
}

function onInput(e) {
  if (CF.mode !== "edit") return;
  const t = e.target;
  if (t.id === "cf-trip" && e.type === "change") { refreshGrades(mapGrade(val("cf-grade"), val("cf-trip"))); syncTrip(); }
  else if (t.id === "cf-showall") refreshGrades(val("cf-grade"));
  else if (t.classList.contains("cf-cur") && e.type === "change") syncFxRows();
  else if (t.id === "cf-city" && e.type === "input") {
    const q = t.value.trim(), g = CITY_GRADE[q];
    if (g) $("#cf-cgrade").value = g; else if (q) $("#cf-cgrade").value = "";
    cityHint();
  }
  else if (t.id === "cf-cgrade" && e.type === "change") { if (CITY_GRADE[val("cf-city").trim()] !== t.value) { $("#cf-city").value = ""; cityHint(); } }
  else if (t.classList.contains("lg-tz") && e.type === "change") {
    t.dataset.manual = "1";
    const o = t.parentElement.querySelector(".lg-tzo"); o.hidden = t.value !== TZ_OTHER;
    if (!o.hidden) o.focus();
  }
  else if (t.classList.contains("lg-place") && e.type === "input") {
    const sel = t.closest("tr").querySelector(`.lg-tz[data-end="${t.dataset.end}"]`), z = placeTz(t.value);
    if (sel && !sel.dataset.manual && z) sel.value = z;
  }
  if (e.type === "input" && (t.tagName === "SELECT" || t.type === "checkbox")) return;  // select·체크는 change 에서 한 번만
  if (e.type === "change" && t.tagName === "INPUT" && t.type !== "checkbox") return;  // 글자·숫자·날짜 칸은 input 에서 이미 갱신 (blur 의 change 로 다시 그리면 다음 클릭을 잃음)
  update();
}

function readInputs() {
  const tr = val("cf-transit").trim();
  return {
    tripType: val("cf-trip") === "dom" ? "dom" : "intl", grade: val("cf-grade"), showAll: $("#cf-showall").checked,
    citySearch: val("cf-city").trim(), cityGrade: val("cf-cgrade"), region: Number(val("cf-region")), fx: numVal("cf-fx"), fxs: readFxs(), fxDate: val("cf-fxdate"),
    ts: val("cf-ts"), te: val("cf-te"), cs: val("cf-cs"), ce: val("cf-ce"), legs: readLegs(), transitManual: tr === "" || !Number.isFinite(Number(tr.replace(/[,\s]/g, ""))) ? null : Math.max(0, Math.floor(Number(tr.replace(/[,\s]/g, "")))),
    fare: numVal("cf-fare"), fareCur: val("cf-fare-cur"), lodgePaid: numVal("cf-lodge"), lodgeCur: val("cf-lodge-cur"), confMeals: Math.floor(numVal("cf-confmeals")),
    regFee: numVal("cf-reg"), regCur: val("cf-reg-cur"), printFee: numVal("cf-print"), printCur: val("cf-print-cur"),
    etcFee: numVal("cf-etc"), etcCur: val("cf-etc-cur"), extFund: numVal("cf-ext"), extCur: val("cf-ext-cur"), docs: { ...CF.docs },
  };
}
function applyInputs(inp) {
  const s = { ...defaultInputs(), ...inp };
  const set = (id, v) => { const el = $("#" + id); if (el) el.value = v ?? ""; };
  const amt = v => nz(v) ? fmtN(v) : "";  // 천 단위 구분 (numVal 이 쉼표를 지우므로 안전)
  CF.fxKeep = {};
  set("cf-trip", s.tripType === "dom" ? "dom" : "intl");
  $("#cf-showall").checked = !!s.showAll;
  refreshGrades(String(s.grade || "2")); syncTrip();
  set("cf-city", s.citySearch); set("cf-cgrade", s.cityGrade); set("cf-region", String(s.region || 100000)); if (!$("#cf-region").value) $("#cf-region").selectedIndex = 0;
  set("cf-fx", amt(s.fx)); set("cf-fxdate", s.fxDate); set("cf-ts", s.ts); set("cf-te", s.te); set("cf-cs", s.cs); set("cf-ce", s.ce);
  set("cf-transit", s.transitManual == null ? "" : String(s.transitManual));
  [["cf-fare", "fare", "fareCur"], ["cf-lodge", "lodgePaid", "lodgeCur"], ["cf-reg", "regFee", "regCur"], ["cf-print", "printFee", "printCur"], ["cf-etc", "etcFee", "etcCur"], ["cf-ext", "extFund", "extCur"]]
    .forEach(([id, k, ck]) => { set(id, amt(s[k])); set(id + "-cur", s.tripType === "dom" ? "KRW" : curCode(s[ck])); });
  syncFxRows(s.fxs && typeof s.fxs === "object" ? s.fxs : {});
  set("cf-confmeals", amt(s.confMeals));
  $("#cf-legbody").innerHTML = "";
  (Array.isArray(s.legs) && s.legs.length ? s.legs : defaultInputs().legs).forEach(addLeg);
  relabelLegs();
  CF.docs = s.docs && typeof s.docs === "object" ? { ...s.docs } : {};
  cityHint();
}

const noteLi = n => `<li class="${esc(n.type)}"><b>${esc(NOTE_LABEL[n.type] || n.type)}</b>${esc(n.text)}</li>`;
function linesTable(lines, cap) {
  return `<table class="grid compact cf-lines"><caption class="sr-only">${esc(cap)}</caption><thead><tr><th scope="col">항목</th><th scope="col">산식·비고</th><th scope="col" class="num amt">금액(원)</th></tr></thead><tbody>${lines.map(l => {
    const tot = l.kind === "total", sub = l.kind === "sub";
    return `<tr class="${tot ? "total" : sub ? "cf-subtot" : ""}"><td>${esc(l.k)}${l.law ? `<div class="cf-law">${esc(l.law)}</div>` : ""}</td><td class="cf-f">${esc(l.f || "")}</td><td class="num amt${l.amt < 0 ? " neg" : ""}">${l.amt < 0 ? "−" + fmtN(-l.amt) : fmtN(l.amt)}</td></tr>`;
  }).join("")}</tbody></table>`;
}
function docsHtml(docs, ro) {
  return docs.map(s => `<h4>${esc(s.sec)}</h4><ul class="cf-docs">${s.items.map(it => {
    const key = (s.sec in REG.docs.intl ? "intl" : "dom") + "|" + it.t;
    return `<li><label class="chk"><input type="checkbox" data-doc="${esc(key)}"${it.c ? " checked" : ""}${ro ? " disabled" : ""}> <span>${esc(it.t)}</span></label></li>`;
  }).join("")}</ul>`).join("");
}
function summaryCards(o) {
  const card = (k, v, cls = "") => `<div class="card"><div class="k">${esc(k)}</div><div class="v${cls}">${v}</div></div>`;
  return card("총 지급 예상액", esc(fmtW(o.합계))) + card("여비", esc(fmtW(o.여비))) + card("부대비", esc(fmtW(o.부대비))) + card("외부 지원 차감", o.외부지원 ? "−" + esc(fmtW(o.외부지원)) : "0원", o.외부지원 ? " neg" : "")
    + card("일수 · 박수", `${o.일수}일 · ${o.박수}박`) + (o.구분 === "국내" ? card("숙박 지역", `${esc(String(o.등급).split(" (")[0])}${/\(/.test(o.등급) ? `<div class="cf-sub">${esc(o.등급.slice(o.등급.indexOf("(") + 1).replace(/\)$/, ""))}</div>` : ""}`) : card("도시 등급", esc(o.등급)));
}
function renderOut(res) {
  const out = $("#conf-out");
  const sum = $("#conf-sum");
  const docsEl = $("#cf-docs");
  if (res.blocked) {
    sum.innerHTML = `<div class="card cf-blocked"><div class="k">총 지급 예상액</div><div class="v">입력 미완료</div></div>`;
    out.innerHTML = `<section class="cf-sec"><h3>계산하려면</h3><ul class="cf-todo">${[...res.missing.map(m => `<li><button type="button" class="lnk" data-focus="${esc(m.id)}">${esc(m.msg)} 입력</button></li>`), ...res.errors.map(e => `<li class="cf-err"><button type="button" class="lnk" data-focus="${esc(e.id)}">${esc(e.msg)}</button></li>`)].join("")}</ul>
      ${res.notes.length ? `<ul class="cf-notes">${res.notes.filter(n => n.type === "warn").map(noteLi).join("")}</ul>` : ""}</section>`;
    return;
  }
  const o = outOf(res, CF.inp);
  sum.innerHTML = summaryCards(o);
  const drift = CF.mode === "view" && CF.saved && CF.saved.합계 !== res.grandW
    ? `<p class="toolbar-note warn">저장된 합계 ${esc(fmtW(CF.saved.합계))}와 지금 규정으로 다시 계산한 합계 ${esc(fmtW(res.grandW))}가 다릅니다. 인쇄는 저장된 산출 내역으로 합니다.</p>` : "";
  out.innerHTML = drift + `<div class="cf-cols">
    <section class="cf-sec" aria-labelledby="cf-h-lines"><h3 id="cf-h-lines">산출 내역</h3>${linesTable(res.lines, "산출 내역")}
      <p class="toolbar-note cf-basisnote"><b>기준</b> ${esc(KST_NOTE)} 출장 기간 ${esc(res.ts)} ~ ${esc(res.te)} (한국 날짜 ${res.D}일), 기내박 ${res.transitNights}박${res.basis.length ? " (" + esc(res.basis.join(", ")) + ")" : ""}.</p></section>
    <div><section class="cf-sec" aria-labelledby="cf-h-notes"><h3 id="cf-h-notes">안내</h3><ul class="cf-notes">${res.notes.map(noteLi).join("")}</ul></section>
      <section class="cf-sec" aria-labelledby="cf-h-docs"><h3 id="cf-h-docs">제출 서류 체크리스트</h3><div id="cf-docs-slot"></div></section></div>
  </div><p class="toolbar-note cf-disc">※ ${esc(REG.disclaimer)}</p>`;
  // 체크리스트 노드는 다시 쓰지 않고 옮겨 둔다: 숫자 칸 blur 가 input 을 다시 보내 산출 영역이 다시 그려져도 체크 클릭·포커스가 유지된다
  const key = (res.intl ? "intl" : "dom") + (CF.mode !== "edit" ? "|ro" : "");
  const slot = $("#cf-docs-slot");
  if (docsEl && docsEl.dataset.key === key) slot.replaceWith(docsEl);
  else { const d = document.createElement("div"); d.id = "cf-docs"; d.dataset.key = key; d.innerHTML = docsHtml(res.docs, CF.mode !== "edit"); slot.replaceWith(d); }
}
function renderLegs(res) {
  $$("#cf-legbody tr.cf-dep").forEach((tr, j) => {
    const L = res.legs[j] || {}, i = tr.dataset.leg;
    ["dep", "arr"].forEach(k => {
      const cell = $(`#cf-legbody tr[data-leg="${i}"] [data-kst="${k}"]`), e = L[k] || {};
      cell.textContent = e.kst ? `${e.kst}` : "";
      cell.title = e.kst ? `현지 ${e.local} (${e.tz}, ${e.off})` : "";
      cell.classList.toggle("cf-bad", !!L.order);
      const tzo = $(`#cf-legbody tr[data-leg="${i}"] .lg-tzo[data-end="${k}"]`), sel = $(`#cf-legbody tr[data-leg="${i}"] .lg-tz[data-end="${k}"]`);
      const badTz = res.errors.some(x => x.id === `leg-${j}-${k}-tz`);
      const mark = (el, on) => on ? el.setAttribute("aria-invalid", "true") : el.removeAttribute("aria-invalid");
      mark(tzo, badTz && !tzo.hidden); mark(sel, badTz && tzo.hidden);
    });
    tr.querySelector(".cf-nights").textContent = L.ok ? (L.order ? "0 (확인)" : String(L.nights)) : "";
  });
  $("#cf-inflight").value = res.inflight + " 끼";
  $("#cf-transit-hint").textContent = `자동 계산: ${res.autoNights}박${res.basis.length ? " (" + res.basis.join(", ") + ")" : ""}. 실제와 다르면 직접 입력하세요.`;
}
function update() {
  const inp = readInputs();
  if (CF.res && JSON.stringify(inp) === JSON.stringify(CF.inp)) return;  // 값이 같으면(숫자 칸 blur 의 쉼표 재서식 등) 다시 그리지 않는다 → 체크리스트 클릭·포커스 유지
  CF.inp = inp;
  CF.res = compute(CF.inp);
  renderLegs(CF.res); renderOut(CF.res);
  $("#conf-apply").disabled = CF.res.blocked;
  $("#conf-print").disabled = CF.res.blocked && !(CF.mode === "view" && CF.saved);
}

// ---------- 신청 폼 연동 ----------
function calcFromForm() { const el = F("_calc"); if (!el || !el.value) return null; try { const c = JSON.parse(el.value); return c && c.in ? c : null; } catch { return null; } }
function formCtx() {
  const v = k => F(k)?.value?.trim() || "";
  return { 신청번호: v("신청번호") === "(자동)" ? "" : v("신청번호"), 신청인: v("신청인"), 학회명: v("품목"), 관련과제: v("관련과제") };
}
function ctxOfRec(r) { return { 신청번호: r?.["신청번호"] || "", 신청인: r?.["신청인"] || "", 학회명: r?.["품목"] || "", 관련과제: r?.["관련과제"] || "" }; }
function seedFromForm(inp) {  // 새 계산: 신청 폼의 학회 칸으로 시작값
  const v = k => F(k)?.value?.trim() || "";
  if (v("_국내외") === "국내") { inp.tripType = "dom"; inp.grade = "2"; inp.legs = [{ mode: "철도", meal: 0, dep: { place: "", tz: KST, at: "" }, arr: { place: "", tz: KST, at: "" } }, { mode: "철도", meal: 0, dep: { place: "", tz: KST, at: "" }, arr: { place: "", tz: KST, at: "" } }]; }
  if (v("_시작일")) inp.cs = v("_시작일");
  if (v("_종료일")) inp.ce = v("_종료일");
  const place = v("_장소");
  if (place) {
    const hit = Object.keys(CITY_GRADE).sort((a, b) => b.length - a.length).find(n => place.includes(n));
    if (hit && inp.tripType !== "dom") { inp.citySearch = hit; inp.cityGrade = CITY_GRADE[hit]; }
    const z = placeTz(place);
    if (inp.tripType !== "dom") { inp.legs[0].arr.place = place; inp.legs[0].arr.tz = z; inp.legs[1].dep.place = place; inp.legs[1].dep.tz = z; }
  }
  const reg = numOf(v("_등록비")); if (reg) inp.regFee = reg;
  return inp;
}

function mergeForm(inp) {  // 기존 계산을 다시 열 때: 폼에서 바꾼 학회 기간·등록비를 계산 입력에 반영
  const v = k => F(k)?.value?.trim() || "";
  if (v("_시작일")) inp.cs = v("_시작일");
  if (v("_종료일")) inp.ce = v("_종료일");
  if (F("_등록비")) { const reg = numOf(v("_등록비")); if (reg !== nz(inp.regFee)) inp.regFee = reg || 0; }
  return inp;
}
const confDirty = () => CF.mode === "edit" && CF.initial && JSON.stringify(readInputs()) !== CF.initial;
async function closeConf() {
  if (confDirty() && !await confirmDlg({ title: "계산 취소", body: "입력한 내용은 금액에 적용되지 않습니다.", verb: "버리고 닫기", cancel: "계속 입력", danger: true })) return;
  dlg().close();
}
function openConfCalc(opts = {}) {
  buildShell();
  if (!opts.readonly && $("#dlg").open && $("#req-calc-btn")?.dataset.view === "1")  // 잠긴 신청: 폼에서도 보기 전용
    opts = { readonly: true, calc: calcFromForm(), rec: reqFind(Number($("#dlg").dataset.row)) };
  const ro = !!opts.readonly;
  const calc = ro ? (opts.calc && opts.calc.in ? opts.calc : null) : calcFromForm();
  if (ro && !calc) { showAlert("저장된 여비 계산이 없습니다.", "warn"); return; }
  CF.ctx = ro ? ctxOfRec(opts.rec) : formCtx();
  CF.saved = ro ? calc.out || null : null;
  CF.mode = ro ? "view" : "edit";
  applyInputs(calc ? (ro ? calc.in : mergeForm({ ...calc.in })) : seedFromForm(defaultInputs()));
  $("#cf-fs").disabled = ro;
  $("#cf-docs")?.remove();  // 새로 열 때는 체크리스트를 저장값으로 다시 그린다
  CF.res = null; CF.inp = null;  // update() 의 '변경 없음' 건너뛰기를 막고 처음부터 그린다
  CF.initial = ro ? "" : JSON.stringify(readInputs());
  const d = dlg();
  d.classList.toggle("cf-ro", ro);
  $("#conf-title").textContent = ro ? `학회 여비 산출 내역${CF.ctx.신청번호 ? " · " + CF.ctx.신청번호 : ""}` : "학회 여비 계산기";
  $("#conf-reset").hidden = true;  // 초기화는 신청 폼의 [계산 초기화] 버튼 하나로 (동작 통일)
  $("#conf-apply").hidden = ro;
  $("#conf-close").textContent = ro ? "닫기" : "취소";
  update();
  d.showModal();
  (ro ? $("#conf-print") : $("#cf-trip")).focus();
}
function applyToForm() {
  if (!CF.res || CF.res.blocked) return;
  const o = outOf(CF.res, CF.inp), calc = { v: 2, in: CF.inp, out: o };
  const el = F("_calc"); if (!el) return;
  el.value = JSON.stringify(calc);
  const amt = F("금액");
  if (amt) { amt.value = fmt(o.합계); amt.readOnly = true; amt.classList.add("locked"); amt.title = "여비 계산기 합계 (계산기에서 바꾸세요)"; amt.removeAttribute("aria-invalid"); }
  const set = (k, v) => { const f = F(k); if (f && v !== "" && v != null) f.value = v; };
  set("_국내외", o.구분);
  set("_시작일", CF.inp.cs); set("_종료일", CF.inp.ce);
  if (F("_장소") && !F("_장소").value.trim()) set("_장소", CF.inp.citySearch || CF.inp.legs.find(l => l.arr.place && l.arr.tz !== KST)?.arr.place || "");
  const regEl = F("_등록비"), regBefore = regEl ? numOf(regEl.value) || 0 : 0;
  if (regEl) regEl.value = o.등록비 > 0 ? fmt(o.등록비) : "";  // 계산기에서 0으로 지우면 폼도 비움 (상세 등록비 = in.regFee)
  syncFormRow();
  return regEl && regBefore !== (o.등록비 || 0) ? `등록비는 ${fmtW(o.등록비 || 0)}으로 바꿨습니다.` : "";
}
function resetForm() {
  const el = F("_calc"); if (el) el.value = "";
  const amt = F("금액");  // 상태·주문 잠금(aria-readonly)은 그대로 두고 계산기 잠금만 푼다
  if (amt && amt.getAttribute("aria-readonly") !== "true") { amt.readOnly = false; amt.classList.remove("locked"); amt.title = ""; }
  syncFormRow();
}
function syncFormRow() {
  const note = $("#req-calc-row .toolbar-note"), c = calcFromForm(), rb = $("#req-calc-reset");
  if (note) note.textContent = c ? `계산 적용됨 · ${c.out.일수}일 ${c.out.박수}박 · ${c.out.등급} · 합계 ${fmtW(c.out.합계)} (금액은 계산기에서 바꿉니다)` : "항공·숙박·일비를 계산해 금액과 상세에 채웁니다";
  if (rb) rb.hidden = !c || $("#req-calc-btn")?.dataset.view === "1";
}
// request.js requestFormAfterOpen 에서 호출: 숨은 칸(#f-_calc)에 기존 계산을 담고, 초기화 버튼을 단다
function confFormInit(det, opts = {}) {
  const row = $("#req-calc-row"); if (!row) return;
  const calc = det && det.v && det.in && det.out ? { v: det.v, in: det.in, out: det.out } : null;
  const hid = document.createElement("input"); hid.type = "hidden"; hid.id = "f-_calc"; hid.value = calc ? JSON.stringify(calc) : "";
  row.append(hid);
  row.querySelector(".toolbar-note")?.insertAdjacentHTML("beforebegin", `<button type="button" class="btn btn-sm" id="req-calc-reset" title="상세의 계산 결과를 지우고 금액을 직접 입력할 수 있게 합니다">계산 초기화</button>`);
  const btn = $("#req-calc-btn");
  if (opts.locked) {  // 품의전환·완료: 계산 결과만 볼 수 있다
    if (calc) { btn.removeAttribute("disabled"); btn.textContent = "산출 내역 보기"; btn.dataset.view = "1"; } else btn.setAttribute("disabled", "");
  }
  syncFormRow();
}
function confCalcValue() { const el = F("_calc"); return el ? (el.value ? calcFromForm() : null) : undefined; }

// 상세 패널 요약 (request.js renderReqDrawer)
function confDrawerKv(det, kv) {
  if (!det || !det.out || det.합계 == null) return "";
  const o = det.out;
  return kv("여비 계산", `${esc(o.일수)}일 · ${esc(o.박수)}박${o.기내박 ? ` (기내박 ${esc(o.기내박)})` : ""} · ${esc(o.등급)} <button type="button" class="lnk" data-rd="confview">산출 내역 보기</button>`);
}

// ---------- 인쇄 (A4, 기본 정보 / 산출 내역 / 안내 / 서류 체크리스트) ----------
function printHtml(o, ctx) {
  const T = s => esc(s ?? "");
  const head = [["신청번호", ctx.신청번호], ["신청인(출장자)", ctx.신청인], ["학회명", ctx.학회명], ["관련과제", ctx.관련과제]].filter(([, v]) => v);
  const meta = [...head, ...(o.meta || [])];
  const legs = o.legs || [];
  return `<header class="os-head"><h2>학회 여비 산출 내역</h2><div class="os-no">${ctx.신청번호 ? `신청번호 <b>${T(ctx.신청번호)}</b> · ` : ""}계산 ${T(o.계산일 || "")} · 출력 ${T(today())}</div></header>
    <p class="pc-basis">근거: ${T(o.basis || REG.basis)} · 과제별 지급기준이 따로 있으면 그 기준이 우선합니다.</p>
    <h3 class="pc-h">1. 기본 정보</h3>
    <table class="os-meta"><tbody>${meta.map(([k, v]) => `<tr><th scope="row">${T(k)}</th><td>${T(v)}</td></tr>`).join("")}</tbody></table>
    ${legs.length ? `<table class="os-lines pc-legs"><thead><tr><th scope="col" class="num">구간</th><th scope="col">수단</th><th scope="col">출발 (현지)</th><th scope="col">도착 (현지)</th><th scope="col">한국 시각 (KST)</th><th scope="col" class="num">기내박</th><th scope="col" class="num">기내식</th></tr></thead><tbody>${legs.map(l => `<tr><td class="num">${l.n}</td><td>${T(l.mode)}</td><td>${T(l.dep.place)} ${T(l.dep.local)}<div class="pc-sub">${T(l.dep.tz)} ${T(l.dep.off)}</div></td><td>${T(l.arr.place)} ${T(l.arr.local)}<div class="pc-sub">${T(l.arr.tz)} ${T(l.arr.off)}</div></td><td>${T(l.dep.kst)} → ${T(l.arr.kst)}</td><td class="num">${l.order ? "0 (확인 필요)" : l.nights}</td><td class="num">${l.meal}</td></tr>`).join("")}</tbody></table>` : ""}
    <h3 class="pc-h">2. 산출 내역</h3>
    <table class="os-lines pc-lines"><thead><tr><th scope="col">항목</th><th scope="col">산식·비고</th><th scope="col" class="num">금액(원)</th></tr></thead><tbody>${(o.lines || []).map(l => `<tr class="${l.kind === "total" || l.kind === "sub" ? "pc-b" : ""}"><td>${T(l.k)}</td><td>${T(l.f)}</td><td class="num">${l.amt < 0 ? "−" + fmtN(-l.amt) : fmtN(l.amt)}</td></tr>`).join("")}</tbody></table>
    <p class="pc-basis">기준: ${T(KST_NOTE)}</p>
    <h3 class="pc-h">3. 안내</h3>
    <ul class="pc-notes">${(o.notes || []).map(n => `<li>[${T(NOTE_LABEL[n.type] || n.type)}] ${T(n.text)}</li>`).join("")}</ul>
    <h3 class="pc-h">4. 제출 서류 체크리스트</h3>
    ${(o.docs || []).map(s => `<h4 class="pc-h4">${T(s.sec)}</h4><ul class="pc-docs">${s.items.map(it => `<li>${it.c ? "☑" : "☐"} ${T(it.t)}</li>`).join("")}</ul>`).join("")}
    <p class="pc-disc">※ ${T(REG.disclaimer)}</p>
    <p class="pc-sign">위와 같이 여비 산출 내역을 확인함.<br><br>확인자: ______________ (서명)</p>`;
}
function prepPrint() {  // 인쇄 사본 준비. 인쇄할 게 없으면 false
  const o = CF.mode === "view" && CF.saved && CF.saved.lines ? CF.saved : (CF.res && !CF.res.blocked ? outOf(CF.res, CF.inp) : null);
  if (!o) return false;
  $("#print-conf").innerHTML = printHtml(o, CF.ctx);
  document.body.classList.add("printing-conf");
  return true;
}
function printConf() { if (prepPrint()) window.print(); }
window.addEventListener("beforeprint", () => {  // Ctrl+P: 계산기가 열려 있으면 뒤 화면 대신 산출 내역 (결의서·발주서와 같은 방식)
  if (document.body.classList.contains("printing-conf") || !dlg().open) return;
  if (!prepPrint()) showAlert("입력이 완료되지 않아 산출 내역을 인쇄할 수 없습니다.", "warn");
});
window.addEventListener("afterprint", () => { if (!document.body.classList.contains("printing-conf")) return; document.body.classList.remove("printing-conf"); $("#print-conf").innerHTML = ""; });

// ---------- 이벤트 ----------
document.addEventListener("click", e => {
  if (e.target.closest("#req-calc-reset")) { resetForm(); const a = F("금액"); if (a && !a.readOnly) a.value = ""; a?.focus(); showAlert("계산 결과를 지웠습니다. 금액을 직접 입력할 수 있습니다 (저장해야 반영).", "ok"); }
});
function applyConf() {
  if (CF.mode !== "edit") return;
  update();
  if (CF.res.blocked) { showAlert("입력이 완료되지 않아 적용할 수 없습니다. '계산하려면' 목록을 확인하세요.", "warn"); return; }
  const extra = applyToForm(); CF.initial = ""; dlg().close(); F("금액")?.focus();
  showAlert(`여비 합계 ${fmtW(CF.res.grandW)}을 금액에 넣었습니다. ${extra ? extra + " " : ""}신청을 저장해야 반영됩니다.`, "ok");
}
$("#conf-form").addEventListener("submit", e => { e.preventDefault(); if (e.submitter) applyConf(); });  // 버튼·Ctrl+Enter 만. Enter 의 암묵 제출(submitter 없음)은 무시
// 신청 폼과 같은 규칙: Enter 는 다음 칸, Ctrl+Enter 는 금액에 적용 (도시 검색·숫자 칸에서 Enter 로 닫히지 않게)
$("#conf-form").addEventListener("keydown", e => {
  if (e.key !== "Enter" || e.isComposing) return;
  const t = e.target;
  if (t.tagName === "BUTTON" || t.tagName === "TEXTAREA") return;
  if (e.ctrlKey || e.metaKey) { e.preventDefault(); applyConf(); return; }
  if (t.hasAttribute("list")) return;  // 도시 검색: Enter 는 datalist 선택에 쓰고, 제출은 submitter 검사로 막는다
  e.preventDefault();
  if (CF.mode !== "edit") return;
  const all = $$("#conf-form input, #conf-form select, #conf-form button").filter(x => !x.disabled && !x.hidden && x.tabIndex !== -1 && x.offsetParent !== null);
  const i = all.indexOf(t); if (i >= 0 && all[i + 1]) all[i + 1].focus();
});
$("#conf-close").addEventListener("click", closeConf);
dlg().addEventListener("cancel", e => { if (!confDirty()) return; e.preventDefault(); closeConf(); });
$("#conf-reset").addEventListener("click", () => { resetForm(); dlg().close(); F("금액")?.focus(); showAlert("계산 결과를 지웠습니다. 금액을 직접 입력할 수 있습니다 (저장해야 반영).", "ok"); });
$("#conf-print").addEventListener("click", printConf);

window.openConfCalc = openConfCalc;
window.confFormInit = confFormInit;
window.confCalcValue = confCalcValue;
window.confDrawerKv = confDrawerKv;
window.ConfCalc = { REG, CITY_GRADE, TZ_LIST, KST_NOTE, localToUtc, resolveLocal, validTz, kstDay, kstStr, wallStr, placeTz, compute, outOf, defaultInputs, printHtml };
})();
