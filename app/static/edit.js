/* 집행내역 편집 모드 (팝업 격자) — 엑셀처럼 셀 단위로 고치고 [저장]으로 한 번에 반영 */
"use strict";

// 시트 열 순서 그대로 (거래번호·상태·증빙 열은 읽기 전용)
const EDIT_COLS = [
  { k: "거래번호", ro: true, w: 120 }, { k: "상태", ro: true, w: 56, calc: r => STATUS_LABEL[execStatusOf(r)] || "" },
  { k: "원인발생일", t: "date", w: 104, req: true }, { k: "지급청구일", t: "date", w: 104 }, { k: "지출완료일", t: "date", w: 104 }, { k: "결의일", t: "date", w: 104 },
  { k: "재원", t: "select", opts: () => fundOptions(), w: 90, req: true }, { k: "예산목", t: "select", opts: () => DATA.meta.budget_items, w: 120, req: true },
  { k: "세목", w: 90 }, { k: "결제수단", t: "select", opts: () => DATA.meta.pay_methods, w: 90 }, { k: "세세목", w: 90 },
  { k: "거래처", w: 110 }, { k: "적요", w: 200 }, { k: "금액", t: "num", w: 100, req: true }, { k: "사용자", w: 80 },
  { k: "태그", t: "select", opts: () => DATA.tags.length ? DATA.tags.map(t => t["태그명"]) : null, w: 90 }, { k: "관리번호", w: 110 }, { k: "비고", w: 160 },
];
const EDIT_LOCKED = ["재원", "예산목", "금액", "거래처", "원인발생일"];
function execStatusOf(r) { if (r["결의일"]) return "결의"; if (r["지출완료일"]) return "완료"; if (r["지급청구일"]) return r["상태"] === "보완" ? "보완" : "청구"; return "발생"; }

const ED = { rows: [], undo: [], focus: null, anchor: null, editing: null, open: false, op: null };

function openEditMode() {
  const src = filtered("exec").slice().sort((a, b) => (b["원인발생일"] || "").localeCompare(a["원인발생일"] || "") || b._row - a._row);
  ED.rows = src.map(r => ({ _row: r._row, orig: r, cur: { ...r }, isNew: false, del: false, locked: !!execOrigin(r)?.locked, err: null, bad: null }));
  ED.rows.push(newEditRow());
  ED.undo = []; ED.op = null; ED.focus = null; ED.anchor = null; ED.editing = null; ED.open = true;
  $("#edit-note").textContent = `${src.length}건 (현재 필터 기준). 더블클릭·Enter·글자 입력으로 편집, Tab/방향키 이동, Ctrl+V 로 엑셀 붙여넣기, Ctrl+D 위 칸 채우기, Ctrl+Z 되돌리기, Ctrl+S 저장. 맨 아래 빈 행에 입력하면 새 행이 됩니다.`;
  renderEditGrid();
  const d = $("#dlg-edit"); d.showModal();
  focusCell(0, 2);
}
function newEditRow() {
  const cur = Object.fromEntries(EDIT_COLS.map(c => [c.k, ""]));
  cur["원인발생일"] = ""; cur["재원"] = FILTERS.exec?.["재원"] || "";
  return { _row: null, orig: null, cur, isNew: true, del: false, locked: false, err: null, bad: null, blank: true };
}
const EDIT_FIRST = EDIT_COLS.findIndex(c => !c.ro), EDIT_LAST = EDIT_COLS.length - 1;  // Tab 줄바꿈 기준 열
const isEditable = (row, c) => !c.ro && !row.del && !(row.locked && EDIT_LOCKED.includes(c.k));
function cellVal(row, c) { return c.calc ? c.calc(row.cur) : row.cur[c.k]; }
function fmtCell(row, c) { const v = cellVal(row, c); if (v == null || v === "") return ""; return c.t === "num" ? fmt(v) : String(v); }
function isChanged(row, k) { return !row.isNew && row.orig && String(row.orig[k] ?? "") !== String(row.cur[k] ?? ""); }

