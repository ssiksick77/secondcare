/* 지출 신청 화면 (/request) — app.js 의 공통 함수($, api, openForm, renderList, confirmDlg, showAlert …)를 그대로 사용.
   연구원 화면: /request 직접 접속 (신청 목록·상태 확인, 본인 신청 추가·수정·첨부)
   담당자 화면: 회계대장·인건비 화면에서 헤더 [신청] 버튼으로 들어온 경우 (sessionStorage "request-admin") — 승인·반려·품의 전환·주문 */
"use strict";

// ---------- 공통 정의 확장 ----------
Object.assign(IDENT, { request: ["신청번호"], order: ["주문번호"], ratt: ["신청번호", "파일명"] });
FILTERS.request = {};
const REQ_LOCKED = ["품의전환", "완료"];  // 비고만 수정 가능, 삭제 불가
const REQ_ORDER_LOCK = ["구분", "단가", "수량", "금액", "구매처", "부가세구분", "부가세액"];  // 주문에 묶인 신청
const REQ_APPROVAL_KEYS = ["품목", "규격", "단가", "수량", "금액", "관련과제", "부가세구분", "부가세액"];  // 승인된 건에서 바뀌면 다시 결재 (서버도 같은 기준)
const REQ_CONF_KEYS = [["_시작일", "시작일"], ["_종료일", "종료일"], ["_국내외", "국내외"], ["_장소", "장소"], ["_참가자", "참가자"], ["_등록비", "등록비"]];
const reqExcerpt = (s, n = 24) => { s = String(s ?? "").replace(/\s+/g, " ").trim(); return s.length > n ? s.slice(0, n) + "…" : s; };
const rattCount = r => (DATA.ratt || []).filter(a => a["신청번호"] === r["신청번호"]).length;
const reqLocked = r => REQ_LOCKED.includes(r?.["상태"]);
const isReqAdmin = () => document.body.classList.contains("req-admin");
const reqType = () => $("#request-tabs [role=tab][aria-selected=true]")?.dataset.rtype || "장비";
const safeUrl = u => /^https?:\/\/\S+$/i.test(String(u ?? "").trim()) ? String(u).trim() : "";
const reqFind = row => (DATA?.request || []).find(x => x._row === row);
const listLabel = (list, n = 3) => list.slice(0, n).map(r => r["신청번호"]).join(", ") + (list.length > n ? ` 외 ${list.length - n}건` : "");
function reqDetail(r) { try { const d = JSON.parse(r?.["상세"] || "{}"); return d && typeof d === "object" && !Array.isArray(d) ? d : {}; } catch { return {}; } }
// 소모품 구매처: 목록·이용 가능 여부·안내는 /api/all meta (설정 › 신청 · 발주서에서 담당자가 관리)
const reqSuppliers = () => DATA?.meta?.suppliers || [];
const supOff = name => reqSuppliers().some(x => x.name === name && !x.available);
const supAvail = () => reqSuppliers().filter(x => x.available).map(x => x.name);
const supSplit = v => [...new Set(String(v ?? "").split(/[,，、\n]/).map(x => x.trim()).filter(Boolean))];
const OFF_SUFFIX = " (현재 이용 불가)";
function supNoteText() {
  const off = reqSuppliers().filter(x => !x.available).map(x => x.name), note = String(DATA?.meta?.supplier_note || "").trim();
  const parts = [];
  if (note) parts.push(note);
  if (!supAvail().length) parts.push("지금은 신청 가능한 구매처가 없습니다. 담당자에게 문의하세요.");
  else if (off.length) parts.push(`현재 이용 불가: ${off.join(", ")}`);
  return parts.join(" · ");
}
function numOf(v) { const ev = evalAmount(v); if (ev !== undefined) return ev; return String(v ?? "").trim() === "" ? null : numText(v); }
const vatOn = r => r?.["부가세구분"] === "Y";
const vatOf = (u, q) => Math.round(u * q * 0.1);  // 부가세 기본값: 공급가액의 10%

COLS.request = [
  { k: "신청번호", rowbtn: true },
  { k: "상태", t: "badge" },
  { k: "신청인" },
  { k: "신청일", t: "date" },
  { k: "관련과제" },
  { k: "품목", t: "title", subCalc: r => r["규격"] || reqExcerpt(r["사유"], 40) },
  { k: "구매처", get hide() { return reqType() !== "소모품"; } },  // 소모품 탭에서만 표시
  { k: "수량", t: "num" },
  { k: "금액", t: "num", amt: true },
  { k: "첨부", ctr: true, calc: rattCount, title: "첨부 파일 수", html: r => { const n = rattCount(r); return n ? String(n) : '<span class="muted">-</span>'; } },
  { k: "결재", calc: r => r["결재일"] || "", title: "결재인 · 결재일 (반려는 사유)",
    html: r => `${r["상태"] === "반려" ? `<span class="rej" title="반려 사유: ${esc(r["반려사유"] || "")}">${esc(r["반려사유"] || "사유 없음")}</span>`
      : r["결재인"] && r["결재일"] ? `${esc(r["결재인"])} <span class="muted" title="${esc(r["결재일"])}">${esc(mmdd(r["결재일"]))}</span>` : '<span class="muted">-</span>'}` },
  { k: "주문번호", get hide() { return reqType() !== "소모품"; } },  // 주문은 소모품에만
  { k: "연결품의번호", label: "연결 품의" },
  { k: "부가세구분", hide: true }, { k: "부가세액", t: "num", hide: true },  // 화면에서는 생략, CSV 에는 포함
];
const REQUEST_TITLES = { request: "신청" };
const REQUEST_FORMS = {
  request: () => {
    const items = ["장비", "소모품", "기타"].join("|");
    return [
      { k: "신청번호", type: "ro" },
      { k: "구분", type: "select", opts: DATA.meta.request_types || ["장비", "소모품", "학회", "기타"], req: true },
      { k: "신청인", type: "datalist", list: "신청인", req: true },
      { k: "신청일", type: "date", req: true },
      { k: "관련과제", type: "datalist", list: "관련과제", hint: "과제 목록에서 고르거나 직접 입력" },
      { k: "희망일", type: "date", hint: "필요한 날짜" },
      { k: "품목", type: "text", req: true, cls: "mid", focus: true },
      { k: "규격", type: "text", dep: items, hint: "모델·사양" },
      { k: "단가", type: "num", req: true, dep: items, label: "단가 (부가세 포함)" },
      { k: "수량", type: "num", req: true, dep: items },
      { k: "부가세구분", type: "check", label: "부가세 구분 입력", dep: items },
      { k: "부가세액", type: "num", dep: items, hint: "단가 × 수량의 10%, 고칠 수 있음" },
      { k: "_금액", type: "ro", label: "금액 (단가 × 수량)", dep: items },
      { k: "금액", type: "num", req: true, dep: "학회", hint: "여비 계산기 합계 또는 직접 입력" },
      { k: "_국내외", type: "select", opts: ["국내", "국외"], label: "국내 / 국외", dep: "학회" },
      { k: "_시작일", type: "date", label: "시작일", dep: "학회" },
      { k: "_종료일", type: "date", label: "종료일", dep: "학회" },
      { k: "_장소", type: "text", label: "장소", dep: "학회", hint: "도시·국가" },
      { k: "_참가자", type: "text", label: "참가자", dep: "학회", hint: "쉼표로 구분" },
      { k: "_등록비", type: "num", label: "등록비", dep: "학회" },
      { k: "사유", type: "text", cls: "wide", hint: "용도·필요한 이유" },
      { k: "구매처", type: "select", opts: isReqAdmin() ? reqSuppliers().map(x => x.name) : supAvail(), req: true, dep: "소모품", hint: "주문할 쇼핑몰" },
      { k: "온라인코드", type: "text", dep: "소모품" },
      { k: "상품코드", type: "text", dep: "소모품" },
      { k: "상품링크", type: "text", dep: "소모품", hint: "https://…" },
      { k: "비고", type: "text", cls: "wide" },
    ];
  },
};
function requestDefaults(kind) {
  if (kind !== "request") return {};
  let name = ""; try { name = localStorage.getItem("request-name") || ""; } catch { }
  const av = supAvail();
  return { 구분: reqType(), 신청일: today(), 신청인: name, 수량: 1, _국내외: "국내", 관련과제: FILTERS.request["관련과제"] || "", 구매처: av.length === 1 ? av[0] : (FILTERS.request["구매처"] && av.includes(FILTERS.request["구매처"]) ? FILTERS.request["구매처"] : "") };
}

// ---------- 화면 전환 · 담당자/연구원 ----------
try { if (sessionStorage.getItem("request-admin") === "1") { document.body.classList.add("req-admin"); if (document.body.classList.contains("request-mode")) setMode("request", false); } } catch { }  // 제목·머리글을 담당자용으로
function switchReqTab(t, render = true) {
  $$("#request-tabs [role=tab]").forEach(b => b.setAttribute("aria-selected", String(b.dataset.rtype === t)));
  $("#rpanel").setAttribute("aria-labelledby", "rtab-" + t);
  FILTERS.request["구분"] = t; LIST_MORE.request = false; REQSEL.clear();
  if (t !== "소모품" && FILTERS.request["구매처"]) { FILTERS.request["구매처"] = ""; const fs = $("#rq-sup-filter select"); if (fs) fs.value = ""; }
  closeReqDrawer();
  try { localStorage.setItem("ledger-rtab", t); } catch { }
  if (render && DATA) renderRequest();
}
$$("#request-tabs [role=tab]").forEach(b => b.addEventListener("click", () => switchReqTab(b.dataset.rtype)));
rovingTabs($("#request-tabs"));
$("#btn-request").addEventListener("click", () => {
  if (document.body.classList.contains("request-mode")) { setMode("main"); return; }
  try { sessionStorage.setItem("request-admin", "1"); } catch { }  // 회계대장에서 들어오면 담당자 (이 탭이 열려 있는 동안)
  document.body.classList.add("req-admin");
  setMode("request");
  if (DATA) renderRequest();
});
function setReqYear(y) {
  const ysel = $("#request-year");
  if (![...ysel.options].some(o => o.value === y)) return false;
  ysel.value = y; FILTERS.request.year = y; LIST_MORE.request = false; REQSEL.clear();
  return true;
}
$("#request-year").addEventListener("change", e => { setReqYear(e.target.value); renderRequest(); });
// 이전 연도에 남은 '신청' 건: 연도를 '전체', 상태를 '신청'으로
$("#req-prev-year").addEventListener("click", () => {
  setReqYear("");
  const st = $("select[data-filter='상태'][data-kind=request]"); st.value = "신청"; FILTERS.request["상태"] = "신청";
  renderRequest(); $("#request-year").focus();
});

