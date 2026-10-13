/* 인건비 관리 화면 (/labor) — app.js 의 공통 함수($, api, openForm, renderList, showAlert …)를 그대로 사용 */
"use strict";

// ---------- 공통 정의 확장 ----------
Object.assign(IDENT, { people: ["이름"], salary: ["이름", "시작월"], payee: ["지급처코드"], labor: ["지급월", "귀속월", "이름", "지급처"], ladj: ["월", "이름", "금액"] });
FILTERS.labor = {};
Object.assign(COLS, {
  labor: [{ k: "지급월" }, { k: "귀속월" }, { k: "이름" }, { k: "지급처" }, { k: "지급처명", calc: r => payeeName(r["지급처"]), wrap: true }, { k: "금액", t: "num", amt: true },
    { k: "상태", t: "badge" }, { k: "지급일", t: "date" }, { k: "연결거래번호" }, { k: "비고", wrap: true }],
  people: [{ k: "이름" }, { k: "인건비구분" }, { k: "입사일", t: "date" }, { k: "퇴사일", t: "date" }, { k: "기준급여", t: "num", calc: r => salaryFor(r["이름"], curMonth()), title: "이번 달 기준급여" },
    { k: "이월선급", t: "num", amt: true, title: "연초 이월 선급(+) / 미지급(−)" }, { k: "비고", wrap: true }],
  salary: [{ k: "이름" }, { k: "시작월" }, { k: "종료월" }, { k: "월액", t: "num", amt: true }, { k: "비고", wrap: true }],
  payee: [{ k: "지급처코드" }, { k: "지급처명", wrap: true }, { k: "인건비예산", t: "num", amt: true }, { k: "사용건수", t: "num", calc: r => DATA.labor.filter(x => x["지급처"] === r["지급처코드"]).length }, { k: "비고", wrap: true }],
  ladj: [{ k: "월" }, { k: "이름" }, { k: "금액", t: "num", amt: true }, { k: "사유", wrap: true }],
});
const LABOR_TITLES = { people: "인원", salary: "기준급여", payee: "외부 지급처", labor: "인건비 지급", ladj: "선급·미지급 조정" };
const LABOR_FORMS = {
  people: () => [
    { k: "이름", type: "text", req: true, focus: true }, { k: "인건비구분", type: "select", opts: DATA.meta.labor_kinds, req: true, hint: "확정 시 예산목 결정" },
    { k: "입사일", type: "date" }, { k: "퇴사일", type: "date", hint: "예정일도 가능" },
    { k: "이월선급", type: "num", hint: "연초 이월 선급(+) / 미지급(−)" }, { k: "비고", type: "text", cls: "wide" },
  ],
  salary: () => [
    { k: "이름", type: "select", opts: peopleNames(), req: true }, { k: "월액", type: "num", req: true },
    { k: "시작월", type: "month", req: true }, { k: "종료월", type: "month", req: true }, { k: "비고", type: "text", cls: "wide" },
  ],
  payee: () => [
    { k: "지급처코드", type: "text", req: true, focus: true, hint: "'-' 없이. 집행내역 재원 열과 거래번호에 사용" }, { k: "지급처명", type: "text", cls: "mid" },
    { k: "인건비예산", type: "num", hint: "비우면 '관리 안 함'" }, { k: "비고", type: "text", cls: "mid" },
  ],
  labor: () => [
    { k: "이름", type: "select", opts: peopleNames(), req: true },
    { k: "귀속월", type: "month", req: true, hint: "급여가 발생한 달" }, { k: "지급월", type: "month", req: true },
    { k: "지급처", type: "select", opts: payeeOptions(), req: true, hint: "재원코드 또는 외부 지급처" },
    { k: "금액", type: "num", req: true, focus: true }, { k: "비고", type: "text" },
  ],
  ladj: () => [
    { k: "월", type: "month", req: true }, { k: "이름", type: "select", opts: peopleNames(), req: true },
    { k: "금액", type: "num", req: true, hint: "+ 선급 / − 미지급" }, { k: "사유", type: "text", cls: "wide" },
  ],
};
function laborDefaults(kind) {
  const m = curMonth();
  if (kind === "labor") return { 귀속월: m, 지급월: m, 지급처: FILTERS.labor["지급처"] || "", 이름: FILTERS.labor["이름"] || "" };
  if (kind === "ladj") return { 월: m };
  if (kind === "salary") return { 시작월: `${laborYear()}-01`, 종료월: `${laborYear()}-12` };
  if (kind === "people") return { 인건비구분: "내부" };
  return {};
}
function laborLabel(kind, r) {
  if (kind === "labor") return `${r["지급월"]} ${r["이름"]} · ${r["지급처"]} ${fmt(r["금액"])}원 (${r["상태"]})`;
  if (kind === "people") return `인원 ${r["이름"]}`;
  if (kind === "salary") return `${r["이름"]} 기준급여 ${r["시작월"]}~${r["종료월"]} ${fmt(r["월액"])}원`;
  if (kind === "payee") return `지급처 ${r["지급처코드"]} ${r["지급처명"] || ""}`;
  if (kind === "ladj") return `${r["월"]} ${r["이름"]} 조정 ${fmt(r["금액"])}원`;
  return null;
}

