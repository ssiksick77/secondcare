/* 센터 회계대장 관리도구 - 프론트엔드 */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const fmt = n => (n == null || isNaN(n)) ? "" : Math.round(n).toLocaleString("ko-KR");
const pct = r => r == null ? "-" : (r * 100).toFixed(1) + "%";
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const localISO = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const today = () => localISO(new Date());  // 로컬(한국) 날짜. toISOString 은 UTC 라 오전 9시 전에 어제가 됨
const mmdd = d => (typeof d === "string" && /^\d{4}-\d{2}-\d{2}$/.test(d)) ? d.slice(5, 7) + "/" + d.slice(8, 10) : d;
// 행 식별값 (서버가 다른 창/MCP 에서 행이 밀렸는지 검사)
const IDENT = { funds: ["재원코드"], exec: ["거래번호"], req: ["품의번호"], tags: ["태그명"], vendor: ["거래처명", "코드"], budget: ["재원", "변경회차", "신청일자"], deposit: ["일자", "거래처", "구분", "금액"], memo: ["종류", "대상", "내용"] };
const F = k => document.getElementById("f-" + k);
// 단계 ↔ 날짜: 발생=원인발생일, 청구=지급청구일, (보완=수동 표시), 승인=지출완료일, 결의=결의일
const STATUS_LABEL = { 발생: "발생", 청구: "청구", 보완: "보완", 완료: "승인", 결의: "완료", 취소: "취소" };
const isCancelled = r => r?.["상태"] === "취소";  // 취소 건: 표에는 남고 모든 합계·잔액·집계·결의서에서 빠진다 (2026-10-19)
const activeExec = () => DATA.exec.filter(r => !isCancelled(r));  // 결의일이 등록되면 '완료'로 표시
const STATUS_HELP = { 취소: "취소된 집행. 금액은 어떤 합계·잔액에도 들어가지 않음 (상세 패널에서 해제 가능)", 발생: "원인발생일만 있음. 다음: 청구(지급청구일)", 청구: "지급청구일 등록됨. 다음: 승인(지출완료일)", 보완: "서류·증빙 보완이 필요하다고 표시한 건 (청구 단계)", 완료: "지출완료일 등록됨(승인). 다음: 결의(결의일)", 결의: "결의일 등록됨, 완료" };
// 상태 열의 다음 단계 버튼: [동작, 라벨, 설명]
const NEXT_STEP = { 발생: ["claim", "청구", "지급청구일을 오늘로 등록"], 청구: ["complete", "승인", "지출완료일을 오늘로 등록"], 보완: ["complete", "승인", "지출완료일을 오늘로 등록 (보완 해제)"], 완료: ["resolve", "결의", "결의일을 오늘로 등록 (마지막 단계)"] };
// 적립금 사용 행의 단계 (2026-10-19, 집행 단계 방식): 대기 → 발주(발주일) → 결제(결제일) → 수령(수령일). 적립 행은 단계 없음
const DEP_STATUS_HELP = { 대기: "단계 날짜 없음. 다음: 발주(발주일)", 발주: "발주일 등록됨. 다음: 결제(결제일)", 결제: "결제일 등록됨. 다음: 수령(수령일)", 수령: "수령일 등록됨, 완료" };
const DEP_NEXT_STEP = { 대기: ["order", "발주", "발주일을 오늘로 등록"], 발주: ["pay", "결제", "결제일을 오늘로 등록"], 결제: ["receive", "수령", "수령일을 오늘로 등록 (마지막 단계)"] };
const DEP_STAGES = [["발주", "발주일", "order"], ["결제", "결제일", "pay"], ["수령", "수령일", "receive"]];  // [라벨, 날짜 열, '오늘 등록' 동작]
const DATE_STAGE = { 원인발생일: "발생", 지급청구일: "청구", 지출완료일: "승인", 결의일: "결의" };  // 폼 필드 (예산목 이름에 괄호·점이 있어 CSS 선택자 불가)
// 행 식별값 + 전체 스냅샷: 서버가 다른 창/MCP 에서 먼저 바뀐 행을 덮어쓰지 않도록 검사
const expectOf = (kind, r) => r ? { ...Object.fromEntries((IDENT[kind] || []).map(c => [c, r[c]])), _snapshot: Object.fromEntries(Object.entries(r).filter(([k]) => !k.startsWith("_"))) } : undefined;

let DATA = null;
const FILTERS = { exec: {}, req: {}, budget: {}, deposit: {} };

// ---------- 열 정의 ----------
const COLS = {
  exec: [
    { k: "거래번호", w: 1 }, { k: "상태", t: "badge" }, { k: "관리번호", minor: true }, { k: "연결품의번호", hide: true }, { k: "원인발생일", t: "date", label: "발생일" }, { k: "지급청구일", t: "date", hide: true },
    { k: "지출완료일", t: "date", hide: true }, { k: "결의일", t: "date", hide: true }, { k: "재원" }, { k: "예산목" }, { k: "세목" }, { k: "세세목", minor: true },
    { k: "거래처", hide: true }, { k: "적요", t: "title", sub: "거래처" }, { k: "결제수단" }, { k: "금액", t: "num", amt: true }, { k: "예산목 잔액", t: "num", calc: r => runningBalance(r), title: "이 거래까지 반영한 재원·예산목 잔액 (원인발생일까지 신청된 예산변동 합 − 원인발생일 순 누적 집행). 품의대기는 제외" }, { k: "사용자", minor: true }, { k: "태그" }, { k: "증빙", t: "num", calc: r => evidCount(r), title: "등록된 증빙 수 (파일 없이 실물만 등록한 항목 포함)" }, { k: "비고", wrap: true, minor: true },
  ],
  req: [
    { k: "품의번호" }, { k: "상태", t: "badge" }, { k: "원인발생일", t: "date" }, { k: "지출예정일", t: "date" }, { k: "재원" },
    { k: "예산목" }, { k: "세목" }, { k: "세세목" }, { k: "거래처" }, { k: "결제수단" }, { k: "적요", wrap: true },
    { k: "금액", t: "num", amt: true }, { k: "태그" }, { k: "품의자" }, { k: "비고", wrap: true },
  ],
  budget: null, // meta 로드 후 생성
  deposit: [{ k: "적립번호", title: "적립금 거래 번호 (적립-연도-일련번호). 행을 누르면 상세·증빙" }, { k: "일자", t: "date" }, { k: "거래처" }, { k: "구분", t: "badge" }, { k: "상태", t: "badge", title: "사용 행의 단계: 대기 → 발주 → 결제 → 수령 (발주일·결제일·수령일로 계산). 체크를 누르면 다음 단계를 오늘로 등록" }, { k: "금액", t: "num", amt: true }, { k: "적요", wrap: true },
    { k: "사용자" }, { k: "증빙번호", title: "영수증·주문 번호 등 손으로 적는 번호 (증빙 파일은 '증빙' 열)" }, { k: "연결거래번호" }, { k: "증빙", t: "num", calc: r => evidCountNo(r["적립번호"]), title: "등록된 증빙 수 (파일 없이 실물만 등록한 항목 포함)" }, { k: "비고", wrap: true }],
  funds: [{ k: "재원코드" }, { k: "종류" }, { k: "잔액미관리", label: "잔액", ctr: true, html: r => r["잔액미관리"] === "Y" ? '<span class="muted" title="재원 출처로만 쓰고 예산·잔액을 관리하지 않음">미관리</span>' : "관리" }, { k: "과제명", wrap: true }, { k: "시작일", t: "date" }, { k: "종료일", t: "date" }, { k: "비고", wrap: true }, { k: "인건비예산", t: "num", title: "인건비 화면의 지급처 예산 (비우면 예산목 합계)" }],
  tags: [{ k: "태그명" }, { k: "분류" }, { k: "설명", wrap: true }, { k: "사용건수", t: "num", calc: r => tagUsage(r["태그명"]) }],
  vendor: [{ k: "거래처명" }, { k: "코드", title: "적립번호 앞자리 (코드-적립|사용-연도-번호). 번호에 쓰인 뒤에는 바꿀 수 없음" }, { k: "비고", wrap: true }, { k: "적립금 건수", t: "num", calc: r => DATA.deposit.filter(d => (d["거래처"] || "").trim().toLowerCase() === (r["거래처명"] || "").trim().toLowerCase()).length }],
};
function tagUsage(name) { return ["exec", "req", "deposit"].reduce((a, k) => a + DATA[k].filter(r => r["태그"] === name).length, 0); }
function tagField(extra = {}) {
  // 태그 마스터가 있으면 1개 선택, 없으면 자유 입력
  if (DATA.tags.length) {
    const cats = {};
    DATA.tags.forEach(t => { (cats[t["분류"] || "기타"] = cats[t["분류"] || "기타"] || []).push(t["태그명"]); });
    return { k: "태그", type: "select", opts: ["", ...DATA.tags.map(t => t["태그명"])], groups: cats, hint: "내부 계정", ...extra };
  }
  return { k: "태그", type: "datalist", hint: "태그 탭에서 목록을 등록하면 선택식으로 바뀜", ...extra };
}

// 입력 폼 필드 정의 (type: text|date|num|select|datalist|textarea)
function formFields(kind) {
  if (typeof LABOR_FORMS !== "undefined" && LABOR_FORMS[kind]) return LABOR_FORMS[kind]();
  if (typeof REQUEST_FORMS !== "undefined" && REQUEST_FORMS[kind]) return REQUEST_FORMS[kind]();
  const funds = fundOptions();
  const items = DATA.meta.budget_items;
  // 실무 입력 순서: 날짜 → 재원 → 예산목 → 거래처 → 금액 → 적요 → 세목 → 태그 → (부가 정보)
  const common = [
    { k: "원인발생일", type: "date", req: true, hint: "발생 단계" },
    { k: "재원", type: "select", opts: funds, req: true },
    { k: "예산목", type: "select", opts: items, req: true },
    { k: "거래처", type: "datalist", focus: true },
    { k: "금액", type: "num", req: true },
    { k: "적요", type: "text" },
    { k: "세목", type: "datalist" }, { k: "세세목", type: "datalist" },
    tagField(),
  ];
  if (kind === "exec") return [
    { k: "거래번호", type: "ro" },
    ...common,
    { k: "결제수단", type: "select", opts: ["", ...DATA.meta.pay_methods] }, { k: "사용자", type: "datalist" }, { k: "관리번호", type: "text", hint: "ERP/전자결재 문서번호 (선택)" },
    { k: "지급청구일", type: "date", hint: "청구 단계" }, { k: "지출완료일", type: "date", hint: "승인 단계, 비우면 미승인" }, { k: "결의일", type: "date", hint: "결의 단계 (마지막)" }, { k: "비고", type: "text" },
  ];
  if (kind === "req") return [
    { k: "품의번호", type: "ro" },
    ...common,
    { k: "품의자", type: "datalist" }, { k: "지출예정일", type: "date" }, { k: "결제수단", type: "select", opts: ["", ...DATA.meta.pay_methods] },
    { k: "상태", type: "select", opts: DATA.meta.req_status, req: true }, { k: "비고", type: "text" },
  ];
  if (kind === "budget") return [
    { k: "재원", type: "select", opts: funds.filter(f => !isUntrackedFund(f)), req: true, hint: "잔액 미관리 재원은 예산변동을 적지 않습니다" },
    { k: "변경회차", type: "text", req: true, hint: "이월 / 당초 / 1, 2, 3…" },
    { k: "신청일자", type: "date", req: true, hint: "이 날짜부터 거래별 예산목 잔액에 반영" },
    { k: "변경사유", type: "text", cls: "wide" },
    ...items.map(i => ({ k: i, type: "num" })),
    { k: "입금", type: "num", hint: "공금 재원만: 입금액 (예산목 구분 없음, 환입은 음수)" },
  ];
  if (kind === "deposit") return [
    { k: "일자", type: "date", req: true }, { k: "거래처", type: "datalist", req: true },
    { k: "구분", type: "select", opts: DATA.meta.dep_types, req: true },
    { k: "금액", type: "num", req: true }, { k: "사용자", type: "datalist" }, { k: "증빙번호", type: "text", hint: "영수증·전표 번호" },
    tagField({ dep: "사용", hint: "사용 건의 내부 계정" }),
    { k: "발주일", type: "date", dep: "사용", hint: "비우면 일자" }, { k: "결제일", type: "date", dep: "사용" }, { k: "수령일", type: "date", dep: "사용" }, { k: "적요", type: "text", cls: "mid" }, { k: "비고", type: "text", cls: "wide" },
    { k: "_record_exec", type: "check", label: "집행내역에 기록 (선결제 금액을 예산에서 차감)", cls: "wide", onlyNew: true, dep: "적립" },
    { k: "_재원", type: "select", opts: ["", ...funds], label: "재원", dep: "적립", req: "exec" },
    { k: "_예산목", type: "select", opts: ["", ...items], label: "예산목", dep: "적립", req: "exec" },
    { k: "_세목", type: "datalist", list: "세목", label: "세목", dep: "적립" },
    tagField({ k: "_태그", label: "집행 태그", dep: "적립", hint: "집행내역에 붙일 내부 계정" }),
    { k: "연결거래번호", type: "ro" },
  ];
  if (kind === "memo") return [
    { k: "종류", type: "select", opts: DATA.meta.memo_kinds || ["재원", "거래처", "일반"], req: true, hint: "재원·거래처별 특이사항, 일반 규정" },
    { k: "대상", type: "datalist", list: "대상", hint: "재원코드 또는 거래처명 · 일반은 비움" },
    { k: "작성일", type: "date", hint: "비우면 오늘" },
    { k: "내용", type: "text", cls: "wide", req: true, hint: "AI 도우미가 답할 때 그대로 참고" },
    { k: "비고", type: "text", cls: "wide" },
  ];
  if (kind === "tags") return [
    { k: "태그명", type: "text", req: true, hint: "쉼표 금지" }, { k: "분류", type: "datalist", list: "분류", hint: "상위 계정" },
    { k: "설명", type: "text", cls: "wide" },
  ];
  if (kind === "vendor") return [
    { k: "거래처명", type: "text", req: true, hint: "적립금 입력의 거래처와 같은 이름" }, { k: "코드", type: "text", req: true, hint: "한글·영문·숫자 2~6자, 적립번호 앞자리" },
    { k: "비고", type: "text", cls: "wide" },
  ];
  if (kind === "funds") return [
    { k: "재원코드", type: "text", req: true, hint: "'-' 없이, 예: AI01" },
    { k: "종류", type: "select", opts: DATA.meta.fund_types || ["국책", "원내", "위탁", "교육", "공금", "기타"], req: true, hint: "공금은 예산목 없이 잔액만 관리" },
    { k: "과제명", type: "text", cls: "mid" },
    { k: "잔액미관리", type: "check", cls: "wide", label: "잔액 미관리 — 재원 출처로만 쓰고 예산·잔액을 관리하지 않음 (예산변동 불가, 대시보드·가용잔액·결의서 재원 현황 제외)" },
    { k: "시작일", type: "date" }, { k: "종료일", type: "date" }, { k: "비고", type: "text", cls: "wide" },
    { k: "인건비예산", type: "num", hint: "비우면 예산변동의 내부·외부인건비 합계를 사용 (인건비 화면)" },
  ];
}

// 재원 종류: 비어 있으면 국책. 공금은 예산목별 예산 없이 재원 잔액(예산변동 '입금' 합계 − 집행 − 대기 품의)만 관리
const fundType = code => (DATA.funds.find(f => f["재원코드"] === code)?.["종류"]) || "국책";
const isPoolFund = code => !!code && fundType(code) === (DATA.meta.fund_type_pool || "공금");
const isUntrackedFund = code => !!code && DATA.funds.find(f => f["재원코드"] === code)?.["잔액미관리"] === "Y";  // 재원 출처로만: 예산·잔액 관리 안 함
const poolDeposit = code => DATA.budget.filter(r => r["재원"] === code).reduce((a, r) => a + (r["입금"] || 0), 0);
// 예산변동 폼: 공금 재원이면 예산목 칸을 숨기고 입금 칸만, 아니면 반대
function budgetFormSync() {
  if ($("#dlg").dataset.kind !== "budget") return;
  const pool = isPoolFund(F("재원")?.value);
  DATA.meta.budget_items.forEach(i => { const l = F(i)?.closest("label"); if (l) l.hidden = pool; });
  const dl = F("입금")?.closest("label"); if (dl) dl.hidden = !pool;
}
function fundOptions() {
  const s = new Set(DATA.funds.map(f => f["재원코드"]));
  const payees = new Set((DATA.payee || []).map(p => p["지급처코드"]));  // 외부 지급처(인건비)는 예산 집계에서 제외
  [...DATA.exec, ...DATA.req, ...DATA.budget].forEach(r => r["재원"] && !payees.has(r["재원"]) && s.add(r["재원"]));
  return [...s];
}

// ---------- 데이터 로드 ----------
let LAST_WRITE_ID = null;  // 서버가 알려준 직전 쓰기 ID (토스트 '되돌리기'는 자기 ID 일 때만)
// body 가 FormData 면 그대로 전송 (파일 업로드). 실패 시 Error(한국어 문구) + err.status
async function api(method, url, body) {
  let res;
  const form = typeof FormData !== "undefined" && body instanceof FormData;
  try { res = await fetch(url, { method, headers: form ? undefined : { "Content-Type": "application/json" }, body: form ? body : body ? JSON.stringify(body) : undefined }); }
  catch { throw new Error("서버에 연결할 수 없습니다. run.bat 이 실행 중인지 확인하세요."); }
  const wid = res.headers.get("X-Write-Id");
  if (wid && wid !== LAST_WRITE_ID) { LAST_WRITE_ID = wid; $$(".toast-undo").forEach(b => { if (b.dataset.wid !== wid) b.remove(); }); }  // 새 쓰기 뒤에는 이전 되돌리기 버튼 제거
  if (!res.ok) {
    let msg = { 404: "찾을 수 없습니다", 405: "지원하지 않는 요청입니다", 409: "충돌", 413: "파일이 너무 큽니다 (25MB 이하)", 422: "입력 형식 오류", 423: "장부 파일이 잠겨 있습니다", 500: "서버 오류" }[res.status] || res.statusText;
    try { const d = (await res.json()).detail; if (Array.isArray(d)) msg = d.map(x => x.msg || JSON.stringify(x)).join(" / "); else if (d) msg = typeof d === "string" ? d : JSON.stringify(d); } catch { }
    const err = new Error(msg); err.status = res.status; throw err;
  }
  return res.json();
}
const isResearcher = () => document.body.classList.contains("request-mode") && !document.body.classList.contains("req-admin");

async function load() {
  try {
    DATA = await api("GET", "/api/all"); RUN_BAL = null;
    COLS.budget = [{ k: "재원" }, { k: "변경회차" }, { k: "신청일자", t: "date" }, { k: "변경사유", wrap: true },
      ...DATA.meta.budget_items.map((i, n) => ({ k: i, t: "num", amt: n === 0 })), { k: "입금", t: "num", title: "공금 재원의 입금액 (예산목 구분 없음)" }, { k: "합계", t: "num", calc: r => DATA.meta.budget_items.reduce((a, i) => a + (r[i] || 0), 0) + (r["입금"] || 0) }];
    renderStatus();
    fillSelects();
    fillDatalists();
    renderAll();
    if ($("#dlg-settings")?.open) memoRender();  // 설정 패널이 열린 채 메모를 저장·삭제하면 목록 갱신
  } catch (e) {
    showAlert("불러오기 실패: " + e.message, "error");
  }
}

function renderStatus() {
  const st = $("#file-status");
  // 연구원 화면(/request 직접 접속): 장부 파일 경로·수정 시각은 숨기고, 잠겼을 때만 할 일을 알림
  st.textContent = isResearcher() ? (DATA.meta.locked ? "지금은 저장할 수 없습니다. 담당자에게 알려 주세요." : "")
    : (DATA.meta.locked ? "주의: 엑셀에서 열려 있음 (저장 불가) · " : "") + (DATA.meta.formula_count ? `수식 셀 ${DATA.meta.formula_count}개 · ` : "") + "파일 수정 " + DATA.meta.mtime.replace("T", " ");
  st.classList.toggle("locked", DATA.meta.locked);
  showBanner(DATA.meta.formula_count ? `장부에 수식 셀이 ${DATA.meta.formula_count}개 있습니다 (${DATA.meta.formula_cells.join(", ")}). 앱은 수식을 읽지 못해 0으로 집계하며, 해당 행을 저장하면 값으로 바뀝니다. 엑셀에서 값으로 바꿔 주세요.` : "");
  $("#foot-path").textContent = DATA.meta.file;
}

function fillSelects() {
  const funds = fundOptions();
  const years = new Set();
  [...DATA.exec, ...DATA.req].forEach(r => r["원인발생일"] && years.add(r["원인발생일"].slice(0, 4)));
  DATA.deposit.forEach(r => r["일자"] && years.add(r["일자"].slice(0, 4)));
  years.add(String(new Date().getFullYear()));
  const ys = [...years].sort().reverse();

  const vendors = [...new Set(DATA.deposit.map(r => r["거래처"]).filter(Boolean))].sort();
  $$("select[data-filter='거래처']").forEach(sel => setOptions(sel, ["", ...vendors], ["전체", ...vendors]));
  $$("select[data-filter='재원']").forEach(sel => setOptions(sel, ["", ...funds], ["전체", ...funds]));
  $$("select[data-filter='year']").forEach(sel => setOptions(sel, ["", ...ys], ["전체", ...ys]));
  $$("select[data-filter='month'], #dash-month").forEach(sel => setOptions(sel, ["", ...Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, "0"))], ["전체", ...Array.from({ length: 12 }, (_, i) => (i + 1) + "월")]));
  $$("select[data-filter='예산목']").forEach(sel => setOptions(sel, ["", ...DATA.meta.budget_items], ["전체", ...DATA.meta.budget_items]));
  setOptions($("#dash-fund"), ["", ...funds], ["전체", ...funds]);
  setOptions($("#dash-year"), ["", ...ys], ["전체", ...ys]);
  setOptions($("#rep-fund"), ["", ...funds], ["전체", ...funds]);
  setOptions($("#rep-year"), ["", ...ys], ["전체", ...ys]);
  if (typeof fillLaborSelects === "function") fillLaborSelects();
  if (typeof fillRequestSelects === "function") fillRequestSelects();
  if (!$("#dash-year").dataset.init) {
    // 올해 데이터가 없으면 데이터가 있는 가장 최근 연도
    const thisYear = String(new Date().getFullYear());
    const hasThis = [...DATA.exec, ...DATA.req].some(r => (r["원인발생일"] || "").startsWith(thisYear));
    $("#dash-year").value = hasThis ? thisYear : (ys.find(y => y !== thisYear) || thisYear);
    $("#dash-year").dataset.init = 1;
  }
  // 옵션이 사라져 select 가 "전체"로 돌아간 경우 필터 상태도 맞춤
  $$("select[data-filter]").forEach(sel => { const k = sel.dataset.kind, f = sel.dataset.filter; if (FILTERS[k] && FILTERS[k][f] && FILTERS[k][f] !== sel.value) FILTERS[k][f] = sel.value; });
}

function setOptions(sel, values, labels) {
  const cur = sel.value;
  sel.innerHTML = values.map((v, i) => `<option value="${esc(v)}">${esc(labels[i])}</option>`).join("");
  if (values.includes(cur)) sel.value = cur;
}

function fillDatalists() {
  const collect = (keys) => {
    const s = new Set();
    [...DATA.exec, ...DATA.req, ...DATA.deposit].forEach(r => keys.forEach(k => {
      const v = r[k]; if (!v) return;
      s.add(String(v));
    }));
    return [...s].sort();
  };
  const fill = (id, vals) => { $(id).innerHTML = vals.map(v => `<option value="${esc(v)}">`).join(""); };
  fill("#dl-거래처", [...new Set([...(DATA.vendor || []).map(v => v["거래처명"]), ...collect(["거래처"])])]);  // 등록 거래처 먼저
  fill("#dl-사용자", collect(["사용자", "품의자"]));
  fill("#dl-태그", collect(["태그"]));
  fill("#dl-세목", collect(["세목"]));
  fill("#dl-세세목", collect(["세세목"]));
  let dk = $("#dl-증빙종류"); if (!dk) { dk = document.createElement("datalist"); dk.id = "dl-증빙종류"; document.body.appendChild(dk); }
  dk.innerHTML = [...new Set((DATA.evidence || []).map(e => e["증빙종류"]).filter(Boolean))].sort().map(v => `<option value="${esc(v)}">`).join("");
  let dl = $("#dl-분류"); if (!dl) { dl = document.createElement("datalist"); dl.id = "dl-분류"; document.body.appendChild(dl); }
  dl.innerHTML = [...new Set(DATA.tags.map(t => t["분류"]).filter(Boolean))].sort().map(v => `<option value="${esc(v)}">`).join("");
}

// ---------- 렌더 ----------
function renderAll() {
  renderExecTiles();
  if (XD.row != null && !$("#exec-drawer").hidden) rerenderDrawer(false);
  renderDashboard();
  renderList("exec"); renderList("req"); renderList("budget"); renderList("funds"); renderList("deposit"); renderList("tags"); renderList("vendor");
  renderBudgetSummary(); renderDepositSummary();
  if (typeof renderLabor === "function") renderLabor();
  if (typeof renderRequest === "function") renderRequest();
}

const SORT = {};  // kind -> {k, dir}
// 목록별 선택 열·행 표시 훅 (신청 화면: request.js 가 채움). {head(), cell(r), rowCls(r), after()}
const SEL_HOOK = {};
// 행이 많으면 처음 LIST_LIMIT 건만 그리고 '더 보기'로 나머지 (합계·CSV 는 항상 전체 기준). 필터가 바뀌면 다시 접힘
const LIST_LIMIT = 400, LIST_MORE = {};
const norm = s => String(s ?? "").toLowerCase().replace(/,/g, "");
function detailText(d) { if (!d) return ""; try { const o = JSON.parse(d); return o && typeof o === "object" ? ["학회명", "장소", "참가자"].map(k => o[k] || "").join(" ") : ""; } catch { return ""; } }
function filtered(kind) {
  const f = FILTERS[kind] || {};
  const q = norm((f.q || "").trim());
  return DATA[kind].filter(r => {
    if (f["재원"] && r["재원"] !== f["재원"]) return false;
    if (f["예산목"] && r["예산목"] !== f["예산목"]) return false;
    if (f["상태"] && r["상태"] !== f["상태"]) return false;
    if (f["거래처"] && r["거래처"] !== f["거래처"]) return false;
    if (f["구분"] && r["구분"] !== f["구분"]) return false;
    if (f["이름"] && r["이름"] !== f["이름"]) return false;
    if (f["지급처"] && r["지급처"] !== f["지급처"]) return false;
    if (f["신청인"] && r["신청인"] !== f["신청인"]) return false;
    if (f["관련과제"] && r["관련과제"] !== f["관련과제"]) return false;
    if (f["구매처"] && r["구매처"] !== f["구매처"]) return false;
    const d = r["원인발생일"] || r["일자"] || r["지급월"] || r["신청일"] || "";
    if (f.year && d.slice(0, 4) !== f.year) return false;
    if (f.month && d.slice(5, 7) !== f.month) return false;
    if (f.unpaid && r["지출완료일"]) return false;
    if (kind === "exec" && QUICK) {
      if (QUICK === "unclaimed" && r["상태"] !== "발생") return false;
      if (QUICK === "fix" && r["상태"] !== "보완") return false;
      if (QUICK === "done" && r["상태"] !== "완료") return false;
      if (QUICK === "resolved" && r["상태"] !== "결의") return false;
      if (QUICK === "cancel" && r["상태"] !== "취소") return false;
      if (QUICK === "noevid" && hasEvidence(r)) return false;
      if (QUICK === "excluded" && !isExcludedExec(r)) return false;
    }
    if (q && !Object.entries(r).some(([k, v]) => !k.startsWith("_") && k !== "상세" && norm(v).includes(q)) && !norm(detailText(r["상세"])).includes(q)) return false;  // 상세(JSON)는 키·코드가 아니라 학회명·장소·참가자만 검색
    return true;
  });
}

