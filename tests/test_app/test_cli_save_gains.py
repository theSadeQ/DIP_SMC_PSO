#==========================================================================================\\\
#========================== tests/test_app/test_cli_save_gains.py =======================\\\
#==========================================================================================\\\
"""
CLI PSO flow — persistence & logging of saved gains.

Invokes the CLI with --run-pso and --save-gains, asserts the file is
created with numeric gains and stdout contains the save message.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


def _create_fast_config(dst_config: Path):
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
                'boundary_layer': 0.02,
            }
        },
        'pso': {
            'n_particles': 3,
            'bounds': {
                'min': [1.0, 1.0, 1.0, 1.0, 5.0, 0.1],
                'max': [100.0, 100.0, 20.0, 20.0, 150.0, 10.0]
            },
            'w': 0.5,
            'c1': 1.5,
            'c2': 1.5,
            'iters': 3,
            'n_processes': 1,
            'seed': 42,
            'tune': {
                'classical_smc': {'w': 0.5, 'c1': 1.5, 'c2': 1.5}
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
            'n_evals': 1,
            'cart_mass': 0.0,
            'pendulum1_mass': 0.0,
            'pendulum2_mass': 0.0,
            'pendulum1_length': 0.0,
            'pendulum2_length': 0.0,
            'pendulum1_com': 0.0,
            'pendulum2_com': 0.0,
            'pendulum1_inertia': 0.0,
            'pendulum2_inertia': 0.0,
            'gravity': 0.0,
            'cart_friction': 0.0,
            'joint1_friction': 0.0,
            'joint2_friction': 0.0
        },
        'simulation': {
            'duration': 1.0,
            'dt': 0.05,
            'initial_state': [0.0, 0.05, -0.03, 0.0, 0.0, 0.0],
            'use_full_dynamics': False
        },
        'verification': {
            'test_conditions': [],
            'integrators': ['RK45'],
            'criteria': {}
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
                'classical_smc': 100.0
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
    dst_config.write_text(yaml.safe_dump(cfg), encoding="utf-8")


@pytest.mark.slow
def test_cli_save_gains_creates_file_and_logs(tmp_path: Path):
    app = Path("simulate.py").resolve()
    if not app.exists():
        pytest.skip("simulate.py not found; skipping CLI save-gains test.")

    cfg = tmp_path / "config.yaml"
    _create_fast_config(cfg)

    out_path = tmp_path / "saved_gains.json"

    cmd = [
        sys.executable, str(app),
        "--run-pso",
        "--controller", "classical_smc",
        "--config", str(cfg),
        "--seed", "123",
        "--save-gains", str(out_path),
    ]
    # Monkeypatch PSOTuner.optimise to avoid heavy deps (e.g., pyswarms)
    import src.optimizer.pso_optimizer as pso_mod

    class _Dummy:
        def optimise(self):  # noqa: D401
            return {"best_cost": 1.23, "best_pos": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]}

    # Swap class temporarily by launching via a small shim script that patches at runtime
    shim = tmp_path / "shim.py"
    shim.write_text(
        (
            "import runpy, sys\n"
            f"sys.path.insert(0, r'{str(app.parent)}')\n"
            "import src.optimizer.pso_optimizer as p\n"
            "class _Dummy:\n"
            "    def __init__(self, *a, **k): pass\n"
            "    def optimise(self): return {'best_cost':1.23,'best_pos':[1,2,3,4,5,6]}\n"
            "p.PSOTuner = _Dummy\n"
            "sys.argv = ['simulate.py', '--run-pso', '--controller','classical_smc','--config', r'%s','--seed','123','--save-gains', r'%s']\n" % (str(cfg), str(out_path)) +
            "runpy.run_path(r'%s', run_name='__main__')\n" % str(app)
        ),
        encoding="utf-8",
    )
    proc = subprocess.run([sys.executable, str(shim)], cwd=app.parent, capture_output=True, text=True, timeout=90)

    assert proc.returncode == 0, f"CLI failed: {proc.stdout}\n{proc.stderr}"
    assert out_path.exists(), "Gains file should be created"
    assert any("Gains saved to:" in line for line in proc.stdout.splitlines()), proc.stdout

    data = json.loads(out_path.read_text(encoding="utf-8"))
    gains = data.get("classical_smc")
    assert isinstance(gains, list) and gains and all(isinstance(x, (int, float)) for x in gains)