// ---------- 조회 도우미 ----------
const laborYear = () => $("#labor-year").value || String(new Date().getFullYear());
function curMonth() { const y = laborYear(), now = new Date(); return y === String(now.getFullYear()) ? localISO(now).slice(0, 7) : `${y}-01`; }
// 선급·미지급 기준월: 이번 달 급여는 아직 발생 전으로 보고 직전 달까지 누적 (2026-10-13 결정). 과거 연도는 12월까지
function closedMonth() { const y = laborYear(), now = new Date(); return y === String(now.getFullYear()) ? addMonth(localISO(now).slice(0, 7), -1) : (y < String(now.getFullYear()) ? `${y}-12` : `${y}-00`); }
const monthsOf = y => Array.from({ length: 12 }, (_, i) => `${y}-${String(i + 1).padStart(2, "0")}`);
const addMonth = (ym, n) => { let y = +ym.slice(0, 4), m = +ym.slice(5, 7) + n; while (m > 12) { m -= 12; y++; } while (m < 1) { m += 12; y--; } return `${y}-${String(m).padStart(2, "0")}`; };
const peopleNames = () => DATA.people.map(p => p["이름"]);
const payeeOptions = () => [...DATA.funds.map(f => f["재원코드"]), ...DATA.payee.map(p => p["지급처코드"])];
function payeeName(code) { const f = DATA.funds.find(x => x["재원코드"] === code); if (f) return f["과제명"] || ""; const p = DATA.payee.find(x => x["지급처코드"] === code); return p ? (p["지급처명"] || "") : "(미등록)"; }
function laborBudget(code) {
  const f = DATA.funds.find(x => x["재원코드"] === code);
  if (f) {
    if (f["인건비예산"] != null) return f["인건비예산"];
    const rows = DATA.budget.filter(r => r["재원"] === code);
    return rows.length ? rows.reduce((a, r) => a + (r["내부인건비(공통)"] || 0) + (r["외부인건비(공통)"] || 0), 0) : null;
  }
  const p = DATA.payee.find(x => x["지급처코드"] === code);
  return p ? p["인건비예산"] : null;
}
function salaryFor(name, month) { const t = DATA.salary.find(s => s["이름"] === name && s["시작월"] <= month && month <= s["종료월"]); return t ? t["월액"] : null; }
function activeIn(p, month) { if (p["입사일"] && month < p["입사일"].slice(0, 7)) return false; if (p["퇴사일"] && month > p["퇴사일"].slice(0, 7)) return false; return true; }
function prepaid(p, year, through) {
  // 이월선급 + 확정지급(지급월) − 발생(귀속월, 기준급여×재직월) + 조정, 기준월까지 누적. 양수 선급, 음수 미지급
  let accrued = 0, paid = 0, adj = 0;
  monthsOf(year).filter(m => m <= through).forEach(m => { if (activeIn(p, m)) accrued += salaryFor(p["이름"], m) || 0; });
  // 발생은 직전 달(through)까지, 확정 지급·조정은 이번 달까지 → 이번 달 지급은 선급으로 잡힘
  const payThrough = year === String(new Date().getFullYear()) ? curMonth() : `${year}-12`;
  DATA.labor.forEach(r => { if (r["이름"] === p["이름"] && r["상태"] === "확정" && r["지급월"].startsWith(year) && r["지급월"] <= payThrough) paid += r["금액"] || 0; });
  DATA.ladj.forEach(r => { if (r["이름"] === p["이름"] && r["월"].startsWith(year) && r["월"] <= payThrough) adj += r["금액"] || 0; });
  return { opening: p["이월선급"] || 0, accrued, paid, adj, balance: (p["이월선급"] || 0) + paid - accrued + adj };
}

