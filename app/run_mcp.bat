@echo off
REM 이 파일은 직접 실행하는 용도가 아닙니다.
REM Claude Desktop / Claude Code 가 MCP 서버로 띄울 때 쓰는 진입점입니다 (README "MCP 서버" 참고).
REM 더블클릭하면 입력을 기다리는 빈 창만 보입니다. 창을 닫아도 됩니다.
cd /d "%~dp0"
python mcp_server.py