// ---------- 목록 ----------
function fillRequestSelects() {
  if (!DATA.request) return;
  const rows = DATA.request;
  const years = new Set([String(new Date().getFullYear())]);
  rows.forEach(r => r["신청일"] && years.add(r["신청일"].slice(0, 4)));
  const ys = [...years].sort().reverse();
  const ysel = $("#request-year");
  setOptions(ysel, ["", ...ys], ["전체", ...ys]);
  if (!ysel.dataset.init) { ysel.value = String(new Date().getFullYear()); ysel.dataset.init = 1; }
  FILTERS.request.year = ysel.value;
  const uniq = k => [...new Set(rows.map(r => r[k]).filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b), "ko"));
  const names = uniq("신청인"), tasks = uniq("관련과제");
  $$("select[data-filter='신청인'][data-kind=request]").forEach(sel => setOptions(sel, ["", ...names], ["전체", ...names]));
  $$("select[data-filter='관련과제'][data-kind=request]").forEach(sel => setOptions(sel, ["", ...tasks], ["전체", ...tasks]));
  const sups = [...new Set([...reqSuppliers().map(x => x.name), ...uniq("구매처")])];
  $$("select[data-filter='구매처'][data-kind=request]").forEach(sel => { setOptions(sel, ["", ...sups], ["전체", ...sups]); FILTERS.request["구매처"] = sel.value; });
  const dl = (id, html) => { let el = $("#" + id); if (!el) { el = document.createElement("datalist"); el.id = id; document.body.appendChild(el); } el.innerHTML = html; };
  const people = [...new Set([...names, ...(DATA.people || []).map(p => p["이름"])])].sort((a, b) => a.localeCompare(b, "ko"));
  dl("dl-신청인", people.map(v => `<option value="${esc(v)}">`).join(""));
  const funds = DATA.funds.map(f => [f["재원코드"], f["과제명"] || ""]);
  const extra = tasks.filter(t => !funds.some(([c]) => c === t)).map(t => [t, ""]);
  dl("dl-관련과제", [...funds, ...extra].map(([v, l]) => `<option value="${esc(v)}"${l ? ` label="${esc(l)}"` : ""}>`).join(""));
}
function renderRequest() {
  if (!DATA || !DATA.request) return;
  FILTERS.request["구분"] = reqType();
  $("#request-table").dataset.rtype = reqType();  // 소모품 탭은 열(구매처·주문번호)이 더 많아 최소 폭이 다름
  renderList("request");
  renderOrders();
  updateReqTabCounts();
  $("#rq-sup-filter").hidden = reqType() !== "소모품";
  const info = $("#req-sup-info"), txt = reqType() === "소모품" ? supNoteText() : "";
  info.hidden = !txt;
  info.innerHTML = txt ? `<b>구매처 안내</b> ${esc(txt)}` : "";
  if (RD.row != null && !$("#req-drawer").hidden) RD.render = renderReqDrawer(false);
}
// 하위 탭 배지: '신청' 상태 건수 (연도와 무관하게 전부, 해를 넘겨 남은 건도 보이도록)
function updateReqTabCounts() {
  $$("#request-tabs [role=tab]").forEach(b => {
    const t = b.dataset.rtype, n = DATA.request.filter(r => r["구분"] === t && r["상태"] === "신청").length;
    b.innerHTML = `${esc(t)}${n ? ` <span class="tab-n" title="신청 ${n}건"><span class="sr-only">신청 상태 </span>${n}<span class="sr-only">건</span></span>` : ""}`;
  });
  const y = FILTERS.request.year, t = reqType();
  const old = y ? DATA.request.filter(r => r["구분"] === t && r["상태"] === "신청" && (r["신청일"] || "").slice(0, 4) < y).length : 0;
  const link = $("#req-prev-year"); link.hidden = !old; link.textContent = old ? `이전 연도 신청 ${old}건` : "";
}
// 표가 넘치면 우측 그림자 힌트 (드로어를 열고 닫을 때 열이 접히므로 다시 잼)
function reqScrollHint() {
  const t = $("#request-table"), w = t?.closest(".table-wrap");
  if (w) w.classList.toggle("scrollable", t.scrollWidth > w.clientWidth + 4);
}

let REQ_RESIZE_T = null;
window.addEventListener("resize", () => { clearTimeout(REQ_RESIZE_T); REQ_RESIZE_T = setTimeout(reqScrollHint, 120); });

// 담당자 선택 열 (승인·반려·품의 전환·주문·삭제를 체크한 행에 한꺼번에)
const REQSEL = new Set();
const reqFiltered = () => ["상태", "신청인", "관련과제", "구매처", "q"].some(k => String(FILTERS.request[k] ?? "").trim());
SEL_HOOK.request = {
  head: () => isReqAdmin() ? `<th class="sel"><input type="checkbox" id="request-sel-all" aria-label="표시된 신청 모두 선택"></th>` : "",
  cell: r => isReqAdmin() ? `<td class="sel"><input type="checkbox" data-rsel="${r._row}" aria-label="${esc(r["신청번호"])} 선택"${REQSEL.has(r._row) ? " checked" : ""}></td>` : "",
  rowCls: r => (RD.row === r._row ? " selected" : "") + (REQSEL.has(r._row) ? " checked" : ""),
  after: () => {
    const vis = new Set($$("#request-table tbody tr[data-row]").map(tr => Number(tr.dataset.row)));
    [...REQSEL].forEach(r => { if (!vis.has(r)) REQSEL.delete(r); });  // 필터로 가려진 행은 선택 해제
    updateSelBar(); updateRdNav();
  },
  // 빈 목록: 조건 때문에 없는지, 이 구분에 신청이 아직 하나도 없는지 구분
  empty: () => {
    const t = reqType(), any = DATA.request.some(r => r["구분"] === t);
    return any || reqFiltered() ? "조건에 맞는 신청이 없습니다. 검색어·필터를 지워 보세요."
      : `아직 ${esc(t)} 신청이 없습니다. <button type="button" class="btn btn-sm btn-primary" data-add="request">신청 추가</button>로 시작하세요.`;
  },
};
const selRows = () => [...REQSEL].map(reqFind).filter(Boolean);
const canApprove = r => r["상태"] === "신청" || r["상태"] === "반려";
const canReject = r => (r["상태"] === "신청" || r["상태"] === "승인") && !r["주문번호"];
const canConvert = r => r["상태"] === "승인" && !r["연결품의번호"];
const canOrder = r => r["구분"] === "소모품" && r["상태"] === "승인" && !r["주문번호"] && !r["연결품의번호"];
const canDelete = r => !reqLocked(r) && !r["주문번호"];
const SUP_MIXED = "구매처가 같은 신청만 한 주문으로 묶을 수 있습니다";
let REQ_BUSY = false;  // 선택 바 일괄 처리 중
function updateSelBar() {
  if (REQ_BUSY) return;
  const list = selRows(), n = list.length, sup = reqType() === "소모품";
  $("#req-sel-n").textContent = n ? `${n}건 선택 · ${fmt(list.reduce((a, r) => a + (r["금액"] || 0), 0))}원` : "선택 없음";
  // 막힌 동작의 첫 사유를 #req-sel-why 에 글로 (툴팁에만 두지 않음). 승인·반려는 다른 동작도 전부 막혔을 때만 (승인된 건에 '승인 불가'는 소음)
  const reasons = [], minor = [];
  const set = (act, on, why, block) => { const b = $(`#req-selbar [data-rq=${act}]`); b.disabled = !on; b.hidden = !n || (act === "order" && !sup); if (why !== undefined) b.title = why; if (n && !on && block && !b.hidden) (act === "approve" || act === "reject" ? minor : reasons).push(block); };
  set("approve", list.some(canApprove), "신청·반려 상태의 선택 건을 승인", "승인할 수 있는 건이 없습니다 (신청·반려 상태만)");
  set("reject", list.some(canReject), "신청·승인 상태의 선택 건을 반려 (사유 입력)", "반려할 수 있는 건이 없습니다 (신청·승인 상태, 주문 전)");
  const convWhy = "승인된 신청만 품의로 전환할 수 있습니다";
  set("convert", n > 0 && list.every(canConvert), n && !list.every(canConvert) ? convWhy : "선택한 승인 건을 품의 1건으로", convWhy);
  const mixed = new Set(list.map(r => r["구매처"] || "")).size > 1;
  const orderWhy = n && !list.every(canOrder) ? "주문 전 승인된 소모품 신청만 묶을 수 있습니다" : mixed ? SUP_MIXED : "";
  set("order", n > 0 && !orderWhy, orderWhy || "선택한 승인 소모품을 주문 1건으로 묶음", orderWhy);
  const delWhy = "품의전환·완료·주문에 묶인 신청은 삭제할 수 없습니다";
  set("delete", n > 0 && list.every(canDelete), n && !list.every(canDelete) ? delWhy : "선택한 신청 삭제", delWhy);
  set("clear", n > 0);
  const none = n && $$("#req-selbar button[data-rq]:not([data-rq=clear])").every(b => b.hidden || b.disabled);
  const why = $("#req-sel-why"); why.textContent = sup && mixed ? SUP_MIXED : reasons[0] || (none ? minor[0] : "") || ""; why.hidden = !why.textContent; $("#req-sel-help").hidden = !!n;
  const all = $("#request-sel-all"); if (all) { const boxes = $$("#request-table input[data-rsel]"); all.checked = boxes.length > 0 && boxes.every(b => b.checked); all.indeterminate = boxes.some(b => b.checked) && !all.checked; }
}
const markChecked = box => box.closest("tr")?.classList.toggle("checked", box.checked);
document.addEventListener("change", e => {
  if (e.target.id === "request-sel-all") { $$("#request-table input[data-rsel]").forEach(b => { b.checked = e.target.checked; markChecked(b); const r = Number(b.dataset.rsel); e.target.checked ? REQSEL.add(r) : REQSEL.delete(r); }); updateSelBar(); }
  else if (e.target.dataset?.rsel !== undefined) { const r = Number(e.target.dataset.rsel); e.target.checked ? REQSEL.add(r) : REQSEL.delete(r); markChecked(e.target); updateSelBar(); }
});
$("#req-selbar").addEventListener("click", e => {
  const b = e.target.closest("button[data-rq]"); if (!b || b.disabled || REQ_BUSY) return;
  const list = selRows(), act = b.dataset.rq;
  REQ_FOCUS = "selbar";
  if (act === "clear") { REQSEL.clear(); renderList("request"); reqRefocus(); return; }
  if (act === "approve") return runReqAction(list.filter(canApprove), "approve", {}, { skipped: list.length - list.filter(canApprove).length });
  if (act === "reject") return rejectRequests(list.filter(canReject), list.length - list.filter(canReject).length);
  if (act === "convert") return convertRequests(list);
  if (act === "order") return openOrderDialog(list);
  if (act === "delete") return deleteRequests(list);
});
// 처리 뒤 포커스 복귀: 드로어에서 했으면 드로어의 새 주 버튼(없으면 닫기), 선택 바에서 했으면 선택 건수 글자
let REQ_FOCUS = null;
async function reqRefocus(from = REQ_FOCUS) {
  REQ_FOCUS = null;
  if (from === "drawer" && RD.row != null && !$("#req-drawer").hidden) {
    try { await RD.render; } catch { }
    ($("#rd-body .rd-actions .btn-primary:not(:disabled)") || $("#rd-body .rd-actions .btn:not(:disabled)") || $("#rd-close")).focus();
    return;
  }
  if (isReqAdmin() && $("#req-sel-n").offsetParent) $("#req-sel-n").focus();
  else ($("#request-table tbody input[data-rsel]") || $("#request-table tbody .rowbtn") || $("#rpanel [data-add=request]"))?.focus();
}

