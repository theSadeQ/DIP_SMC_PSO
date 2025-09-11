@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM gh_upsert_and_pr.bat
REM
REM Modes:
REM   SINGLE-FILE:
REM     gh_upsert_and_pr.bat <TARGET_IN_REPO> <LOCAL_SOURCE> <BRANCH> [COMMIT_MSG] [PR_TITLE] [BASE]
REM
REM   MANIFEST (multi-file):
REM     gh_upsert_and_pr.bat --manifest <MANIFEST_PATH> <BRANCH> [COMMIT_MSG] [PR_TITLE] [BASE]
REM
REM Notes:
REM - Requires: git, gh (GitHub CLI)
REM - Optional: set RUN_TESTS=1 to run `pytest -q` before committing.
REM - If push to origin fails (no push access), the script forks repo and pushes to your fork, then opens a PR.
REM - MANIFEST format: one mapping per line =>  LOCAL_PATH|TARGET_PATH_IN_REPO
REM   Example:
REM     C:\tmp\config.py|src\config.py
REM     C:\tmp\factory.py|src\Controllers\factory.py
REM ============================================================

where gh >nul 2>nul || (echo ERROR: GitHub CLI (gh) not found. & exit /b 1)
where git >nul 2>nul || (echo ERROR: git not found. & exit /b 1)

if not exist ".git" (
  echo ERROR: Run this from the repository root (where .git exists).
  exit /b 1
)

set "MODE=SINGLE"
set "BASE=main"

if "%~1"=="--manifest" (
  if "%~2"=="" (
    echo Usage: --manifest ^<MANIFEST_PATH^> ^<BRANCH^> [COMMIT_MSG] [PR_TITLE] [BASE]
    exit /b 1
  )
  set "MODE=MANIFEST"
  set "MANIFEST=%~2"
  set "BRANCH=%~3"
  set "COMMIT=%~4"
  set "TITLE=%~5"
  if not "%~6"=="" set "BASE=%~6"
) else (
  if "%~3"=="" (
    echo Usage: ^<TARGET_IN_REPO^> ^<LOCAL_SOURCE^> ^<BRANCH^> [COMMIT_MSG] [PR_TITLE] [BASE]
    exit /b 1
  )
  set "TARGET=%~1"
  set "SRC=%~2"
  set "BRANCH=%~3"
  set "COMMIT=%~4"
  set "TITLE=%~5"
  if not "%~6"=="" set "BASE=%~6"
)

if "%COMMIT%"=="" set "COMMIT=Automated update"
if "%TITLE%"=="" set "TITLE=%COMMIT%"

REM ---- Sync base and create/checkout branch
git fetch --all
git checkout "%BASE%" || git checkout -q .
git pull --rebase || (echo ERROR: failed to update base branch %BASE%. & exit /b 1)
git checkout -b "%BRANCH%" 2>nul || git checkout "%BRANCH%" || (echo ERROR: cannot checkout branch. & exit /b 1)

REM ---- Apply changes
set "CHANGES=0"

if /I "%MODE%"=="MANIFEST" (
  if not exist "%MANIFEST%" (echo ERROR: Manifest not found: %MANIFEST% & exit /b 1)
  for /f "usebackq tokens=1,2 delims=|" %%A in ("%MANIFEST%") do (
    set "SRCFILE=%%~A"
    set "TGTFILE=%%~B"
    if "!SRCFILE!"=="" (echo Skipping blank line in manifest & goto :CONT_LOOP)
    if "!TGTFILE!"=="" (echo ERROR: Bad line in manifest (missing target): %%A^|%%B & exit /b 1)

    if not exist "!SRCFILE!" (
      echo ERROR: Source file not found: !SRCFILE!
      exit /b 1
    )

    for %%I in ("!TGTFILE!") do set "TGT_DIR=%%~dpI"
    if not exist "!TGT_DIR!" mkdir "!TGT_DIR!"

    copy /Y "!SRCFILE!" "!TGTFILE!" >nul || (echo ERROR: Copy failed: !SRCFILE! -> !TGTFILE! & exit /b 1)
    git add "!TGTFILE!"
    set /a CHANGES+=1
    :CONT_LOOP
  )
) else (
  if not exist "%SRC%" (echo ERROR: Source file not found: %SRC% & exit /b 1)
  if not exist "%TARGET%" (
    for %%I in ("%TARGET%") do set "TARGETDIR=%%~dpI"
    if not exist "%TARGETDIR%" mkdir "%TARGETDIR%"
  )
  copy /Y "%SRC%" "%TARGET%" >nul || (echo ERROR: Copy failed: %SRC% -> %TARGET% & exit /b 1)
  git add "%TARGET%"
  set /a CHANGES+=1
)

if "%CHANGES%"=="0" (
  echo No changes staged. Exiting.
  exit /b 0
)

REM ---- Optional tests
if "%RUN_TESTS%"=="1" (
  where pytest >nul 2>nul || (echo WARNING: pytest not found, skipping tests.)
  if not errorlevel 1 (
    echo Running tests...
    pytest -q || (echo ERROR: tests failed. Aborting commit. & exit /b 1)
  )
)

REM ---- Commit
git commit -m "%COMMIT%" || (echo Nothing to commit. & exit /b 1)

REM ---- Push (fall back to fork if necessary)
git push -u origin "%BRANCH%"
if errorlevel 1 (
  echo Push failed (no push access?). Attempting fork flow...
  gh repo fork --remote || (echo ERROR: fork failed. & exit /b 1)
  git push -u origin "%BRANCH%" || (echo ERROR: push to fork failed. & exit /b 1)
)

REM ---- Open PR
gh pr create --fill --base "%BASE%" --head "%BRANCH%" --web
endlocal
