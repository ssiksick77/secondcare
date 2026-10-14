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

const ED = { rows: [], undo: [], focus: null, anchor: null, editing: null, open: false };

function openEditMode() {
  const src = filtered("exec").slice().sort((a, b) => (b["원인발생일"] || "").localeCompare(a["원인발생일"] || "") || b._row - a._row);
  ED.rows = src.map(r => ({ _row: r._row, orig: r, cur: { ...r }, isNew: false, del: false, locked: !!execOrigin(r)?.locked, err: null }));
  ED.rows.push(newEditRow());
  ED.undo = []; ED.focus = null; ED.anchor = null; ED.editing = null; ED.open = true;
  $("#edit-note").textContent = `${src.length}건 (현재 필터 기준). 더블클릭·Enter·글자 입력으로 편집, Tab/방향키 이동, Ctrl+V 로 엑셀 붙여넣기, Ctrl+D 위 칸 채우기, Ctrl+Z 되돌리기. 맨 아래 빈 행에 입력하면 새 행이 됩니다.`;
  renderEditGrid();
  const d = $("#dlg-edit"); d.showModal();
  focusCell(0, 2);
}
function newEditRow() {
  const cur = Object.fromEntries(EDIT_COLS.map(c => [c.k, ""]));
  cur["원인발생일"] = ""; cur["재원"] = FILTERS.exec?.["재원"] || "";
  return { _row: null, orig: null, cur, isNew: true, del: false, locked: false, err: null, blank: true };
}
const isEditable = (row, c) => !c.ro && !row.del && !(row.locked && EDIT_LOCKED.includes(c.k));
function cellVal(row, c) { return c.calc ? c.calc(row.cur) : row.cur[c.k]; }
function fmtCell(row, c) { const v = cellVal(row, c); if (v == null || v === "") return ""; return c.t === "num" ? fmt(v) : String(v); }
function isChanged(row, k) { return !row.isNew && row.orig && String(row.orig[k] ?? "") !== String(row.cur[k] ?? ""); }

function renderEditGrid() {
  const head = `<thead><tr><th class="sel"><input type="checkbox" id="edit-all" aria-label="전체 선택"></th>${EDIT_COLS.map(c => `<th style="width:${c.w}px"${c.t === "num" ? ' class="num"' : ""}>${esc(c.k)}${c.req ? ' <span class="req">*</span>' : ""}</th>`).join("")}</tr></thead>`;
  const body = ED.rows.map((row, ri) => `<tr data-ri="${ri}" class="${row.del ? "del" : ""}${row.isNew && !row.blank ? " new" : ""}${row.err ? " err" : ""}"${row.err ? ` title="${esc(row.err)}"` : ""}><td class="sel"><input type="checkbox" data-sel="${ri}" ${row.del ? "checked" : ""} ${row.blank ? "disabled" : ""} aria-label="행 선택"></td>${EDIT_COLS.map((c, ci) => `<td data-ri="${ri}" data-ci="${ci}" tabindex="-1" class="${c.t === "num" ? "num" : ""}${isEditable(row, c) ? "" : " ro"}${isChanged(row, c.k) ? " chg" : ""}">${esc(fmtCell(row, c))}</td>`).join("")}</tr>`).join("");
  $("#edit-grid").innerHTML = head + `<tbody>${body}</tbody>`;
  updateEditCount();
}
function updateEditCount() {
  const n = ED.rows.filter(r => r.del && !r.blank).length, m = ED.rows.filter(r => !r.isNew && !r.del && EDIT_COLS.some(c => isChanged(r, c.k))).length, a = ED.rows.filter(r => r.isNew && !r.blank && !r.del).length;
  $("#edit-count").textContent = (m || a || n) ? `수정 ${m} · 추가 ${a} · 삭제 ${n}` : "변경 없음";
  $("#edit-save").disabled = !(m || a || n);
}
function cellEl(ri, ci) { return $(`#edit-grid td[data-ri="${ri}"][data-ci="${ci}"]`); }
function focusCell(ri, ci, extend = false) {
  ri = Math.max(0, Math.min(ED.rows.length - 1, ri)); ci = Math.max(0, Math.min(EDIT_COLS.length - 1, ci));
  if (!extend) ED.anchor = [ri, ci];
  ED.focus = [ri, ci];
  $$("#edit-grid td.cur, #edit-grid td.rng").forEach(td => td.classList.remove("cur", "rng"));
  const [r0, r1] = [Math.min(ED.anchor[0], ri), Math.max(ED.anchor[0], ri)], [c0, c1] = [Math.min(ED.anchor[1], ci), Math.max(ED.anchor[1], ci)];
  for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) cellEl(r, c)?.classList.add("rng");
  const el = cellEl(ri, ci); if (el) { el.classList.add("cur"); el.focus({ preventScroll: false }); el.scrollIntoView({ block: "nearest", inline: "nearest" }); }
}
function rangeBounds() { const [a, f] = [ED.anchor || ED.focus, ED.focus]; return [Math.min(a[0], f[0]), Math.max(a[0], f[0]), Math.min(a[1], f[1]), Math.max(a[1], f[1])]; }

