#///===================================================================\\\
#///============== tests/test_core/test_determinism.py ================\\\
#///===================================================================\\\
"""
Verifies PSO determinism when launched from the CLI entrypoint (simulate.py).

This test runs `python simulate.py --run-pso --controller classical_smc` twice
and asserts that the stdout lines reporting final "Best Cost" and "Best Gains"
are identical across runs.
"""
import subprocess
import sys
import re
import os
import yaml
from pathlib import Path
import pytest


def _find_repo_config() -> Path:
    """Walk up from this test file to locate the repository's config.yaml."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        cand = parent / "config.yaml"
        if cand.exists():
            return cand
    return Path("config.yaml").resolve()


def _create_fast_pso_config(tmp_path: Path) -> Path:
    """
    Create a modified config that forces very fast PSO runs.
    """
    src_cfg = _find_repo_config()
    
    # Load and modify the config
    # On Windows the default text encoding may be cp1252, which can fail
    # when parsing UTF‑8 YAML files.  Explicitly specify UTF‑8 to
    # ensure deterministic cross‑platform behaviour.
    with open(src_cfg, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Force minimal PSO parameters
    config['pso']['n_particles'] = 5
    config['pso']['iters'] = 3
    
    # Reduce simulation duration
    config['simulation']['duration'] = 1.0
    
    # Reduce uncertainty evaluations
    if 'physics_uncertainty' in config:
        config['physics_uncertainty']['n_evals'] = 2
    
    # Write modified config
    dst_cfg = tmp_path / "config.yaml"
    with open(dst_cfg, 'w') as f:
        yaml.safe_dump(config, f)
    
    return dst_cfg


# The seeding logic is now handled inside simulate.py.  The wrapper script is no longer
# required; instead, we run simulate.py directly with a seed argument.

def _create_seeded_wrapper(*args, **kwargs):
    raise RuntimeError("_create_seeded_wrapper is unused in the updated test suite")


BEST_COST_RE = re.compile(r"^\s*Best Cost:\s*(?P<val>[-+Ee0-9\.]+)\s*$")
BEST_GAINS_RE = re.compile(r"^\s*Best Gains:\s*(?P<val>.+)\s*$")


def _find_simulate_py() -> Path:
    """Walk up from this file to locate the repository's simulate.py."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        cand = parent / "simulate.py"
        if cand.exists():
            return cand
    return Path("simulate.py").resolve()


def _run_cli(config: Path, seed: int = 42) -> str:
    """
    Run the CLI directly and return captured stdout as text.
    The seeding logic is handled inside simulate.py; this helper
    simply forwards the seed argument to the CLI entrypoint.
    """
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    app_path = _find_simulate_py()
    cmd = [
        sys.executable,
        str(app_path),
        "--run-pso",
        "--controller", "classical_smc",
        "--config", str(config),
        "--seed", str(seed),
    ]
    proc = subprocess.run(
        cmd,
        cwd=app_path.parent,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=env,
    )
    assert proc.returncode == 0, (
        f"CLI failed (returncode={proc.returncode}).\n"
        f"STDOUT:\n{proc.stdout}\n"
        f"STDERR:\n{proc.stderr}"
    )
    return proc.stdout


def _extract_final_lines(stdout: str) -> str:
    """Extract the final report lines from stdout."""
    best_cost_line = None
    best_gains_line = None
    
    for line in stdout.splitlines():
        if best_cost_line is None and BEST_COST_RE.match(line):
            best_cost_line = line.strip()
        if best_gains_line is None and BEST_GAINS_RE.match(line):
            best_gains_line = line.strip()
    
    assert best_cost_line is not None, f"Could not find 'Best Cost' in stdout:\n{stdout}"
    assert best_gains_line is not None, f"Could not find 'Best Gains' in stdout:\n{stdout}"
    
    return best_cost_line + "\n" + best_gains_line


@pytest.mark.slow
def test_cli_stdout_is_deterministic(tmp_path: Path):
    """Test that running PSO optimization twice produces identical results."""
    cfg = _create_fast_pso_config(tmp_path)
    # Run twice with the same seed via direct invocation
    out1 = _run_cli(cfg, seed=42)
    out2 = _run_cli(cfg, seed=42)
    # Extract the final results
    summary1 = _extract_final_lines(out1)
    summary2 = _extract_final_lines(out2)
    # They should be identical
    assert summary1 == summary2, (
        "CLI stdout differs between runs for final Best Cost/Gains lines.\n\n"
        f"Run #1:\n{summary1}\n\n"
        f"Run #2:\n{summary2}"
    )

#========================================================================================================\\\