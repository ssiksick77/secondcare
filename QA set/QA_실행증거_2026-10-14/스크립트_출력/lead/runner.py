"""QA runner: start the app on a given port with a given ledger, without opening a browser.
usage: python runner.py <ledger_path> <port>"""
import os, sys
os.environ["LEDGER_XLSX"] = sys.argv[1]
os.environ["LEDGER_PORT"] = sys.argv[2]
os.environ["LEDGER_DRIVE_MOCK"] = "1"
os.environ.pop("ANTHROPIC_API_KEY", None)
import uvicorn
import main, store
store.init_file()
print("ledger:", store.XLSX_PATH, "port:", sys.argv[2], flush=True)
uvicorn.run(main.app, host="127.0.0.1", port=int(sys.argv[2]), log_level="warning")
