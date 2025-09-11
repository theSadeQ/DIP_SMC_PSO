@echo off
setlocal

REM Usage: apply_patches_and_pr.bat <BRANCH> <PATCH1> [PATCH2] ...

if "%~2"=="" (
  echo Usage: %0 ^<BRANCH^> ^<PATCH1^> [PATCH2] ...
  exit /b 1
)

set "BRANCH=%~1"
shift

git fetch --all
git checkout main
git pull --rebase
git checkout -b "%BRANCH%" 2>nul || git checkout "%BRANCH%"

:LOOP
if "%~1"=="" goto DONE
  echo Applying patch %~1
  git apply --whitespace=fix "%~1" || (echo ERROR: applying %~1 failed & exit /b 1)
  shift
goto LOOP

:DONE
git add -A
git commit -m "apply patches: %BRANCH%"
git push -u origin "%BRANCH%" || (
  echo Push failed, trying fork...
  gh repo fork --remote
  git push -u origin "%BRANCH%"
)

gh pr create --fill --base main --head "%BRANCH%" --web
endlocal