function renderList(kind) {
  const cols = COLS[kind].filter(c => !c.hide);  // hide: CSV 에는 포함, 화면에서는 생략
  const rows = (kind === "funds" || kind === "tags" || kind === "vendor") ? [...DATA[kind]] : filtered(kind);
  const defKey = { exec: "원인발생일", req: "원인발생일", deposit: "일자", labor: "지급월", salary: "시작월", ladj: "월", request: "신청일" }[kind];
  const noAct = kind === "exec" || kind === "request";  // 작업 열 없음: 행 클릭 = 상세 패널, 두 번 클릭 = 수정
  const sort = SORT[kind] || (defKey ? { k: defKey, dir: -1 } : null);
  if (sort) {
    const col = cols.find(c => c.k === sort.k);
    const val = r => col?.calc ? col.calc(r) : r[sort.k];
    rows.sort((a, b) => { const va = val(a), vb = val(b); const c = (typeof va === "number" && typeof vb === "number") ? va - vb : String(va ?? "").localeCompare(String(vb ?? ""), "ko"); return (c || (a._row - b._row)) * sort.dir; });
  }
  const table = $(`#${kind}-table`);
  let showMinor = false; try { showMinor = kind === "exec" && localStorage.getItem("ledger-exec-minor") === "1"; } catch { }
  table.classList.toggle("show-minor", showMinor);
  if (kind === "exec") table.classList.toggle("delmode", DELMODE);
  const minorCls = c => c.minor ? " col-minor" : "";
  const CENTER = new Set(["구분", "결제수단", "지급월", "귀속월", "월", "시작월", "종료월", "인건비구분", "변경회차", "상태", "증빙", "태그"]);
  const ctrCls = c => (c.ctr || c.t === "date" || c.t === "badge" || CENTER.has(c.k)) ? " ctr" : "";
  const SORT_SVG = d => `<span class="sort-ind" aria-hidden="true"><svg viewBox="0 0 10 10"><path d="${d > 0 ? "M2 7l3-4 3 4" : "M2 3l3 4 3-4"}" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>`;
  const head = `<thead><tr>${cols.map(c => `<th class="sortable${c.t === "num" ? " num" : ""}${c.amt ? " amt" : ""}${minorCls(c)}${ctrCls(c)}" data-col="${esc(c.k)}" data-sort="${esc(c.k)}" title="${esc(c.title || "클릭하여 정렬")}" aria-sort="${sort && sort.k === c.k ? (sort.dir > 0 ? "ascending" : "descending") : "none"}"><button type="button" class="sortbtn">${esc(c.label || c.k)}${sort && sort.k === c.k ? SORT_SVG(sort.dir) : ""}</button></th>`).join("")}${noAct ? "" : '<th class="actions">작업</th>'}</tr></thead>`;
  const selHead = kind === "exec" && DELMODE ? `<th class="sel"><input type="checkbox" id="exec-sel-all" aria-label="표시된 행 모두 선택"></th>` : (SEL_HOOK[kind]?.head() || "");
  const headFinal = selHead ? head.replace("<thead><tr>", "<thead><tr>" + selHead) : head;
  const shown = rows.length > LIST_LIMIT && !LIST_MORE[kind] ? rows.slice(0, LIST_LIMIT) : rows;
  const span = cols.length + (noAct ? 0 : 1) + (selHead ? 1 : 0);
  const more = shown.length < rows.length ? `<tr class="more-row"><td colspan="${span}"><button type="button" class="btn btn-sm" data-more="${kind}">더 보기 (${(rows.length - shown.length).toLocaleString("ko-KR")}건 남음)</button></td></tr>` : "";
  const body = rows.length ? shown.map(r => {
    const tds = cols.map(c => {
      const v = c.calc ? c.calc(r) : r[c.k];
      const td = html => { let h = html.replace(/^<td(?=[\s>])/, `<td data-col="${esc(c.k)}"`); if (ctrCls(c)) h = /^<td[^>]*\sclass="/.test(h) ? h.replace(/^(<td[^>]*\sclass=")/, "$1ctr ") : h.replace(/^<td/, '<td class="ctr"'); return h; };
      return td(cellHtml(c, r, v));
    }).join("");
    return rowHtml(r, tds);
  }).join("") + more : `<tr><td class="empty" colspan="${span}">${SEL_HOOK[kind]?.empty?.() || "표시할 항목이 없습니다."}</td></tr>`;
  function cellHtml(c, r, v) {
      if (c.html) return `<td class="${c.wrap ? "wrap" : ""}${minorCls(c)}">${c.html(r)}</td>`;  // 열 정의가 직접 그리는 칸 (값은 함수 안에서 esc)
      if (c.t === "num") return `<td class="num${c.amt ? " amt" : ""}${minorCls(c)}${typeof v === "number" && v < 0 ? " neg" : ""}">${v == null ? '<span class="muted" title="예산 미입력">-</span>' : fmt(v)}</td>`;
      if (c.t === "date" && v && (kind === "exec" || kind === "req" || kind === "budget" || kind === "deposit" || kind === "request")) {
        return `<td title="${esc(v)}">${esc(mmdd(v))}</td>`;  // 내역 탭은 MM/DD, 전체 날짜는 툴팁
      }
      if (c.t === "badge" && kind === "deposit" && c.k === "상태") {
        if (!v) return '<td class="st-cell"><div class="t"><span class="muted" title="적립 행은 단계가 없습니다">–</span></div></td>';
        const nx = DEP_NEXT_STEP[v], stDate = { 발주: r["발주일"], 결제: r["결제일"], 수령: r["수령일"] }[v];
        return `<td class="st-cell"><div class="t"><span class="badge ${esc(v)}" title="${esc(DEP_STATUS_HELP[v] || "")}">${esc(v)}</span>${nx ? `<button type="button" class="next" data-act="dact" data-action="${nx[0]}" data-row="${r._row}" title="다음 단계로: ${esc(nx[1])} (${esc(nx[2])})" aria-label="다음 단계로: ${esc(nx[1])}"><svg viewBox="0 0 12 12" aria-hidden="true" focusable="false"><path d="M2.5 6.5l2.5 2.5 4.5-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>` : '<span class="next ph" aria-hidden="true"></span>'}</div><div class="s">${stDate ? `<span title="${esc(stDate)}">${esc(mmdd(stDate))}</span>` : "&nbsp;"}</div></td>`;
      }
      if (c.t === "badge") {
        const nx = kind === "exec" ? NEXT_STEP[v] : null;
        // 두 줄: 윗줄 상태 + 다음 단계 체크, 아랫줄 그 단계의 날짜(+ 청구 단계에서는 보완 표시/해제 링크)
        const stDate = kind === "exec" ? { 청구: r["지급청구일"], 보완: r["지급청구일"], 완료: r["지출완료일"], 결의: r["결의일"] }[v] : null;
        const fixLink = kind === "exec" && v === "청구" ? `<button type="button" class="lnk" data-act="xact" data-action="fix" data-row="${r._row}" title="서류·증빙 보완 필요로 표시">보완</button>`
          : kind === "exec" && v === "취소" ? `<button type="button" class="lnk" data-act="xact" data-action="uncancel" data-row="${r._row}" title="${esc(latestCancel(r["거래번호"])?.["사유"] ? "취소 사유: " + latestCancel(r["거래번호"])["사유"] + " — 눌러서 해제" : "취소 해제")}" aria-label="취소 해제">해제</button>`
          : kind === "exec" && v === "보완" ? `<button type="button" class="lnk fix" data-act="xact" data-action="unfix" data-row="${r._row}" title="${esc(latestFix(r["거래번호"])?.["사유"] ? "보완 사유: " + latestFix(r["거래번호"])["사유"] + " — 눌러서 해제" : "보완 표시 해제")}" aria-label="보완 해제">해제</button>` : "";
        const sub = kind === "exec" && (stDate || fixLink) ? `<div class="s">${stDate ? `<span title="${esc(stDate)}">${esc(mmdd(stDate))}</span>` : ""}${stDate && fixLink ? " · " : ""}${fixLink}</div>` : "";
        return `<td class="st-cell${v === "보완" ? " fix" : ""}"><div class="t"><span class="badge ${esc(v)}" title="${esc(kind === "exec" ? STATUS_HELP[v] || "" : "")}">${esc(kind === "exec" ? STATUS_LABEL[v] || v : v)}</span>${nx ? `<button type="button" class="next" data-act="xact" data-action="${nx[0]}" data-row="${r._row}" title="다음 단계로: ${esc(nx[1])} (${esc(nx[2])})" aria-label="다음 단계로: ${esc(nx[1])}"><svg viewBox="0 0 12 12" aria-hidden="true" focusable="false"><path d="M2.5 6.5l2.5 2.5 4.5-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>` : (kind === "exec" ? '<span class="next ph" aria-hidden="true"></span>' : "")}</div>${sub || (kind === "exec" ? '<div class="s">&nbsp;</div>' : "")}</td>`;
      }
      if (c.t === "title") { const memo = String(r["비고"] || "").trim(), sub = c.subCalc ? c.subCalc(r) : r[c.sub]; return `<td class="tit${memo ? " memo" : ""}" title="${esc([v, sub].filter(Boolean).join(" · "))}${memo ? esc("\n비고: " + memo) : ""}"${memo ? ` data-memo="${esc(memo)}"` : ""}>${memo ? '<i class="memo-mark" aria-hidden="true"></i>' : ""}<div class="t">${esc(v || "")}${kind === "exec" ? originBadge(r) : ""}</div>${sub ? `<div class="s">${esc(sub)}</div>` : ""}</td>`; }
      if ((kind === "exec" && c.k === "거래번호") || c.rowbtn) return `<td class="nowrap"><button type="button" class="rowbtn" aria-label="${esc(v)} 상세 열기 (Shift+Enter 수정)">${esc(v)}</button></td>`;
      return `<td class="${c.wrap ? "wrap" : ""}${minorCls(c)}"${c.wrap && v ? ` title="${esc(v)}"` : ""}>${esc(v)}</td>`;
  }
  function rowHtml(r, tds) {
    const extra = kind === "req" && r["상태"] === "대기"
      ? `<button type="button" class="btn btn-sm" data-act="toexec" data-row="${r._row}">집행전환</button>`
      : kind === "labor" ? (r["상태"] === "예정" ? `<button type="button" class="btn btn-sm" data-labor="confirm" data-row="${r._row}" title="지급일을 입력하고 확정 (집행내역에 기록)">확정</button>` : `<button type="button" class="btn btn-sm" data-labor="unconfirm" data-row="${r._row}" title="예정으로 되돌리고 연결 집행 삭제">확정 취소</button>`) : "";
    const editBtn = kind === "labor" && r["상태"] === "확정" ? "" : `<button type="button" class="btn btn-sm" data-act="edit" data-kind="${kind}" data-row="${r._row}">수정</button>`;
    return `<tr data-kind="${kind}" data-row="${r._row}" class="${kind === XD.kind && XD.row === r._row ? "selected" : ""}${kind === "exec" && r["상태"] === "보완" ? " row-alert" : ""}${kind === "exec" && r["상태"] === "취소" ? " row-cancel" : ""}${SEL_HOOK[kind]?.rowCls(r) || ""}">${SEL_HOOK[kind]?.cell(r) || ""}${kind === "exec" && DELMODE ? `<td class="sel">${execOrigin(r)?.locked ? '<input type="checkbox" disabled title="인건비·적립금과 연결된 집행은 원본 화면에서 처리">' : `<input type="checkbox" data-selrow="${r._row}" aria-label="${esc(r["거래번호"])} 삭제 선택"${DELSEL.has(r._row) ? " checked" : ""}>`}</td>` : ""}${tds}${noAct ? "" : `<td class="actions">${extra}${editBtn}<button type="button" class="btn btn-sm btn-danger" data-act="del" data-kind="${kind}" data-row="${r._row}">삭제</button></td>`}</tr>`;
  }
  let foot = "";
  if (rows.length && (kind === "exec" || kind === "req" || kind === "deposit" || kind === "labor" || kind === "request")) {
    const sum = rows.reduce((a, r) => a + (r["금액"] || 0), 0);
    foot = `<tfoot><tr class="total">${selHead ? '<td class="sel"></td>' : ""}${cols.map(c => c.k === "금액" ? `<td data-col="${esc(c.k)}" class="num amt${minorCls(c)}">${fmt(sum)}</td>` : `<td data-col="${esc(c.k)}" class="${minorCls(c).trim()}">${c === cols[0] ? `합계 ${rows.length}건` : ""}</td>`).join("")}${noAct ? "" : '<td class="actions"></td>'}</tr></tfoot>`;
  }
  table.innerHTML = headFinal + `<tbody>${body}</tbody>` + foot;
  table.querySelectorAll("th.sortable").forEach(th => th.addEventListener("click", () => {
    const k = th.dataset.sort; const cur = SORT[kind] || (defKey ? { k: defKey, dir: -1 } : null);
    SORT[kind] = cur && cur.k === k ? { k, dir: -cur.dir } : { k, dir: 1 }; renderList(kind);
    table.querySelector(`th[data-sort="${CSS.escape(k)}"] .sortbtn`)?.focus();  // 다시 그린 뒤 같은 머리글에 포커스 유지
  }));
  const wrap = table.closest(".table-wrap"); if (wrap) { wrap.classList.toggle("empty", rows.length === 0); wrap.classList.toggle("scrollable", table.scrollWidth > wrap.clientWidth + 4); }
  if (kind === "exec") updateXdNav();  // 필터·정렬이 바뀌면 상세 패널의 n / N 도 갱신
  SEL_HOOK[kind]?.after?.();

  if (kind === "exec" || kind === "req" || kind === "labor" || kind === "request") {
    const sum = rows.reduce((a, r) => a + (r["금액"] || 0), 0);
    $(`#${kind}-sum`).textContent = `${rows.length}건 · 합계 ${fmt(sum)}원`;
  }
}

function renderBudgetSummary() {
  const items = DATA.meta.budget_items;
  const funds = fundOptions();
  const sum = {};
  funds.forEach(f => sum[f] = Object.fromEntries(items.map(i => [i, 0])));
  DATA.budget.forEach(r => { if (sum[r["재원"]]) items.forEach(i => sum[r["재원"]][i] += r[i] || 0); });
  const head = `<thead><tr><th>재원</th>${items.map(i => `<th class="num">${esc(i)}</th>`).join("")}<th class="num">예산현액 합계</th></tr></thead>`;
  const body = funds.map(f => {
    const t = items.reduce((a, i) => a + sum[f][i], 0);
    return `<tr><td>${esc(f)}</td>${items.map(i => `<td class="num">${fmt(sum[f][i])}</td>`).join("")}<td class="num">${fmt(t)}</td></tr>`;
  }).join("") || `<tr><td class="empty" colspan="${items.length + 2}">예산 데이터가 없습니다.</td></tr>`;
  $("#budget-summary").innerHTML = head + `<tbody>${body}</tbody>`;
}

function renderDepositSummary() {
  const m = {};
  DATA.deposit.forEach(r => {
    const v = r["거래처"] || "(미지정)";
    m[v] = m[v] || { in: 0, out: 0, last: "" };
    if (r["구분"] === "적립") m[v].in += r["금액"] || 0; else m[v].out += r["금액"] || 0;
    if ((r["일자"] || "") > m[v].last) m[v].last = r["일자"] || "";
  });
  const rows = Object.entries(m).sort((a, b) => a[0].localeCompare(b[0]));
  const t = rows.reduce((a, [, v]) => ({ in: a.in + v.in, out: a.out + v.out }), { in: 0, out: 0 });
  const head = `<thead><tr><th>거래처</th><th class="num amt">적립 누계</th><th class="num">사용 누계</th><th class="num">잔액</th><th>최근 거래일</th><th class="actions">작업</th></tr></thead>`;
  const body = rows.map(([v, x]) => `<tr><td>${esc(v)}</td><td class="num amt">${fmt(x.in)}</td><td class="num">${fmt(x.out)}</td><td class="num ${x.in - x.out < 0 ? "neg" : ""}">${fmt(x.in - x.out)}</td><td>${esc(x.last)}</td><td class="actions"><button type="button" class="btn btn-sm" data-act="dep-use" data-vendor="${esc(v)}">사용 입력</button><button type="button" class="btn btn-sm" data-act="dep-add" data-vendor="${esc(v)}">적립 입력</button></td></tr>`).join("")
    + (rows.length ? `<tr class="total"><td>합계</td><td class="num amt">${fmt(t.in)}</td><td class="num">${fmt(t.out)}</td><td class="num">${fmt(t.in - t.out)}</td><td></td><td></td></tr>` : "");
  $("#deposit-summary").innerHTML = head + `<tbody>${body || '<tr><td class="empty" colspan="6">적립금 내역이 없습니다.</td></tr>'}</tbody>`;
}

function switchSubTab(name) {
  $$("#panel-dash .subtabs [role=tab]").forEach(b => {
    const on = b.id === "sub-" + name;
    b.setAttribute("aria-selected", on);
    $("#" + b.getAttribute("aria-controls")).hidden = !on;
  });
  try { localStorage.setItem("ledger-subtab", name); } catch { }
}
$$("#panel-dash .subtabs [role=tab]").forEach(b => b.addEventListener("click", () => switchSubTab(b.id.replace("sub-", ""))));
try { const st = localStorage.getItem("ledger-subtab"); if (st && $("#sub-" + st)) switchSubTab(st); } catch { }

function renderTagDashboard(fund, year) {
  const linked = new Set(DATA.deposit.map(r => r["연결거래번호"]).filter(Boolean));
  const inYear = d => !year || (d || "").startsWith(year);
  const rows = activeExec().filter(r => !linked.has(r["거래번호"]) && (!fund || r["재원"] === fund) && inYear(r["원인발생일"]))
    .map(r => ({ tag: r["태그"], d: r["원인발생일"], amt: r["금액"] || 0, src: "exec" }));
  if (!fund) rows.push(...DATA.deposit.filter(r => r["구분"] === "사용" && inYear(r["일자"])).map(r => ({ tag: r["태그"], d: r["일자"], amt: r["금액"] || 0, src: "dep" })));
  $("#tag-note").textContent = (fund ? "재원 필터 적용 중: 적립금 사용 건(재원 없음)은 제외됩니다. " : "집행내역(적립 선결제 건 제외) + 적립금 사용 건. ")
    + (year ? `${year}년 기준.` : "전체 기간.");
  {
    const execAll = activeExec().filter(r => (!fund || r["재원"] === fund) && inYear(r["원인발생일"])).reduce((a, r) => a + (r["금액"] || 0), 0);
    const linkedAmt = activeExec().filter(r => linked.has(r["거래번호"]) && (!fund || r["재원"] === fund) && inYear(r["원인발생일"])).reduce((a, r) => a + (r["금액"] || 0), 0);
    const depUse = fund ? 0 : DATA.deposit.filter(r => r["구분"] === "사용" && inYear(r["일자"])).reduce((a, r) => a + (r["금액"] || 0), 0);
    $("#tag-recon").textContent = `조정: 예산 집계 집행액 ${fmt(execAll)} − 적립 선결제 ${fmt(linkedAmt)} + 적립금 사용 ${fmt(depUse)} = 태그 집계 ${fmt(execAll - linkedAmt + depUse)}원`;
  }

  const cat = Object.fromEntries(DATA.tags.map(t => [t["태그명"], t["분류"] || "기타"]));
  const agg = {};
  rows.forEach(x => {
    const t = x.tag || "(태그 없음)";
    const e = agg[t] = agg[t] || { tag: t, cat: x.tag ? (cat[x.tag] || "(미등록)") : "", amt: 0, n: 0, dep: 0, months: {} };
    e.amt += x.amt; e.n++; if (x.src === "dep") e.dep += x.amt;
    if (x.d) e.months[x.d.slice(0, 7)] = (e.months[x.d.slice(0, 7)] || 0) + x.amt;
  });
  const total = rows.reduce((a, x) => a + x.amt, 0);
  const untagged = agg["(태그 없음)"];
  $("#tag-cards").innerHTML = [["집계 금액", fmt(total)], ["건수", rows.length + "건"], ["태그 수", Object.keys(agg).filter(k => k !== "(태그 없음)").length + "개"],
    ["태그 없음", untagged ? `${fmt(untagged.amt)} (${untagged.n}건)` : "0"]]
    .map(([k, v]) => `<div class="card"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("");

  // 분류별 소계 표
  const byCat = {};
  Object.values(agg).forEach(e => (byCat[e.cat] = byCat[e.cat] || []).push(e));
  let body = "";
  Object.keys(byCat).sort((a, b) => (a === "" ? 1 : b === "" ? -1 : a.localeCompare(b))).forEach(c => {
    const list = byCat[c].sort((a, b) => b.amt - a.amt);
    const ca = list.reduce((a, e) => a + e.amt, 0), cn = list.reduce((a, e) => a + e.n, 0);
    body += `<tr class="total"><td>${esc(c || "(태그 없음)")}</td><td>소계</td><td class="num amt">${fmt(ca)}</td><td class="num">${cn}</td><td class="num">${pct(total ? ca / total : null)}</td><td class="num">${fmt(list.reduce((a, e) => a + e.dep, 0))}</td></tr>`;
    list.forEach(e => { body += `<tr class="sub"><td></td><td>${esc(e.tag)}</td><td class="num amt">${fmt(e.amt)}</td><td class="num">${e.n}</td><td class="num">${pct(total ? e.amt / total : null)}</td><td class="num">${fmt(e.dep)}</td></tr>`; });
  });
  $("#tag-table").innerHTML = `<thead><tr><th>분류</th><th>태그</th><th class="num amt">금액</th><th class="num">건수</th><th class="num">비중</th><th class="num">(그중 적립금 사용)</th></tr></thead><tbody>${body || '<tr><td class="empty" colspan="6">집계할 데이터가 없습니다.</td></tr>'}</tbody>`;

  // 태그 × 월
  const months = year ? Array.from({ length: 12 }, (_, i) => `${year}-${String(i + 1).padStart(2, "0")}`)
    : [...new Set(rows.map(x => (x.d || "").slice(0, 7)).filter(Boolean))].sort();
  const list = Object.values(agg).sort((a, b) => (a.cat || "힣").localeCompare(b.cat || "힣") || b.amt - a.amt);
  const mh = `<thead><tr><th>태그</th>${months.map(m => `<th class="num">${year ? parseInt(m.slice(5)) + "월" : esc(m)}</th>`).join("")}<th class="num">합계</th></tr></thead>`;
  const mb = list.map(e => `<tr><td>${esc(e.tag)}</td>${months.map(m => `<td class="num">${e.months[m] ? fmt(e.months[m]) : ""}</td>`).join("")}<td class="num"><b>${fmt(e.amt)}</b></td></tr>`).join("")
    + (list.length ? `<tr class="total"><td>합계</td>${months.map(m => `<td class="num">${fmt(list.reduce((a, e) => a + (e.months[m] || 0), 0))}</td>`).join("")}<td class="num">${fmt(total)}</td></tr>` : "");
  $("#tag-month").innerHTML = mh + `<tbody>${mb || '<tr><td class="empty" colspan="' + (months.length + 2) + '">없음</td></tr>'}</tbody>`;
}

function renderDashboard() {
  const fund = $("#dash-fund").value;
  const year = $("#dash-year").value;
  const month = year ? $("#dash-month").value : "";
  $("#dash-month").disabled = !year;
  renderTagDashboard(fund, year);
  const items = DATA.meta.budget_items;
  // 집계 범위 = 재원 시트의 재원 × 예산목 목록 (isExcludedExec · 서버 build_dashboard 와 같은 규칙). 목록 밖은 '집계 제외'로 따로 표시
  const funds = (fund ? [fund] : fundOptions()).filter(f => DATA.funds.some(x => x["재원코드"] === f) && !isPoolFund(f) && !isUntrackedFund(f));
  const poolFunds = (fund ? [fund] : fundOptions()).filter(f => isPoolFund(f) && !isUntrackedFund(f));  // 공금: 예산목 없이 재원 잔액 한 줄
  const untrackedFunds = (fund ? [fund] : fundOptions()).filter(f => isUntrackedFund(f));  // 잔액 미관리: 집계·집계 제외 목록 모두에서 뺀다

  // 연도 필터는 집행·품의에 적용 (예산은 연도 개념 없이 재원 기준). 월을 고르면 '당월'과 '누계(연초~당월)'를 함께 표시
  const inYear = r => !year || (r["원인발생일"] || "").startsWith(year);
  const upTo = r => !month || (r["원인발생일"] || "").slice(5, 7) <= month;
  const inMonth = r => month && (r["원인발생일"] || "").slice(5, 7) === month;
  // 잔액·가용잔액·집행률은 파일 전체 기준(sa), 연·월 필터는 '집행액'(s)·'M월 집행'(sm) 열에만 적용. 대기 품의는 날짜 무관 전부 차감 (2026-10-13 결정)
  const execsAll = activeExec().filter(r => !fund || r["재원"] === fund);
  const execs = execsAll.filter(r => inYear(r) && upTo(r));
  const reqs = DATA.req.filter(r => r["상태"] === "대기" && (!fund || r["재원"] === fund) && !isExcludedExec(r));  // 목록 밖 재원·예산목 품의는 집계 제외
  const budgets = DATA.budget.filter(r => !fund || r["재원"] === fund);

  const cell = () => ({ b: 0, s: 0, sm: 0, sa: 0, p: 0 });
  const m = {};
  funds.forEach(f => { m[f] = {}; items.forEach(i => m[f][i] = cell()); });
  budgets.forEach(r => m[r["재원"]] && items.forEach(i => m[r["재원"]][i].b += r[i] || 0));
  const excluded = [];  // 재원 목록 밖(외부 지급처 인건비 등)·예산목 목록 밖 집행: 예산 집계에서 제외
  const pm = {};  // 공금 재원별 셀
  poolFunds.forEach(f => { pm[f] = cell(); pm[f].b = budgets.filter(r => r["재원"] === f).reduce((a, r) => a + (r["입금"] || 0), 0); });
  execsAll.forEach(r => { if (isUntrackedFund(r["재원"])) return; if (pm[r["재원"]]) { const c = pm[r["재원"]]; c.sa += r["금액"] || 0; if (inYear(r) && upTo(r)) { c.s += r["금액"] || 0; if (inMonth(r)) c.sm += r["금액"] || 0; } return; } const c = !isExcludedExec(r) && m[r["재원"]]?.[r["예산목"]]; if (!c) { if (inYear(r) && upTo(r)) excluded.push(r); return; } c.sa += r["금액"] || 0; if (inYear(r) && upTo(r)) { c.s += r["금액"] || 0; if (inMonth(r)) c.sm += r["금액"] || 0; } });
  reqs.forEach(r => { if (isUntrackedFund(r["재원"])) return; if (pm[r["재원"]]) { pm[r["재원"]].p += r["금액"] || 0; return; } !isExcludedExec(r) && m[r["재원"]]?.[r["예산목"]] && (m[r["재원"]][r["예산목"]].p += r["금액"] || 0); });
  const add = (t, c) => { t.b += c.b; t.s += c.s; t.sm += c.sm; t.sa += c.sa; t.p += c.p; };

  // 카드
  const tot = cell();
  funds.forEach(f => items.forEach(i => add(tot, m[f][i])));
  poolFunds.forEach(f => add(tot, pm[f]));
  const unpaid = execs.filter(r => !r["지출완료일"]).length;
  const itemCards = [...items.map(i => { const c = cell(); funds.forEach(f => add(c, m[f][i])); return [i, c]; }),
    ...poolFunds.map(f => [`${f} 잔액 (공금)`, pm[f]])]
    .filter(([, c]) => c.b || c.sa || c.p);
  $("#dash-cards").innerHTML = itemCards.length ? itemCards.map(([i, c]) => {
    const avail = c.b - c.sa - c.p, rate = c.b ? c.sa / c.b : null, used = c.b ? Math.min(1, (c.sa + c.p) / c.b) : 1;
    const bar = c.b ? `<div class="bar" aria-hidden="true"><i class="${c.sa > c.b ? "over" : ""}" style="width:${Math.min(100, c.sa / c.b * 100).toFixed(1)}%"></i>${c.p ? `<i class="p" style="left:${Math.min(100, c.sa / c.b * 100).toFixed(1)}%;width:${Math.max(0, (used - Math.min(1, c.sa / c.b)) * 100).toFixed(1)}%"></i>` : ""}</div>` : "";
    return `<div class="card" role="listitem" title="${esc(i)}: 예산현액 ${fmt(c.b)} · 집행 ${fmt(c.sa)}${c.p ? ` · 품의대기 ${fmt(c.p)}` : ""} · 가용잔액 ${fmt(avail)}"><div class="k">${esc(i)}</div>${c.b ? `<div class="v${avail < 0 ? " neg" : ""}">${fmt(avail)}</div>` : `<div class="v nobudget" title="예산변동에 이 예산목의 예산을 입력하면 가용잔액이 계산됩니다">예산 미입력</div>`}<div class="sub"><span>집행 ${fmt(c.sa)}${c.p ? ` <span class="muted">+대기 ${fmt(c.p)}</span>` : ""}</span><span>${rate == null ? "" : pct(rate)}</span></div>${bar}</div>`;
  }).join("") : `<div class="card empty-card"><div class="k">예산목별 가용잔액</div><div class="v">-</div><div class="sub"><span>${DATA.funds.length ? "예산·집행 데이터가 없습니다" : "재원을 먼저 등록하세요"}</span></div></div>`;
  const exAmt = excluded.reduce((a, r) => a + (r["금액"] || 0), 0);
  $("#dash-note").innerHTML = esc((year ? (month ? `${year}년 1월~${parseInt(month)}월 누계 · ` : `${year}년 · `) : "전체 기간 · ") + `예산현액 ${fmt(tot.b)} · 집행 ${fmt(tot.s)}${month ? ` (${parseInt(month)}월 ${fmt(tot.sm)})` : ""} · 집행률 ${tot.b ? pct(tot.sa / tot.b) : "-"} · ${tot.p || reqs.length ? `품의대기 ${fmt(tot.p)} (${reqs.length}건) · ` : ""}가용잔액 ${tot.b ? fmt(tot.b - tot.sa - tot.p) : "예산 미입력"} · 미승인 ${unpaid}건`)
    + (untrackedFunds.length ? ` · <span class="muted" title="재원 탭에서 '잔액 미관리'로 표시한 재원: 재원 출처로만 쓰고 예산·잔액 집계에 넣지 않음">잔액 미관리 재원 ${untrackedFunds.length}곳 (${untrackedFunds.join(", ")})</span>` : "")
    + (excluded.length ? ` · <button type="button" class="link" data-act="show-excluded" title="재원 목록에 없는 지급처(외부 인건비 등)나 예산목 목록 밖의 집행. 집행내역·태그 집계에는 포함되지만 예산 집계에서는 제외">집계 제외 ${excluded.length}건 ${fmt(exAmt)}원</button>` : "");
  $("#dash-defs").innerHTML = `칸의 큰 숫자 = 가용잔액 = 예산현액 − 집행(파일 전체) − 품의대기(날짜 무관, 선택한 재원 합산) · 막대 = 집행률(회색은 품의대기) · 예산현액 = 재원별 이월+당초+변경 합계 · 집행액 열만 연·월 필터(원인발생일) 적용 · 잔액 = 예산현액 − 집행(전체) · 미승인 = 지출완료일 없는 집행 건 · 공금 재원은 예산목 구분 없이 입금 합계 − 집행으로 잔액 한 줄`;

  // 표
  const cols = month ? ["예산현액", `${parseInt(month)}월 집행`, "누계 집행", "잔액", "집행률", "품의대기", "가용잔액"] : ["예산현액", "집행액", "잔액", "집행률", "품의대기", "가용잔액"];
  const th = `<thead><tr><th>재원</th><th>예산목</th>${cols.map(c => `<th class="num${c === "예산현액" ? " amt" : ""}">${c}</th>`).join("")}</tr></thead>`;
  const line = (f, i, c, cls) => `<tr class="${cls}"><td>${cls === "total" ? esc(f) : ""}</td><td>${esc(i)}</td><td class="num amt">${fmt(c.b)}</td>${month ? `<td class="num">${fmt(c.sm)}</td>` : ""}<td class="num">${fmt(c.s)}</td><td class="num ${c.b && c.b - c.sa < 0 ? "neg" : ""}">${c.b ? fmt(c.b - c.sa) : '<span class="muted" title="예산 미입력">-</span>'}</td><td class="num">${pct(c.b ? c.sa / c.b : null)}</td><td class="num">${fmt(c.p)}</td><td class="num ${c.b && c.b - c.sa - c.p < 0 ? "neg" : ""}">${c.b ? fmt(c.b - c.sa - c.p) : '<span class="muted" title="예산 미입력">-</span>'}</td></tr>`;
  let body = "";
  DASH_ROWS = [];
  poolFunds.forEach(f => {
    const c = pm[f]; if (!c.b && !c.sa && !c.p) return;
    body += line(f, "잔액 (공금)", c, "total"); DASH_ROWS.push([f, "잔액 (공금)", c.b, ...(month ? [c.sm] : []), c.s, c.b - c.sa, c.b ? (c.sa / c.b * 100).toFixed(1) + "%" : "", c.p, c.b - c.sa - c.p]);
  });
  funds.forEach(f => {
    const ft = cell();
    let rows = "";
    items.forEach(i => {
      const c = m[f][i];
      if (!c.b && !c.sa && !c.p) return;
      add(ft, c);
      rows += line(f, i, c, "sub"); DASH_ROWS.push([f, i, c.b, ...(month ? [c.sm] : []), c.s, c.b - c.sa, c.b ? (c.sa / c.b * 100).toFixed(1) + "%" : "", c.p, c.b - c.sa - c.p]);
    });
    if (!rows) return;
    body += line(f, "소계", ft, "total") + rows;
  });
  DASH_COLS = ["재원", "예산목", ...cols];
  $("#dash-table").closest(".table-wrap").classList.toggle("empty", !body);
  $("#dash-table").innerHTML = th + `<tbody>${body || `<tr><td class="empty" colspan="${cols.length + 2}">${DATA.funds.length ? "예산 또는 집행 데이터가 없습니다." : "등록된 재원이 없습니다. [재원] 탭에서 과제를 먼저 등록하고 [예산변동]에 예산을 입력하세요."}</td></tr>`}</tbody>`;

  // 월별 차트 (누적선 + 예산현액 기준선)
  renderChart(execs, funds, year, tot.b);

  // 거래처별 적립금 잔액 (재원 구분 없음)
  const dep = {};
  DATA.deposit.forEach(r => { const v = r["거래처"] || "(미지정)"; dep[v] = (dep[v] || 0) + (r["구분"] === "적립" ? 1 : -1) * (r["금액"] || 0); });
  const depRows = Object.entries(dep).filter(([, v]) => v !== 0).sort((a, b) => b[1] - a[1]);
  const depTot = depRows.reduce((a, [, v]) => a + v, 0);
  $("#dash-deposit").innerHTML = `<thead><tr><th>거래처</th><th class="num amt">잔액</th></tr></thead><tbody>${depRows.slice(0, 10).map(([k, v]) => `<tr><td class="wrap">${esc(k)}</td><td class="num amt${v < 0 ? " neg" : ""}">${fmt(v)}</td></tr>`).join("") || '<tr><td class="empty" colspan="2">적립금 잔액이 없습니다.</td></tr>'}</tbody>${depRows.length ? `<tfoot><tr class="total"><td>합계${depRows.length > 10 ? ` (${depRows.length}곳)` : ""}</td><td class="num amt${depTot < 0 ? " neg" : ""}">${fmt(depTot)}</td></tr></tfoot>` : ""}`;
}

let DASH_ROWS = [], DASH_COLS = [];
function toCSV(cols, rows) { const q = v => `"${String(v ?? "").replace(/"/g, '""')}"`; return "\ufeff" + [cols, ...rows].map(r => r.map(q).join(",")).join("\r\n"); }
function downloadCSV(name, cols, rows) { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([toCSV(cols, rows)], { type: "text/csv;charset=utf-8" })); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000); }
$("#dash-csv").addEventListener("click", () => { if (!DASH_ROWS.length) { showAlert("저장할 표가 없습니다.", "warn"); return; } downloadCSV(`집행현황_${$("#dash-fund").value || "전체"}_${$("#dash-year").value || "전체"}${$("#dash-month").value ? "-" + $("#dash-month").value : ""}.csv`, DASH_COLS, DASH_ROWS); });
$("#dash-print").addEventListener("click", () => window.print());
// 인쇄 머리글: 화면 이름·재원·기간·출력일 (대시보드는 합계 한 줄 포함). 집계 기준은 펼쳐서 인쇄
window.addEventListener("beforeprint", () => {
  const labor = document.body.classList.contains("labor-mode");
  const tab = $(`${labor ? "#labor-tabs" : "#main-tabs"} [role=tab][aria-selected="true"]`);
  const panel = tab ? $("#" + tab.getAttribute("aria-controls")) : null, dash = panel?.id === "panel-dash" && !document.body.classList.contains("request-mode");
  const val = sel => panel?.querySelector(sel)?.value || "";
  const fund = dash ? $("#dash-fund").value : (val('[data-filter="재원"]') || val('[data-filter="지급처"]'));
  const year = dash ? $("#dash-year").value : (val('[data-filter="year"]') || (labor && panel?.id === "lpanel-plan" ? $("#labor-year").value : ""));
  const month = dash ? $("#dash-month").value : val('[data-filter="month"]');
  const period = year ? `${year}년${month ? " " + parseInt(month) + "월" : ""}` : month ? `${parseInt(month)}월` : "전체 기간";
  let name = (labor ? "인건비 " : "") + (tab?.textContent.trim() || "");
  if (document.body.classList.contains("request-mode")) name = "지출 신청 " + ($("#request-tabs [aria-selected=true]")?.dataset.rtype || "") + (typeof reqSub === "function" && reqSub() === "주문" ? " · 주문" : "");
  if (dash) name += ` (${$("#panel-dash .subtabs [aria-selected=true]")?.textContent.trim() || ""})`;
  const note = dash ? $("#dash-note").textContent.trim() : "";
  // 신청 화면: 숨은 회계대장 탭의 재원·예산 값 대신 연도·구매처·상태 (request.js reqPrintHead)
  if (document.body.classList.contains("request-mode") && typeof reqPrintHead === "function") $("#print-head").innerHTML = `<b>의료인공지능센터 회계대장</b> · ${esc(reqPrintHead())} · 출력일 ${today()}`;
  else $("#print-head").innerHTML = `<b>의료인공지능센터 회계대장</b> · ${esc(name)} · 재원 ${esc(fund || "전체")} · ${esc(period)} · 출력 ${today()}${note ? `<p>${esc(note)}</p>` : ""}`;
  $$("details.defs-box").forEach(d => { if (!d.open) { d.open = true; d.dataset.printOpened = "1"; } });
});
window.addEventListener("afterprint", () => {
  $$("details.defs-box[data-print-opened]").forEach(d => { d.open = false; delete d.dataset.printOpened; });
});
$("#dash-month").addEventListener("change", renderDashboard);
$$("[data-csv]").forEach(b => b.addEventListener("click", () => {
  const kind = b.dataset.csv; const cols = COLS[kind].filter(c => !c.calc).map(c => c.k); const rows = filtered(kind).map(r => cols.map(k => k === "상태" && kind === "exec" ? (r["상태표시"] || STATUS_LABEL[r[k]] || r[k]) : r[k]));  // 집행 상태는 화면 이름 (서버 상태표시와 같음)
  if (!rows.length) { showAlert("저장할 행이 없습니다.", "warn"); return; }
  downloadCSV(`${{ exec: "집행내역", req: "품의내역", labor: "인건비지급", request: "지출신청" }[kind] || kind}_${today()}.csv`, cols, rows);
}));
$("#exec-cols-all").addEventListener("change", e => { try { localStorage.setItem("ledger-exec-minor", e.target.checked ? "1" : "0"); } catch { } renderList("exec"); });
try { $("#exec-cols-all").checked = localStorage.getItem("ledger-exec-minor") === "1"; } catch { }

