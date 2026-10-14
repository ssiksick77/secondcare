/* 지출 신청 화면 (/request) — app.js 의 공통 함수($, api, openForm, renderList, confirmDlg, showAlert …)를 그대로 사용.
   연구원 화면: /request 직접 접속 (신청 목록·상태 확인, 본인 신청 추가·수정·첨부)
   담당자 화면: 회계대장·인건비 화면에서 헤더 [신청] 버튼으로 들어온 경우 (sessionStorage "request-admin") — 승인·반려·품의 전환·주문 */
"use strict";

// ---------- 공통 정의 확장 ----------
Object.assign(IDENT, { request: ["신청번호"], order: ["주문번호"], ratt: ["신청번호", "파일명"] });
FILTERS.request = {};
const REQ_LOCKED = ["품의전환", "완료"];  // 비고만 수정 가능, 삭제 불가
const REQ_ORDER_LOCK = ["구분", "단가", "수량", "금액", "구매처"];  // 주문에 묶인 신청
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
function numOf(v) { const ev = evalAmount(v); if (ev !== undefined) return ev; const t = String(v ?? "").replace(/[,\s원]/g, ""); return t === "" || isNaN(Number(t)) ? null : Number(t); }

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
  { k: "첨부", t: "num", calc: rattCount, title: "첨부 파일 수" },
  { k: "결재", calc: r => r["결재일"] || "", title: "결재인 · 결재일 (반려는 사유)",
    html: r => r["상태"] === "반려" ? `<span class="rej" title="반려 사유: ${esc(r["반려사유"] || "")}">반려 · ${esc(reqExcerpt(r["반려사유"], 16))}</span>`
      : r["결재인"] && r["결재일"] ? `${esc(r["결재인"])} <span class="muted" title="${esc(r["결재일"])}">${esc(mmdd(r["결재일"]))}</span>` : '<span class="muted">-</span>' },
  { k: "주문번호" },
  { k: "연결품의번호", label: "연결 품의" },
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
      { k: "관련과제", type: "datalist", list: "관련과제", hint: "재원 목록 또는 직접 입력" },
      { k: "희망일", type: "date", hint: "받고 싶은 날" },
      { k: "품목", type: "text", req: true, cls: "mid", focus: true },
      { k: "규격", type: "text", dep: items, hint: "모델·사양" },
      { k: "단가", type: "num", req: true, dep: items },
      { k: "수량", type: "num", req: true, dep: items },
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
try { if (sessionStorage.getItem("request-admin") === "1") document.body.classList.add("req-admin"); } catch { }
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
$("#request-year").addEventListener("change", e => { FILTERS.request.year = e.target.value; LIST_MORE.request = false; REQSEL.clear(); renderRequest(); });

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
  renderList("request");
  renderOrders();
  updateReqTabCounts();
  $("#rq-order-btn").hidden = reqType() !== "소모품";
  $("#rq-sup-filter").hidden = reqType() !== "소모품";
  const info = $("#req-sup-info"), txt = reqType() === "소모품" ? supNoteText() : "";
  info.hidden = !txt;
  info.innerHTML = txt ? `<b>구매처 안내</b> ${esc(txt)}` : "";
  if (RD.row != null && !$("#req-drawer").hidden) renderReqDrawer(false);
}
function updateReqTabCounts() {
  const y = FILTERS.request.year;
  $$("#request-tabs [role=tab]").forEach(b => {
    const t = b.dataset.rtype, n = DATA.request.filter(r => r["구분"] === t && r["상태"] === "신청" && (!y || (r["신청일"] || "").startsWith(y))).length;
    b.innerHTML = `${esc(t)}${n ? ` <span class="tab-n" title="결재 대기 ${n}건"><span class="sr-only">결재 대기 </span>${n}</span>` : ""}`;
  });
}

