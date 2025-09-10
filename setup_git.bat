@echo off
setlocal

REM =========================
REM === CONFIG — EDIT ME ===
REM =========================
set "REPO_PATH=D:\Projects\main\DIP_SMC_PSO"
set "REPO_NAME=DIP_SMC_PSO"
set "GITHUB_USER=thesadeq"
set "USER_NAME=thesadeq"
set "USER_EMAIL=xxxxsadeqxxxx@gmail.com"
REM =========================

echo.
echo === GitHub SSH one-shot setup for %REPO_NAME% ===
echo Repo folder: %REPO_PATH%
echo GitHub user: %GITHUB_USER%
echo.

REM --- Go to repo folder ---
cd /d "%REPO_PATH%" || (echo [ERROR] Repo path not found. & pause & exit /b 1)

REM --- Ensure this is a git repo (won't hurt if already init) ---
if not exist ".git" git init

REM --- Basic git config + line-endings to silence LF/CRLF warnings ---
git --version
git config user.name "%USER_NAME%"
git config user.email "%USER_EMAIL%"
git config --global init.defaultBranch main
git config --global core.autocrlf true

REM --- Rename master -> main if needed ---
for /f "delims=" %%i in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "CURBR=%%i"
if /i "%CURBR%"=="master" git branch -M main

REM --- Create starter files if missing (safe if they already exist) ---
if not exist "README.md" echo # %REPO_NAME%> "README.md"
if not exist ".gitignore" (
  >".gitignore" echo .vscode/
  >>".gitignore" echo __pycache__/
  >>".gitignore" echo node_modules/
  >>".gitignore" echo *.log
  >>".gitignore" echo dist/
  >>".gitignore" echo build/
)

REM --- First commit (no error if nothing to commit) ---
git add -A
git commit -m "chore: initial commit" 2>nul

REM =========================
REM === SSH KEY + AGENT  ===
REM =========================

REM Ensure .ssh exists
if not exist "%USERPROFILE%\.ssh" mkdir "%USERPROFILE%\.ssh"

REM Generate ed25519 key if missing (no passphrase; change if you want)
if not exist "%USERPROFILE%\.ssh\id_ed25519" (
  echo Generating SSH key...
  ssh-keygen -t ed25519 -C "%USER_EMAIL%" -f "%USERPROFILE%\.ssh\id_ed25519" -N ""
)

REM Try to enable and start ssh-agent (OK if this fails; key still works without agent)
sc config ssh-agent start= auto >nul 2>&1
net start ssh-agent >nul 2>&1
ssh-add "%USERPROFILE%\.ssh\id_ed25519" >nul 2>&1

echo.
echo === COPY THIS PUBLIC KEY TO GitHub > Settings > SSH and GPG keys ===
type "%USERPROFILE%\.ssh\id_ed25519.pub"
echo ====================================================================
echo After adding the key on GitHub, press any key to continue...
pause >nul

REM =========================
REM === REMOTE + FIRST PUSH
REM =====================