// ---------- 화면 전환 ----------
function setMode(labor, push = true) {
  document.body.classList.toggle("labor-mode", labor);
  $("#labor-tabs").hidden = !labor; $("#main-tabs").hidden = labor;
  $$("#main-tabs [role=tab]").forEach(b => { $("#" + b.getAttribute("aria-controls")).hidden = labor || b.getAttribute("aria-selected") !== "true"; });
  $$("#labor-tabs [role=tab]").forEach(b => { $("#" + b.getAttribute("aria-controls")).hidden = !labor || b.getAttribute("aria-selected") !== "true"; });
  $("#btn-mode").textContent = labor ? "회계대장으로" : "인건비";
  $("#btn-mode").title = labor ? "회계대장 화면으로 돌아가기" : "인건비 관리 화면으로 전환";
  document.title = labor ? "센터 회계대장 · 인건비" : "센터 회계대장";
  if (labor) closeExecDrawer();
  if (push) history.pushState({}, "", labor ? "/labor" : "/");
}
function switchLaborTab(name) {
  $$("#labor-tabs [role=tab]").forEach(b => { const on = b.id === "ltab-" + name; b.setAttribute("aria-selected", on); $("#" + b.getAttribute("aria-controls")).hidden = !on; });
  try { localStorage.setItem("ledger-ltab", name); } catch { }
}
$$("#labor-tabs [role=tab]").forEach(b => b.addEventListener("click", () => switchLaborTab(b.id.replace("ltab-", ""))));
$("#btn-mode").addEventListener("click", () => setMode(!document.body.classList.contains("labor-mode")));
window.addEventListener("popstate", () => setMode(location.pathname === "/labor", false));
try { const t = localStorage.getItem("ledger-ltab"); if (t && $("#ltab-" + t)) switchLaborTab(t); } catch { }
setMode(location.pathname === "/labor", false);

