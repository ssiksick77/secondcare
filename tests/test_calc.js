// 학회 여비 계산기(app/static/conf.js) 순수 계산 검사. DOM 없이 node 로 실행: node tests/test_calc.js
"use strict";
const fs = require("fs");
const path = require("path");

// conf.js 가 로드 시 건드리는 전역의 최소 스텁
const stub = { addEventListener() {}, querySelector() { return stub; }, innerHTML: "", open: false,
  classList: { contains() { return false; }, add() {}, remove() {}, toggle() {} } };
stub.body = stub;
global.window = { addEventListener() {} };
global.document = stub;
global.$ = () => stub; global.$$ = () => []; global.esc = s => String(s); global.F = () => null;
global.today = () => "2026-10-16"; global.fmt = n => Number(n).toLocaleString("ko-KR");
new Function(fs.readFileSync(path.join(__dirname, "..", "app", "static", "conf.js"), "utf8"))();
const { compute, outOf, defaultInputs } = window.ConfCalc;
const won = n => Math.floor(n + 1e-6);

let n = 0; const fails = [];
const ck = (name, cond, detail) => { n++; console.log(`  ${cond ? "ok  " : "FAIL"} ${name}${cond ? "" : "  " + JSON.stringify(detail)}`); if (!cond) fails.push(name); };
const leg = (mode, dep, arr, meal = 0) => ({ mode, meal, dep: { place: dep[0], tz: dep[1], at: dep[2] }, arr: { place: arr[0], tz: arr[1], at: arr[2] } });
const PAR = [leg("항공", ["인천", "Asia/Seoul", "2026-11-09T10:00"], ["파리", "Europe/Paris", "2026-11-09T15:00"]), leg("항공", ["파리", "Europe/Paris", "2026-11-13T12:00"], ["인천", "Asia/Seoul", "2026-11-14T07:00"])];
const base = { ...defaultInputs(), fx: 1380, cityGrade: "나", cs: "2026-11-10", ce: "2026-11-12", legs: PAR };

// 통화 환산
let r = compute({ ...base, regFee: 500, regCur: "EUR", fxs: { EUR: 1500 }, fare: 1000, fareCur: "USD" });
ck("EUR·USD 환산", !r.blocked && r.regW === 750000 && r.fareW === 1380000, { blocked: r.blocked, regW: r.regW, fareW: r.fareW });
ck("환율표", r.fxTable.USD === 1380 && r.fxTable.EUR === 1500, r.fxTable);
ck("산식 표기", r.lines.find(l => l.k === "학회 등록비").f === "€500 × 환율 1,500", r.lines.find(l => l.k === "학회 등록비").f);
r = compute({ ...base, regFee: 500, regCur: "EUR" });
ck("EUR 환율 누락 → 미입력", r.blocked && r.missing.some(m => m.id === "cf-fx-EUR"), r.missing);
r = compute({ ...base, regFee: 100, regCur: "$", fare: 50000, fareCur: "₩" });
ck("v:1 기호(₩/$) 호환", r.regW === 138000 && r.fareW === 50000, { regW: r.regW, fareW: r.fareW });
r = compute({ ...base, etcFee: 10, etcCur: "XXX" });
ck("미등록 통화 코드 → 오류", r.errors.some(e => e.id === "cf-etc-cur"), r.errors);
r = compute({ ...base, lodgePaid: 30000, lodgeCur: "JPY", fxs: { JPY: 9.2 } });
ck("JPY 숙박 결제 환산", r.lodgePaidW === 276000, r.lodgePaidW);