const PALETTE = ["#246BEB", "#008A1E", "#E66B00", "#8A2BE2", "#0097A7", "#C2185B", "#5D6D7E", "#9A6700"];
const short = n => n >= 1e8 ? (n / 1e8).toFixed(1) + "억" : n >= 1e6 ? Math.round(n / 1e4).toLocaleString() + "만" : n >= 1e4 ? (n / 1e4).toFixed(1).replace(/\.0$/, "") + "만" : fmt(n);
function renderChart(execs, allFunds, year, budget) {
  const months = year ? Array.from({ length: 12 }, (_, i) => `${year}-${String(i + 1).padStart(2, "0")}`)
    : [...new Set(execs.map(r => (r["원인발생일"] || "").slice(0, 7)).filter(Boolean))].sort();
  const funds = allFunds.filter(f => execs.some(r => r["재원"] === f));  // 범례는 데이터가 있는 재원만
  const series = funds.map(f => months.map(mo => execs.filter(r => r["재원"] === f && (r["원인발생일"] || "").startsWith(mo)).reduce((a, r) => a + (r["금액"] || 0), 0)));
  const totals = months.map((_, i) => series.reduce((a, s) => a + s[i], 0));
  const cum = []; totals.reduce((a, v, i) => (cum[i] = a + v), 0);
  const lastIdx = totals.map((v, i) => v > 0 ? i : -1).reduce((a, b) => Math.max(a, b), -1);  // 데이터가 있는 마지막 달까지만 누적선
  const cumEnd = lastIdx >= 0 ? cum[lastIdx] : 0;
  const showBudget = budget > 0 && budget <= Math.max(cumEnd, ...totals) * 2.5;  // 예산선이 그래프를 납작하게 만들면 글자로만 표기
  const rawMax = Math.max(1, ...totals, cumEnd, showBudget ? budget : 0) * 1.15;  // 최대 막대 위 값 라벨 여유
  // 눈금은 1·2·2.5·5×10ⁿ 간격의 깔끔한 수 (0/25/50/75/100 등)
  const step = (raw => { const p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p; return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p; })(rawMax / 4);
  const nTick = Math.max(1, Math.ceil(rawMax / step - 1e-9)), max = step * nTick;
  const W = 720, H = 248, padL = 70, padB = 28, padT = 20;
  const man = max >= 2e4;  // 축 표기 통일: 만원 또는 원
  const tick = v => man ? (v / 1e4).toFixed(v / 1e4 >= 10 ? 0 : 1).replace(/\.0$/, "") : fmt(Math.round(v));
  const bw = (W - padL - 10) / Math.max(1, months.length);
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="월별 집행 추이 막대 그래프">`;
  let lastLabel = null;
  for (let g = 0; g <= nTick; g++) {
    const y = padT + (H - padT - padB) * (1 - g / nTick);
    const label = tick(step * g);
    svg += `<line x1="${padL}" x2="${W - 10}" y1="${y}" y2="${y}" stroke="#E7EAEE"/>` + (label !== lastLabel ? `<text x="${padL - 6}" y="${y + 4}" font-size="10" text-anchor="end" fill="#5A6270">${label}</text>` : "");
    lastLabel = label;
  }
  svg += `<text x="${W - 10}" y="${padT - 6}" font-size="10" text-anchor="end" fill="#5A6270">단위: ${man ? "만원" : "원"}${budget > 0 && !showBudget ? ` · 예산현액 ${fmt(budget)}원` : ""}</text>`;
  const Y = v => H - padB - (v / max) * (H - padT - padB);
  const budgetColor = cumEnd > budget ? "#B3261E" : "#5A6270";  // 예산선은 회색 점선, 누적 집행이 넘으면 붉은색
  if (showBudget) svg += `<line x1="${padL}" x2="${W - 10}" y1="${Y(budget)}" y2="${Y(budget)}" stroke="${budgetColor}" stroke-width="1" stroke-dasharray="4 3"/><text x="${padL + 4}" y="${Y(budget) - 3}" font-size="9" fill="${budgetColor}">예산현액 ${man ? tick(budget) : fmt(budget)}${cumEnd > budget ? " (초과)" : ""}</text>`;
  months.forEach((mo, i) => {
    let y0 = H - padB;
    series.forEach((s, si) => {
      const h = (s[i] / max) * (H - padT - padB);
      if (h > 0) { svg += `<rect x="${padL + i * bw + bw * .15}" y="${y0 - h}" width="${bw * .7}" height="${h}" fill="${PALETTE[si % PALETTE.length]}"><title>${esc(funds[si])} ${mo}: ${fmt(s[i])}원</title></rect>`; y0 -= h; }
    });
    if (totals[i] > 0) svg += `<text x="${padL + i * bw + bw / 2}" y="${y0 - 4}" font-size="9" text-anchor="middle" fill="#1E2124">${man ? tick(totals[i]) : fmt(totals[i])}</text>`;
    svg += `<text x="${padL + i * bw + bw / 2}" y="${H - 8}" font-size="10" text-anchor="middle" fill="#5A6270">${year ? parseInt(mo.slice(5)) + "월" : esc(mo)}</text>`;
  });
  if (lastIdx >= 0) {
    const firstIdx = totals.findIndex(v => v > 0);  // 첫 집행 달부터 누적선
    const pts = cum.slice(firstIdx, lastIdx + 1).map((v, i) => `${(padL + (firstIdx + i) * bw + bw / 2).toFixed(1)},${Y(v).toFixed(1)}`);
    svg += `<polyline points="${pts.join(" ")}" fill="none" stroke="#1F3A93" stroke-width="1.5" stroke-linejoin="round"/>`;
    svg += pts.map(p => `<circle cx="${p.split(",")[0]}" cy="${p.split(",")[1]}" r="2.2" fill="#1F3A93"/>`).join("");
    const ex = padL + lastIdx * bw + bw / 2, ey = Y(cumEnd);
    svg += `<text x="${Math.min(ex + 6, W - 12)}" y="${ey - 6}" font-size="9" text-anchor="${lastIdx >= months.length - 2 ? "end" : "start"}" fill="#1F3A93">누적 ${man ? tick(cumEnd) : fmt(cumEnd)}</text>`;
  }
  svg += "</svg>";
  const legend = `<div class="legend">${funds.map((f, i) => `<span><i style="background:${PALETTE[i % PALETTE.length]}"></i>${esc(f)}</span>`).join("")}<span><i style="background:#1F3A93;height:2px;vertical-align:3px"></i>누적 집행</span>${showBudget ? `<span><i style="background:${budgetColor};height:2px;vertical-align:3px"></i>예산현액</span>` : ""}</div>`;
  const mlabel = mo => year ? parseInt(mo.slice(5)) + "월" : mo;
  const srTable = `<table class="sr-only"><caption>월별 집행 추이 표</caption><thead><tr><th scope="col">월</th>${funds.map(f => `<th scope="col">${esc(f)}</th>`).join("")}<th scope="col">합계</th><th scope="col">누적</th></tr></thead><tbody>${months.map((mo, i) => `<tr><th scope="row">${esc(mlabel(mo))}</th>${series.map(s => `<td>${fmt(s[i])}원</td>`).join("")}<td>${fmt(totals[i])}원</td><td>${fmt(cum[i])}원</td></tr>`).join("")}</tbody></table>`;
  $("#dash-chart").innerHTML = svg + legend + srTable;
}

// ---------- 입력 대화상자 ----------
const LAST = {};  // 종류별 직전 입력값 (연속 입력용)
function lastDefaults(kind) {
  try { return JSON.parse(sessionStorage.getItem("ledger-last-" + kind) || "{}"); } catch { return {}; }
}
function rememberLast(kind, rec) {
  const keep = { exec: ["재원", "예산목", "사용자"], req: ["재원", "예산목", "품의자", "결제수단"], deposit: ["거래처", "사용자"], budget: ["재원"], request: ["관련과제"] }[kind] || [];  // 날짜는 '저장 후 계속' 안에서만 유지
  const o = {}; keep.forEach(k => { if (rec[k]) o[k] = rec[k]; });
  try { sessionStorage.setItem("ledger-last-" + kind, JSON.stringify(o)); } catch { }
}
function openForm(kind, row, preset, opts = {}) {
  const rec = row != null ? DATA[kind].find(r => r._row === row) : null;
  const fields = formFields(kind).filter(f => !(f.onlyNew && rec));
  const titles = { exec: "집행", req: "품의", budget: "예산 변동", funds: "재원", deposit: "적립금", tags: "태그", vendor: "거래처", memo: "메모", ...(typeof LABOR_TITLES !== "undefined" ? LABOR_TITLES : {}), ...(typeof REQUEST_TITLES !== "undefined" ? REQUEST_TITLES : {}) };
  $("#dlg-title").textContent = opts.title || (titles[kind] + (rec ? " 수정" + (IDENT_LABEL(kind, rec) ? " · " + IDENT_LABEL(kind, rec) : "") : " 추가"));
  $("#dlg-error").hidden = true; $("#dlg-error").classList.remove("info");
  $("#dlg-save-more").hidden = !!rec || !!opts.convertRow || !!opts.convertRequests || !["exec", "req", "deposit", "budget", "tags", "labor", "salary", "people", "request"].includes(kind);
  const tagDefault = DATA.tags.some(t => t["태그명"] === "적립금") ? "적립금" : "";
  const defaults = { 원인발생일: today(), 일자: today(), 상태: "대기", 구분: "적립", 종류: "국책", _태그: tagDefault, 재원: FILTERS[kind]?.["재원"] || "", ...(typeof laborDefaults === "function" ? laborDefaults(kind) : {}), ...(typeof requestDefaults === "function" ? requestDefaults(kind) : {}), ...lastDefaults(kind), ...(FILTERS[kind]?.["재원"] ? { 재원: FILTERS[kind]["재원"] } : {}), ...(preset || {}) };  // 필터 재원이 있으면 직전 입력값보다 우선
  $("#dlg-fields").innerHTML = fields.map(f => {
    const v = rec ? (rec[f.k] ?? "") : (defaults[f.k] ?? "");
    const id = "f-" + f.k;
    const lab = `${esc(f.label || f.k)}${f.req === true ? ' <span class="req" aria-hidden="true">*</span>' : ""}`;
    let input;
    if (f.type === "check") return `<label class="${f.cls || ""} chk" for="${id}" data-dep="${esc(f.dep || "")}"><input id="${id}" name="${esc(f.k)}" type="checkbox"${v === true || v === "Y" ? " checked" : ""}> ${lab}</label>`;
    if (f.type === "ro") input = `<input id="${id}" name="${esc(f.k)}" type="text" value="${esc(v || "(자동)")}" readonly tabindex="-1">`;
    else if (f.type === "select" && f.groups) input = `<select id="${id}" name="${esc(f.k)}"><option value="">(선택)</option>${(v && !f.opts.includes(v)) ? `<option value="${esc(v)}" selected>${esc(v)} (목록 외)</option>` : ""}${Object.entries(f.groups).map(([g, names]) => `<optgroup label="${esc(g)}">${names.map(o => `<option value="${esc(o)}"${o === v ? " selected" : ""}>${esc(o)}</option>`).join("")}</optgroup>`).join("")}</select>`;
    else if (f.type === "select") {
      const opts = f.opts.includes("") ? f.opts : ["", ...f.opts];  // 명시적 선택 강제
      const extra = (v !== "" && v != null && !opts.includes(v)) ? `<option value="${esc(v)}" selected>${esc(v)} (목록 외)</option>` : "";
      input = `<select id="${id}" name="${esc(f.k)}"${f.req ? " required" : ""}>${opts.map(o => `<option value="${esc(o)}"${o === v ? " selected" : ""}>${esc(o || "(선택)")}</option>`).join("")}${extra}</select>`;
    }
    else if (f.type === "date") input = `<input id="${id}" name="${esc(f.k)}" type="date" value="${esc(v)}"${f.req ? " required" : ""}>`;
    else if (f.type === "month") input = `<input id="${id}" name="${esc(f.k)}" type="month" value="${esc(v)}"${f.req ? " required" : ""}>`;
    else if (f.type === "num") input = `<input id="${id}" name="${esc(f.k)}" type="text" inputmode="numeric" class="num-input" value="${v === "" || v == null ? "" : fmt(v)}"${f.req ? " required" : ""} placeholder="0" title="'=' 로 시작하면 계산식 입력 가능 (예: =12000*3)">`;
    else if (f.type === "datalist") input = `<input id="${id}" name="${esc(f.k)}" type="text" list="dl-${esc(f.list || (f.k === "품의자" ? "사용자" : f.k))}" value="${esc(v)}" autocomplete="off"${f.req ? ' required aria-required="true"' : ""}>`;
    else input = `<input id="${id}" name="${esc(f.k)}" type="text" value="${esc(v)}"${f.req ? " required" : ""}>`;
    return `<label class="${f.cls || ""}" for="${id}" data-dep="${esc(f.dep || "")}"><span class="lab">${lab}${f.hint ? ` <small>(${esc(f.hint)})</small>` : ""}</span>${input}</label>`;
  }).join("");
  syncDepFields();
  if (kind === "exec" && rec) { const o = execOrigin(rec); if (o?.locked) { LOCKED_COLS.forEach(k => { const el = F(k); if (el) { el.readOnly = true; el.setAttribute("aria-readonly", "true"); if (el.tagName === "SELECT") el.dataset.lock = el.value; el.classList.add("locked"); el.title = `${o.kind} 연결 행: 원본에서만 변경`; } }); $("#dlg-error").textContent = `${o.label} 에서 생긴 집행입니다. 재원·예산목·금액·거래처·원인발생일은 원본에서 처리하고, 여기서는 세목·태그·관리번호·청구·승인·결의일·비고만 바꿀 수 있습니다.`; $("#dlg-error").hidden = false; $("#dlg-error").classList.add("info"); $("#dlg-error").setAttribute("role", "status"); } }
  const dlg = $("#dlg");
  dlg.dataset.kind = kind; dlg.dataset.row = row ?? ""; dlg.dataset.convert = opts.convertRow ?? "";
  dlg.dataset.convertReq = opts.convertRequests ? JSON.stringify(opts.convertRequests) : "";  // 신청 → 품의 전환 (request.js)
  dlg.dataset.convertPay = opts.convertPay ?? "";  // 주문 묶음 전환: 기본 금액 = 주문 결제금액 (바꾸면 amount_override)
  if (kind === "budget" && !rec && !preset?.["변경회차"]) {  // 다음 회차 자동 제안
    const sel = F("재원"); const fill = async () => { if (!sel.value) return; try { const r = await api("GET", `/api/budget/next-round?fund=${encodeURIComponent(sel.value)}`); if (!F("변경회차").value) F("변경회차").value = r.round; } catch { } };
    sel.addEventListener("change", () => { F("변경회차").value = ""; fill(); }); fill();
  }
  if (kind === "budget") { budgetFormSync(); F("재원")?.addEventListener("change", budgetFormSync); }
  dlg.showModal();
  const focusField = fields.find(f => f.focus && F(f.k) && !F(f.k).readOnly);
  (focusField ? F(focusField.k) : $$("#dlg-fields input:not([readonly]):not([type=hidden]), #dlg-fields select").find(el => !el.readOnly && !el.closest("label")?.hidden))?.focus();
  dlg.dataset.initial = formSnapshot();
}
function formSnapshot() { return JSON.stringify($$("#dlg-fields input, #dlg-fields select").map(el => el.type === "checkbox" ? el.checked : el.value)); }
function formDirty() { return $("#dlg").dataset.initial !== undefined && $("#dlg").dataset.initial !== formSnapshot(); }

// B3: Enter 는 다음 칸, Ctrl+Enter 는 저장
$("#dlg-fields").addEventListener("keydown", e => {
  if (e.key !== "Enter") return;
  const el = e.target;
  if (el.tagName === "TEXTAREA" || el.type === "checkbox") return;
  e.preventDefault();
  if (e.ctrlKey || e.metaKey) { if (e.shiftKey) $("#dlg-save-more").click(); else $("#dlg-form").requestSubmit(); return; }
  const list = $$("#dlg-fields input:not([readonly]):not([type=hidden]), #dlg-fields select").filter(x => !x.closest("label")?.hidden);
  const i = list.indexOf(el);
  const next = list[i + 1];
  if (next) { next.focus(); if (next.select) next.select(); } else $("#dlg-save").focus();
});
const confirmDiscard = () => confirmDlg({ title: "입력 취소", body: "입력한 내용은 저장되지 않습니다.", verb: "버리고 닫기", cancel: "계속 입력", danger: true });
$("#dlg").addEventListener("cancel", async e => {  // Esc: confirmDlg 가 비동기라 항상 막고, 확인되면 직접 닫는다
  if (!formDirty()) return;
  e.preventDefault();
  if (await confirmDiscard()) { DLG_ON_SAVED = null; $("#dlg").dataset.initial = ""; $("#dlg").close(); }
});

// 구분 값에 따라 종속 필드 표시 (적립금 폼)
function syncDepFields() {
  const sel = $("#f-구분"); if (!sel) return;
  const chk = $("#f-_record_exec");
  $$("#dlg-fields label[data-dep]").forEach(l => {
    if (!l.dataset.dep) return;
    const show = l.dataset.dep.split("|").includes(sel.value) && (!chk || l.classList.contains("chk") || chk.checked);
    l.hidden = !show;
  });
}
$("#dlg-fields").addEventListener("change", e => { if (e.target.dataset.lock !== undefined && e.target.value !== e.target.dataset.lock) { e.target.value = e.target.dataset.lock; showAlert("연결된 집행이라 이 값은 원본 화면에서만 바꿀 수 있습니다.", "warn"); } if (e.target.id === "f-구분" || e.target.id === "f-_record_exec") syncDepFields(); if (e.target.id === "f-구분" && typeof requestFormSync === "function") requestFormSync(); });

$("#dlg-form").addEventListener("submit", async e => {
  e.preventDefault();
  const dlg = $("#dlg");
  if (dlg.dataset.busy) return;  // Ctrl+Enter 연타 등 이중 제출 방지
  const kind = dlg.dataset.kind, row = dlg.dataset.row;
  const rec = {};
  const fields = formFields(kind).filter(f => !(f.onlyNew && row));
  const recordExec = !!$("#f-_record_exec")?.checked;
  const missing = [], invalid = []; let firstBad = null;
  fields.forEach(f => {
    const el = F(f.k);
    if (!el || f.type === "ro") return;
    if (f.type === "check") { rec[f.k] = el.checked; return; }
    if (el.closest("label")?.hidden) return;
    let v = el.value.trim();
    el.removeAttribute("aria-invalid");
    const mark = () => { el.setAttribute("aria-invalid", "true"); firstBad = firstBad || el; };
    if (f.type === "num") {
      const ev = evalAmount(v);
      if (ev === null) { invalid.push(`${f.label || f.k}(수식 계산 불가)`); mark(); }
      else if (ev !== undefined) { v = ev; el.value = ev.toLocaleString("ko-KR"); }
      else if (v !== "") { const n = numText(v); if (n == null) { invalid.push(`${f.label || f.k}(숫자 아님)`); mark(); } else { v = n; el.value = n.toLocaleString("ko-KR"); } }
    }
    if (f.req === "exec" && recordExec && v === "") { missing.push(f.label || f.k); mark(); }
    if (f.req === true && (v === "" || v == null)) { missing.push(f.label || f.k); mark(); }
    rec[f.k] = v;
  });
  if (missing.length || invalid.length) {
    showFormError((missing.length ? `입력 필요: ${missing.join(", ")}` : "") + (invalid.length ? ` / 확인 필요: ${invalid.join(", ")}` : ""));
    firstBad?.focus(); return;
  }
  if (kind === "deposit" && rec["구분"] === "사용" && rec["거래처"]) {
    const bal = DATA.deposit.filter(x => x["거래처"] === rec["거래처"] && x._row !== Number(row || 0)).reduce((a, x) => a + (x["구분"] === "적립" ? 1 : -1) * (x["금액"] || 0), 0);
    if (bal - rec["금액"] < 0 && !await confirmDlg({ title: "적립금 잔액 초과", body: `${rec["거래처"]} 적립금 잔액 ${fmt(bal)}원을 넘습니다 (저장 후 ${fmt(bal - rec["금액"])}원). 선결제가 더 있다면 먼저 적립을 입력하세요.`, verb: "그래도 저장" })) return;
  }
  // B8: 저장 전 경고 (차단 아님). 새 행·전환·수정 모두 잔액을 검사하되, 전환 중인 품의와 수정 중인 행 자신은 빼고 계산
  if (kind === "exec" || kind === "req") {
    const warns = [];
    const convertRowNo = dlg.dataset.convert ? Number(dlg.dataset.convert) : null;
    const cur = row ? DATA[kind].find(x => x._row === Number(row)) : null;
    if (!row) {
      if (rec["금액"] < 0) warns.push(`금액이 음수(${fmt(rec["금액"])}원)입니다. 반납·환입 기록이 맞나요?`);
      const dup = DATA[kind].find(x => x["원인발생일"] === rec["원인발생일"] && (x["거래처"] || "") === (rec["거래처"] || "") && x["금액"] === rec["금액"]);
      if (dup) warns.push(`같은 날·거래처·금액의 건이 이미 있습니다: ${dup["거래번호"] || dup["품의번호"]} (${dup["적요"] || "-"}). 중복 입력일 수 있습니다.`);
    }
    const opts = convertRowNo != null ? { excludeReq: convertRowNo } : cur ? (kind === "exec" ? { excludeExec: cur._row } : { excludeReq: cur._row }) : {};
    const counts = kind === "exec" || rec["상태"] === "대기";  // 취소·집행완료 품의는 잔액에 영향 없음
    const av = availableBudget(rec["재원"], rec["예산목"], opts);
    const changed = !cur || cur["재원"] !== rec["재원"] || cur["예산목"] !== rec["예산목"] || (rec["금액"] || 0) > (cur["금액"] || 0) || cur["상태"] !== rec["상태"];
    if (counts && changed && av != null && av - rec["금액"] < 0) warns.push(`${rec["재원"]} ${rec["예산목"]} 가용잔액 ${fmt(av)}원을 넘습니다 (저장 후 ${fmt(av - rec["금액"])}원).`);
    if (warns.length && !await confirmDlg({ title: "저장 전 확인", body: warns.join("\n\n"), verb: "그래도 저장" })) return;
  }
  if (kind === "exec" && row) { const cur = DATA.exec.find(x => x._row === Number(row)); if (cur) ["상태", "증빙폴더", "증빙목록"].forEach(k => { rec[k] = cur[k]; }); }
  if (kind === "request" && typeof requestPrepare === "function") { const err = requestPrepare(rec, row ? Number(row) : null); if (err) { showFormError(err); return; } }
  let putExtra = null;  // 신청: 승인된 건을 고칠 때 담당자가 고른 처리 (승인 유지 → {keep_approval: true})
  if (kind === "request" && row && typeof requestConfirmSave === "function") { const r = await requestConfirmSave(rec, Number(row)); if (r === null) return; putExtra = r || null; }
  const more = dlg.dataset.saveMore === "1"; dlg.dataset.saveMore = "";
  const convertRow = dlg.dataset.convert ? Number(dlg.dataset.convert) : null;
  const convertReq = dlg.dataset.convertReq ? JSON.parse(dlg.dataset.convertReq) : null;
  let doneMsg = null;
  const saveBtn = $("#dlg-save"), moreBtn = $("#dlg-save-more");
  dlg.dataset.busy = "1";
  try {
    saveBtn.disabled = true; moreBtn.disabled = true; saveBtn.textContent = "저장 중…";
    let saved;
    if (convertReq) {  // 신청 여러 건 → 품의 1건 (서버가 품의 생성 + 신청 품의전환을 한 번에)
      const res = await api("POST", "/api/request/convert", { rows: convertReq, expects: convertReq.map(n => expectOf("request", DATA.request.find(x => x._row === n))), extra: { ...rec, ...(dlg.dataset.convertPay !== "" && Number(rec["금액"]) !== Number(dlg.dataset.convertPay) ? { amount_override: true } : {}) } });
      saved = { ...res.req }; doneMsg = `품의 ${res["품의번호"]} 를 만들고 신청 ${res.numbers.join(", ")} 을(를) 품의전환으로 바꿨습니다.`;
    } else if (convertRow != null) {
      const req = DATA.req.find(x => x._row === convertRow);
      saved = await api("POST", `/api/req/${convertRow}/to-exec`, { extra: rec, expect: expectOf("req", req) });
    } else {
      saved = row ? await api("PUT", `/api/${kind}/${row}`, { rec, expect: expectOf(kind, DATA[kind].find(x => x._row === Number(row))), ...(putExtra ? { extra: putExtra } : {}) }) : await api("POST", `/api/${kind}`, rec);
    }
    const cb = DLG_ON_SAVED; DLG_ON_SAVED = null;
    if (!row) rememberLast(kind, rec);
    const no = saved["거래번호"] || saved["품의번호"] || saved["신청번호"] || saved["적립번호"] || saved["재원코드"] || saved["태그명"] || saved["거래처명"] || "";
    dlg.dataset.initial = ""; dlg.close();
    if (doneMsg) showAlert(doneMsg, "ok", { undo: true });
    else if (kind === "request" && typeof requestSavedMsg === "function") requestSavedMsg(saved, !row);
    else if (saved["_vendor_registered"]) showAlert(`${no} 저장했습니다. 거래처 '${saved["거래처"]}' 를 코드 '${saved["_vendor_registered"]}' 로 자동 등록했습니다 — 거래처 탭에서 코드를 확인하세요.`, "warn", { action: { label: "거래처 탭", run: () => switchTab("vendor") } });
    else showAlert(`${no ? no + " " : ""}저장했습니다.` + (convertRow != null ? " (품의 → 집행 전환 완료)" : "") + (saved["_renamed"] ? ` 증빙 파일 ${saved["_renamed"]}개 이름을 바꿨습니다.` : "") + (saved["_rename_error"] ? ` (증빙 파일 이름 변경 실패: ${saved["_rename_error"]})` : ""), saved["_rename_error"] ? "warn" : "ok");
    await load();
    if (kind === "request" && typeof requestAfterSave === "function") requestAfterSave(saved);
    if (cb) cb(saved);
    if (more) { const carry = {}; ["원인발생일", "일자", "귀속월", "지급월", "이름"].forEach(k => { if (rec[k]) carry[k] = rec[k]; }); openForm(kind, null, { ...carry, 거래처: "", 금액: "", 적요: "", 세목: "", 세세목: "", 관리번호: "", 비고: "", 증빙번호: "", 결의일: "", 지출완료일: "", 지급청구일: "" }); }
  } catch (err) {
    showFormError(err.message);
    if (kind === "request") { if (typeof requestSaveFailed === "function") requestSaveFailed(err); }  // 신청 폼: 오류는 폼 안에만 (토스트 중복 없음)
    else showAlert("저장 실패: " + err.message, "error");
  } finally { delete dlg.dataset.busy; saveBtn.disabled = false; moreBtn.disabled = false; saveBtn.textContent = "저장"; }
});
$("#dlg-save-more").addEventListener("click", () => { $("#dlg").dataset.saveMore = "1"; $("#dlg-form").requestSubmit(); });

// 가용잔액 = 예산현액 − 집행(파일 전체) − 대기 품의(날짜 무관). 대시보드·집행내역 열·저장 경고가 모두 이 함수를 쓴다 (2026-10-13 결정).
// excludeReq / excludeExec: 품의→집행 전환 중인 품의, 수정 중인 집행 행은 빼고 계산 (이중 차감 방지)
// 거래별 누적 잔액: 같은 재원·예산목의 예산변동(신청일자)과 집행(원인발생일)을 날짜 순으로 섞어 쌓아 "이 거래까지 반영한 뒤" 남는 예산.
// 같은 날이면 예산변동 먼저(그날 거래부터 변경액 반영), 집행끼리는 행 순. 그 날짜까지 신청된 예산이 없으면 null (사용자 결정 2026-10-19)
let RUN_BAL = null;
// 재원·예산목의 예산변동 중 날짜 d 까지 신청된 금액 합 (공금은 입금). 신청일자가 빈 행은 서버가 1월 1일로 채우지만, 혹시 비어 있으면 처음부터 포함
function budgetUpTo(fund, item, d) {
  const col = isPoolFund(fund) ? "입금" : item;
  return DATA.budget.filter(x => x["재원"] === fund && (x["신청일자"] || "") <= (d || "")).reduce((a, x) => a + (x[col] || 0), 0);
}
function runningBalance(r) {
  if (!RUN_BAL) {
    RUN_BAL = new Map();
    const groups = {};
    DATA.exec.forEach(x => { const k = x["재원"] + "" + (isPoolFund(x["재원"]) ? "" : x["예산목"]); (groups[k] = groups[k] || []).push(x); });  // 공금은 재원 단위로 누적
    Object.values(groups).forEach(list => {
      const f = list[0]["재원"], i = list[0]["예산목"];
      list.sort((a, c) => (a["원인발생일"] || "").localeCompare(c["원인발생일"] || "") || a._row - c._row);
      let acc = 0;
      list.forEach(x => { if (isCancelled(x)) { RUN_BAL.set(x._row, null); return; } acc += x["금액"] || 0; const b = isUntrackedFund(f) ? 0 : budgetUpTo(f, i, x["원인발생일"]); RUN_BAL.set(x._row, b ? b - acc : null); });
    });
  }
  return RUN_BAL.get(r._row) ?? null;
}
function availableBudget(fund, item, opts = {}) {
  if (!fund || !item || isUntrackedFund(fund)) return null;  // 잔액 미관리 재원: 예산 없음·경고 없음
  if (isPoolFund(fund)) {  // 공금: 예산목과 무관한 재원 잔액
    const b = poolDeposit(fund);
    if (!b) return null;
    const s = activeExec().filter(r => r["재원"] === fund && r._row !== opts.excludeExec).reduce((a, r) => a + (r["금액"] || 0), 0);
    const p = DATA.req.filter(r => r["재원"] === fund && r["상태"] === "대기" && r._row !== opts.excludeReq).reduce((a, r) => a + (r["금액"] || 0), 0);
    return b - s - p;
  }
  const b = DATA.budget.filter(r => r["재원"] === fund).reduce((a, r) => a + (r[item] || 0), 0);
  if (!b) return null;  // 예산 미입력(재원 또는 예산목)은 '-' 로 표시하고 경고 생략 (대시보드 '예산 미입력'과 동일 기준)
  const s = activeExec().filter(r => r["재원"] === fund && r["예산목"] === item && r._row !== opts.excludeExec).reduce((a, r) => a + (r["금액"] || 0), 0);
  const p = DATA.req.filter(r => r["재원"] === fund && r["예산목"] === item && r["상태"] === "대기" && r._row !== opts.excludeReq).reduce((a, r) => a + (r["금액"] || 0), 0);
  return b - s - p;
}
let DLG_ON_SAVED = null;
$("#dlg-cancel").addEventListener("click", async () => { if (formDirty() && !await confirmDiscard()) return; DLG_ON_SAVED = null; $("#dlg").dataset.initial = ""; $("#dlg").close(); });
$("#dlg").addEventListener("close", () => { DLG_ON_SAVED = null; });
function showFormError(msg) { const p = $("#dlg-error"); p.textContent = msg; p.hidden = false; p.classList.remove("info"); p.setAttribute("role", "alert"); }

// 금액 칸의 '=' 수식: "=12000*3+500" 처럼 사칙연산·괄호만 허용해 계산하고, 저장은 숫자로. 계산 불가면 null
function evalAmount(str) {
  const t = String(str ?? "").trim();
  if (!t.startsWith("=")) return undefined;  // 수식 아님
  const body = t.slice(1).replace(/[,\s원]/g, "");
  if (!body || !/^[\d.+\-*/()]+$/.test(body) || /[+\-*/.]{2,}/.test(body.replace(/\*\*/g, "x"))) return null;
  try { const n = Function(`"use strict"; return (${body});`)(); return Number.isFinite(n) ? Math.round(n) : null; } catch { return null; }
}
// 금액 입력 자동 쉼표 (입력 중 캐럿 이동을 막기 위해 포커스를 벗어날 때만). '=' 로 시작하면 수식을 계산해 숫자로 바꿈
// 숫자 칸 글자 → 수: 쉼표·공백·'원' 허용, '350만'·'1.2억' 처럼 만/억 한 단위. 그 밖의 글자가 있으면 null (값을 몰래 고치지 않음)
const NUM_PLAIN = /^-?[\d,\s]*\.?\d*원?$/;
function numText(str) {
  const t = String(str ?? "").trim();
  if (!/\d/.test(t)) return null;
  const m = /^(-?[\d,]*\.?\d*)\s*(만|억)\s*원?$/.exec(t);
  const n = m ? Number(m[1].replace(/,/g, "")) * (m[2] === "억" ? 1e8 : 1e4) : NUM_PLAIN.test(t) ? Number(t.replace(/[,\s원]/g, "")) : NaN;
  return Number.isFinite(n) && Math.abs(n) < 1e15 ? (m ? Math.round(n) : n) : null;
}
// 금액 입력 자동 쉼표 (입력 중 캐럿 이동을 막기 위해 포커스를 벗어날 때만). 순수 숫자·'=' 수식만 다시 쓰고, 그 밖은 표시만 하고 글자를 그대로 둔다
document.addEventListener("focusout", e => {
  const el = e.target;
  if (!el.classList?.contains("num-input")) return;
  if (el.dataset.hint === undefined) el.dataset.hint = el.title || "";
  const bad = msg => { el.setAttribute("aria-invalid", "true"); el.title = msg; };
  const v = el.value.trim(), ev = evalAmount(v);
  if (ev === null) return bad("수식을 계산할 수 없습니다. 숫자와 + - * / ( ) 만 쓸 수 있습니다.");
  if (ev === undefined && (v === "" || v === "-")) { el.removeAttribute("aria-invalid"); el.title = el.dataset.hint; return; }
  const n = ev !== undefined ? ev : numText(v);
  if (n == null) return bad("숫자 또는 =수식만 입력할 수 있습니다");
  el.removeAttribute("aria-invalid"); el.title = el.dataset.hint;
  const out = n.toLocaleString("ko-KR");
  if (el.value !== out) { el.value = out; el.dispatchEvent(new Event("input", { bubbles: true })); }  // 미리보기·합계 갱신
});

// ---------- 품의 -> 집행 전환 ----------
function toExec(row) {
  // 품의 값이 채워진 집행 입력 폼을 열고, 저장 시 서버가 전환(집행 생성 + 품의 집행완료)을 한 번에 처리. 취소하면 아무것도 바뀌지 않음.
  const r = DATA.req.find(x => x._row === row);
  if (!r) return Promise.resolve(null);
  return new Promise(resolve => {
    const preset = { 원인발생일: r["원인발생일"], 재원: r["재원"], 예산목: r["예산목"], 세목: r["세목"], 세세목: r["세세목"], 거래처: r["거래처"],
      적요: r["적요"], 금액: r["금액"], 태그: r["태그"], 결제수단: r["결제수단"], 사용자: r["품의자"], 비고: `품의 ${r["품의번호"]}` + (r["비고"] ? ` / ${r["비고"]}` : "") };
    DLG_ON_SAVED = saved => { resolve(saved); switchTab("exec"); QUICK = ""; FILTERS.exec = {}; $$("[data-filter][data-kind=exec]").forEach(el => { if (el.type === "checkbox") el.checked = false; else el.value = ""; }); renderExecTiles(); renderList("exec"); openExecDrawer(saved._row); };
    openForm("exec", null, preset, { convertRow: row, title: `집행 전환 - 품의 ${r["품의번호"]} (저장하면 품의는 '집행완료'로 바뀝니다)` });
    const onClose = () => { $("#dlg").removeEventListener("close", onClose); setTimeout(() => resolve(null), 0); };
    $("#dlg").addEventListener("close", onClose);
  });
}

// ---------- 지급청구일/지출완료일 당일 등록 ----------
async function setDateToday(row, col, btn) {
  const r = DATA.exec.find(x => x._row === row);
  if (!r) return;
  btn.disabled = true;
  try {
    const rec = { ...r }; delete rec._row; rec[col] = today();
    await api("PUT", `/api/exec/${row}`, { rec, expect: expectOf("exec", r) });
    showAlert(`${r["거래번호"]} ${col} ${today()} 등록`, "ok");
    await load();
  } catch (e) { showAlert(e.message, "error"); btn.disabled = false; }
}

// ---------- 삭제 ----------
const DEL_KIND = { exec: "집행", req: "품의", budget: "예산 변동", funds: "재원", deposit: "적립금", tags: "태그", vendor: "거래처", memo: "메모", ...(typeof LABOR_TITLES !== "undefined" ? LABOR_TITLES : {}) };
function IDENT_LABEL(kind, r) { return r?.["거래번호"] || r?.["품의번호"] || r?.["신청번호"] || r?.["재원코드"] || r?.["태그명"] || (typeof laborIdent === "function" ? laborIdent(kind, r) : ""); }
async function del(kind, row) {
  const r = DATA[kind].find(x => x._row === row);
  if (kind === "exec" && r) { const o = execOrigin(r); if (o?.locked) { showAlert(`${o.label} 에서 생긴 집행이라 여기서 지울 수 없습니다. ${o.kind === "인건비" ? "인건비 원장에서 '확정 취소' 또는 삭제" : "적립금 탭에서 해당 적립 행 삭제"}로 처리하세요.`, "warn"); return; } }
  if (kind === "deposit" && r && r["연결거래번호"]) {
    const ex = DATA.exec.find(x => x["거래번호"] === r["연결거래번호"]);
    const msg = `이 적립 건은 집행 ${r["연결거래번호"]}${ex ? ` (${ex["거래처"] || "-"}, ${fmt(ex["금액"])}원)` : ""} 과 연결되어 있습니다.\n\n[확인] = 적립 건과 연결 집행을 함께 삭제 (예산 차감도 취소)\n[취소] = 아무것도 삭제하지 않음\n\n적립 건만 지우려면 먼저 집행내역에서 해당 집행을 정리하세요.`;
    if (!await confirmDlg({ title: "적립 건과 연결 집행 삭제", body: msg.replace(/\n\n\[확인\][\s\S]*$/, "\n\n적립 건과 연결 집행을 함께 삭제합니다 (예산 차감도 취소). 적립 건만 지우려면 먼저 집행내역에서 해당 집행을 정리하세요."), verb: "둘 다 삭제", danger: true })) return;
    try { await api("DELETE", `/api/deposit/${row}`, { expect: expectOf("deposit", r), cascade: true }); showAlert(`적립 건과 집행 ${r["연결거래번호"]} 을 삭제했습니다.`, "ok", { undo: true }); await load(); }
    catch (e) { showAlert(e.message, "error"); }
    return;
  }
  const no = r?.["거래번호"] || r?.["품의번호"] || r?.["재원코드"] || r?.["태그명"];
  if (kind === "labor" && r?.["연결거래번호"]) { const ev = DATA.evidence.filter(e => e["거래번호"] === r["연결거래번호"]).length; if (ev) { showAlert(`집행 ${r["연결거래번호"]} 에 증빙 ${ev}개가 있어 삭제할 수 없습니다. 증빙을 먼저 지우세요.`, "warn"); return; } }
  const laborLbl = typeof laborLabel === "function" ? laborLabel(kind, r) : null;
  const label = laborLbl ? laborLbl + (kind === "labor" && r["연결거래번호"] ? `\n연결 집행 ${r["연결거래번호"]} 도 함께 삭제됩니다.` : "") : no ? [no, r["거래처"] || r["과제명"] || r["분류"], r["금액"] != null && kind !== "funds" && kind !== "tags" ? fmt(r["금액"]) + "원" : "", r["원인발생일"] ? mmdd(r["원인발생일"]) : "", (r["적요"] || r["설명"] || "").slice(0, 30)].filter(Boolean).join(" · ")
    : kind === "memo" ? `${r?.["종류"]}${r?.["대상"] ? " · " + r["대상"] : ""} · ${(r?.["내용"] || "").slice(0, 40)}` : (kind === "deposit" ? `${r?.["일자"]} ${r?.["거래처"]} ${r?.["구분"]} ${fmt(r?.["금액"])}원` : `${r?.["재원"]} ${r?.["변경회차"]}회차`);
  if (!await confirmDlg({ title: `${DEL_KIND[kind] || "항목"} 삭제`, body: `${label}\n\n삭제 직후 알림의 [되돌리기]로 복구할 수 있습니다. 그 뒤에는 app/backup 폴더의 백업 파일로만 복원됩니다.`, verb: "삭제", danger: true })) return;
  try { await api("DELETE", `/api/${kind}/${row}`, { expect: expectOf(kind, r) }); showAlert(`${no || label} 삭제했습니다.`, "ok", { undo: true }); await load(); }
  catch (e) { showAlert(e.message, "error"); }
}

// ---------- 공통 UI ----------
// 스타일 확인 대화상자. confirmDlg({title, body, verb, danger, cancel, alt, input:{label,type,value,required,error}})
// → 확인이면 true(입력 있으면 값), alt 버튼이면 "alt", 취소면 null. input.required 는 대화상자 안에서 검증(빈 값이면 열린 채 오류 표시)
function confirmDlg(o) {
  return new Promise(resolve => {
    const d = $("#dlg-confirm"), form = $("#dlg-confirm-form"), cancel = $("#confirm-cancel"), ok = $("#confirm-ok"), alt = $("#confirm-alt");
    const w = $("#confirm-input-wrap"), inp = $("#confirm-input"), err = $("#confirm-input-err");
    $("#confirm-title").textContent = o.title || "확인";
    $("#confirm-body").textContent = o.body || "";
    w.hidden = !o.input; err.hidden = true; err.textContent = ""; inp.removeAttribute("aria-invalid"); inp.required = false; inp.removeAttribute("aria-required");
    if (o.input) {
      $("#confirm-input-label").innerHTML = esc(o.input.label || "") + (o.input.required ? ' <span class="req" aria-hidden="true">*</span>' : "");
      inp.type = o.input.type || "text"; inp.value = o.input.value || "";
      if (o.input.required) { inp.required = true; inp.setAttribute("aria-required", "true"); }
    }
    ok.textContent = o.verb || "확인"; ok.className = "btn " + (o.danger ? "btn-danger-solid" : "btn-primary");
    cancel.textContent = o.cancel || "취소";
    alt.hidden = !o.alt; alt.textContent = o.alt || "";
    let done = false;
    const onSubmit = e => {
      e.preventDefault();
      if (o.input?.required && !String(inp.value).trim()) {  // 대화상자를 닫지 않고 그 자리에서 알림
        inp.setAttribute("aria-invalid", "true"); err.textContent = o.input.error || `${o.input.label || "값"}을(를) 입력하세요.`; err.hidden = false; inp.focus(); return;
      }
      finish(o.input ? inp.value : true);
    };
    const onCancel = () => finish(null);
    const onAlt = () => finish("alt");
    const onClose = () => finish(null);
    const onInput = () => { if (!err.hidden && String(inp.value).trim()) { err.hidden = true; inp.removeAttribute("aria-invalid"); } };
    function finish(v) {
      if (done) return; done = true;
      form.removeEventListener("submit", onSubmit); cancel.removeEventListener("click", onCancel); alt.removeEventListener("click", onAlt); d.removeEventListener("close", onClose); inp.removeEventListener("input", onInput);
      if (d.open) d.close();
      resolve(v);
    }
    form.addEventListener("submit", onSubmit); cancel.addEventListener("click", onCancel); alt.addEventListener("click", onAlt); inp.addEventListener("input", onInput);
    // 직전 대화상자의 close 이벤트가 뒤늦게 도착해 이번 대화상자를 닫지 않도록, 열고 난 다음 틱에 close 를 듣는다
    const open = () => { d.showModal(); (o.input ? inp : (o.danger ? cancel : ok)).focus(); setTimeout(() => { if (!done) d.addEventListener("close", onClose); }, 0); };
    if (d.open) { d.close(); setTimeout(open, 0); } else open();
  });
}
// 직전 저장 되돌리기 (서버가 저장 직전 백업을 복원; 그 뒤 다른 변경이 있으면 거부)
async function undoLast(t, wid) {
  try { await api("POST", "/api/undo", { write_id: wid || LAST_WRITE_ID }); if (t) t.remove(); showAlert("되돌렸습니다.", "ok"); await load(); if (typeof refreshCellDialog === "function") refreshCellDialog(); }
  catch (e) { showAlert("되돌리기 실패: " + e.message, "error"); }
}
// 토스트 메시지: ok 4초, warn 7초 후 자동 닫힘. error 는 닫기 버튼을 누를 때까지 유지(최대 5개).
function showAlert(msg, type = "ok", opts = {}) {
  let box = $("#toasts");
  if (!box) { box = document.createElement("div"); box.id = "toasts"; box.className = "toasts"; box.setAttribute("aria-live", "polite"); document.body.appendChild(box); }
  // 모달 대화상자(top layer) 위에도 보이도록 popover 로 띄움 (지원 브라우저만)
  try { if ("showPopover" in box) { if (!box.hasAttribute("popover")) box.setAttribute("popover", "manual"); if (box.matches(":popover-open")) box.hidePopover(); box.showPopover(); } } catch { }  // 다시 띄워 가장 위 층으로
  const dup = [...box.children].find(x => x.querySelector(".toast-msg")?.textContent === msg);
  if (dup) dup.remove();
  const t = document.createElement("div");
  t.className = "toast " + type; t.setAttribute("role", type === "error" ? "alert" : "status");
  t.innerHTML = `<span class="toast-msg"></span><button type="button" class="toast-x" aria-label="닫기"><svg viewBox="0 0 12 12" aria-hidden="true" focusable="false"><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg></button>`;
  t.querySelector(".toast-msg").textContent = msg;
  if (opts.undo) { const u = document.createElement("button"); u.type = "button"; u.className = "btn btn-sm toast-undo"; u.textContent = "되돌리기"; u.dataset.wid = LAST_WRITE_ID || ""; u.addEventListener("click", () => undoLast(t, u.dataset.wid)); t.insertBefore(u, t.querySelector(".toast-x")); }
  if (opts.action) { const a = document.createElement("button"); a.type = "button"; a.className = "btn btn-sm toast-undo toast-act"; a.textContent = opts.action.label; a.addEventListener("click", () => { t.remove(); opts.action.run(); }); t.insertBefore(a, t.querySelector(".toast-x")); }
  t.querySelector(".toast-x").addEventListener("click", () => t.remove());
  box.appendChild(t);
  while (box.children.length > 5) box.firstChild.remove();
  const ttl = opts.undo || opts.action ? 12000 : type === "ok" ? 4000 : type === "warn" ? 7000 : 0;
  if (ttl) setTimeout(() => t.remove(), ttl);
}
// 지속 배너 (수식 셀 경고처럼 사용자가 해결할 때까지 보여야 하는 것)
// 수식 셀 배너: 집행내역 탭에서만 전체 문구, 다른 곳은 헤더 상태 한 줄로만 (붉은색 상시 노출 방지)
function showBanner(msg) {
  const a = $("#alert");
  if (!msg) { a.hidden = true; return; }
  a.textContent = msg; a.className = "alert error formula"; a.hidden = false;
}

function closeExecDrawer() {
  const dr = $("#exec-drawer"), wasOpen = !dr.hidden, row = XD.row, kind = XD.kind;
  // 포커스가 드로어 안(또는 body)에 있을 때만 연 행으로 되돌림 — 탭 전환 등으로 닫힐 때는 건드리지 않음
  const ae = document.activeElement, restore = wasOpen && (!ae || ae === document.body || dr.contains(ae));
  dr.hidden = true; document.body.classList.remove("drawer-open");
  if (XD.row != null) { XD.row = null; if (DATA && kind === "exec") markExecRow(row, null); else if (DATA) $(`#deposit-table tbody tr[data-row="${row}"]`)?.classList.remove("selected"); }
  if (restore && row != null) ($(`#${kind}-table tbody tr[data-row="${row}"] .rowbtn`) || $(`#${kind}-table tbody tr[data-row="${row}"] button`))?.focus();
}
// Esc: 열린 대화상자가 있으면 그 대화상자가 먼저 처리 (드로어는 닫지 않음)
document.addEventListener("keydown", e => { if (e.key === "Escape" && !e.defaultPrevented && !$("#exec-drawer").hidden && !document.querySelector("dialog[open]")) closeExecDrawer(); });
function switchTab(name) {
  document.body.dataset.tab = name;
  if (name !== XD.kind) closeExecDrawer();
  $$("#main-tabs [role=tab]").forEach(b => {
    const on = b.id === "tab-" + name;
    b.setAttribute("aria-selected", on);
    $("#" + b.getAttribute("aria-controls")).hidden = !on;
  });
  try { localStorage.setItem("ledger-tab", name); } catch { }
}
$$("#main-tabs [role=tab]").forEach(b => b.addEventListener("click", () => switchTab(b.id.replace("tab-", ""))));
// 탭 목록: 선택된 탭만 Tab 순서에 두고(roving tabindex), 좌우 화살표·Home·End 로 이동하며 바로 선택
function rovingTabs(list) {
  const tabs = () => [...list.querySelectorAll("[role=tab]")];
  const sync = () => tabs().forEach(t => t.tabIndex = t.getAttribute("aria-selected") === "true" ? 0 : -1);
  sync();
  new MutationObserver(sync).observe(list, { subtree: true, attributes: true, attributeFilter: ["aria-selected"] });
  list.addEventListener("keydown", e => {
    const ts = tabs(), i = ts.indexOf(e.target.closest("[role=tab]")); if (i < 0) return;
    const j = { ArrowLeft: i - 1, ArrowRight: i + 1, Home: 0, End: ts.length - 1 }[e.key]; if (j == null) return;
    e.preventDefault(); const t = ts[(j + ts.length) % ts.length]; t.click(); t.focus();
  });
}
["#main-tabs", "#labor-tabs", ".subtabs"].forEach(sel => $$(sel).forEach(rovingTabs));

