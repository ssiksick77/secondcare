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
const IDENT = { funds: ["재원코드"], exec: ["거래번호"], req: ["품의번호"], tags: ["태그명"], budget: ["재원", "변경회차", "신청일자"], deposit: ["일자", "거래처", "구분", "금액"] };
const F = k => document.getElementById("f-" + k);
// 단계 ↔ 날짜: 발생=원인발생일, 청구=지급청구일, (보완=수동 표시), 승인=지출완료일, 결의=결의일
const STATUS_LABEL = { 발생: "발생", 청구: "청구", 보완: "보완", 완료: "승인", 결의: "완료" };  // 결의일이 등록되면 '완료'로 표시
const STATUS_HELP = { 발생: "원인발생일만 있음. 다음: 청구(지급청구일)", 청구: "지급청구일 등록됨. 다음: 승인(지출완료일)", 보완: "서류·증빙 보완이 필요하다고 표시한 건 (청구 단계)", 완료: "지출완료일 등록됨(승인). 다음: 결의(결의일)", 결의: "결의일 등록됨, 완료" };
// 상태 열의 다음 단계 버튼: [동작, 라벨, 설명]
const NEXT_STEP = { 발생: ["claim", "청구", "지급청구일을 오늘로 등록"], 청구: ["complete", "승인", "지출완료일을 오늘로 등록"], 보완: ["complete", "승인", "지출완료일을 오늘로 등록 (보완 해제)"], 완료: ["resolve", "결의", "결의일을 오늘로 등록 (마지막 단계)"] };
const DATE_STAGE = { 원인발생일: "발생", 지급청구일: "청구", 지출완료일: "승인", 결의일: "결의" };  // 폼 필드 (예산목 이름에 괄호·점이 있어 CSS 선택자 불가)
const expectOf = (kind, r) => r ? Object.fromEntries((IDENT[kind] || []).map(c => [c, r[c]])) : undefined;

let DATA = null;
const FILTERS = { exec: {}, req: {}, budget: {}, deposit: {} };

// ---------- 열 정의 ----------
const COLS = {
  exec: [
    { k: "거래번호", w: 1 }, { k: "상태", t: "badge" }, { k: "관리번호", minor: true }, { k: "원인발생일", t: "date", label: "날짜" }, { k: "지급청구일", t: "date", hide: true },
    { k: "지출완료일", t: "date", hide: true }, { k: "결의일", t: "date", hide: true }, { k: "재원" }, { k: "예산목" }, { k: "세목" }, { k: "세세목", minor: true },
    { k: "거래처", hide: true }, { k: "적요", t: "title", sub: "거래처" }, { k: "결제수단" }, { k: "금액", t: "num", amt: true }, { k: "예산목 잔액", t: "num", calc: r => runningBalance(r), title: "이 거래까지 반영한 재원·예산목 잔액 (예산현액 − 원인발생일 순 누적 집행). 품의대기는 제외" }, { k: "사용자", minor: true }, { k: "태그" }, { k: "증빙", t: "num", calc: r => evidCount(r), title: "등록된 증빙 파일 수" }, { k: "비고", wrap: true, minor: true },
  ],
  req: [
    { k: "품의번호" }, { k: "상태", t: "badge" }, { k: "원인발생일", t: "date" }, { k: "지출예정일", t: "date" }, { k: "재원" },
    { k: "예산목" }, { k: "세목" }, { k: "세세목" }, { k: "거래처" }, { k: "결제수단" }, { k: "적요", wrap: true },
    { k: "금액", t: "num", amt: true }, { k: "태그" }, { k: "품의자" }, { k: "비고", wrap: true },
  ],
  budget: null, // meta 로드 후 생성
  deposit: [{ k: "일자", t: "date" }, { k: "거래처" }, { k: "구분", t: "badge" }, { k: "금액", t: "num", amt: true }, { k: "적요", wrap: true },
    { k: "사용자" }, { k: "증빙번호" }, { k: "연결거래번호" }, { k: "비고", wrap: true }],
  funds: [{ k: "재원코드" }, { k: "과제명", wrap: true }, { k: "시작일", t: "date" }, { k: "종료일", t: "date" }, { k: "비고", wrap: true }, { k: "인건비예산", t: "num", title: "인건비 화면의 지급처 예산 (비우면 예산목 합계)" }],
  tags: [{ k: "태그명" }, { k: "분류" }, { k: "설명", wrap: true }, { k: "사용건수", t: "num", calc: r => tagUsage(r["태그명"]) }],
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
  const funds = fundOptions();
  const items = DATA.meta.budget_items;
  // 실무 입력 순서: 날짜 → 재원 → 예산목 → 거래처 → 금액 → 적요 → 세목 → 태그 → (부가 정보)
  const common = [
    { k: "원인발생일", type: "date", req: true, hint: "발생 단계 (표의 '날짜')" },
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
    { k: "재원", type: "select", opts: funds, req: true },
    { k: "변경회차", type: "text", req: true, hint: "이월 / 당초 / 1, 2, 3…" },
    { k: "신청일자", type: "date" },
    { k: "변경사유", type: "text", cls: "wide" },
    ...items.map(i => ({ k: i, type: "num" })),
  ];
  if (kind === "deposit") return [
    { k: "일자", type: "date", req: true }, { k: "거래처", type: "datalist", req: true },
    { k: "구분", type: "select", opts: DATA.meta.dep_types, req: true },
    { k: "금액", type: "num", req: true }, { k: "사용자", type: "datalist" }, { k: "증빙번호", type: "text", hint: "영수증·전표 번호" },
    tagField({ dep: "사용", hint: "사용 건의 내부 계정" }), { k: "적요", type: "text", cls: "mid" }, { k: "비고", type: "text", cls: "wide" },
    { k: "_record_exec", type: "check", label: "집행내역에 기록 (선결제 금액을 예산에서 차감)", cls: "wide", onlyNew: true, dep: "적립" },
    { k: "_재원", type: "select", opts: ["", ...funds], label: "재원", dep: "적립", req: "exec" },
    { k: "_예산목", type: "select", opts: ["", ...items], label: "예산목", dep: "적립", req: "exec" },
    { k: "_세목", type: "datalist", list: "세목", label: "세목", dep: "적립" },
    tagField({ k: "_태그", label: "집행 태그", dep: "적립", hint: "집행내역에 붙일 내부 계정" }),
    { k: "연결거래번호", type: "ro" },
  ];
  if (kind === "tags") return [
    { k: "태그명", type: "text", req: true, hint: "쉼표 금지" }, { k: "분류", type: "datalist", list: "분류", hint: "상위 계정" },
    { k: "설명", type: "text", cls: "wide" },
  ];
  if (kind === "funds") return [
    { k: "재원코드", type: "text", req: true, hint: "'-' 없이, 예: AI01" }, { k: "과제명", type: "text", cls: "mid" },
    { k: "시작일", type: "date" }, { k: "종료일", type: "date" }, { k: "비고", type: "text", cls: "wide" },
    { k: "인건비예산", type: "num", hint: "비우면 예산변동의 내부·외부인건비 합계를 사용 (인건비 화면)" },
  ];
}

function fundOptions() {
  const s = new Set(DATA.funds.map(f => f["재원코드"]));
  const payees = new Set((DATA.payee || []).map(p => p["지급처코드"]));  // 외부 지급처(인건비)는 예산 집계에서 제외
  [...DATA.exec, ...DATA.req, ...DATA.budget].forEach(r => r["재원"] && !payees.has(r["재원"]) && s.add(r["재원"]));
  return [...s];
}

// ---------- 데이터 로드 ----------
async function api(method, url, body) {
  const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch { }
    throw new Error(msg);
  }
  return res.json();
}

async function load() {
  try {
    DATA = await api("GET", "/api/all"); RUN_BAL = null;
    COLS.budget = [{ k: "재원" }, { k: "변경회차" }, { k: "신청일자", t: "date" }, { k: "변경사유", wrap: true },
      ...DATA.meta.budget_items.map((i, n) => ({ k: i, t: "num", amt: n === 0 })), { k: "합계", t: "num", calc: r => DATA.meta.budget_items.reduce((a, i) => a + (r[i] || 0), 0) }];
    renderStatus();
    fillSelects();
    fillDatalists();
    renderAll();
  } catch (e) {
    showAlert("불러오기 실패: " + e.message, "error");
  }
}

