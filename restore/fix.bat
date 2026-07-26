@echo off
REM ==============================================================
REM  lifeinfo - blind display fix + diagnostics, with LOG READBACK
REM  ASCII only (project rule for .bat files)
REM
REM  PURPOSE
REM    Run this from a USB stick on a laptop whose screen is dead.
REM    You cannot see anything, so this script:
REM      1) beeps to tell you where it is (audio feedback)
REM      2) writes fix_log.txt NEXT TO ITSELF on the USB
REM         -> unplug the USB, read the log on another PC
REM
REM  SAFE TO RUN MULTIPLE TIMES. It does not delete user data.
REM
REM  BEEP CODE
REM    1 beep       = script started, found on the USB
REM    1 long low   = UAC prompt is about to appear -> press Alt+Y
REM    2 rising     = running with admin rights (good), work started
REM    3 (last long)= finished, log written, safe to power off
REM
REM  If you hear beep 1 and the long low beep but never the 2 rising
REM  beeps, the UAC prompt was not accepted. Retry and press Alt+Y.
REM ==============================================================
setlocal enabledelayedexpansion

set LOG=%~dp0fix_log.txt
set PS=powershell -NoProfile -ExecutionPolicy Bypass -Command

REM --- beep 1: started -----------------------------------------
%PS% "[console]::Beep(880,200)" >nul 2>&1

REM --- self-elevate --------------------------------------------
net session >nul 2>&1
if errorlevel 1 (
  %PS% "[console]::Beep(300,900)" >nul 2>&1
  echo Requesting admin rights. Press Alt+Y when UAC appears.
  %PS% "Start-Process -FilePath '%~f0' -Verb RunAs" >nul 2>&1
  REM the elevated copy does the real work; this one exits
  goto :eof
)

REM --- beep 2: we are admin ------------------------------------
%PS% "[console]::Beep(880,150); Start-Sleep -m 120; [console]::Beep(1320,150)" >nul 2>&1

> "%LOG%" echo ================================================
>> "%LOG%" echo  lifeinfo blind fix log
>> "%LOG%" echo  run at: %DATE% %TIME%
>> "%LOG%" echo  script: %~f0
>> "%LOG%" echo ================================================
>> "%LOG%" echo.

>> "%LOG%" echo --- [0] identity / elevation ---
>> "%LOG%" 2>&1 whoami
>> "%LOG%" echo elevation: ADMIN (net session succeeded)
>> "%LOG%" echo.

>> "%LOG%" echo --- [1] Windows edition (RDP host needs Pro/Enterprise) ---
>> "%LOG%" 2>&1 %PS% "$o=Get-CimInstance Win32_OperatingSystem; '{0} | build {1} | {2}' -f $o.Caption,$o.BuildNumber,$o.OSArchitecture"
>> "%LOG%" echo.

>> "%LOG%" echo --- [2] SAFE MODE state (this is the key question) ---
>> "%LOG%" 2>&1 %PS% "$b=(Get-CimInstance Win32_ComputerSystem).BootupState; 'BootupState: ' + $b"
>> "%LOG%" echo   ('Normal boot' = normal mode, 'Fail-safe boot' = SAFE MODE)
>> "%LOG%" echo BCD entry for current boot:
>> "%LOG%" 2>&1 bcdedit /enum {current}
>> "%LOG%" echo.

>> "%LOG%" echo --- [3] removing safeboot flag ---
>> "%LOG%" 2>&1 bcdedit /deletevalue {current} safeboot
>> "%LOG%" 2>&1 bcdedit /deletevalue {current} safebootalternateshell
>> "%LOG%" echo   (an error here just means the flag was not set - that is fine)
>> "%LOG%" echo.

>> "%LOG%" echo --- [4] graphics adapters ---
>> "%LOG%" 2>&1 %PS% "Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,CurrentHorizontalResolution,CurrentVerticalResolution,VideoModeDescription,Status | Format-List"
>> "%LOG%" echo.