// 집행내역 삭제 모드: [삭제] → 체크 열 표시 → [선택 n건 삭제] 한 번에 (서버 일괄 저장, 되돌리기 가능)
let DELMODE = false; const DELSEL = new Set();
function setDelMode(on) {
  DELMODE = on; DELSEL.clear();
  $("#exec-del-bar").hidden = !on; $("#btn-del-mode").hidden = on; $("#btn-edit-mode").hidden = on; $("button[data-add=exec]").hidden = on;
  if (on) closeExecDrawer();
  renderList("exec"); updateDelBar();
  if (on) $("#exec-sel-all")?.focus(); else $("#btn-del-mode").focus();
}
function updateDelBar() { const n = DELSEL.size; $("#exec-del-run").disabled = !n; $("#exec-del-run").textContent = n ? `선택 ${n}건 삭제` : "선택 삭제"; const all = $("#exec-sel-all"); if (all) { const boxes = $$("#exec-table input[data-selrow]"); all.checked = boxes.length > 0 && boxes.every(b => b.checked); all.indeterminate = boxes.some(b => b.checked) && !all.checked; } }
document.addEventListener("change", e => {
  if (e.target.id === "exec-sel-all") { $$("#exec-table input[data-selrow]").forEach(b => { b.checked = e.target.checked; const r = Number(b.dataset.selrow); e.target.checked ? DELSEL.add(r) : DELSEL.delete(r); }); updateDelBar(); }
  else if (e.target.dataset.selrow !== undefined) { const r = Number(e.target.dataset.selrow); e.target.checked ? DELSEL.add(r) : DELSEL.delete(r); updateDelBar(); }
});
$("#btn-del-mode").addEventListener("click", () => setDelMode(true));
$("#exec-del-cancel").addEventListener("click", () => setDelMode(false));
$("#exec-del-run").addEventListener("click", async () => {
  const rows = [...DELSEL].map(r => DATA.exec.find(x => x._row === r)).filter(Boolean); if (!rows.length) return;
  const ev = rows.filter(r => evidCount(r) > 0);
  if (ev.length) { showAlert(`증빙이 등록된 ${ev.length}건(${ev.slice(0, 3).map(r => r["거래번호"]).join(", ")}${ev.length > 3 ? " …" : ""})은 증빙을 먼저 지워야 삭제할 수 있습니다.`, "warn"); return; }
  const sum = rows.reduce((a, r) => a + (r["금액"] || 0), 0);
  const body = rows.slice(0, 6).map(r => `${r["거래번호"]} · ${r["거래처"] || "-"} · ${fmt(r["금액"])}원`).join("\n") + (rows.length > 6 ? `\n… 외 ${rows.length - 6}건` : "") + `\n\n합계 ${fmt(sum)}원. 삭제 직후 알림의 [되돌리기]로 복구할 수 있습니다.`;
  if (!await confirmDlg({ title: `집행 ${rows.length}건 삭제`, body, verb: `${rows.length}건 삭제`, danger: true })) return;
  const btn = $("#exec-del-run"); btn.disabled = true;
  try { const res = await api("POST", "/api/exec/batch", { deletes: rows.map(r => ({ row: r._row, expect: expectOf("exec", r) })) }); setDelMode(false); showAlert(`${res.deleted}건 삭제했습니다.`, "ok", { undo: true }); await load(); }
  catch (e) { showAlert("삭제 실패: " + e.message, "error"); btn.disabled = false; }
});
let EXEC_CLICK_T = null;
$("#exec-table").addEventListener("keydown", e => {
  const btn = e.target.closest(".rowbtn"); if (!btn) return;
  const tr = btn.closest("tr[data-row]"); if (!tr) return;
  const row = Number(tr.dataset.row);
  if ((e.key === "Enter" && e.shiftKey) || e.key === "F2") { e.preventDefault(); clearTimeout(EXEC_CLICK_T); EXEC_CLICK_T = null; openForm("exec", row); }
  else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); clearTimeout(EXEC_CLICK_T); EXEC_CLICK_T = null; openExecDrawer(row); }
});
document.addEventListener("click", e => {
  const b = e.target.closest("button[data-act], button[data-add]");
  if (!b) {
    const trd = e.target.closest("#deposit-table tbody tr[data-row]");  // 적립금 행 한 번 클릭 = 상세·증빙 드로어 (작업 열 버튼은 제외)
    if (trd && !e.target.closest("a, input, select, button")) { openDepDrawer(Number(trd.dataset.row)); return; }
    const tr = e.target.closest("#exec-table tbody tr[data-row]");
    // 한 번 클릭 = 상세 패널(잠깐 기다렸다가 열어 두 번째 클릭이 밀린 버튼 위에 떨어지지 않게), 두 번 클릭 = 수정 창
    if (tr && DELMODE && !e.target.closest("input, button, a")) { const cb = tr.querySelector("input[data-selrow]"); if (cb) { cb.checked = !cb.checked; cb.dispatchEvent(new Event("change", { bubbles: true })); } return; }
    if (tr && !e.target.closest("a, input, select")) {
      const row = Number(tr.dataset.row);
      if (e.detail >= 2) { clearTimeout(EXEC_CLICK_T); EXEC_CLICK_T = null; window.getSelection()?.removeAllRanges(); openForm("exec", row); }
      else { clearTimeout(EXEC_CLICK_T); EXEC_CLICK_T = setTimeout(() => { EXEC_CLICK_T = null; openExecDrawer(row); }, 220); }
    }
    return;
  }
  if (b.dataset.act === "xact") return execAction(Number(b.dataset.row), b.dataset.action, b);
  if (b.dataset.act === "dact") return depAction(Number(b.dataset.row), b.dataset.action, b);
  if (b.dataset.act === "origin") return gotoOrigin(Number(b.dataset.row));
  if (b.dataset.act === "voucher") return openVoucher(Number(b.dataset.row), b);
  if (b.dataset.act === "show-excluded") { switchTab("exec"); QUICK = "excluded"; FILTERS.exec = {}; $$("[data-filter][data-kind=exec]").forEach(el => { if (el.type === "checkbox") el.checked = false; else el.value = ""; }); renderExecTiles(); renderList("exec"); showAlert("예산 집계에서 제외된 집행만 표시 중입니다. 빠른 필터 타일을 누르거나 새로고침하면 해제됩니다.", "ok"); return; }
  if (b.dataset.add) return openForm(b.dataset.add);
  if (b.dataset.act === "dep-exec") { const ex = DATA.exec.find(x => x["거래번호"] === b.dataset.no); switchTab("exec"); setSearch("exec", b.dataset.no); if (ex) openExecDrawer(ex._row); return; }
  if (b.dataset.act === "dep-use") return openForm("deposit", null, { 거래처: b.dataset.vendor, 구분: "사용" });
  if (b.dataset.act === "dep-add") return openForm("deposit", null, { 거래처: b.dataset.vendor, 구분: "적립" });
  const row = Number(b.dataset.row);
  if (b.dataset.act === "setdate") return setDateToday(row, b.dataset.col, b);
  if (b.dataset.act === "edit") openForm(b.dataset.kind, row);
  else if (b.dataset.act === "del") del(b.dataset.kind, row);
  else if (b.dataset.act === "toexec") toExec(row);
});

