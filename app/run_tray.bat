@echo off
cd /d "%~dp0"
pythonw -c "import pystray, PIL, uvicorn, fastapi, openpyxl" 2>nul
if errorlevel 1 (
  echo 필요한 패키지가 설치되어 있지 않습니다. 먼저 setup.bat 을 실행하세요.
  pause
  exit /b 1
)
start "" pythonw tray.pyw