// 담당자 선택 열 (승인·반려·품의 전환·주문·삭제를 체크한 행에 한꺼번에)
const REQSEL = new Set();
SEL_HOOK.request = {
  head: () => isReqAdmin() ? `<th class="sel"><input type="checkbox" id="request-sel-all" aria-label="표시된 신청 모두 선택"></th>` : "",
  cell: r => isReqAdmin() ? `<td class="sel"><input type="checkbox" data-rsel="${r._row}" aria-label="${esc(r["신청번호"])} 선택"${REQSEL.has(r._row) ? " checked" : ""}></td>` : "",
  rowCls: r => (RD.row === r._row ? " selected" : ""),
  after: () => {
    const vis = new Set($$("#request-table tbody tr[data-row]").map(tr => Number(tr.dataset.row)));
    [...REQSEL].forEach(r => { if (!vis.has(r)) REQSEL.delete(r); });  // 필터로 가려진 행은 선택 해제
    updateSelBar(); updateRdNav();
  },
};
const selRows = () => [...REQSEL].map(reqFind).filter(Boolean);
const canApprove = r => r["상태"] === "신청" || r["상태"] === "반려";
const canReject = r => (r["상태"] === "신청" || r["상태"] === "승인") && !r["주문번호"];
const canConvert = r => r["상태"] === "승인" && !r["연결품의번호"];
const canOrder = r => r["구분"] === "소모품" && r["상태"] === "승인" && !r["주문번호"] && !r["연결품의번호"];
const canDelete = r => !reqLocked(r) && !r["주문번호"];
const SUP_MIXED = "구매처가 같은 신청만 한 주문으로 묶을 수 있습니다";
function updateSelBar() {
  const list = selRows(), n = list.length;
  $("#req-sel-n").textContent = n ? `${n}건 선택 · ${fmt(list.reduce((a, r) => a + (r["금액"] || 0), 0))}원` : "선택 없음";
  const set = (act, on, why) => { const b = $(`#req-selbar [data-rq=${act}]`); b.disabled = !on; if (why !== undefined) b.title = why; };
  set("approve", list.some(canApprove), "신청·반려 상태의 선택 건을 승인");
  set("reject", list.some(canReject), "신청·승인 상태의 선택 건을 반려 (사유 입력)");
  set("convert", n > 0 && list.every(canConvert), n && !list.every(canConvert) ? "승인된 신청만 품의로 전환할 수 있습니다" : "선택한 승인 건을 품의 1건으로");
  const mixed = new Set(list.map(r => r["구매처"] || "")).size > 1;
  const orderWhy = n && !list.every(canOrder) ? "주문 전 승인된 소모품 신청만 묶을 수 있습니다" : mixed ? SUP_MIXED : "";
  set("order", n > 0 && !orderWhy, orderWhy || "선택한 승인 소모품을 주문 1건으로 묶음");
  const why = $("#req-sel-why"); why.textContent = mixed && reqType() === "소모품" ? SUP_MIXED : ""; why.hidden = !why.textContent; $("#req-sel-help").hidden = !why.hidden;
  set("delete", n > 0 && list.every(canDelete), n && !list.every(canDelete) ? "품의전환·완료·주문에 묶인 신청은 삭제할 수 없습니다" : "선택한 신청 삭제");
  set("clear", n > 0);
  const all = $("#request-sel-all"); if (all) { const boxes = $$("#request-table input[data-rsel]"); all.checked = boxes.length > 0 && boxes.every(b => b.checked); all.indeterminate = boxes.some(b => b.checked) && !all.checked; }
}
document.addEventListener("change", e => {
  if (e.target.id === "request-sel-all") { $$("#request-table input[data-rsel]").forEach(b => { b.checked = e.target.checked; const r = Number(b.dataset.rsel); e.target.checked ? REQSEL.add(r) : REQSEL.delete(r); }); updateSelBar(); }
  else if (e.target.dataset?.rsel !== undefined) { const r = Number(e.target.dataset.rsel); e.target.checked ? REQSEL.add(r) : REQSEL.delete(r); updateSelBar(); }
});
$("#req-selbar").addEventListener("click", e => {
  const b = e.target.closest("button[data-rq]"); if (!b || b.disabled) return;
  const list = selRows(), act = b.dataset.rq;
  if (act === "clear") { REQSEL.clear(); renderList("request"); return; }
  if (act === "approve") return runReqAction(list.filter(canApprove), "approve");
  if (act === "reject") return rejectRequests(list.filter(canReject));
  if (act === "convert") return convertRequests(list);
  if (act === "order") return openOrderDialog(list);
  if (act === "delete") return deleteRequests(list);
});

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