// 행: 한 번 클릭 = 상세 패널, 두 번 클릭 = 수정 창 (집행내역과 같은 방식)
let REQ_CLICK_T = null;
$("#request-table").addEventListener("click", e => {
  if (e.target.closest("input, a, select, label") || (e.target.closest("button") && !e.target.closest(".rowbtn"))) return;
  const tr = e.target.closest("tbody tr[data-row]"); if (!tr) return;
  const row = Number(tr.dataset.row);
  clearTimeout(REQ_CLICK_T); REQ_CLICK_T = null;
  if (e.detail >= 2) { window.getSelection()?.removeAllRanges(); editRequest(row); }
  else REQ_CLICK_T = setTimeout(() => { REQ_CLICK_T = null; openReqDrawer(row); }, 220);
});
$("#request-table").addEventListener("keydown", e => {
  const btn = e.target.closest(".rowbtn"); if (!btn) return;
  const row = Number(btn.closest("tr[data-row]").dataset.row);
  if ((e.key === "Enter" && e.shiftKey) || e.key === "F2") { e.preventDefault(); editRequest(row); }
  else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openReqDrawer(row); }
});
function canEditReq(r) { return isReqAdmin() || r["상태"] === "신청"; }
function editRequest(row) {
  const r = reqFind(row); if (!r) return;
  if (!canEditReq(r)) { showAlert(`'${r["상태"]}' 상태의 신청은 담당자만 고칠 수 있습니다. 바꿀 내용은 담당자에게 알려 주세요.`, "warn"); return; }
  openForm("request", row);
}

// ---------- 입력 폼 (구분별 칸 · 금액 미리보기 · 부가세 · 잠금 · 상세 JSON) ----------
const _openFormBeforeRequest = openForm;
openForm = function (kind, row, preset, opts) {
  _openFormBeforeRequest(kind, row, preset, opts);
  if (kind === "request") requestFormAfterOpen(row ?? null);
};
// 폼 맨 위 안내 (잠금·전환 설명). 오류 칸(#dlg-error)과 따로 두어 검증 오류가 안내를 지우지 않게
function reqFormNote(text) {
  const p = document.createElement("p"); p.className = "wide toolbar-note req-form-note"; p.id = "req-form-note"; p.textContent = text;
  $("#dlg-fields").prepend(p);
}
function requestFormAfterOpen(row) {
  const rec = row != null ? reqFind(row) : null;
  const amt = F("금액")?.closest("label");
  if (amt) {  // 학회: 여비 계산기 (conf.js)
    const calc = document.createElement("div"); calc.className = "wide req-calc"; calc.id = "req-calc-row";
    calc.innerHTML = `<button type="button" class="btn btn-sm" id="req-calc-btn" aria-haspopup="dialog">여비 계산기</button><span class="toolbar-note">항공·숙박·일비를 계산해 금액과 상세에 채웁니다</span>`;
    amt.after(calc);
  }
  const sup = F("구매처");
  if (sup) {  // 이용 불가 구매처 표시 (담당자 목록, 또는 기존 값) + 안내 문구
    [...sup.options].forEach(o => { if (o.value && supOff(o.value)) o.textContent = o.value + OFF_SUFFIX; });
    const p = document.createElement("p"); p.className = "wide toolbar-note req-sup-note"; p.id = "req-sup-note";
    p.textContent = supNoteText(); p.hidden = !p.textContent;
    sup.closest("label").after(p);
  }
  const det = reqDetail(rec);
  if (rec) REQ_CONF_KEYS.forEach(([k, dk]) => { const el = F(k); if (el && det[dk] != null && det[dk] !== "") el.value = el.classList.contains("num-input") ? fmt(det[dk]) : det[dk]; });
  // 부가세: 저장값이 Y 면 체크. 부가세액이 자동값(10%)과 같으면 단가·수량을 고칠 때 따라 바뀜
  const vchk = F("부가세구분"), vamt = F("부가세액");
  if (vchk) {
    vchk.checked = vatOn(rec);
    const u = numOf(rec?.["단가"]), q = numOf(rec?.["수량"]), stored = numOf(rec?.["부가세액"]);
    vamt.dataset.auto = !vatOn(rec) || stored == null || (u != null && q != null && stored === vatOf(u, q)) ? "1" : "";
  }
  const lock = (pred, note) => {
    $$("#dlg-fields input[name], #dlg-fields select[name]").forEach(el => {
      if (el.readOnly && el.type === "text" && el.tabIndex === -1) return;  // ro 칸
      if (!pred(el.name.replace(/^_/, ""))) return;
      if (el.tagName === "SELECT" || el.type === "checkbox") el.disabled = true; else { el.readOnly = true; el.setAttribute("aria-readonly", "true"); }
      el.classList.add("locked");
    });
    reqFormNote(note);
  };
  if (rec && reqLocked(rec)) { lock(k => k !== "비고", `'${rec["상태"]}' 상태(연결 품의 ${rec["연결품의번호"] || "-"})라 비고만 바꿀 수 있습니다.`); $("#req-calc-btn")?.setAttribute("disabled", ""); F("비고")?.focus(); }
  else if (rec && rec["주문번호"]) lock(k => REQ_ORDER_LOCK.includes(k), `주문 ${rec["주문번호"]} 에 묶여 구분·단가·수량·금액·부가세·구매처는 바꿀 수 없습니다. 주문을 취소하면 바꿀 수 있습니다.`);
  if (det["합계"] != null && F("금액") && !F("금액").readOnly) { F("금액").readOnly = true; F("금액").classList.add("locked"); F("금액").title = "여비 계산기 합계 (계산기에서 바꾸세요)"; }
  if (typeof confFormInit === "function") confFormInit(det, { locked: !!(rec && reqLocked(rec)) });  // 숨은 칸 #f-_calc 에 기존 계산
  requestFormSync();
  if (!rec && F("신청인") && !F("신청인").value.trim()) F("신청인").focus();  // 처음 쓰는 사람: 비어 있는 신청인부터 (아니면 품목)
  $("#dlg").dataset.initial = formSnapshot();
}
const setLab = (el, text) => { const lab = el?.closest("label")?.querySelector(".lab"); if (lab?.firstChild?.nodeType === 3) lab.firstChild.nodeValue = text; };
function requestFormSync() {
  if ($("#dlg").dataset.kind !== "request") return;
  const t = F("구분")?.value;
  setLab(F("품목"), t === "학회" ? "학회명 " : "품목 ");  // 뒤 공백: 필수 표시(*)와 띄움
  const calc = $("#req-calc-row"); if (calc) calc.hidden = t !== "학회";
  const sn = $("#req-sup-note"); if (sn) sn.hidden = t !== "소모품" || !sn.textContent;
  const vchk = F("부가세구분"), vat = !!vchk?.checked && !vchk.closest("label").hidden;
  setLab(F("단가"), vat ? "단가 (공급가, 부가세 별도) " : "단가 (부가세 포함) ");
  setLab(F("_금액"), vat ? "금액 (단가 × 수량 + 부가세)" : "금액 (단가 × 수량)");
  const vl = F("부가세액")?.closest("label"); if (vl) vl.hidden = !vat;
  updateAmtPreview();
}
// 부가세액 자동 채움: 사용자가 직접 고치기 전까지 단가 × 수량 × 10%
function fillVat(force) {
  const v = F("부가세액"); if (!v || v.readOnly || !F("부가세구분")?.checked) return;
  if (!force && !v.dataset.auto && v.value.trim()) return;
  const u = numOf(F("단가")?.value), q = numOf(F("수량")?.value);
  v.value = u != null && q != null ? fmt(vatOf(u, q)) : ""; v.dataset.auto = "1"; v.removeAttribute("aria-invalid");
}
function updateAmtPreview() {
  const p = F("_금액"); if (!p) return;
  const u = numOf(F("단가")?.value), q = numOf(F("수량")?.value);
  if (u == null || q == null || String(F("단가").value).trim() === "") { p.value = "(자동)"; return; }
  const vat = F("부가세구분")?.checked && !F("부가세액").closest("label").hidden;
  const va = vat ? (numOf(F("부가세액").value) ?? vatOf(u, q)) : 0;
  p.value = `${fmt(Math.round(u * q) + va)}원`;
}
$("#dlg-fields").addEventListener("input", e => {
  if ($("#dlg").dataset.kind !== "request") return;
  const id = e.target.id;
  if (id === "f-단가" || id === "f-수량") { fillVat(false); updateAmtPreview(); }
  else if (id === "f-부가세액") { if (e.isTrusted) e.target.dataset.auto = e.target.value.trim() ? "" : "1"; updateAmtPreview(); }
});
$("#dlg-fields").addEventListener("change", e => {
  if ($("#dlg").dataset.kind !== "request" || e.target.id !== "f-부가세구분") return;
  if (e.target.checked) fillVat(false);
  requestFormSync();
});
// 학회 여비 계산기: openConfCalc 는 conf.js (계산 결과를 #f-_calc 에 담고 금액 칸을 합계로 잠금)
document.addEventListener("click", e => { if (e.target.closest("#req-calc-btn") && typeof openConfCalc === "function") openConfCalc(); });