// ---------- 렌더 ----------
function fillLaborSelects() {
  const years = new Set([String(new Date().getFullYear())]);
  DATA.labor.forEach(r => r["지급월"] && years.add(r["지급월"].slice(0, 4)));
  DATA.salary.forEach(r => years.add(r["시작월"].slice(0, 4)));
  const ys = [...years].sort().reverse();
  setOptions($("#labor-year"), ys, ys);
  if (!$("#labor-year").dataset.init) { $("#labor-year").value = String(new Date().getFullYear()); $("#labor-year").dataset.init = 1; }
  const names = peopleNames(), payees = payeeOptions();
  $$("select[data-filter='이름']").forEach(sel => setOptions(sel, ["", ...names], ["전체", ...names]));
  $$("select[data-filter='지급처']").forEach(sel => setOptions(sel, ["", ...payees], ["전체", ...payees]));
}
function renderLabor() {
  renderLaborFunds(); renderLaborPlan();
  renderList("labor"); renderList("people"); renderList("salary"); renderList("payee"); renderList("ladj");
  renderPrepaid();
}
function renderLaborFunds() {
  const y = laborYear();
  const codes = payeeOptions().filter(c => laborBudget(c) != null || DATA.labor.some(r => r["지급처"] === c && r["지급월"].startsWith(y)));
  const rows = codes.map(c => {
    const mine = DATA.labor.filter(r => r["지급처"] === c && r["지급월"].startsWith(y));
    const done = mine.filter(r => r["상태"] === "확정").reduce((a, r) => a + (r["금액"] || 0), 0);
    const plan = mine.filter(r => r["상태"] === "예정").reduce((a, r) => a + (r["금액"] || 0), 0);
    const b = laborBudget(c);
    return { c, name: payeeName(c), b, done, plan, external: !DATA.funds.some(f => f["재원코드"] === c) };
  });
  const t = rows.filter(r => r.b != null).reduce((a, r) => ({ b: a.b + r.b, done: a.done + r.done, plan: a.plan + r.plan }), { b: 0, done: 0, plan: 0 });
  const u = rows.filter(r => r.b == null).reduce((a, r) => ({ n: a.n + 1, done: a.done + r.done, plan: a.plan + r.plan }), { n: 0, done: 0, plan: 0 });
  const cell = (v, neg) => `<td class="num${neg ? " neg" : ""}">${v == null ? '<span class="muted" title="인건비예산 미입력">-</span>' : fmt(v)}</td>`;
  const line = r => `<tr><td>${esc(r.c)}${r.external ? ' <span class="muted">(외부)</span>' : ""}</td><td class="wrap">${esc(r.name)}</td><td class="num amt">${r.b == null ? '<span class="muted">관리 안 함</span>' : fmt(r.b)}</td>${cell(r.done)}${cell(r.plan)}${cell(r.b == null ? null : r.b - r.done, r.b != null && r.b - r.done < 0)}${cell(r.b == null ? null : r.b - r.done - r.plan, r.b != null && r.b - r.done - r.plan < 0)}</tr>`;
  $("#labor-funds").innerHTML = `<thead><tr><th>지급처</th><th>과제명 · 지급처명</th><th class="num amt">인건비 예산</th><th class="num">확정 지급</th><th class="num">예정</th><th class="num">확정잔액</th><th class="num">예정잔액</th></tr></thead><tbody>${rows.map(line).join("") || `<tr><td class="empty" colspan="7">${y}년 인건비 지급 건과 인건비 예산이 없습니다. 재원 탭의 예산변동(내부·외부인건비) 또는 재원의 인건비예산 열, 지급처 탭의 인건비예산을 확인하세요.</td></tr>`}</tbody>${rows.length ? `<tfoot><tr class="total"><td>합계 (예산 관리 지급처)</td><td></td><td class="num amt">${fmt(t.b)}</td><td class="num">${fmt(t.done)}</td><td class="num">${fmt(t.plan)}</td><td class="num${t.b - t.done < 0 ? " neg" : ""}">${fmt(t.b - t.done)}</td><td class="num${t.b - t.done - t.plan < 0 ? " neg" : ""}">${fmt(t.b - t.done - t.plan)}</td></tr>${u.n ? `<tr class="sub"><td>관리 안 함 지급처 ${u.n}곳</td><td class="muted">예산 없음 · 잔액 계산 제외</td><td class="num amt"></td><td class="num">${fmt(u.done)}</td><td class="num">${fmt(u.plan)}</td><td></td><td></td></tr>` : ""}</tfoot>` : ""}`;
  $("#labor-funds").closest(".table-wrap").classList.toggle("empty", !rows.length);
}
function renderLaborPlan() {
  const y = laborYear(), months = monthsOf(y), through = closedMonth();
  const people = DATA.people.filter(p => months.some(m => activeIn(p, m)) || DATA.labor.some(r => r["이름"] === p["이름"] && r["귀속월"].startsWith(y)));
  const head = `<thead><tr><th>이름</th><th>구분</th>${months.map((m, i) => `<th class="num${i === 0 ? " amt" : ""}">${i + 1}월</th>`).join("")}<th class="num amt">연간 배분</th><th class="num">확정</th><th class="num">예정</th><th class="num">선급 / 미지급</th></tr></thead>`;
  const body = people.map(p => {
    let year = 0, done = 0, plan = 0;
    const cells = months.map((m, i) => {
      const rows = DATA.labor.filter(r => r["이름"] === p["이름"] && r["귀속월"] === m);
      const sum = rows.reduce((a, r) => a + (r["금액"] || 0), 0);
      year += sum; done += rows.filter(r => r["상태"] === "확정").reduce((a, r) => a + r["금액"], 0); plan += rows.filter(r => r["상태"] === "예정").reduce((a, r) => a + r["금액"], 0);
      const sal = salaryFor(p["이름"], m), act = activeIn(p, m);
      let cls = "cell", sub = "";
      if (!act && !rows.length) { cls += " off"; sub = p["입사일"] && m < p["입사일"].slice(0, 7) ? "입사 전" : "퇴사"; }
      else if (!rows.length) { cls += " none"; sub = sal ? `소요 ${fmt(sal)}` : "미배정"; }
      else if (sal == null) { sub = "기준급여 없음"; }
      else if (sum < sal) { cls += " short"; sub = `부족 ${fmt(sal - sum)}`; }
      else if (sum > sal) { cls += " over"; sub = `초과 ${fmt(sum - sal)}`; }
      else { cls += " ok"; sub = "소요 일치"; }
      if (rows.some(r => r["상태"] === "확정")) cls += " has-done";
      return `<td class="num ${cls}${i === 0 ? " amt" : ""}" data-name="${esc(p["이름"])}" data-month="${m}" title="${esc(p["이름"])} ${m} · 클릭하여 배분 편집">${rows.length ? fmt(sum) : '<span class="muted">—</span>'}<small>${esc(sub)}</small></td>`;
    }).join("");
    const pp = prepaid(p, y, through);
    const ppTxt = pp.balance > 0 ? `<span class="muted">선급</span> ${fmt(pp.balance)}` : pp.balance < 0 ? `<span class="warn">미지급</span> ${fmt(-pp.balance)}` : "-";
    return `<tr><td>${esc(p["이름"])}</td><td class="muted">${esc(p["인건비구분"])}</td>${cells}<td class="num amt">${fmt(year)}</td><td class="num">${fmt(done)}</td><td class="num">${fmt(plan)}</td><td class="num" title="${through}까지: 이월 ${fmt(pp.opening)} + 확정지급 ${fmt(pp.paid)} − 발생 ${fmt(pp.accrued)} + 조정 ${fmt(pp.adj)}">${ppTxt}</td></tr>`;
  }).join("");
  const tot = months.map(m => DATA.labor.filter(r => r["귀속월"] === m).reduce((a, r) => a + (r["금액"] || 0), 0));
  const all = DATA.labor.filter(r => r["귀속월"].startsWith(y));
  const foot = people.length ? `<tfoot><tr class="total"><td>합계</td><td></td>${tot.map((v, i) => `<td class="num${i === 0 ? " amt" : ""}">${fmt(v)}</td>`).join("")}<td class="num amt">${fmt(tot.reduce((a, b) => a + b, 0))}</td><td class="num">${fmt(all.filter(r => r["상태"] === "확정").reduce((a, r) => a + r["금액"], 0))}</td><td class="num">${fmt(all.filter(r => r["상태"] === "예정").reduce((a, r) => a + r["금액"], 0))}</td><td></td></tr></tfoot>` : "";
  $("#labor-plan").innerHTML = head + `<tbody>${body || `<tr><td class="empty" colspan="18">인원이 없습니다. [인원] 탭에서 지급 대상을 먼저 등록하세요.</td></tr>`}</tbody>` + foot;
  $("#labor-plan").closest(".table-wrap").classList.toggle("empty", !people.length);
  $("#labor-plan-note").textContent = `${y}년 귀속월 기준 · 칸 = 예정+확정 배분 합계, 작은 글자 = 기준급여 대비 · 선급/미지급은 직전 달(${through.endsWith("-00") ? "없음" : through})까지 누적 (확정 지급 − 기준급여 발생)`;
}
function renderPrepaid() {
  const y = laborYear(), through = closedMonth();
  const rows = DATA.people.map(p => ({ p, ...prepaid(p, y, through) })).filter(x => x.opening || x.accrued || x.paid || x.adj);
  $("#labor-prepaid-note").textContent = `${y}년 직전 달(${through.endsWith("-00") ? "없음" : through})까지 누적. 이번 달 급여는 아직 발생 전으로 보며, 이번 달 확정 지급은 선급으로 잡힙니다. 잔액 = 이월선급 + 확정 지급(지급월) − 발생(귀속월 기준급여 × 재직월) + 조정. 양수 선급, 음수 미지급.`;
  $("#labor-prepaid").innerHTML = `<thead><tr><th>이름</th><th class="num amt">이월선급</th><th class="num">발생 누계</th><th class="num">확정 지급 누계</th><th class="num">조정</th><th class="num">잔액 (선급 + / 미지급 −)</th></tr></thead><tbody>${rows.map(x => `<tr><td>${esc(x.p["이름"])}</td><td class="num amt">${fmt(x.opening)}</td><td class="num">${fmt(x.accrued)}</td><td class="num">${fmt(x.paid)}</td><td class="num">${fmt(x.adj)}</td><td class="num${x.balance < 0 ? " neg" : ""}">${fmt(x.balance)}</td></tr>`).join("") || '<tr><td class="empty" colspan="6">기준급여·지급·조정 내역이 있는 인원이 없습니다.</td></tr>'}</tbody>`;
  $("#labor-prepaid").closest(".table-wrap").classList.toggle("empty", !rows.length);
}
$("#labor-year").addEventListener("change", () => { FILTERS.labor.year = ""; renderLabor(); });

