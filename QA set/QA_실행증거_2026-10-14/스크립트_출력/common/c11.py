from ui import *
def vis(pg, sel):
    loc = pg.locator(sel); return any(loc.nth(i).is_visible() for i in range(loc.count()))
def survey(pg, label):
    pg.wait_for_timeout(800)
    hdr = {s: vis(pg, s) for s in ["#btn-mode", "#btn-settings", "#btn-ai", "#btn-request", "#btn-reload"]}
    btns = [t.strip() for t in pg.locator("button:visible").all_inner_texts() if t.strip()]
    selbar = vis(pg, "#req-selbar"); checks = pg.locator("#request-table input[type=checkbox]:visible").count()
    print(f"[{label}] url={pg.url} body.class={pg.evaluate('document.body.className')}")
    print("  header visible:", hdr); print("  selbar visible:", selbar, "checkbox count:", checks)
    print("  key buttons present:", {k: any(k == b or b.startswith(k) for b in btns) for k in ["승인", "반려", "품의 전환", "주문 생성", "삭제", "신청 추가", "회계대장으로"]})
    print("  tab-bar text:", pg.locator("#request-tabs").inner_text().replace("\n", " ")[:200] if pg.locator("#request-tabs").count() else "")
    return btns
with sync_playwright() as p:
    br = p.chromium.launch()
    # researcher: fresh context, direct /request
    c1 = br.new_context(viewport={"width": 1500, "height": 950}); r = c1.new_page(); r.goto(B + "/request"); r.wait_for_load_state("networkidle")
    survey(r, "직접 /request"); shot(r, "C-11_researcher_direct")
    # click a 신청 row to open detail; look for approve buttons in drawer
    first = r.locator("#request-table tbody tr").first; first.click(); r.wait_for_timeout(600)
    print("  researcher drawer buttons:", [t for t in r.locator("#req-drawer button:visible").all_inner_texts() if t.strip()][:20])
    shot(r, "C-11_researcher_drawer")
    # admin: fresh context, / then click 신청
    c2 = br.new_context(viewport={"width": 1500, "height": 950}); a = c2.new_page(); a.goto(B + "/"); a.wait_for_load_state("networkidle")
    a.click("#btn-request"); a.wait_for_load_state("networkidle")
    survey(a, "회계장부 → 신청 버튼"); shot(a, "C-11_admin_from_ledger")
    a.locator("#request-table tbody tr").first.click(); a.wait_for_timeout(600)
    print("  admin drawer buttons:", [t for t in a.locator("#req-drawer button:visible").all_inner_texts() if t.strip()][:20])
    # admin: reload in same tab keeps admin? new tab in same context?
    a.reload(); a.wait_for_load_state("networkidle"); print("  admin after reload body.class:", a.evaluate("document.body.className"))
    a2 = c2.new_page(); a2.goto(B + "/request"); a2.wait_for_load_state("networkidle"); print("  same browser, new tab /request body.class:", a2.evaluate("document.body.className"))
    # researcher can become admin by setting sessionStorage (UI-only distinction)
    r.evaluate("sessionStorage.setItem('request-admin','1')"); r.reload(); r.wait_for_load_state("networkidle"); print("  researcher after sessionStorage flag body.class:", r.evaluate("document.body.className"))
    br.close()
# API: no auth - approve via API directly (README 명시)
d = all_(); target = [x for x in d["request"] if x["상태"] == "신청"][0]
r = post(f"/api/request/{target['_row']}/action", {"action": "approve", "extra": {"결재인": "인증없는호출"}, "expect": {"신청번호": target["신청번호"]}})
print("API approve without auth:", target["신청번호"], show(r))
