@'
param(
  [string]$Branch = "c04/tests-integration",
  [string]$Base   = "main",
  [string]$File   = "tests/test_integration/test_settings_precedence.py",
  [string]$Commit = "tests: add settings precedence integration test"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Run($cmd) {
  & $env:ComSpec /c $cmd
  if ($LASTEXITCODE -ne 0) { throw "Command failed: $cmd" }
}

# sanity checks
if (-not (Test-Path ".git")) { throw "Run this from the repository root (where .git exists)." }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git not found in PATH." }
if (-not (Get-Command gh  -ErrorAction SilentlyContinue)) { throw "GitHub CLI (gh) not found in PATH." }

# stash local changes so rebase won't fail
& git diff --quiet
if ($LASTEXITCODE -ne 0) { Run 'git stash push -m "auto-stash for new test"' }

# sync base and branch
Run "git fetch --all"
Run "git checkout $Base"
Run "git pull --rebase"
# create branch if missing, otherwise checkout
& git checkout -b $Branch
if ($LASTEXITCODE -ne 0) { Run "git checkout $Branch" }

# ensure directory exists
$TargetDir = Split-Path -Parent $File
if ($TargetDir -and -not (Test-Path $TargetDir)) { New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null }

# write the test file
$testContent = @'
import os
from pathlib import Path
import pytest

from src.config import load_config


def _repo_root_from_here() -> Path:
    """Resolve the repository root relative to this test file location."""
    here = Path(__file__).resolve()
    return here.parents[2]


def test_env_overrides_file(monkeypatch: pytest.MonkeyPatch):
    """ENV should override values coming from the config file."""
    repo_root = _repo_root_from_here()
    cfg_path = repo_root / "config.yaml"
    assert cfg_path.exists()

    monkeypatch.setenv("C04__SIMULATION__DT", "0.005")
    cfg = load_config(str(cfg_path))
    assert float(cfg.simulation.dt) == pytest.approx(0.005, rel=0, abs=1e-12)

    monkeypatch.delenv("C04__SIMULATION__DT", raising=False)


def test_dotenv_overrides_file_but_not_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """.env should override file, but real ENV must still have highest precedence."""
    repo_root = _repo_root_from_here()
    cfg_path = repo_root / "config.yaml"
    assert cfg_path.exists()

    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("C04__SIMULATION__DT=0.010\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("C04__SIMULATION__DT", "0.003")
    cfg = load_config(str(cfg_path))
    assert float(cfg.simulation.dt) == pytest.approx(0.003, rel=0, abs=1e-12)

    monkeypatch.delenv("C04__SIMULATION__DT", raising=False)
    cfg = load_config(str(cfg_path))
    assert float(cfg.simulation.dt) == pytest.approx(0.010, rel=0, abs=1e-12)


def test_file_used_when_no_env_or_dotenv(monkeypatch: pytest.MonkeyPatch):
    """When no ENV/.env, fall back to file value."""
    repo_root = _repo_root_from_here()
    cfg_path = repo_root / "config.yaml"
    assert cfg_path.exists()

    monkeypatch.delenv("C04__SIMULATION__DT", raising=False)
    cfg = load_config(str(cfg_path))
    assert float(cfg.simulation.dt) > 0.0
'@

Set-Content -LiteralPath $File -Encoding UTF8 -Value $testContent

# commit & push (fork fallback if needed)
Run "git add `"$File`""
& git commit -m "$Commit"
if ($LASTEXITCODE -ne 0) { throw "Nothing to commit (did the file write succeed?)" }

& git push -u origin $Branch
if ($LASTEXITCODE -ne 0) {
  Write-Host "Push failed; attempting fork..." -ForegroundColor Yellow
  Run "gh repo fork --remote"
  Run "git push -u origin $Branch"
}

# open PR
Run "gh pr create --fill --base $Base --head $Branch --web"
'@ | Set-Content -LiteralPath .\Add-SettingsPrecedenceTest.ps1 -Encoding UTF8