// ---------- 확정 / 확정 취소 ----------
function laborConfirm(row) {
  const r = DATA.labor.find(x => x._row === row); if (!r) return;
  const d = $("#dlg-pay"); $("#pay-label").textContent = `${r["지급월"]} ${r["이름"]} · ${r["지급처"]} ${fmt(r["금액"])}원`; $("#pay-date").value = today();
  const p = DATA.people.find(x => x["이름"] === r["이름"]);
  $("#pay-note").textContent = `확정하면 집행내역에 재원 ${r["지급처"]} · ${p?.["인건비구분"] === "외부" ? "외부인건비(공통)" : "내부인건비(공통)"} 1건이 지급일 날짜로 추가되고, 이 지급 건은 잠깁니다. 금액·지급처를 바꾸려면 '확정 취소' 뒤에 수정하세요.`;
  d.dataset.row = row; d.showModal(); $("#pay-date").focus();
}
$("#dlg-pay-form").addEventListener("submit", async e => {
  e.preventDefault();
  const d = $("#dlg-pay"), row = Number(d.dataset.row), r = DATA.labor.find(x => x._row === row);
  try {
    const res = await api("POST", `/api/labor/${row}/action`, { action: "confirm", pay_date: $("#pay-date").value, expect: expectOf("labor", r) });
    d.close(); showAlert(`확정했습니다. 집행 ${res["연결거래번호"]} 생성`, "ok"); await load(); refreshCellDialog();
  } catch (err) { showAlert("확정 실패: " + err.message, "error"); }
});
$("#dlg-pay-cancel").addEventListener("click", () => $("#dlg-pay").close());
async function laborUnconfirm(row) {
  const r = DATA.labor.find(x => x._row === row); if (!r) return;
  const ev = DATA.evidence.filter(e => e["거래번호"] === r["연결거래번호"]).length;
  if (ev) return showAlert(`집행 ${r["연결거래번호"]} 에 증빙 ${ev}개가 등록되어 있어 확정을 취소할 수 없습니다. 집행내역 상세에서 증빙을 먼저 지우세요.`, "warn");
  if (!await confirmDlg({ title: "확정 취소", body: `${r["지급월"]} ${r["이름"]} · ${r["지급처"]} ${fmt(r["금액"])}원\n\n연결 집행 ${r["연결거래번호"] || ""} 이 집행내역에서 삭제되고 이 건은 '예정'으로 돌아갑니다.`, verb: "확정 취소", danger: true })) return;
  try { await api("POST", `/api/labor/${row}/action`, { action: "unconfirm", expect: expectOf("labor", r) }); showAlert("확정을 취소했습니다 (예정으로 되돌림).", "ok", { undo: true }); await load(); refreshCellDialog(); }
  catch (err) { showAlert("취소 실패: " + err.message, "error"); }
}

