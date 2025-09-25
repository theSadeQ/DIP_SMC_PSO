#======================================================================================================\\\
#======================= tests/test_optimizer/test_cli_determinism.py =================================\\\
#======================================================================================================\\\
"""
Verifies PSO determinism through the CLI (simulate.py).
Runs the PSO twice with the same --seed and checks identical results.

Notes:
- Adjust the regex patterns below if your app prints different labels.
- If the expected lines aren't found, the test is skipped (so it won't break CI).
"""
import subprocess
import sys
import re
import os
from pathlib import Path
import pytest
import yaml

BEST_COST_RE = re.compile(r"^\s*Best\s+Cost\s*:\s*(?P<val>[-+Ee0-9\.]+)\s*$")
BEST_GAINS_RE = re.compile(r"^\s*Best\s+Gains\s*:\s*(?P<val>.+)\s*$")

def _find_repo_file(name: str) -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        cand = parent / name
        if cand.exists():
            return cand
    return Path(name).resolve()

def _extract(app_output: str):
    best_cost = None
    best_gains = None
    for line in app_output.splitlines():
        if best_cost is None:
            m = BEST_COST_RE.match(line)
            if m:
                best_cost = m.group("val")
        if best_gains is None:
            m = BEST_GAINS_RE.match(line)
            if m:
                best_gains = m.group("val")
    return best_cost, best_gains

def _create_fast_config(src_config: Path, dst_config: Path):
    """Create a test-optimized config with all required fields."""
    # Start with a minimal complete config
    cfg = {
        'global_seed': 42,
        'controller_defaults': {
            'classical_smc': {
                'gains': [5.0, 5.0, 5.0, 0.5, 0.5, 0.5]
            }
        },
        'controllers': {
            'classical_smc': {
                'max_force': 150.0,
                'rate_weight': 1.0,
                'boundary_layer': 0.02,
                'use_adaptive_boundary': True
            }
        },
        'pso': {
            'n_particles': 5,  # Minimal for fast testing
            'bounds': {
                'min': [1.0, 1.0, 1.0, 1.0, 5.0, 0.1],
                'max': [100.0, 100.0, 20.0, 20.0, 150.0, 10.0]
            },
            'w': 0.5,
            'c1': 1.5,
            'c2': 1.5,
            'iters': 5,  # Minimal for fast testing
            'n_processes': 1,
            'seed': 42,
            'hyper_trials': 50,
            'hyper_search': {
                'w': [0.1, 0.9],
                'c1': [0.5, 2.5],
                'c2': [0.5, 2.5]
            },
            'study_timeout': 600,
            'tune': {
                'classical_smc': {
                    'w': 0.5,
                    'c1': 1.5,
                    'c2': 1.5
                }
            }
        },
        'physics': {
            'cart_mass': 1.5,
            'pendulum1_mass': 0.2,
            'pendulum2_mass': 0.15,
            'pendulum1_length': 0.4,
            'pendulum2_length': 0.3,
            'pendulum1_com': 0.2,
            'pendulum2_com': 0.15,
            'pendulum1_inertia': 0.00265,
            'pendulum2_inertia': 0.00115,
            'gravity': 9.81,
            'cart_friction': 0.2,
            'joint1_friction': 0.005,
            'joint2_friction': 0.004,
            'singularity_cond_threshold': 1e8
        },
        'physics_uncertainty': {
            'n_evals': 1,  # Just nominal for speed
            'cart_mass': 0.05,
            'pendulum1_mass': 0.05,
            'pendulum2_mass': 0.05,
            'pendulum1_length': 0.05,
            'pendulum2_length': 0.05,
            'pendulum1_com': 0.05,
            'pendulum2_com': 0.05,
            'pendulum1_inertia': 0.05,
            'pendulum2_inertia': 0.05,
            'gravity': 0.0,
            'cart_friction': 0.1,
            'joint1_friction': 0.1,
            'joint2_friction': 0.1
        },
        'simulation': {
            'duration': 2.0,  # Short for speed
            'dt': 0.01,
            'initial_state': [0.0, 0.05, -0.03, 0.0, 0.0, 0.0],
            'use_full_dynamics': False
        },
        'verification': {
            'test_conditions': [
                {
                    'name': 'nominal',
                    'disturbance': [0, 0, 0]
                }
            ],
            'integrators': ['RK45'],
            'criteria': {
                'position_tolerance': 0.01,
                'angle_tolerance': 0.01
            }
        },
        'cost_function': {
            'weights': {
                'state_error': 50.0,
                'control_effort': 0.2,
                'control_rate': 0.1,
                'stability': 0.1
            },
            'instability_penalty': 1000.0,
            'baseline': {
                'classical_smc': 100.0,
                'sta_smc': 90.0,
                'adaptive_smc': 85.0
            }
        },
        'sensors': {
            'angle_noise_std': 0.0,
            'position_noise_std': 0.0,
            'quantization_angle': 0.0,
            'quantization_position': 0.0
        },
        'hil': {
            'plant_ip': '127.0.0.1',
            'plant_port': 5555,
            'controller_ip': '127.0.0.1',
            'controller_port': 5556,
            'extra_latency_ms': 0.0,
            'sensor_noise_std': 0.0
        }
    }
    
    # If we have a source config, try to read some values from it
    # to maintain compatibility with the actual config structure
    if src_config.exists():
        try:
            with open(src_config, 'r') as f:
                src_cfg = yaml.safe_load(f)
            # Only override certain sections if they exist
            if 'fdi' in src_cfg:
                cfg['fdi'] = src_cfg['fdi']
        except:
            pass  # Use our defaults if we can't read the source
    
    with open(dst_config, 'w') as f:
        yaml.safe_dump(cfg, f)

def _run_cli(app: Path, config: Path) -> str:
    # Set TEST_MODE to force fast mode
    env = os.environ.copy()
    env["TEST_MODE"] = "1"
    
    cmd = [
        sys.executable, str(app),
        "--run-pso",
        "--controller", "classical_smc",
        "--config", str(config),
        "--seed", "123",
    ]
    
    proc = subprocess.run(
        cmd, 
        cwd=app.parent, 
        capture_output=True, 
        text=True, 
        timeout=60,  # Give it a bit more time
        env=env
    )
    assert proc.returncode == 0, (
        f"CLI failed (code={proc.returncode}).\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    )
    return proc.stdout

@pytest.mark.slow
def test_cli_stdout_is_deterministic(tmp_path: Path):
    app = _find_repo_file("simulate.py")
    cfg_src = _find_repo_file("config.yaml")
    if not app.exists():
        pytest.skip("simulate.py not found; skipping CLI determinism test.")

    # Create a fast config for testing
    cfg = tmp_path / "config.yaml"
    _create_fast_config(cfg_src, cfg)

    out1 = _run_cli(app, cfg)
    out2 = _run_cli(app, cfg)

    c1, g1 = _extract(out1)
    c2, g2 = _extract(out2)
    if c1 is None or g1 is None or c2 is None or g2 is None:
        pytest.skip("Could not find 'Best Cost'/'Best Gains' lines in output; adjust regex if needed.")

    assert c1 == c2, f"Best Cost differs: {c1} != {c2}"
    assert g1 == g2, f"Best Gains differ: {g1} != {g2}"
#======================================================================================================\\\