@echo off
REM ==============================================================
REM  Back up studio/ to a PRIVATE repository - credential-safe by design
REM  ASCII only (project rule for .bat files)
REM
REM  WHY THIS EXISTS
REM    studio/ (the whole publish pipeline), posts/ and CLAUDE.md have never
REM    been in any git repository. The 2026-07-26 lockout showed the cost:
REM    the console, DB and thumbnails were all safe on GitHub while the tools
REM    existed on exactly one machine.
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
set XF=/XF client_secret*.json client_secrets*.json credentials*.json token*.json token*.pickle service_account*.json *.pem *.key *.p12 *.pfx .env
set XD=/XD __pycache__ .venv venv .git node_modules

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
>> "%DST%\.gitignore" echo client_secret*.json
>> "%DST%\.gitignore" echo client_secrets*.json
>> "%DST%\.gitignore" echo credentials*.json
>> "%DST%\.gitignore" echo token*.json
>> "%DST%\.gitignore" echo token*.pickle
>> "%DST%\.gitignore" echo service_account*.json
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
REM Matches secret VALUES, not identifiers. Naming a variable refresh_token or
REM reading os.environ["CLIENT_SECRET"] is correct practice and must not trip
REM this - otherwise the guard blocks every run and the backup never happens.
REM PowerShell is used because batch findstr regex cannot express these.
echo [3/5] scanning for credentials ...
set SCAN=%DST%\_credscan.txt
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$pat = @(" ^
 "  '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'," ^
 "  '[0-9]{10,}-[a-z0-9]{20,}\.apps\.googleusercontent\.com'," ^
 "  'GOCSPX-[A-Za-z0-9_\-]{15,}'," ^
 "  '\"client_secret\"\s*:\s*\"[^\"]{10,}\"'," ^
 "  '\"refresh_token\"\s*:\s*\"[^\"]{20,}\"'," ^
 "  '\"private_key\"\s*:\s*\"-----BEGIN'" ^
 ") -join '|';" ^
 "Get-ChildItem -Path '%DST%' -Recurse -File -Include *.json,*.txt,*.py,*.bat,*.md,*.cfg,*.ini,*.yaml,*.yml,*.ps1 -ErrorAction SilentlyContinue |" ^
 " Select-String -Pattern $pat -List -ErrorAction SilentlyContinue |" ^
 " ForEach-Object { $_.Path } | Set-Content -Encoding ASCII '%SCAN%'"

set HITS=0
if exist "%SCAN%" (
  for /f "usebackq delims=" %%F in ("%SCAN%") do (
    echo    [SECRET] %%F
    set /a HITS+=1
  )
  del "%SCAN%" >nul 2>&1
)

if not "%HITS%"=="0" (
  echo.
  echo ==========================================================
  echo  STOPPED - %HITS% file^(s^) above look like they contain a
  echo  credential. Nothing has been committed or pushed.
  echo.
  echo  Review each one. If a file legitimately needs to live in
  echo  the repo, strip the secret out of it first and have the
  echo  code read the value from an environment variable instead.
  echo  Then delete %DST% and run this again.
  echo ==========================================================
  goto :end
)
echo    clean - no credential patterns found.

REM ---- 4) what is about to be committed ------------------------
echo [4/5] contents to be committed:
pushd "%DST%"
git init -q
git add -A
echo.
git -c core.quotepath=off status --short
echo.
for /f %%C in ('git diff --cached --name-only ^| find /c /v ""') do echo    total %%C files
echo.
echo Review the list above. Nothing has been pushed yet.
set /p OK=Type YES to commit and push:
if /i not "%OK%"=="YES" (
  echo Aborted. %DST% is left in place for inspection.
  popd
  goto :end
)

REM ---- 5) commit and push -------------------------------------
echo [5/5] committing and pushing ...
git -c user.useConfigOnly=false commit -q -m "initial backup of studio pipeline, posts and harness rules"
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
