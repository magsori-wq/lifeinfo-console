@echo off
REM ==============================================================
REM  Back up studio/ to a PRIVATE repository - credential-safe by design
REM  ASCII only (project rule for .bat files)
REM
REM  SUPERSEDED - 2026-07-27. You probably do not need this.
REM    It was written on a wrong premise: that studio/ existed on one machine
REM    only. In fact the private repo magsori-wq/lifeinfo-source already holds
REM    studio/, posts/, thumbs_naver/ and CLAUDE.md, with credentials already
REM    excluded by its .gitignore. C:\lifeinfo is a clone of THAT repo.
REM
REM    The real gap was staleness, not absence - that backup lagged by four
REM    days. The fix is a habit, not a script:
REM        cd C:\lifeinfo && git add -A && git commit && git push
REM
REM    Kept only for a one-off export to a brand-new repository. For a
REM    pre-commit credential check, use scan_secrets.py directly:
REM        python scan_secrets.py C:\lifeinfo
REM
REM  WHY IT DOES NOT TOUCH C:\lifeinfo
REM    C:\lifeinfo already participates in the lifeinfo-console git setup that
REM    deploy.bat drives. Running `git init` there could nest or confuse
REM    repositories. So this copies to a SEPARATE staging folder and pushes
REM    from there. C:\lifeinfo is only ever read.
REM
REM  SAFETY: credentials are blocked twice
REM    1) excluded at copy time, so they never reach the staging folder
REM    2) a filename AND file-content scan runs before the first commit,
REM       and the script refuses to continue if anything looks like a secret
REM
REM  USAGE
REM    backup_studio.bat https://github.com/magsori-wq/lifeinfo-studio.git
REM ==============================================================
setlocal enabledelayedexpansion

set SRC=C:\lifeinfo
set DST=C:\lifeinfo_studio_backup
set REPO=%~1

if "%REPO%"=="" (
  echo [STOP] Pass the private repository URL.
  echo    backup_studio.bat https://github.com/magsori-wq/lifeinfo-studio.git
  goto :end
)
if not exist "%SRC%" (
  echo [STOP] %SRC% not found.
  goto :end
)
if exist "%DST%" (
  echo [STOP] %DST% already exists. Rename or delete it first.
  goto :end
)
where git >nul 2>&1
if errorlevel 1 (
  echo [STOP] git is not on PATH.
  goto :end
)

echo.
echo === studio backup ===============================
echo   source : %SRC%   (read only)
echo   staging: %DST%
echo   repo   : %REPO%
echo.

mkdir "%DST%" 2>nul

REM ---- 1) copy, excluding anything credential-shaped -----------
REM /XF excludes files by pattern, /XD excludes directories.
REM Wildcards on BOTH sides. An earlier version used token*.json, which does
REM NOT match studio\.secrets\blogger_token.json - real tokens got staged and
REM were only caught by the human reading the file list. Directory exclusions
REM matter just as much: .secrets\ is where they actually live.
set XF=/XF *token*.json *token*.pickle *secret*.json *credential*.json *oauth*.json *service_account*.json *apikey*.json *.pem *.key *.p12 *.pfx .env
set XD=/XD __pycache__ .venv venv .git node_modules .secrets secrets .credentials .keys

echo [1/5] copying studio\ ...
if exist "%SRC%\studio" robocopy "%SRC%\studio" "%DST%\studio" /E /R:1 /W:1 /NFL /NDL /NJH /NJS %XF% %XD% >nul
echo [1/5] copying posts\ ...
if exist "%SRC%\posts" robocopy "%SRC%\posts" "%DST%\posts" /E /R:1 /W:1 /NFL /NDL /NJH /NJS %XF% %XD% >nul
echo [1/5] copying references\ ...
if exist "%SRC%\references" robocopy "%SRC%\references" "%DST%\references" /E /R:1 /W:1 /NFL /NDL /NJH /NJS %XF% %XD% >nul
echo [1/5] copying thumbs_naver\ ...
if exist "%SRC%\thumbs_naver" robocopy "%SRC%\thumbs_naver" "%DST%\thumbs_naver" /E /R:1 /W:1 /NFL /NDL /NJH /NJS %XF% %XD% >nul
for %%F in (CLAUDE.md deploy.bat requirements.txt) do (
  if exist "%SRC%\%%F" copy /Y "%SRC%\%%F" "%DST%\%%F" >nul
)

REM ---- 2) .gitignore ------------------------------------------
echo [2/5] writing .gitignore ...
> "%DST%\.gitignore" echo # Blogger / Google API credentials - never commit
>> "%DST%\.gitignore" echo # Patterns are wildcarded on both sides: the real files are named
>> "%DST%\.gitignore" echo # blogger_token.json / adsense_token.json, which token*.json misses.
>> "%DST%\.gitignore" echo .secrets/
>> "%DST%\.gitignore" echo secrets/
>> "%DST%\.gitignore" echo .credentials/
>> "%DST%\.gitignore" echo *token*.json
>> "%DST%\.gitignore" echo *token*.pickle
>> "%DST%\.gitignore" echo *secret*.json
>> "%DST%\.gitignore" echo *credential*.json
>> "%DST%\.gitignore" echo *oauth*.json
>> "%DST%\.gitignore" echo *service_account*.json
>> "%DST%\.gitignore" echo .env
>> "%DST%\.gitignore" echo .env.*
>> "%DST%\.gitignore" echo.
>> "%DST%\.gitignore" echo # keys and certificates
>> "%DST%\.gitignore" echo *.pem
>> "%DST%\.gitignore" echo *.key
>> "%DST%\.gitignore" echo *.p12
>> "%DST%\.gitignore" echo *.pfx
>> "%DST%\.gitignore" echo.
>> "%DST%\.gitignore" echo # python
>> "%DST%\.gitignore" echo __pycache__/
>> "%DST%\.gitignore" echo *.py[cod]
>> "%DST%\.gitignore" echo .venv/
>> "%DST%\.gitignore" echo venv/
>> "%DST%\.gitignore" echo.
>> "%DST%\.gitignore" echo # scratch
>> "%DST%\.gitignore" echo scratch_*
>> "%DST%\.gitignore" echo *.log

