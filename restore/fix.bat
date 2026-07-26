@echo off
REM ==============================================================
REM  lifeinfo - blind display fix + diagnostics, with LOG READBACK
REM  ASCII only (project rule for .bat files)
REM
REM  PURPOSE
REM    Run this from a USB stick on a laptop whose screen is dead.
REM    You cannot see anything, so this script:
REM      1) beeps to tell you where it is (audio feedback)
REM      2) writes a log file NEXT TO ITSELF on the USB
REM         -> power off, unplug the USB, read the log on another PC
REM
REM  TWO PASSES, TWO LOGS - so a missed UAC prompt is still diagnosable:
REM    fix_log.txt        written WITHOUT admin rights. Display switching
REM                       and all diagnostics live here - they need no admin.
REM    fix_log_admin.txt  written WITH admin rights. Adds: clearing the
REM                       safeboot flag, enabling Remote Desktop, power cfg.
REM
REM  If only fix_log.txt exists, the UAC prompt was missed. Retry and
REM  press Alt+Y. The display fix may already have worked anyway.
REM
REM  SAFE TO RUN MULTIPLE TIMES. Does not delete user data.
REM  Does not disable the internal panel (see force_external.bat for that).
REM
REM  BEEP CODE
REM    1 beep        = script found and started
REM    1 long low    = UAC prompt is appearing now -> press Alt+Y
REM    2 rising      = running with admin rights, doing the admin steps
REM    3 (last long) = finished, log written, safe to power off
REM ==============================================================
setlocal enabledelayedexpansion

set DIR=%~dp0
set SELF=%~f0
set PS=powershell -NoProfile -ExecutionPolicy Bypass -Command

REM --- beep 1: started -----------------------------------------
%PS% "[console]::Beep(880,200)" >nul 2>&1

REM --- are we elevated? ----------------------------------------
net session >nul 2>&1
if not errorlevel 1 goto :elevated

REM ============ PASS 1: no admin rights ========================
REM Do everything that does NOT need admin, and log it. This way a
REM missed UAC prompt still leaves us a full diagnostic report.
set LOG=%DIR%fix_log.txt
set ELEV=NO
call :header
call :diagnose
call :switchdisplay
>> "%LOG%" echo.
>> "%LOG%" echo --- requesting admin rights now ---
>> "%LOG%" echo If fix_log_admin.txt does NOT exist next to this file, the UAC
>> "%LOG%" echo prompt was not accepted. Re-run and press Alt+Y.
>> "%LOG%" echo.
call :footer

REM beep long+low: UAC is coming
%PS% "[console]::Beep(300,900)" >nul 2>&1
%PS% "Start-Process -FilePath '%SELF%' -ArgumentList 'elevated' -Verb RunAs" >nul 2>&1
endlocal
goto :eof

REM ============ PASS 2: elevated ===============================
:elevated
REM beep 2 rising: we have admin
%PS% "[console]::Beep(880,150); Start-Sleep -m 120; [console]::Beep(1320,150)" >nul 2>&1

set LOG=%DIR%fix_log_admin.txt
set ELEV=YES
call :header
call :diagnose
call :fixsafeboot
call :switchdisplay
call :enablerdp
call :powercfg
call :checkproject
call :footer

REM beep 3: finished
%PS% "[console]::Beep(880,150); Start-Sleep -m 120; [console]::Beep(880,150); Start-Sleep -m 120; [console]::Beep(1320,400)" >nul 2>&1
endlocal
goto :eof


REM ============ subroutines ====================================
REM  Flattened on purpose: nested if/for blocks with redirection
REM  inside them are a fragile batch construct.

:header
> "%LOG%" echo ================================================
>> "%LOG%" echo  lifeinfo blind fix log
>> "%LOG%" echo  run at    : %DATE% %TIME%
>> "%LOG%" echo  script    : %SELF%
>> "%LOG%" echo  elevated  : %ELEV%
>> "%LOG%" echo ================================================
>> "%LOG%" echo.
>> "%LOG%" echo   (the USB drive letter above is the one that worked -
>> "%LOG%" echo    useful to know for next time)
>> "%LOG%" echo.
>> "%LOG%" echo --- [0] identity ---
>> "%LOG%" 2>&1 whoami
>> "%LOG%" echo.
goto :eof

