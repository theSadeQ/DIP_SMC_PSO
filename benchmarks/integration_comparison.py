# benchmarks/integration_comparison.py============================================\\\
#
"""
Compares the performance and accuracy of different numerical integration methods
for the double inverted pendulum dynamics, specifically Euler, RK4, and RK45.
"""

import sys
import time
from typing import Any, Dict

import numpy as np
import pytest
from scipy.integrate import solve_ivp

# Note: For a distributable package, relative imports or proper packaging
# (pyproject.toml) would be preferred over manipulating sys.path.
sys.path.append("..")

from src.config import load_config
from src.controllers.classic_smc import ClassicSMC
from src.core.dynamics import (
    DIPDynamics,
    DoubleInvertedPendulum,
    step_euler_numba,
    step_rk4_numba,
)


class IntegrationBenchmark:
    """
    A test suite for benchmarking numerical integration methods.

    This class sets up a standard simulation scenario and provides methods
    to run it using different fixed-step and adaptive-step integrators.
    """

    # Define default gains as a constant for clarity
    DEFAULT_GAINS = np.array([10.0, 5.0, 3.0, 2.0, 50.0])

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initializes the benchmark with dynamics and controller from a config file.
        """
        cfg = load_config(config_path)
        self.physics = cfg.physics.model_dump()
        self.dynamics = DIPDynamics(self.physics)
        self.controller = ClassicSMC(self.DEFAULT_GAINS, max_force=150.0)
        self.x0 = np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0])

    def euler_integrate(
        self, sim_time: float, dt: float, use_controller: bool = True
    ) -> Dict[str, Any]:
        """
        Runs a simulation using the fast, Numba-based Euler method.

        Args:
            sim_time: The total duration of the simulation in seconds.
            dt: The time step for the fixed-step integrator.
            use_controller: If True, runs in closed-loop mode with the controller;
                            if False, runs open-loop with u=0.

        Returns:
            A dictionary containing the simulation results.
        """
        n_steps = int(sim_time / dt) + 1
        t = np.linspace(0, sim_time, n_steps)
        states = np.zeros((n_steps, 6))
        controls = np.zeros(n_steps)
        states[0] = self.x0.copy()

        # --- Initialize Controller (if needed) ---
        if use_controller:
            (last_u,) = self.controller.initialize_state()
            history = self.controller.initialize_history()

        start_time = time.time()

        # --- Simulation Loop ---
        for i in range(n_steps - 1):
            if use_controller:
                u, last_u, history = self.controller.compute_control(
                    states[i], last_u, history
                )
            else:
                u = 0.0
            controls[i] = u
            states[i + 1] = step_euler_numba(states[i], u, dt, self.dynamics.params)

        elapsed = time.time() - start_time
        return {
            "t": t,
            "states": states,
            "controls": controls,
            "time": elapsed,
            "method": "Euler",
        }

    def rk4_integrate(
        self, sim_time: float, dt: float, use_controller: bool = True
    ) -> Dict[str, Any]:
        """
        Runs a simulation using the fast, Numba-based RK4 method.

        Args:
            sim_time: The total duration of the simulation in seconds.
            dt: The time step for the fixed-step integrator.
            use_controller: If True, runs in closed-loop; if False, runs open-loop.

        Returns:
            A dictionary containing the simulation results.
        """
        n_steps = int(sim_time / dt) + 1
        t = np.linspace(0, sim_time, n_steps)
        states = np.zeros((n_steps, 6))
        controls = np.zeros(n_steps)
        states[0] = self.x0.copy()

        # --- Initialize Controller (if needed) ---
        if use_controller:
            (last_u,) = self.controller.initialize_state()
            history = self.controller.initialize_history()

        start_time = time.time()

        # --- Simulation Loop ---
        for i in range(n_steps - 1):
            if use_controller:
                u, last_u, history = self.controller.compute_control(
                    states[i], last_u, history
                )
            else:
                u = 0.0
            controls[i] = u
            states[i + 1] = step_rk4_numba(states[i], u, dt, self.dynamics.params)

        elapsed = time.time() - start_time
        return {
            "t": t,
            "states": states,
            "controls": controls,
            "time": elapsed,
            "method": "RK4",
        }

    def rk45_integrate(self, sim_time: float, rtol: float = 1e-8) -> Dict[str, Any]:
        """
        Runs an open-loop simulation using SciPy's adaptive RK45 solver.

        Note: Closed-loop mode is not supported for this adaptive solver.

        Args:
            sim_time: The total duration of the simulation.
            rtol: The relative tolerance for the adaptive-step solver.

        Returns:
            A dictionary containing the simulation results.
        """
        start_time = time.time()

        # solve_ivp requires a function of signature f(t, y).
        def open_loop_rhs(t, y):
            return self.dynamics._rhs(t, y, u=0.0)

        sol = solve_ivp(
            fun=open_loop_rhs,
            t_span=(0, sim_time),
            y0=self.x0,
            method="RK45",
            rtol=rtol,
            atol=1e-10,
            dense_output=True,
        )

        elapsed = time.time() - start_time
        controls = np.zeros(sol.y.shape[1])  # Controls are zero since it's open-loop

        return {
            "t": sol.t,
            "states": sol.y.T,
            "controls": controls,
            "time": elapsed,
            "method": "RK45",
            "nfev": sol.nfev,
        }

    def calculate_energy_drift(self, result: Dict[str, Any]) -> np.ndarray:
        """
        Calculates the cumulative drift in the system's total mechanical energy.
        """
        dynamics = DoubleInvertedPendulum(self.physics)
        energies = np.array(
            [
                dynamics.kinetic_energy(state) + dynamics.potential_energy(state)
                for state in result["states"]
            ]
        )
        return energies - energies[0]


@pytest.fixture
def benchmark() -> IntegrationBenchmark:
    """Provides a reusable instance of the IntegrationBenchmark class for tests."""
    return IntegrationBenchmark()


def test_rk4_reduces_euler_drift(benchmark: IntegrationBenchmark):
    """
    Verify that RK4 is more accurate than Euler by showing less energy drift in open-loop mode.
    """
    # Run in open-loop for a fair comparison of numerical error.
    res_euler = benchmark.euler_integrate(sim_time=5.0, dt=0.01, use_controller=False)
    res_rk4 = benchmark.rk4_integrate(sim_time=5.0, dt=0.01, use_controller=False)

    drift_euler = benchmark.calculate_energy_drift(res_euler)
    drift_rk4 = benchmark.calculate_energy_drift(res_rk4)

    mean_drift_euler = np.mean(np.abs(drift_euler))
    mean_drift_rk4 = np.mean(np.abs(drift_rk4))

    assert (
        mean_drift_rk4 < mean_drift_euler
    ), f"RK4 mean drift ({mean_drift_rk4:.4f}) was not lower than Euler drift ({mean_drift_euler:.4f})"


def test_rk45_executes_and_counts_evals(benchmark: IntegrationBenchmark):
    """Verify that the SciPy RK45 solver runs and reports its function evaluations."""
    res_rk45 = benchmark.rk45_integrate(sim_time=5.0, rtol=1e-8)
    assert "nfev" in res_rk45 and isinstance(
        res_rk45["nfev"], int
    ), "RK45 result dictionary is missing an integer 'nfev' field"
    assert (
        res_rk45["nfev"] > 0
    ), "RK45 performed no function evaluations, which is unexpected."


def test_energy_conservation_bound(benchmark: IntegrationBenchmark):
    """
    Verify that the RK4 integrator conserves energy within a bound in a frictionless, open-loop simulation.
    """
    # Override friction to zero to create a Hamiltonian system
    benchmark.physics["cart_friction"] = 0.0
    benchmark.physics["joint1_friction"] = 0.0
    benchmark.physics["joint2_friction"] = 0.0

    # Reinitialize dynamics with updated physics
    benchmark.dynamics = DIPDynamics(benchmark.physics)

    # Run a long open-loop simulation
    res_rk4 = benchmark.rk4_integrate(sim_time=10.0, dt=0.01, use_controller=False)

    # Calculate total energies using the model's total_energy method
    energies = np.array(
        [benchmark.dynamics.total_energy(state) for state in res_rk4["states"]]
    )

    initial_energy = energies[0]
    drift = np.abs(energies - initial_energy)
    max_drift = np.max(drift)

    # Assert max drift < 1% of initial energy
    tolerance = 0.01 * initial_energy
    assert (
        max_drift < tolerance
    ), f"Max energy drift {max_drift:.6f} exceeds tolerance {tolerance:.6f}"


# ===========================================================================================================\\\