function editRowHtml(row, ri) {
  return `<tr data-ri="${ri}" class="${row.del ? "del" : ""}${row.isNew && !row.blank ? " new" : ""}${row.err ? " err" : ""}"${row.err ? ` title="${esc(row.err)}"` : ""}><td class="sel"><input type="checkbox" data-sel="${ri}" ${row.del ? "checked" : ""} ${row.blank ? "disabled" : ""} aria-label="이 행 삭제 표시"></td>${EDIT_COLS.map((c, ci) => { const bad = row.bad?.[ci]; return `<td data-ri="${ri}" data-ci="${ci}" tabindex="-1" class="${c.t === "num" ? "num" : ""}${isEditable(row, c) ? "" : " ro"}${isChanged(row, c.k) ? " chg" : ""}${bad ? " bad" : ""}"${bad ? ` title="${esc(bad)}"` : ""}>${esc(fmtCell(row, c))}</td>`; }).join("")}</tr>`;
}
function renderEditGrid() {
  const live = ED.rows.filter(r => !r.blank), allDel = live.length > 0 && live.every(r => r.del);
  const head = `<thead><tr><th class="sel"><label><input type="checkbox" id="edit-all" aria-label="모든 행 삭제 표시"${allDel ? " checked" : ""}>삭제</label></th>${EDIT_COLS.map(c => `<th style="width:${c.w}px"${c.t === "num" ? ' class="num"' : ""}>${esc(c.k)}${c.req ? ' <span class="req">*</span>' : ""}</th>`).join("")}</tr></thead>`;
  $("#edit-grid").innerHTML = head + `<tbody>${ED.rows.map(editRowHtml).join("")}</tbody>`;
  updateEditCount();
}
// 한 행만 다시 그림 (셀 확정 시 전체 재생성을 피함)
function updateEditRow(ri) {
  const tr = $(`#edit-grid tbody tr[data-ri="${ri}"]`), row = ED.rows[ri];
  if (!row) { tr?.remove(); return; }
  if (tr) tr.outerHTML = editRowHtml(row, ri); else $("#edit-grid tbody").insertAdjacentHTML("beforeend", editRowHtml(row, ri));
}
function updateEditCount() {
  const n = ED.rows.filter(r => r.del && !r.blank).length, m = ED.rows.filter(r => !r.isNew && !r.del && EDIT_COLS.some(c => isChanged(r, c.k))).length, a = ED.rows.filter(r => r.isNew && !r.blank && !r.del).length;
  $("#edit-count").textContent = (m || a || n) ? `수정 ${m} · 추가 ${a} · 삭제 ${n}` : "변경 없음";
  $("#edit-save").disabled = !(m || a || n);
}
function cellEl(ri, ci) { return $(`#edit-grid td[data-ri="${ri}"][data-ci="${ci}"]`); }
function focusCell(ri, ci, extend = false) {
  ri = Math.max(0, Math.min(ED.rows.length - 1, ri)); ci = Math.max(0, Math.min(EDIT_COLS.length - 1, ci));
  if (!extend || !ED.anchor) ED.anchor = [ri, ci];
  ED.focus = [ri, ci];
  $$("#edit-grid td.cur, #edit-grid td.rng").forEach(td => td.classList.remove("cur", "rng"));
  const [r0, r1] = [Math.min(ED.anchor[0], ri), Math.max(ED.anchor[0], ri)], [c0, c1] = [Math.min(ED.anchor[1], ci), Math.max(ED.anchor[1], ci)];
  for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) cellEl(r, c)?.classList.add("rng");
  const el = cellEl(ri, ci); if (el) { el.classList.add("cur"); el.focus({ preventScroll: false }); el.scrollIntoView({ block: "nearest", inline: "nearest" }); }
}
function rangeBounds() { const [a, f] = [ED.anchor || ED.focus, ED.focus]; return [Math.min(a[0], f[0]), Math.max(a[0], f[0]), Math.min(a[1], f[1]), Math.max(a[1], f[1])]; }
// Tab 이동: 끝 열에서 다음 행 첫 편집 열로, 첫 편집 열에서 이전 행 끝 열로. 격자 끝을 넘으면 null (격자 밖으로)
function tabTarget(ri, ci, back) {
  if (!back) { if (ci < EDIT_LAST) return [ri, Math.max(ci + 1, EDIT_FIRST)]; return ri < ED.rows.length - 1 ? [ri + 1, EDIT_FIRST] : null; }
  if (ci > EDIT_FIRST) return [ri, ci - 1]; return ri > 0 ? [ri - 1, EDIT_LAST] : null;
}
function leaveGrid(back) {
  if (back) { $("#edit-all")?.focus(); return; }
  const save = $("#edit-save"); (save.disabled ? $("#edit-cancel") : save).focus();
}
function tabMove(back) { const [ri, ci] = ED.focus; const t = tabTarget(ri, ci, back); if (t) focusCell(t[0], t[1]); else leaveGrid(back); }

