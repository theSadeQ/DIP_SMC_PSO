import numpy as np
import pytest
from typing import Any

from src.config import load_config, ControllersConfig, PermissiveControllerConfig
from src.core.simulation_runner import run_simulation
from src.core.dynamics_full import FullDIPDynamics
from src.controllers.factory import build_controller, create_controller


@pytest.fixture
def hybrid_controller(config) -> Any:
    # Conservative, 1 kHz control, modest adaptation
    # Create controller configuration
    ctrl_cfg = {
        "gains": [5.0, 3.0, 5.0, 1.8],  # [c1, λ1, c2, λ2]
        "max_force": 150.0,
        "dt": 0.001,
        "k1_init": 6.0,
        "k2_init": 1.2,
        "gamma1": 0.8,
        "gamma2": 0.4,
        "dead_zone": 0.02,
        "enable_equivalent": True,
    }
    return build_controller(
        "hybrid_adaptive_sta_smc",
        ctrl_cfg,
        allow_unknown=True,
        config=config
    )


# Use full_dynamics fixture from conftest.py


def test_stabilization_and_adaptation(hybrid_controller, full_dynamics) -> None:
    # Attach dynamics (even though u_eq is disabled by default)
    if hasattr(hybrid_controller, "set_dynamics"):
        hybrid_controller.set_dynamics(full_dynamics)

    sim_time = 5.0
    dt = 0.001  # 1 kHz
    initial_state = np.array([0.0, 0.1, -0.05, 0.0, 0.0, 0.0], dtype=float)

    t1, x1, u1 = run_simulation(
        controller=hybrid_controller,
        dynamics_model=full_dynamics,
        sim_time=sim_time,
        dt=dt,
        initial_state=initial_state,
    )

    final_state = x1[-1]
    assert np.all(np.abs(final_state[:3]) < 0.15), (
        f"System did not stabilise. Final state: {final_state[:3]}"
    )

    max_abs_u = float(np.max(np.abs(u1))) if len(u1) else 0.0
    assert max_abs_u <= hybrid_controller.max_force, (
        f"Control output exceeded saturation limit. Max |u|: {max_abs_u}"
    )

    rms_error_pos = float(np.sqrt(np.mean(x1[:, 0] ** 2)))
    rms_error_ang1 = float(np.sqrt(np.mean(x1[:, 1] ** 2)))
    rms_error_ang2 = float(np.sqrt(np.mean(x1[:, 2] ** 2)))
    assert rms_error_pos < 0.12, f"Cart position RMS error too high: {rms_error_pos}"
    assert rms_error_ang1 < 0.12, f"Pendulum 1 RMS error too high: {rms_error_ang1}"
    assert rms_error_ang2 < 0.12, f"Pendulum 2 RMS error too high: {rms_error_ang2}"

    # Reproducibility
    config2 = load_config("config.yaml", allow_unknown=True)
    # Permit extra keys during this construction for reproducibility config
    PermissiveControllerConfig.allow_unknown = True
    ctrl_cfg2 = PermissiveControllerConfig(
        gains=[5.0, 3.0, 5.0, 1.8],
        max_force=150.0,
        dt=dt,
        k1_init=6.0,
        k2_init=1.2,
        gamma1=0.8,
        gamma2=0.4,
        dead_zone=0.02,
        enable_equivalent=True,
    )
    try:
        config2.controllers.hybrid_adaptive_sta_smc = ctrl_cfg2  # type: ignore[attr-defined]
    except Exception:
        config2.controllers = ControllersConfig(
            **{
                **config2.controllers.model_dump(exclude_unset=False),
                "hybrid_adaptive_sta_smc": ctrl_cfg2,
            }
        )
    controller2 = create_controller("hybrid_adaptive_sta_smc", config=config2)
    if hasattr(controller2, "set_dynamics"):
        controller2.set_dynamics(full_dynamics)

    t2, x2, u2 = run_simulation(
        controller=controller2,
        dynamics_model=full_dynamics,
        sim_time=sim_time,
        dt=dt,
        initial_state=initial_state,
    )
    np.testing.assert_allclose(x1, x2, atol=2e-2, err_msg="Simulation results are not reproducible.")

    # Adaptation: gains increase, then slow
    state_vars = hybrid_controller.initialize_state()
    hist = hybrid_controller.initialize_history()
    for i in range(len(u1)):
        ret = hybrid_controller.compute_control(x1[i], state_vars, hist)
        try:
            _, state_vars, hist = ret[:3]
        except Exception:
            _, state_vars, hist = ret
    k1_hist = np.array(hist["k1"], dtype=float)
    k2_hist = np.array(hist["k2"], dtype=float)
    assert k1_hist[-1] > hybrid_controller.k1_init
    assert k2_hist[-1] > hybrid_controller.k2_init

    mid = len(k1_hist) // 2
    change_first = float(np.mean(np.diff(k1_hist[:mid])))
    change_second = float(np.mean(np.diff(k1_hist[mid:])))
    assert change_second < change_first
