@echo off
REM ==============================================================
REM  OFFLINE safeboot fix - run this on the WORKING PC
REM  ASCII only (project rule for .bat files)
REM
REM  Use when the broken laptop's disk has been removed and attached
REM  to this PC (USB enclosure / adapter). No blind typing, no guessing:
REM  the safeboot flag is cleared directly in the laptop's BCD store.
REM
REM  ------------------------------------------------------------
REM  IMPORTANT SAFETY PROPERTY
REM  This script NEVER touches this PC's own boot configuration.
REM  Every bcdedit call is made with an explicit /store pointing at a
REM  file on the attached disk. It refuses to run without one.
REM  ------------------------------------------------------------
REM
REM  USAGE
REM    Step 1 - find the store:      offline_fix.bat scan
REM    Step 2 - clear the flag:      offline_fix.bat fix E:\EFI\Microsoft\Boot\BCD
REM    Step 3 - back up the project: offline_fix.bat backup E: C:\lifeinfo_backup
REM
REM  Must be run from an ADMIN command prompt.
REM ==============================================================
setlocal enabledelayedexpansion

net session >nul 2>&1
if errorlevel 1 (
  echo [STOP] This must run from an ADMIN command prompt.
  echo        Press Win+X then A, then run it again.
  goto :end
)

if "%~1"=="" goto :usage
if /i "%~1"=="scan"   goto :scan
if /i "%~1"=="fix"    goto :fix
if /i "%~1"=="backup" goto :backup
goto :usage


REM ============ scan ===========================================
:scan
echo.
echo === searching every drive letter for BCD stores ===
echo.
set FOUND=0
for %%L in (D E F G H I J K L M N O P Q R S T U V W X Y Z) do call :probe %%L
echo.
if "%FOUND%"=="0" (
  echo No BCD store found on any attached drive.
  echo.
  echo The EFI System Partition usually has NO drive letter. Assign one:
  echo.
  echo   diskpart
  echo     list disk
  echo     select disk N          ^(N = the attached laptop disk^)
  echo     list partition
  echo     select partition M     ^(M = the ~100-500MB System partition^)
  echo     assign letter=S
  echo     exit
  echo.
  echo Then run:  offline_fix.bat scan
) else (
  echo Found %FOUND% store^(s^) above.
  echo Pick the one on the LAPTOP disk, then run:
  echo   offline_fix.bat fix ^<that full path^>
)
goto :end

:probe
if exist "%1:\EFI\Microsoft\Boot\BCD" call :report "%1:\EFI\Microsoft\Boot\BCD" UEFI
if exist "%1:\Boot\BCD"               call :report "%1:\Boot\BCD" BIOS
goto :eof

:report
set /a FOUND+=1
echo ----------------------------------------------------------
echo   STORE : %~1
echo   TYPE  : %2
echo   safeboot present in this store?
bcdedit /store "%~1" /enum all 2>nul | findstr /i "safeboot description identifier"
echo ----------------------------------------------------------
echo.
goto :eof


REM ============ fix ============================================
:fix
if "%~2"=="" (
  echo [STOP] You must pass the store path explicitly.
  echo        Example: offline_fix.bat fix E:\EFI\Microsoft\Boot\BCD
  echo        Run 'offline_fix.bat scan' first to find it.
  goto :end
)
if not exist "%~2" (
  echo [STOP] Not found: %~2
  echo        Run 'offline_fix.bat scan' to list real store paths.
  goto :end
)

set STORE=%~2
set LOG=%~dp0offline_fix_log.txt

> "%LOG%" echo === offline safeboot fix ===
>> "%LOG%" echo run at : %DATE% %TIME%
>> "%LOG%" echo store  : %STORE%
>> "%LOG%" echo.

echo.
echo === BEFORE ===
>> "%LOG%" echo --- BEFORE ---
bcdedit /store "%STORE%" /enum all
>> "%LOG%" 2>&1 bcdedit /store "%STORE%" /enum all
>> "%LOG%" echo.

echo.
echo === clearing safeboot ===
>> "%LOG%" echo --- clearing safeboot ---
for %%E in ({default} {current}) do call :clearone %%E

echo.
echo === AFTER ===
>> "%LOG%" echo --- AFTER ---
bcdedit /store "%STORE%" /enum all
>> "%LOG%" 2>&1 bcdedit /store "%STORE%" /enum all

echo.
echo Done. If no 'safeboot' line appears above, the flag is gone.
echo Log: %LOG%
echo.
echo Next: shut down, put the disk back in the laptop, and power on.
echo The external monitor should light up as it did before.
goto :end

:clearone
echo   %1 ...
>> "%LOG%" echo entry %1:
>> "%LOG%" 2>&1 bcdedit /store "%STORE%" /deletevalue %1 safeboot
>> "%LOG%" 2>&1 bcdedit /store "%STORE%" /deletevalue %1 safebootalternateshell
goto :eof


REM ============ backup =========================================
:backup
if "%~2"=="" goto :usage
if "%~3"=="" goto :usage
set SRC=%~2\lifeinfo
set DST=%~3

if not exist "%SRC%" (
  echo [STOP] Not found: %SRC%
  echo        Pass the drive letter of the laptop's Windows partition.
  echo        Example: offline_fix.bat backup E: C:\lifeinfo_backup
  goto :end
)

echo.
echo Copying %SRC%  ->  %DST%
echo This includes studio\ and posts\, which have NO GitHub backup.
echo.
robocopy "%SRC%" "%DST%" /E /R:1 /W:1 /XJ /NFL /NDL /TEE /LOG+:"%~dp0backup_log.txt"
echo.
echo Copy finished. Verify the contents of %DST%
echo.
echo REMINDER: this copy contains Blogger API credentials.
echo Never commit it to the public lifeinfo-console repository.
echo Use a PRIVATE repository for studio\ and keep credentials out of git.
goto :end


REM ============ usage ==========================================
:usage
echo.
echo offline safeboot fix - run on the WORKING PC with the laptop disk attached
echo.
echo   offline_fix.bat scan
echo       search all drive letters for the laptop's BCD store
echo.
echo   offline_fix.bat fix ^<store path^>
echo       clear the safeboot flag in that store
echo       e.g. offline_fix.bat fix E:\EFI\Microsoft\Boot\BCD
echo.
echo   offline_fix.bat backup ^<laptop drive^> ^<destination^>
echo       copy the whole lifeinfo project off the laptop disk
echo       e.g. offline_fix.bat backup E: C:\lifeinfo_backup
echo.
echo Run from an ADMIN prompt. Never modifies this PC's own boot config.
echo.

:end
endlocal
pause