// 적요 칸 비고 메모: 좌상단 회색 삼각 마크, 마우스를 올리면 비고 내용을 툴팁으로 (엑셀 메모 차용)
(() => {
  let tip = null, cur = null;
  const show = (td, x, y) => {
    if (!tip) { tip = document.createElement("div"); tip.className = "memo-tip"; tip.setAttribute("role", "tooltip"); document.body.appendChild(tip); }
    tip.textContent = td.dataset.memo; tip.hidden = false;
    const r = td.getBoundingClientRect(); tip.style.left = Math.min(r.left + 8, window.innerWidth - tip.offsetWidth - 12) + "px";
    const top = r.bottom + 4; tip.style.top = (top + tip.offsetHeight > window.innerHeight ? r.top - tip.offsetHeight - 4 : top) + "px";
  };
  document.addEventListener("mouseover", e => { const td = e.target.closest("td.tit.memo"); if (!td || td === cur) return; cur = td; show(td); });
  document.addEventListener("mouseout", e => { if (cur && !cur.contains(e.relatedTarget)) { cur = null; if (tip) tip.hidden = true; } });
  document.addEventListener("scroll", () => { if (tip) tip.hidden = true; cur = null; }, true);
})();

// 행 더블클릭 → 수정 창 (표 안 버튼·입력·링크 제외, 확정된 인건비 건 제외)
document.addEventListener("dblclick", e => {
  if (e.target.closest("button, a, input, select, label")) return;
  const tr = e.target.closest("table.grid tbody tr[data-kind][data-row]"); if (!tr) return;
  const kind = tr.dataset.kind, row = Number(tr.dataset.row);
  if (kind === "exec" || kind === "request") return;  // 집행내역·신청은 click 핸들러에서 처리
  if (!COLS[kind]) return;
  if (kind === "labor") { const r = DATA.labor.find(x => x._row === row); if (r && r["상태"] === "확정") { showAlert("확정된 지급 건은 '확정 취소' 뒤에 수정할 수 있습니다.", "warn"); return; } }
  window.getSelection()?.removeAllRanges();
  openForm(kind, row);
});
const FILTER_T = {};  // 종류별 검색 디바운스 타이머
$$("[data-filter]").forEach(el => el.addEventListener("input", () => {
  const k = el.dataset.kind;
  FILTERS[k][el.dataset.filter] = el.type === "checkbox" ? el.checked : el.value;
  LIST_MORE[k] = false;
  clearTimeout(FILTER_T[k]);
  if (el.dataset.filter === "q") FILTER_T[k] = setTimeout(() => renderList(k), 150);  // 검색은 타자가 멈춘 뒤 한 번만
  else renderList(k);
}));
// 더 보기: 나머지 행을 그리고 처음 새로 보인 행으로 포커스
document.addEventListener("click", e => {
  const b = e.target.closest("button[data-more]"); if (!b) return;
  const kind = b.dataset.more; LIST_MORE[kind] = true; renderList(kind);
  $(`#${kind}-table`)?.querySelectorAll("tbody tr")[LIST_LIMIT]?.querySelector("button, input")?.focus();
});
$("#dash-fund").addEventListener("change", renderDashboard);
$("#dash-year").addEventListener("change", renderDashboard);
$("#btn-reload").addEventListener("click", load);
document.addEventListener("keydown", e => {
  if (e.key === "F5") { e.preventDefault(); load(); }
});
// 다른 창·MCP·엑셀이 장부를 바꿨으면 탭으로 돌아올 때 자동 새로고침 (입력 중인 대화상자가 없을 때만)
// 창으로 돌아올 때(focus)도 같은 검사. 업로드 등 진행 중([aria-busy=true])이면 건너뜀
let STALE_CHECK = false;
async function refreshIfStale() {
  if (document.visibilityState !== "visible" || !DATA || STALE_CHECK || document.querySelector("dialog[open], [aria-busy=true]")) return;
  STALE_CHECK = true;
  try { const m = await api("GET", "/api/meta"); if (m.mtime === DATA.meta.mtime && m.suppliers && typeof requestSettingsSaved === "function" && JSON.stringify([m.suppliers, m.supplier_note]) !== JSON.stringify([DATA.meta.suppliers, DATA.meta.supplier_note])) requestSettingsSaved({ suppliers: m.suppliers, supplier_note: m.supplier_note }); if (m.mtime !== DATA.meta.mtime) { await load(); showAlert("다른 곳에서 바뀐 장부를 다시 불러왔습니다.", "ok"); } } catch { }
  finally { STALE_CHECK = false; }
}
document.addEventListener("visibilitychange", refreshIfStale);
window.addEventListener("focus", refreshIfStale);

try { const t = localStorage.getItem("ledger-tab"); if (t && $("#tab-" + t)) switchTab(t); } catch { }
load();

// ================= AI 기능 =================
let AI = { enabled: false, model: "" };
const CHAT = [];
let CHAT_BUSY = false;

async function aiInit() {
  try {
    AI = await api("GET", "/api/ai/status");
  } catch { AI = { enabled: false }; }
  applyAIState();
  setOptions($("#rep-month"), ["", ...Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, "0"))], ["전체", ...Array.from({ length: 12 }, (_, i) => (i + 1) + "월")]);
}

function applyAIState() {
  const b = $("#btn-ai");
  b.hidden = false; b.disabled = !AI.enabled;
  b.title = AI.enabled ? `AI 도우미 (${AI.provider} · ${AI.model})` : "AI 도우미를 쓰려면 오른쪽 위 설정(톱니)에서 API 키를 입력하세요";
  $("#report-box").hidden = !AI.enabled;
  $("#ai-model").textContent = AI.enabled ? `${AI.provider} · ${AI.model}` : "";
}
$$(".chip-ex").forEach(c => c.addEventListener("click", () => { $("#ai-input").value = c.textContent; $("#ai-input").focus(); }));
let CHAT_TURN = 0;

// ---- 채팅 패널 ----
function toggleDrawer(open) {
  const d = $("#ai-drawer");
  d.hidden = open === undefined ? !d.hidden : !open;
  document.body.classList.toggle("ai-open", !d.hidden);
  if (!d.hidden && !$("#rep-out").dataset.raw) { $("#rep-fund").value = $("#dash-fund").value; $("#rep-year").value = $("#dash-year").value; $("#rep-month").value = $("#dash-month").value || ""; }
  $("#btn-ai").setAttribute("aria-expanded", String(!d.hidden));
  if (!d.hidden) $("#ai-input").focus();
}
function addMsg(role, text, cls = "") {
  const el = document.createElement("div");
  el.className = `msg ${role} ${cls}`.trim();
  el.textContent = text;
  $("#ai-log").appendChild(el);
  $("#ai-log").scrollTop = $("#ai-log").scrollHeight;
  return el;
}
$("#btn-ai").addEventListener("click", () => toggleDrawer());
$("#ai-close").addEventListener("click", () => toggleDrawer(false));
$("#ai-clear").addEventListener("click", () => { CHAT.length = 0; $$("#ai-log .msg").forEach(m => m.remove()); });
$("#ai-input").addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#ai-form").requestSubmit(); } });
$("#ai-form").addEventListener("submit", async e => {
  e.preventDefault();
  const q = $("#ai-input").value.trim();
  if (!q || CHAT_BUSY) return;
  CHAT_BUSY = true;
  $("#ai-input").value = "";
  addMsg("user", q);
  const qIdx = CHAT.push({ role: "user", content: q }) - 1;
  const pending = addMsg("assistant", "답변 생성 중… (장부 전체를 전송하므로 수십 초 걸릴 수 있음)", "pending");
  $("#ai-send").disabled = true; $("#ai-input").disabled = true;
  CHAT_TURN++;
  try {
    const r = await api("POST", "/api/ai/chat", { messages: CHAT.slice(-24), turn: CHAT_TURN });
    pending.textContent = r.answer || "(제안만 생성)"; pending.classList.remove("pending");
    CHAT.push({ role: "assistant", content: r.answer || "(제안 생성)" });
    (r.proposals || []).forEach(renderProposal);
    if (r.usage) { const u = document.createElement("div"); u.className = "toolbar-note"; u.style.alignSelf = "flex-start"; u.textContent = `이번 질문 입력 약 ${(r.usage.input || 0).toLocaleString()} 토큰${r.usage.cached ? ` (캐시 ${(r.usage.cached).toLocaleString()})` : ""}`; $("#ai-log").appendChild(u); }
  } catch (err) {
    pending.textContent = "답변을 받지 못했습니다: " + err.message; pending.className = "msg error";
    const rb = document.createElement("button"); rb.type = "button"; rb.className = "btn btn-sm retry"; rb.textContent = "다시 보내기";
    rb.addEventListener("click", () => { $("#ai-input").value = q; pending.remove(); $("#ai-form").requestSubmit(); });
    pending.appendChild(rb);
    CHAT.splice(qIdx, 1);
    $("#ai-input").value = q;
  } finally { CHAT_BUSY = false; $("#ai-send").disabled = false; $("#ai-input").disabled = false; $("#ai-input").focus(); }
});

// ---- 거래 제안 카드 (사용자 확인·수정 후 저장) ----
const PROPOSAL_LABEL = { propose_exec: "집행 추가", propose_req: "품의 추가", propose_deposit: "적립금 기록", propose_update: "행 수정", propose_req_to_exec: "품의→집행 전환" };
function renderProposal(p) {
  const card = document.createElement("div");
  card.className = "msg assistant proposal";
  const inp = p.input || {};
  const KIND_KO = { exec: "집행", req: "품의", deposit: "적립금", budget: "예산변동", funds: "재원" };
  const rowDesc = (kind, row) => { const r = DATA[kind]?.find(x => x._row === row); if (!r) return `(${KIND_KO[kind] || kind} 행 ${row} — 현재 목록에 없음, 새로고침 필요)`; return [r["거래번호"] || r["품의번호"] || r["재원코드"] || `${r["일자"] || ""} ${r["거래처"] || ""}`, r["거래처"], r["금액"] != null ? fmt(r["금액"]) + "원" : "", (r["적요"] || "").slice(0, 20)].filter(Boolean).join(" · "); };
  let detail;
  if (p.tool === "propose_update") {
    const r = DATA[inp.kind]?.find(x => x._row === inp.row);
    detail = `${KIND_KO[inp.kind] || inp.kind}: ${rowDesc(inp.kind, inp.row)}\n` + Object.entries(inp.fields || {}).map(([k, v]) => `${k}: ${r && r[k] !== undefined && r[k] !== "" ? `${r[k]} → ` : ""}${v}`).join("\n") + (inp.reason ? `\n이유: ${inp.reason}` : "");
  }
  else if (p.tool === "propose_req_to_exec") detail = `품의 ${rowDesc("req", inp.row)} 를 집행으로 전환` + (inp.reason ? `\n이유: ${inp.reason}` : "");
  else detail = Object.entries(inp).filter(([, v]) => v !== "" && v != null).map(([k, v]) => `${k}: ${k === "금액" ? fmt(v) + "원" : v}`).join("\n");
  card.innerHTML = `<div class="proposal-head">제안 ${esc(p.id)} · ${esc(PROPOSAL_LABEL[p.tool] || p.tool)}</div><div class="proposal-body">${esc(detail)}</div>
    <div class="proposal-actions"><button type="button" class="btn btn-sm btn-primary" data-pact="review" title="입력 폼이 열립니다. 저장 전에는 장부가 바뀌지 않습니다">검토 후 저장</button><button type="button" class="btn btn-sm" data-pact="skip">무시</button></div>`;
  $("#ai-log").appendChild(card); $("#ai-log").scrollTop = $("#ai-log").scrollHeight;
  const done = (text) => { card.querySelector(".proposal-actions").innerHTML = `<span class="proposal-done">${esc(text)}</span>`; };
  card.querySelector("[data-pact=skip]").addEventListener("click", () => { done("무시함"); CHAT.push({ role: "user", content: `[알림] 제안 ${p.id} 는 사용자가 무시했습니다.` }); });
  card.querySelector("[data-pact=review]").addEventListener("click", async () => {
    try {
      if (p.tool === "propose_req_to_exec") {
        const r = DATA.req.find(x => x._row === inp.row);
        if (!r) throw new Error("해당 품의 행을 찾을 수 없습니다. 새로고침 후 다시 시도하세요.");
        const rec = await toExec(inp.row);  // 전환 폼에서 저장해야 반영
        if (!rec) return;  // 취소: 카드 유지
        done(`처리됨 (${rec["거래번호"]})`); CHAT.push({ role: "user", content: `[알림] 제안 ${p.id} 를 사용자가 확인하여 품의 ${r["품의번호"]} 를 집행 ${rec["거래번호"]} 로 전환했습니다.` });
        return;
      }
      let kind, row = null, preset = {};
      if (p.tool === "propose_update") {
        kind = inp.kind; row = inp.row;
        if (!DATA[kind]?.find(x => x._row === row)) throw new Error("해당 행을 찾을 수 없습니다. 새로고침 후 다시 시도하세요.");
      } else {
        kind = { propose_exec: "exec", propose_req: "req", propose_deposit: "deposit" }[p.tool];
        preset = { ...inp };
      }
      DLG_ON_SAVED = (saved) => {
        const no = saved["거래번호"] || saved["품의번호"] || `행 ${saved._row}`;
        done(`저장됨 (${no})`);
        CHAT.push({ role: "user", content: `[알림] 제안 ${p.id} 를 사용자가 검토·수정 후 저장했습니다: ${no}` });
      };
      openForm(kind, row, preset);
      if (p.tool === "propose_update") {
        const failed = [];
        Object.entries(inp.fields || {}).forEach(([k, v]) => {
          const el = F(k);
          if (!el || el.readOnly) { failed.push(k); return; }
          if (el.classList.contains("num-input")) { const n = Number(String(v).replace(/[^\d.-]/g, "")); if (isNaN(n)) failed.push(k); else el.value = n.toLocaleString("ko-KR"); return; }
          el.value = v;
          if (el.value !== String(v)) { failed.push(`${k}(${v})`); }
        });
        if (failed.length) showFormError("제안 값 중 폼에 반영하지 못한 항목: " + failed.join(", ") + " — 직접 입력해 주세요.");
      }
      if (!row) {
        Object.entries(preset).forEach(([k, v]) => setField(k, v));  // 금액 쉼표 등 보정
        const failed = Object.entries(preset).filter(([k, v]) => v !== "" && v != null).filter(([k, v]) => { const el = F(k); if (!el) return k !== "_row"; const got = el.classList.contains("num-input") ? Number(String(el.value).replace(/[^\d.-]/g, "")) : el.value; return String(got) !== String(v) && !(typeof v === "number" && got === v); }).map(([k, v]) => `${k}(${v})`);
        if (failed.length) showFormError("제안 값 중 폼에 반영하지 못한 항목: " + failed.join(", ") + " — 목록에 없는 값이거나 형식이 다릅니다. 직접 선택해 주세요.");
      }
      $("#dlg").dataset.initial = formSnapshot();
    } catch (err) { showAlert(err.message, "error"); }
  });
}

// ---- 입력 폼: 영수증 추출 / 추천·검증 ----
function setField(k, v) { const el = F(k); if (!el || v == null || v === "") return; el.value = (el.classList.contains("num-input")) ? Number(v).toLocaleString("ko-KR") : v; }
function aiMsg(text, warn) { const m = $("#dlg-ai-msg"); m.textContent = text; m.classList.toggle("warn", !!warn); }

$("#dlg-receipt-btn").addEventListener("click", () => $("#dlg-receipt").click());
$("#dlg-receipt").addEventListener("change", async e => {
  const f = e.target.files[0]; if (!f) return;
  e.target.value = "";
  aiMsg("증빙 판독 중…");
  try {
    const fd = new FormData(); fd.append("file", f);
    const res = await fetch("/api/ai/extract", { method: "POST", body: fd });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const d = await res.json();
    const filled = [], kept = [];
    ["원인발생일", "거래처", "금액", "적요", "세목", "예산목"].forEach(k => {
      const el = F(k); if (!el || d[k] === "" || d[k] == null) return;
      const cur = el.value.trim(); const isDefault = (k === "원인발생일" && cur === today());
      if (cur && !isDefault) { kept.push(k); return; }
      setField(k, d[k]);
      if (String(el.value).replace(/,/g, "") === String(d[k]).replace(/,/g, "") || k === "금액") { el.classList.add("ai-filled"); filled.push(k); }
    });
    if (d["증빙번호"] && F("비고") && !F("비고").value) { setField("비고", `승인번호 ${d["증빙번호"]}`); F("비고").classList.add("ai-filled"); filled.push("비고(승인번호)"); }
    const conf = { high: "높음", medium: "보통", low: "낮음" }[d["신뢰도"]] || d["신뢰도"];
    aiMsg(`추출 완료 · 신뢰도 ${conf} · 채운 항목: ${filled.join(", ") || "없음"}${kept.length ? ` · 이미 입력된 ${kept.join(", ")}은 유지` : ""}. 금액은 부가세 포함 합계입니다. 재원·태그·사용자는 직접 선택하세요.${d["메모"] ? " 메모: " + d["메모"] : ""}`, d["신뢰도"] !== "high");
  } catch (err) { aiMsg("추출 실패: " + err.message, true); }
});

$("#dlg-suggest").addEventListener("click", async () => {
  const kind = $("#dlg").dataset.kind;
  const rec = {};
  $$("#dlg-fields input, #dlg-fields select").forEach(el => { if (el.name && !el.name.startsWith("_")) rec[el.name] = el.value; });
  if (rec["금액"]) rec["금액"] = rec["금액"].replace(/[,\s원]/g, "");
  aiMsg("추천 생성 중…");
  $("#dlg-suggest").disabled = true;
  try {
    const d = await api("POST", "/api/ai/suggest", { rec, kind });
    if (d["예산목"] && $("#f-예산목")) $("#f-예산목").value = d["예산목"];
    ["세목", "태그"].forEach(k => { if (d[k] && F(k) && !F(k).value) setField(k, d[k]); });
    const warn = (d["경고"] || []).length ? " 경고: " + d["경고"].join(" / ") : "";
    aiMsg(`추천: ${d["예산목"]} · ${d["세목"] || "-"}${d["태그"] ? " · " + d["태그"] : ""} (${d["근거"]})${warn}`, !!warn);
  } catch (err) { aiMsg("추천 실패: " + err.message, true); }
  finally { $("#dlg-suggest").disabled = false; }
});

// 폼이 열릴 때 AI 바 표시 여부 (집행·품의만)
const _openForm = openForm;
openForm = function (kind, row, preset, opts) {
  _openForm(kind, row, preset, opts);
  const show = AI.enabled && (kind === "exec" || kind === "req");
  $("#dlg-ai").hidden = !show;
  aiMsg("");
};

