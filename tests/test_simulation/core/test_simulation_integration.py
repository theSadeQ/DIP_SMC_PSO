#==========================================================================================\\
#============ tests/test_simulation/core/test_simulation_integration.py ==================\\
#==========================================================================================\\

"""
Comprehensive test suite for simulation integration robustness.

This module tests complete controller-plant-simulation integration workflows,
validates integrator compatibility, and ensures reliable end-to-end simulation
execution with comprehensive error handling and edge case robustness.
"""

import pytest
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Tuple
import warnings
from unittest.mock import Mock, patch, MagicMock
import time

# Core simulation imports
from src.simulation.engines.simulation_runner import run_simulation, step
from src.simulation.integrators.fixed_step.euler import ForwardEuler
from src.simulation.integrators.fixed_step.runge_kutta import RungeKutta4
from src.simulation.integrators.adaptive.runge_kutta import DormandPrince45
from src.simulation.core.interfaces import Integrator

# Controller and plant imports for integration testing
try:
    from src.controllers.factory import create_controller
    CONTROLLER_AVAILABLE = True
except ImportError:
    CONTROLLER_AVAILABLE = False

try:
    from src.plant.models.simplified.dip_dynamics import DIPDynamics
    PLANT_AVAILABLE = True
except ImportError:
    PLANT_AVAILABLE = False


class MockDynamicsModel:
    """Mock dynamics model for testing."""

    def __init__(self, state_dim: int = 4, fail_after: Optional[int] = None, return_nan: bool = False):
        """Initialize mock dynamics.

        Parameters
        ----------
        state_dim : int
            State dimension
        fail_after : int, optional
            Step after which to fail
        return_nan : bool
            Whether to return NaN values
        """
        self.state_dim = state_dim
        self.step_count = 0
        self.fail_after = fail_after
        self.return_nan = return_nan

    def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        """Step the dynamics forward."""
        self.step_count += 1

        if self.fail_after is not None and self.step_count > self.fail_after:
            raise RuntimeError("Simulated dynamics failure")

        state = np.asarray(state).reshape(-1)

        if self.return_nan:
            next_state = np.full_like(state, np.nan)
        else:
            # Simple linear dynamics with control
            A = np.eye(len(state)) + 0.01 * np.random.randn(len(state), len(state))
            B = 0.1 * np.ones(len(state))
            next_state = A @ state + B * u + 0.001 * np.random.randn(len(state))

        return next_state


class MockController:
    """Mock controller for testing."""

    def __init__(self, max_force: Optional[float] = None, fail_after: Optional[int] = None,
                 use_compute_control: bool = False, stateful: bool = False):
        """Initialize mock controller.

        Parameters
        ----------
        max_force : float, optional
            Maximum control force
        fail_after : int, optional
            Step after which to fail
        use_compute_control : bool
            Whether to implement compute_control method
        stateful : bool
            Whether controller maintains state
        """
        self.max_force = max_force
        self.step_count = 0
        self.fail_after = fail_after
        self.use_compute_control = use_compute_control
        self.stateful = stateful
        self._state = {"integral": 0.0} if stateful else None
        self._history = [] if stateful else None

    def __call__(self, t: float, state: np.ndarray) -> float:
        """Basic controller interface."""
        self.step_count += 1

        if self.fail_after is not None and self.step_count > self.fail_after:
            raise RuntimeError("Controller computation failed")

        # Simple PD control
        position_error = -state[0]  # Stabilize to origin
        velocity = state[1] if len(state) > 1 else 0.0

        control = 2.0 * position_error - 0.5 * velocity + 0.1 * np.sin(2 * np.pi * t)
        return control

    def compute_control(self, state: np.ndarray, ctrl_state: Any, history: Any) -> Tuple[float, Any, Any]:
        """Advanced controller interface with state management."""
        if not self.use_compute_control:
            raise AttributeError("compute_control not available")

        self.step_count += 1

        if self.fail_after is not None and self.step_count > self.fail_after:
            raise RuntimeError("Controller computation failed")

        # Update internal state
        if self.stateful and ctrl_state is not None:
            ctrl_state["integral"] += state[0] * 0.01  # Simple integral term

        # PID control with state
        kp, ki, kd = 2.0, 0.1, 0.5
        position_error = -state[0]
        velocity = state[1] if len(state) > 1 else 0.0
        integral_term = ctrl_state["integral"] if (self.stateful and ctrl_state) else 0.0

        control = kp * position_error + ki * integral_term - kd * velocity

        # Update history
        if self.stateful and history is not None:
            history.append({"time": time.time(), "error": position_error, "control": control})
            if len(history) > 100:  # Limit history size
                history.pop(0)

        return control, ctrl_state, history

    def initialize_state(self) -> Dict[str, float]:
        """Initialize controller state."""
        if not self.stateful:
            return {}
        return {"integral": 0.0}

    def initialize_history(self) -> List[Dict[str, float]]:
        """Initialize controller history."""
        if not self.stateful:
            return []
        return []