// 박수·일수 (기내박 = 현지 날짜, 일수 = KST)
r = compute(base);
ck("유럽 왕복: 6일, 기내박 1, 인정 4박", r.D === 6 && r.transitNights === 1 && r.nights === 4, { D: r.D, t: r.transitNights, n: r.nights });
const LAX = [leg("항공", ["인천", "Asia/Seoul", "2026-11-09T10:00"], ["로스앤젤레스", "America/Los_Angeles", "2026-11-09T06:00"], 1), leg("항공", ["로스앤젤레스", "America/Los_Angeles", "2026-11-13T23:00"], ["인천", "Asia/Seoul", "2026-11-15T05:00"], 1)];
r = compute({ ...base, legs: LAX, lodgePaid: 2000, lodgeCur: "USD" });
ck("미주 서향 귀국: 기내박 2, 인정 4박", r.transitNights === 2 && r.nights === 4 && r.D === 7, { D: r.D, t: r.transitNights, n: r.nights });
ck("숙박 상한 = 137 × 4박 × 1380", r.capW === 756240 && r.lodgeW === 756240, { capW: r.capW, lodgeW: r.lodgeW });
r = compute({ ...base, legs: [PAR[0], leg("항공", ["파리", "Europe/Paris", "2026-11-08T12:00"], ["인천", "Asia/Seoul", "2026-11-09T07:00"])] });
ck("구간 순서 역전 → 주의", r.notes.some(x => /구간 2 출발/.test(x.text)), r.notes.map(x => x.text));
r = compute({ ...base, tripType: "dom", region: 100000, legs: [leg("철도", ["서울", "Europe/Paris", "2026-11-09T10:00"], ["부산", "Europe/Paris", "2026-11-09T13:00"]), leg("철도", ["부산", "", "2026-11-11T10:00"], ["서울", "", "2026-11-11T13:00"])] });
ck("국내: 시간대 무시(KST), 3일 2박", !r.blocked && r.D === 3 && r.nights === 2, { blocked: r.blocked, D: r.D, n: r.nights });
r = compute({ ...base, legs: [leg("항공", ["인천", "Asia/Seoul", "2026-11-09T08:00"], ["도쿄", "Asia/Tokyo", "2026-11-09T10:00"]), leg("항공", ["도쿄", "Asia/Tokyo", "2026-11-09T19:00"], ["인천", "Asia/Seoul", "2026-11-09T22:00"])], lodgePaid: 100, lodgeCur: "USD" });
ck("당일 출장 + 숙박 결제 → 0박 안내", r.nights === 0 && r.notes.some(x => /0박이라/.test(x.text)), r.notes.map(x => x.text));