// ---------- 계획표 셀 편집 ----------
const CELL = { name: null, month: null };
function openCellDialog(name, month) {
  CELL.name = name; CELL.month = month;
  refreshCellDialog(); const d = $("#dlg-cell"); if (!d.open) d.showModal();
}
function refreshCellDialog() {
  if (!CELL.name || !$("#dlg-cell").open && !document.body.contains($("#dlg-cell"))) return;
  if (!CELL.name) return;
  const rows = DATA.labor.filter(r => r["이름"] === CELL.name && r["귀속월"] === CELL.month);
  const sal = salaryFor(CELL.name, CELL.month), sum = rows.reduce((a, r) => a + (r["금액"] || 0), 0);
  $("#cell-title").textContent = `${CELL.name} · ${CELL.month} 배분`;
  $("#cell-note").textContent = (sal != null ? `기준급여 ${fmt(sal)}원 · ` : "기준급여 없음 · ") + `배분 합계 ${fmt(sum)}원` + (sal != null && sum !== sal ? ` (${sum < sal ? "부족" : "초과"} ${fmt(Math.abs(sal - sum))}원)` : "");
  $("#cell-table").innerHTML = `<thead><tr><th>지급월</th><th>지급처</th><th class="num amt">금액</th><th>상태</th><th class="actions">작업</th></tr></thead><tbody>${rows.map(r => `<tr><td>${r["지급월"]}</td><td>${esc(r["지급처"])} <span class="muted">${esc(payeeName(r["지급처"]))}</span></td><td class="num amt">${fmt(r["금액"])}</td><td><span class="badge ${r["상태"]}">${r["상태"]}</span>${r["지급일"] ? ` <span class="muted">${esc(mmdd(r["지급일"]))}</span>` : ""}</td><td class="actions">${r["상태"] === "예정"
    ? `<button type="button" class="btn btn-sm" data-cell="edit" data-row="${r._row}">수정</button><button type="button" class="btn btn-sm" data-cell="confirm" data-row="${r._row}">확정</button>`
    : `<button type="button" class="btn btn-sm" data-cell="unconfirm" data-row="${r._row}">확정 취소</button>`}<button type="button" class="btn btn-sm btn-danger" data-cell="del" data-row="${r._row}">삭제</button></td></tr>`).join("") || '<tr><td class="empty" colspan="5">이 달 배분이 없습니다.</td></tr>'}</tbody>`;
}
$("#dlg-cell").addEventListener("click", async e => {
  const b = e.target.closest("button[data-cell]"); if (!b) return;
  const row = Number(b.dataset.row), act = b.dataset.cell;
  if (act === "close") { $("#dlg-cell").close(); return; }
  if (act === "add" || act === "edit") {
    $("#dlg-cell").close();
    DLG_ON_SAVED = () => openCellDialog(CELL.name, CELL.month);
    const onClose = () => { $("#dlg").removeEventListener("close", onClose); setTimeout(() => { if (!$("#dlg-cell").open && CELL.name) openCellDialog(CELL.name, CELL.month); }, 0); };
    $("#dlg").addEventListener("close", onClose);
    if (act === "add") openForm("labor", null, { 이름: CELL.name, 귀속월: CELL.month, 지급월: CELL.month }); else openForm("labor", row);
    return;
  }
  if (act === "confirm") return laborConfirm(row);
  if (act === "unconfirm") return laborUnconfirm(row);
  if (act === "del") { await del("labor", row); refreshCellDialog(); }
});
$("#dlg-cell").addEventListener("close", () => { if (!$("#dlg").open) CELL.name = null; });
document.addEventListener("click", e => {
  const td = e.target.closest("#labor-plan td.cell"); if (td) openCellDialog(td.dataset.name, td.dataset.month);
});