function renderStatus() {
  const st = $("#file-status");
  st.textContent = (DATA.meta.locked ? "주의: 엑셀에서 열려 있음 (저장 불가) · " : "") + (DATA.meta.formula_count ? `수식 셀 ${DATA.meta.formula_count}개 · ` : "") + "파일 수정 " + DATA.meta.mtime.replace("T", " ");
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
  fill("#dl-거래처", collect(["거래처"]));
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
  if (XD.row != null && !$("#exec-drawer").hidden) renderExecDrawer(false);
  renderDashboard();
  renderList("exec"); renderList("req"); renderList("budget"); renderList("funds"); renderList("deposit"); renderList("tags");
  renderBudgetSummary(); renderDepositSummary();
  if (typeof renderLabor === "function") renderLabor();
}

const SORT = {};  // kind -> {k, dir}
const norm = s => String(s ?? "").toLowerCase().replace(/,/g, "");
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
    const d = r["원인발생일"] || r["일자"] || r["지급월"] || "";
    if (f.year && d.slice(0, 4) !== f.year) return false;
    if (f.month && d.slice(5, 7) !== f.month) return false;
    if (f.unpaid && r["지출완료일"]) return false;
    if (kind === "exec" && QUICK) {
      if (QUICK === "unclaimed" && r["상태"] !== "발생") return false;
      if (QUICK === "fix" && r["상태"] !== "보완") return false;
      if (QUICK === "done" && r["상태"] !== "완료") return false;
      if (QUICK === "resolved" && r["상태"] !== "결의") return false;
      if (QUICK === "noevid" && hasEvidence(r)) return false;
      if (QUICK === "excluded" && !isExcludedExec(r)) return false;
    }
    if (q && !Object.entries(r).some(([k, v]) => !k.startsWith("_") && norm(v).includes(q))) return false;
    return true;
  });
}