// ---------- 입력 폼 (구분별 칸 · 금액 미리보기 · 잠금 · 상세 JSON) ----------
const _openFormBeforeRequest = openForm;
openForm = function (kind, row, preset, opts) {
  _openFormBeforeRequest(kind, row, preset, opts);
  if (kind === "request") requestFormAfterOpen(row ?? null);
};
function requestFormAfterOpen(row) {
  const rec = row != null ? reqFind(row) : null;
  const amt = F("금액")?.closest("label");
  if (amt) {  // 학회: 여비 계산기 자리 (계산기는 다음 단계)
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
  const lock = (pred, note) => {
    $$("#dlg-fields input[name], #dlg-fields select[name]").forEach(el => {
      if (el.readOnly && el.type === "text" && el.tabIndex === -1) return;  // ro 칸
      if (!pred(el.name.replace(/^_/, ""))) return;
      if (el.tagName === "SELECT") el.disabled = true; else { el.readOnly = true; el.setAttribute("aria-readonly", "true"); }
      el.classList.add("locked");
    });
    const p = $("#dlg-error"); p.textContent = note; p.hidden = false; p.classList.add("info");
  };
  if (rec && reqLocked(rec)) { lock(k => k !== "비고", `'${rec["상태"]}' 상태(연결 품의 ${rec["연결품의번호"] || "-"})라 비고만 바꿀 수 있습니다.`); $("#req-calc-btn")?.setAttribute("disabled", ""); F("비고")?.focus(); }
  else if (rec && rec["주문번호"]) lock(k => REQ_ORDER_LOCK.includes(k), `주문 ${rec["주문번호"]} 에 묶여 구분·단가·수량·금액·구매처는 바꿀 수 없습니다. 주문을 취소하면 바꿀 수 있습니다.`);
  if (det["합계"] != null && F("금액") && !F("금액").readOnly) { F("금액").readOnly = true; F("금액").classList.add("locked"); F("금액").title = "여비 계산기 합계 (계산기에서 바꾸세요)"; }
  requestFormSync();
  $("#dlg").dataset.initial = formSnapshot();
}
function requestFormSync() {
  if ($("#dlg").dataset.kind !== "request") return;
  const t = F("구분")?.value;
  const lab = F("품목")?.closest("label")?.querySelector(".lab");
  if (lab?.firstChild?.nodeType === 3) lab.firstChild.nodeValue = t === "학회" ? "학회명" : "품목";
  const calc = $("#req-calc-row"); if (calc) calc.hidden = t !== "학회";
  const sn = $("#req-sup-note"); if (sn) sn.hidden = t !== "소모품" || !sn.textContent;
  updateAmtPreview();
}
function updateAmtPreview() {
  const p = F("_금액"); if (!p) return;
  const u = numOf(F("단가")?.value), q = numOf(F("수량")?.value);
  p.value = u != null && q != null && String(F("단가").value).trim() !== "" ? `${fmt(u * q)}원` : "(자동)";
}
$("#dlg-fields").addEventListener("input", e => { if ($("#dlg").dataset.kind === "request" && (e.target.id === "f-단가" || e.target.id === "f-수량")) updateAmtPreview(); });
document.addEventListener("click", e => { if (e.target.closest("#req-calc-btn")) openConfCalc(); });
// 학회 여비 계산기 훅: 다음 단계에서 계산 결과를 상세 JSON({..., 합계})과 금액 칸에 채운다
function openConfCalc() { $("#dlg-conf").showModal(); }

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
    if (det["시작일"] && det["종료일"] && det["종료일"] < det["시작일"]) return "학회 종료일이 시작일보다 빠릅니다.";
    out["상세"] = JSON.stringify(det); out["단가"] = ""; out["수량"] = 1; out["규격"] = "";
    if (det["합계"] != null && det["합계"] !== "") out["금액"] = det["합계"];
  } else {
    out["상세"] = "";
    if (out["수량"] === "" || out["수량"] == null) out["수량"] = 1;
    if (out["단가"] !== "" && out["단가"] != null) out["금액"] = Math.round(Number(out["단가"]) * Number(out["수량"]));
  }
  if (t !== "소모품") { out["온라인코드"] = ""; out["상품코드"] = ""; out["상품링크"] = ""; out["구매처"] = ""; }
  if (out["상품링크"] && !safeUrl(out["상품링크"])) return "상품링크는 http:// 또는 https:// 로 시작하는 주소여야 합니다.";
  if (cur?.["주문번호"]) REQ_ORDER_LOCK.forEach(k => { out[k] = cur[k]; });
  if (Number(out["수량"]) <= 0) return "수량은 0보다 커야 합니다.";
  try { if (out["신청인"]) localStorage.setItem("request-name", out["신청인"]); } catch { }
  Object.keys(rec).forEach(k => delete rec[k]); Object.assign(rec, out);
  return null;
}

