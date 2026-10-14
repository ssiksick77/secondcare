@echo off
rem QA ledger runner: virtual ledger docs\qa_data_2026_01_09\qa_ledger.xlsx on port 8792.
rem Real ledger and app\.env are not used. Drive uploads go to app\drive_mock (LEDGER_DRIVE_MOCK=1).
cd /d "%~dp0"
python -c "import uvicorn, fastapi, openpyxl" >nul 2>&1
if errorlevel 1 (
  echo Required packages are missing. Run setup.bat first.
  pause
  exit /b 1
)
if not exist "..\docs\qa_data_2026_01_09\qa_ledger.xlsx" (
  echo QA ledger not found: ..\docs\qa_data_2026_01_09\qa_ledger.xlsx
  pause
  exit /b 1
)
set "LEDGER_XLSX=..\docs\qa_data_2026_01_09\qa_ledger.xlsx"
set "LEDGER_ENV=..\docs\qa_data_2026_01_09\qa.env"
set "LEDGER_DRIVE_MOCK=1"
set "LEDGER_PORT=8792"
echo [QA] ledger=%LEDGER_XLSX%  env=%LEDGER_ENV%  port=%LEDGER_PORT%  drive=mock
python main.py
pause
