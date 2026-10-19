@echo off
chcp 65001 >nul
title Merge cloud branch into main (Console PC)
cd /d "%~dp0"

rem ============================================================
rem  Console PC merge button.
rem  Cloud sessions push ONLY to a work branch. Merging into main
rem  happens here, on the PC, by you. This script never pushes.
rem  Push/deploy afterwards with deploy.bat as usual.
rem ============================================================
set "BRANCH=ccr-478bb848-5x7ulr"
if not "%~1"=="" set "BRANCH=%~1"

echo.
echo  Merge target : main  (this PC)
echo  Cloud branch : %BRANCH%
echo.

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 ( echo [ERROR] Not a git folder. Put this file in the clone folder. & goto :end )

git status --porcelain > "%TEMP%\_merge_dirty.txt"
for %%A in ("%TEMP%\_merge_dirty.txt") do if %%~zA GTR 0 (
  echo [STOP] Uncommitted changes exist. Commit or stash them first:
  type "%TEMP%\_merge_dirty.txt"
  goto :end
)

echo [1/4] Fetching from GitHub...
git fetch origin
if errorlevel 1 ( echo [ERROR] fetch failed. Check the network. & goto :end )

git rev-parse --verify "origin/%BRANCH%" >nul 2>&1
if errorlevel 1 ( echo [ERROR] origin/%BRANCH% not found. See MERGE_NEEDED.md for the branch name. & goto :end )

echo.
echo [2/4] Commits that will be merged:
git log --oneline "main..origin/%BRANCH%"
echo.
set /p OK=Merge these into main? (y/N): 
if /i not "%OK%"=="y" ( echo Cancelled. Nothing changed. & goto :end )

echo.
echo [3/4] Updating main...
git checkout main
if errorlevel 1 ( echo [ERROR] checkout main failed. & goto :end )
git pull --ff-only origin main
if errorlevel 1 (
  echo [STOP] main cannot fast-forward. Fix this on the PC first, then run again.
  goto :end
)

echo.
echo [4/4] Merging...
git merge --no-ff --no-edit "origin/%BRANCH%"
if errorlevel 1 (
  echo.
  echo [CONFLICT] Merge stopped. Aborting so nothing is half-merged.
  git merge --abort
  echo Resolve manually or ask Claude for help.
  goto :end
)

echo.
echo [DONE] Merged locally. NOT pushed.
echo Next: run deploy.bat as usual to publish.

:end
echo.
pause
