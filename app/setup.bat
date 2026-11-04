@echo off
cd /d "%~dp0"
echo [1/3] Python 확인...
python --version >nul 2>&1
if errorlevel 1 (
  echo   Python 이 없습니다. https://www.python.org/downloads/ 에서 3.10 이상을 설치하고
  echo   설치 화면에서 "Add python.exe to PATH" 를 반드시 체크하세요.
  pause
  exit /b 1
)
python --version
echo [2/3] 패키지 설치 - 인터넷 필요, 1~3분...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo   설치에 실패했습니다. 병원망 프록시 때문이면 아래처럼 시도하세요:
  echo   python -m pip install --proxy http://프록시주소:포트 -r requirements.txt
  pause
  exit /b 1
)
echo [3/3] 완료. run.bat 을 실행하세요.
pause