:diagnose
>> "%LOG%" echo --- [1] Windows edition (RDP host needs Pro or better) ---
>> "%LOG%" 2>&1 %PS% "$o=Get-CimInstance Win32_OperatingSystem; '{0} | build {1} | {2}' -f $o.Caption,$o.BuildNumber,$o.OSArchitecture"
>> "%LOG%" echo.

>> "%LOG%" echo --- [2] SAFE MODE state (the key question) ---
>> "%LOG%" 2>&1 %PS% "'BootupState: ' + (Get-CimInstance Win32_ComputerSystem).BootupState"
>> "%LOG%" echo   'Normal boot'    = normal mode
>> "%LOG%" echo   'Fail-safe boot' = SAFE MODE - external output is impossible here
>> "%LOG%" echo.

>> "%LOG%" echo --- [3] graphics adapters ---
>> "%LOG%" 2>&1 %PS% "Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,CurrentHorizontalResolution,CurrentVerticalResolution,VideoModeDescription,Status | Format-List"
>> "%LOG%" echo.

>> "%LOG%" echo --- [4] MONITORS WINDOWS CAN SEE (most important section) ---
>> "%LOG%" echo Active monitor EDIDs:
>> "%LOG%" 2>&1 %PS% "Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorID -ErrorAction SilentlyContinue | ForEach-Object { $m=($_.ManufacturerName|Where-Object {$_ -gt 0}|ForEach-Object {[char]$_}) -join ''; $n=($_.UserFriendlyName|Where-Object {$_ -gt 0}|ForEach-Object {[char]$_}) -join ''; 'MFG=' + $m + ' NAME=' + $n + ' ACTIVE=' + $_.Active + ' INSTANCE=' + $_.InstanceName }"
>> "%LOG%" echo.
>> "%LOG%" echo Monitor PnP devices (including disabled ones):
>> "%LOG%" 2>&1 %PS% "Get-PnpDevice -Class Monitor -ErrorAction SilentlyContinue | Select-Object Status,FriendlyName,InstanceId | Format-List"
>> "%LOG%" echo.
>> "%LOG%" echo Desktop bounds Windows currently reports:
>> "%LOG%" 2>&1 %PS% "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::AllScreens | ForEach-Object { 'SCREEN ' + $_.DeviceName + ' primary=' + $_.Primary + ' bounds=' + $_.Bounds }"
>> "%LOG%" echo.
>> "%LOG%" echo   HOW TO READ THIS:
>> "%LOG%" echo   TWO monitors / TWO screens -^> the external one IS detected. This
>> "%LOG%" echo     is only a topology problem and force_external.bat will fix it.
>> "%LOG%" echo   ONE monitor (the internal panel) -^> the external output is not
>> "%LOG%" echo     being initialized. Try the other port (HDMI vs USB-C), then
>> "%LOG%" echo     see the hardware route in DISPLAY_RECOVERY.md.
>> "%LOG%" echo.
goto :eof

:fixsafeboot
>> "%LOG%" echo --- [5] clearing the safeboot flag ---
>> "%LOG%" 2>&1 bcdedit /enum {current}
>> "%LOG%" echo removing:
>> "%LOG%" 2>&1 bcdedit /deletevalue {current} safeboot
>> "%LOG%" 2>&1 bcdedit /deletevalue {current} safebootalternateshell
>> "%LOG%" echo   (an error here just means the flag was not set - that is fine)
>> "%LOG%" echo.
goto :eof

