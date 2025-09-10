@echo off
REM === CONFIGURATION ===
set "REPO_PATH=D:\Projects\main\DIP_SMC_PSO"
set "REPO_NAME=DIP_SMC_PSO"
set "GITHUB_USER=thesadeq"
set "USER_NAME=thesadeq"
set "USER_EMAIL=xxxxsadeqxxxx@gmail.com"

REM === STEP 1: go to repo folder ===
cd /d "%REPO_PATH%"

REM === STEP 2: basic git setup ===
git config user.name "%USER_NAME%"
git config user.email "%USER_EMAIL%"
git config --global init.defaultBranch main

REM rename master -> main if needed
for /f "delims=" %%i in ('git branch --show-current') do (
  if "%%i"=="master" git branch -M main
)

REM === STEP 3: create starter files if missing ===
if not exist README.md echo # %REPO_NAME%> README.md
if not exist .gitignore (
  echo .vscode/>> .gitignore
  echo node_modules/>> .gitignore
  echo __pycache__/>> .gitignore
  echo *.log>> .gitignore
  echo dist/>> .gitignore
  echo build/>> .gitignore
)

git add -A
git commit -m "chore: initial commit" 2>nul

REM === STEP 4: SSH setup ===
if not exist "%USERPROFILE%\.ssh\id_ed25519" (
  echo Generating SSH key...
  ssh-keygen -t ed25519 -C "%USER_EMAIL%" -f "%USERPROFILE%\.ssh\id_ed25519" -N ""
)

sc config ssh-agent start= auto >nul
net start ssh-agent >nul
ssh-add %USERPROFILE%\.ssh\id_ed25519

echo.
echo === COPY THE FOLLOWING PUBLIC KEY TO GITHUB (Settings -> SSH and GPG keys) ===
type %USERPROFILE%\.ssh\id_ed25519.pub
echo ==============================================================================

pause
echo Continuing after you add the SSH key on GitHub...

REM === STEP 5: set origin and push ===
git remote remove origin 2>nul
git remote add origin git@github.com:%GITHUB_USER%/%REPO_NAME%.git
git push -u origin main

REM === STEP 6: verification ===
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
pause
