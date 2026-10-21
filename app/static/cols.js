/* 열 숨기기 (2026-10-21, 연구비 화면의 집행·품의·적립·예산 변경 내역·대시보드 집행 현황).
   한 열의 상태는 셋 중 하나다.
   - 보임: 폭을 갖는 보통 열.
   - 스텁: 10px 로 좁힌 열. 사용자가 숨긴 열, 폭이 모자라 자동으로 접힌 열, 기본 숨김 열(옛 '상세 열': 관리번호·세세목·사용자·비고).
     머리글을 누르면 다시 보인다. 숨긴 열이 있다는 사실을 늘 볼 수 있게 한다 (사용자 결정).
   - 없음: 화면에 아예 그리지 않는 열 (COLS 의 hide: true, 대시보드의 내부인건비·연구개발부담비). 이 파일은 관여하지 않는다.
   사용자 선택은 sessionStorage (한 세션만, 다음 접속 때 초기화). 번호 열·작업 열·대시보드의 재원·항목 열은 숨길 수 없고, 숨길 수 있는 열 중 하나는 늘 보여야 한다.
   표 폭: 보이는 열의 폭 합을 표의 min-width 로 두고 width 는 100% 라 틀 폭을 늘 채운다. 넘치면 표 틀이 가로 스크롤한다. */

const COLW = {  // 열 폭(px). 폭이 없는 열(적요 등)이 남는 폭을 모두 가진다
  exec: { 거래번호: 120, 상태: 100, 관리번호: 90, 원인발생일: 64, 재원: 84, 예산목: 112, 세목: 84, 세세목: 90, 결제수단: 84, 금액: 104, "예산목 잔액": 104, 사용자: 90, 작성자: 80, 태그: 72, 증빙: 44, 비고: 140, _flex: "적요", _min: 160 },
  req: { 품의번호: 120, 상태: 84, 지출예정일: 64, 재원: 84, 예산목: 112, 세목: 84, 세세목: 90, 거래처: 100, 결제수단: 84, 금액: 104, 태그: 72, 품의자: 96, 작성자: 80, 비고: 120, _actions: 150, _flex: "적요", _min: 140 },
  deposit: { 적립번호: 150, 일자: 64, 거래처: 110, 구분: 60, 상태: 96, 금액: 104, 사용자: 90, 작성자: 80, 증빙번호: 130, 연결거래번호: 120, 증빙: 44, 비고: 120, _actions: 110, _flex: "적요", _min: 160 },
  budget: { 변경회차: 60, 신청일자: 64, 변경사유: 160, _num: 104, _actions: 110 },  // 숫자 열은 모두 104
  dash: { 재원: 72, 항목: 84, _num: 108, 합계: 116 },
};
// 숨길 수 없는 열
const COL_FIXED = { exec: ["거래번호"], req: ["품의번호"], deposit: ["적립번호"], budget: [], dash: ["재원", "항목"] };
// 기본 숨김(스텁) 열: 옛 '상세 열'
const COL_MINOR = { exec: ["관리번호", "세세목", "사용자", "비고"], req: [], deposit: [], budget: [], dash: [] };
// 본문 폭에 따른 자동 접기 (폭 < 기준 이면 스텁). 날짜 열은 접지 않는다 (비평 P1)
const COL_FOLD = {
  exec: [[1300, ["결제수단", "예산목 잔액"]], [1100, ["세목", "태그", "작성자"]], [900, ["재원", "증빙"]], [760, ["예산목"]]],
  req: [[1500, ["비고", "세세목", "결제수단"]], [1300, ["세목", "품의자", "작성자"]], [1100, ["태그"]], [900, ["재원", "거래처"]], [760, ["예산목"]]],
  deposit: [[1400, ["비고", "연결거래번호"]], [1100, ["사용자", "작성자", "증빙번호"]], [900, ["상태", "증빙"]]],
  budget: [], dash: [],
};
const COL_TABLE = { exec: "#exec-table", req: "#req-table", deposit: "#deposit-table", budget: "#budget-table", dash: "#dash-table" };
const STUB_W = 10;

