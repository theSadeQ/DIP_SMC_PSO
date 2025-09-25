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
