from ui import *
import subprocess, time
lk = subprocess.Popen([sys.executable, "locker.py", str(LEDGER), "25", "deny_write"], stdout=subprocess.PIPE, text=True)
print(lk.stdout.readline().strip()); t0 = time.time()
n0 = None
r = requests.get(B + "/api/all"); print("GET /api/all while locked:", r.status_code, "meta.locked:", r.json()["meta"]["locked"] if r.status_code == 200 else r.text[:200])
if r.status_code == 200: n0 = len(r.json()["exec"])
r = post("/api/exec", dict(EXEC_OK, 적요="C12 API 잠금중")); print("API POST while locked:", show(r))
with sync_playwright() as p:
    b, c, pg = open_page(p); tab_exec(pg)
    print("header status:", pg.locator("#file-status").inner_text())
    open_add(pg); F(pg, "재원").select_option("QA10"); F(pg, "예산목").select_option("연구활동비"); F(pg, "거래처").fill("C12거래처"); F(pg, "금액").fill("12,345"); F(pg, "적요").fill("C12 잠금중 UI 저장")
    pg.click("#dlg-save"); pg.wait_for_timeout(1500); confirm_ok(pg)
    print("form err:", err(pg)); print("toasts:", toasts(pg)); print("dialog open:", pg.locator("#dlg[open]").count(), "values kept:", [F(pg, k).input_value() for k in ["재원", "거래처", "금액", "적요"]])
    shot(pg, "C-12_locked_save")
    while lk.poll() is None: time.sleep(0.5)
    print("lock released after %.1fs" % (time.time() - t0))
    pg.click("#dlg-save"); pg.wait_for_timeout(1500); confirm_ok(pg)
    print("retry: dialog open:", pg.locator("#dlg[open]").count(), "toasts:", toasts(pg)); shot(pg, "C-12_after_release")
    b.close()
rows = [r for r in all_()["exec"] if r["적요"].startswith("C12")]; print("C12 rows:", [(r["거래번호"], r["금액"], r["적요"]) for r in rows], "total exec", len(all_()["exec"]), "before", n0)