// ---- 보고서 초안 ----
// 아주 작은 마크다운 → HTML (제목·굵게·목록·표·단락). 입력은 esc 처리 후 변환.
function mdToHtml(md) {
  const lines = esc(md || "").split("\n"); let html = "", i = 0;
  const inline = s => s.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`(.+?)`/g, "<code>$1</code>");
  while (i < lines.length) {
    const l = lines[i];
    if (/^\|/.test(l) && /^\|/.test(lines[i + 1] || "") && /^\|[\s:|-]+\|$/.test(lines[i + 1])) {
      const cells = r => r.replace(/^\||\|$/g, "").split("|").map(c => inline(c.trim()));
      let t = `<table><thead><tr>${cells(l).map(c => `<th>${c}</th>`).join("")}</tr></thead><tbody>`; i += 2;
      while (i < lines.length && /^\|/.test(lines[i])) { t += `<tr>${cells(lines[i]).map(c => `<td>${c}</td>`).join("")}</tr>`; i++; }
      html += t + "</tbody></table>"; continue;
    }
    const h = l.match(/^(#{1,6})\s+(.*)/); if (h) { html += `<h${Math.min(3, h[1].length)}>${inline(h[2])}</h${Math.min(3, h[1].length)}>`; i++; continue; }
    if (/^\s*[-*]\s+/.test(l)) { let u = "<ul>"; while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) { u += `<li>${inline(lines[i].replace(/^\s*[-*]\s+/, ""))}</li>`; i++; } html += u + "</ul>"; continue; }
    if (/^\s*\d+[.)]\s+/.test(l)) { let o = "<ol>"; while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) { o += `<li>${inline(lines[i].replace(/^\s*\d+[.)]\s+/, ""))}</li>`; i++; } html += o + "</ol>"; continue; }
    if (l.trim() === "") { i++; continue; }
    html += `<p>${inline(l)}</p>`; i++;
  }
  return html;
}
$("#rep-run").addEventListener("click", async () => {
  const out = $("#rep-out");
  out.hidden = false; out.textContent = "보고서 생성 중… (수십 초 소요)";
  $("#rep-run").disabled = true; $("#rep-copy").hidden = true;
  try {
    const r = await api("POST", "/api/ai/report", { fund: $("#rep-fund").value, year: $("#rep-year").value, month: $("#rep-month").value, style: $("#rep-style").value });
    out.innerHTML = mdToHtml(r.report); out.dataset.raw = r.report; $("#rep-copy").hidden = false; $("#rep-caveat").hidden = false;
  } catch (err) { out.textContent = "보고서를 만들지 못했습니다: " + err.message + ". 잠시 후 다시 생성하세요."; }
  finally { $("#rep-run").disabled = false; }
});
$("#rep-copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("#rep-out").dataset.raw || $("#rep-out").textContent); showAlert("보고서(마크다운)를 복사했습니다.", "ok"); }
  catch { showAlert("복사 실패. 텍스트를 직접 선택해 복사하세요.", "error"); }
});

aiInit();

// ================= 설정 (관리 패널) =================
const SET_FIELDS = ["REQUEST_SUPPLIERS", "REQUEST_SUPPLIERS_OFF", "REQUEST_SUPPLIER_NOTE", "REQUEST_BUYER", "REQUEST_SHIP_TO", "REQUEST_CONTACT", "LEDGER_ORG", "LEDGER_PROVIDER", "ANTHROPIC_API_KEY", "LEDGER_MODEL", "LEDGER_EFFORT", "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "OPENAI_REASONING_EFFORT"];
function setMsg(text, warn) { const m = $("#settings-msg"); m.textContent = text; m.classList.toggle("warn", !!warn); }
function syncProviderGroups() {
  const p = $("#s-provider").value;
  $$(".s-group[data-provider]").forEach(g => g.hidden = g.dataset.provider !== p);
}
async function openSettings() {
  try {
    const { values } = await api("GET", "/api/settings");
    $("#settings-form").reset();
    SET_FIELDS.forEach(k => {
      const el = $(`[name=${k}]`); if (!el) return;
      const v = values[k];
      if (v && typeof v === "object") { el.value = ""; const h = $(`#${el.id}-hint`); if (h) h.textContent = v.set ? `(설정됨 ${v.hint})` : "(미설정)"; }
      else el.value = v ?? "";
    });
    syncProviderGroups(); setMsg("");
    if (typeof requestSettingsOpen === "function") requestSettingsOpen();
    refreshDriveStatus();
    memoRender();
    $("#dlg-settings").showModal();
  } catch (e) { showAlert("설정을 불러오지 못했습니다: " + e.message, "error"); }
}
function collectSettings() {
  const out = {};
  SET_FIELDS.forEach(k => { const el = $(`[name=${k}]`); if (el) out[k] = el.value.trim(); });
  return out;
}
async function saveSettings() {
  const r = await api("PUT", "/api/settings", collectSettings());
  AI = { enabled: r.status.enabled, model: r.status.model, provider: r.status.provider };
  applyAIState();
  if (r.request && typeof requestSettingsSaved === "function") requestSettingsSaved(r.request, r.values);
  // 비밀 입력칸은 비우고 힌트 갱신
  ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"].forEach(k => { const el = $(`[name=${k}]`); el.value = ""; const h = $(`#${el.id}-hint`); const v = r.values[k]; if (h) h.textContent = v.set ? `(설정됨 ${v.hint})` : "(미설정)"; });
  return r;
}
$("#btn-settings").addEventListener("click", openSettings);
$("#s-provider").addEventListener("change", syncProviderGroups);
$("#s-cancel").addEventListener("click", () => $("#dlg-settings").close());
$("#settings-form").addEventListener("submit", async e => {
  e.preventDefault();
  try { await saveSettings(); showAlert("설정을 저장했습니다.", "ok"); $("#dlg-settings").close(); }
  catch (err) { setMsg("저장 실패: " + err.message, true); }
});
$("#s-test").addEventListener("click", async () => {
  $("#s-test").disabled = true; setMsg("입력한 값으로 연결 확인 중… (짧은 호출 1회, 소액 과금)");
  try { const r = await api("POST", "/api/settings/test", collectSettings()); await saveSettings(); setMsg("연결 성공 · 저장됨: " + r.message); }
  catch (err) { setMsg("연결 실패 (저장하지 않음): " + err.message, true); }
  finally { $("#s-test").disabled = false; }
});
$("#s-clear-key").addEventListener("click", async () => {
  const p = $("#s-provider").value;
  const key = p === "openai" ? "OPENAI_API_KEY" : "ANTHROPIC_API_KEY";
  if (!await confirmDlg({ title: "API 키 삭제", body: `${p === "openai" ? "OpenAI" : "Anthropic"} API 키를 설정 파일(.env)에서 삭제합니다.`, verb: "삭제", danger: true })) return;
  try { $(`[name=${key}]`).value = "__clear__"; await saveSettings(); setMsg("키를 삭제했습니다."); }
  catch (err) { setMsg("삭제 실패: " + err.message, true); }
});


// ---------- 메모 (설정 패널 · AI 도우미가 read_memo 로 읽는 장부 밖 지식) ----------
function memoRender() {
  const box = $("#memo-list"); if (!box) return;
  $("#dl-대상").innerHTML = [...new Set([...DATA.funds.map(f => f["재원코드"]), ...DATA.vendor.map(v => v["거래처명"]), ...DATA.exec.map(r => r["거래처"])].filter(Boolean))].sort().map(v => `<option value="${esc(v)}">`).join("");
  const rows = [...(DATA.memo || [])].sort((a, b) => (a["종류"] || "").localeCompare(b["종류"] || "") || (a["대상"] || "").localeCompare(b["대상"] || "") || a._row - b._row);
  box.innerHTML = rows.length ? `<table><thead><tr><th>종류</th><th>대상</th><th>내용</th><th>작성일</th><th class="actions">작업</th></tr></thead><tbody>${rows.map(r => `<tr><td>${esc(r["종류"])}</td><td>${esc(r["대상"] || "-")}</td><td class="wrap">${esc(r["내용"])}${r["비고"] ? `<div class="muted">${esc(r["비고"])}</div>` : ""}</td><td>${esc(r["작성일"] || "")}</td><td class="actions"><button type="button" class="btn btn-sm" data-memo-edit="${r._row}">수정</button> <button type="button" class="btn btn-sm btn-ghost" data-memo-del="${r._row}">삭제</button></td></tr>`).join("")}</tbody></table>`
    : '<p class="empty">메모가 없습니다. [메모 추가]로 재원·거래처 특이사항이나 규정을 적어 두세요.</p>';
}
$("#memo-add")?.addEventListener("click", () => openForm("memo", null, { 종류: "일반", 작성일: today() }));
$("#memo-list")?.addEventListener("click", e => {
  const ed = e.target.closest("[data-memo-edit]"), dl = e.target.closest("[data-memo-del]");
  if (ed) openForm("memo", Number(ed.dataset.memoEdit));
  else if (dl) del("memo", Number(dl.dataset.memoDel));
});

// ================= 집행 상세 드로어 · 증빙 · 단계 처리 =================
let QUICK = "";
const XD = { kind: "exec", row: null, evid: null, drive: null, seq: 0 };  // kind: 드로어가 보여 주는 행의 종류 (exec | deposit)
function evidCountNo(no) { return no ? (DATA.evidence || []).filter(e => e["거래번호"] === no).length : 0; }
function evidCount(r) { return evidCountNo(r["거래번호"]); }
// 집행 행의 출처: 인건비 확정 / 적립금 적립 기록 / 품의 전환. 연결 행은 핵심 열이 잠김
const LOCKED_COLS = ["재원", "예산목", "금액", "거래처", "원인발생일"];
function execOrigin(r) {
  if (!r || !r["거래번호"]) return null;
  const lab = (DATA.labor || []).find(x => x["연결거래번호"] === r["거래번호"]); if (lab) return { kind: "인건비", locked: true, row: lab._row, label: `${lab["지급월"]} ${lab["이름"]} · ${lab["지급처"]}` };
  const dep = DATA.deposit.find(x => x["연결거래번호"] === r["거래번호"]); if (dep) return { kind: "적립", locked: true, row: dep._row, label: `${dep["일자"]} ${dep["거래처"]} 적립` };
  const no = execReqNo(r); if (no) { const req = DATA.req.find(x => x["품의번호"] === no); return { kind: "품의", locked: false, row: req?._row, no, label: `품의 ${no}` }; }
  return null;
}
// 품의→집행 전환으로 생긴 집행의 품의번호: 연결품의번호 열 우선, 비어 있으면 비고 '품의 X' (이관 전 장부 호환). 비고는 자유 편집
function execReqNo(r) { const v = String(r?.["연결품의번호"] ?? "").trim(); if (v) return v; const m = /^품의 (\S+)/.exec(r?.["비고"] || ""); return m ? m[1] : ""; }
function originBadge(r) { const o = execOrigin(r); return o ? ` <button type="button" class="origin ${o.kind}" data-act="origin" data-row="${r._row}" title="${esc(o.label)} 에서 생성${o.locked ? " · 재원·예산목·금액·거래처·원인발생일은 원본에서만 변경" : ""} · 클릭하면 원본으로 이동">${o.kind}</button>` : ""; }
// 어떤 탭의 검색 칸에 q 만 남기고 그 표를 다시 그림 (원본으로 이동·연결 집행 보기)
const setSearch = (kind, q) => { FILTERS[kind] = { q }; $$(`[data-filter][data-kind=${kind}]`).forEach(el => { if (el.type === "checkbox") el.checked = false; else el.value = el.dataset.filter === "q" ? q : ""; }); renderList(kind); };
function gotoOrigin(row) {
  const r = DATA.exec.find(x => x._row === row); const o = execOrigin(r); if (!o) return;
  if (o.kind === "인건비") { setMode(true); switchLaborTab("ledger"); setSearch("labor", r["거래번호"]); }
  else if (o.kind === "적립") { switchTab("deposit"); setSearch("deposit", r["거래번호"]); }
  else { switchTab("req"); setSearch("req", o.no); }
}
function isExcludedExec(r) { return !DATA.funds.some(f => f["재원코드"] === r["재원"]) || !DATA.meta.budget_items.includes(r["예산목"]); }
function hasEvidence(r) { return !!(r["증빙목록"]) || (DATA.evidence || []).some(e => e["거래번호"] === r["거래번호"]); }

function renderExecTiles() {
  const rows = DATA.exec.filter(r => {  // 빠른 필터를 제외한 현재 필터 기준
    const f = FILTERS.exec || {}; const d = r["원인발생일"] || "";
    if (f["재원"] && r["재원"] !== f["재원"]) return false;
    if (f.year && d.slice(0, 4) !== f.year) return false;
    if (f.month && d.slice(5, 7) !== f.month) return false;
    return true;
  });
  const n = k => rows.filter(k).length;
  const tiles = [
    ["unclaimed", "발생 (미청구)", n(r => r["상태"] === "발생")],
    ["fix", "보완", n(r => r["상태"] === "보완")],
    ["done", "승인 (결의 대기)", n(r => r["상태"] === "완료")],
    ["noevid", "증빙 없음", n(r => !hasEvidence(r))],
    ["resolved", "완료", n(r => r["상태"] === "결의")],
    ["cancel", "취소", n(r => r["상태"] === "취소")],
  ];
  $("#exec-tiles").innerHTML = tiles.map(([k, l, c]) => `<div class="card ${QUICK === k ? "on" : ""}" role="button" tabindex="0" data-quick="${k}" aria-pressed="${QUICK === k}"><div class="k">${l}</div><div class="v">${c}건</div></div>`).join("");
}
// 드라이브 동기화: 이름 변경 반영 · 지운 파일의 증빙 삭제 · 폴더 이름 수정 (2026-10-20)
$("#btn-evid-sync")?.addEventListener("click", async e => {
  const b = e.currentTarget; b.disabled = true; const t = b.textContent; b.textContent = "동기화 중…";
  try {
    const r = await api("POST", "/api/evidence/sync-all");
    const parts = [`거래 ${r.numbers}건 확인`, r.renamed ? `이름 ${r.renamed}개 반영` : "", r.removed.length ? `드라이브에서 지운 증빙 ${r.removed.length}개 삭제` : "", r.folders_fixed ? `폴더 이름 ${r.folders_fixed}개 수정` : ""].filter(Boolean);
    showAlert(parts.join(" · ") + (r.errors.length ? ` · 오류 ${r.errors.length}건: ${r.errors[0]}` : ""), r.errors.length ? "warn" : "ok");
    await load();
  } catch (err) { showAlert("동기화 실패: " + err.message, "error"); }
  b.disabled = false; b.textContent = t;
});
$("#exec-tiles").addEventListener("click", e => { const t = e.target.closest("[data-quick]"); if (!t) return; QUICK = QUICK === t.dataset.quick ? "" : t.dataset.quick; renderExecTiles(); renderList("exec"); });
$("#exec-tiles").addEventListener("keydown", e => { if ((e.key === "Enter" || e.key === " ") && e.target.dataset.quick) { e.preventDefault(); e.target.click(); } });
$$("[data-filter][data-kind=exec]").forEach(el => el.addEventListener("input", renderExecTiles));

// 보완 이력 (보완이력 시트): 거래번호별 최신순
const fixLogOf = no => (DATA.fixlog || []).filter(x => x["거래번호"] === no).sort((a, b) => String(b["일시"]).localeCompare(String(a["일시"])) || b._row - a._row);
const latestFix = no => fixLogOf(no).find(x => x["구분"] === "표시") || null;
const latestCancel = no => fixLogOf(no).find(x => x["구분"] === "취소") || null;
// 적립금 사용 행의 단계 처리 ([오늘 등록]·상태 열 체크). 서버가 앞 단계 빈 날짜를 채우고 뒤 단계가 있으면 취소를 거부한다
async function depAction(row, action, btn) {
  const r = DATA.deposit.find(x => x._row === row); if (!r) return;
  const md = (() => { const [, m, d] = today().split("-"); return `${parseInt(m)}/${parseInt(d)}`; })();
  const label = { order: `발주 처리 · 발주일 ${md}`, pay: `결제 처리 · 결제일 ${md}`, receive: `수령 처리 · 수령일 ${md} (완료)`, unorder: "발주 취소", unpay: "결제 취소", unreceive: "수령 취소" }[action] || action;
  const inDrawer = !!btn?.closest("#exec-drawer");
  if (btn) btn.disabled = true;
  try {
    await api("POST", `/api/deposit/${row}/action`, { action, expect: expectOf("deposit", r) });
    showAlert(`${r["적립번호"] || r["거래처"]} ${label}`, "ok", { undo: true });
    await load();
    if (XD.kind === "deposit" && XD.row === row) { await renderDepDrawer(false); if (inDrawer) xdRefocus(".xd-step.next button[data-act=dact]"); }
  } catch (e) { showAlert(e.message, "error"); if (btn) btn.disabled = false; }
}
// 적립금 드로어의 단계 날짜 칸 수정 (비우면 단계 취소, 뒤 단계가 있으면 거부)
async function depSetDate(row, col, value) {
  const r = DATA.deposit.find(x => x._row === row); if (!r) return false;
  const i = DEP_STAGES.findIndex(st => st[1] === col); if (i < 0) return false;
  const lab = DEP_STAGES[i][0];
  if (!value) { if (DEP_STAGES.slice(i + 1).some(st => r[st[1]])) { showAlert("뒤 단계를 먼저 취소하세요", "warn"); return false; } }
  else if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) { showAlert("날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).", "warn"); return false; }
  const rec = { ...r }; delete rec._row; delete rec._locked_by; rec[col] = value;
  if (value) DEP_STAGES.slice(0, i).forEach(st => { if (!rec[st[1]]) rec[st[1]] = value; });  // 앞 단계 빈 날짜는 같은 날로
  try {
    await api("PUT", `/api/deposit/${row}`, { rec, expect: expectOf("deposit", r) });
    showAlert(`${r["적립번호"] || r["거래처"]} ${value ? (r[col] ? `${lab} 날짜 변경 · ${col} ${mmdd(value)}` : `${lab} 처리 · ${col} ${mmdd(value)}`) : `${lab} 취소 · ${col} 삭제`}`, "ok", { undo: true });
    await load();
    if (XD.kind === "deposit" && XD.row === row) await renderDepDrawer(false);
    return true;
  } catch (e) { showAlert(e.message, "error"); return false; }
}
async function execAction(row, action, btn) {
  const r = DATA.exec.find(x => x._row === row); if (!r) return;
  const md = (() => { const [, m, d] = today().split("-"); return `${parseInt(m)}/${parseInt(d)}`; })();
  const label = { cancel: "취소", uncancel: "취소 해제", claim: `청구 처리 · 지급청구일 ${md}`, resolve: `결의 처리 · 결의일 ${md} (완료)`, unresolve: "결의 취소", complete: `승인 처리 · 지출완료일 ${md}`, fix: "보완 표시", unfix: "보완 해제", uncomplete: "승인 취소 · 지출완료일 삭제" }[action];
  if (action === "uncomplete" && !await confirmDlg({ title: "승인 취소", body: `${r["거래번호"]} 의 지출완료일(${r["지출완료일"]})을 지우고 청구 상태로 되돌립니다.`, verb: "승인 취소", danger: true })) return;
  let extra = null;  // 보완: 사유를 받아 보완이력에 남긴다 (표시는 필수, 해제는 선택)
  if (action === "fix") {
    const reason = await confirmDlg({ title: `보완 표시 · ${r["거래번호"]}`, body: `${r["거래처"] || "-"} · ${fmt(r["금액"])}원 · ${r["적요"] || ""}\n\n무엇을 보완해야 하는지 적으세요. 보완 이력에 남고 상세 패널에서 볼 수 있습니다.`, verb: "보완 표시", input: { label: "보완 사유", value: "", required: true, error: "보완 사유를 입력하세요." } });
    if (reason === null) return;
    extra = { 사유: String(reason).trim() };
  } else if (action === "cancel") {
    const memo = await confirmDlg({ title: `집행 취소 · ${r["거래번호"]}`, body: `${r["거래처"] || "-"} · ${fmt(r["금액"])}원 · ${r["적요"] || ""}\n\n취소하면 이 금액은 집행액·잔액·대시보드·결의서에서 빠집니다. 행은 '취소' 상태로 남고 언제든 해제할 수 있습니다.`, verb: "취소", danger: true, input: { label: "취소 사유 (선택)", value: "", required: false } });
    if (memo === null) return;
    extra = { 사유: String(memo).trim() };
  } else if (action === "uncancel") {
    const last = latestCancel(r["거래번호"]);
    const memo = await confirmDlg({ title: `취소 해제 · ${r["거래번호"]}`, body: `${last ? `취소 사유: ${last["사유"] || "-"} (${last["일시"]})\n\n` : ""}해제하면 날짜대로 상태가 돌아오고 금액이 다시 집계됩니다.`, verb: "취소 해제", input: { label: "메모 (선택)", value: "", required: false } });
    if (memo === null) return;
    extra = { 사유: String(memo).trim() };
  } else if (action === "unfix") {
    const last = latestFix(r["거래번호"]);
    const memo = await confirmDlg({ title: `보완 해제 · ${r["거래번호"]}`, body: `${last ? `보완 사유: ${last["사유"]} (${last["일시"]})\n\n` : ""}보완이 끝났으면 해제합니다. 처리 내용은 선택 사항입니다.`, verb: "보완 해제", input: { label: "처리 내용 (선택)", value: "", required: false } });
    if (memo === null) return;
    extra = { 사유: String(memo).trim() };
  }
  const inDrawer = !!btn?.closest("#exec-drawer");
  if (btn) btn.disabled = true;
  try {
    await api("POST", `/api/exec/${row}/action`, { action, expect: expectOf("exec", r), ...(extra ? { extra } : {}) });
    showAlert(`${r["거래번호"]} ${label}`, "ok", { undo: true });
    await load();
    if (XD.row === row) { await renderExecDrawer(false); if (inDrawer) xdRefocus(action === "fix" || action === "unfix" ? ".xd-fix" : ".xd-step.next button[data-act=xact]"); }
  } catch (e) { showAlert(e.message, "error"); if (btn) btn.disabled = false; }
}

// 선택 행 표시만 옮김 (1,500건에서 renderList 는 수백 ms). 새 행을 표에서 못 찾을 때만 다시 그림
function markExecRow(prev, next) {
  const t = $("#exec-table"), find = r => r == null ? null : t.querySelector(`tbody tr[data-row="${r}"]`);
  const n = find(next);
  if (next != null && !n) { renderList("exec"); return; }
  find(prev)?.classList.remove("selected"); n?.classList.add("selected");
  const wrap = t.closest(".table-wrap"); if (wrap) wrap.classList.toggle("scrollable", t.scrollWidth > wrap.clientWidth + 4);  // 열 접기로 폭이 바뀜
}
function openExecDrawer(row, opts = {}) {
  const prev = XD.kind === "exec" ? XD.row : null;
  if (XD.kind !== "exec") { XD.kind = "exec"; renderList("deposit"); }
  XD.row = row; XD.evid = null;
  $("#ai-drawer").hidden = true;
  $("#exec-drawer").hidden = false; document.body.classList.add("drawer-open");
  markExecRow(prev, row);
  renderExecDrawer(true);
  if (opts.focus !== false) $("#xd-close").focus();
}
$("#xd-close").addEventListener("click", closeExecDrawer);

// ---- 이전/다음 건: 지금 그려진 집행 표의 행 순서 ----
function xdRows() { return $$(`#${XD.kind}-table tbody tr[data-row]`).map(tr => Number(tr.dataset.row)); }
function rerenderDrawer(fetchEvid) { return XD.kind === "deposit" ? renderDepDrawer(fetchEvid) : renderExecDrawer(fetchEvid); }
function updateXdNav() {
  if (XD.row == null || $("#exec-drawer").hidden) return;
  const rows = xdRows(), i = rows.indexOf(XD.row);
  $("#xd-prev").disabled = i <= 0;
  $("#xd-next").disabled = i < 0 || i >= rows.length - 1;
  $("#xd-pos").textContent = rows.length ? `${i < 0 ? "–" : i + 1} / ${rows.length}` : "";
}
function xdNav(delta) {
  const rows = xdRows(), i = rows.indexOf(XD.row), j = i + delta;
  if (i < 0 || j < 0 || j >= rows.length) return false;
  // 본문은 다시 그려지므로 그 안에 있던 포커스는 드로어로 옮겨 둠 (계속 ↑↓ 가능)
  if ($("#xd-body").contains(document.activeElement)) $("#exec-drawer").focus();
  (XD.kind === "deposit" ? openDepDrawer : openExecDrawer)(rows[j], { focus: false });
  $(`#${XD.kind}-table tbody tr[data-row="${rows[j]}"]`)?.scrollIntoView({ block: "nearest" });
  updateXdNav();
  return true;
}
$("#xd-prev").addEventListener("click", () => xdNav(-1));
$("#xd-next").addEventListener("click", () => xdNav(1));
$("#exec-drawer").addEventListener("keydown", e => {
  if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
  const d = { ArrowUp: -1, PageUp: -1, ArrowDown: 1, PageDown: 1 }[e.key]; if (!d) return;
  if (e.target.closest("input, select, textarea, [contenteditable=true]")) return;
  e.preventDefault(); xdNav(d);
});
function xdRefocus(sel) { const el = sel && $(`#xd-body ${sel}`); (el || $("#exec-drawer")).focus(); }

// ---- 단계 타임라인 · 바로 고치는 칸 ----
// [라벨, 날짜 열, '오늘 등록' 동작(execAction)]
const XD_STAGES = [["발생", "원인발생일", null], ["청구", "지급청구일", "claim"], ["승인", "지출완료일", "complete"], ["결의", "결의일", "resolve"]];
// 드로어에서 바로 고치는 칸 (재원·예산목·금액·거래처·적요는 수정 창에서)
const XD_INLINE = [["결제수단", "select"], ["세목", "text"], ["세세목", "text"], ["태그", "tag"], ["사용자", "text"], ["관리번호", "text"], ["비고", "textarea"]];
const XD_DL = { 세목: "dl-세목", 세세목: "dl-세세목", 사용자: "dl-사용자" };
const XD_IMG = /\.(jpe?g|png|gif|webp)$/i;
const VOUCHER_OFF = "지출완료일을 등록하면 결의서를 출력할 수 있습니다";   // [결의서] 버튼이 꺼진 이유 (지출결의서는 파일 끝)
const fileExt = n => (/\.([A-Za-z0-9]{1,5})$/.exec(n || "")?.[1] || "파일").toUpperCase();

// 날짜 직접 저장 (청구·승인·결의일 지정/수정/삭제). 앞 단계 빈 날짜는 store.exec_action 과 같은 규칙으로 채움
async function execSetDate(row, col, value) {
  const r = DATA.exec.find(x => x._row === row); if (!r) return false;
  const i = XD_STAGES.findIndex(s => s[1] === col); if (i < 0) return false;
  const lab = XD_STAGES[i][0];
  if (!value) {
    if (col === "원인발생일") { showAlert("원인발생일은 비울 수 없습니다.", "warn"); return false; }
    if (XD_STAGES.slice(i + 1).some(s => r[s[1]])) { showAlert("뒤 단계를 먼저 취소하세요", "warn"); return false; }
  } else if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) { showAlert("날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).", "warn"); return false; }
  const rec = { ...r }; delete rec._row; rec[col] = value;
  if (value && col === "지출완료일" && !rec["지급청구일"]) rec["지급청구일"] = value;
  if (value && col === "결의일") { if (!rec["지급청구일"]) rec["지급청구일"] = value; if (!rec["지출완료일"]) rec["지출완료일"] = value; }
  try {
    await api("PUT", `/api/exec/${row}`, { rec, expect: expectOf("exec", r) });
    showAlert(`${r["거래번호"]} ${value ? (r[col] ? `${lab} 날짜 변경 · ${col} ${mmdd(value)}` : `${lab} 처리 · ${col} ${mmdd(value)}`) : `${lab} 취소 · ${col} 삭제`}`, "ok", { undo: true });
    await load();
    if (XD.row === row) await renderExecDrawer(false);
    return true;
  } catch (e) { showAlert(e.message, "error"); return false; }
}
async function execSetField(row, field, value) {
  const r = DATA.exec.find(x => x._row === row); if (!r) return false;
  const rec = { ...r }; delete rec._row; rec[field] = value;
  try {
    await api("PUT", `/api/exec/${row}`, { rec, expect: expectOf("exec", r) });
    showAlert(`${r["거래번호"]} ${field} 저장`, "ok", { undo: true });
    await load();
    if (XD.row === row) await renderExecDrawer(false);
    return true;
  } catch (e) { showAlert(e.message, "error"); return false; }
}

