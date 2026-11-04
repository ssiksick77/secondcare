import ctypes, sys, time, pathlib
from ctypes import wintypes
path = sys.argv[1]; secs = float(sys.argv[2]); mode = sys.argv[3] if len(sys.argv) > 3 else "deny_write"
k = ctypes.WinDLL("kernel32", use_last_error=True)
k.CreateFileW.restype = wintypes.HANDLE
GENERIC_READ, GENERIC_WRITE = 0x80000000, 0x40000000
share = 0x1 if mode == "deny_write" else 0x0  # Excel: FILE_SHARE_READ only
h = k.CreateFileW(path, GENERIC_READ | GENERIC_WRITE, share, None, 3, 0x80, None)
if h == wintypes.HANDLE(-1).value: print("lock fail", ctypes.get_last_error()); sys.exit(1)
p = pathlib.Path(path); owner = p.with_name("~$" + p.name); owner.write_bytes(b"QA lock owner")
print("locked", flush=True); time.sleep(secs); k.CloseHandle(h); owner.unlink(); print("released", flush=True)
