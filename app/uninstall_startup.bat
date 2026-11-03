@echo off
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SECONDCare.lnk"
if exist "%LNK%" (del "%LNK%" && echo 시작 프로그램에서 뺐습니다.) else echo 등록되어 있지 않습니다.
pause