// ---------- 결재 (승인 · 반려 · 승인 취소 · 재신청) ----------
const ACT_LABEL = { approve: "승인", reject: "반려", unapprove: "승인 취소", reopen: "재신청(신청으로 되돌림)" };
async function runReqAction(list, action, extra = {}) {
  if (!list.length) { showAlert("처리할 수 있는 신청이 없습니다.", "warn"); return false; }
  let ok = 0; const errs = [];
  for (const r of list) {
    try { await api("POST", `/api/request/${r._row}/action`, { action, extra, expect: expectOf("request", r) }); ok++; }
    catch (e) { errs.push(`${r["신청번호"]}: ${e.message}`); }
  }
  REQSEL.clear();
  if (ok) showAlert(`${ok === 1 ? list[0]["신청번호"] + " " : ok + "건 "}${ACT_LABEL[action]} 처리했습니다.`, "ok", ok === 1 && list.length === 1 ? { undo: true } : {});
  if (errs.length) showAlert(`${ACT_LABEL[action]} 실패 ${errs.length}건 — ${errs.join(" / ")}`, "error");
  await load();
  return ok > 0;
}
async function rejectRequests(list) {
  if (!list.length) return showAlert("반려할 수 있는 신청이 없습니다 (신청·승인 상태, 주문 전).", "warn");
  const reason = await confirmDlg({ title: `신청 ${list.length}건 반려`, body: `${listLabel(list)}\n\n신청인이 목록에서 사유를 볼 수 있습니다. 반려한 건은 '재신청'으로 다시 신청 상태로 돌릴 수 있습니다.`, verb: "반려", danger: true, input: { label: "반려 사유 (필수)", value: "" } });
  if (reason === null) return;
  if (!String(reason).trim()) { showAlert("반려 사유를 입력하세요.", "warn"); return; }
  return runReqAction(list, "reject", { 사유: String(reason).trim() });
}

// ---------- 품의 전환 ----------
function convertRequests(list) {
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
  const p = $("#dlg-error");
  p.textContent = `저장하면 품의 1건이 만들어지고 신청 ${list.length}건이 '품의전환'으로 바뀝니다 (되돌리기 가능). 비고에는 '신청 ${list.map(r => r["신청번호"]).join(", ")}'가 자동으로 붙습니다. 재원·예산목을 고르세요.`;
  p.hidden = false; p.classList.add("info");
}

// ---------- 삭제 ----------
async function deleteRequests(list) {
  const bad = list.filter(r => !canDelete(r));
  if (!list.length) return;
  if (bad.length) return showAlert(`품의로 전환됐거나 주문에 묶인 신청은 삭제할 수 없습니다: ${listLabel(bad)}`, "warn");
  if (!isReqAdmin() && list.some(r => r["상태"] !== "신청")) return showAlert("신청 상태인 건만 삭제할 수 있습니다.", "warn");
  const att = list.reduce((a, r) => a + rattCount(r), 0);
  const body = list.slice(0, 6).map(r => `${r["신청번호"]} · ${r["품목"]} · ${fmt(r["금액"])}원`).join("\n") + (list.length > 6 ? `\n… 외 ${list.length - 6}건` : "")
    + (att ? `\n\n첨부 ${att}개도 함께 지우고 드라이브 휴지통으로 옮깁니다.` : "") + (list.length === 1 && !att ? "\n\n삭제 직후 알림의 [되돌리기]로 복구할 수 있습니다." : "");
  if (!await confirmDlg({ title: `신청 ${list.length}건 삭제`, body, verb: att ? "첨부와 함께 삭제" : "삭제", danger: true })) return;
  let ok = 0; const errs = [], warns = [];
  for (const r of [...list].sort((a, b) => b._row - a._row)) {  // 아래 행부터 (행 번호 밀림 방지)
    try { const res = await api("DELETE", `/api/request/${r._row}`, { expect: expectOf("request", r), cascade: rattCount(r) > 0 }); ok++; if (res?.warning) warns.push(res.warning); }
    catch (e) { errs.push(`${r["신청번호"]}: ${e.message}`); }
  }
  REQSEL.clear(); if (list.some(r => r._row === RD.row)) closeReqDrawer();
  if (ok) showAlert(`신청 ${ok}건을 삭제했습니다.` + (warns.length ? " " + warns.join(" ") : ""), warns.length ? "warn" : "ok", ok === 1 && list.length === 1 && !att ? { undo: true } : {});
  if (errs.length) showAlert("삭제 실패 — " + errs.join(" / "), "error");
  await load();
}