// 값 자리(host)를 그 자리 편집기로 바꿈. Enter(textarea 는 Ctrl+Enter)·blur 저장, Esc 취소, 값이 같으면 요청 없음
function xdOpenEditor(host) {
  const row = XD.row, field = host.dataset.field, type = host.dataset.type, pick = !!host.dataset.pick;
  const r = (XD.kind === "deposit" ? DATA.deposit : DATA.exec).find(x => x._row === row); if (!r) return;
  const orig = r[field] == null ? "" : String(r[field]);
  let ed;
  if (type === "select" || (type === "tag" && DATA.tags.length)) {
    ed = document.createElement("select");
    const opts = type === "select" ? ["", ...DATA.meta.pay_methods] : ["", ...DATA.tags.map(t => t["태그명"])];
    if (orig && !opts.includes(orig)) opts.push(orig);  // 목록에 없는 기존 값도 유지
    ed.innerHTML = opts.map(v => `<option value="${esc(v)}">${esc(v || "(없음)")}</option>`).join("");
  } else if (type === "textarea") { ed = document.createElement("textarea"); ed.rows = 2; }
  else {
    ed = document.createElement("input"); ed.type = type === "date" ? "date" : "text"; ed.autocomplete = "off";
    if (XD_DL[field]) ed.setAttribute("list", XD_DL[field]);
    if (type === "tag") ed.setAttribute("list", "dl-태그");
  }
  ed.className = "xd-edit"; ed.dataset.field = field; ed.value = pick ? "" : orig;
  ed.setAttribute("aria-label", `${host.dataset.label || field} ${type === "textarea" ? "(Ctrl+Enter 저장, Esc 취소)" : "(Enter 저장, Esc 취소)"}`);
  let busy = false, closed = false, lastKey = 0;
  const restore = focus => { closed = true; if (ed.isConnected) ed.replaceWith(host); if (focus) host.focus(); };
  const commit = async viaKey => {
    if (busy || closed) return;
    const v = type === "textarea" ? ed.value.replace(/\s+$/, "") : ed.value.trim();
    if (v === orig || (pick && !v)) { restore(viaKey); return; }
    busy = true;
    const ok = type === "date" ? await (XD.kind === "deposit" ? depSetDate : execSetDate)(row, field, v) : await execSetField(row, field, v);
    busy = false;
    if (ok) { closed = true; if (viaKey || document.activeElement === document.body) xdRefocus(`.xd-val[data-field="${field}"]`); }
    else if (ed.isConnected) ed.focus();  // 실패: 입력값 그대로 편집기 유지
  };
  ed.addEventListener("keydown", e => {
    lastKey = Date.now();
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); restore(true); }
    else if (e.key === "Enter" && (type !== "textarea" || e.ctrlKey || e.metaKey)) { e.preventDefault(); commit(true); }
  });
  // 마우스로 목록·달력에서 고르면 바로 저장 (키보드로 넘기는 중에는 저장하지 않음)
  if (ed.tagName === "SELECT" || type === "date") ed.addEventListener("change", () => { if (Date.now() - lastKey > 400) commit(true); });
  ed.addEventListener("blur", () => { if (ed.isConnected) commit(false); });
  host.replaceWith(ed); ed.focus();
  if (type === "date" && pick) { try { ed.showPicker(); } catch { } }
}

async function renderExecDrawer(fetchEvid) {
  const r = DATA.exec.find(x => x._row === XD.row);
  if (!r) { $("#exec-drawer").hidden = true; XD.row = null; return; }
  $("#xd-title").innerHTML = esc(r["거래번호"]) + originBadge(r);
  $("#xd-sub").innerHTML = `${esc(r["재원"])} · ${esc(r["예산목"])} · <b>${fmt(r["금액"])}원</b>`;
  updateXdNav();
  // 다른 저장·새로고침으로 다시 그릴 때 입력 중이던 증빙 업로드 폼은 유지
  const oldForm = $("#evid-form"), keep = oldForm && XD.formRow === r._row ? { kind: oldForm.kind.value, date: oldForm.date.value, note: oldForm.note.value, files: oldForm.files.files } : null;
  const oldEntry = $("#evid-entry-form"), keepEntry = oldEntry && XD.formRow === r._row ? { kind: oldEntry.kind.value, note: oldEntry.note.value } : null;
  const seq = ++XD.seq;  // 빠르게 다른 행을 열면 늦게 온 응답은 버림
  if (fetchEvid || !XD.evid) {
    try { const d = await api("GET", `/api/evidence/${encodeURIComponent(r["거래번호"])}`); if (seq !== XD.seq || XD.row !== r._row) return; XD.evid = d.items; XD.drive = d.drive; }
    catch (e) { XD.evid = []; XD.drive = { connected: false, error: e.message }; }
  }
  if (seq !== XD.seq) return;
  const body = $("#xd-body"), scroll = XD.shownRow === r._row ? body.scrollTop : 0;
  const st = r["상태"], o = execOrigin(r), locked = !!o?.locked;
  const evid = XD.evid || [];
  const drive = XD.drive || {};
  // 타임라인: 마지막으로 날짜가 있는 단계의 다음이 '다음 단계'
  const last = XD_STAGES.reduce((a, s, i) => r[s[1]] ? i : a, -1), next = last + 1;
  const dateVal = (lab, col, v) => `<span class="xd-val xd-date${v ? "" : " empty"}" role="button" tabindex="0" data-field="${col}" data-type="date" data-label="${lab} ${col}" title="${col}: 눌러서 날짜 수정 (지우면 단계 취소)" aria-label="${lab} ${col} ${v || "없음"}, 눌러서 수정">${esc(v || "–")}</span>`;
  const steps = XD_STAGES.map(([lab, col, act], i) => {
    const v = r[col] || "", done = !!v, isNext = i === next, fix = i === 1 && st === "보완";
    const cls = (done ? "done" : isNext ? "next" : "todo") + (fix ? " fix" : "");
    let below;
    if (done || i < next) below = col === "원인발생일" && locked ? `<span class="xd-date" title="${esc(o.kind)} 연결 행: 원인발생일은 원본에서만 변경">${esc(v || "–")}</span>` : dateVal(lab, col, v);
    else if (isNext) below = (act ? `<button type="button" class="btn btn-sm btn-primary" data-act="xact" data-action="${act}" data-row="${r._row}" title="${col}을 오늘(${today()})로 등록">오늘 등록</button>` : "")
      + `<button type="button" class="xd-pick" data-pick="1" data-field="${col}" data-type="date" data-label="${lab} ${col}" aria-label="${lab} ${col} 날짜 지정">날짜 지정</button>`;
    else below = `<span class="xd-date empty" aria-hidden="true">–</span>`;
    const fixBtn = i === 1 && (st === "청구" || st === "보완") ? `<button type="button" class="xd-fix" data-act="xact" data-action="${fix ? "unfix" : "fix"}" data-row="${r._row}" aria-pressed="${fix}" title="${fix ? "보완 해제" : "서류·증빙 보완이 필요하다고 표시"}"><span class="box" aria-hidden="true"><svg viewBox="0 0 12 12" focusable="false"><path d="M2.5 6.5l2.5 2.5 4.5-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span>보완</button>` : "";
    const label = i === 3 && done ? STATUS_LABEL["결의"] : lab;
    return `<li class="xd-step ${cls}" data-col="${col}"><span class="xd-dot" aria-hidden="true"></span><span class="xd-step-l">${label}<span class="sr-only">${done ? " 단계 완료" : isNext ? " 단계 (다음 처리)" : " 단계 (대기)"}${fix ? ", 보완 필요" : ""}</span></span><div class="xd-step-d">${below}${fixBtn}</div></li>`;
  }).join("");
  const kv = (k, v) => `<b>${k}</b><span class="xd-ro">${esc(v || "-")}</span>`;
  const iv = (k, type) => { const v = r[k] == null ? "" : String(r[k]); return `<b>${k}</b><span class="xd-val${v ? "" : " empty"}${type === "textarea" ? " multi" : ""}" role="button" tabindex="0" data-field="${k}" data-type="${type}" title="눌러서 수정" aria-label="${k} ${esc(v || "비어 있음")}, 눌러서 수정">${esc(v || "–")}</span>`; };
  body.innerHTML = `
    <section class="xd-sec xd-tl-sec" aria-label="처리 단계">
      <h3>처리 단계 <span class="badge ${esc(st)}" title="${esc(STATUS_HELP[st] || "")}">${esc(STATUS_LABEL[st] || st)}</span></h3>
      <ol class="xd-timeline">${steps}</ol>
    </section>
    ${(() => { const log = fixLogOf(r["거래번호"]); if (!log.length && st !== "보완") return ""; return `<section class="xd-sec xd-fixlog" aria-label="보완·취소 이력"><h3>보완·취소 이력${st === "보완" && log[0] ? ` <span class="muted">· 현재 보완 필요</span>` : st === "취소" ? ` <span class="muted">· 현재 취소됨</span>` : ""}</h3>
      <ul class="xd-fixlist">${log.map(x => `<li class="${x["구분"] === "표시" || x["구분"] === "취소" ? "mark" : "clear"}"><span class="fl-when">${esc(x["일시"])}</span><span class="fl-kind">${esc(x["구분"])}</span><span class="fl-why">${esc(x["사유"] || "-")}</span></li>`).join("") || '<li class="muted">기록 없음</li>'}</ul></section>`; })()}
    <section class="xd-sec xd-info">
      <h3>집행 정보 <span class="sp"></span><button type="button" class="btn btn-sm" data-act="edit" data-kind="exec" data-row="${r._row}" title="재원·예산목·금액·거래처·적요는 수정 창에서">수정</button></h3>
      ${locked ? `<p class="toolbar-note xd-lock">${esc(o.label)} 에서 생긴 집행입니다. 재원·예산목·금액·거래처·원인발생일은 원본에서 처리합니다.</p>` : ""}
      <div class="kv">
        ${kv("거래처", r["거래처"])}${kv("적요", r["적요"])}
        ${XD_INLINE.map(([k, t]) => iv(k, t)).join("")}
      </div>
    </section>
    ${evidSectionsHtml({ number: r["거래번호"], evid, drive, dateDefault: r["원인발생일"], folderHint: `증빙관리/${esc((r["원인발생일"] || "").slice(0, 4))}/${esc(r["재원"])}/${esc(r["거래번호"])}`, folderUrl: r["증빙폴더"] })}
    <section class="xd-sec xd-foot">${(() => { const ev = evid.length; const dis = locked || ev; const vOk = !!r["지출완료일"] && st !== "취소"; return `<button type="button" class="btn btn-sm" data-act="voucher" data-row="${r._row}"${vOk ? "" : " disabled"} title="${st === "취소" ? "취소된 집행" : vOk ? "지출결의서 미리보기 · A4 인쇄" : VOUCHER_OFF}">결의서</button>${st === "취소"
      ? `<button type="button" class="btn btn-sm" data-act="xact" data-action="uncancel" data-row="${r._row}" title="취소를 해제하고 날짜대로 상태를 되돌림">취소 해제</button>`
      : `<button type="button" class="btn btn-sm" data-act="xact" data-action="cancel" data-row="${r._row}"${locked ? " disabled" : ""} title="${locked ? `${o.kind} 연결 행: 원본 화면에서 처리` : "이 집행을 취소 (금액은 집계에서 빠지고 행은 남음, 해제 가능)"}">취소</button>`}<button type="button" class="btn btn-sm btn-danger" data-act="del" data-kind="exec" data-row="${r._row}"${dis ? " disabled" : ""} title="${locked ? `${o.kind} 연결 행: 원본 화면에서 처리` : ev ? "증빙을 먼저 지워야 삭제할 수 있습니다" : "이 집행을 삭제 (되돌리기 가능)"}">이 집행 삭제</button>${dis ? `<span class="toolbar-note">${locked ? `${o.kind} 연결 행이라 원본 화면에서 처리합니다` : `증빙 ${ev}개를 먼저 지우면 삭제할 수 있습니다`}</span>` : ""}`; })()}</section>`;
  bindEvidForm({ number: r["거래번호"], rerender: () => renderExecDrawer(true) });
  bindXdBody();
  XD.formRow = r._row; XD.shownRow = r._row;
  if (keepEntry) { const f = $("#evid-entry-form"); f.kind.value = keepEntry.kind; f.note.value = keepEntry.note; }
  if (keep) { const f = $("#evid-form"); f.kind.value = keep.kind; if (keep.date) f.date.value = keep.date; f.note.value = keep.note; try { if (keep.files?.length && !f.files.disabled) f.files.files = keep.files; } catch { } }
  body.scrollTop = scroll;
}

// ---- 적립금 드로어: 집행 드로어(#exec-drawer)를 같이 쓴다. 거래 정보 + 증빙 3절 ----
function openDepDrawer(row, opts = {}) {
  const prev = XD.kind === "deposit" ? XD.row : null;
  if (XD.kind !== "deposit") { if (XD.row != null) markExecRow(XD.row, null); XD.kind = "deposit"; }
  XD.row = row; XD.evid = null;
  $("#ai-drawer").hidden = true;
  $("#exec-drawer").hidden = false; document.body.classList.add("drawer-open");
  const t = $("#deposit-table"); t.querySelector(`tbody tr[data-row="${prev}"]`)?.classList.remove("selected"); t.querySelector(`tbody tr[data-row="${row}"]`)?.classList.add("selected");
  renderDepDrawer(true);
  if (opts.focus !== false) $("#xd-close").focus();
}
async function renderDepDrawer(fetchEvid) {
  const r = DATA.deposit.find(x => x._row === XD.row);
  if (!r) { $("#exec-drawer").hidden = true; XD.row = null; return; }
  const no = r["적립번호"] || "";
  $("#xd-title").innerHTML = esc(no || "적립금");
  $("#xd-sub").innerHTML = `${esc(r["일자"])} · ${esc(r["거래처"])} · ${esc(r["구분"])} <b>${fmt(r["금액"])}원</b>`;
  updateXdNav();
  const oldForm = $("#evid-form"), keep = oldForm && XD.formRow === r._row ? { kind: oldForm.kind.value, date: oldForm.date.value, note: oldForm.note.value, files: oldForm.files.files } : null;
  const oldEntry = $("#evid-entry-form"), keepEntry = oldEntry && XD.formRow === r._row ? { kind: oldEntry.kind.value, note: oldEntry.note.value } : null;
  const seq = ++XD.seq;
  if (fetchEvid || !XD.evid) {
    try { const d = no ? await api("GET", `/api/evidence/${encodeURIComponent(no)}`) : { items: [], drive: {} }; if (seq !== XD.seq || XD.row !== r._row) return; XD.evid = d.items; XD.drive = d.drive; }
    catch (e) { XD.evid = []; XD.drive = { connected: false, error: e.message }; }
  }
  if (seq !== XD.seq) return;
  const body = $("#xd-body"), scroll = XD.shownRow === r._row ? body.scrollTop : 0;
  const evid = XD.evid || [], drive = XD.drive || {};
  const kv = (k, v) => `<b>${k}</b><span class="xd-ro">${esc(v == null || v === "" ? "-" : v)}</span>`;
  const lockedBy = r._locked_by;  // 주문이 남긴 사용 행: 핵심 열·삭제 잠금
  const linkNo = r["연결거래번호"], linkEv = linkNo ? evidCountNo(linkNo) : 0;
  // 단계 타임라인 (사용 행만): 마지막으로 날짜가 있는 단계의 다음이 '다음 단계'. 날짜 칸은 눌러서 수정, 비우면 취소
  const st = r["상태"] || "";
  let timeline = "";
  if (r["구분"] === "사용") {
    const last = DEP_STAGES.reduce((a, s_, i) => r[s_[1]] ? i : a, -1), next = last + 1;
    const dateVal = (lab, col, v) => `<span class="xd-val xd-date${v ? "" : " empty"}" role="button" tabindex="0" data-field="${col}" data-type="date" data-label="${lab} ${col}" title="${col}: 눌러서 날짜 수정 (지우면 단계 취소)" aria-label="${lab} ${col} ${v || "없음"}, 눌러서 수정">${esc(v || "–")}</span>`;
    const steps = DEP_STAGES.map(([lab, col, act], i) => {
      const v = r[col] || "", done = !!v, isNext = i === next;
      let below;
      if (done || i < next) below = dateVal(lab, col, v);
      else if (isNext) below = `<button type="button" class="btn btn-sm btn-primary" data-act="dact" data-action="${act}" data-row="${r._row}" title="${col}을 오늘(${today()})로 등록">오늘 등록</button>`
        + `<button type="button" class="xd-pick" data-pick="1" data-field="${col}" data-type="date" data-label="${lab} ${col}" aria-label="${lab} ${col} 날짜 지정">날짜 지정</button>`;
      else below = `<span class="xd-date empty" aria-hidden="true">–</span>`;
      return `<li class="xd-step ${done ? "done" : isNext ? "next" : "todo"}" data-col="${col}"><span class="xd-dot" aria-hidden="true"></span><span class="xd-step-l">${lab}<span class="sr-only">${done ? " 단계 완료" : isNext ? " 단계 (다음 처리)" : " 단계 (대기)"}</span></span><div class="xd-step-d">${below}</div></li>`;
    }).join("");
    timeline = `<section class="xd-sec xd-tl-sec" aria-label="처리 단계"><h3>처리 단계 <span class="badge ${esc(st)}" title="${esc(DEP_STATUS_HELP[st] || "")}">${esc(st)}</span></h3><ol class="xd-timeline">${steps}</ol></section>`;
  }
  body.innerHTML = `
    ${timeline}
    <section class="xd-sec xd-info">
      <h3>적립금 정보 <span class="badge">${esc(r["구분"])}</span><span class="sp"></span><button type="button" class="btn btn-sm" data-act="edit" data-kind="deposit" data-row="${r._row}">수정</button></h3>
      ${lockedBy ? `<p class="toolbar-note xd-lock">주문 ${esc(lockedBy)} 에 연결된 적립금 기록입니다. 금액·거래처·구분·증빙번호는 주문 보기에서 처리합니다.</p>` : ""}
      ${linkNo ? `<p class="toolbar-note">연결 집행 <button type="button" class="lnk" data-act="dep-exec" data-no="${esc(linkNo)}" title="집행내역에서 이 집행 보기">${esc(linkNo)}</button> · 그 집행의 증빙 ${linkEv}개 (이 적립금 기록의 증빙과 별개)</p>` : ""}
      <div class="kv">
        ${kv("일자", r["일자"])}${kv("거래처", r["거래처"])}${kv("금액", fmt(r["금액"]) + "원")}${kv("적요", r["적요"])}
        ${kv("사용자", r["사용자"])}${kv("증빙번호(수기)", r["증빙번호"])}${kv("태그", r["태그"])}${kv("비고", r["비고"])}
        ${r["구분"] === "사용" ? "" : kv("단계", "적립 행은 단계 없음")}
      </div>
    </section>
    ${evidSectionsHtml({ number: no, evid, drive, dateDefault: r["일자"], folderHint: `증빙관리/${esc((r["일자"] || "").slice(0, 4))}/적립금/${esc(r["거래처"])}/${esc(no)}` })}
    <section class="xd-sec xd-foot">${(() => { const ev = evid.length, dis = lockedBy || ev; return `<button type="button" class="btn btn-sm btn-danger" data-act="del" data-kind="deposit" data-row="${r._row}"${dis ? " disabled" : ""} title="${lockedBy ? "주문 연결 행: 주문 보기에서 처리" : ev ? "증빙을 먼저 지워야 삭제할 수 있습니다" : "이 적립금 기록을 삭제"}">이 기록 삭제</button>${dis ? `<span class="toolbar-note">${lockedBy ? "주문에 연결된 기록이라 주문 보기에서 처리합니다" : `증빙 ${ev}개를 먼저 지우면 삭제할 수 있습니다`}</span>` : ""}`; })()}</section>`;
  bindEvidForm({ number: no, rerender: () => renderDepDrawer(true) });
  bindXdBody();
  XD.formRow = r._row; XD.shownRow = r._row;
  if (keepEntry) { const f = $("#evid-entry-form"); f.kind.value = keepEntry.kind; f.note.value = keepEntry.note; }
  if (keep) { const f = $("#evid-form"); f.kind.value = keep.kind; if (keep.date) f.date.value = keep.date; f.note.value = keep.note; try { if (keep.files?.length && !f.files.disabled) f.files.files = keep.files; } catch { } }
  body.scrollTop = scroll;
}
// 증빙 절 3개(목록 · 실물만 항목 추가 · 업로드): 집행 드로어와 적립금 드로어가 같이 쓴다.
// c = { number(거래번호|적립번호), evid, drive, dateDefault(파일명 날짜 기본값), folderHint(끌어놓기 칸 안내), folderUrl(폴더 열기, 없으면 생략) }
function evidSectionsHtml(c) {
  const evid = c.evid || [], drive = c.drive || {};
  const kinds = [...new Set(evid.map(e => e["증빙종류"]).filter(Boolean))];
  const nFile = evid.filter(evHasFile).length;
  return `
    <section class="xd-sec">
      <h3>증빙 <span class="toolbar-note">${evid.length}개${nFile < evid.length ? ` · 파일 ${nFile}개` : ""}</span><span class="sp"></span>${c.folderUrl ? `<a class="btn btn-sm" href="${esc(c.folderUrl)}" target="_blank" rel="noopener">폴더 열기</a>` : ""}</h3>
      ${!drive.connected ? `<p class="toolbar-note warn">구글 드라이브가 연결되지 않았습니다. 오른쪽 위 설정(톱니)에서 연결하면 업로드할 수 있습니다.${drive.error ? " (" + esc(drive.error) + ")" : ""}</p>` : ""}
      ${evid.length ? `<div class="table-wrap"><table class="grid compact evid-table"><thead><tr><th class="xd-th-cell"><span class="sr-only">미리보기</span></th><th>증빙</th><th>파일</th><th>비고</th><th><span class="sr-only">작업</span></th></tr></thead><tbody>
        ${evid.map(evidRowHtml).join("")}
      </tbody></table></div>` : '<p class="toolbar-note">등록된 증빙이 없습니다.</p>'}
      <div class="evid-list"><span class="toolbar-note">증빙목록</span><code>${esc(kinds.join(", ") || "(없음)")}</code>${kinds.length ? `<button type="button" class="btn btn-sm" id="evid-copy">복사</button>` : ""}</div>
    </section>
    <section class="xd-sec">
      <h3>증빙 항목 추가 <span class="toolbar-note">파일 없이 실물만</span></h3>
      <form id="evid-entry-form" class="evid-form evid-entry">
        <label>증빙종류 <input type="text" name="kind" list="dl-증빙종류" required autocomplete="off" placeholder="예: 영수증, 거래명세서"></label>
        <label>비고 <input type="text" name="note" placeholder="선택"></label>
        <div class="wide evid-entry-row"><span class="toolbar-note">첨부 양식을 출력해 실물을 붙입니다. 파일은 나중에 목록의 [파일 첨부]로 올립니다.</span><button type="submit" class="btn btn-sm">항목 추가</button></div>
      </form>
      <input type="file" id="evid-attach-input" class="sr-only" tabindex="-1" aria-hidden="true">
    </section>
    <section class="xd-sec">
      <h3>증빙 업로드</h3>
      <form id="evid-form" class="evid-form">
        <label>증빙종류 <input type="text" name="kind" list="dl-증빙종류" required autocomplete="off" placeholder="예: 카드전표, 견적서, 회의록"></label>
        <label>파일명 날짜 <input type="date" name="date" value="${esc(c.dateDefault || today())}"></label>
        <label>비고 <input type="text" name="note" placeholder="선택"></label>
        <label class="file-pick">파일 <span class="file-pick-row"><input type="file" name="files" multiple ${drive.connected ? "" : "disabled"}><span class="btn btn-sm file-btn" aria-hidden="true">파일 선택</span><span class="file-names">선택된 파일 없음</span></span></label>
        <div class="wide evid-drop-row"><div class="drop" id="evid-drop" title="이름은 ${/-(적립|사용)-\d{4}-/.test(c.number) ? "거래처_증빙종류_금액_YYMMDD" : "재원_증빙종류_금액_YYMMDD"} 로 자동 변환됩니다 (재원·거래처·금액을 고치면 따라 바뀜)"><b>파일을 여기로 끌어다 놓기</b> · ${c.folderHint}</div><button type="submit" class="btn btn-primary btn-sm" ${drive.connected ? "" : "disabled"}>업로드</button></div>
      </form>
    </section>`;
}
// 증빙 한 줄: 파일이 없으면(실물만 항목) '파일 없음' 표시와 [파일 첨부]
const evHasFile = e => e.has_file ?? !!(e["파일명"] || e["드라이브파일ID"]);
function evidRowHtml(e) {
  const has = evHasFile(e), n = e["파일명"] || "", id = e["드라이브파일ID"];
  const thumb = !has ? "" : XD_IMG.test(n) && id ? `<img class="xd-thumb" loading="lazy" alt="" src="/api/evidence/thumb/${encodeURIComponent(id)}" data-ext="${esc(fileExt(n))}">` : `<span class="xd-chip" aria-hidden="true">${esc(fileExt(n))}</span>`;
  const meta = [e["크기"] ? Math.max(1, Math.round(e["크기"] / 1024)).toLocaleString() + " KB" : "", e["업로드일"] ? mmdd(e["업로드일"]) : ""].filter(Boolean).join(" · ");
  const file = has ? `${e.missing ? `<span class="evid-nofile" title="드라이브에서 지워졌거나 휴지통에 있습니다. 장부 기록만 남아 있으니 [삭제]로 정리하거나 드라이브에서 복구하세요">${esc(n)} · 드라이브에 없음</span>` : e.url ? `<a href="${esc(e.url)}" target="_blank" rel="noopener" title="새 창에서 열기">${esc(n)}</a>` : esc(n)}${meta ? `<div class="toolbar-note">${esc(meta)}</div>` : ""}` : `<span class="evid-nofile">파일 없음</span>`;
  const conn = !!XD.drive?.connected;
  const attach = has
    ? `<button type="button" class="btn btn-sm" data-evattach="${e._row}" data-replace="1"${conn ? "" : " disabled"} title="${conn ? "파일을 새 파일로 바꿉니다 (증빙번호·종류·비고 유지, 옛 파일은 드라이브 휴지통)" : "구글 드라이브를 연결하면 교체할 수 있습니다"}">교체</button>`
    : `<button type="button" class="btn btn-sm" data-evattach="${e._row}"${conn ? "" : " disabled"} title="${conn ? "이 항목에 파일 1개를 올려 붙입니다" : "구글 드라이브를 연결하면 첨부할 수 있습니다"}">파일 첨부</button>`;
  const label = has ? n : `${e["증빙번호"]} ${e["증빙종류"]}`;
  return `<tr${has ? "" : ' class="evid-row-nofile"'}><td class="xd-th-cell">${thumb}</td><td class="evid-id"><span class="evid-kind">${esc(e["증빙종류"])}</span><span class="evid-no">${esc(e["증빙번호"])}</span></td><td class="evid-name">${file}</td><td class="evid-note">${esc(e["비고"])}</td><td class="evid-acts"><button type="button" class="btn btn-sm" data-evmount="${e._row}" title="이 증빙의 첨부 양식 인쇄">양식</button>${has ? `<button type="button" class="btn btn-sm" data-evcopy="${e._row}"${conn ? "" : " disabled"} title="이 파일을 다른 거래의 증빙으로 복사 (그 거래 폴더에, 그 거래 기준 이름으로)">복사</button>` : ""}${attach}<button type="button" class="btn btn-sm btn-danger" data-evdel="${e._row}" data-name="${esc(label)}" data-file="${has ? 1 : ""}" title="${has ? "장부에서 삭제하고 드라이브 휴지통으로 이동" : "장부에서 이 항목을 삭제"}">삭제</button></td></tr>`;
}
function bindXdBody() {
  const body = $("#xd-body");
  $$(".xd-val, .xd-pick", body).forEach(el => {
    el.addEventListener("click", () => xdOpenEditor(el));
    if (el.tagName !== "BUTTON") el.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " " || e.key === "F2") { e.preventDefault(); xdOpenEditor(el); } });
  });
  // 썸네일을 못 받으면(이미지 아님·드라이브 오류 → 204) 확장자 칩으로 바꿈
  $$("img.xd-thumb", body).forEach(img => {
    const toChip = () => { if (!img.isConnected) return; const c = document.createElement("span"); c.className = "xd-chip"; c.setAttribute("aria-hidden", "true"); c.textContent = img.dataset.ext; img.replaceWith(c); };
    img.addEventListener("error", toChip);
  });
}

