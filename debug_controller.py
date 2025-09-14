#!/usr/bin/env python3
"""
Debug script to understand controller instability
"""
import numpy as np
from src.controllers.hybrid_adaptive_sta_smc import HybridAdaptiveSTASMC
from src.core.dynamics_full import FullDIPDynamics
from src.core.simulation_runner import run_simulation

def debug_controller():
    # Ultra-minimal controller setup
    from src.core.dynamics import DIPParams
    params = DIPParams.default()
    dyn = FullDIPDynamics(params)

    ctrl = HybridAdaptiveSTASMC(
        gains=[0.2, 1.0, 0.4, 0.8],  # Extremely small gains
        dt=0.001,
        max_force=150.0,
        k1_init=0.01, k2_init=0.01,
        gamma1=0.1, gamma2=0.1,
        dead_zone=0.05,  # Large dead zone
        dynamics_model=dyn,
        gain_leak=0.05,  # Strong leak
        k1_max=5.0, k2_max=5.0,  # Very low limits
        adaptation_sat_threshold=0.3,
        taper_eps=0.5,  # Heavy tapering
        enable_equivalent=False,
        damping_gain=0.05,
        cart_p_gain=0.0,  # No cart recentering
    )

    initial_state = np.array([0.0, 0.1, -0.05, 0.0, 0.0, 0.0])

    try:
        print("Running short simulation (1s)...")
        t, X, U = run_simulation(
            controller=ctrl,
            dynamics_model=dyn,
            sim_time=1.0,
            dt=0.001,
            initial_state=initial_state
        )

        print(f"Final state (1s): {X[-1]}")
        print(f"Final state norm: {np.linalg.norm(X[-1])}")
        print(f"Control range: [{np.min(U):.3f}, {np.max(U):.3f}]")
        print(f"Max |control|: {np.max(np.abs(U)):.3f}")

        # Check if still stable after 1s
        if np.all(np.isfinite(X[-1])) and np.linalg.norm(X[-1]) < 100:
            print("\n1s test passed, trying 5s...")

            t, X, U = run_simulation(
                controller=ctrl,
                dynamics_model=dyn,
                sim_time=5.0,
                dt=0.001,
                initial_state=initial_state
            )

            print(f"Final state (5s): {X[-1]}")
            print(f"Final state norm: {np.linalg.norm(X[-1])}")
            print(f"Control range: [{np.min(U):.3f}, {np.max(U):.3f}]")
            print(f"Max |control|: {np.max(np.abs(U)):.3f}")

        else:
            print("Controller diverged within 1s")

    except Exception as e:
        print(f"Simulation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_controller()