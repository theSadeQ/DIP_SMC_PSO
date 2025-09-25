"""
Script-level test for scripts/reoptimize_controllers.py.
Skips gracefully if the script isn't present.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

try:
    import scripts.reoptimize_controllers as rc
except Exception:
    rc = None  # allow graceful skip

@pytest.mark.skipif(rc is None, reason="scripts/reoptimize_controllers.py not present")
def test_main_script_flow(monkeypatch, tmp_path: Path):
    # Fake optimizer results
    fake_results = {
        "classical_smc": {"best_gains": [1, 2, 3], "best_cost": 0.1, "mean_cost": 0.2, "std_cost": 0.01},
        "sta_smc":       {"best_gains": [4, 5, 6], "best_cost": 0.2, "mean_cost": 0.3, "std_cost": 0.02},
        "adaptive_smc":  {"best_gains": [7, 8, 9], "best_cost": 0.3, "mean_cost": 0.4, "std_cost": 0.03},
    }

    # Mock ControllerReoptimizer
    mock_instance = MagicMock()
    mock_instance.optimize_all_controllers.return_value = fake_results
    mock_instance.results_dir = tmp_path
    mock_class = MagicMock(return_value=mock_instance)
    monkeypatch.setattr(rc, "ControllerReoptimizer", mock_class)

    output_json = tmp_path / "final_gains.json"
    rc.main(["--config", "config.yaml", "--save-json", str(output_json)])

    # constructed with CLI arg
    mock_class.assert_called_once_with(config_path="config.yaml")
    # ran once
    mock_instance.optimize_all_controllers.assert_called_once()
    # JSON saved & matches fake data
    assert output_json.exists()
    saved = json.loads(output_json.read_text())
    assert saved["classical_smc"] == [1, 2, 3]
    assert saved["sta_smc"] == [4, 5, 6]
    assert saved["adaptive_smc"] == [7, 8, 9]