// ---------- 되돌리기: 작업 단위 스냅샷 ----------
// 작업 하나(셀 확정·붙여넣기·채우기·지우기·삭제 표시) = 되돌리기 한 번. 바뀌기 직전의 행 상태와 행 수를 기억
function beginOp() { ED.op = { rows: new Map(), length: ED.rows.length, focus: ED.focus ? [...ED.focus] : null }; }
function snapRow(ri) {
  const op = ED.op; if (!op || ri >= op.length || op.rows.has(ri)) return;
  const r = ED.rows[ri]; op.rows.set(ri, { cur: { ...r.cur }, isNew: r.isNew, blank: !!r.blank, del: r.del, bad: r.bad ? { ...r.bad } : null });
}
function endOp() {
  const op = ED.op; ED.op = null; if (!op) return false;
  const reshaped = normalizeBlankRows();
  if (op.rows.size || op.length !== ED.rows.length) { ED.undo.push(op); if (ED.undo.length > 200) ED.undo.shift(); }
  return reshaped;
}
// 모든 값이 빈 새 행은 다시 빈 행으로, 맨 아래 빈 행은 정확히 하나만. 반환: 행 구성이 바뀌었는지
function normalizeBlankRows() {
  let changed = false;
  const defFund = FILTERS.exec?.["재원"] || "";
  ED.rows.forEach(r => {
    if (!r.isNew || r.blank) return;
    if (EDIT_COLS.every(c => c.ro || r.cur[c.k] === "" || r.cur[c.k] == null || (c.k === "재원" && r.cur[c.k] === defFund))) { r.blank = true; r.del = false; r.err = null; r.bad = null; changed = true; }
  });
  while (ED.rows.length > 1 && ED.rows[ED.rows.length - 1].blank && ED.rows[ED.rows.length - 2].blank) { ED.rows.pop(); changed = true; }
  if (!ED.rows.length || !ED.rows[ED.rows.length - 1].blank) { ED.rows.push(newEditRow()); changed = true; }
  return changed;
}
function undoEdit() {
  if (ED.editing) cancelEdit();
  const op = ED.undo.pop(); if (!op) { showAlert("되돌릴 변경이 없습니다.", "warn"); return; }
  ED.rows.length = Math.min(ED.rows.length, op.length);
  while (ED.rows.length < op.length) ED.rows.push(newEditRow());
  op.rows.forEach((s, ri) => { Object.assign(ED.rows[ri], { cur: { ...s.cur }, isNew: s.isNew, blank: s.blank, del: s.del, bad: s.bad, err: null }); });
  normalizeBlankRows();
  renderEditGrid();
  const f = op.focus || [0, EDIT_FIRST]; focusCell(f[0], f[1]);
}

// ---------- 값 해석 ----------
function normDate(s) {
  s = String(s ?? "").replace(/[\s ]+/g, ""); if (!s) return "";
  if (/^\d{5}(\.0+)?$/.test(s)) {  // 엑셀 날짜 일련번호 (1899-12-30 기준)
    const n = parseInt(s, 10); if (n < 20000 || n > 80000) return null;
    const d = new Date(Date.UTC(1899, 11, 30) + n * 86400000);
    return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
  }
  s = s.replace(/\.$/, "");  // "2026. 5. 1." 의 끝 점
  const m = s.match(/^(\d{4})[-./](\d{1,2})[-./](\d{1,2})$/) || s.match(/^(\d{4})(\d{2})(\d{2})$/) || s.match(/^(\d{4})년(\d{1,2})월(\d{1,2})일?$/);
  if (!m) return null;
  const d = new Date(+m[1], +m[2] - 1, +m[3]); if (d.getMonth() !== +m[2] - 1) return null;
  return `${m[1]}-${String(m[2]).padStart(2, "0")}-${String(m[3]).padStart(2, "0")}`;
}
// 금액: 쉼표·원·₩·$·공백 제거, "(1,000)" = -1000, '=' 수식 계산. 반환 { v } 또는 { err }
function parseAmount(raw) {
  const str = String(raw ?? "").trim();
  const ev = evalAmount(str); if (ev === null) return { err: "수식을 계산할 수 없습니다" }; if (ev !== undefined) return { v: ev };
  let t = str.replace(/[,\s 원₩￦$]/g, ""); if (t === "") return { v: "" };
  let neg = false; const pm = t.match(/^\((.*)\)$/); if (pm) { neg = true; t = pm[1]; }
  if (!/^-?\d+(\.\d+)?$/.test(t)) return { err: "숫자가 아닙니다" };
  const n = Math.round(Number(t)); return { v: neg ? -n : n };
}
function parseCell(c, raw) {
  if (c.t === "num") return parseAmount(raw);
  if (c.t === "date") { const v = normDate(raw); return v === null ? { err: "날짜 형식이 아닙니다 (YYYY-MM-DD)" } : { v }; }
  return { v: String(raw ?? "").trim() };
}