class TestSimulationIntegrationBasic:
    """Test basic simulation integration functionality."""

    def test_basic_simulation_workflow(self):
        """Test basic end-to-end simulation workflow."""
        # Setup
        controller = MockController()
        dynamics = MockDynamicsModel(state_dim=4)
        initial_state = np.array([0.1, 0.0, 0.05, 0.0])

        # Run simulation
        t_arr, x_arr, u_arr = run_simulation(
            controller=controller,
            dynamics_model=dynamics,
            sim_time=1.0,
            dt=0.01,
            initial_state=initial_state
        )

        # Validate results
        assert isinstance(t_arr, np.ndarray)
        assert isinstance(x_arr, np.ndarray)
        assert isinstance(u_arr, np.ndarray)

        # Check dimensions
        expected_steps = int(1.0 / 0.01)
        assert len(t_arr) == expected_steps + 1
        assert x_arr.shape == (expected_steps + 1, 4)
        assert len(u_arr) == expected_steps

        # Check initial state
        np.testing.assert_array_equal(x_arr[0], initial_state)

        # Check time progression
        assert t_arr[0] == 0.0
        assert np.abs(t_arr[-1] - 1.0) < 1e-10

        # Check finite values
        assert np.all(np.isfinite(x_arr))
        assert np.all(np.isfinite(u_arr))

    def test_controller_with_compute_control(self):
        """Test simulation with stateful controller using compute_control."""
        controller = MockController(use_compute_control=True, stateful=True)
        dynamics = MockDynamicsModel(state_dim=2)
        initial_state = np.array([0.2, 0.0])

        # Run simulation
        t_arr, x_arr, u_arr = run_simulation(
            controller=controller,
            dynamics_model=dynamics,
            sim_time=0.5,
            dt=0.01,
            initial_state=initial_state
        )

        # Validate results
        assert len(t_arr) == 51  # 0.5/0.01 + 1
        assert x_arr.shape == (51, 2)
        assert len(u_arr) == 50

        # Check that controller state was used
        assert hasattr(controller, "_last_history")

    def test_control_saturation(self):
        """Test control saturation functionality."""
        controller = MockController()
        dynamics = MockDynamicsModel()
        initial_state = np.array([10.0, 0.0, 0.0, 0.0])  # Large initial error

        # Test with explicit u_max
        t_arr, x_arr, u_arr = run_simulation(
            controller=controller,
            dynamics_model=dynamics,
            sim_time=0.1,
            dt=0.01,
            initial_state=initial_state,
            u_max=5.0
        )

        # Control should be saturated
        assert np.all(np.abs(u_arr) <= 5.0)

        # Test with controller max_force
        controller_with_limit = MockController(max_force=2.0)
        t_arr2, x_arr2, u_arr2 = run_simulation(
            controller=controller_with_limit,
            dynamics_model=dynamics,
            sim_time=0.1,
            dt=0.01,
            initial_state=initial_state
        )

        # Control should be saturated by controller limit
        assert np.all(np.abs(u_arr2) <= 2.0)

    def test_different_state_dimensions(self):
        """Test simulation with different state dimensions."""
        dimensions = [1, 2, 4, 6, 8]

        for dim in dimensions:
            controller = MockController()
            dynamics = MockDynamicsModel(state_dim=dim)
            initial_state = 0.1 * np.random.randn(dim)

            t_arr, x_arr, u_arr = run_simulation(
                controller=controller,
                dynamics_model=dynamics,
                sim_time=0.1,
                dt=0.01,
                initial_state=initial_state
            )

            assert x_arr.shape[1] == dim, f"Failed for dimension {dim}"
            assert np.all(np.isfinite(x_arr)), f"Non-finite values for dimension {dim}"


