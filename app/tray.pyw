"""SECONDCare 트레이 실행기 (2026-11-03). pythonw 로 돌아 콘솔 창이 없다.
서버는 이 프로세스 안의 스레드에서 돌고, 작업 표시줄 트레이 아이콘의 메뉴로 열기·종료한다.
콘솔이 없으므로 출력은 app/tray.log 에 쓴다. 실행: run_tray.bat (또는 시작 프로그램 바로가기, install_startup.bat)."""
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
sys.path.insert(0, str(HERE))
LOG = HERE / "tray.log"
sys.stdout = sys.stderr = open(LOG, "a", encoding="utf-8", buffering=1)  # pythonw 는 표준 출력이 없다

import pystray  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import settings  # noqa: E402

NAME = settings.APP_NAME


def icon_image():
    img = Image.new("RGB", (64, 64), "#1d4ed8")
    d = ImageDraw.Draw(img)
    d.rectangle((14, 18, 50, 46), fill="white")
    d.rectangle((20, 26, 44, 30), fill="#1d4ed8")
    d.rectangle((20, 34, 36, 38), fill="#1d4ed8")
    return img


def main():
    import main as web  # 서버 앱 (장부 경로·포트는 .env)
    import store
    url = f"http://{web.HOST}:{web.PORT}"
    with socket.socket() as s:
        if s.connect_ex((web.HOST, web.PORT)) == 0:
            print(f"이미 실행 중: {url}")
            webbrowser.open(url)
            return
    if not store.DATA_PATH.exists():
        print(f"[오류] 장부 파일을 찾을 수 없습니다: {store.DATA_PATH}")
        pystray.Icon(NAME, icon_image(), NAME).notify(f"장부 파일을 찾을 수 없습니다:\n{store.DATA_PATH}", NAME)
        return
    try:
        store.init_file()
    except Exception as e:  # 잠금 등. main.py 와 같이 첫 저장 때 다시 시도
        print(f"[경고] {e}")

    import uvicorn
    server = uvicorn.Server(uvicorn.Config(web.app, host=web.HOST, port=web.PORT, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()

    def quit_(icon, _item):
        server.should_exit = True
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(f"{NAME} 열기", lambda *_: webbrowser.open(url), default=True),
        pystray.MenuItem("로그 보기", lambda *_: os.startfile(LOG)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("종료", quit_),
    )
    print(f"시작: {url} (장부 {store.DATA_PATH})")
    pystray.Icon(NAME, icon_image(), f"{NAME} · {url}", menu).run()
    print("종료")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