:switchdisplay
>> "%LOG%" echo --- [6] switching output to the external monitor ---
>> "%LOG%" echo trying /clone (most tolerant of EDID problems)...
start "" DisplaySwitch.exe /clone
%PS% "Start-Sleep -Seconds 6" >nul 2>&1
>> "%LOG%" 2>&1 %PS% "Get-CimInstance Win32_VideoController | Select-Object Name,CurrentHorizontalResolution,CurrentVerticalResolution | Format-List"
>> "%LOG%" echo.
>> "%LOG%" echo trying /external ...
start "" DisplaySwitch.exe /external
%PS% "Start-Sleep -Seconds 6" >nul 2>&1
>> "%LOG%" 2>&1 %PS% "Get-CimInstance Win32_VideoController | Select-Object Name,CurrentHorizontalResolution,CurrentVerticalResolution | Format-List"
>> "%LOG%" echo.
>> "%LOG%" echo screens after switching:
>> "%LOG%" 2>&1 %PS% "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::AllScreens | ForEach-Object { 'SCREEN ' + $_.DeviceName + ' primary=' + $_.Primary + ' bounds=' + $_.Bounds }"
>> "%LOG%" echo.
goto :eof

:enablerdp
>> "%LOG%" echo --- [7] enabling Remote Desktop ---
>> "%LOG%" 2>&1 reg add "HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f
>> "%LOG%" echo   NLA is deliberately left ENABLED. Do not weaken RDP auth unless
>> "%LOG%" echo   a connection is actually refused - see BLIND_USB.md.
>> "%LOG%" 2>&1 netsh advfirewall firewall set rule group="remote desktop" new enable=Yes
>> "%LOG%" 2>&1 sc config TermService start= auto
>> "%LOG%" 2>&1 net start TermService
>> "%LOG%" echo.
>> "%LOG%" echo --- [8] address to connect to (use mstsc from another PC) ---
>> "%LOG%" 2>&1 %PS% "Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {$_.IPAddress -notlike '127.*'} | Select-Object IPAddress,InterfaceAlias,PrefixLength | Format-List"
>> "%LOG%" 2>&1 %PS% "'hostname: ' + [System.Net.Dns]::GetHostName()"
>> "%LOG%" 2>&1 %PS% "Get-CimInstance Win32_UserAccount -Filter 'LocalAccount=True' | Select-Object Name,Disabled | Format-List"
>> "%LOG%" echo.
goto :eof

:powercfg
>> "%LOG%" echo --- [9] lid close action -^> do nothing ---
>> "%LOG%" 2>&1 powercfg /setacvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 5ca83367-6e45-459f-a27b-476b1d01c936 0
>> "%LOG%" 2>&1 powercfg /setdcvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 5ca83367-6e45-459f-a27b-476b1d01c936 0
>> "%LOG%" 2>&1 powercfg /setactive SCHEME_CURRENT
>> "%LOG%" echo.
goto :eof

:checkproject
>> "%LOG%" echo --- [10] is C:\lifeinfo intact? ---
if exist "C:\lifeinfo" goto :proj_yes
>> "%LOG%" echo C:\lifeinfo MISSING - folder gone or drive not mounted
>> "%LOG%" echo.
goto :eof
:proj_yes
>> "%LOG%" echo C:\lifeinfo EXISTS
>> "%LOG%" 2>&1 dir "C:\lifeinfo"
call :chkdir studio
call :chkdir posts
call :chkdir webapp
call :chkdir thumbs
call :chkdir thumbs_naver
call :chkfile lifeinfo_db.txt
call :chkfile deploy.bat
call :chkfile CLAUDE.md
>> "%LOG%" echo.
goto :eof

:chkdir
if exist "C:\lifeinfo\%1" goto :chkdir_yes
>> "%LOG%" echo   %1\ : MISSING
goto :eof
:chkdir_yes
for /f %%C in ('dir /b "C:\lifeinfo\%1" 2^>nul ^| find /c /v ""') do >> "%LOG%" echo   %1\ : EXISTS  %%C items
goto :eof

:chkfile
if exist "C:\lifeinfo\%1" goto :chkfile_yes
>> "%LOG%" echo   %1 : MISSING
goto :eof
:chkfile_yes
>> "%LOG%" echo   %1 : EXISTS
goto :eof

:footer
>> "%LOG%" echo ================================================
>> "%LOG%" echo  END OF LOG (elevated=%ELEV%)
>> "%LOG%" echo  Power off with a SHORT press of the power button,
>> "%LOG%" echo  unplug the USB, and read this on another PC.
>> "%LOG%" echo ================================================
goto :eof