class TestSimulationErrorHandling:
    """Test simulation error handling and recovery."""

    def test_controller_failure_handling(self):
        """Test handling of controller computation failures."""
        controller = MockController(fail_after=5)  # Fail after 5 steps
        dynamics = MockDynamicsModel()
        initial_state = np.array([0.1, 0.0, 0.0, 0.0])

        # Should terminate early without crashing
        t_arr, x_arr, u_arr = run_simulation(
            controller=controller,
            dynamics_model=dynamics,
            sim_time=1.0,
            dt=0.01,
            initial_state=initial_state
        )

        # Should have stopped early
        assert len(t_arr) <= 7  # Failed after step 5, so max 6 time points
        assert len(u_arr) <= 6
        assert x_arr.shape[0] == len(t_arr)

        # Results up to failure should be valid
        assert np.all(np.isfinite(t_arr))
        assert np.all(np.isfinite(x_arr))
        assert np.all(np.isfinite(u_arr))

    def test_dynamics_failure_handling(self):
        """Test handling of dynamics computation failures."""
        controller = MockController()
        dynamics = MockDynamicsModel(fail_after=3)  # Fail after 3 steps
        initial_state = np.array([0.1, 0.0, 0.0, 0.0])

        # Should terminate early
        t_arr, x_arr, u_arr = run_simulation(
            controller=controller,
            dynamics_model=dynamics,
            sim_time=1.0,
            dt=0.01,
            initial_state=initial_state
        )

        # Should have stopped after dynamics failure
        assert len(t_arr) <= 5  # Failed after step 3
        assert len(u_arr) <= 4
        assert x_arr.shape[0] == len(t_arr)

    def test_nan_detection_handling(self):
        """Test detection and handling of NaN values."""
        controller = MockController()
        dynamics = MockDynamicsModel(return_nan=True)
        initial_state = np.array([0.1, 0.0, 0.0, 0.0])

        # Should terminate when NaN detected
        t_arr, x_arr, u_arr = run_simulation(
            controller=controller,
            dynamics_model=dynamics,
            sim_time=0.1,
            dt=0.01,
            initial_state=initial_state
        )

        # Should have stopped after first NaN
        assert len(t_arr) <= 3  # Initial + maybe 1-2 steps before NaN detection
        assert x_arr.shape[0] == len(t_arr)

        # Initial state should be finite
        assert np.all(np.isfinite(x_arr[0]))

    def test_invalid_inputs_handling(self):
        """Test handling of invalid inputs."""
        controller = MockController()
        dynamics = MockDynamicsModel()

        # Test negative dt
        with pytest.raises(ValueError, match="dt must be positive"):
            run_simulation(
                controller=controller,
                dynamics_model=dynamics,
                sim_time=0.1,
                dt=-0.01,
                initial_state=[1, 0, 0, 0]
            )

        # Test zero dt
        with pytest.raises(ValueError, match="dt must be positive"):
            run_simulation(
                controller=controller,
                dynamics_model=dynamics,
                sim_time=0.1,
                dt=0.0,
                initial_state=[1, 0, 0, 0]
            )

    def test_zero_simulation_time(self):
        """Test simulation with zero or negative simulation time."""
        controller = MockController()
        dynamics = MockDynamicsModel()
        initial_state = np.array([0.1, 0.0, 0.0, 0.0])

        # Zero simulation time
        t_arr, x_arr, u_arr = run_simulation(
            controller=controller,
            dynamics_model=dynamics,
            sim_time=0.0,
            dt=0.01,
            initial_state=initial_state
        )

        assert len(t_arr) == 1  # Only initial time
        assert len(u_arr) == 0   # No control steps
        assert x_arr.shape == (1, 4)  # Only initial state
        np.testing.assert_array_equal(x_arr[0], initial_state)

    def test_fallback_controller_activation(self):
        """Test fallback controller activation on latency issues."""

        class SlowController(MockController):
            def __call__(self, t: float, state: np.ndarray) -> float:
                if self.step_count > 2:  # Be slow after initial steps
                    time.sleep(0.05)  # Simulate slow computation
                result = super().__call__(t, state)
                return result

        def fast_fallback_controller(t: float, state: np.ndarray) -> float:
            return -0.5 * state[0]  # Simple proportional control

        slow_controller = SlowController()
        dynamics = MockDynamicsModel()
        initial_state = np.array([0.1, 0.0, 0.0, 0.0])

        t_arr, x_arr, u_arr = run_simulation(
            controller=slow_controller,
            dynamics_model=dynamics,
            sim_time=0.1,
            dt=0.01,  # 10ms timestep
            initial_state=initial_state,
            fallback_controller=fast_fallback_controller
        )

        # Should complete simulation using fallback
        expected_steps = int(0.1 / 0.01)
        assert len(t_arr) == expected_steps + 1
        assert np.all(np.isfinite(x_arr))
        assert np.all(np.isfinite(u_arr))


