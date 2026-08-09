@echo off
chcp 65001 >nul
title Saenghwal-info Console - Stop Server
echo Stopping local server on port 8000 ...

set "FOUND="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
  taskkill /F /PID %%P >nul 2>nul
  set "FOUND=1"
)

if defined FOUND (
  echo [OK] Server stopped.
) else (
  echo [Info] No server was running on port 8000.
)
timeout /t 3 >nul
exit /b