REM ---- 3) credential scan (filenames + contents) ---------------
REM The scan lives in scan_secrets.py, not inline here. An inline PowerShell
REM version broke on batch caret/quote escaping, printed parser errors, and then
REM still reported "clean - no credential patterns found" - a scan that never
REM ran reporting success is the worst possible failure. A separate Python file
REM has no escaping problem and can be tested directly.
REM
REM FAIL-CLOSED: any outcome other than a clean exit 0 stops the run. Missing
REM Python, missing scanner, a crash - all abort. Never proceed on "unknown".
echo [3/5] scanning for credentials ...

if not exist "%~dp0scan_secrets.py" (
  echo    fetching scan_secrets.py ...
  powershell -NoProfile -Command "try{Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/magsori-wq/lifeinfo-console/main/restore/scan_secrets.py' -OutFile '%~dp0scan_secrets.py'}catch{exit 1}"
)
if not exist "%~dp0scan_secrets.py" (
  echo [STOP] scan_secrets.py is missing and could not be downloaded.
  echo        Nothing was committed. Put it next to this .bat and retry.
  goto :end
)

where python >nul 2>&1
if errorlevel 1 (
  echo [STOP] python is not on PATH, so the credential scan cannot run.
  echo        Refusing to continue - a backup without the scan risks
  echo        committing tokens. Nothing was committed.
  goto :end
)

python "%~dp0scan_secrets.py" "%DST%"
set RC=%ERRORLEVEL%

if "%RC%"=="1" (
  echo.
  echo ==========================================================
  echo  STOPPED - credentials found. Nothing was committed.
  echo.
  echo  Delete the offending files from %DST%
  echo  ^(the originals in C:\lifeinfo are untouched^), then run
  echo     python "%~dp0scan_secrets.py" "%DST%"
  echo  again until it reports clean, and re-run this script.
  echo ==========================================================
  goto :end
)
if not "%RC%"=="0" (
  echo.
  echo [STOP] the scan itself failed ^(exit %RC%^). Refusing to continue -
  echo        an unverified folder is treated as unsafe. Nothing was committed.
  goto :end
)

REM ---- 4) what is about to be committed ------------------------
REM Nothing is STAGED before the confirmation. An earlier version ran
REM `git add -A` here, so aborting at the prompt left a .git whose index still
REM held the files - including, on the first real run, four OAuth tokens. They
REM were never committed, but `git ls-files` still listed them, and any later
REM commit from that folder would have picked them up. A dry run previews the
REM same list without touching the index.
echo [4/5] contents to be committed:
pushd "%DST%"
git init -q
echo.
git -c core.quotepath=off add -A --dry-run
echo.
for /f %%C in ('git add -A --dry-run ^| find /c /v ""') do echo    total %%C files
echo.
echo Review the list above. Nothing is staged and nothing has been pushed yet.
set /p OK=Type YES to commit and push:
if /i not "%OK%"=="YES" (
  echo.
  echo Aborted - nothing was staged, committed or pushed.
  echo Delete the staging folder before retrying:
  echo    rmdir /s /q "%DST%"
  popd
  goto :end
)

REM ---- 5) stage, commit and push -------------------------------
REM Staging happens HERE, only after the confirmation - step 4 previewed with
REM a dry run and left the index untouched on purpose.
echo [5/5] staging, committing and pushing ...
git add -A
if errorlevel 1 (
  echo [STOP] git add failed. Nothing was committed.
  popd
  goto :end
)
git -c user.useConfigOnly=false commit -q -m "initial backup of studio pipeline, posts and harness rules"
if errorlevel 1 (
  echo [STOP] commit failed - nothing to commit, or git identity is unset.
  echo        Set it with: git config --global user.email you@example.com
  popd
  goto :end
)
git branch -M main
git remote add origin "%REPO%"
git push -u origin main
if errorlevel 1 (
  echo.
  echo [!] push failed. Common causes:
  echo     - the repository was not created yet, or the URL is wrong
  echo     - it was created WITH a README, so the remote has a commit
  echo       ^(fix: git pull --rebase origin main, then push again^)
  echo     - credentials: sign in when the browser/git prompt appears
  popd
  goto :end
)

popd
echo.
echo ==========================================================
echo  DONE. studio/ is now backed up to a private repository.
echo.
echo  From now on, treat an uncommitted change in studio/ as a
echo  fault condition - push before you finish for the day.
echo ==========================================================

:end
endlocal
pause