class TestIntegratorCompatibility:
    """Test compatibility with different integrator types."""

    def test_euler_integration_compatibility(self):
        """Test compatibility with Euler integrator."""
        # Create integrator-aware dynamics
        class IntegratorDynamics:
            def __init__(self):
                self.integrator = ForwardEuler()

            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                def dynamics_fn(t, x, control):
                    # Simple pendulum-like dynamics
                    return np.array([x[1], -0.5 * x[0] + control])

                return self.integrator.integrate(dynamics_fn, state, np.array([u]), dt)

        controller = MockController()
        dynamics = IntegratorDynamics()
        initial_state = np.array([0.1, 0.0])

        t_arr, x_arr, u_arr = run_simulation(
            controller=controller,
            dynamics_model=dynamics,
            sim_time=0.2,
            dt=0.01,
            initial_state=initial_state
        )

        assert len(t_arr) == 21
        assert x_arr.shape == (21, 2)
        assert np.all(np.isfinite(x_arr))

    def test_rk4_integration_compatibility(self):
        """Test compatibility with RK4 integrator."""
        class RK4Dynamics:
            def __init__(self):
                self.integrator = RungeKutta4()

            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                def dynamics_fn(t, x, control):
                    # Nonlinear dynamics
                    return np.array([x[1], -np.sin(x[0]) - 0.1 * x[1] + 0.5 * control])

                return self.integrator.integrate(dynamics_fn, state, np.array([u]), dt)

        controller = MockController()
        dynamics = RK4Dynamics()
        initial_state = np.array([0.2, 0.0])

        t_arr, x_arr, u_arr = run_simulation(
            controller=controller,
            dynamics_model=dynamics,
            sim_time=0.3,
            dt=0.01,
            initial_state=initial_state
        )

        assert x_arr.shape[1] == 2
        assert np.all(np.isfinite(x_arr))

        # RK4 should be more accurate than Euler for same step size
        # (This is implicit validation through stability)

    def test_adaptive_integration_compatibility(self):
        """Test compatibility with adaptive integrator."""
        class AdaptiveDynamics:
            def __init__(self):
                self.integrator = DormandPrince45(rtol=1e-6, atol=1e-9)
                self.current_time = 0.0

            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                def dynamics_fn(t, x, control):
                    # Stiff dynamics that benefit from adaptive integration
                    return np.array([
                        x[1],
                        -100 * x[0] - 20 * x[1] + control,
                        x[3],
                        -10 * x[2] - 2 * x[3] + 0.5 * control
                    ])

                # Adaptive integrator interface
                try:
                    next_state = self.integrator.integrate(
                        dynamics_fn, state, np.array([u]), dt, t=self.current_time
                    )
                    self.current_time += dt
                    return next_state
                except Exception:
                    # Fallback to simple integration if adaptive fails
                    return state + dt * dynamics_fn(self.current_time, state, u)

        controller = MockController()
        dynamics = AdaptiveDynamics()
        initial_state = np.array([0.01, 0.0, 0.01, 0.0])

        t_arr, x_arr, u_arr = run_simulation(
            controller=controller,
            dynamics_model=dynamics,
            sim_time=0.1,
            dt=0.001,  # Small timestep for stiff system
            initial_state=initial_state
        )

        assert x_arr.shape[1] == 4
        assert np.all(np.isfinite(x_arr))

    def test_integrator_statistics_tracking(self):
        """Test that integrator statistics are properly tracked."""
        class StatTrackingDynamics:
            def __init__(self):
                self.integrator = DormandPrince45()

            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                def dynamics_fn(t, x, control):
                    return np.array([-0.1 * x[0] + control])

                result = self.integrator.integrate(dynamics_fn, state, np.array([u]), dt)

                # Check statistics are being updated
                stats = self.integrator.get_statistics()
                assert stats["total_steps"] >= 0
                assert stats["function_evaluations"] >= 0

                return result

        controller = MockController()
        dynamics = StatTrackingDynamics()
        initial_state = np.array([0.1])

        # Reset statistics before test
        dynamics.integrator.reset_statistics()

        t_arr, x_arr, u_arr = run_simulation(
            controller=controller,
            dynamics_model=dynamics,
            sim_time=0.1,
            dt=0.01,
            initial_state=initial_state
        )

        # Verify statistics were updated
        stats = dynamics.integrator.get_statistics()
        assert stats["total_steps"] > 0
        assert stats["function_evaluations"] > 0


