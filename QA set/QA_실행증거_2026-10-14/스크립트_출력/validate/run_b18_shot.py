import sys, json, requests, time
sys.path.insert(0, "<home>/AppData/Local/Temp/claude/<session>/18367f8b-184a-424d-99ad-8ce7d7ee1121/scratchpad/qa/work")
from harness_common import *
from playwright.sync_api import sync_playwright
import pathlib
F = QA/"work"/"files"
print("reset:", reset())
with open(F/"qa_receipt_1x1.png","rb") as fh:
    r = requests.post(f"{BASE}/api/evidence/2026-QA01-001", files=[("files", ("qa_receipt_1x1.png", fh, "image/png"))], data={"kind":"영수증","note":"QA validate B-18 upload"})
print("upload", r.status_code)
r = requests.post(f"{BASE}/api/evidence/2026-QA01-002/entry", json={"증빙종류":"영수증","비고":"QA B-18 실물만"}); print("entry", r.status_code, r.json().get("_row"))
row = r.json()["_row"]
with open(F/"qa_receipt.pdf","rb") as fh:
    r = requests.post(f"{BASE}/api/evidence/2026-QA01-002", files=[("files", ("qa_receipt.pdf", fh, "application/pdf"))], data={"kind":"영수증","row":str(row)})
print("attach", r.status_code)
shots = QA/"shots"
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width":1400,"height":900})
    pg.goto(BASE + "/")
    pg.click("#tab-exec")
    pg.wait_for_selector("#exec-table tbody tr[data-row]", state="attached", timeout=20000)
    time.sleep(1)
    # locate exec rows by 거래번호 text in table
    for num, name in [("2026-QA01-001","B18_QA01-001"),("2026-QA01-002","B18_QA01-002")]:
        loc = pg.locator("#exec-table tbody tr[data-row]", has=pg.get_by_text(num, exact=True)).first
        loc.click()
        time.sleep(1.2)
        sec = pg.locator("section.xd-sec", has=pg.locator("h3", has_text="증빙")).first
        sec.scroll_into_view_if_needed()
        sec.screenshot(path=str(shots/f"validate_{name}_evidence.png"))
        pg.screenshot(path=str(shots/f"validate_{name}_page.png"))
        print("shot", name, sec.inner_text()[:300].replace("\n"," | "))
        pg.keyboard.press("Escape"); time.sleep(0.5)
    b.close()