// 저장 직전 (app.js 제출 처리에서 호출): 기존 행과 합치고, 구분별로 쓰지 않는 칸 정리, 학회 입력은 상세 JSON 으로. 오류 문구를 반환하면 저장 중단
function requestPrepare(rec, row) {
  const cur = row ? reqFind(row) : null;
  const base = cur ? Object.fromEntries(Object.entries(cur).filter(([k]) => !k.startsWith("_"))) : {};
  if (cur && reqLocked(cur)) { const memo = rec["비고"]; Object.keys(rec).forEach(k => delete rec[k]); Object.assign(rec, base, { 비고: memo ?? base["비고"] }); return null; }
  const out = { ...base };
  Object.entries(rec).forEach(([k, v]) => { if (!k.startsWith("_")) out[k] = v; });
  const t = out["구분"];
  if (t === "학회") {
    const det = { ...reqDetail(cur), 학회명: out["품목"] };
    REQ_CONF_KEYS.forEach(([k, dk]) => { det[dk] = rec[k] ?? ""; });
    const calc = typeof confCalcValue === "function" ? confCalcValue() : undefined;  // undefined: 계산기 칸 없음(기존 값 유지)
    if (calc !== undefined) {
      ["v", "in", "out", "합계"].forEach(k => delete det[k]);
      if (calc) Object.assign(det, { v: calc.v, in: calc.in, out: calc.out, 합계: calc.out["합계"] });
    }
    if (det["시작일"] && det["종료일"] && det["종료일"] < det["시작일"]) return "학회 종료일이 시작일보다 빠릅니다.";
    out["상세"] = JSON.stringify(det); out["단가"] = ""; out["수량"] = 1; out["규격"] = "";
    out["부가세구분"] = "N"; out["부가세액"] = "";
    if (det["합계"] != null && det["합계"] !== "") out["금액"] = det["합계"];
  } else {
    out["상세"] = "";
    if (out["수량"] === "" || out["수량"] == null) out["수량"] = 1;
    // 부가세 구분: Y 면 단가는 공급가, 금액 = 단가 × 수량 + 부가세액(비우면 10%). N 이면 단가에 부가세 포함, 금액 = 단가 × 수량
    const vat = rec["부가세구분"] === true;
    out["부가세구분"] = vat ? "Y" : "N";
    if (out["단가"] !== "" && out["단가"] != null) {
      const u = Number(out["단가"]), q = Number(out["수량"]);
      const va = vat ? (rec["부가세액"] === "" || rec["부가세액"] == null ? vatOf(u, q) : Math.round(Number(rec["부가세액"]))) : "";
      if (vat && va < 0) return "부가세액은 0 이상이어야 합니다.";
      out["부가세액"] = va;
      out["금액"] = Math.round(u * q) + (vat ? va : 0);
    } else if (!vat) out["부가세액"] = "";
  }
  if (t !== "소모품") { out["온라인코드"] = ""; out["상품코드"] = ""; out["상품링크"] = ""; out["구매처"] = ""; }
  if (out["상품링크"] && !safeUrl(out["상품링크"])) return "상품링크는 http:// 또는 https:// 로 시작하는 주소여야 합니다.";
  if (cur?.["주문번호"]) REQ_ORDER_LOCK.forEach(k => { if (k in cur) out[k] = cur[k]; });
  if (Number(out["수량"]) <= 0) return "수량은 0보다 커야 합니다.";
  try { if (out["신청인"]) localStorage.setItem("request-name", out["신청인"]); } catch { }
  Object.keys(rec).forEach(k => delete rec[k]); Object.assign(rec, out);
  return null;
}
// 담당자가 승인된 건의 품목·금액 등을 고치면 서버가 '신청'으로 되돌린다 → 미리 묻고, [승인 유지]면 keep_approval
// 반환: null = 저장 취소, {keep_approval:true} = 승인 유지, undefined = 그대로 저장
async function requestConfirmSave(rec, row) {
  const cur = reqFind(row);
  if (!cur || cur["상태"] !== "승인" || !isReqAdmin()) return undefined;
  const nv = (k, v) => k === "부가세구분" ? (v === "Y" ? "Y" : "N") : ["단가", "수량", "금액", "부가세액"].includes(k) ? Number(v || 0) : String(v ?? "").trim();
  const changed = REQ_APPROVAL_KEYS.filter(k => k in rec && nv(k, rec[k]) !== nv(k, cur[k]));
  if (!changed.length) return undefined;
  const r = await confirmDlg({ title: `승인된 신청 수정 · ${cur["신청번호"]}`, body: `바뀌는 칸: ${changed.map(k => k === "부가세구분" ? "부가세" : k).join("·")}\n\n수정하면 승인이 취소되어 '신청'으로 돌아갑니다. 승인을 유지하려면 [승인 유지]를 누르세요.`, verb: "승인 유지", alt: "신청으로 되돌리기" });
  if (r === null) return null;
  return r === "alt" ? undefined : { keep_approval: true };
}
// 저장 알림 (app.js 제출 처리에서 호출): 연구원 새 신청은 다음 할 일(첨부)까지
function requestSavedMsg(saved, isNew) {
  const no = saved?.["신청번호"] || "";
  if (isNew && !isReqAdmin()) showAlert(`${no} 신청했습니다. 견적서는 행을 눌러 첨부하세요.`, "ok");
  else showAlert(`${no ? no + " " : ""}저장했습니다.`, "ok");
  if (saved?.reapproval) showAlert(`${no} 내용이 바뀌어 승인이 취소되고 '신청'으로 돌아갔습니다. 다시 승인하세요.`, "warn");
}
// 저장 뒤: 다른 해의 신청일로 저장했으면 목록 연도를 그 해로 (안 그러면 방금 저장한 행이 안 보임)
function requestAfterSave(saved) {
  const y = String(saved?.["신청일"] || "").slice(0, 4), cur = FILTERS.request.year;
  if (/^\d{4}$/.test(y) && cur && cur !== y && setReqYear(y)) { renderRequest(); showAlert(`${y}년 신청이라 목록 연도를 ${y}로 바꿨습니다.`, "ok"); }
}

// ---------- 결재 (승인 · 반려 · 승인 취소 · 재신청) ----------
const ACT_LABEL = { approve: "승인", reject: "반려", unapprove: "승인 취소", reopen: "재신청" };
const ACT_DONE = { approve: "승인했습니다", reject: "반려했습니다", unapprove: "승인을 취소했습니다 (신청 상태로)", reopen: "반려를 풀고 다시 신청 상태로 돌렸습니다" };
const reqLines = (list, n = 6) => list.slice(0, n).map(r => `${r["신청번호"]} · ${r["품목"] || "-"} · ${fmt(r["금액"])}원`).join("\n") + (list.length > n ? `\n… 외 ${list.length - n}건` : "");
// 선택 바 일괄 처리 중: 선택 바 전체 비활성 + 진행 표시 (연타·충돌 방지)
function setReqBusy(on, text) {
  const bar = $("#req-selbar");
  REQ_BUSY = on;
  if (on) { bar.setAttribute("aria-busy", "true"); $$("#req-selbar button").forEach(b => { b.disabled = true; }); $$("#request-table input[data-rsel], #request-sel-all").forEach(b => { b.disabled = true; }); }
  else { bar.removeAttribute("aria-busy"); $$("#request-table input[data-rsel], #request-sel-all").forEach(b => { b.disabled = false; }); updateSelBar(); }
  if (on && text) $("#req-sel-n").textContent = text;
}
async function runReqAction(list, action, extra = {}, opts = {}) {
  const from = REQ_FOCUS;
  if (!list.length) { showAlert("처리할 수 있는 신청이 없습니다.", "warn"); return false; }
  const bulk = from === "selbar";
  if (bulk) setReqBusy(true, `${ACT_LABEL[action]} 중… 0/${list.length}`);
  let ok = 0, batched = false; const errs = [];
  if (list.length > 1) {  // 일괄 엔드포인트가 있으면 한 번에 저장 (없으면 한 건씩)
    try {
      const res = await api("POST", "/api/request/batch-action", { rows: list.map(r => ({ row: r._row, expect: expectOf("request", r) })), action, extra });
      const fails = res.errors || res.failed || [];
      fails.forEach(f => errs.push(typeof f === "string" ? f : `${f["신청번호"] || f.row || ""}: ${f.error || f.detail || f.message || ""}`));
      ok = typeof res.done === "number" ? res.done : Array.isArray(res.done) ? res.done.length : typeof res.count === "number" ? res.count : Array.isArray(res.numbers) ? res.numbers.length : list.length - fails.length;
      batched = true;
    } catch (e) { if (e.status !== 404 && e.status !== 405) { errs.push(e.message); batched = true; } }
  }
  if (!batched) {
    let i = 0;
    for (const r of list) {
      if (bulk) $("#req-sel-n").textContent = `${ACT_LABEL[action]} 중… ${++i}/${list.length}`;
      try { await api("POST", `/api/request/${r._row}/action`, { action, extra, expect: expectOf("request", r) }); ok++; }
      catch (e) { errs.push(`${r["신청번호"]}: ${e.message}`); }
    }
  }
  REQSEL.clear();
  const one = ok === 1 && list.length === 1;
  if (ok) showAlert(`${one ? list[0]["신청번호"] + " " : ok + "건 "}${ACT_DONE[action]}.` + (opts.skipped ? ` ${ACT_LABEL[action]}할 수 없는 ${opts.skipped}건은 건너뛰었습니다.` : ""), "ok", one || (batched && !errs.length) ? { undo: true } : {});  // 일괄 엔드포인트는 한 번 저장이라 되돌리기 가능
  if (errs.length) showAlert(`${ACT_LABEL[action]} 실패 ${errs.length}건 — ${errs.join(" / ")}`, "error");
  await load();
  if (bulk) setReqBusy(false);
  reqRefocus(from);
  return ok > 0;
}
async function rejectRequests(list, skipped = 0) {
  const from = REQ_FOCUS;
  if (!list.length) return showAlert("반려할 수 있는 신청이 없습니다 (신청·승인 상태, 주문 전).", "warn");
  const reason = await confirmDlg({ title: `신청 ${list.length}건 반려`, body: `${reqLines(list)}\n\n신청인이 목록에서 사유를 볼 수 있습니다. 반려한 건은 '재신청'으로 다시 신청 상태로 돌릴 수 있습니다.`, verb: "반려", input: { label: "반려 사유", value: "", required: true, error: "반려 사유를 입력하세요. 신청인에게 그대로 보입니다." } });
  if (reason === null) { REQ_FOCUS = null; return; }
  REQ_FOCUS = from;
  return runReqAction(list, "reject", { 사유: String(reason).trim() }, { skipped });
}