>> "%LOG%" echo --- [5] MONITORS WINDOWS CAN SEE (critical) ---
>> "%LOG%" echo Active monitor EDIDs:
>> "%LOG%" 2>&1 %PS% "Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorID -ErrorAction SilentlyContinue | ForEach-Object { $m=($_.ManufacturerName|Where-Object {$_ -gt 0}|ForEach-Object {[char]$_}) -join ''; $n=($_.UserFriendlyName|Where-Object {$_ -gt 0}|ForEach-Object {[char]$_}) -join ''; 'MFG=' + $m + ' NAME=' + $n + ' ACTIVE=' + $_.Active + ' INSTANCE=' + $_.InstanceName }"
>> "%LOG%" echo.
>> "%LOG%" echo Monitor PnP devices (including disabled/unknown):
>> "%LOG%" 2>&1 %PS% "Get-PnpDevice -Class Monitor -ErrorAction SilentlyContinue | Select-Object Status,FriendlyName,InstanceId | Format-List"
>> "%LOG%" echo.
>> "%LOG%" echo   HOW TO READ THIS: if TWO monitors appear, the external one IS
>> "%LOG%" echo   detected and this is purely a topology problem (fixable in software).
>> "%LOG%" echo   If only ONE appears and it is the internal panel, the external
>> "%LOG%" echo   output is not being initialized -> try the other port, or the
>> "%LOG%" echo   hardware route in DISPLAY_RECOVERY.md.
>> "%LOG%" echo.

>> "%LOG%" echo --- [6] switching output to the external monitor ---
>> "%LOG%" echo trying /clone first (most tolerant of EDID problems)...
start /wait "" DisplaySwitch.exe /clone
>> "%LOG%" echo   DisplaySwitch /clone issued
%PS% "Start-Sleep -Seconds 6" >nul 2>&1
>> "%LOG%" echo resolution after /clone:
>> "%LOG%" 2>&1 %PS% "Get-CimInstance Win32_VideoController | Select-Object Name,CurrentHorizontalResolution,CurrentVerticalResolution | Format-List"
>> "%LOG%" echo.
>> "%LOG%" echo trying /external ...
start /wait "" DisplaySwitch.exe /external
>> "%LOG%" echo   DisplaySwitch /external issued
%PS% "Start-Sleep -Seconds 6" >nul 2>&1
>> "%LOG%" echo resolution after /external:
>> "%LOG%" 2>&1 %PS% "Get-CimInstance Win32_VideoController | Select-Object Name,CurrentHorizontalResolution,CurrentVerticalResolution | Format-List"
>> "%LOG%" echo.

>> "%LOG%" echo --- [7] enabling Remote Desktop (so you can use another PC) ---
>> "%LOG%" 2>&1 reg add "HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f
>> "%LOG%" echo   (NLA is left ENABLED on purpose - do not weaken RDP auth unless
>> "%LOG%" echo    a connection actually gets refused. See BLIND_USB.md if so.)
>> "%LOG%" 2>&1 netsh advfirewall firewall set rule group="remote desktop" new enable=Yes
>> "%LOG%" 2>&1 sc config TermService start= auto
>> "%LOG%" 2>&1 net start TermService
>> "%LOG%" echo.

>> "%LOG%" echo --- [8] network address (use this to connect by RDP) ---
>> "%LOG%" 2>&1 %PS% "Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {$_.IPAddress -notlike '127.*'} | Select-Object IPAddress,InterfaceAlias,PrefixLength | Format-List"
>> "%LOG%" 2>&1 %PS% "'hostname: ' + [System.Net.Dns]::GetHostName()"
>> "%LOG%" echo.

>> "%LOG%" echo --- [9] lid close action -> do nothing (keeps PC awake) ---
>> "%LOG%" 2>&1 powercfg /setacvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 5ca83367-6e45-459f-a27b-476b1d01c936 0
>> "%LOG%" 2>&1 powercfg /setdcvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 5ca83367-6e45-459f-a27b-476b1d01c936 0
>> "%LOG%" 2>&1 powercfg /setactive SCHEME_CURRENT
>> "%LOG%" echo.

>> "%LOG%" echo --- [10] is C:\lifeinfo intact? ---
if not exist "C:\lifeinfo" goto :nolifeinfo
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
goto :lifeinfodone

:nolifeinfo
>> "%LOG%" echo C:\lifeinfo MISSING - folder gone or drive not mounted

:lifeinfodone
>> "%LOG%" echo.

>> "%LOG%" echo ================================================
>> "%LOG%" echo  DONE. Next: power off, unplug the USB, and read
>> "%LOG%" echo  this file on another PC. Then reboot the laptop
>> "%LOG%" echo  normally - safeboot has been cleared.
>> "%LOG%" echo ================================================

REM --- beep 3: finished ---------------------------------------
%PS% "[console]::Beep(880,150); Start-Sleep -m 120; [console]::Beep(880,150); Start-Sleep -m 120; [console]::Beep(1320,400)" >nul 2>&1

endlocal
goto :eof

REM ============ subroutines ====================================
REM  Flattened on purpose: nested if/for blocks with redirection
REM  inside them are a known-fragile batch construct.

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