// ---------- 값 설정 (현재 작업에 스냅샷 기록 + 빈 행 자동 추가) ----------
// 반환: { ok: true, changed } | { ok: false, why: "locked" | "format", msg }
function setCell(ri, ci, val, { quiet = false } = {}) {
  const row = ED.rows[ri], c = EDIT_COLS[ci]; if (!row || !c) return { ok: false, why: "locked" };
  if (!isEditable(row, c)) return { ok: false, why: "locked" };
  const p = parseCell(c, val);
  if (p.err) { if (!quiet) showAlert(`${c.k}: ${p.err}`, "warn"); return { ok: false, why: "format", msg: p.err }; }
  const v = p.v, prev = row.cur[c.k];
  if (String(prev ?? "") === String(v ?? "")) { if (row.bad?.[ci]) { snapRow(ri); delete row.bad[ci]; } return { ok: true, changed: false }; }
  snapRow(ri);
  row.cur[c.k] = v; row.err = null; if (row.bad) delete row.bad[ci];
  if (row.blank && v !== "") { row.blank = false; if (ri === ED.rows.length - 1) ED.rows.push(newEditRow()); }
  return { ok: true, changed: true };
}
function markBad(ri, ci, msg) { const row = ED.rows[ri]; snapRow(ri); row.bad = row.bad || {}; row.bad[ci] = msg; }

// ---------- 셀 편집기 ----------
function startEdit(ri, ci, initial) {
  const row = ED.rows[ri], c = EDIT_COLS[ci]; if (!isEditable(row, c)) return;
  if (ED.editing) commitEdit();
  const td = cellEl(ri, ci); const cur = row.cur[c.k] ?? "";
  let inp;
  const opts = c.t === "select" ? c.opts() : null;
  if (opts) { inp = document.createElement("select"); inp.innerHTML = `<option value="">(없음)</option>` + opts.map(o => `<option value="${esc(o)}"${o === cur ? " selected" : ""}>${esc(o)}</option>`).join("") + (cur && !opts.includes(cur) ? `<option value="${esc(cur)}" selected>${esc(cur)} (목록 외)</option>` : ""); }
  else { inp = document.createElement("input"); inp.type = c.t === "date" ? "date" : "text"; inp.value = initial != null ? initial : (c.t === "num" ? (cur === "" ? "" : String(cur)) : String(cur)); if (c.t === "num") inp.inputMode = "numeric"; }
  inp.className = "cell-input"; inp.setAttribute("aria-label", c.k); td.textContent = ""; td.appendChild(inp); td.classList.add("editing");
  ED.editing = { ri, ci, inp };
  inp.focus(); if (inp.select && initial == null && c.t !== "date") inp.select();
  inp.addEventListener("blur", () => { if (ED.editing && ED.editing.inp === inp) commitEdit(); });
}
function commitEdit(move) {
  const e = ED.editing; if (!e) return; ED.editing = null;
  const len0 = ED.rows.length;
  beginOp();
  const res = setCell(e.ri, e.ci, e.inp.value);
  const grewOne = ED.rows.length === len0 + 1;  // 빈 행에 입력 → 새 빈 행 하나 추가
  const reshaped = endOp();
  // 한 칸만 바뀌면 그 행(과 새로 붙은 빈 행)만 다시 그림. 빈 행 정리로 모양이 바뀌면 전체 다시 그림
  if (reshaped && !(grewOne && ED.rows.length === len0 + 1)) renderEditGrid();
  else { updateEditRow(e.ri); for (let ri = len0; ri < ED.rows.length; ri++) updateEditRow(ri); updateEditCount(); }
  if (!res.ok) { focusCell(e.ri, e.ci); return; }
  if (move === "down") focusCell(e.ri + 1, e.ci);
  else if (move === "next" || move === "prev") { ED.focus = [e.ri, e.ci]; tabMove(move === "prev"); }
  else focusCell(e.ri, e.ci);
}
function cancelEdit() { const e = ED.editing; if (!e) return; ED.editing = null; updateEditRow(e.ri); focusCell(e.ri, e.ci); }