// ---------- 품의 전환 ----------
function convertRequests(list) {
  const from = REQ_FOCUS;
  const bad = list.filter(r => !canConvert(r));
  if (!list.length || bad.length) { showAlert(`승인된 신청만 품의로 전환할 수 있습니다${bad.length ? ": " + listLabel(bad) : ""}.`, "warn"); return; }
  const items = list.map(r => r["품목"]), names = [...new Set(list.map(r => r["신청인"]).filter(Boolean))];
  const tasks = [...new Set(list.map(r => r["관련과제"]).filter(Boolean))];
  const orders = [...new Set(list.map(r => r["주문번호"] || ""))];
  const order = orders.length === 1 && orders[0] ? (DATA.order || []).find(o => o["주문번호"] === orders[0]) : null;
  const preset = {
    원인발생일: today(), 적요: items.length <= 3 ? items.join(", ") : `${items.slice(0, 3).join(", ")} 외 ${items.length - 3}건`,
    금액: list.reduce((a, r) => a + (r["금액"] || 0), 0), 품의자: names.join(", "), 거래처: order?.["거래처"] || "", 비고: "", 상태: "대기",
  };
  if (tasks.length === 1 && fundOptions().includes(tasks[0])) preset["재원"] = tasks[0];
  openForm("req", null, preset, { convertRequests: list.map(r => r._row), title: `품의 전환 - 신청 ${listLabel(list)}` });
  reqFormNote(`저장하면 품의 1건이 만들어지고 신청 ${list.length}건이 '품의전환'으로 바뀝니다 (되돌리기 가능). 비고에는 '신청 ${list.map(r => r["신청번호"]).join(", ")}'가 자동으로 붙습니다. 재원·예산목을 고르세요.`);
  $("#dlg").dataset.initial = formSnapshot();
  DLG_ON_SAVED = () => reqRefocus(from);
}

// ---------- 삭제 ----------
async function deleteRequests(list) {
  const from = REQ_FOCUS;
  const bad = list.filter(r => !canDelete(r));
  if (!list.length) return;
  if (bad.length) return showAlert(`품의로 전환됐거나 주문에 묶인 신청은 삭제할 수 없습니다: ${listLabel(bad)}`, "warn");
  if (!isReqAdmin() && list.some(r => r["상태"] !== "신청")) return showAlert("승인 전(신청 상태)인 건만 삭제할 수 있습니다.", "warn");
  const att = list.reduce((a, r) => a + rattCount(r), 0);
  const body = reqLines(list) + (att ? `\n\n첨부 ${att}개도 함께 지우고 드라이브 휴지통으로 옮깁니다.` : "") + (list.length === 1 && !att ? "\n\n삭제 직후 알림의 [되돌리기]로 복구할 수 있습니다." : "");
  if (!await confirmDlg({ title: `신청 ${list.length}건 삭제`, body, verb: att ? "첨부와 함께 삭제" : "삭제", danger: true })) { REQ_FOCUS = null; return; }
  const bulk = from === "selbar" && list.length > 1;
  if (bulk) setReqBusy(true, `삭제 중… 0/${list.length}`);
  let ok = 0, i = 0; const errs = [], warns = [];
  for (const r of [...list].sort((a, b) => b._row - a._row)) {  // 아래 행부터 (행 번호 밀림 방지)
    if (bulk) $("#req-sel-n").textContent = `삭제 중… ${++i}/${list.length}`;
    try { const res = await api("DELETE", `/api/request/${r._row}`, { expect: expectOf("request", r), cascade: rattCount(r) > 0 }); ok++; if (res?.warning) warns.push(res.warning); }
    catch (e) { errs.push(`${r["신청번호"]}: ${e.message}`); }
  }
  REQSEL.clear(); if (list.some(r => r._row === RD.row)) closeReqDrawer();
  if (ok) showAlert(`신청 ${ok}건을 삭제했습니다.` + (warns.length ? " " + warns.join(" ") : ""), warns.length ? "warn" : "ok", ok === 1 && list.length === 1 && !att ? { undo: true } : {});
  if (errs.length) showAlert("삭제 실패 — " + errs.join(" / "), "error");
  await load();
  if (bulk) setReqBusy(false);
  reqRefocus(from);
}

// ---------- 상세 패널 ----------
const RD = { row: null, items: null, drive: null, listErr: null, seq: 0, shown: null, render: null };
const RATT_MAX = 25 * 1024 * 1024;  // 서버 한도와 같음 (보내기 전에 검사)
function markReqRow() { $$("#request-table tbody tr[data-row]").forEach(tr => tr.classList.toggle("selected", Number(tr.dataset.row) === RD.row)); }
function openReqDrawer(row, opts = {}) {
  RD.row = row; RD.items = null; RD.listErr = null;
  $("#ai-drawer").hidden = true;
  $("#req-drawer").hidden = false; document.body.classList.add("drawer-open");
  markReqRow(); reqScrollHint(); RD.render = renderReqDrawer(true);
  if (opts.focus !== false) $("#rd-close").focus();
}
function closeReqDrawer() {
  const dr = $("#req-drawer"); if (!dr || (dr.hidden && RD.row == null)) return;
  const ae = document.activeElement, restore = !dr.hidden && (!ae || ae === document.body || dr.contains(ae)), row = RD.row;
  dr.hidden = true; document.body.classList.remove("drawer-open"); RD.row = null; markReqRow(); reqScrollHint();
  if (restore && row != null) $(`#request-table tbody tr[data-row="${row}"] .rowbtn`)?.focus();
}
$("#rd-close").addEventListener("click", closeReqDrawer);
// Esc: 대화상자가 열려 있으면 대화상자 먼저. 드로어 안 입력 칸(메모 등)에서는 닫지 않음 (입력 중인 글이 사라지지 않게)
document.addEventListener("keydown", e => { if (e.key === "Escape" && !e.defaultPrevented && !$("#req-drawer").hidden && !document.querySelector("dialog[open]") && !e.target.closest?.("#req-drawer input, #req-drawer textarea, #req-drawer select")) closeReqDrawer(); });
const rdRows = () => $$("#request-table tbody tr[data-row]").map(tr => Number(tr.dataset.row));
function updateRdNav() {
  if (RD.row == null || $("#req-drawer").hidden) return;
  const rows = rdRows(), i = rows.indexOf(RD.row);
  $("#rd-prev").disabled = i <= 0; $("#rd-next").disabled = i < 0 || i >= rows.length - 1;
  $("#rd-pos").textContent = rows.length ? `${i < 0 ? "–" : i + 1} / ${rows.length}` : "";
}
function rdNav(d) {
  const rows = rdRows(), i = rows.indexOf(RD.row), j = i + d;
  if (i < 0 || j < 0 || j >= rows.length) return;
  if ($("#rd-body").contains(document.activeElement)) $("#req-drawer").focus();
  openReqDrawer(rows[j], { focus: false });
  $(`#request-table tbody tr[data-row="${rows[j]}"]`)?.scrollIntoView({ block: "nearest" });
}
$("#rd-prev").addEventListener("click", () => rdNav(-1));
$("#rd-next").addEventListener("click", () => rdNav(1));
$("#req-drawer").addEventListener("keydown", e => {
  if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
  const d = { ArrowUp: -1, PageUp: -1, ArrowDown: 1, PageDown: 1 }[e.key]; if (!d) return;
  if (e.target.closest("input, select, textarea")) return;
  e.preventDefault(); rdNav(d);
});