// ---------- 값 설정 (되돌리기 기록 + 빈 행 자동 추가) ----------
function setCell(ri, ci, val, { record = true, rerender = true } = {}) {
  const row = ED.rows[ri], c = EDIT_COLS[ci]; if (!row || !c || !isEditable(row, c)) return false;
  let v = val;
  if (c.t === "num") { const ev = evalAmount(String(v)); if (ev === null) { showAlert(`${c.k}: 수식을 계산할 수 없습니다.`, "warn"); return false; } v = ev !== undefined ? ev : (String(v).replace(/[,\s원]/g, "") === "" ? "" : Number(String(v).replace(/[,\s원]/g, ""))); if (v !== "" && isNaN(v)) { showAlert(`${c.k}: 숫자가 아닙니다.`, "warn"); return false; } }
  else if (c.t === "date") { v = normDate(String(v)); if (v === null) { showAlert(`${c.k}: 날짜 형식(YYYY-MM-DD)이 아닙니다.`, "warn"); return false; } }
  else v = String(v ?? "").trim();
  const prev = row.cur[c.k];
  if (String(prev ?? "") === String(v ?? "")) return true;
  row.cur[c.k] = v; row.err = null;
  if (record) ED.undo.push({ ri, ci, prev });
  if (row.blank && v !== "") { row.blank = false; ED.rows.push(newEditRow()); if (rerender) renderEditGrid(); }
  else if (rerender) { const td = cellEl(ri, ci); if (td) { td.textContent = fmtCell(row, c); td.classList.toggle("chg", isChanged(row, c.k)); } cellEl(ri, 1).textContent = fmtCell(row, EDIT_COLS[1]); updateEditCount(); }
  return true;
}
function normDate(s) {
  s = s.trim(); if (!s) return "";
  const m = s.match(/^(\d{4})[-./](\d{1,2})[-./](\d{1,2})$/) || s.match(/^(\d{4})(\d{2})(\d{2})$/);
  if (!m) return null;
  const d = new Date(+m[1], +m[2] - 1, +m[3]); if (d.getMonth() !== +m[2] - 1) return null;
  return `${m[1]}-${String(m[2]).padStart(2, "0")}-${String(m[3]).padStart(2, "0")}`;
}

// ---------- 셀 편집기 ----------
function startEdit(ri, ci, initial) {
  const row = ED.rows[ri], c = EDIT_COLS[ci]; if (!isEditable(row, c)) return;
  if (ED.editing) commitEdit();
  const td = cellEl(ri, ci); const cur = row.cur[c.k] ?? "";
  let inp;
  const opts = c.t === "select" ? c.opts() : null;
  if (opts) { inp = document.createElement("select"); inp.innerHTML = `<option value="">(없음)</option>` + opts.map(o => `<option value="${esc(o)}"${o === cur ? " selected" : ""}>${esc(o)}</option>`).join("") + (cur && !opts.includes(cur) ? `<option value="${esc(cur)}" selected>${esc(cur)} (목록 외)</option>` : ""); }
  else { inp = document.createElement("input"); inp.type = c.t === "date" ? "date" : "text"; inp.value = initial != null ? initial : (c.t === "num" ? (cur === "" ? "" : String(cur)) : String(cur)); if (c.t === "num") inp.inputMode = "numeric"; }
  inp.className = "cell-input"; td.textContent = ""; td.appendChild(inp); td.classList.add("editing");
  ED.editing = { ri, ci, inp };
  inp.focus(); if (inp.select && initial == null && c.t !== "date") inp.select();
  inp.addEventListener("blur", () => { if (ED.editing && ED.editing.inp === inp) commitEdit(); });
}
function commitEdit(move) {
  const e = ED.editing; if (!e) return; ED.editing = null;
  const ok = setCell(e.ri, e.ci, e.inp.value, { rerender: false });
  const row = ED.rows[e.ri], c = EDIT_COLS[e.ci];
  if (row.blank === false && ED.rows[ED.rows.length - 1].blank !== true) { ED.rows.push(newEditRow()); }
  renderEditGrid();
  if (!ok) { focusCell(e.ri, e.ci); return; }
  if (move === "down") focusCell(e.ri + 1, e.ci); else if (move === "right") focusCell(e.ri, e.ci + 1); else if (move === "left") focusCell(e.ri, e.ci - 1); else focusCell(e.ri, e.ci);
}
function cancelEdit() { const e = ED.editing; if (!e) return; ED.editing = null; renderEditGrid(); focusCell(e.ri, e.ci); }

