@echo off
REM ============================================================
REM  lifeinfo diagnostics collector
REM  ASCII only (project rule for .bat files)
REM
REM  Run this from C:\lifeinfo if the PC still boots.
REM  It writes diag_report.txt - paste that back to Claude.
REM  READ ONLY: it changes nothing, deletes nothing.
REM ============================================================
setlocal enabledelayedexpansion

set OUT=%~dp0diag_report.txt
set ROOT=C:\lifeinfo

echo Collecting diagnostics... this takes a few seconds.
echo.

> "%OUT%" echo === lifeinfo diagnostic report ===
>> "%OUT%" echo generated: %DATE% %TIME%
>> "%OUT%" echo.

>> "%OUT%" echo --- [1] project root ---
if exist "%ROOT%" (
  >> "%OUT%" echo %ROOT% EXISTS
  >> "%OUT%" dir "%ROOT%"
) else (
  >> "%OUT%" echo %ROOT% MISSING - folder is gone or drive not mounted
)
>> "%OUT%" echo.

>> "%OUT%" echo --- [2] key subfolders ---
for %%D in (studio posts webapp thumbs thumbs_naver logo references) do (
  if exist "%ROOT%\%%D" (
    for /f %%C in ('dir /b "%ROOT%\%%D" 2^>nul ^| find /c /v ""') do >> "%OUT%" echo   %%D : EXISTS  %%C items
  ) else (
    >> "%OUT%" echo   %%D : MISSING
  )
)
>> "%OUT%" echo.

>> "%OUT%" echo --- [3] key files ---
for %%F in (lifeinfo_db.txt deploy.bat CLAUDE.md progress.json health.json queue.json pending.json) do (
  if exist "%ROOT%\%%F" (
    >> "%OUT%" echo   %%F : EXISTS
  ) else (
    >> "%OUT%" echo   %%F : MISSING
  )
)
>> "%OUT%" echo.

>> "%OUT%" echo --- [4] studio modules ---
for %%M in (pipeline.py board_seed.py pubqueue.py dupcheck.py blogger.py selfcheck.py validate_db.py __init__.py) do (
  if exist "%ROOT%\studio\%%M" (
    >> "%OUT%" echo   studio\%%M : EXISTS
  ) else (
    >> "%OUT%" echo   studio\%%M : MISSING
  )
)
>> "%OUT%" echo.

>> "%OUT%" echo --- [5] python ---
>> "%OUT%" echo where python:
>> "%OUT%" 2>&1 where python
>> "%OUT%" echo version:
>> "%OUT%" 2>&1 python --version
>> "%OUT%" echo import check (PIL, requests, google auth):
>> "%OUT%" 2>&1 python -c "import PIL; print('PIL', PIL.__version__)"
>> "%OUT%" 2>&1 python -c "import requests; print('requests', requests.__version__)"
>> "%OUT%" 2>&1 python -c "import google.auth; print('google-auth OK')"
>> "%OUT%" echo.

>> "%OUT%" echo --- [6] studio import + smoke ---
if exist "%ROOT%\studio" (
  pushd "%ROOT%"
  >> "%OUT%" 2>&1 python -c "import studio; print('studio package imports OK')"
  >> "%OUT%" 2>&1 python -m studio.selfcheck --help
  popd
) else (
  >> "%OUT%" echo skipped - studio missing
)
>> "%OUT%" echo.

>> "%OUT%" echo --- [7] git state ---
if exist "%ROOT%\.git" (
  pushd "%ROOT%"
  >> "%OUT%" 2>&1 git status --short
  >> "%OUT%" echo branch:
  >> "%OUT%" 2>&1 git rev-parse --abbrev-ref HEAD
  >> "%OUT%" echo last 5 commits:
  >> "%OUT%" 2>&1 git log --oneline -5
  >> "%OUT%" echo unpushed:
  >> "%OUT%" 2>&1 git log --oneline @{u}..HEAD
  >> "%OUT%" echo remotes:
  >> "%OUT%" 2>&1 git remote -v
  popd
) else (
  >> "%OUT%" echo no .git in %ROOT%
)
>> "%OUT%" echo.

>> "%OUT%" echo --- [8] webapp git state ---
if exist "%ROOT%\webapp\.git" (
  pushd "%ROOT%\webapp"
  >> "%OUT%" 2>&1 git status --short
  >> "%OUT%" 2>&1 git log --oneline -5
  >> "%OUT%" 2>&1 git log --oneline @{u}..HEAD
  popd
) else (
  >> "%OUT%" echo no .git in %ROOT%\webapp
)
>> "%OUT%" echo.

>> "%OUT%" echo --- [9] disk space ---
>> "%OUT%" 2>&1 wmic logicaldisk get caption,freespace,size
>> "%OUT%" echo.

>> "%OUT%" echo --- [10] disk health (SMART) ---
>> "%OUT%" 2>&1 wmic diskdrive get model,status,size
>> "%OUT%" echo.

>> "%OUT%" echo --- [11] network reachability ---
>> "%OUT%" 2>&1 ping -n 2 github.com
>> "%OUT%" 2>&1 ping -n 2 lifeinfo8975.blogspot.com
>> "%OUT%" echo.

>> "%OUT%" echo --- [12] recent system errors (24h) ---
>> "%OUT%" 2>&1 powershell -NoProfile -Command "Get-EventLog -LogName System -EntryType Error -After (Get-Date).AddDays(-1) -ErrorAction SilentlyContinue | Select-Object -First 15 TimeGenerated,Source,Message | Format-List"
>> "%OUT%" echo.

>> "%OUT%" echo === end of report ===

echo Done. Report written to:
echo   %OUT%
echo.
echo Open it, check there is nothing private in it, then paste it to Claude.
echo.
notepad "%OUT%"

endlocal