async function renderReqDrawer(fetchItems) {
  const r = reqFind(RD.row);
  if (!r) { closeReqDrawer(); return; }
  const st = r["상태"], admin = isReqAdmin(), det = reqDetail(r), conf = r["구분"] === "학회", vat = !conf && vatOn(r);
  $("#rd-title").textContent = r["신청번호"];
  $("#rd-sub").innerHTML = `${esc(r["구분"])} · ${esc(r["신청인"])} · <b>${fmt(r["금액"])}원</b>`;
  updateRdNav();
  const keep = $("#ratt-form") && RD.shown === r._row ? { note: $("#ratt-form").note.value } : null;
  const seq = ++RD.seq;
  if (fetchItems || (!RD.items && !RD.listErr)) {
    try { const d = await api("GET", `/api/ratt/${encodeURIComponent(r["신청번호"])}`); if (seq !== RD.seq || RD.row !== r._row) return; RD.items = d.items; RD.drive = d.drive; RD.listErr = null; }
    catch (e) { if (seq !== RD.seq || RD.row !== r._row) return; RD.items = null; RD.listErr = e.message; }  // 목록 조회 실패 ≠ 드라이브 미연결
  }
  if (seq !== RD.seq) return;
  const body = $("#rd-body"), scroll = RD.shown === r._row ? body.scrollTop : 0;
  const items = RD.items || [], drive = RD.drive || {}, listErr = RD.listErr;
  const kv = (k, v, cls = "") => `<b>${esc(k)}</b><span class="xd-ro${cls}">${v === "" || v == null ? '<span class="muted">-</span>' : v}</span>`;
  const t = s => esc(s ?? "");
  const won = v => v !== "" && v != null ? fmt(v) + "원" : "";
  const fund = DATA.funds.find(f => f["재원코드"] === r["관련과제"]);
  const link = safeUrl(r["상품링크"]);
  const order = r["주문번호"] ? (DATA.order || []).find(o => o["주문번호"] === r["주문번호"]) : null;
  const sup = r["구분"] === "소모품";
  const vatAmt = Number(r["부가세액"]) || 0;
  const money = vat
    ? [kv("단가", won(r["단가"]) + (r["단가"] !== "" && r["단가"] != null ? ' <span class="muted">공급가</span>' : "")), kv("수량", fmt(r["수량"])), kv("공급가액", won((Number(r["금액"]) || 0) - vatAmt)), kv("부가세액", won(vatAmt)), kv("금액", `<b>${fmt(r["금액"])}원</b>`)]
    : [kv("단가", won(r["단가"])), kv("수량", fmt(r["수량"])), kv("금액", `<b>${fmt(r["금액"])}원</b>`)];
  const info = [
    kv("구분", t(r["구분"])), kv("신청인", t(r["신청인"])), kv("신청일", t(r["신청일"])),
    kv("관련과제", r["관련과제"] ? `${t(r["관련과제"])}${fund?.["과제명"] ? ` <span class="muted">${t(fund["과제명"])}</span>` : ""}` : ""),
    kv(conf ? "학회명" : "품목", t(r["품목"])),
    ...(conf ? [
      kv("기간", det["시작일"] || det["종료일"] ? `${t(det["시작일"] || "?")} ~ ${t(det["종료일"] || "?")}` : ""), kv("국내/국외", t(det["국내외"])), kv("장소", t(det["장소"])),
      kv("참가자", t(det["참가자"])), kv("등록비", won(det["등록비"])), kv("금액", `<b>${fmt(r["금액"])}원</b>`),
      typeof confDrawerKv === "function" ? confDrawerKv(det, kv) : "",
    ] : [kv("규격", t(r["규격"])), ...money]),
    kv("사유", t(r["사유"]), " multi"), kv("희망일", t(r["희망일"])),
    ...(sup ? [kv("구매처", r["구매처"] ? `${t(r["구매처"])}${supOff(r["구매처"]) ? ' <span class="muted">(현재 이용 불가)</span>' : ""}` : ""), kv("온라인코드", t(r["온라인코드"])), kv("상품코드", t(r["상품코드"])),
      kv("상품링크", link ? `<a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${esc(reqExcerpt(link, 48))}</a>` : t(r["상품링크"])),
      kv("주문", order ? `${t(order["주문번호"])} <span class="muted">주문 ${t(mmdd(order["주문일"]))}${order["배송일"] ? ` · 배송 ${t(mmdd(order["배송일"]))}` : " · 배송 전"}</span>` : t(r["주문번호"]))] : []),
    kv("연결 품의", r["연결품의번호"] ? `${t(r["연결품의번호"])}${admin ? ` <button type="button" class="lnk" data-rd="gotoreq">품의내역에서 보기</button>` : ""}` : ""),
    kv("비고", t(r["비고"]), " multi"),
  ].join("");
  // 담당자 동작 (상태에 따라)
  const btn = (act, label, title, primary) => `<button type="button" class="btn btn-sm${primary ? " btn-primary" : ""}" data-rd="${act}" title="${esc(title)}">${label}</button>`;
  const bundle = r["주문번호"] ? DATA.request.filter(q => q["주문번호"] === r["주문번호"] && canConvert(q)) : [r];
  const acts = !admin ? "" : [
    canApprove(r) ? btn("approve", "승인", "결재인·결재일(오늘)을 기록하고 승인", true) : "",
    canReject(r) ? btn("reject", "반려", "사유를 입력하고 반려") : "",
    st === "승인" && !r["주문번호"] ? btn("unapprove", "승인 취소", "신청 상태로 되돌림") : "",
    st === "반려" ? btn("reopen", "재신청", "반려를 풀고 신청 상태로 되돌림") : "",
    canConvert(r) ? btn("convert", r["주문번호"] && bundle.length > 1 ? `품의 전환 (주문 ${bundle.length}건)` : "품의 전환", r["주문번호"] ? `주문 ${r["주문번호"]} 묶음 전체를 품의 1건으로` : "이 신청으로 품의 작성", st === "승인") : "",
    canOrder(r) ? btn("order", "주문 생성", "이 소모품으로 주문 1건 생성 (적립금 사용 기록 가능)") : "",
  ].join("");
  const rejNote = st === "반려" || r["반려사유"] ? kv("반려사유", `<span class="rej">${t(r["반려사유"])}</span>`, " multi") : "";
  const thumb = a => { const n = a["파일명"] || "", id = a["드라이브파일ID"]; return XD_IMG.test(n) && id ? `<img class="xd-thumb" loading="lazy" alt="" src="/api/ratt/thumb/${encodeURIComponent(id)}" data-ext="${esc(fileExt(n))}">` : `<span class="xd-chip" aria-hidden="true">${esc(fileExt(n))}</span>`; };
  const canDelAtt = admin || st === "신청" || st === "반려";
  const ownEdit = canEditReq(r), ownDel = canDelete(r) && (admin || st === "신청");
  const canUp = !listErr && drive.connected;
  const delWhy = reqLocked(r) ? "품의로 전환된 신청은 지울 수 없습니다" : r["주문번호"] ? `주문 ${r["주문번호"]} 를 먼저 취소하세요` : !admin ? `${st === "반려" ? "반려된" : "승인된"} 신청은 지울 수 없습니다. 취소가 필요하면 담당자에게 알려 주세요.` : "신청 상태에서만 삭제할 수 있습니다";
  const attHint = r["구분"] === "장비" ? "견적서·사양서를 올리세요." : "견적서·인보이스·요금제 안내 등을 올리세요.";
  const attState = listErr
    ? `<p class="toolbar-note warn">첨부 목록을 불러오지 못했습니다. <button type="button" class="lnk" data-rd="rattretry">다시 시도</button>${admin ? ` <span class="muted">(${esc(listErr)})</span>` : ""}</p>`
    : !drive.connected ? `<p class="toolbar-note warn">구글 드라이브가 연결되지 않아 첨부를 올릴 수 없습니다. ${admin ? "오른쪽 위 설정(톱니)에서 연결하세요." : "담당자에게 알려 주세요."}${admin && drive.error ? " (" + esc(drive.error) + ")" : ""}</p>` : "";
  body.innerHTML = `
    <section class="xd-sec xd-info rd-approval">
      <h3>결재 <span class="badge ${esc(st)}">${esc(st)}</span></h3>
      <div class="kv">${kv("결재인", t(r["결재인"]))}${kv("결재일", t(r["결재일"]))}${rejNote}</div>
      ${acts ? `<div class="rd-actions" role="group" aria-label="담당자 처리">${acts}</div>` : ""}
      ${!admin && st === "반려" ? '<p class="toolbar-note">반려된 신청입니다. 사유를 반영해 새로 신청하거나 담당자에게 재신청을 요청하세요.</p>' : ""}
      ${!admin && st === "품의전환" ? '<p class="toolbar-note">담당자가 구매 품의(결재 문서)를 올렸습니다. 더 할 일은 없습니다.</p>' : ""}
    </section>
    <section class="xd-sec xd-info">
      <h3>신청 정보 <span class="sp"></span>${ownEdit ? `<button type="button" class="btn btn-sm" data-rd="edit"${reqLocked(r) ? ' title="비고만 수정할 수 있습니다"' : ""}>${reqLocked(r) ? "비고 수정" : "수정"}</button>` : ""}</h3>
      <div class="kv">${info}</div>
    </section>
    <section class="xd-sec">
      <h3>첨부 <span class="toolbar-note">${listErr ? "" : items.length + "개"}</span><span class="sp"></span>${safeUrl(r["첨부폴더"]) ? `<a class="btn btn-sm" href="${esc(safeUrl(r["첨부폴더"]))}" target="_blank" rel="noopener noreferrer">폴더 열기</a>` : ""}</h3>
      ${attState}
      ${items.length ? `<div class="table-wrap"><table class="grid compact evid-table"><thead><tr><th class="xd-th-cell"><span class="sr-only">미리보기</span></th><th>파일명</th><th class="num">크기</th><th>업로드</th><th><span class="sr-only">작업</span></th></tr></thead><tbody>
        ${items.map(a => `<tr><td class="xd-th-cell">${thumb(a)}</td><td class="evid-name">${safeUrl(a.url) ? `<a href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer" title="새 창에서 열기">${esc(a["원본파일명"] || a["파일명"])}</a>` : esc(a["원본파일명"] || a["파일명"])}${a["비고"] ? `<div class="toolbar-note">${esc(a["비고"])}</div>` : ""}</td><td class="num">${a["크기"] ? Math.max(1, Math.round(a["크기"] / 1024)).toLocaleString() + " KB" : ""}</td><td>${esc(mmdd(a["업로드일"]))}</td><td>${canDelAtt ? `<button type="button" class="btn btn-sm btn-danger" data-rattdel="${a._row}" data-name="${esc(a["원본파일명"] || a["파일명"])}" title="장부에서 지우고 드라이브 휴지통으로 이동">삭제</button>` : ""}</td></tr>`).join("")}
      </tbody></table></div>` : listErr ? "" : `<p class="toolbar-note">첨부가 없습니다. ${attHint}</p>`}
      <form id="ratt-form" class="evid-form">
        <label class="file-pick">파일 <span class="file-pick-row"><input type="file" name="files" multiple ${canUp ? "" : "disabled"}><span class="btn btn-sm file-btn" aria-hidden="true">파일 선택</span><span class="file-names">선택된 파일 없음</span></span></label>
        <label>메모 <input type="text" name="note" placeholder="예: 견적서 (비워도 됨)"></label>
        <div class="wide evid-drop-row"><div class="drop" id="ratt-drop"${admin ? ' title="파일 이름은 신청번호_품목_원본이름 으로 저장됩니다"' : ""}><b>파일을 여기로 끌어다 놓기</b>${admin ? ` · 신청/${esc((r["신청일"] || "").slice(0, 4))}/${esc(r["신청번호"])}` : " · 25MB 이하"}</div><button type="submit" class="btn btn-primary btn-sm" ${canUp ? "" : "disabled"}>업로드</button></div>
      </form>
    </section>
    <section class="xd-sec xd-foot">
      <button type="button" class="btn btn-sm btn-danger" data-rd="delete"${ownDel ? "" : " disabled"} title="${esc(ownDel ? (items.length ? "첨부와 함께 삭제" : "이 신청 삭제 (되돌리기 가능)") : delWhy)}">이 신청 삭제</button>
      ${ownDel ? "" : `<span class="toolbar-note">${esc(delWhy)}</span>`}
    </section>`;
  bindRattForm(r);
  $$("img.xd-thumb", body).forEach(img => img.addEventListener("error", () => { if (!img.isConnected) return; const c = document.createElement("span"); c.className = "xd-chip"; c.setAttribute("aria-hidden", "true"); c.textContent = img.dataset.ext; img.replaceWith(c); }));
  if (keep) $("#ratt-form").note.value = keep.note;
  RD.shown = r._row; body.scrollTop = scroll;
}
function bindRattForm(r) {
  const form = $("#ratt-form"); if (!form) return;
  const fileInput = form.querySelector("[name=files]"), names = form.querySelector(".file-names");
  const showNames = () => { const f = fileInput.files; names.textContent = f.length ? (f.length === 1 ? f[0].name : `${f[0].name} 외 ${f.length - 1}개`) : "선택된 파일 없음"; };
  fileInput.addEventListener("change", showNames);
  const dz = $("#ratt-drop");
  ["dragenter", "dragover"].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add("hot"); }));
  ["dragleave", "drop"].forEach(ev => dz.addEventListener(ev, () => dz.classList.remove("hot")));
  dz.addEventListener("drop", e => {
    e.preventDefault();
    if (form.dataset.busy) { showAlert("업로드 중입니다. 끝난 뒤 다시 놓아 주세요.", "warn"); return; }
    if (e.dataTransfer.files.length && !fileInput.disabled) { fileInput.files = e.dataTransfer.files; showNames(); form.requestSubmit(); }
  });
  form.addEventListener("submit", async e => {
    e.preventDefault();
    if (form.dataset.busy) return;  // 업로드 중 다시 제출(드롭·Enter) 방지
    const files = [...fileInput.files];
    if (!files.length) { showAlert("파일을 선택하세요.", "warn"); return; }
    const big = files.filter(f => f.size > RATT_MAX), empty = files.filter(f => !f.size);
    if (big.length) { showAlert(`25MB 를 넘는 파일은 올릴 수 없습니다: ${big.map(f => f.name).join(", ")}. 아무것도 올리지 않았습니다.`, "error"); return; }
    if (empty.length) { showAlert(`빈 파일입니다: ${empty.map(f => f.name).join(", ")}. 아무것도 올리지 않았습니다.`, "error"); return; }
    const fd = new FormData(); files.forEach(f => fd.append("files", f)); fd.append("note", form.note.value.trim());
    const btn = form.querySelector("button[type=submit]"); btn.disabled = true; btn.textContent = `업로드 중… (${files.length}개)`;
    form.dataset.busy = "1"; form.setAttribute("aria-busy", "true");
    try {
      const d = await api("POST", `/api/ratt/${encodeURIComponent(r["신청번호"])}`, fd);
      showAlert(`${r["신청번호"]} 첨부 ${d.items.length}개를 올렸습니다.`, "ok");
      delete form.dataset.busy; form.removeAttribute("aria-busy");
      await load(); if (RD.row === r._row) await (RD.render = renderReqDrawer(true));
    } catch (err) { showAlert("업로드 실패: " + err.message, "error"); btn.disabled = false; btn.textContent = "업로드"; }
    finally { delete form.dataset.busy; form.removeAttribute("aria-busy"); }
  });
}
$("#rd-body").addEventListener("click", async e => {
  const del = e.target.closest("[data-rattdel]");
  if (del) {
    if (!await confirmDlg({ title: "첨부 삭제", body: `'${del.dataset.name}' 을 장부에서 지우고 드라이브 휴지통으로 옮깁니다.`, verb: "삭제", danger: true })) return;
    const row = Number(del.dataset.rattdel), a = (RD.items || []).find(x => x._row === row);
    try {
      const res = await api("DELETE", `/api/ratt/${row}`, { expect: a ? { 신청번호: a["신청번호"], 파일명: a["파일명"] } : undefined, ...(isReqAdmin() ? { extra: { admin: true } } : {}) });
      showAlert(res.warning || "첨부를 삭제했습니다.", res.warning ? "warn" : "ok"); await load(); if (RD.row != null) await (RD.render = renderReqDrawer(true));
      ($("#rd-body [data-rattdel]") || $("#ratt-form input[name=files]") || $("#rd-close")).focus();
    }
    catch (err) { showAlert(err.message, "error"); }
    return;
  }
  const b = e.target.closest("button[data-rd]"); if (!b) return;
  const r = reqFind(RD.row); if (!r) return;
  const act = b.dataset.rd;
  REQ_FOCUS = "drawer";
  if (act === "edit") return editRequest(r._row);
  if (act === "rattretry") { RD.listErr = null; RD.render = renderReqDrawer(true); await RD.render; $("#ratt-form input[name=files]")?.focus(); return; }
  if (act === "delete") return deleteRequests([r]);
  if (act === "approve" || act === "unapprove" || act === "reopen") { b.disabled = true; const ok = await runReqAction([r], act); if (!ok) b.disabled = false; return; }
  if (act === "reject") return rejectRequests([r]);
  if (act === "convert") return convertRequests(r["주문번호"] ? DATA.request.filter(q => q["주문번호"] === r["주문번호"] && canConvert(q)) : [r]);
  if (act === "order") return openOrderDialog([r]);
  if (act === "confview") { const d = reqDetail(r); return openConfCalc({ readonly: true, rec: r, calc: { v: d.v, in: d.in, out: d.out } }); }
  if (act === "gotoreq") {
    const no = r["연결품의번호"]; setMode("main"); switchTab("req");
    FILTERS.req = { q: no }; $$("[data-filter][data-kind=req]").forEach(el => { el.value = el.dataset.filter === "q" ? no : ""; }); renderList("req");
  }
});