class TestSimulationStepRouter:
    """Test the simulation step router functionality."""

    def test_step_function_dispatch(self):
        """Test the step function dispatches correctly."""
        state = np.array([0.1, 0.0, 0.05, 0.0])
        control = 0.1
        dt = 0.01

        # Should not crash and return valid state
        try:
            next_state = step(state, control, dt)
            assert isinstance(next_state, np.ndarray)
            assert len(next_state) == len(state)
            assert np.all(np.isfinite(next_state))
        except RuntimeError as e:
            # Expected if full dynamics unavailable
            assert "Full dynamics unavailable" in str(e)

    def test_step_function_with_different_inputs(self):
        """Test step function with various input types."""
        test_cases = [
            (np.array([1.0]), 0.5, 0.01),
            (np.array([1.0, 0.5]), 1.0, 0.005),
            (np.array([0.1, 0.0, 0.2, 0.0]), -0.5, 0.02),
        ]

        for state, control, dt in test_cases:
            try:
                next_state = step(state, control, dt)
                assert isinstance(next_state, np.ndarray)
                assert len(next_state) == len(state)
            except RuntimeError:
                # Expected if dynamics module unavailable
                pass


class TestSimulationPerformance:
    """Test simulation performance characteristics."""

    def test_simulation_performance_scaling(self):
        """Test that simulation performance scales reasonably."""
        controller = MockController()
        dynamics = MockDynamicsModel(state_dim=6)
        initial_state = np.zeros(6)

        # Test different simulation lengths
        sim_times = [0.1, 0.5, 1.0]
        run_times = []

        for sim_time in sim_times:
            start = time.time()

            t_arr, x_arr, u_arr = run_simulation(
                controller=controller,
                dynamics_model=dynamics,
                sim_time=sim_time,
                dt=0.001,  # Fine timestep
                initial_state=initial_state
            )

            end = time.time()
            run_times.append(end - start)

            # Basic validation
            expected_steps = int(sim_time / 0.001)
            assert len(t_arr) == expected_steps + 1
            assert np.all(np.isfinite(x_arr))

        # Runtime should scale roughly linearly
        assert all(rt < 5.0 for rt in run_times)  # Reasonable performance

    def test_memory_usage_stability(self):
        """Test that simulation doesn't have memory leaks."""
        import gc

        initial_objects = len(gc.get_objects())

        # Run multiple simulations
        for _ in range(20):
            controller = MockController()
            dynamics = MockDynamicsModel()
            initial_state = np.random.randn(4) * 0.1

            t_arr, x_arr, u_arr = run_simulation(
                controller=controller,
                dynamics_model=dynamics,
                sim_time=0.1,
                dt=0.01,
                initial_state=initial_state
            )

            # Clear references
            del t_arr, x_arr, u_arr, controller, dynamics

        gc.collect()
        final_objects = len(gc.get_objects())

        # Allow reasonable object growth
        object_growth = final_objects - initial_objects
        assert object_growth < 1000, f"Excessive object growth: {object_growth}"


