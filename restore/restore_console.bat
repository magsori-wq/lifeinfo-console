@echo off
REM ============================================================
REM  lifeinfo console restore - pull the GitHub copy to your PC
REM  ASCII only (project rule for .bat files)
REM
REM  SAFE BY DESIGN: this clones into a NEW folder and never
REM  overwrites an existing C:\lifeinfo. You copy what you need.
REM ============================================================
setlocal

set REPO=https://github.com/magsori-wq/lifeinfo-console.git
set DEST=C:\lifeinfo_restore

echo.
echo === lifeinfo console restore =========================
echo   source : %REPO%
echo   dest   : %DEST%
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo [STOP] git is not installed or not on PATH.
  echo        Install Git for Windows first: https://git-scm.com/download/win
  goto :end
)

if exist "%DEST%" (
  echo [STOP] %DEST% already exists.
  echo        Rename or delete it first so nothing gets overwritten.
  goto :end
)

echo [1/3] cloning...
git clone "%REPO%" "%DEST%"
if errorlevel 1 (
  echo [STOP] clone failed. Check network / GitHub login.
  goto :end
)

echo.
echo [2/3] what you just recovered:
echo.
dir /b "%DEST%\*.html"
echo.
for /f %%C in ('dir /b "%DEST%\thumbs" 2^>nul ^| find /c /v ""') do echo   thumbs : %%C files
for /f %%C in ('dir /b "%DEST%\logo" 2^>nul ^| find /c /v ""') do echo   logo   : %%C files
if exist "%DEST%\lifeinfo_db.txt" echo   lifeinfo_db.txt : OK  (post database, 153 entries)

echo.
echo [3/3] NOT in GitHub - these are still missing:
echo   studio\        Python package (pipeline, board_seed, pubqueue, dupcheck, blogger, selfcheck)
echo   posts\         .lsg source files   -^> recover with restore\recover_posts_from_blogger.py
echo   thumbs_naver\  light thumbnail variants (regenerate with PIL)
echo   deploy.bat     deploy script
echo   CLAUDE.md      harness rules
echo   Blogger API credentials  -^> must be re-issued, never recoverable
echo.
echo Next: read restore\DISPLAY_RECOVERY.md for the full order of operations.
echo.

:end
endlocal
pause
