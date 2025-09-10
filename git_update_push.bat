@echo off
setlocal

REM =========================
REM === CONFIG — EDIT ME ===
REM =========================
set "REPO_PATH=D:\Projects\main\DIP_SMC_PSO"
set "REPO_NAME=DIP_SMC_PSO"
set "GITHUB_USER=theSadeQ"
set "COMMIT_MSG=%*"
if "%COMMIT_MSG%"=="" set "COMMIT_MSG=update: quick save"

echo.
echo === Git Update & Push (SSH) ===
echo Repo: %REPO_PATH%
echo User: %GITHUB_USER%
echo Msg : %COMMIT_MSG%
echo.

REM --- Go to repo folder ---
cd /d "%REPO_PATH%" || (echo [ERROR] Repo path not found. & pause & exit /b 1)

REM --- Optional: silence CRLF warnings globally ---
git config --global core.autocrlf true

REM --- Ensure branch is 'main' (rename if currently on master) ---
for /f "delims=" %%i in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "CURBR=%%i"
if /i "%CURBR%"=="master" git branch -M main

REM --- Ensure 'origin' points to correct SSH URL ---
set "SSH_URL=git@github.com:%GITHUB_USER%/%REPO_NAME%.git"
for /f "delims=" %%u in ('git remote get-url origin 2^>nul') do set "CURURL=%%u"
if "%CURURL%"=="" (
  git remote add origin "%SSH_URL%"
) else (
  if /i not "%CURURL%"=="%SSH_URL%" git remote set-url origin "%SSH_URL%"
)

REM --- Start ssh-agent and add key (quietly) ---
sc config ssh-agent start= auto >nul 2>&1
net start ssh-agent >nul 2>&1
if exist "%USERPROFILE%\.ssh\id_ed25519" (
  ssh-add "%USERPROFILE%\.ssh\id_ed25519" >nul 2>&1
) else (
  echo [WARN] No SSH key found at %USERPROFILE%\.ssh\id_ed25519
  echo        If you need one, run your setup script again to create it.
)

REM --- Save & push workflow ---
git add -A
git commit -m "%COMMIT_MSG%" 2>nul || echo (Nothing to commit; continuing)
echo.
echo Pulling latest (rebase)...
git pull --rebase origin main
echo.
echo Pushing to %SSH_URL% ...
git push -u origin main

REM --- Verification ---
echo.
echo === REMOTE URLS ===
git remote -v
echo.
echo === CURRENT BRANCH ===
git branch --show-current
echo.
echo === RECENT COMMITS ===
git log --oneline -n 3

echo.
echo Open in browser: https://github.com/%GITHUB_USER%/%REPO_NAME%
start "" "https://github.com/%GITHUB_USER%/%REPO_NAME%"
echo Done.
pause