// 증빙 폼 동작 바인딩. c = { number(거래번호|적립번호), rerender(저장 뒤 드로어 다시 그리기) }
function bindEvidForm(c) {
  const form = $("#evid-form"); if (!form) return;
  const fileInput = form.querySelector("[name=files]");
  const names = form.querySelector(".file-names");
  const showNames = () => { const f = fileInput.files; names.textContent = f.length ? (f.length === 1 ? f[0].name : `${f[0].name} 외 ${f.length - 1}개`) : "선택된 파일 없음"; };
  fileInput.addEventListener("change", showNames); showNames();
  const dz = $("#evid-drop");
  ["dragenter", "dragover"].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add("hot"); }));
  ["dragleave", "drop"].forEach(ev => dz.addEventListener(ev, () => dz.classList.remove("hot")));
  dz.addEventListener("drop", e => { e.preventDefault(); if (e.dataTransfer.files.length && !fileInput.disabled) { fileInput.files = e.dataTransfer.files; form.requestSubmit(); } });
  form.addEventListener("submit", async e => {
    e.preventDefault();
    const fd = new FormData(form);
    const files = fileInput.files;
    if (!files.length) { showAlert("파일을 선택하세요.", "warn"); return; }
    if (!fd.get("kind").trim()) { showAlert("증빙종류를 입력하세요.", "warn"); form.querySelector("[name=kind]").focus(); return; }
    const btn = form.querySelector("button[type=submit]"); btn.disabled = true; btn.textContent = `업로드 중… (${files.length}개)`;
    try {
      const res = await fetch(`/api/evidence/${encodeURIComponent(c.number)}`, { method: "POST", body: fd });
      if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
      const d = await res.json();
      const up = d.items || [];
      showAlert(`${up.length}개 업로드 완료`, "ok", up.length ? { action: { label: "양식 인쇄", run: () => openMount(up, 0, null) } } : {});
      await load();
      await c.rerender();
    } catch (err) { showAlert("업로드 실패: " + err.message, "error"); btn.disabled = false; btn.textContent = "업로드"; }
  });
  // 증빙 항목 추가 (파일 없이 실물만): 증빙번호를 받고, 알림에서 바로 첨부 양식 인쇄
  const ef = $("#evid-entry-form");
  ef?.addEventListener("submit", async e => {
    e.preventDefault();
    const kind = ef.kind.value.trim(), note = ef.note.value.trim();
    if (!kind) { showAlert("증빙종류를 입력하세요.", "warn"); ef.kind.focus(); return; }
    const btn = ef.querySelector("button[type=submit]"); btn.disabled = true; btn.textContent = "추가 중…";
    try {
      const it = await api("POST", `/api/evidence/${encodeURIComponent(c.number)}/entry`, { 증빙종류: kind, 비고: note });
      ef.kind.value = ""; ef.note.value = "";
      showAlert(`증빙 항목 ${it["증빙번호"]} 을 추가했습니다 (파일 없음)`, "ok", { action: { label: "양식 인쇄", run: () => openMount([it], 0, null) } });
      await load(); await c.rerender();
    } catch (err) { showAlert("항목 추가 실패: " + err.message, "error"); btn.disabled = false; btn.textContent = "항목 추가"; }
  });
  // [파일 첨부]: 실물만 항목에 파일 1개를 붙임 (같은 증빙번호·종류·비고, 드라이브 이름·폴더 규칙은 업로드와 같음)
  const ai = $("#evid-attach-input");
  $$("#xd-body [data-evattach]").forEach(b => b.addEventListener("click", () => { if (!ai) return; XD.attachRow = Number(b.dataset.evattach); XD.attachReplace = !!b.dataset.replace; ai.value = ""; ai.click(); }));
  ai?.addEventListener("change", async () => {
    const f = ai.files[0], row = XD.attachRow, e = (XD.evid || []).find(x => x._row === row); if (!f || !e) return;
    const replace = !!XD.attachReplace;
    const b = $(`#xd-body [data-evattach="${row}"]`); if (b) { b.disabled = true; b.textContent = replace ? "교체 중…" : "첨부 중…"; }
    const fd = new FormData(); fd.append("files", f); fd.append("row", String(row)); fd.append("증빙번호", e["증빙번호"]); if (replace) fd.append("replace", "1");
    const d = $("#evid-form")?.date.value; if (d) fd.append("date", d);
    try {
      const res = await fetch(`/api/evidence/${encodeURIComponent(c.number)}`, { method: "POST", body: fd });
      if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
      showAlert(replace ? `증빙 ${e["증빙번호"]} 의 파일을 교체했습니다 (옛 파일은 드라이브 휴지통)` : `증빙 ${e["증빙번호"]} 에 파일을 첨부했습니다`, "ok");
      await load(); await c.rerender();
      $(`#xd-body [data-evmount="${row}"]`)?.focus();
    } catch (err) { showAlert((replace ? "교체" : "첨부") + " 실패: " + err.message, "error"); if (b?.isConnected) { b.disabled = false; b.textContent = replace ? "교체" : "파일 첨부"; b.focus(); } }
  });
  $("#evid-copy")?.addEventListener("click", async () => { try { await navigator.clipboard.writeText($(".evid-list code").textContent); showAlert("증빙목록을 복사했습니다.", "ok"); } catch { } });
  $$("#xd-body [data-evmount]").forEach(b => b.addEventListener("click", () => {
    const e = (XD.evid || []).find(x => x._row === Number(b.dataset.evmount)); if (e) openMount([e], 0, b);
  }));
  // [복사]: 같은 파일을 다른 거래(들)의 증빙으로 — 거래번호를 쉼표로 여러 개 (2026-10-20)
  $$("#xd-body [data-evcopy]").forEach(b => b.addEventListener("click", async () => {
    const e = (XD.evid || []).find(x => x._row === Number(b.dataset.evcopy)); if (!e) return;
    const v = await confirmDlg({ title: `증빙 복사 · ${e["증빙번호"]}`, body: `'${e["파일명"]}' 을 다른 거래의 증빙으로 복사합니다. 파일은 그 거래의 드라이브 폴더에 그 거래 기준 이름으로 저장되고, 각 거래에 독립된 증빙 항목이 생깁니다.`, verb: "복사", input: { label: "복사할 거래번호 (여러 개면 쉼표)", value: "", required: true } });
    if (v === null) return;
    const targets = String(v).split(/[,\s]+/).map(x => x.trim()).filter(Boolean);
    if (!targets.length) return;
    b.disabled = true;
    try {
      const r = await api("POST", `/api/evidence/${encodeURIComponent(c.number)}/copy`, { row: e._row, targets });
      const ok = r.copied.map(x => `${x["거래번호"]} (${x["증빙번호"]})`).join(", ");
      showAlert(`${r.copied.length}건 복사${ok ? ": " + ok : ""}${r.errors.length ? ` · 실패 ${r.errors.length}건: ${r.errors.join("; ")}` : ""}`, r.errors.length ? "warn" : "ok");
      await load(); await c.rerender();
    } catch (err) { showAlert("복사 실패: " + err.message, "error"); b.disabled = false; }
  }));
  $$("#xd-body [data-evdel]").forEach(b => b.addEventListener("click", async () => {
    const body = b.dataset.file ? `'${b.dataset.name}' 을 장부에서 지우고 드라이브 휴지통으로 옮깁니다.` : `'${b.dataset.name}' 항목을 장부에서 지웁니다(파일 없음).`;
    if (!await confirmDlg({ title: "증빙 삭제", body, verb: "삭제", danger: true })) return;
    const row = Number(b.dataset.evdel); const e = (XD.evid || []).find(x => x._row === row);
    try {
      const res = await api("DELETE", `/api/evidence/${row}`, { expect: e ? { 거래번호: e["거래번호"], 증빙번호: e["증빙번호"], 파일명: e["파일명"] } : undefined });
      showAlert(res.warning || "증빙을 삭제했습니다.", res.warning ? "warn" : "ok");
      await load(); await c.rerender();
    } catch (err) { showAlert(err.message, "error"); }
  }));
}

// ---- 설정 패널: 드라이브 ----
async function refreshDriveStatus() {
  try {
    const s = await api("GET", "/api/drive/status");
    $("#drive-status").textContent = s.mock ? "테스트(모의) 모드: 로컬 app/drive_mock 폴더에 저장됩니다."
      : s.expired ? "인증이 만료되었습니다 (테스트 모드 앱은 7일마다 만료). '다시 연결'을 누르세요."
      : s.connected ? "연결됨. 내 드라이브의 '증빙관리' 폴더에 저장됩니다."
      : s.configured ? "OAuth 클라이언트 등록됨. '드라이브 연결'을 눌러 로그인하세요."
      : "OAuth 클라이언트 JSON이 없습니다. 사용 안내의 발급 절차를 따라 업로드하세요.";
    $("#drive-connect").textContent = s.expired || s.connected ? "다시 연결 (브라우저 로그인)" : "드라이브 연결 (브라우저 로그인)";
    $("#drive-connect").disabled = !s.configured || s.mock;
    $("#drive-why").textContent = s.mock ? "" : !s.configured ? "← JSON을 먼저 올리면 연결 버튼이 켜집니다" : "";
    $("#drive-disconnect").disabled = !(s.connected || s.expired) || s.mock;
  } catch (e) { $("#drive-status").textContent = "상태 확인 실패: " + e.message; }
}
$("#drive-secret-btn").addEventListener("click", () => $("#drive-secret").click());
$("#drive-secret").addEventListener("change", async e => {
  const f = e.target.files[0]; if (!f) return; e.target.value = "";
  try { const fd = new FormData(); fd.append("file", f); const res = await fetch("/api/drive/client-secret", { method: "POST", body: fd }); if (!res.ok) throw new Error((await res.json()).detail); setMsg("OAuth 클라이언트를 등록했습니다. 이제 '드라이브 연결'을 누르세요."); refreshDriveStatus(); }
  catch (err) { setMsg("등록 실패: " + err.message, true); }
});
$("#drive-connect").addEventListener("click", async () => {
  setMsg("브라우저에서 구글 로그인 창이 열립니다. 로그인 후 이 화면으로 돌아오세요…");
  $("#drive-connect").disabled = true;
  try { await api("POST", "/api/drive/connect"); setMsg("드라이브가 연결되었습니다."); }
  catch (err) { setMsg("연결 실패: " + err.message, true); }
  finally { refreshDriveStatus(); }
});
$("#drive-disconnect").addEventListener("click", async () => {
  if (!await confirmDlg({ title: "드라이브 연결 해제", body: "토큰을 삭제합니다. 업로드된 파일은 드라이브에 그대로 남습니다.", verb: "연결 해제", danger: true })) return;
  try { await api("POST", "/api/drive/disconnect"); setMsg("연결을 해제했습니다."); } catch (err) { setMsg(err.message, true); }
  refreshDriveStatus();
});

// ================= 지출결의서 (집행 1건 = 1장, 지출완료일 등록 후 · 시안 .impeccable/mocks/voucher/A5_수정형.html) =================
// 재원 현황의 9줄: [결의서 표기, 장부 예산목]. 학생인건비는 따로 두지 않고 인건비 줄에 포함(사용자 결정 2026-10-14). 발생이자는 넣지 않음
const VOUCHER_GROUPS = [
  ["인건비", ["내부인건비(공통)", "외부인건비(공통)"]],
  ["연구시설·장비비", ["연구시설.장비비"]],
  ["연구재료비", ["연구재료비"]],
  ["위탁연구개발비", ["위탁연구개발비"]],
  ["국제공동연구개발비", ["국제공동연구개발비"]],
  ["연구개발부담비", ["연구개발부담비"]],
  ["연구활동비", ["연구활동비"]],
  ["연구수당", ["연구수당"]],
  ["간접비", ["간접비(공통)"]],
];
// 금액 한글: 1,234,567 → "금 일백이십삼만사천오백육십칠 원정". 십·백·천 앞의 1은 읽지 않되, 맨 앞 묶음의 첫 백·천과 1인 만·억 묶음은 '일'을 붙임
function korWon(n) {
  n = Math.round(Number(n) || 0);
  if (!n) return "금 영 원정";
  const neg = n < 0, D = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"], P = ["천", "백", "십", ""], U = ["", "만", "억", "조", "경"];
  const groups = []; let s = String(Math.abs(n));
  while (s.length) { groups.unshift(s.slice(-4)); s = s.slice(0, -4); }
  const words = groups.map((g, gi) => {
    const v = Number(g), u = U[groups.length - 1 - gi];
    if (!v) return "";
    if (v === 1 && u) return "일" + u;
    let w = "", lead = true;
    g.padStart(4, "0").split("").forEach((c, k) => {
      const d = Number(c); if (!d) return;
      const skipOne = d === 1 && P[k] && !(gi === 0 && lead && (P[k] === "천" || P[k] === "백"));
      w += (skipOne ? "" : D[d]) + P[k]; lead = false;
    });
    return w + u;
  });
  return `금 ${neg ? "마이너스 " : ""}${words.join("")} 원정`;
}
const VOUCHER_SIGNERS = ["담당", "매니저", "선임연구원", "센터장"];  // 결재란 칸 (사용자 결정 2026-10-16)
// 결재란 서명 칸에 미리 인쇄하는 이름 (사용자 결정 2026-10-20). 담당은 비움. tag 는 이름 위 작은 글씨
const VOUCHER_SIGNER_NAMES = { "매니저": { name: "오인선" }, "선임연구원": { name: "이진영" }, "센터장": { name: "류지원", tag: "직무대행" } };
const ymdKo = d => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(d || ""); return m ? `${m[1]}년 ${m[2]}월 ${m[3]}일` : ""; };
const vcNum = n => n < 0 ? "−" + fmt(-n) : fmt(n);   // 음수는 U+2212
// 재원 현황: 이 행 위치(원인발생일 순, 같은 날은 행 순 = 집행 표 '예산목 잔액'의 runningBalance 와 같은 순서)까지 누적한 예산목 묶음별 잔액.
// 예산은 이 거래의 원인발생일까지 신청된 예산변동만 (runningBalance 와 같은 기준)
function voucherFund(r) {
  const fund = r["재원"], upTo = x => ((x["원인발생일"] || "").localeCompare(r["원인발생일"] || "") || x._row - r._row) <= 0;
  const execs = activeExec().filter(x => x["재원"] === fund && upTo(x));
  if (isUntrackedFund(fund)) return { rows: [], own: false, before: 0, cur: 0, after: 0, untracked: true };  // 잔액 미관리: 재원 현황 표 대신 안내 한 줄
  if (isPoolFund(fund)) {  // 공금: 예산목 없이 재원 잔액 한 줄 (이 날짜까지의 입금 − 이 거래까지의 집행)
    const cur = r["금액"] || 0, after = budgetUpTo(fund, null, r["원인발생일"]) - execs.reduce((a, x) => a + (x["금액"] || 0), 0);
    return { rows: [{ label: "공금 잔액", own: true, cur, after, before: after + cur }], own: true, before: after + cur, cur, after, pool: true };
  }
  const bal = i => budgetUpTo(fund, i, r["원인발생일"]) - execs.filter(x => x["예산목"] === i).reduce((a, x) => a + (x["금액"] || 0), 0);
  const rows = VOUCHER_GROUPS.map(([label, items]) => {
    const own = items.includes(r["예산목"]), cur = own ? (r["금액"] || 0) : 0, after = items.reduce((a, i) => a + bal(i), 0);
    return { label, own, cur, after, before: after + cur };
  });
  const sum = k => rows.reduce((a, x) => a + x[k], 0);
  return { rows, own: rows.some(x => x.own), before: sum("before"), cur: sum("cur"), after: sum("after") };
}
function voucherModel(r, evid, cfg) {
  const no = execReqNo(r), req = no && DATA.req.find(x => x["품의번호"] === no);
  const fund = DATA.funds.find(f => f["재원코드"] === r["재원"]);
  return {
    r, evid, fund: voucherFund(r),
    org: cfg.LEDGER_ORG || "", contact: String(cfg.REQUEST_CONTACT || "").split("(")[0].trim(),
    title: fund?.["과제명"] || "",
    req: req ? [req["품의번호"], req["품의자"]].filter(Boolean).join(" · ") : no || "-",
  };
}
function voucherHtml(v, withIds) {
  const r = v.r, t = x => esc(x == null ? "" : x), f = v.fund;
  const cur = x => !x.own ? "-" : x.cur > 0 ? "−" + fmt(x.cur) : x.cur < 0 ? "+" + fmt(-x.cur) : "0";
  const kv = (a, b, c, d) => `<tr><th scope="row">${a}</th><td>${t(b)}</td><th scope="row">${c}</th><td>${t(d)}</td></tr>`;
  const full = (a, b, cls = "") => `<tr><th scope="row">${a}</th><td colspan="3"${cls}>${b}</td></tr>`;
  return `<article class="voucher">
  <header class="vc-head">
    <p class="vc-inst">${t(v.org)}</p>
    <table class="vc-sign" aria-label="결재란"><tbody><tr><th scope="row" rowspan="2" class="vc-sign-k">결재</th>${VOUCHER_SIGNERS.map(x => `<th scope="col" class="vc-sign-t">${x}</th>`).join("")}</tr>
      <tr>${VOUCHER_SIGNERS.map(x => { const n = VOUCHER_SIGNER_NAMES[x]; return n ? `<td class="vc-sign-n">${n.tag ? `<small>${n.tag}</small>` : ""}${n.name}</td>` : "<td></td>"; }).join("")}</tr></tbody></table>
    <div class="vc-band"><h2 class="vc-title"${withIds ? ' id="voucher-title"' : ""}>지출결의서</h2></div>
  </header>
  <h3>결의 내역</h3>
  <table class="vc-t vc-kv"><colgroup><col class="l"><col><col class="l"><col></colgroup><tbody>
    <tr><th scope="row">거래번호</th><td class="vc-no">${t(r["거래번호"])}</td><th scope="row">관리번호</th><td>${t(r["관리번호"])}</td></tr>
    ${kv("재원코드", r["재원"], "예산목", r["예산목"])}
    ${full("과제명", t(v.title))}
    ${kv("세목", r["세목"], "세세목", r["세세목"])}
    ${full("거래처", t(r["거래처"]))}
    ${full("적요", t(r["적요"]))}
    ${full("금액", `${vcNum(r["금액"] || 0)}원<span>${esc(korWon(r["금액"]))}</span>`, ' class="vc-amt"')}
    ${kv("결제수단", r["결제수단"], "사용자", r["사용자"])}
    ${full("품의", t(v.req))}
    ${kv("원인발생일", ymdKo(r["원인발생일"]), "지급청구일", ymdKo(r["지급청구일"]))}
    ${kv("지출완료일", ymdKo(r["지출완료일"]), "전산결의일", ymdKo(r["결의일"]))}
    ${full("비고", t(r["비고"]))}
  </tbody></table>
  <h3>증빙 목록</h3>
  <table class="vc-t vc-g vc-ev"><colgroup><col style="width:14mm"><col style="width:40mm"><col></colgroup>
    <thead><tr><th scope="col">번호</th><th scope="col">증빙종류</th><th scope="col">비고</th></tr></thead>
    <tbody>${v.evid.map((e, i) => `<tr><td class="c">${i + 1}</td><td>${t(e["증빙종류"])}</td><td>${t(e["비고"])}</td></tr>`).join("") || '<tr><td colspan="3" class="c">등록된 증빙 없음</td></tr>'}</tbody></table>
  <h3>재원 현황 · ${t(r["재원"])} <small>${f.untracked ? "잔액 미관리 재원" : f.pool ? "공금 · 입금 합계 − 원인발생일 순 누적 집행" : "원인발생일 순 누적"}</small></h3>
  ${f.untracked ? `<table class="vc-t vc-g vc-fund"><tbody><tr><td class="c">이 재원은 재원 출처로만 쓰며 예산·잔액을 관리하지 않습니다.</td></tr></tbody></table>` : `<table class="vc-t vc-g vc-fund"><colgroup><col class="l"><col><col><col></colgroup>
    <thead><tr><th scope="col">예산목</th><th scope="col">집행 전 잔액</th><th scope="col">금회 집행분</th><th scope="col">집행 후 잔액</th></tr></thead>
    <tbody>${f.rows.map(x => `<tr${x.own ? ' class="vc-own"' : ""}><th scope="row">${x.label}</th><td class="num">${vcNum(x.before)}</td><td class="num">${x.own ? `<b>${cur(x)}</b>` : "-"}</td><td class="num">${x.own ? `<b>${vcNum(x.after)}</b>` : vcNum(x.after)}</td></tr>`).join("")}
      ${f.pool ? "" : `<tr class="vc-sum"><th scope="row">합계</th><td class="num">${vcNum(f.before)}</td><td class="num">${cur(f)}</td><td class="num">${vcNum(f.after)}</td></tr>`}</tbody></table>`}
</article>`;
}
let VOUCHER = null, VOUCHER_BTN = null;
async function openVoucher(row, btn) {
  const r = DATA.exec.find(x => x._row === row); if (!r) return;
  if (isCancelled(r)) { showAlert("취소된 집행은 결의서를 만들 수 없습니다.", "warn"); return; }
  if (!r["지출완료일"]) { showAlert(VOUCHER_OFF + ".", "warn"); return; }
  try {
    const [ev, st] = await Promise.all([api("GET", `/api/evidence/${encodeURIComponent(r["거래번호"])}`), api("GET", "/api/settings")]);
    VOUCHER = voucherModel(r, ev.items || [], st.values || {});
  } catch (e) { showAlert("결의서를 만들지 못했습니다: " + e.message, "error"); return; }
  VOUCHER_BTN = btn || null;
  $("#voucher-sheet").innerHTML = voucherHtml(VOUCHER, true); $("#voucher-sheet").scrollTop = 0;
  const miss = [!VOUCHER.title && "과제명"].filter(Boolean);  // 담당자 칸은 2026-10-16 양식에서 빠짐(결재란 '담당' 서명으로 대체)
  $("#voucher-note").hidden = !miss.length;
  $("#voucher-note").textContent = miss.length ? `${miss.join("·")} 칸이 비어 있습니다. 과제명은 [재원] 탭에서 입력합니다.` : "";
  $("#dlg-voucher").showModal(); $("#voucher-print").focus();
}
// 인쇄 사본: [인쇄] 버튼이든 Ctrl+P든 결의서 대화상자가 열려 있으면 결의서만 (A4 세로, 아래 가운데 k/n)
function preparePrintVoucher() {
  if (!VOUCHER || !$("#dlg-voucher").open) return false;
  $("#print-voucher").innerHTML = voucherHtml(VOUCHER, false);
  document.body.classList.add("printing-voucher");
  return true;
}
$("#voucher-close").addEventListener("click", () => $("#dlg-voucher").close());
$("#voucher-print").addEventListener("click", () => { if (preparePrintVoucher()) window.print(); });
$("#dlg-voucher").addEventListener("close", () => {
  // 드로어가 다시 그려졌어도 같은 행의 [결의서] 버튼으로 초점을 돌려줌
  const b = VOUCHER_BTN?.isConnected ? VOUCHER_BTN : VOUCHER && $(`#xd-body [data-act="voucher"][data-row="${VOUCHER.r._row}"]`);
  if (b) b.focus();
});
window.addEventListener("beforeprint", () => { if (!document.body.classList.contains("printing-voucher")) preparePrintVoucher(); });
window.addEventListener("afterprint", () => { if (!document.body.classList.contains("printing-voucher")) return; document.body.classList.remove("printing-voucher"); $("#print-voucher").innerHTML = ""; });

// ================= 증빙 첨부 양식 (증빙 1건 = 1장 · 시안 .impeccable/mocks/voucher/E3_첨부양식.html, 기관명 줄 없음 · 거래처/적요 같은 폭) =================
// 실물 증빙(영수증 등)을 붙이는 A4 한 장: 위 3행 표(증빙번호·증빙종류·금액 / 거래처·적요 / 비고) + 아래 빈 부착란. 집행 단계와 무관하게 출력
let MOUNT = null;   // { items: [증빙 행], i, btn }
function mountHtml(e) {
  const r = DATA.exec.find(x => x["거래번호"] === e["거래번호"]), t = x => esc(x == null ? "" : x);
  const amt = r ? vcNum(r["금액"] || 0) + "원" : "";
  return `<article class="ev-mount">
  <table class="mt-f"><colgroup><col class="c1"><col class="c2"><col class="c3"><col class="c4"><col class="c5"><col class="c6"><col class="c7"><col class="c8"></colgroup><tbody>
    <tr><th scope="row">증빙번호</th><td class="mt-no"><span>${t(e["증빙번호"])}</span></td><th scope="row">증빙종류</th><td colspan="3">${t(e["증빙종류"])}</td><th scope="row">금액</th><td class="mt-num">${t(amt)}</td></tr>
    <tr><th scope="row">거래처</th><td colspan="3" class="mt-vendor" title="${t(r?.["거래처"])}">${t(r?.["거래처"])}</td><th scope="row">적요</th><td colspan="3" class="mt-memo" title="${t(r?.["적요"])}">${t(r?.["적요"])}</td></tr>
    <tr><th scope="row">비고</th><td colspan="7">${t(e["비고"])}</td></tr>
  </tbody></table>
  <section class="mt-frame" aria-label="실물 증빙 부착란"></section>
</article>`;
}
// 증빙번호는 잘리면 안 되는 값: 36mm 칸에 다 들어가도록 글자만 줄임 (10.5pt → 최소 7.5pt, 인쇄 글꼴 차이 여유 4%). 열린 미리보기에서 재서 인쇄 사본에도 같은 크기
function fitMountNo() {
  const td = $("#mount-sheet .mt-no"), span = td?.firstElementChild; if (!span) return "";
  td.style.fontSize = "";
  const cs = getComputedStyle(td), avail = (td.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)) * 0.96;
  for (let pt = 10; span.getBoundingClientRect().width > avail && pt >= 7.5; pt -= 0.5) td.style.fontSize = pt + "pt";
  return td.style.fontSize;
}
function renderMount() {
  const { items, i } = MOUNT, e = items[i], n = items.length;
  $("#mount-sheet").innerHTML = `<div class="mt-page">${mountHtml(e)}</div>`; $("#mount-sheet").scrollTop = 0;
  MOUNT.noSize = fitMountNo();
  $("#mount-no").textContent = e["증빙번호"] ? " · " + e["증빙번호"] : "";
  $("#mount-pos").hidden = n < 2; $("#mount-pos").textContent = `${n}건 중 ${i + 1}번째`;
  $("#mount-prev").hidden = $("#mount-next").hidden = n < 2;
  $("#mount-prev").disabled = i === 0; $("#mount-next").disabled = i === n - 1;
}
function openMount(items, i, btn) {
  if (!items?.length) return;
  MOUNT = { items, i: Math.max(0, Math.min(i || 0, items.length - 1)), btn: btn || null };
  if (!$("#dlg-mount").open) $("#dlg-mount").showModal();   // 먼저 열어야 증빙번호 칸 폭을 잴 수 있음
  renderMount();
  $("#mount-print").focus();
}
function mountStep(d) {
  if (!MOUNT) return;
  const i = MOUNT.i + d; if (i < 0 || i >= MOUNT.items.length) return;
  MOUNT.i = i; renderMount();
  const b = d < 0 ? $("#mount-prev") : $("#mount-next");   // 끝에 닿아 꺼진 버튼에서 초점이 사라지지 않게
  (b.disabled ? (d < 0 ? $("#mount-next") : $("#mount-prev")) : b).focus();
}
// 인쇄 사본: [인쇄] 버튼이든 Ctrl+P든 양식 대화상자가 열려 있으면 지금 보이는 한 장만 (A4 세로 15mm, 쪽 번호 없음)
function preparePrintMount() {
  if (!MOUNT || !$("#dlg-mount").open) return false;
  $("#print-mount").innerHTML = mountHtml(MOUNT.items[MOUNT.i]);
  if (MOUNT.noSize) $("#print-mount .mt-no").style.fontSize = MOUNT.noSize;
  document.body.classList.add("printing-mount");
  return true;
}
$("#mount-close").addEventListener("click", () => $("#dlg-mount").close());
$("#mount-print").addEventListener("click", () => { if (preparePrintMount()) window.print(); });
$("#mount-prev").addEventListener("click", () => mountStep(-1));
$("#mount-next").addEventListener("click", () => mountStep(1));
$("#dlg-mount").addEventListener("close", () => {
  // 드로어가 다시 그려졌어도 같은 증빙의 [양식] 버튼으로 초점을 돌려줌 (업로드 알림에서 열었으면 지금 보던 증빙의 버튼)
  const e = MOUNT?.items[MOUNT.i];
  const b = MOUNT?.btn?.isConnected ? MOUNT.btn : e && $(`#xd-body [data-evmount="${e._row}"]`);
  if (b) b.focus();
});
window.addEventListener("beforeprint", () => { if (!document.body.classList.contains("printing-mount")) preparePrintMount(); });
window.addEventListener("afterprint", () => { if (!document.body.classList.contains("printing-mount")) return; document.body.classList.remove("printing-mount"); $("#print-mount").innerHTML = ""; });
