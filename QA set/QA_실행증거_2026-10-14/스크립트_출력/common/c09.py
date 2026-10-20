from ui import *
import time, json
def totals():
    d = all_(); qa4 = [r for r in d["exec"] if r["재원"] == "QA04"]
    return len(d["exec"]), sum(r["금액"] for r in d["exec"]), len(qa4), sum(r["금액"] for r in qa4)
def ui_delete(pg, no):
    pg.click("#btn-del-mode"); pg.wait_for_timeout(200)
    find_row(pg, no).locator("input[data-selrow]").check(); pg.click("#exec-del-run"); pg.wait_for_timeout(400); confirm_ok(pg); pg.wait_for_timeout(800)
X1, X2 = "2026-QA04-003", "2026-QA04-004"
with sync_playwright() as p:
    b, c, pg = open_page(p); tab_exec(pg)
    t0 = totals(); r0 = exec_by_no(X1)[0]; print("before:", t0)
    ui_delete(pg, X1); t_del = time.time()
    print("after delete:", totals(), "exists:", len(exec_by_no(X1)), "toasts:", toasts(pg))
    undo = pg.locator("#toasts .toast-undo"); print("undo buttons:", undo.count()); shot(pg, "C-09_delete_toast")
    undo.first.click(); pg.wait_for_timeout(1200)
    t1 = totals(); r1 = exec_by_no(X1)
    print("after undo:", t1, "toasts:", toasts(pg), "restored identical:", bool(r1) and {k: v for k, v in r1[0].items()} == r0)
    shot(pg, "C-09_after_undo")
    # toast lifetime
    pg.fill('[data-filter="q"][data-kind="exec"]', ""); ui_delete(pg, X1); ts = time.time()
    while pg.locator("#toasts .toast-undo").count() and time.time() - ts < 30: pg.wait_for_timeout(250)
    print("undo toast lifetime ~%.1fs" % (time.time() - ts))
    # undo via API (toast expired) to restore X1
    wid = requests.get(B + "/api/meta").json()["write_id"]; print("API undo after toast expiry:", show(post("/api/undo", {"write_id": wid})), "exists:", len(exec_by_no(X1)))
    # second case: delete -> other window save -> undo
    pg.reload(); pg.wait_for_load_state("networkidle"); tab_exec(pg)
    t2 = totals(); ui_delete(pg, X2); print("deleted X2:", len(exec_by_no(X2)) == 0)
    other = exec_by_no("2026-QA04-005")[0]
    r = put(f"/api/exec/{other['_row']}", {"rec": dict({k: v for k, v in other.items() if not k.startswith('_')}, 적요="C09 다른창 저장"), "expect": expect(other)}); print("other window save:", r.status_code)
    pg.locator("#toasts .toast-undo").first.click(); pg.wait_for_timeout(1200)
    print("undo toasts:", toasts(pg)); shot(pg, "C-09_undo_rejected")
    print("X2 exists:", len(exec_by_no(X2)), "| other save kept:", exec_by_no("2026-QA04-005")[0]["적요"])
    b.close()
# API-level: stale write_id
x3 = exec_by_no("2026-QA04-006")[0]
r = delete(f"/api/exec/{x3['_row']}", {"expect": expect(x3)}); w1 = r.headers.get("X-Write-Id"); print("API delete:", show(r))
x7 = exec_by_no("2026-QA04-007")[0]; r = put(f"/api/exec/{x7['_row']}", {"rec": dict({k: v for k, v in x7.items() if not k.startswith('_')}, 적요="C09 API 다른저장"), "expect": expect(x7)}); print("other save wid", r.headers.get("X-Write-Id"))
print("undo old wid:", show(post("/api/undo", {"write_id": w1})), "| X3 exists:", len(exec_by_no("2026-QA04-006")))
print("undo without write_id (body empty):", show(post("/api/undo", {})), "| 007 적요:", exec_by_no("2026-QA04-007")[0]["적요"])