function renderList(kind) {
  const cols = COLS[kind].filter(c => !c.hide);  // hide: CSV 에는 포함, 화면에서는 생략
  const rows = (kind === "funds" || kind === "tags") ? [...DATA[kind]] : filtered(kind);
  const defKey = { exec: "원인발생일", req: "원인발생일", deposit: "일자", labor: "지급월", salary: "시작월", ladj: "월" }[kind];
  const sort = SORT[kind] || (defKey ? { k: defKey, dir: -1 } : null);
  if (sort) {
    const col = cols.find(c => c.k === sort.k);
    const val = r => col?.calc ? col.calc(r) : r[sort.k];
    rows.sort((a, b) => { const va = val(a), vb = val(b); const c = (typeof va === "number" && typeof vb === "number") ? va - vb : String(va ?? "").localeCompare(String(vb ?? ""), "ko"); return (c || (a._row - b._row)) * sort.dir; });
  }
  const table = $(`#${kind}-table`);
  const showMinor = kind === "exec" && localStorage.getItem("ledger-exec-minor") === "1";
  table.classList.toggle("show-minor", showMinor);
  const minorCls = c => c.minor ? " col-minor" : "";
  const SORT_SVG = d => `<span class="sort-ind" aria-hidden="true"><svg viewBox="0 0 10 10"><path d="${d > 0 ? "M2 7l3-4 3 4" : "M2 3l3 4 3-4"}" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>`;
  const head = `<thead><tr>${cols.map(c => `<th class="sortable${c.t === "num" ? " num" : ""}${c.amt ? " amt" : ""}${minorCls(c)}" data-col="${esc(c.k)}" data-sort="${esc(c.k)}" title="${esc(c.title || "클릭하여 정렬")}" aria-sort="${sort && sort.k === c.k ? (sort.dir > 0 ? "ascending" : "descending") : "none"}">${esc(c.label || c.k)}${sort && sort.k === c.k ? SORT_SVG(sort.dir) : ""}</th>`).join("")}<th class="actions">작업</th></tr></thead>`;
  const body = rows.length ? rows.map(r => {
    const tds = cols.map(c => {
      const v = c.calc ? c.calc(r) : r[c.k];
      const td = html => html.replace(/^<td(?=[\s>])/, `<td data-col="${esc(c.k)}"`);
      return td(cellHtml(c, r, v));
    }).join("");
    return rowHtml(r, tds);
  }).join("") : `<tr><td class="empty" colspan="${cols.length + 1}">표시할 항목이 없습니다.</td></tr>`;
  function cellHtml(c, r, v) {
      if (c.t === "num") return `<td class="num${c.amt ? " amt" : ""}${minorCls(c)}${typeof v === "number" && v < 0 ? " neg" : ""}">${v == null ? '<span class="muted" title="예산 미등록 재원">-</span>' : fmt(v)}</td>`;
      if (c.t === "date" && v && (kind === "exec" || kind === "req" || kind === "budget" || kind === "deposit")) {
        return `<td title="${esc(v)}">${esc(mmdd(v))}</td>`;  // 내역 탭은 MM/DD, 전체 날짜는 툴팁
      }
      if (c.t === "badge") {
        const nx = kind === "exec" ? NEXT_STEP[v] : null;
        const fixBtn = kind === "exec" && (v === "청구" || v === "보완") ? `<button type="button" class="fixtg${v === "보완" ? " on" : ""}" data-act="xact" data-action="${v === "보완" ? "unfix" : "fix"}" data-row="${r._row}" title="${v === "보완" ? "보완 해제" : "보완 필요로 표시"}" aria-label="${v === "보완" ? "보완 해제" : "보완 필요로 표시"}" aria-pressed="${v === "보완"}"><svg viewBox="0 0 12 12" aria-hidden="true" focusable="false"><path d="M6 2.2v4.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="6" cy="9.4" r="1" fill="currentColor"/></svg></button>` : "";
        return `<td class="st-cell"><span class="badge ${esc(v)}" title="${esc(STATUS_HELP[v] || "")}">${esc(STATUS_LABEL[v] || v)}</span>${fixBtn}${nx ? `<button type="button" class="next" data-act="xact" data-action="${nx[0]}" data-row="${r._row}" title="다음 단계로: ${esc(nx[1])} (${esc(nx[2])})" aria-label="다음 단계로: ${esc(nx[1])}"><svg viewBox="0 0 12 12" aria-hidden="true" focusable="false"><path d="M2.5 6.5l2.5 2.5 4.5-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>` : ""}</td>`;
      }
      if (c.t === "title") return `<td class="tit" title="${esc([v, r[c.sub]].filter(Boolean).join(" · "))}"><div class="t">${esc(v || "")}</div>${r[c.sub] ? `<div class="s">${esc(r[c.sub])}</div>` : ""}</td>`;
      if (kind === "exec" && c.k === "거래번호") return `<td class="nowrap">${esc(v)}${originBadge(r)}</td>`;
      return `<td class="${c.wrap ? "wrap" : ""}${minorCls(c)}"${c.wrap && v ? ` title="${esc(v)}"` : ""}>${esc(v)}</td>`;
  }
  function rowHtml(r, tds) {
    const extra = kind === "req" && r["상태"] === "대기"
      ? `<button type="button" class="btn btn-sm" data-act="toexec" data-row="${r._row}">집행전환</button>`
      : kind === "labor" ? (r["상태"] === "예정" ? `<button type="button" class="btn btn-sm" data-labor="confirm" data-row="${r._row}" title="지급일을 입력하고 확정 (집행내역에 기록)">확정</button>` : `<button type="button" class="btn btn-sm" data-labor="unconfirm" data-row="${r._row}" title="예정으로 되돌리고 연결 집행 삭제">확정 취소</button>`) : "";
    const editBtn = kind === "labor" && r["상태"] === "확정" ? "" : `<button type="button" class="btn btn-sm" data-act="edit" data-kind="${kind}" data-row="${r._row}">수정</button>`;
    return `<tr data-kind="${kind}" data-row="${r._row}" class="${kind === "exec" && XD.row === r._row ? "selected" : ""}${kind === "exec" && r["상태"] === "보완" ? " row-alert" : ""}">${tds}<td class="actions">${extra}${editBtn}<button type="button" class="btn btn-sm btn-danger" data-act="del" data-kind="${kind}" data-row="${r._row}">삭제</button></td></tr>`;
  }
  let foot = "";
  if (rows.length && (kind === "exec" || kind === "req" || kind === "deposit" || kind === "labor")) {
    const sum = rows.reduce((a, r) => a + (r["금액"] || 0), 0);
    foot = `<tfoot><tr class="total">${cols.map(c => c.k === "금액" ? `<td class="num amt${minorCls(c)}">${fmt(sum)}</td>` : `<td class="${minorCls(c).trim()}">${c === cols[0] ? `합계 ${rows.length}건` : ""}</td>`).join("")}<td class="actions"></td></tr></tfoot>`;
  }
  table.innerHTML = head + `<tbody>${body}</tbody>` + foot;
  table.querySelectorAll("th.sortable").forEach(th => th.addEventListener("click", () => {
    const k = th.dataset.sort; const cur = SORT[kind] || (defKey ? { k: defKey, dir: -1 } : null);
    SORT[kind] = cur && cur.k === k ? { k, dir: -cur.dir } : { k, dir: 1 }; renderList(kind);
  }));
  const wrap = table.closest(".table-wrap"); if (wrap) { wrap.classList.toggle("empty", rows.length === 0); wrap.classList.toggle("scrollable", table.scrollWidth > wrap.clientWidth + 4); }

  if (kind === "exec" || kind === "req" || kind === "labor") {
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
  $$(".subtabs [role=tab]").forEach(b => {
    const on = b.id === "sub-" + name;
    b.setAttribute("aria-selected", on);
    $("#" + b.getAttribute("aria-controls")).hidden = !on;
  });
  try { localStorage.setItem("ledger-subtab", name); } catch { }
}
$$(".subtabs [role=tab]").forEach(b => b.addEventListener("click", () => switchSubTab(b.id.replace("sub-", ""))));
try { const st = localStorage.getItem("ledger-subtab"); if (st && $("#sub-" + st)) switchSubTab(st); } catch { }

function renderTagDashboard(fund, year) {
  const linked = new Set(DATA.deposit.map(r => r["연결거래번호"]).filter(Boolean));
  const inYear = d => !year || (d || "").startsWith(year);
  const rows = DATA.exec.filter(r => !linked.has(r["거래번호"]) && (!fund || r["재원"] === fund) && inYear(r["원인발생일"]))
    .map(r => ({ tag: r["태그"], d: r["원인발생일"], amt: r["금액"] || 0, src: "exec" }));
  if (!fund) rows.push(...DATA.deposit.filter(r => r["구분"] === "사용" && inYear(r["일자"])).map(r => ({ tag: r["태그"], d: r["일자"], amt: r["금액"] || 0, src: "dep" })));
  $("#tag-note").textContent = (fund ? "재원 필터 적용 중: 적립금 사용 건(재원 없음)은 제외됩니다. " : "집행내역(적립 선결제 건 제외) + 적립금 사용 건. ")
    + (year ? `${year}년 기준.` : "전체 기간.");
  {
    const execAll = DATA.exec.filter(r => (!fund || r["재원"] === fund) && inYear(r["원인발생일"])).reduce((a, r) => a + (r["금액"] || 0), 0);
    const linkedAmt = DATA.exec.filter(r => linked.has(r["거래번호"]) && (!fund || r["재원"] === fund) && inYear(r["원인발생일"])).reduce((a, r) => a + (r["금액"] || 0), 0);
    const depUse = fund ? 0 : DATA.deposit.filter(r => r["구분"] === "사용" && inYear(r["일자"])).reduce((a, r) => a + (r["금액"] || 0), 0);
    $("#tag-recon").textContent = `조정: 결의 집행액 ${fmt(execAll)} − 적립 선결제 ${fmt(linkedAmt)} + 적립금 사용 ${fmt(depUse)} = 태그 집계 ${fmt(execAll - linkedAmt + depUse)}원`;
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
  const funds = fund ? [fund] : fundOptions();

  // 연도 필터는 집행·품의에 적용 (예산은 연도 개념 없이 재원 기준). 월을 고르면 '당월'과 '누계(연초~당월)'를 함께 표시
  const inYear = r => !year || (r["원인발생일"] || "").startsWith(year);
  const upTo = r => !month || (r["원인발생일"] || "").slice(5, 7) <= month;
  const inMonth = r => month && (r["원인발생일"] || "").slice(5, 7) === month;
  // 잔액·가용잔액·집행률은 파일 전체 기준(sa), 연·월 필터는 '집행액'(s)·'M월 집행'(sm) 열에만 적용. 대기 품의는 날짜 무관 전부 차감 (2026-10-13 결정)
  const execsAll = DATA.exec.filter(r => !fund || r["재원"] === fund);
  const execs = execsAll.filter(r => inYear(r) && upTo(r));
  const reqs = DATA.req.filter(r => r["상태"] === "대기" && (!fund || r["재원"] === fund));
  const budgets = DATA.budget.filter(r => !fund || r["재원"] === fund);

  const cell = () => ({ b: 0, s: 0, sm: 0, sa: 0, p: 0 });
  const m = {};
  funds.forEach(f => { m[f] = {}; items.forEach(i => m[f][i] = cell()); });
  budgets.forEach(r => m[r["재원"]] && items.forEach(i => m[r["재원"]][i].b += r[i] || 0));
  const excluded = [];  // 재원 목록 밖(외부 지급처 인건비 등)·예산목 목록 밖 집행: 예산 집계에서 제외
  execsAll.forEach(r => { const c = m[r["재원"]]?.[r["예산목"]]; if (!c) { if (inYear(r) && upTo(r)) excluded.push(r); return; } c.sa += r["금액"] || 0; if (inYear(r) && upTo(r)) { c.s += r["금액"] || 0; if (inMonth(r)) c.sm += r["금액"] || 0; } });
  reqs.forEach(r => m[r["재원"]]?.[r["예산목"]] && (m[r["재원"]][r["예산목"]].p += r["금액"] || 0));
  const add = (t, c) => { t.b += c.b; t.s += c.s; t.sm += c.sm; t.sa += c.sa; t.p += c.p; };

  // 카드
  const tot = cell();
  funds.forEach(f => items.forEach(i => add(tot, m[f][i])));
  const unpaid = execs.filter(r => !r["지출완료일"]).length;
  const itemCards = items.map(i => { const c = cell(); funds.forEach(f => add(c, m[f][i])); return [i, c]; })
    .filter(([, c]) => c.b || c.sa || c.p);
  $("#dash-cards").innerHTML = itemCards.length ? itemCards.map(([i, c]) => {
    const avail = c.b - c.sa - c.p, rate = c.b ? c.sa / c.b : null, used = c.b ? Math.min(1, (c.sa + c.p) / c.b) : 1;
    const bar = c.b ? `<div class="bar" aria-hidden="true"><i class="${c.sa > c.b ? "over" : ""}" style="width:${Math.min(100, c.sa / c.b * 100).toFixed(1)}%"></i>${c.p ? `<i class="p" style="left:${Math.min(100, c.sa / c.b * 100).toFixed(1)}%;width:${Math.max(0, (used - Math.min(1, c.sa / c.b)) * 100).toFixed(1)}%"></i>` : ""}</div>` : "";
    return `<div class="card" role="listitem" title="${esc(i)}: 예산현액 ${fmt(c.b)} · 집행 ${fmt(c.sa)}${c.p ? ` · 품의대기 ${fmt(c.p)}` : ""} · 가용잔액 ${fmt(avail)}"><div class="k">${esc(i)}</div>${c.b ? `<div class="v${avail < 0 ? " neg" : ""}">${fmt(avail)}</div>` : `<div class="v nobudget" title="예산변동에 이 예산목의 예산을 입력하면 가용잔액이 계산됩니다">예산 미입력</div>`}<div class="sub"><span>집행 ${fmt(c.sa)}${c.p ? ` <span class="muted">+대기 ${fmt(c.p)}</span>` : ""}</span><span>${rate == null ? "예산 없음" : pct(rate)}</span></div>${bar}</div>`;
  }).join("") : `<div class="card empty-card"><div class="k">예산목별 가용잔액</div><div class="v">-</div><div class="sub"><span>${DATA.funds.length ? "예산·집행 데이터가 없습니다" : "재원을 먼저 등록하세요"}</span></div></div>`;
  const exAmt = excluded.reduce((a, r) => a + (r["금액"] || 0), 0);
  $("#dash-note").innerHTML = esc((year ? (month ? `${year}년 1월~${parseInt(month)}월 누계 · ` : `${year}년 · `) : "전체 기간 · ") + `예산현액 ${fmt(tot.b)} · 집행 ${fmt(tot.s)}${month ? ` (${parseInt(month)}월 ${fmt(tot.sm)})` : ""} · 집행률 ${tot.b ? pct(tot.sa / tot.b) : "-"} · 품의대기 ${fmt(tot.p)} (${reqs.length}건) · 가용잔액 ${tot.b ? fmt(tot.b - tot.sa - tot.p) : "예산 미입력"} · 미완료 ${unpaid}건`)
    + (excluded.length ? ` · <button type="button" class="link" data-act="show-excluded" title="재원 목록에 없는 지급처(외부 인건비 등)나 예산목 목록 밖의 집행. 집행내역·태그 집계에는 포함되지만 예산 집계에서는 제외">집계 제외 ${excluded.length}건 ${fmt(exAmt)}원</button>` : "");
  $("#dash-defs").innerHTML = `칸의 큰 숫자 = 가용잔액 = 예산현액 − 집행(파일 전체) − 품의대기(날짜 무관, 선택한 재원 합산) · 막대 = 집행률(회색은 품의대기) · 예산현액 = 재원별 이월+당초+변경 합계 · 집행액 열만 연·월 필터(원인발생일) 적용 · 잔액 = 예산현액 − 집행(전체) · 미완료 = 지출완료일 없는 집행 건`;

  // 표
  const cols = month ? ["예산현액", `${parseInt(month)}월 집행`, "누계 집행", "잔액", "집행률", "품의대기", "가용잔액"] : ["예산현액", "집행액", "잔액", "집행률", "품의대기", "가용잔액"];
  const th = `<thead><tr><th>재원</th><th>예산목</th>${cols.map(c => `<th class="num${c === "예산현액" ? " amt" : ""}">${c}</th>`).join("")}</tr></thead>`;
  const line = (f, i, c, cls) => `<tr class="${cls}"><td>${cls === "total" ? esc(f) : ""}</td><td>${esc(i)}</td><td class="num amt">${fmt(c.b)}</td>${month ? `<td class="num">${fmt(c.sm)}</td>` : ""}<td class="num">${fmt(c.s)}</td><td class="num ${c.b && c.b - c.sa < 0 ? "neg" : ""}">${c.b ? fmt(c.b - c.sa) : '<span class="muted" title="예산 미입력">-</span>'}</td><td class="num">${pct(c.b ? c.sa / c.b : null)}</td><td class="num">${fmt(c.p)}</td><td class="num ${c.b && c.b - c.sa - c.p < 0 ? "neg" : ""}">${c.b ? fmt(c.b - c.sa - c.p) : '<span class="muted" title="예산 미입력">-</span>'}</td></tr>`;
  let body = "";
  DASH_ROWS = [];
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
$("#dash-month").addEventListener("change", renderDashboard);
$$("[data-csv]").forEach(b => b.addEventListener("click", () => {
  const kind = b.dataset.csv; const cols = COLS[kind].filter(c => !c.calc).map(c => c.k); const rows = filtered(kind).map(r => cols.map(k => k === "상태" ? (STATUS_LABEL[r[k]] || r[k]) : r[k]));
  if (!rows.length) { showAlert("저장할 행이 없습니다.", "warn"); return; }
  downloadCSV(`${{ exec: "집행내역", req: "품의내역", labor: "인건비지급" }[kind] || kind}_${today()}.csv`, cols, rows);
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
  const max = Math.max(1, ...totals, cumEnd, showBudget ? budget : 0) * 1.15;  // 최대 막대 위 값 라벨 여유
  const W = 720, H = 248, padL = 70, padB = 28, padT = 20;
  const man = max >= 2e4;  // 축 표기 통일: 만원 또는 원
  const tick = v => man ? (v / 1e4).toFixed(v / 1e4 >= 10 ? 0 : 1).replace(/\.0$/, "") : fmt(Math.round(v));
  const bw = (W - padL - 10) / Math.max(1, months.length);
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="월별 집행 추이 막대 그래프">`;
  let lastLabel = null;
  for (let g = 0; g <= 4; g++) {
    const y = padT + (H - padT - padB) * (1 - g / 4);
    const label = tick(max * g / 4);
    svg += `<line x1="${padL}" x2="${W - 10}" y1="${y}" y2="${y}" stroke="#E7EAEE"/>` + (label !== lastLabel ? `<text x="${padL - 6}" y="${y + 4}" font-size="10" text-anchor="end" fill="#5A6270">${label}</text>` : "");
    lastLabel = label;
  }
  svg += `<text x="${W - 10}" y="${padT - 6}" font-size="10" text-anchor="end" fill="#5A6270">단위: ${man ? "만원" : "원"}${budget > 0 && !showBudget ? ` · 예산현액 ${fmt(budget)}원` : ""}</text>`;
  const Y = v => H - padB - (v / max) * (H - padT - padB);
  if (showBudget) svg += `<line x1="${padL}" x2="${W - 10}" y1="${Y(budget)}" y2="${Y(budget)}" stroke="#B3261E" stroke-width="1" stroke-dasharray="4 3"/><text x="${padL + 4}" y="${Y(budget) - 3}" font-size="9" fill="#B3261E">예산현액 ${man ? tick(budget) : fmt(budget)}</text>`;
  months.forEach((mo, i) => {
    let y0 = H - padB;
    series.forEach((s, si) => {
      const h = (s[i] / max) * (H - padT - padB);
      if (h > 0) { svg += `<rect x="${padL + i * bw + bw * .15}" y="${y0 - h}" width="${bw * .7}" height="${h}" fill="${PALETTE[si % PALETTE.length]}"><title>${esc(funds[si])} ${mo}: ${fmt(s[i])}원</title></rect>`; y0 -= h; }
    });
    if (totals[i] > 0) svg += `<text x="${padL + i * bw + bw / 2}" y="${y0 - 4}" font-size="9" text-anchor="middle" fill="#1E2124">${man ? tick(totals[i]) : fmt(totals[i])}</text>`;
    svg += `<text x="${padL + i * bw + bw / 2}" y="${H - 8}" font-size="10" text-anchor="middle" fill="#5A5C60">${year ? parseInt(mo.slice(5)) + "월" : esc(mo)}</text>`;
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
  const legend = `<div class="legend">${funds.map((f, i) => `<span><i style="background:${PALETTE[i % PALETTE.length]}"></i>${esc(f)}</span>`).join("")}<span><i style="background:#1F3A93;height:2px;vertical-align:3px"></i>누적 집행</span>${showBudget ? `<span><i style="background:#B3261E;height:2px;vertical-align:3px"></i>예산현액</span>` : ""}</div>`;
  $("#dash-chart").innerHTML = svg + legend;
}

// ---------- 입력 대화상자 ----------
const LAST = {};  // 종류별 직전 입력값 (연속 입력용)
function lastDefaults(kind) {
  try { return JSON.parse(sessionStorage.getItem("ledger-last-" + kind) || "{}"); } catch { return {}; }
}
function rememberLast(kind, rec) {
  const keep = { exec: ["재원", "예산목", "사용자"], req: ["재원", "예산목", "품의자", "결제수단"], deposit: ["거래처", "사용자"], budget: ["재원"] }[kind] || [];  // 날짜는 '저장 후 계속' 안에서만 유지
  const o = {}; keep.forEach(k => { if (rec[k]) o[k] = rec[k]; });
  try { sessionStorage.setItem("ledger-last-" + kind, JSON.stringify(o)); } catch { }
}
function openForm(kind, row, preset, opts = {}) {
  const rec = row != null ? DATA[kind].find(r => r._row === row) : null;
  const fields = formFields(kind).filter(f => !(f.onlyNew && rec));
  const titles = { exec: "집행", req: "품의", budget: "예산 변동", funds: "재원", deposit: "적립금", tags: "태그", ...(typeof LABOR_TITLES !== "undefined" ? LABOR_TITLES : {}) };
  $("#dlg-title").textContent = opts.title || ((rec ? "수정 - " : "추가 - ") + titles[kind]);
  $("#dlg-error").hidden = true; $("#dlg-error").classList.remove("info");
  $("#dlg-save-more").hidden = !!rec || !!opts.convertRow || !["exec", "req", "deposit", "budget", "tags", "labor", "salary", "people"].includes(kind);
  const tagDefault = DATA.tags.some(t => t["태그명"] === "적립금") ? "적립금" : "";
  const defaults = { 원인발생일: today(), 일자: today(), 상태: "대기", 구분: "적립", _태그: tagDefault, 재원: FILTERS[kind]?.["재원"] || "", ...(typeof laborDefaults === "function" ? laborDefaults(kind) : {}), ...lastDefaults(kind), ...(preset || {}) };
  $("#dlg-fields").innerHTML = fields.map(f => {
    const v = rec ? (rec[f.k] ?? "") : (defaults[f.k] ?? "");
    const id = "f-" + f.k;
    const lab = `${esc(f.label || f.k)}${f.req === true ? ' <span class="req" aria-hidden="true">*</span>' : ""}`;
    let input;
    if (f.type === "check") return `<label class="${f.cls || ""} chk" for="${id}" data-dep="${esc(f.dep || "")}"><input id="${id}" name="${esc(f.k)}" type="checkbox"> ${lab}</label>`;
    if (f.type === "ro") input = `<input id="${id}" name="${esc(f.k)}" type="text" value="${esc(v || "(자동)")}" readonly tabindex="-1">`;
    else if (f.type === "select" && f.groups) input = `<select id="${id}" name="${esc(f.k)}"><option value="">(선택)</option>${(v && !f.opts.includes(v)) ? `<option value="${esc(v)}" selected>${esc(v)} (목록 외)</option>` : ""}${Object.entries(f.groups).map(([g, names]) => `<optgroup label="${esc(g)}">${names.map(o => `<option value="${esc(o)}"${o === v ? " selected" : ""}>${esc(o)}</option>`).join("")}</optgroup>`).join("")}</select>`;
    else if (f.type === "select") {
      const opts = f.opts.includes("") ? f.opts : ["", ...f.opts];  // 명시적 선택 강제
      const extra = (v !== "" && v != null && !opts.includes(v)) ? `<option value="${esc(v)}" selected>${esc(v)} (목록 외)</option>` : "";
      input = `<select id="${id}" name="${esc(f.k)}"${f.req ? " required" : ""}>${opts.map(o => `<option value="${esc(o)}"${o === v ? " selected" : ""}>${esc(o || "(선택)")}</option>`).join("")}${extra}</select>`;
    }
    else if (f.type === "date") input = `<input id="${id}" name="${esc(f.k)}" type="date" value="${esc(v)}"${f.req ? " required" : ""}>`;
    else if (f.type === "month") input = `<input id="${id}" name="${esc(f.k)}" type="month" value="${esc(v)}"${f.req ? " required" : ""}>`;
    else if (f.type === "num") input = `<input id="${id}" name="${esc(f.k)}" type="text" inputmode="numeric" class="num-input" value="${v === "" || v == null ? "" : fmt(v)}"${f.req ? " required" : ""} placeholder="0">`;
    else if (f.type === "datalist") input = `<input id="${id}" name="${esc(f.k)}" type="text" list="dl-${esc(f.list || (f.k === "품의자" ? "사용자" : f.k))}" value="${esc(v)}" autocomplete="off">`;
    else input = `<input id="${id}" name="${esc(f.k)}" type="text" value="${esc(v)}"${f.req ? " required" : ""}>`;
    return `<label class="${f.cls || ""}" for="${id}" data-dep="${esc(f.dep || "")}"><span class="lab">${lab}${f.hint ? ` <small>(${esc(f.hint)})</small>` : ""}</span>${input}</label>`;
  }).join("");
  syncDepFields();
  if (kind === "exec" && rec) { const o = execOrigin(rec); if (o?.locked) { LOCKED_COLS.forEach(k => { const el = F(k); if (el) { el.readOnly = true; el.setAttribute("aria-readonly", "true"); if (el.tagName === "SELECT") el.dataset.lock = el.value; el.classList.add("locked"); el.title = `${o.kind} 연결 행: 원본에서만 변경`; } }); $("#dlg-error").textContent = `${o.label} 에서 생긴 집행입니다. 재원·예산목·금액·거래처·원인발생일은 원본에서 처리하고, 여기서는 세목·태그·관리번호·날짜·비고만 바꿀 수 있습니다.`; $("#dlg-error").hidden = false; $("#dlg-error").classList.add("info"); } }
  const dlg = $("#dlg");
  dlg.dataset.kind = kind; dlg.dataset.row = row ?? ""; dlg.dataset.convert = opts.convertRow ?? "";
  if (kind === "budget" && !rec && !preset?.["변경회차"]) {  // 다음 회차 자동 제안
    const sel = F("재원"); const fill = async () => { if (!sel.value) return; try { const r = await api("GET", `/api/budget/next-round?fund=${encodeURIComponent(sel.value)}`); if (!F("변경회차").value) F("변경회차").value = r.round; } catch { } };
    sel.addEventListener("change", () => { F("변경회차").value = ""; fill(); }); fill();
  }
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
$("#dlg").addEventListener("cancel", e => {  // Esc
  if (formDirty() && !confirm("입력한 내용을 버리고 닫을까요?")) e.preventDefault();
});

// 구분 값에 따라 종속 필드 표시 (적립금 폼)
function syncDepFields() {
  const sel = $("#f-구분"); if (!sel) return;
  const chk = $("#f-_record_exec");
  $$("#dlg-fields label[data-dep]").forEach(l => {
    if (!l.dataset.dep) return;
    const show = sel.value === l.dataset.dep && (l.classList.contains("chk") || (chk && chk.checked));
    l.hidden = !show;
  });
}
$("#dlg-fields").addEventListener("change", e => { if (e.target.dataset.lock !== undefined && e.target.value !== e.target.dataset.lock) { e.target.value = e.target.dataset.lock; showAlert("연결된 집행이라 이 값은 원본 화면에서만 바꿀 수 있습니다.", "warn"); } if (e.target.id === "f-구분" || e.target.id === "f-_record_exec") syncDepFields(); });

$("#dlg-form").addEventListener("submit", async e => {
  e.preventDefault();
  const dlg = $("#dlg");
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
    if (f.type === "num") { v = v.replace(/[,\s원]/g, ""); if (v && isNaN(Number(v))) { invalid.push(`${f.label || f.k}(숫자 아님)`); mark(); } v = v === "" ? "" : Number(v); }
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
  const more = dlg.dataset.saveMore === "1"; dlg.dataset.saveMore = "";
  const convertRow = dlg.dataset.convert ? Number(dlg.dataset.convert) : null;
  const saveBtn = $("#dlg-save"), moreBtn = $("#dlg-save-more");
  try {
    saveBtn.disabled = true; moreBtn.disabled = true; saveBtn.textContent = "저장 중…";
    let saved;
    if (convertRow != null) {
      const req = DATA.req.find(x => x._row === convertRow);
      saved = await api("POST", `/api/req/${convertRow}/to-exec`, { extra: rec, expect: expectOf("req", req) });
    } else {
      saved = row ? await api("PUT", `/api/${kind}/${row}`, { rec, expect: expectOf(kind, DATA[kind].find(x => x._row === Number(row))) }) : await api("POST", `/api/${kind}`, rec);
    }
    const cb = DLG_ON_SAVED; DLG_ON_SAVED = null;
    if (!row) rememberLast(kind, rec);
    const no = saved["거래번호"] || saved["품의번호"] || saved["재원코드"] || saved["태그명"] || "";
    dlg.dataset.initial = ""; dlg.close();
    showAlert(`${no ? no + " " : ""}저장했습니다.` + (convertRow != null ? " (품의 → 집행 전환 완료)" : ""), "ok");
    await load();
    if (cb) cb(saved);
    if (more) { const carry = {}; ["원인발생일", "일자", "귀속월", "지급월", "이름"].forEach(k => { if (rec[k]) carry[k] = rec[k]; }); openForm(kind, null, { ...carry, 거래처: "", 금액: "", 적요: "", 세목: "", 세세목: "", 관리번호: "", 비고: "", 증빙번호: "", 결의일: "", 지출완료일: "", 지급청구일: "" }); }
  } catch (err) {
    showFormError(err.message); showAlert("저장 실패: " + err.message, "error");
  } finally { saveBtn.disabled = false; moreBtn.disabled = false; saveBtn.textContent = "저장"; }
});
$("#dlg-save-more").addEventListener("click", () => { $("#dlg").dataset.saveMore = "1"; $("#dlg-form").requestSubmit(); });

// 가용잔액 = 예산현액 − 집행(파일 전체) − 대기 품의(날짜 무관). 대시보드·집행내역 열·저장 경고가 모두 이 함수를 쓴다 (2026-10-13 결정).
// excludeReq / excludeExec: 품의→집행 전환 중인 품의, 수정 중인 집행 행은 빼고 계산 (이중 차감 방지)
// 거래별 누적 잔액: 같은 재원·예산목의 집행을 원인발생일(같으면 행 순)으로 쌓아 "이 거래까지 반영한 뒤" 남는 예산. 예산 미입력이면 null
let RUN_BAL = null;
function runningBalance(r) {
  if (!RUN_BAL) {
    RUN_BAL = new Map();
    const groups = {};
    DATA.exec.forEach(x => { const k = x["재원"] + "" + x["예산목"]; (groups[k] = groups[k] || []).push(x); });
    Object.values(groups).forEach(list => {
      const f = list[0]["재원"], i = list[0]["예산목"];
      const b = DATA.budget.filter(x => x["재원"] === f).reduce((a, x) => a + (x[i] || 0), 0);
      list.sort((a, c) => (a["원인발생일"] || "").localeCompare(c["원인발생일"] || "") || a._row - c._row);
      let acc = 0; list.forEach(x => { acc += x["금액"] || 0; RUN_BAL.set(x._row, b ? b - acc : null); });
    });
  }
  return RUN_BAL.get(r._row) ?? null;
}
function availableBudget(fund, item, opts = {}) {
  if (!fund || !item) return null;
  const b = DATA.budget.filter(r => r["재원"] === fund).reduce((a, r) => a + (r[item] || 0), 0);
  if (!b) return null;  // 예산 미입력(재원 또는 예산목)은 '-' 로 표시하고 경고 생략 (대시보드 '예산 미입력'과 동일 기준)
  const s = DATA.exec.filter(r => r["재원"] === fund && r["예산목"] === item && r._row !== opts.excludeExec).reduce((a, r) => a + (r["금액"] || 0), 0);
  const p = DATA.req.filter(r => r["재원"] === fund && r["예산목"] === item && r["상태"] === "대기" && r._row !== opts.excludeReq).reduce((a, r) => a + (r["금액"] || 0), 0);
  return b - s - p;
}
let DLG_ON_SAVED = null;
$("#dlg-cancel").addEventListener("click", () => { if (formDirty() && !confirm("입력한 내용을 버리고 닫을까요?")) return; DLG_ON_SAVED = null; $("#dlg").dataset.initial = ""; $("#dlg").close(); });
$("#dlg").addEventListener("close", () => { DLG_ON_SAVED = null; });
function showFormError(msg) { const p = $("#dlg-error"); p.textContent = msg; p.hidden = false; }

// 금액 입력 자동 쉼표 (입력 중 캐럿 이동을 막기 위해 포커스를 벗어날 때만)
document.addEventListener("focusout", e => {
  if (!e.target.classList?.contains("num-input")) return;
  const raw = e.target.value.replace(/[^\d.-]/g, "");
  if (raw === "" || raw === "-") return;
  const n = Number(raw); if (isNaN(n)) return;
  e.target.value = n.toLocaleString("ko-KR");
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
    : (kind === "deposit" ? `${r?.["일자"]} ${r?.["거래처"]} ${r?.["구분"]} ${fmt(r?.["금액"])}원` : `${r?.["재원"]} ${r?.["변경회차"]}회차`);
  if (!await confirmDlg({ title: "삭제", body: `${label}\n\n삭제 직후 토스트의 '되돌리기'로 복구할 수 있습니다. 그 뒤에는 app/backup 폴더의 백업 파일로만 복원됩니다.`, verb: "삭제", danger: true })) return;
  try { await api("DELETE", `/api/${kind}/${row}`, { expect: expectOf(kind, r) }); showAlert(`${no || label} 삭제했습니다.`, "ok", { undo: true }); await load(); }
  catch (e) { showAlert(e.message, "error"); }
}

// ---------- 공통 UI ----------
// 스타일 확인 대화상자. confirmDlg({title, body, verb, danger, input:{label,type,value}}) → 확인이면 true(입력 있으면 값), 취소면 null
function confirmDlg(o) {
  return new Promise(resolve => {
    const d = $("#dlg-confirm"), form = $("#dlg-confirm-form"), cancel = $("#confirm-cancel"), ok = $("#confirm-ok");
    const w = $("#confirm-input-wrap"), inp = $("#confirm-input");
    $("#confirm-title").textContent = o.title || "확인";
    $("#confirm-body").textContent = o.body || "";
    w.hidden = !o.input; if (o.input) { $("#confirm-input-label").textContent = o.input.label || ""; inp.type = o.input.type || "text"; inp.value = o.input.value || ""; }
    ok.textContent = o.verb || "확인"; ok.className = "btn " + (o.danger ? "btn-danger-solid" : "btn-primary");
    let done = false;
    const onSubmit = e => { e.preventDefault(); finish(o.input ? inp.value : true); };
    const onCancel = () => finish(null);
    const onClose = () => finish(null);
    function finish(v) {
      if (done) return; done = true;
      form.removeEventListener("submit", onSubmit); cancel.removeEventListener("click", onCancel); d.removeEventListener("close", onClose);
      if (d.open) d.close();
      resolve(v);
    }
    form.addEventListener("submit", onSubmit); cancel.addEventListener("click", onCancel);
    // 직전 대화상자의 close 이벤트가 뒤늦게 도착해 이번 대화상자를 닫지 않도록, 열고 난 다음 틱에 close 를 듣는다
    const open = () => { d.showModal(); (o.input ? inp : (o.danger ? cancel : ok)).focus(); setTimeout(() => { if (!done) d.addEventListener("close", onClose); }, 0); };
    if (d.open) { d.close(); setTimeout(open, 0); } else open();
  });
}
// 직전 저장 되돌리기 (서버가 저장 직전 백업을 복원; 그 뒤 다른 변경이 있으면 거부)
async function undoLast(t) {
  try { await api("POST", "/api/undo"); if (t) t.remove(); showAlert("되돌렸습니다.", "ok"); await load(); if (typeof refreshCellDialog === "function") refreshCellDialog(); }
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
  if (opts.undo) { const u = document.createElement("button"); u.type = "button"; u.className = "btn btn-sm toast-undo"; u.textContent = "되돌리기"; u.addEventListener("click", () => undoLast(t)); t.insertBefore(u, t.querySelector(".toast-x")); }
  t.querySelector(".toast-x").addEventListener("click", () => t.remove());
  box.appendChild(t);
  while (box.children.length > 5) box.firstChild.remove();
  const ttl = opts.undo ? 12000 : type === "ok" ? 4000 : type === "warn" ? 7000 : 0;
  if (ttl) setTimeout(() => t.remove(), ttl);
}
// 지속 배너 (수식 셀 경고처럼 사용자가 해결할 때까지 보여야 하는 것)
// 수식 셀 배너: 집행내역 탭에서만 전체 문구, 다른 곳은 헤더 상태 한 줄로만 (붉은색 상시 노출 방지)
function showBanner(msg) {
  const a = $("#alert");
  if (!msg) { a.hidden = true; return; }
  a.textContent = msg; a.className = "alert error formula"; a.hidden = false;
}

function closeExecDrawer() { $("#exec-drawer").hidden = true; document.body.classList.remove("drawer-open"); if (XD.row != null) { XD.row = null; if (DATA) renderList("exec"); } }
document.addEventListener("keydown", e => { if (e.key === "Escape" && !$("#exec-drawer").hidden && !$("#dlg").open && !$("#dlg-settings").open) closeExecDrawer(); });
function switchTab(name) {
  document.body.dataset.tab = name;
  if (name !== "exec") closeExecDrawer();
  $$("#main-tabs [role=tab]").forEach(b => {
    const on = b.id === "tab-" + name;
    b.setAttribute("aria-selected", on);
    $("#" + b.getAttribute("aria-controls")).hidden = !on;
  });
  try { localStorage.setItem("ledger-tab", name); } catch { }
}
$$("#main-tabs [role=tab]").forEach(b => b.addEventListener("click", () => switchTab(b.id.replace("tab-", ""))));

document.addEventListener("click", e => {
  const b = e.target.closest("button[data-act], button[data-add]");
  if (!b) {
    const tr = e.target.closest("#exec-table tbody tr[data-row]");
    if (tr && !e.target.closest("a, input, select")) openExecDrawer(Number(tr.dataset.row));
    return;
  }
  if (b.dataset.act === "xact") return execAction(Number(b.dataset.row), b.dataset.action, b);
  if (b.dataset.act === "origin") return gotoOrigin(Number(b.dataset.row));
  if (b.dataset.act === "show-excluded") { switchTab("exec"); QUICK = "excluded"; FILTERS.exec = {}; $$("[data-filter][data-kind=exec]").forEach(el => { if (el.type === "checkbox") el.checked = false; else el.value = ""; }); renderExecTiles(); renderList("exec"); showAlert("예산 집계에서 제외된 집행만 표시 중입니다. 빠른 필터 타일을 누르거나 새로고침하면 해제됩니다.", "ok"); return; }
  if (b.dataset.add) return openForm(b.dataset.add);
  if (b.dataset.act === "dep-use") return openForm("deposit", null, { 거래처: b.dataset.vendor, 구분: "사용" });
  if (b.dataset.act === "dep-add") return openForm("deposit", null, { 거래처: b.dataset.vendor, 구분: "적립" });
  const row = Number(b.dataset.row);
  if (b.dataset.act === "setdate") return setDateToday(row, b.dataset.col, b);
  if (b.dataset.act === "edit") openForm(b.dataset.kind, row);
  else if (b.dataset.act === "del") del(b.dataset.kind, row);
  else if (b.dataset.act === "toexec") toExec(row);
});

$$("[data-filter]").forEach(el => el.addEventListener("input", () => {
  const k = el.dataset.kind;
  FILTERS[k][el.dataset.filter] = el.type === "checkbox" ? el.checked : el.value;
  renderList(k);
}));
$("#dash-fund").addEventListener("change", renderDashboard);
$("#dash-year").addEventListener("change", renderDashboard);
$("#btn-reload").addEventListener("click", load);
document.addEventListener("keydown", e => {
  if (e.key === "F5") { e.preventDefault(); load(); }
});

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
  b.title = AI.enabled ? `AI 도우미 (${AI.provider} · ${AI.model})` : "AI 도우미를 쓰려면 우하단 설정에서 API 키를 입력하세요";
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
    pending.textContent = "오류: " + err.message; pending.className = "msg error";
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
  } catch (err) { out.textContent = "오류: " + err.message; }
  finally { $("#rep-run").disabled = false; }
});
$("#rep-copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("#rep-out").dataset.raw || $("#rep-out").textContent); showAlert("보고서(마크다운)를 복사했습니다.", "ok"); }
  catch { showAlert("복사 실패. 텍스트를 직접 선택해 복사하세요.", "error"); }
});

aiInit();

// ================= 설정 (관리 패널) =================
const SET_FIELDS = ["LEDGER_PROVIDER", "ANTHROPIC_API_KEY", "LEDGER_MODEL", "LEDGER_EFFORT", "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "OPENAI_REASONING_EFFORT"];
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
    refreshDriveStatus();
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


// ================= 집행 상세 드로어 · 증빙 · 단계 처리 =================
let QUICK = "";
const XD = { row: null, evid: null, drive: null };
function evidCount(r) { return (DATA.evidence || []).filter(e => e["거래번호"] === r["거래번호"]).length; }
// 집행 행의 출처: 인건비 확정 / 적립금 적립 기록 / 품의 전환. 연결 행은 핵심 열이 잠김
const LOCKED_COLS = ["재원", "예산목", "금액", "거래처", "원인발생일"];
function execOrigin(r) {
  if (!r || !r["거래번호"]) return null;
  const lab = (DATA.labor || []).find(x => x["연결거래번호"] === r["거래번호"]); if (lab) return { kind: "인건비", locked: true, row: lab._row, label: `${lab["지급월"]} ${lab["이름"]} · ${lab["지급처"]}` };
  const dep = DATA.deposit.find(x => x["연결거래번호"] === r["거래번호"]); if (dep) return { kind: "적립", locked: true, row: dep._row, label: `${dep["일자"]} ${dep["거래처"]} 적립` };
  const m = /^품의 (\S+)/.exec(r["비고"] || ""); if (m) { const req = DATA.req.find(x => x["품의번호"] === m[1]); return { kind: "품의", locked: false, row: req?._row, no: m[1], label: `품의 ${m[1]}` }; }
  return null;
}
function originBadge(r) { const o = execOrigin(r); return o ? ` <button type="button" class="origin ${o.kind}" data-act="origin" data-row="${r._row}" title="${esc(o.label)} 에서 생성${o.locked ? " · 재원·예산목·금액·거래처·원인발생일은 원본에서만 변경" : ""} · 클릭하면 원본으로 이동">${o.kind}</button>` : ""; }
function gotoOrigin(row) {
  const r = DATA.exec.find(x => x._row === row); const o = execOrigin(r); if (!o) return;
  const setSearch = (kind, q) => { FILTERS[kind] = { q }; $$(`[data-filter][data-kind=${kind}]`).forEach(el => { if (el.type === "checkbox") el.checked = false; else el.value = el.dataset.filter === "q" ? q : ""; }); renderList(kind); };
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
  ];
  $("#exec-tiles").innerHTML = tiles.map(([k, l, c]) => `<div class="card ${QUICK === k ? "on" : ""}" role="button" tabindex="0" data-quick="${k}" aria-pressed="${QUICK === k}"><div class="k">${l}</div><div class="v">${c}건</div></div>`).join("");
}
$("#exec-tiles").addEventListener("click", e => { const t = e.target.closest("[data-quick]"); if (!t) return; QUICK = QUICK === t.dataset.quick ? "" : t.dataset.quick; renderExecTiles(); renderList("exec"); });
$("#exec-tiles").addEventListener("keydown", e => { if ((e.key === "Enter" || e.key === " ") && e.target.dataset.quick) { e.preventDefault(); e.target.click(); } });
$$("[data-filter][data-kind=exec]").forEach(el => el.addEventListener("input", renderExecTiles));

async function execAction(row, action, btn) {
  const r = DATA.exec.find(x => x._row === row); if (!r) return;
  const label = { claim: "청구 (지급청구일 등록)", resolve: "결의 (결의일 등록)", unresolve: "결의 취소", complete: "승인 (지출완료일 등록)", fix: "보완 표시", unfix: "보완 해제", uncomplete: "승인 취소 (지출완료일 삭제)" }[action];
  if (action === "uncomplete" && !await confirmDlg({ title: "승인 취소", body: `${r["거래번호"]} 의 지출완료일(${r["지출완료일"]})을 지우고 청구 상태로 되돌립니다.`, verb: "승인 취소", danger: true })) return;
  if (btn) btn.disabled = true;
  try {
    await api("POST", `/api/exec/${row}/action`, { action, expect: expectOf("exec", r) });
    showAlert(`${r["거래번호"]} ${label} (${today()})`, "ok", { undo: true });
    await load();
  } catch (e) { showAlert(e.message, "error"); if (btn) btn.disabled = false; }
}

function openExecDrawer(row) {
  XD.row = row; XD.evid = null;
  $("#ai-drawer").hidden = true;
  $("#exec-drawer").hidden = false; document.body.classList.add("drawer-open");
  renderList("exec");
  renderExecDrawer(true);
}
$("#xd-close").addEventListener("click", closeExecDrawer);

async function renderExecDrawer(fetchEvid) {
  const r = DATA.exec.find(x => x._row === XD.row);
  if (!r) { $("#exec-drawer").hidden = true; XD.row = null; return; }
  $("#xd-title").innerHTML = esc(r["거래번호"]) + originBadge(r);
  $("#xd-sub").textContent = `${r["재원"]} · ${r["예산목"]} · ${fmt(r["금액"])}원`;
  // 다른 저장·새로고침으로 다시 그릴 때 입력 중이던 증빙 업로드 폼은 유지
  const oldForm = $("#evid-form"), keep = oldForm && XD.formRow === r._row ? { kind: oldForm.kind.value, date: oldForm.date.value, note: oldForm.note.value, files: oldForm.files.files } : null;
  if (fetchEvid || !XD.evid) {
    try { const d = await api("GET", `/api/evidence/${encodeURIComponent(r["거래번호"])}`); XD.evid = d.items; XD.drive = d.drive; }
    catch (e) { XD.evid = []; XD.drive = { connected: false, error: e.message }; }
  }
  const st = r["상태"];
  const acts = [];
  if (st === "발생") acts.push(["claim", "청구 (지급청구일 등록)", true]);
  if (st === "청구") { acts.push(["complete", "승인 (지출완료일 등록)", true]); acts.push(["fix", "보완 표시", false]); }
  if (st === "보완") { acts.push(["complete", "승인 (지출완료일 등록)", true]); acts.push(["unfix", "보완 해제", false]); }
  if (st === "완료") { acts.push(["resolve", "결의 (결의일 등록 → 완료)", true]); acts.push(["uncomplete", "승인 취소", false]); }
  if (st === "결의") { acts.push(["unresolve", "결의 취소 (승인으로 되돌림)", false]); }
  const evid = XD.evid || [];
  const kinds = [...new Set(evid.map(e => e["증빙종류"]).filter(Boolean))];
  const drive = XD.drive || {};
  $("#xd-body").innerHTML = `
    <section class="xd-sec">
      <h3>집행 정보 <span class="sp"></span><button type="button" class="btn btn-sm" data-act="edit" data-kind="exec" data-row="${r._row}">수정</button></h3>
      <div class="kv">
        <b>상태</b><span><span class="badge ${esc(st)}">${esc(STATUS_LABEL[st] || st)}</span> <span class="toolbar-note">${esc(STATUS_HELP[st] || "")}</span></span>
        <b>발생 <small>원인발생일</small></b><span>${esc(r["원인발생일"] || "-")}</span>
        <b>청구 <small>지급청구일</small></b><span>${esc(r["지급청구일"] || "-")}</span>
        <b>승인 <small>지출완료일</small></b><span>${esc(r["지출완료일"] || "-")}</span>
        <b>결의 <small>결의일</small></b><span>${esc(r["결의일"] || "-")}</span>
        <b>결제수단</b><span>${esc(r["결제수단"] || "-")}</span>
        <b>거래처</b><span>${esc(r["거래처"] || "-")}</span>
        <b>적요</b><span>${esc(r["적요"] || "-")}</span>
        <b>세목</b><span>${esc(r["세목"] || "-")}${r["세세목"] ? " / " + esc(r["세세목"]) : ""}</span>
        <b>사용자</b><span>${esc(r["사용자"] || "-")}</span>
        <b>태그</b><span>${esc(r["태그"] || "-")}</span>
        <b>관리번호</b><span>${esc(r["관리번호"] || "-")}</span>
        <b>비고</b><span>${esc(r["비고"] || "-")}</span>
      </div>
    </section>
    <section class="xd-sec">
      <h3>다음 처리</h3>
      <div class="xd-actions">${acts.length ? acts.map(([a, l, p]) => `<button type="button" class="btn btn-sm ${p ? "btn-primary" : ""}" data-act="xact" data-action="${a}" data-row="${r._row}">${l}</button>`).join("") : `<span class="toolbar-note">완료된 건입니다.</span><button type="button" class="btn btn-sm" data-act="xact" data-action="uncomplete" data-row="${r._row}">완료 취소</button>`}</div>
    </section>
    <section class="xd-sec">
      <h3>증빙 <span class="toolbar-note">${evid.length}개</span><span class="sp"></span>${r["증빙폴더"] ? `<a class="btn btn-sm" href="${esc(r["증빙폴더"])}" target="_blank" rel="noopener">폴더 열기</a>` : ""}</h3>
      ${!drive.connected ? `<p class="toolbar-note warn">구글 드라이브가 연결되지 않았습니다. 우하단 설정에서 연결하면 업로드할 수 있습니다.${drive.error ? " (" + esc(drive.error) + ")" : ""}</p>` : ""}
      ${evid.length ? `<div class="table-wrap"><table class="grid compact evid-table"><thead><tr><th>종류</th><th>파일명</th><th class="num">크기</th><th>업로드</th><th></th></tr></thead><tbody>
        ${evid.map(e => `<tr><td>${esc(e["증빙종류"])}</td><td class="evid-name">${e.url ? `<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e["파일명"])}</a>` : esc(e["파일명"])}${e["원본파일명"] && e["원본파일명"] !== e["파일명"] ? `<div class="toolbar-note">${esc(e["원본파일명"])}</div>` : ""}</td><td class="num">${e["크기"] ? Math.round(e["크기"] / 1024).toLocaleString() + " KB" : ""}</td><td>${esc(mmdd(e["업로드일"]))}</td><td><button type="button" class="btn btn-sm btn-danger" data-evdel="${e._row}" data-name="${esc(e["파일명"])}" title="장부에서 삭제하고 드라이브 휴지통으로 이동">삭제</button></td></tr>`).join("")}
      </tbody></table></div>` : '<p class="toolbar-note">등록된 증빙이 없습니다.</p>'}
      <div class="evid-list" style="margin-top:8px"><span class="toolbar-note">증빙목록</span><code>${esc(kinds.join(", ") || "(없음)")}</code>${kinds.length ? `<button type="button" class="btn btn-sm" id="evid-copy">복사</button>` : ""}</div>
    </section>
    <section class="xd-sec">
      <h3>증빙 업로드</h3>
      <form id="evid-form" class="evid-form">
        <label>증빙종류 <input type="text" name="kind" list="dl-증빙종류" required autocomplete="off" placeholder="예: 카드전표, 견적서, 회의록"></label>
        <label>파일명 날짜 <input type="date" name="date" value="${esc(r["원인발생일"] || today())}"></label>
        <label class="wide">비고 <input type="text" name="note" placeholder="선택"></label>
        <label class="wide file-pick">파일 <span class="file-pick-row"><input type="file" name="files" multiple ${drive.connected ? "" : "disabled"}><span class="btn btn-sm file-btn" aria-hidden="true">파일 선택</span><span class="file-names">선택된 파일 없음</span></span></label>
        <div class="drop wide" id="evid-drop"><b>파일을 여기로 끌어다 놓으세요</b><br>이름은 재원_적요_증빙종류_금액_YYMMDD 로 자동 변환되어 드라이브 증빙관리/${esc((r["원인발생일"] || "").slice(0, 4))}/${esc(r["재원"])}/${esc(r["거래번호"])} 에 저장됩니다.</div>
        <div class="wide" style="display:flex;justify-content:flex-end"><button type="submit" class="btn btn-primary btn-sm" ${drive.connected ? "" : "disabled"}>업로드</button></div>
      </form>
    </section>`;
  bindEvidForm(r);
  XD.formRow = r._row;
  if (keep) { const f = $("#evid-form"); f.kind.value = keep.kind; if (keep.date) f.date.value = keep.date; f.note.value = keep.note; try { if (keep.files?.length && !f.files.disabled) f.files.files = keep.files; } catch { } }
}

function bindEvidForm(r) {
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
      const res = await fetch(`/api/evidence/${encodeURIComponent(r["거래번호"])}`, { method: "POST", body: fd });
      if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
      const d = await res.json();
      showAlert(`${d.items.length}개 업로드 완료`, "ok");
      await load();
      await renderExecDrawer(true);
    } catch (err) { showAlert("업로드 실패: " + err.message, "error"); btn.disabled = false; btn.textContent = "업로드"; }
  });
  $("#evid-copy")?.addEventListener("click", async () => { try { await navigator.clipboard.writeText($(".evid-list code").textContent); showAlert("증빙목록을 복사했습니다.", "ok"); } catch { } });
  $$("#xd-body [data-evdel]").forEach(b => b.addEventListener("click", async () => {
    if (!await confirmDlg({ title: "증빙 삭제", body: `'${b.dataset.name}' 을 장부에서 지우고 드라이브 휴지통으로 옮깁니다.`, verb: "삭제", danger: true })) return;
    const row = Number(b.dataset.evdel); const e = (XD.evid || []).find(x => x._row === row);
    try {
      const res = await api("DELETE", `/api/evidence/${row}`, { expect: e ? { 거래번호: e["거래번호"], 파일명: e["파일명"] } : undefined });
      showAlert(res.warning || "증빙을 삭제했습니다.", res.warning ? "warn" : "ok");
      await load(); await renderExecDrawer(true);
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