// ---------- 기간 일괄 생성 ----------
function openBulk() {
  const d = $("#dlg-bulk");
  setOptions($("#bulk-name"), ["", ...peopleNames()], ["(선택)", ...peopleNames()]);
  $("#bulk-name").value = ""; $("#bulk-from").value = curMonth(); $("#bulk-to").value = `${laborYear()}-12`; $("#bulk-memo").value = "";
  $("#bulk-rows").innerHTML = ""; addBulkRow(); updateBulkPreview();
  d.showModal(); $("#bulk-name").focus();
}
function addBulkRow(code = "", amt = "") {
  const opts = payeeOptions();
  const div = document.createElement("div"); div.className = "bulk-row";
  div.innerHTML = `<select aria-label="지급처"><option value="">(지급처)</option>${opts.map(o => `<option value="${esc(o)}"${o === code ? " selected" : ""}>${esc(o)} ${esc(payeeName(o))}</option>`).join("")}</select><input type="text" inputmode="numeric" class="num-input" placeholder="월 배분액" aria-label="월 배분액" value="${amt === "" ? "" : fmt(amt)}"><button type="button" class="btn btn-sm btn-danger" data-bulk="remove" aria-label="배분 행 삭제">삭제</button>`;
  $("#bulk-rows").appendChild(div);
}
function bulkRows() {
  return $$("#bulk-rows .bulk-row").map(div => ({ code: div.querySelector("select").value, amt: Number(div.querySelector("input").value.replace(/[,\s원]/g, "")) || 0 })).filter(x => x.code || x.amt);
}
function updateBulkPreview() {
  const from = $("#bulk-from").value, to = $("#bulk-to").value, name = $("#bulk-name").value;
  const n = (from && to && from <= to) ? ((+to.slice(0, 4) - +from.slice(0, 4)) * 12 + (+to.slice(5, 7) - +from.slice(5, 7)) + 1) : 0;
  const rows = bulkRows(), monthly = rows.reduce((a, r) => a + r.amt, 0), sal = name && from ? salaryFor(name, from) : null;
  const { dup } = bulkPlanRows();
  $("#bulk-preview").textContent = n && rows.length ? `${n}개월 × ${rows.length}개 지급처 = ${n * rows.length}건 · 월 합계 ${fmt(monthly)}원` + (sal != null ? ` (기준급여 ${fmt(sal)}원${monthly !== sal ? `, ${monthly < sal ? "부족" : "초과"} ${fmt(Math.abs(sal - monthly))}원` : ""})` : "")
    + (dup.length ? ` · 이미 있는 ${dup.length}건은 건너뜀 (${dup.slice(0, 3).map(d => `${d.귀속월} ${d.지급처}`).join(", ")}${dup.length > 3 ? " …" : ""})` : "") : "인원·기간·배분을 입력하세요.";
}
$("#dlg-bulk").addEventListener("input", updateBulkPreview);
$("#bulk-name").addEventListener("change", () => {  // 인원을 고르면 기간을 재직 기간(올해 안)으로 맞춤
  const p = DATA.people.find(x => x["이름"] === $("#bulk-name").value); if (!p) return;
  const y = laborYear(); let from = curMonth(), to = `${y}-12`;
  if (p["입사일"] && p["입사일"].slice(0, 7) > from) from = p["입사일"].slice(0, 7);
  if (p["퇴사일"] && p["퇴사일"].slice(0, 7) < to) to = p["퇴사일"].slice(0, 7);
  if (from.slice(0, 4) === y) $("#bulk-from").value = from;
  $("#bulk-to").value = to; updateBulkPreview();
});
function bulkPlanRows() {
  const name = $("#bulk-name").value, from = $("#bulk-from").value, to = $("#bulk-to").value, offset = Number($("#bulk-offset").value), memo = $("#bulk-memo").value.trim();
  const rows = bulkRows(); const out = [];
  if (!name || !from || !to || from > to) return { out, dup: [] };
  for (let m = from; m <= to && out.length < 1300; m = addMonth(m, 1)) rows.forEach(r => out.push({ 귀속월: m, 지급월: addMonth(m, offset), 이름: name, 지급처: r.code, 금액: r.amt, 비고: memo }));
  const dup = out.filter(o => DATA.labor.some(x => x["이름"] === o.이름 && x["귀속월"] === o.귀속월 && x["지급월"] === o.지급월 && x["지급처"] === o.지급처));
  return { out, dup };
}
$("#dlg-bulk").addEventListener("click", e => {
  const b = e.target.closest("button[data-bulk]"); if (!b) return;
  if (b.dataset.bulk === "add") addBulkRow();
  if (b.dataset.bulk === "remove") { b.closest(".bulk-row").remove(); updateBulkPreview(); }
  if (b.dataset.bulk === "cancel") $("#dlg-bulk").close();
});
$("#dlg-bulk-form").addEventListener("submit", async e => {
  e.preventDefault();
  const name = $("#bulk-name").value, from = $("#bulk-from").value, to = $("#bulk-to").value, offset = Number($("#bulk-offset").value), memo = $("#bulk-memo").value.trim();
  const rows = bulkRows();
  if (!name || !from || !to || from > to) return showAlert("인원과 올바른 기간을 입력하세요.", "warn");
  if (!rows.length || rows.some(r => !r.code || r.amt <= 0)) return showAlert("지급처와 양수 금액을 모두 입력하세요.", "warn");
  const { out, dup } = bulkPlanRows();
  if (out.length > 1200) return showAlert("한 번에 1,200건까지만 생성할 수 있습니다.", "warn");
  if (dup.length === out.length) return showAlert("모든 건이 이미 있어 추가할 것이 없습니다.", "warn");
  const btn = $("#bulk-save"); btn.disabled = true;
  try { const res = await api("POST", "/api/labor/bulk", { rows: out, skip_dup: true }); $("#dlg-bulk").close(); showAlert(`예정 ${res.created}건을 추가했습니다.` + (res.skipped.length ? ` 이미 있는 ${res.skipped.length}건은 건너뛰었습니다.` : ""), "ok"); await load(); }
  catch (err) { showAlert("생성 실패: " + err.message, "error"); }
  finally { btn.disabled = false; }
});

