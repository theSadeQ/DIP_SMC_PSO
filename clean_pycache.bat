@echo off
setlocal

rem Root folder to clean:
set "ROOT=D:\Projects\main\DIP_SMC_PSO"

if not exist "%ROOT%" (
  echo Folder not found: "%ROOT%"
  exit /b 1
)

echo Deleting __pycache__ folders...
for /D /R "%ROOT%" %%d in (__pycache__) do (
  if exist "%%d" rd /S /Q "%%d"
)

echo Deleting folders starting with a dot...
for /D /R "%ROOT%" %%d in (.*) do (
  rem Skip "." and ".." references
  if not "%%~nxd"=="." if not "%%~nxd"==".." (
    if exist "%%d" rd /S /Q "%%d"
  )
)

echo Done.
endlocal