// ---------- 키보드 ----------
$("#edit-grid").addEventListener("keydown", e => {
  if (ED.editing) {
    if (e.key === "Enter") { e.preventDefault(); commitEdit("down"); }
    else if (e.key === "Tab") { e.preventDefault(); commitEdit(e.shiftKey ? "left" : "right"); }
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); cancelEdit(); }
    return;
  }
  if (!ED.focus) return;
  const [ri, ci] = ED.focus;
  const nav = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] }[e.key];
  if (nav) { e.preventDefault(); focusCell(ri + nav[0], ci + nav[1], e.shiftKey); return; }
  if (e.key === "Tab") { e.preventDefault(); focusCell(ri, ci + (e.shiftKey ? -1 : 1)); return; }
  if (e.key === "Enter" || e.key === "F2") { e.preventDefault(); startEdit(ri, ci); return; }
  if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); const [r0, r1, c0, c1] = rangeBounds(); for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) setCell(r, c, "", { rerender: false }); renderEditGrid(); focusCell(ri, ci); return; }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); undoEdit(); return; }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "d") { e.preventDefault(); fillDown(); return; }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "c") { copyRange(e); return; }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "v") { return; }  // paste 이벤트에서 처리
  if (e.key === "Escape") { return; }
  if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); startEdit(ri, ci, e.key); }
});
$("#edit-grid").addEventListener("mousedown", e => {
  const td = e.target.closest("td[data-ci]"); if (!td) return;
  if (ED.editing && ED.editing.inp.contains(e.target)) return;
  if (ED.editing) commitEdit();
  e.preventDefault(); focusCell(+td.dataset.ri, +td.dataset.ci, e.shiftKey);
});
$("#edit-grid").addEventListener("dblclick", e => { const td = e.target.closest("td[data-ci]"); if (td) startEdit(+td.dataset.ri, +td.dataset.ci); });
$("#edit-grid").addEventListener("change", e => {
  if (e.target.id === "edit-all") { ED.rows.forEach(r => { if (!r.blank) r.del = e.target.checked; }); renderEditGrid(); return; }
  if (e.target.dataset.sel !== undefined) { const row = ED.rows[+e.target.dataset.sel]; row.del = e.target.checked; renderEditGrid(); }
});
function undoEdit() { const u = ED.undo.pop(); if (!u) { showAlert("되돌릴 변경이 없습니다.", "warn"); return; } ED.rows[u.ri].cur[EDIT_COLS[u.ci].k] = u.prev; renderEditGrid(); focusCell(u.ri, u.ci); }
function fillDown() {
  const [r0, r1, c0, c1] = rangeBounds();
  for (let c = c0; c <= c1; c++) { const src = r0 > 0 && r0 === r1 ? ED.rows[r0 - 1].cur[EDIT_COLS[c].k] : ED.rows[r0].cur[EDIT_COLS[c].k]; const start = r0 === r1 ? r0 : r0 + 1; for (let r = start; r <= r1; r++) setCell(r, c, src ?? "", { rerender: false }); }
  renderEditGrid(); focusCell(ED.focus[0], ED.focus[1], true);
}
function copyRange(e) {
  const [r0, r1, c0, c1] = rangeBounds(); const lines = [];
  for (let r = r0; r <= r1; r++) { const cells = []; for (let c = c0; c <= c1; c++) { const v = ED.rows[r].cur[EDIT_COLS[c].k]; cells.push(v == null ? "" : String(v)); } lines.push(cells.join("\t")); }
  const text = lines.join("\n");
  try { navigator.clipboard.writeText(text); e.preventDefault(); showAlert(`${lines.length}행 복사`, "ok"); } catch { }
}
$("#edit-grid").addEventListener("paste", e => {
  if (ED.editing || !ED.focus) return;
  const text = e.clipboardData.getData("text/plain"); if (!text) return;
  e.preventDefault();
  const lines = text.replace(/\r/g, "").split("\n"); if (lines.length && lines[lines.length - 1] === "") lines.pop();
  const [ri, ci] = ED.focus; let bad = 0;
  lines.forEach((line, dr) => {
    const r = ri + dr; while (ED.rows.length <= r) ED.rows.push(newEditRow());
    line.split("\t").forEach((v, dc) => { const c = ci + dc; if (c >= EDIT_COLS.length) return; if (!setCell(r, c, v, { rerender: false })) bad++; });
    if (ED.rows[r].blank && line.split("\t").some(v => v.trim())) ED.rows[r].blank = false;
  });
  if (ED.rows[ED.rows.length - 1].blank !== true) ED.rows.push(newEditRow());
  renderEditGrid(); ED.anchor = [ri, ci]; focusCell(ri + lines.length - 1, Math.min(EDIT_COLS.length - 1, ci + Math.max(...lines.map(l => l.split("\t").length)) - 1), true);
  showAlert(`${lines.length}행 붙여넣기${bad ? ` (${bad}칸은 형식 오류로 건너뜀)` : ""}`, bad ? "warn" : "ok");
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
$("#edit-del").addEventListener("click", () => { const [r0, r1] = rangeBounds(); for (let r = r0; r <= r1; r++) if (!ED.rows[r].blank) ED.rows[r].del = !ED.rows[r].del; renderEditGrid(); focusCell(ED.focus[0], ED.focus[1]); });
document.addEventListener("click", e => { if (e.target.closest("#btn-edit-mode")) openEditMode(); });