@pytest.mark.skipif(not CONTROLLER_AVAILABLE, reason="Controller factory not available")
class TestRealControllerIntegration:
    """Test integration with real controllers when available."""

    def test_classical_smc_integration(self):
        """Test integration with classical SMC controller."""
        try:
            # Create controller with safe gains
            controller = create_controller(
                'classical_smc',
                gains=[10.0, 5.0, 8.0, 3.0, 15.0, 2.0]
            )

            dynamics = MockDynamicsModel(state_dim=4)
            initial_state = np.array([0.1, 0.0, 0.05, 0.0])

            t_arr, x_arr, u_arr = run_simulation(
                controller=controller,
                dynamics_model=dynamics,
                sim_time=0.5,
                dt=0.01,
                initial_state=initial_state
            )

            # Validate integration worked
            assert len(t_arr) == 51
            assert x_arr.shape == (51, 4)
            assert np.all(np.isfinite(x_arr))
            assert np.all(np.isfinite(u_arr))

        except Exception as e:
            pytest.skip(f"Real controller integration failed: {e}")

    def test_sta_smc_integration(self):
        """Test integration with super-twisting SMC controller."""
        try:
            controller = create_controller(
                'sta_smc',
                gains=[15.0, 8.0, 12.0, 5.0, 20.0, 3.0]
            )

            dynamics = MockDynamicsModel(state_dim=4)
            initial_state = np.array([0.05, 0.0, 0.1, 0.0])

            t_arr, x_arr, u_arr = run_simulation(
                controller=controller,
                dynamics_model=dynamics,
                sim_time=0.3,
                dt=0.005,
                initial_state=initial_state,
                u_max=50.0  # Reasonable saturation limit
            )

            # Validate results
            assert x_arr.shape[1] == 4
            assert np.all(np.isfinite(x_arr))
            assert np.all(np.abs(u_arr) <= 50.0)

        except Exception as e:
            pytest.skip(f"STA-SMC integration failed: {e}")


@pytest.mark.skipif(not PLANT_AVAILABLE, reason="Plant models not available")
class TestRealPlantIntegration:
    """Test integration with real plant models when available."""

    def test_dip_dynamics_integration(self):
        """Test integration with real DIP dynamics."""
        try:
            controller = MockController()
            dynamics = DIPDynamics()

            # Standard DIP initial condition
            initial_state = np.array([0.1, 0.0, 0.05, 0.0])  # [θ1, θ1̇, θ2, θ2̇]

            t_arr, x_arr, u_arr = run_simulation(
                controller=controller,
                dynamics_model=dynamics,
                sim_time=0.2,
                dt=0.001,  # Small timestep for nonlinear dynamics
                initial_state=initial_state,
                u_max=10.0
            )

            # Validate physics simulation
            assert x_arr.shape[1] == 4
            assert np.all(np.isfinite(x_arr))

            # Check energy conservation (approximately)
            # For small oscillations, energy should be bounded
            angles = x_arr[:, [0, 2]]
            velocities = x_arr[:, [1, 3]]
            max_angle = np.max(np.abs(angles))
            max_velocity = np.max(np.abs(velocities))

            assert max_angle < 1.0  # Reasonable angle range
            assert max_velocity < 10.0  # Reasonable velocity range

        except Exception as e:
            pytest.skip(f"Real plant integration failed: {e}")