// ---------- 상세 패널 ----------
const RD = { row: null, items: null, drive: null, seq: 0, shown: null };
function markReqRow() { $$("#request-table tbody tr[data-row]").forEach(tr => tr.classList.toggle("selected", Number(tr.dataset.row) === RD.row)); }
function openReqDrawer(row, opts = {}) {
  RD.row = row; RD.items = null;
  $("#ai-drawer").hidden = true;
  $("#req-drawer").hidden = false; document.body.classList.add("drawer-open");
  markReqRow(); renderReqDrawer(true);
  if (opts.focus !== false) $("#rd-close").focus();
}
function closeReqDrawer() {
  const dr = $("#req-drawer"); if (!dr || (dr.hidden && RD.row == null)) return;
  const ae = document.activeElement, restore = !dr.hidden && (!ae || ae === document.body || dr.contains(ae)), row = RD.row;
  dr.hidden = true; document.body.classList.remove("drawer-open"); RD.row = null; markReqRow();
  if (restore && row != null) $(`#request-table tbody tr[data-row="${row}"] .rowbtn`)?.focus();
}
$("#rd-close").addEventListener("click", closeReqDrawer);
document.addEventListener("keydown", e => { if (e.key === "Escape" && !e.defaultPrevented && !$("#req-drawer").hidden && !document.querySelector("dialog[open]")) closeReqDrawer(); });
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
  const st = r["상태"], admin = isReqAdmin(), det = reqDetail(r), conf = r["구분"] === "학회";
  $("#rd-title").innerHTML = `${esc(r["신청번호"])} <span class="badge ${esc(st)}">${esc(st)}</span>`;
  $("#rd-sub").innerHTML = `${esc(r["구분"])} · ${esc(r["신청인"])} · <b>${fmt(r["금액"])}원</b>`;
  updateRdNav();
  const keep = $("#ratt-form") && RD.shown === r._row ? { note: $("#ratt-form").note.value } : null;
  const seq = ++RD.seq;
  if (fetchItems || !RD.items) {
    try { const d = await api("GET", `/api/ratt/${encodeURIComponent(r["신청번호"])}`); if (seq !== RD.seq || RD.row !== r._row) return; RD.items = d.items; RD.drive = d.drive; }
    catch (e) { RD.items = []; RD.drive = { connected: false, error: e.message }; }
  }
  if (seq !== RD.seq) return;
  const body = $("#rd-body"), scroll = RD.shown === r._row ? body.scrollTop : 0;
  const items = RD.items || [], drive = RD.drive || {};
  const kv = (k, v, cls = "") => `<b>${esc(k)}</b><span class="xd-ro${cls}">${v === "" || v == null ? '<span class="muted">-</span>' : v}</span>`;
  const t = s => esc(s ?? "");
  const fund = DATA.funds.find(f => f["재원코드"] === r["관련과제"]);
  const link = safeUrl(r["상품링크"]);
  const order = r["주문번호"] ? (DATA.order || []).find(o => o["주문번호"] === r["주문번호"]) : null;
  const info = [
    kv("구분", t(r["구분"])), kv("신청인", t(r["신청인"])), kv("신청일", t(r["신청일"])),
    kv("관련과제", r["관련과제"] ? `${t(r["관련과제"])}${fund?.["과제명"] ? ` <span class="muted">${t(fund["과제명"])}</span>` : ""}` : ""),
    kv(conf ? "학회명" : "품목", t(r["품목"])),
    ...(conf ? [
      kv("기간", det["시작일"] || det["종료일"] ? `${t(det["시작일"] || "?")} ~ ${t(det["종료일"] || "?")}` : ""), kv("국내/국외", t(det["국내외"])), kv("장소", t(det["장소"])),
      kv("참가자", t(det["참가자"])), kv("등록비", det["등록비"] !== "" && det["등록비"] != null ? fmt(det["등록비"]) + "원" : ""), kv("금액", `<b>${fmt(r["금액"])}원</b>`),
    ] : [kv("규격", t(r["규격"])), kv("단가", r["단가"] != null && r["단가"] !== "" ? fmt(r["단가"]) + "원" : ""), kv("수량", fmt(r["수량"])), kv("금액", `<b>${fmt(r["금액"])}원</b>`)]),
    kv("사유", t(r["사유"]), " multi"), kv("희망일", t(r["희망일"])),
    ...(r["구분"] === "소모품" ? [kv("구매처", r["구매처"] ? `${t(r["구매처"])}${supOff(r["구매처"]) ? ' <span class="muted">(현재 이용 불가)</span>' : ""}` : ""), kv("온라인코드", t(r["온라인코드"])), kv("상품코드", t(r["상품코드"])),
      kv("상품링크", link ? `<a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${esc(reqExcerpt(link, 48))}</a>` : t(r["상품링크"]))] : []),
    kv("주문", order ? `${t(order["주문번호"])} <span class="muted">주문 ${t(mmdd(order["주문일"]))}${order["배송일"] ? ` · 배송 ${t(mmdd(order["배송일"]))}` : " · 배송 전"}</span>` : t(r["주문번호"])),
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
  body.innerHTML = `
    <section class="xd-sec xd-info">
      <h3>신청 정보 <span class="sp"></span>${ownEdit ? `<button type="button" class="btn btn-sm" data-rd="edit"${reqLocked(r) ? ' title="비고만 수정할 수 있습니다"' : ""}>${reqLocked(r) ? "비고 수정" : "수정"}</button>` : ""}</h3>
      <div class="kv">${info}</div>
    </section>
    <section class="xd-sec xd-info">
      <h3>결재 <span class="badge ${esc(st)}">${esc(st)}</span></h3>
      <div class="kv">${kv("결재인", t(r["결재인"]))}${kv("결재일", t(r["결재일"]))}${rejNote}</div>
      ${acts ? `<div class="rd-actions" role="group" aria-label="담당자 처리">${acts}</div>` : ""}
      ${!admin && st === "반려" ? '<p class="toolbar-note">반려된 신청입니다. 사유를 반영해 새로 신청하거나 담당자에게 재신청을 요청하세요.</p>' : ""}
    </section>
    <section class="xd-sec">
      <h3>첨부 <span class="toolbar-note">${items.length}개</span><span class="sp"></span>${safeUrl(r["첨부폴더"]) ? `<a class="btn btn-sm" href="${esc(safeUrl(r["첨부폴더"]))}" target="_blank" rel="noopener noreferrer">폴더 열기</a>` : ""}</h3>
      ${!drive.connected ? `<p class="toolbar-note warn">구글 드라이브가 연결되지 않아 첨부를 올릴 수 없습니다. ${admin ? "오른쪽 위 설정(톱니)에서 연결하세요." : "담당자에게 알려 주세요."}${drive.error ? " (" + esc(drive.error) + ")" : ""}</p>` : ""}
      ${items.length ? `<div class="table-wrap"><table class="grid compact evid-table"><thead><tr><th class="xd-th-cell"><span class="sr-only">미리보기</span></th><th>파일명</th><th class="num">크기</th><th>업로드</th><th><span class="sr-only">작업</span></th></tr></thead><tbody>
        ${items.map(a => `<tr><td class="xd-th-cell">${thumb(a)}</td><td class="evid-name">${safeUrl(a.url) ? `<a href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer" title="새 창에서 열기">${esc(a["원본파일명"] || a["파일명"])}</a>` : esc(a["원본파일명"] || a["파일명"])}${a["비고"] ? `<div class="toolbar-note">${esc(a["비고"])}</div>` : ""}</td><td class="num">${a["크기"] ? Math.max(1, Math.round(a["크기"] / 1024)).toLocaleString() + " KB" : ""}</td><td>${esc(mmdd(a["업로드일"]))}</td><td>${canDelAtt ? `<button type="button" class="btn btn-sm btn-danger" data-rattdel="${a._row}" data-name="${esc(a["원본파일명"] || a["파일명"])}" title="장부에서 지우고 드라이브 휴지통으로 이동">삭제</button>` : ""}</td></tr>`).join("")}
      </tbody></table></div>` : '<p class="toolbar-note">첨부가 없습니다. 견적서·인보이스·요금제 안내 등을 올리세요.</p>'}
      <form id="ratt-form" class="evid-form">
        <label class="file-pick">파일 <span class="file-pick-row"><input type="file" name="files" multiple ${drive.connected ? "" : "disabled"}><span class="btn btn-sm file-btn" aria-hidden="true">파일 선택</span><span class="file-names">선택된 파일 없음</span></span></label>
        <label>메모 <input type="text" name="note" placeholder="선택 (예: 견적서)"></label>
        <div class="wide evid-drop-row"><div class="drop" id="ratt-drop" title="파일 이름은 신청번호_품목_원본이름 으로 저장됩니다"><b>파일을 여기로 끌어다 놓기</b> · 신청/${esc((r["신청일"] || "").slice(0, 4))}/${esc(r["신청번호"])}</div><button type="submit" class="btn btn-primary btn-sm" ${drive.connected ? "" : "disabled"}>업로드</button></div>
      </form>
    </section>
    <section class="xd-sec xd-foot">
      <button type="button" class="btn btn-sm btn-danger" data-rd="delete"${ownDel ? "" : " disabled"} title="${ownDel ? (items.length ? "첨부와 함께 삭제" : "이 신청 삭제 (되돌리기 가능)") : reqLocked(r) ? "품의로 전환된 신청은 삭제할 수 없습니다" : r["주문번호"] ? "주문을 먼저 취소하세요" : "신청 상태에서만 삭제할 수 있습니다"}">이 신청 삭제</button>
      ${ownDel ? "" : `<span class="toolbar-note">${reqLocked(r) ? "품의로 전환된 신청은 삭제할 수 없습니다" : r["주문번호"] ? `주문 ${esc(r["주문번호"])} 를 먼저 취소하세요` : "신청 상태에서만 삭제할 수 있습니다 (담당자는 승인 취소 후)"}</span>`}
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
  dz.addEventListener("drop", e => { e.preventDefault(); if (e.dataTransfer.files.length && !fileInput.disabled) { fileInput.files = e.dataTransfer.files; form.requestSubmit(); } });
  form.addEventListener("submit", async e => {
    e.preventDefault();
    const files = fileInput.files;
    if (!files.length) { showAlert("파일을 선택하세요.", "warn"); return; }
    const fd = new FormData(); [...files].forEach(f => fd.append("files", f)); fd.append("note", form.note.value.trim());
    const btn = form.querySelector("button[type=submit]"); btn.disabled = true; btn.textContent = `업로드 중… (${files.length}개)`;
    try {
      const res = await fetch(`/api/ratt/${encodeURIComponent(r["신청번호"])}`, { method: "POST", body: fd });
      if (!res.ok) { let m = res.statusText; try { m = (await res.json()).detail || m; } catch { } throw new Error(m); }
      const d = await res.json();
      showAlert(`${r["신청번호"]} 첨부 ${d.items.length}개 업로드 완료`, "ok");
      await load(); if (RD.row === r._row) await renderReqDrawer(true);
    } catch (err) { showAlert("업로드 실패: " + err.message, "error"); btn.disabled = false; btn.textContent = "업로드"; }
  });
}
$("#rd-body").addEventListener("click", async e => {
  const del = e.target.closest("[data-rattdel]");
  if (del) {
    if (!await confirmDlg({ title: "첨부 삭제", body: `'${del.dataset.name}' 을 장부에서 지우고 드라이브 휴지통으로 옮깁니다.`, verb: "삭제", danger: true })) return;
    const row = Number(del.dataset.rattdel), a = (RD.items || []).find(x => x._row === row);
    try { const res = await api("DELETE", `/api/ratt/${row}`, { expect: a ? { 신청번호: a["신청번호"], 파일명: a["파일명"] } : undefined }); showAlert(res.warning || "첨부를 삭제했습니다.", res.warning ? "warn" : "ok"); await load(); if (RD.row != null) await renderReqDrawer(true); }
    catch (err) { showAlert(err.message, "error"); }
    return;
  }
  const b = e.target.closest("button[data-rd]"); if (!b) return;
  const r = reqFind(RD.row); if (!r) return;
  const act = b.dataset.rd;
  if (act === "edit") return editRequest(r._row);
  if (act === "delete") return deleteRequests([r]);
  if (act === "approve" || act === "unapprove" || act === "reopen") { b.disabled = true; const ok = await runReqAction([r], act); if (!ok) b.disabled = false; return; }
  if (act === "reject") return rejectRequests([r]);
  if (act === "convert") return convertRequests(r["주문번호"] ? DATA.request.filter(q => q["주문번호"] === r["주문번호"] && canConvert(q)) : [r]);
  if (act === "order") return openOrderDialog([r]);
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
