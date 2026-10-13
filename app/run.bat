@echo off
cd /d "%~dp0"
python -c "import uvicorn, fastapi, openpyxl" >nul 2>&1
if errorlevel 1 (
  echo 필요한 패키지가 설치되어 있지 않습니다. 먼저 setup.bat 을 실행하세요.
  pause
  exit /b 1
)
python main.py
pause