function colPrefs(kind) { try { return JSON.parse(sessionStorage.getItem("ledger-cols-" + kind) || "{}"); } catch { return {}; } }
function setColPrefs(kind, p) { try { sessionStorage.setItem("ledger-cols-" + kind, JSON.stringify(p)); } catch { } }
function colKeys(kind) {  // 표에 그려진 열 이름 (없음 열은 이미 빠져 있다)
  return [...document.querySelectorAll(`${COL_TABLE[kind]} thead th[data-col]`)].map(th => th.dataset.col);
}
function colHideable(kind) { return colKeys(kind).filter(k => !COL_FIXED[kind].includes(k)); }
// 열의 상태: "show" | "stub" 와 그 이유
function colState(kind, k, mainW) {
  if (COL_FIXED[kind].includes(k)) return { s: "show" };
  const p = colPrefs(kind);
  if ((p.hidden || []).includes(k)) return { s: "stub", why: "숨김" };
  if ((p.shown || []).includes(k)) return { s: "show" };
  if (COL_MINOR[kind].includes(k)) return { s: "stub", why: "기본 숨김" };
  for (const [w, keys] of COL_FOLD[kind]) if (mainW < w && keys.includes(k)) return { s: "stub", why: "폭 부족" };
  return { s: "show" };
}
function applyCols(kind) {
  const table = document.querySelector(COL_TABLE[kind]); if (!table) return;
  const mainW = document.querySelector("main")?.clientWidth || 9999;
  const W = COLW[kind];
  let min = 0, flexSeen = false;
  const th = [...table.querySelectorAll("thead th")];
  th.forEach(h => {
    const k = h.dataset.col;
    if (!k) {  // 작업 열 등
      if (h.classList.contains("actions") && W._actions) { h.style.width = W._actions + "px"; min += W._actions; }
      return;
    }
    const st = colState(kind, k, mainW);
    const stub = st.s === "stub";
    const w = stub ? STUB_W : (W[k] ?? (h.classList.contains("num") ? W._num : undefined));
    if (k === W._flex) { h.style.width = stub ? STUB_W + "px" : ""; min += stub ? STUB_W : W._min; flexSeen = true; }
    else if (w != null) { h.style.width = w + "px"; min += w; }
    h.classList.toggle("col-stub", stub);
    h.title = stub ? `${k} (${st.why}) · 누르면 보입니다` : (h.dataset.title || "");
    table.querySelectorAll(`tbody td[data-col="${CSS.escape(k)}"], tfoot td[data-col="${CSS.escape(k)}"]`).forEach(td => td.classList.toggle("col-stub", stub));
  });
  table.style.minWidth = min + "px";
  table.dataset.stubs = th.filter(h => h.classList.contains("col-stub")).length;
  if (typeof fixEmptySpan === "function") fixEmptySpan(table);
}
function applyAllCols() { Object.keys(COL_TABLE).forEach(applyCols); }
function colToggle(kind, k, show) {
  const p = colPrefs(kind); const hidden = new Set(p.hidden || []), shown = new Set(p.shown || []);
  if (show) { hidden.delete(k); shown.add(k); }
  else {
    const visible = colHideable(kind).filter(x => colState(kind, x, document.querySelector("main")?.clientWidth || 9999).s === "show");
    if (visible.length <= 1 && visible.includes(k)) { showAlert("열은 하나 이상 보여야 합니다.", "warn"); return; }
    shown.delete(k); hidden.add(k);
  }
  setColPrefs(kind, { hidden: [...hidden], shown: [...shown] });
  applyCols(kind);
}