// ---------- 소모품 주문 ----------
let ORDER_ROWS = [];
const depBalance = vendor => DATA.deposit.filter(x => x["거래처"] === vendor).reduce((a, x) => a + (x["구분"] === "적립" ? 1 : -1) * (x["금액"] || 0), 0);
function openOrderDialog(list) {
  const bad = list.filter(r => !canOrder(r));
  if (!list.length || bad.length) { showAlert(`주문 전인 승인된 소모품 신청만 주문으로 묶을 수 있습니다${bad.length ? ": " + listLabel(bad) : ""}.`, "warn"); return; }
  const sups = [...new Set(list.map(r => r["구매처"] || ""))];
  if (sups.length > 1) { showAlert(`${SUP_MIXED}: ${list.map(r => `${r["신청번호"]} ${r["구매처"] || "구매처 없음"}`).join(", ")}`, "warn"); return; }
  ORDER_ROWS = list.map(r => r._row);
  const sum = list.reduce((a, r) => a + (r["금액"] || 0), 0);
  $("#order-lines").innerHTML = `<thead><tr><th>신청번호</th><th>품목</th><th>온라인코드</th><th class="num">수량</th><th class="num amt">금액</th><th>신청인</th></tr></thead><tbody>${list.map(r => `<tr><td>${esc(r["신청번호"])}</td><td>${esc(r["품목"])}${r["규격"] ? ` <span class="muted">${esc(r["규격"])}</span>` : ""}</td><td>${esc(r["온라인코드"] || "")}</td><td class="num">${fmt(r["수량"])}</td><td class="num amt">${fmt(r["금액"])}</td><td>${esc(r["신청인"])}</td></tr>`).join("")}</tbody><tfoot><tr class="total"><td>합계 ${list.length}건</td><td></td><td></td><td class="num">${fmt(list.reduce((a, r) => a + (Number(r["수량"]) || 0), 0))}</td><td class="num amt">${fmt(sum)}</td><td></td></tr></tfoot>`;
  let vendor = sups[0] || "알파몰"; if (!sups[0]) try { vendor = localStorage.getItem("request-order-vendor") || vendor; } catch { }  // 기본: 신청의 구매처
  $("#ord-date").value = today(); $("#ord-vendor").value = vendor; $("#ord-pay").value = fmt(sum); $("#ord-dep").checked = true; $("#ord-user").value = ""; $("#ord-memo").value = "";
  $("#dlg-order").dataset.sum = sum;
  updateOrderNote();
  $("#dlg-order").showModal(); $("#ord-vendor").focus();
}
function updateOrderNote() {
  const sum = Number($("#dlg-order").dataset.sum || 0), vendor = $("#ord-vendor").value.trim() || "알파몰", pay = numOf($("#ord-pay").value) ?? sum;
  const bal = depBalance(vendor), use = $("#ord-dep").checked;
  const note = $("#ord-note");
  note.textContent = `주문금액 ${fmt(sum)}원 · 결제 ${fmt(pay)}원` + (use ? ` · ${vendor} 적립금 잔액 ${fmt(bal)}원 → 사용 후 ${fmt(bal - pay)}원` : " · 적립금 사용 기록 안 함");
  note.classList.toggle("warn", use && bal - pay < 0);
}
$("#dlg-order").addEventListener("input", updateOrderNote);
$("#ord-cancel").addEventListener("click", () => $("#dlg-order").close());
$("#dlg-order-form").addEventListener("submit", async e => {
  e.preventDefault();
  const d = $("#dlg-order"); if (d.dataset.busy) return;
  const date = $("#ord-date").value, vendor = $("#ord-vendor").value.trim(), payRaw = $("#ord-pay").value.trim(), pay = payRaw ? numOf(payRaw) : "";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) { showAlert("주문일을 입력하세요.", "warn"); $("#ord-date").focus(); return; }
  if (pay === null || (pay !== "" && pay < 0)) { showAlert("결제금액은 0 이상의 숫자로 입력하세요.", "warn"); $("#ord-pay").focus(); return; }
  const list = ORDER_ROWS.map(reqFind).filter(Boolean);
  if (list.length !== ORDER_ROWS.length) { showAlert("목록이 바뀌었습니다. 새로고침 후 다시 시도하세요.", "error"); return; }
  const btn = $("#ord-save"); d.dataset.busy = "1"; btn.disabled = true;
  try {
    const res = await api("POST", "/api/order/create", { rows: ORDER_ROWS, expects: list.map(r => expectOf("request", r)), extra: { 주문일: date, 거래처: vendor, 결제금액: pay, 적립금사용: $("#ord-dep").checked, 사용자: $("#ord-user").value.trim(), 비고: $("#ord-memo").value.trim() } });
    try { if (vendor) localStorage.setItem("request-order-vendor", vendor); } catch { }
    d.close(); REQSEL.clear();
    showAlert(`주문 ${res.order["주문번호"]} 생성 · 신청 ${res.numbers.length}건${res.deposit ? ` · 적립금 사용 ${fmt(res.deposit["금액"])}원 기록` : ""}`, "ok", { undo: true });
    await load();
    reqRefocus();
  } catch (err) { showAlert("주문 생성 실패: " + err.message, "error"); }
  finally { delete d.dataset.busy; btn.disabled = false; }
});