// ---------- 키보드 ----------
$("#edit-grid").addEventListener("keydown", e => {
  if (ED.editing) {
    if (e.key === "Enter") { e.preventDefault(); commitEdit("down"); }
    else if (e.key === "Tab") { e.preventDefault(); commitEdit(e.shiftKey ? "prev" : "next"); }
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); cancelEdit(); }
    return;
  }
  const mod = e.ctrlKey || e.metaKey;
  if (e.target.matches?.("input[type=checkbox]")) { if (mod && e.key.toLowerCase() === "z") { e.preventDefault(); undoEdit(); } return; }  // 삭제 표시 체크박스는 기본 동작
  if (!ED.focus) return;
  const [ri, ci] = ED.focus;
  const nav = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] }[e.key];
  if (nav) { e.preventDefault(); focusCell(ri + nav[0], ci + nav[1], e.shiftKey); return; }
  if (e.key === "Tab") { e.preventDefault(); tabMove(e.shiftKey); return; }
  if (e.key === "Enter" || e.key === "F2") { e.preventDefault(); startEdit(ri, ci); return; }
  if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); clearRange(); return; }
  if (mod && e.key.toLowerCase() === "z") { e.preventDefault(); undoEdit(); return; }
  if (mod && e.key.toLowerCase() === "d") { e.preventDefault(); fillDown(); return; }
  if (mod && e.key.toLowerCase() === "c") { copyRange(e); return; }
  if (mod && e.key.toLowerCase() === "v") { return; }  // paste 이벤트에서 처리
  if (e.key === "Escape") { return; }
  if (e.key.length === 1 && !mod && !e.altKey) { e.preventDefault(); startEdit(ri, ci, e.key); }
});
// Ctrl+S = 저장 (편집 중이면 먼저 확정)
$("#dlg-edit").addEventListener("keydown", e => {
  if (!((e.ctrlKey || e.metaKey) && !e.altKey && e.key.toLowerCase() === "s")) return;
  e.preventDefault(); e.stopPropagation();
  if (ED.editing) commitEdit();
  updateEditCount();
  const save = $("#edit-save");
  if (save.disabled) { showAlert("저장할 변경이 없습니다.", "warn"); return; }
  save.click();
});
$("#edit-grid").addEventListener("mousedown", e => {
  const td = e.target.closest("td[data-ci]"); if (!td) return;
  if (ED.editing && ED.editing.inp.contains(e.target)) return;
  if (ED.editing) commitEdit();
  e.preventDefault(); focusCell(+td.dataset.ri, +td.dataset.ci, e.shiftKey);
});
$("#edit-grid").addEventListener("dblclick", e => { const td = e.target.closest("td[data-ci]"); if (td) startEdit(+td.dataset.ri, +td.dataset.ci); });
function toggleDel(ris, val) {
  beginOp();
  ris.forEach(ri => { const r = ED.rows[ri]; if (!r || r.blank) return; const v = val === undefined ? !r.del : val; if (r.del !== v) { snapRow(ri); r.del = v; } });
  endOp(); renderEditGrid();
}
$("#edit-grid").addEventListener("change", e => {
  if (e.target.id === "edit-all") { toggleDel(ED.rows.map((_, i) => i), e.target.checked); $("#edit-all")?.focus(); return; }
  if (e.target.dataset.sel !== undefined) { const ri = +e.target.dataset.sel; toggleDel([ri], e.target.checked); $(`#edit-grid input[data-sel="${ri}"]`)?.focus(); }
});
function clearRange() {
  const [r0, r1, c0, c1] = rangeBounds(); const f = [...ED.focus], a = ED.anchor ? [...ED.anchor] : f;
  beginOp(); for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) setCell(r, c, "", { quiet: true }); endOp();
  renderEditGrid(); ED.anchor = a; focusCell(f[0], f[1], true);
}
function fillDown() {
  const [r0, r1, c0, c1] = rangeBounds();
  beginOp();
  for (let c = c0; c <= c1; c++) { const src = r0 > 0 && r0 === r1 ? ED.rows[r0 - 1].cur[EDIT_COLS[c].k] : ED.rows[r0].cur[EDIT_COLS[c].k]; const start = r0 === r1 ? r0 : r0 + 1; for (let r = start; r <= r1; r++) setCell(r, c, src ?? "", { quiet: true }); }
  endOp();
  renderEditGrid(); focusCell(ED.focus[0], ED.focus[1], true);
}
function copyRange(e) {
  const [r0, r1, c0, c1] = rangeBounds(); const lines = [];
  const q = v => /[\t\n"]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;  // 엑셀과 같은 따옴표 규칙
  for (let r = r0; r <= r1; r++) { const cells = []; for (let c = c0; c <= c1; c++) { const v = ED.rows[r].cur[EDIT_COLS[c].k]; cells.push(q(v == null ? "" : String(v))); } lines.push(cells.join("\t")); }
  const text = lines.join("\n");
  try { navigator.clipboard.writeText(text); e.preventDefault(); showAlert(`${lines.length}행 복사`, "ok"); } catch { }
}
// 엑셀 TSV: 따옴표로 감싼 칸 안의 줄바꿈·탭, "" 이스케이프 처리. 끝 줄바꿈은 무시
function parseTSV(text) {
  const rows = []; let row = [], cell = "", q = false, start = true;
  text = text.replace(/\r\n?/g, "\n");
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) {
      if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; }
      else cell += ch;
      continue;
    }
    if (ch === '"' && start) { q = true; start = false; continue; }
    if (ch === "\t") { row.push(cell); cell = ""; start = true; continue; }
    if (ch === "\n") { row.push(cell); rows.push(row); row = []; cell = ""; start = true; continue; }
    cell += ch; start = false;
  }
  if (cell !== "" || row.length || !start) { row.push(cell); rows.push(row); }
  return rows;
}
$("#edit-grid").addEventListener("paste", e => {
  if (ED.editing || !ED.focus) return;
  const text = e.clipboardData.getData("text/plain"); if (!text) return;
  e.preventDefault();
  const grid = parseTSV(text); if (!grid.length) return;
  const [ri, ci] = ED.focus; const bad = []; let locked = 0;
  beginOp();
  grid.forEach((cells, dr) => {
    const r = ri + dr; while (ED.rows.length <= r) ED.rows.push(newEditRow());
    cells.forEach((v, dc) => {
      const c = ci + dc; if (c >= EDIT_COLS.length) return;
      const row = ED.rows[r], col = EDIT_COLS[c];
      const res = setCell(r, c, v, { quiet: true });
      if (res.ok) return;
      const t = String(v).trim();
      if (res.why === "locked") { if (t !== "" && t !== fmtCell(row, col) && t !== String(row.cur[col.k] ?? "")) locked++; return; }
      markBad(r, c, `${col.k}: ${res.msg} ('${v}')`);
      bad.push(`${r + 1}행 ${col.k}: '${t.length > 20 ? t.slice(0, 20) + "…" : t}'`);
    });
  });
  endOp();
  renderEditGrid(); ED.anchor = [ri, ci];
  focusCell(Math.min(ED.rows.length - 1, ri + grid.length - 1), Math.min(EDIT_COLS.length - 1, ci + Math.max(...grid.map(l => l.length)) - 1), true);
  const parts = [`${grid.length}행 붙여넣기`];
  if (bad.length) parts.push(`형식 오류 ${bad.length}칸 건너뜀 — ${bad.slice(0, 3).join(", ")}${bad.length > 3 ? ` 외 ${bad.length - 3}칸` : ""}`);
  if (locked) parts.push(`잠긴 칸 ${locked}개 건너뜀`);
  showAlert(parts.join(" · "), bad.length || locked ? "warn" : "ok");
});

