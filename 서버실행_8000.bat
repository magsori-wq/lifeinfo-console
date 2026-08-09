@echo off
chcp 65001 >nul
title Saenghwal-info Console - Launcher
cd /d "%~dp0"

rem --- If already running, just open the browser ---
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if %errorlevel%==0 (
  echo [Info] Server is already running on port 8000.
  start http://localhost:8000/index.html
  timeout /t 2 >nul
  exit /b
)

rem --- Launch python.exe HIDDEN (window hidden, but stdio valid so http.server works) ---
rem     Runs detached: closing any window does NOT stop the server.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process python -ArgumentList '-m','http.server','8000' -WorkingDirectory '%~dp0' -WindowStyle Hidden"

rem --- Wait, then open the browser ---
timeout /t 2 >nul
start http://localhost:8000/index.html

echo ============================================
echo  Server is now running in the BACKGROUND (no window).
echo  Port 8000  =^>  http://localhost:8000
echo.
echo  You can CLOSE this window - the server keeps running.
echo  To STOP the server, double-click:  서버중지_8000.bat
echo ============================================
timeout /t 4 >nul
exit /b
