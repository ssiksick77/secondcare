@echo off
rem 시작 프로그램에 SECONDCare 트레이 실행기 바로가기를 만든다 (현재 사용자만). 지우려면 uninstall_startup.bat
cd /d "%~dp0"
for /f "delims=" %%i in ('where pythonw') do if not defined PYW set "PYW=%%i"
if not defined PYW (
  echo pythonw 를 찾을 수 없습니다. Python 설치 때 "Add python.exe to PATH" 를 체크했는지 확인하세요.
  pause
  exit /b 1
)
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SECONDCare.lnk"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%LNK%'); $s.TargetPath='%PYW%'; $s.Arguments='tray.pyw'; $s.WorkingDirectory='%~dp0'; $s.Description='SECONDCare 트레이 실행기'; $s.Save()"
if errorlevel 1 (
  echo 바로가기를 만들지 못했습니다.
  pause
  exit /b 1
)
echo 등록 완료: %LNK%
echo 다음 로그인부터 트레이에서 자동으로 시작합니다. 지금 시작하려면 run_tray.bat 을 실행하세요.
pause