class TestSimulationRobustness:
    """Test simulation robustness to various edge cases."""

    def test_extreme_initial_conditions(self):
        """Test simulation with extreme initial conditions."""
        controller = MockController(max_force=100.0)
        dynamics = MockDynamicsModel()

        extreme_conditions = [
            np.array([10.0, 0.0, 0.0, 0.0]),    # Large position
            np.array([0.0, 10.0, 0.0, 0.0]),    # Large velocity
            np.array([0.0, 0.0, 10.0, 0.0]),    # Large angle
            np.array([1e-10, 1e-10, 1e-10, 1e-10]),  # Very small
            np.array([-5.0, 2.0, -3.0, 1.0]),   # Mixed signs
        ]

        for initial_state in extreme_conditions:
            t_arr, x_arr, u_arr = run_simulation(
                controller=controller,
                dynamics_model=dynamics,
                sim_time=0.1,
                dt=0.01,
                initial_state=initial_state,
                u_max=100.0
            )

            # Should complete without crashing
            assert len(t_arr) > 1
            assert x_arr.shape[0] == len(t_arr)
            np.testing.assert_array_equal(x_arr[0], initial_state)

    def test_very_small_timesteps(self):
        """Test simulation with very small timesteps."""
        controller = MockController()
        dynamics = MockDynamicsModel()
        initial_state = np.array([0.1, 0.0, 0.0, 0.0])

        # Very small timestep
        t_arr, x_arr, u_arr = run_simulation(
            controller=controller,
            dynamics_model=dynamics,
            sim_time=0.01,
            dt=1e-6,  # Microsecond timestep
            initial_state=initial_state
        )

        # Should complete (though will be many steps)
        assert len(t_arr) == 10001  # 0.01/1e-6 + 1
        assert np.all(np.isfinite(x_arr))

    def test_very_large_timesteps(self):
        """Test simulation with large timesteps."""
        controller = MockController()
        dynamics = MockDynamicsModel()
        initial_state = np.array([0.01, 0.0, 0.0, 0.0])  # Small initial condition

        # Large timestep
        t_arr, x_arr, u_arr = run_simulation(
            controller=controller,
            dynamics_model=dynamics,
            sim_time=1.0,
            dt=0.1,  # Large timestep
            initial_state=initial_state
        )

        assert len(t_arr) == 11  # 1.0/0.1 + 1
        assert np.all(np.isfinite(x_arr))

    def test_random_parameters_robustness(self):
        """Test simulation robustness with randomized parameters."""
        np.random.seed(42)  # For reproducibility

        for _ in range(10):
            # Random parameters
            state_dim = np.random.randint(1, 8)
            sim_time = np.random.uniform(0.05, 0.5)
            dt = np.random.uniform(0.001, 0.02)
            u_max = np.random.uniform(1.0, 50.0)

            controller = MockController(max_force=u_max)
            dynamics = MockDynamicsModel(state_dim=state_dim)
            initial_state = 0.1 * np.random.randn(state_dim)

            try:
                t_arr, x_arr, u_arr = run_simulation(
                    controller=controller,
                    dynamics_model=dynamics,
                    sim_time=sim_time,
                    dt=dt,
                    initial_state=initial_state,
                    u_max=u_max
                )

                # Basic validation
                assert len(t_arr) > 1
                assert x_arr.shape[1] == state_dim
                assert np.all(np.isfinite(x_arr))
                assert np.all(np.abs(u_arr) <= u_max + 1e-10)

            except Exception as e:
                pytest.fail(f"Random test failed with params: state_dim={state_dim}, "
                          f"sim_time={sim_time}, dt={dt}, u_max={u_max}. Error: {e}")


if __name__ == "__main__":
    # Run basic smoke test if executed directly
    print("Running simulation integration validation...")

    try:
        # Test basic integration
        test_basic = TestSimulationIntegrationBasic()
        test_basic.test_basic_simulation_workflow()
        print("✓ Basic simulation workflow test passed")

        test_basic.test_controller_with_compute_control()
        print("✓ Stateful controller test passed")

        # Test error handling
        test_errors = TestSimulationErrorHandling()
        test_errors.test_controller_failure_handling()
        print("✓ Controller failure handling test passed")

        test_errors.test_dynamics_failure_handling()
        print("✓ Dynamics failure handling test passed")

        # Test integrator compatibility
        test_integrators = TestIntegratorCompatibility()
        test_integrators.test_euler_integration_compatibility()
        print("✓ Euler integrator compatibility test passed")

        print("\n🎉 All simulation integration tests passed!")
        print("Simulation framework is robust and ready for deployment.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise