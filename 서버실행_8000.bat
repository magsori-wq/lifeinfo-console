@echo off
title Local Server - Port 8000
cd /d "%~dp0"
echo ============================================
echo  Saenghwal-info Console - Local Server
echo  Port 8000  =^>  http://localhost:8000
echo  Close this window to stop the server.
echo ============================================
echo.
start "" "http://localhost:8000/index.html"
where python >nul 2>nul && (python -m http.server 8000 & goto :eof)
where py >nul 2>nul && (py -m http.server 8000 & goto :eof)
echo.
echo [Error] Python not found.
echo Install from https://www.python.org and check "Add Python to PATH".
pause