// ---------- 저장 / 취소 ----------
function editChanges() {
  const updates = [], creates = [], deletes = [];
  ED.rows.forEach(row => {
    if (row.blank) return;
    if (row.isNew) { if (!row.del) creates.push({ ...row.cur }); return; }
    if (row.del) { deletes.push({ row: row._row, expect: expectOf("exec", row.orig) }); return; }
    const rec = {}; EDIT_COLS.forEach(c => { if (!c.ro && isChanged(row, c.k)) rec[c.k] = row.cur[c.k]; });
    if (Object.keys(rec).length) updates.push({ row: row._row, rec, expect: expectOf("exec", row.orig) });
  });
  return { updates, creates, deletes };
}
$("#edit-save").addEventListener("click", async () => {
  if (ED.editing) commitEdit();
  const ch = editChanges();
  // 클라이언트 필수 검사
  let firstBad = null;
  ED.rows.forEach((row, ri) => { row.err = null; if (row.blank || row.del || (!row.isNew && !EDIT_COLS.some(c => isChanged(row, c.k)))) return; const miss = EDIT_COLS.filter(c => c.req && (row.cur[c.k] === "" || row.cur[c.k] == null)); if (miss.length) { row.err = `입력 필요: ${miss.map(c => c.k).join(", ")}`; firstBad = firstBad ?? ri; } });
  if (firstBad != null) { renderEditGrid(); focusCell(firstBad, 2); showAlert(ED.rows[firstBad].err, "warn"); return; }
  if (!(ch.updates.length || ch.creates.length || ch.deletes.length)) { showAlert("변경이 없습니다.", "warn"); return; }
  if (ch.deletes.length && !await confirmDlg({ title: "편집 내용 저장", body: `수정 ${ch.updates.length}건 · 추가 ${ch.creates.length}건 · 삭제 ${ch.deletes.length}건을 한 번에 저장합니다. 삭제는 되돌리기로 복구할 수 있습니다.`, verb: "저장", danger: true })) return;
  const btn = $("#edit-save"); btn.disabled = true; btn.textContent = "저장 중…";
  try {
    const res = await api("POST", "/api/exec/batch", ch);
    $("#dlg-edit").close(); ED.open = false;
    showAlert(`저장했습니다. 수정 ${res.updated} · 추가 ${res.created.length} · 삭제 ${res.deleted}`, "ok", { undo: true });
    await load();
  } catch (err) {
    const m = /^(행 (\S+)|새 행 (\d+)):\s*/.exec(err.message);
    if (m) { const ri = m[2] ? ED.rows.findIndex(r => r.orig && r.orig["거래번호"] === m[2]) : (() => { let n = 0; return ED.rows.findIndex(r => r.isNew && !r.blank && !r.del && ++n === +m[3]); })(); if (ri >= 0) { ED.rows[ri].err = err.message; renderEditGrid(); focusCell(ri, 2); } }
    showAlert("저장 실패: " + err.message + " (아무것도 저장되지 않았습니다)", "error");
  } finally { btn.disabled = false; btn.textContent = "저장"; updateEditCount(); }
});
async function closeEditMode() {
  if (ED.editing) commitEdit();
  const ch = editChanges();
  if ((ch.updates.length || ch.creates.length || ch.deletes.length) && !await confirmDlg({ title: "편집 취소", body: "저장하지 않은 변경을 버리고 닫습니다.", verb: "버리고 닫기", danger: true })) return;
  $("#dlg-edit").close(); ED.open = false;
}
$("#edit-cancel").addEventListener("click", closeEditMode);
$("#edit-close").addEventListener("click", closeEditMode);
$("#dlg-edit").addEventListener("cancel", e => { e.preventDefault(); closeEditMode(); });
$("#edit-add").addEventListener("click", () => { const last = ED.rows.length - 1; focusCell(last, 2); startEdit(last, 2); });
$("#edit-del").addEventListener("click", () => { if (!ED.focus) return; const [r0, r1] = rangeBounds(); const f = [...ED.focus]; toggleDel(Array.from({ length: r1 - r0 + 1 }, (_, i) => r0 + i)); focusCell(f[0], f[1]); });
document.addEventListener("click", e => { if (e.target.closest("#btn-edit-mode")) openEditMode(); });