// ---------- 전월 계획 복사 ----------
async function copyPrevMonth() {
  const target = await confirmDlg({ title: "전월 계획 복사", body: "대상 월을 고르면 그 전달 귀속 예정·확정 건을 대상 월의 '예정'으로 복사합니다. 이미 있는 건은 건너뜁니다.", verb: "다음", input: { label: "대상 월", type: "month", value: curMonth() } });
  if (!target) return;
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(target)) return showAlert("월 형식은 YYYY-MM 입니다.", "warn");
  const src = addMonth(target, -1);
  const rows = DATA.labor.filter(r => r["귀속월"] === src).map(r => ({ 귀속월: target, 지급월: addMonth(r["지급월"], 1), 이름: r["이름"], 지급처: r["지급처"], 금액: r["금액"], 비고: r["비고"] || "" }));
  if (!rows.length) return showAlert(`${src} 귀속 지급 건이 없어 복사할 것이 없습니다.`, "warn");
  if (!await confirmDlg({ title: "전월 계획 복사", body: `${src} → ${target}: ${rows.length}건을 예정으로 복사합니다.`, verb: `${rows.length}건 복사` })) return;
  try { const res = await api("POST", "/api/labor/bulk", { rows, skip_dup: true }); showAlert(`${res.created}건 복사` + (res.skipped.length ? `, 이미 있는 ${res.skipped.length}건 건너뜀` : ""), "ok"); await load(); }
  catch (err) { showAlert("복사 실패: " + err.message, "error"); }
}
document.addEventListener("click", e => {
  const b = e.target.closest("button[data-labor]"); if (!b) return;
  if (b.dataset.labor === "bulk") openBulk();
  if (b.dataset.labor === "copy") copyPrevMonth();
  if (b.dataset.labor === "confirm") laborConfirm(Number(b.dataset.row));
  if (b.dataset.labor === "unconfirm") laborUnconfirm(Number(b.dataset.row));
});
