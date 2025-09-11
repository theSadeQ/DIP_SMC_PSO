@echo off
setlocal

REM ---- settings you can tweak ----
set "BRANCH=c04/tests-integration"
set "FILE=tests\test_integration\test_settings_precedence.py"
set "BASE=main"
set "COMMIT=tests: add settings precedence integration test"

REM ---- sanity checks ----
where git >nul 2>nul || (echo ERROR: git not found & exit /b 1)
where gh  >nul 2>nul || (echo ERROR: gh (GitHub CLI) not found & exit /b 1)
if not exist ".git" (echo ERROR: run this in the repo root & exit /b 1)

REM ---- stash local changes so rebase won't fail ----
git diff --quiet || git stash push -m "auto-stash for new test"

REM ---- sync base and branch ----
git fetch --all
git checkout "%BASE%" || (echo ERROR: cannot checkout %BASE% & exit /b 1)
git pull --rebase    || (echo ERROR: pull --rebase failed & exit /b 1)
git checkout -b "%BRANCH%" 2>nul || git checkout "%BRANCH%" || (echo ERROR: cannot checkout %BRANCH% & exit /b 1)

REM ---- ensure target folder exists ----
for %%I in ("%FILE%") do set "TARGETDIR=%%~dpI"
if not exist "%TARGETDIR%" mkdir "%TARGETDIR%"

REM ---- write a temporary PowerShell script that writes the test file ----
set "TMPPS=%TEMP%\write_settings_precedence_test.ps1"
> "%TMPPS%" echo Param([string]^$OutPath)
>> "%TMPPS%" echo ^$content = @'
>> "%TMPPS%" echo import os
>> "%TMPPS%" echo from pathlib import Path
>> "%TMPPS%" echo import pytest
>> "%TMPPS%" echo
>> "%TMPPS%" echo from src.config import load_config
>> "%TMPPS%" echo
>> "%TMPPS%" echo
>> "%TMPPS%" echo def _repo_root_from_here() -> Path^:
>> "%TMPPS%" echo     """Resolve the repository root relative to this test file location."""
>> "%TMPPS%" echo     here = Path(__file__).resolve()
>> "%TMPPS%" echo     return here.parents[2]
>> "%TMPPS%" echo
>> "%TMPPS%" echo
>> "%TMPPS%" echo def test_env_overrides_file(monkeypatch: pytest.MonkeyPatch)^:
>> "%TMPPS%" echo     """ENV should override values coming from the config file."""
>> "%TMPPS%" echo     repo_root = _repo_root_from_here()
>> "%TMPPS%" echo     cfg_path = repo_root / "config.yaml"
>> "%TMPPS%" echo     assert cfg_path.exists()
>> "%TMPPS%" echo
>> "%TMPPS%" echo     monkeypatch.setenv("C04__SIMULATION__DT", "0.005")
>> "%TMPPS%" echo     cfg = load_config(str(cfg_path))
>> "%TMPPS%" echo     assert float(cfg.simulation.dt) == pytest.approx(0.005, rel=0, abs=1e-12)
>> "%TMPPS%" echo
>> "%TMPPS%" echo     monkeypatch.delenv("C04__SIMULATION__DT", raising=False)
>> "%TMPPS%" echo
>> "%TMPPS%" echo
>> "%TMPPS%" echo def test_dotenv_overrides_file_but_not_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch)^:
>> "%TMPPS%" echo     """.env should override file, but real ENV must still have highest precedence."""
>> "%TMPPS%" echo     repo_root = _repo_root_from_here()
>> "%TMPPS%" echo     cfg_path = repo_root / "config.yaml"
>> "%TMPPS%" echo     assert cfg_path.exists()
>> "%TMPPS%" echo
>> "%TMPPS%" echo     dotenv_file = tmp_path / ".env"
>> "%TMPPS%" echo     dotenv_file.write_text("C04__SIMULATION__DT=0.010`n", encoding="utf-8")
>> "%TMPPS%" echo
>> "%TMPPS%" echo     monkeypatch.chdir(tmp_path)
>> "%TMPPS%" echo     monkeypatch.setenv("C04__SIMULATION__DT", "0.003")
>> "%TMPPS%" echo     cfg = load_config(str(cfg_path))
>> "%TMPPS%" echo     assert float(cfg.simulation.dt) == pytest.approx(0.003, rel=0, abs=1e-12)
>> "%TMPPS%" echo
>> "%TMPPS%" echo     monkeypatch.delenv("C04__SIMULATION__DT", raising=False)
>> "%TMPPS%" echo     cfg = load_config(str(cfg_path))
>> "%TMPPS%" echo     assert float(cfg.simulation.dt) == pytest.approx(0.010, rel=0, abs=1e-12)
>> "%TMPPS%" echo
>> "%TMPPS%" echo
>> "%TMPPS%" echo def test_file_used_when_no_env_or_dotenv(monkeypatch: pytest.MonkeyPatch)^:
>> "%TMPPS%" echo     """When no ENV/.env, fall back to file value."""
>> "%TMPPS%" echo     repo_root = _repo_root_from_here()
>> "%TMPPS%" echo     cfg_path = repo_root / "config.yaml"
>> "%TMPPS%" echo     assert cfg_path.exists()
>> "%TMPPS%" echo
>> "%TMPPS%" echo     monkeypatch.delenv("C04__SIMULATION__DT", raising=False)
>> "%TMPPS%" echo     cfg = load_config(str(cfg_path))
>> "%TMPPS%" echo     assert float(cfg.simulation.dt) > 0.0
>> "%TMPPS%" echo '@
>> "%TMPPS%" echo New-Item -ItemType Directory -Force -Path ^(Split-Path -Parent ^$OutPath^) ^| Out-Null
>> "%TMPPS%" echo Set-Content -Encoding UTF8 -Path ^$OutPath -Value ^$content

REM ---- call PowerShell to write the file ----
powershell -NoProfile -ExecutionPolicy Bypass -File "%TMPPS%" "%CD%\%FILE%" || (echo ERROR: PowerShell write failed & exit /b 1)
del "%TMPPS%" >nul 2>nul

REM ---- commit, push, PR (auto-fork if needed) ----
git add "%FILE%"
git commit -m "%COMMIT%" || (echo Nothing to commit. & exit /b 1)
git push -u origin "%BRANCH%" || (
  echo Push failed; attempting fork...
  gh repo fork --remote || (echo ERROR: fork failed & exit /b 1)
  git push -u origin "%BRANCH%" || (echo ERROR: push to fork failed & exit /b 1)
)

gh pr create --fill --base "%BASE%" --head "%BRANCH%" --web
endlocal