// 출장 기간 입력 우선, 이동 구간·금액은 선택 사항
r = compute({ ...base, ts: "2026-11-09", te: "2026-11-13", legs: [], regFee: 500, regCur: "USD" });
ck("출장 기간만: 5일 4박, 등록비 합산", !r.blocked && r.D === 5 && r.nights === 4 && r.transitNights === 0 && r.regW === 690000, { blocked: r.blocked, D: r.D, n: r.nights, missing: r.missing });
r = compute({ ...base, ts: "2026-11-09", te: "2026-11-14", legs: PAR });
ck("출장 기간 + 구간: 일수는 입력값, 기내박은 구간", r.D === 6 && r.transitNights === 1 && !r.notes.some(x => /다릅니다/.test(x.text)), { D: r.D, t: r.transitNights, notes: r.notes.map(x => x.text) });
r = compute({ ...base, ts: "2026-11-08", te: "2026-11-14", legs: PAR });
ck("출장 기간 ≠ 구간 날짜 → 주의", r.D === 7 && r.notes.some(x => /다릅니다/.test(x.text)), r.notes.map(x => x.text));
r = compute({ ...base, ts: "2026-11-07", te: "2026-11-15", legs: [] });  // 학회 11-10~12: 앞 3일, 뒤 3일 → 공제 2+2
ck("학회 전후 1일 초과 → 주의 문구", r.notes.some(x => /학회 전후로 각 1일씩만 출장으로 인정됩니다/.test(x.text)), r.notes.map(x => x.text));
ck("공제일수 4 → 일비·식비 5일", r.D === 9 && r.cutDays === 4 && r.Dpay === 5 && r.ilbiW === won(30 * 5 * 1380) && r.mealW === won(59 * 5 * 1380), { D: r.D, cut: r.cutDays, Dpay: r.Dpay, ilbi: r.ilbiW, meal: r.mealW });
ck("공제는 숙박 박수에 영향 없음", r.nights === 8, r.nights);
ck("산식에 공제 표기", /9일 − 공제 4일 = 5일/.test(r.lines.find(l => l.k.startsWith("일비")).f), r.lines.find(l => l.k.startsWith("일비")).f);
ck("outOf: 공제일수·지급일수", outOf(r, { ...base }).공제일수 === 4 && outOf(r, { ...base }).지급일수 === 5);
r = compute({ ...base, ts: "2026-11-09", te: "2026-11-13", legs: [] });
ck("학회 전후 1일 이내 → 주의 없음", !r.notes.some(x => /1일씩만/.test(x.text)), r.notes.map(x => x.text));
r = compute({ ...base, ts: "2026-11-09", te: "", legs: [] });
ck("출장 시작일만 → 종료일 미입력", r.blocked && r.missing.some(m => m.id === "cf-te"), r.missing);
r = compute({ ...base, legs: [], regFee: 500, regCur: "USD" });
ck("구간·출장 기간 없음: 학회 기간 3일 2박", !r.blocked && r.D === 3 && r.nights === 2 && r.notes.some(x => /학회 기간.*출장 기간으로/.test(x.text)), { blocked: r.blocked, D: r.D, n: r.nights });
r = compute({ ...base, legs: [], cs: "", ce: "", regFee: 500, regCur: "USD" });
ck("아무 기간 없음: 0일, 금액만", !r.blocked && r.D === 0 && r.grandW === 690000, { blocked: r.blocked, D: r.D, grand: r.grandW });
r = compute({ ...base, legs: [leg("항공", ["인천", "Asia/Seoul", "2026-11-09T10:00"], ["파리", "", ""])] });
ck("구간을 쓰다 말면 그 칸은 여전히 필수", r.blocked && r.missing.some(m => m.id === "leg-0-arr-at"), r.missing);

// 규정 산식
r = compute({ ...base, legs: PAR, confMeals: 3 });
// 출장 11-09~14(6일), 학회 11-10~12 → 뒤 2일 중 1일 공제 → 지급 5일
ck("일비 = 30 × (6 − 공제 1)일 × 1380", r.cutDays === 1 && r.ilbiW === 207000, { cut: r.cutDays, ilbi: r.ilbiW });
ck("식비 = (59 × 5 − 3 × 59/3) × 1380", r.mealW === Math.floor((59 * 5 - 59) * 1380), r.mealW);
ck("라인 합 = 총액", r.lines.filter(l => ["travel", "side", "ext"].includes(l.kind)).reduce((a, l) => a + l.amt, 0) === r.grandW, r.grandW);
r = compute({ ...base, extFund: 99999999 });
ck("외부 지원금 초과 → 총액 0 + 안내", r.grandW === 0 && r.notes.some(x => /총액은 0원/.test(x.text)), r.grandW);
r = compute({ ...base, cityGrade: "마" });
ck("도시 등급 손상 → 미입력(NaN 없음)", r.blocked && r.missing.some(m => m.id === "cf-cgrade"), r.missing);
const o = outOf(compute({ ...base, regFee: 500, regCur: "EUR", fxs: { EUR: 1500 } }), { ...base, regCur: "EUR", fxs: { EUR: 1500 } });
ck("outOf: 합계·환율표·기준", o.합계 > 0 && o.환율표.EUR === 1500 && o.기준 === "KST", o);

console.log(`계산: ${n - fails.length}/${n} 통과${fails.length ? ", 실패: " + fails.join(", ") : ""}`);
process.exit(fails.length ? 1 : 0);