// ---- 머리글 우클릭 메뉴 · 스텁 클릭 ----
let COLMENU = null;
function closeColMenu() { if (COLMENU) { COLMENU.remove(); COLMENU = null; } }
function openColMenu(kind, k, x, y) {
  closeColMenu();
  const stub = colState(kind, k, document.querySelector("main")?.clientWidth || 9999).s === "stub";
  const fixed = COL_FIXED[kind].includes(k);
  const m = document.createElement("div"); m.className = "ctx-menu"; m.setAttribute("role", "menu");
  m.innerHTML = `<div class="ctx-title">${esc(k)}</div>`
    + (fixed ? `<div class="ctx-note">이 열은 숨길 수 없습니다</div>`
      : `<button type="button" role="menuitem" data-show="${stub ? 1 : 0}">${stub ? "열 보이기" : "이 열 숨기기"}</button>`)
    + `<button type="button" role="menuitem" data-manage="1">조회 열 관리…</button>`;
  document.body.appendChild(m);
  m.style.left = Math.min(x, window.innerWidth - m.offsetWidth - 8) + "px"; m.style.top = Math.min(y, window.innerHeight - m.offsetHeight - 8) + "px";
  m.addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.dataset.manage) { closeColMenu(); openColPopover(kind, document.querySelector(`[data-cols="${kind}"]`)); return; }
    colToggle(kind, k, b.dataset.show === "1"); closeColMenu();
  });
  COLMENU = m; m.querySelector("button")?.focus();
}
document.addEventListener("contextmenu", e => {
  const th = e.target.closest("table.grid thead th[data-col]"); if (!th) return;
  const kind = Object.keys(COL_TABLE).find(k => th.closest(COL_TABLE[k])); if (!kind) return;
  e.preventDefault(); openColMenu(kind, th.dataset.col, e.clientX, e.clientY);
});
document.addEventListener("click", e => {
  if (COLMENU && !COLMENU.contains(e.target)) closeColMenu();
  if (COLPOP && !COLPOP.contains(e.target) && !e.target.closest("[data-cols]")) closeColPopover();
  const th = e.target.closest("table.grid thead th.col-stub[data-col]");
  if (th) { const kind = Object.keys(COL_TABLE).find(k => th.closest(COL_TABLE[k])); if (kind) { e.preventDefault(); e.stopPropagation(); colToggle(kind, th.dataset.col, true); } }
}, true);
document.addEventListener("keydown", e => { if (e.key === "Escape") { closeColMenu(); closeColPopover(); } });

// ---- [조회 열 관리] 팝오버: 체크 목록 ----
let COLPOP = null;
function closeColPopover() { if (COLPOP) { COLPOP.remove(); COLPOP = null; } }
function openColPopover(kind, btn) {
  closeColPopover(); closeColMenu();
  const mainW = document.querySelector("main")?.clientWidth || 9999;
  const keys = colKeys(kind);
  const pop = document.createElement("div"); pop.className = "col-pop"; pop.setAttribute("role", "dialog"); pop.setAttribute("aria-label", "조회 열 관리");
  pop.innerHTML = `<div class="col-pop-head"><strong>조회 열</strong><span class="toolbar-note">체크를 풀면 10px 스텁으로 남고, 머리글을 누르면 다시 보입니다</span></div>`
    + `<div class="col-pop-list">${keys.map(k => {
      const st = colState(kind, k, mainW), fixed = COL_FIXED[kind].includes(k);
      return `<label class="chk${fixed ? " fixed" : ""}"><input type="checkbox" data-k="${esc(k)}"${st.s === "show" ? " checked" : ""}${fixed ? " disabled" : ""}> ${esc(k)}${fixed ? ' <span class="muted">(고정)</span>' : st.why && st.s === "stub" ? ` <span class="muted">(${esc(st.why)})</span>` : ""}</label>`;
    }).join("")}</div>`
    + `<div class="col-pop-foot"><button type="button" class="btn btn-sm" data-reset="1">기본으로</button><button type="button" class="btn btn-sm btn-ghost" data-close="1">닫기</button></div>`;
  document.body.appendChild(pop);
  const r = btn ? btn.getBoundingClientRect() : { left: 20, bottom: 100 };
  pop.style.left = Math.max(8, Math.min(r.left, window.innerWidth - pop.offsetWidth - 8)) + "px"; pop.style.top = (r.bottom + 4) + "px";
  pop.addEventListener("change", e => { const cb = e.target.closest("input[data-k]"); if (!cb) return; colToggle(kind, cb.dataset.k, cb.checked); const st = colState(kind, cb.dataset.k, mainW); cb.checked = st.s === "show"; });
  pop.addEventListener("click", e => {
    if (e.target.closest("[data-close]")) { closeColPopover(); btn?.focus(); }
    if (e.target.closest("[data-reset]")) { setColPrefs(kind, {}); applyCols(kind); closeColPopover(); openColPopover(kind, btn); }
  });
  COLPOP = pop; pop.querySelector("input:not([disabled])")?.focus();
}
document.addEventListener("click", e => { const b = e.target.closest("[data-cols]"); if (b) { if (COLPOP) closeColPopover(); else openColPopover(b.dataset.cols, b); } });
new ResizeObserver(() => applyAllCols()).observe(document.querySelector("main"));