function renderOrders() {
  const sec = $("#order-section"), show = isReqAdmin() && reqType() === "소모품";
  sec.hidden = !show; if (!show) return;
  const y = FILTERS.request.year;
  const rows = (DATA.order || []).filter(o => !y || (o["주문일"] || "").startsWith(y)).sort((a, b) => (b["주문일"] || "").localeCompare(a["주문일"] || "") || b._row - a._row);
  const cnt = o => String(o["신청번호목록"] || "").split(",").filter(s => s.trim()).length;
  $("#order-table").innerHTML = `<thead><tr><th>주문번호</th><th class="ctr">주문일</th><th class="ctr">배송일</th><th>거래처</th><th class="num amt">주문금액</th><th class="num">결제금액</th><th class="ctr">적립금</th><th class="num">건수</th><th>신청번호</th><th class="actions">작업</th></tr></thead><tbody>${rows.map(o => `<tr data-orow="${o._row}">
    <td>${esc(o["주문번호"])}</td><td class="ctr" title="${esc(o["주문일"])}">${esc(mmdd(o["주문일"]))}</td>
    <td class="ctr">${o["배송일"] ? `<span title="${esc(o["배송일"])}">${esc(mmdd(o["배송일"]))}</span> <button type="button" class="lnk" data-ord="undeliver" data-row="${o._row}" title="배송일 지우기 (배송 전으로)">지우기</button>` : `<button type="button" class="btn btn-sm" data-ord="deliver" data-row="${o._row}">배송 등록</button>`}</td>
    <td>${esc(o["거래처"])}</td><td class="num amt">${fmt(o["주문금액"])}</td><td class="num">${fmt(o["결제금액"])}</td><td class="ctr">${o["적립금사용"] === "Y" ? "사용" : '<span class="muted">-</span>'}</td><td class="num">${cnt(o)}</td>
    <td class="wrap" title="${esc(o["신청번호목록"])}">${esc(o["신청번호목록"])}</td>
    <td class="actions"><button type="button" class="btn btn-sm" data-ord="sheet" data-row="${o._row}">발주서</button><button type="button" class="btn btn-sm btn-danger" data-ord="cancel" data-row="${o._row}"${o["배송일"] ? ' disabled title="배송된 주문은 배송일을 지운 뒤 취소할 수 있습니다"' : ' title="주문 취소: 신청 주문 해제, 적립금 사용 기록 삭제"'}>취소</button></td></tr>`).join("")
    || `<tr><td class="empty" colspan="10">${y ? y + "년 " : ""}주문이 없습니다. 승인된 소모품 신청을 체크하고 [주문 생성]을 누르세요.</td></tr>`}</tbody>`;
  $("#order-table").closest(".table-wrap").classList.toggle("empty", !rows.length);
}
$("#order-table").addEventListener("click", async e => {
  const b = e.target.closest("button[data-ord]"); if (!b || b.disabled) return;
  const row = Number(b.dataset.row), o = (DATA.order || []).find(x => x._row === row); if (!o) return;
  const act = b.dataset.ord, no = o["주문번호"];
  if (act === "sheet") return openOrderSheet(row);
  let extra = {}, msg;
  if (act === "deliver") {
    const d = await confirmDlg({ title: "배송 등록", body: `주문 ${no} (${o["거래처"]}, ${fmt(o["주문금액"])}원)의 배송일을 기록합니다.`, verb: "등록", input: { label: "배송일", type: "date", value: today() } });
    if (d === null) return;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) { showAlert("배송일 형식이 올바르지 않습니다 (YYYY-MM-DD).", "warn"); return; }
    extra = { 배송일: d }; msg = `주문 ${no} 배송일 ${mmdd(d)} 등록`;
  } else if (act === "undeliver") msg = `주문 ${no} 배송일을 지웠습니다`;
  else if (act === "cancel") {
    if (!await confirmDlg({ title: "주문 취소", body: `주문 ${no} 을(를) 취소합니다.\n\n묶인 신청 ${String(o["신청번호목록"] || "").split(",").filter(s => s.trim()).length}건은 주문이 해제되어 '승인' 상태로 남고, 적립금 사용 기록${o["적립금사용"] === "Y" ? `(${fmt(o["결제금액"])}원)` : ""}이 있으면 함께 삭제됩니다.`, verb: "주문 취소", danger: true })) return;
    msg = `주문 ${no} 을(를) 취소했습니다`;
  }
  b.disabled = true;
  try {
    const res = await api("POST", `/api/order/${row}/action`, { action: act, extra, expect: expectOf("order", o) });
    showAlert(msg + (res.released ? ` (신청 ${res.released.length}건 해제${res.deposit_removed ? ", 적립금 사용 기록 삭제" : ""})` : ""), "ok", { undo: true });
    await load();
  } catch (err) { showAlert(err.message, "error"); b.disabled = false; }
});

// ---------- 발주서 (인쇄용) ----------
let SHEET = null;
function sheetHtml(d, withIds) {
  const s = d.settings || {}, o = d.order, v = x => x ? esc(x) : '<span class="muted">-</span>';
  const qty = d.lines.reduce((a, l) => a + (Number(l["수량"]) || 0), 0);
  return `<header class="os-head"><h2${withIds ? ' id="sheet-title"' : ""}>구매발주서</h2><div class="os-no">주문번호 <b>${esc(o["주문번호"])}</b> · 주문일 ${esc(o["주문일"])}</div></header>
    <table class="os-meta"><tbody>
      <tr><th scope="row">발주처</th><td>${v(s["발주처"])}</td><th scope="row">구매처</th><td>${v(o["거래처"])}</td></tr>
      <tr><th scope="row">배송지</th><td colspan="3">${v(s["배송지"])}</td></tr>
      <tr><th scope="row">담당자</th><td colspan="3">${v(s["담당자"])}</td></tr>
    </tbody></table>
    <table class="os-lines"><thead><tr><th class="num" scope="col">순번</th><th scope="col">온라인코드</th><th scope="col">상품코드</th><th scope="col">품목</th><th class="num" scope="col">수량</th><th scope="col">신청번호</th></tr></thead>
    <tbody>${d.lines.map(l => `<tr><td class="num">${l["순번"]}</td><td>${esc(l["온라인코드"] || "")}</td><td>${esc(l["상품코드"] || "")}</td><td>${esc(l["품목"] || "")}${l["규격"] ? ` <span class="os-spec">${esc(l["규격"])}</span>` : ""}</td><td class="num">${fmt(l["수량"])}</td><td>${esc(l["신청번호"])}</td></tr>`).join("") || '<tr><td colspan="6">묶인 신청이 없습니다.</td></tr>'}</tbody>
    <tfoot><tr><td colspan="4">합계 ${d.lines.length}품목</td><td class="num">${fmt(qty)}</td><td></td></tr></tfoot></table>
    <p class="os-total">주문금액 <b>${fmt(d.total)}원</b>${o["결제금액"] != null && o["결제금액"] !== "" && Number(o["결제금액"]) !== Number(d.total) ? ` · 결제금액 ${fmt(o["결제금액"])}원` : ""}${o["적립금사용"] === "Y" ? " · 적립금 사용" : ""}</p>
    <p class="os-foot">출력 ${today()}</p>`;
}
async function openOrderSheet(row) {
  try {
    SHEET = await api("GET", `/api/request/order-sheet/${row}`);
    $("#order-sheet").innerHTML = sheetHtml(SHEET, true);
    const s = SHEET.settings || {}, miss = ["발주처", "배송지", "담당자"].filter(k => !s[k]);
    $("#sheet-note").hidden = !miss.length;
    $("#sheet-note").textContent = miss.length ? `${miss.join("·")}이(가) 비어 있습니다. 설정(톱니) › '신청 · 발주서'에서 입력하면 발주서 머리글에 들어갑니다.` : "";
    $("#dlg-order-sheet").showModal(); $("#sheet-print").focus();
  } catch (err) { showAlert("발주서를 불러오지 못했습니다: " + err.message, "error"); }
}
$("#sheet-close").addEventListener("click", () => $("#dlg-order-sheet").close());
$("#sheet-print").addEventListener("click", () => {
  if (!SHEET) return;
  $("#print-sheet").innerHTML = sheetHtml(SHEET, false);
  document.body.classList.add("printing-sheet");
  window.print();
});
window.addEventListener("afterprint", () => { if (!document.body.classList.contains("printing-sheet")) return; document.body.classList.remove("printing-sheet"); $("#print-sheet").innerHTML = ""; });

// ---------- 설정 › 신청 · 발주서: 구매처 목록 · 현재 신청 가능 · 안내 (app.js 설정 열기/저장에서 호출) ----------
function renderSupChecks() {
  const box = $("#s-rq-sup-checks"); if (!box) return;
  const names = supSplit($("#s-rq-sup").value || "알파몰,드림디포"), off = new Set(supSplit($("#s-rq-sup-off").value));
  box.innerHTML = names.map((n, i) => `<label class="chk" for="s-rq-sup-${i}"><input type="checkbox" id="s-rq-sup-${i}" data-sup="${esc(n)}"${off.has(n) ? "" : " checked"}> ${esc(n)} 현재 신청 가능</label>`).join("");
  syncSupOff();
}
function syncSupOff() { $("#s-rq-sup-off").value = $$("#s-rq-sup-checks input[data-sup]").filter(c => !c.checked).map(c => c.dataset.sup).join(","); }
function requestSettingsOpen() { renderSupChecks(); }
function requestSettingsSaved(meta, values) {
  if (values) { $("#s-rq-sup").value = values.REQUEST_SUPPLIERS ?? ""; $("#s-rq-sup-off").value = values.REQUEST_SUPPLIERS_OFF ?? ""; renderSupChecks(); }
  if (!DATA?.meta) return;
  Object.assign(DATA.meta, meta);
  fillRequestSelects(); renderRequest();
}
$("#s-rq-sup").addEventListener("input", renderSupChecks);
$("#s-rq-sup-checks").addEventListener("change", syncSupOff);

// ---------- 시작 ----------
try { const t = localStorage.getItem("ledger-rtab"); if (t && $(`#request-tabs [data-rtype="${t}"]`)) switchReqTab(t, false); else FILTERS.request["구분"] = reqType(); } catch { FILTERS.request["구분"] = reqType(); }
if (DATA) { fillRequestSelects(); renderRequest(); }  // load() 가 먼저 끝난 경우
