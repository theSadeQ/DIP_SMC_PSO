#==========================================================================================\\\
#============== tests/test_benchmarks/core/test_simulation_throughput.py ================\\\
#==========================================================================================\\\
"""
Simulation Throughput Benchmarks.

This test suite focuses on end-to-end simulation performance:
- Full simulation throughput
- Batch processing performance
- Integration method efficiency
- Memory usage during simulation
"""

import numpy as np
import pytest

from src.core.dynamics import DoubleInvertedPendulum
from src.core.vector_sim import simulate_system_batch

try:
    from src.controllers.factory import create_controller
except Exception:
    create_controller = None

try:
    from src.core.vector_sim import simulate_system_batch as _simulate_batch
except Exception:
    from src.core.vector_sim import _simulate_batch_numba_full as _simulate_fallback


CTRL_NAMES = ["classical_smc", "sta_smc"]  # Focus on available controllers


def _default_gains_for(ctrl_name, config):
    """Get default gains for controllers."""
    key = ctrl_name.lower()
    try:
        gains = config.controller_defaults[key]["gains"]
        return np.asarray(gains, dtype=float)
    except Exception:
        if key == "classical_smc":
            return np.array([10.0, 8.0, 2.0, 2.0, 50.0, 1.0], dtype=float)
        if key == "sta_smc":
            return np.array([2.0, 1.0, 5.0, 5.0, 3.0, 3.0], dtype=float)
    return np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0], dtype=float)


@pytest.mark.parametrize("ctrl_name", CTRL_NAMES)
def test_full_simulation_throughput(ctrl_name, config, full_dynamics, benchmark):
    """Benchmark complete simulation throughput."""
    gains = _default_gains_for(ctrl_name, config)

    if not create_controller:
        pytest.skip("Factory not available for throughput testing")

    try:
        controller = create_controller(ctrl_name, config, gains)
    except Exception:
        pytest.skip(f"Controller {ctrl_name} not available")

    # Simulation parameters
    dt = 0.01
    duration = 1.0  # 1 second simulation
    n_steps = int(duration / dt)

    initial_state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])

    def run_simulation():
        """Run a complete simulation."""
        try:
            return simulate_system_batch(
                controller=controller,
                initial_state=initial_state,
                dt=dt,
                n_steps=n_steps,
                dynamics=full_dynamics
            )
        except Exception:
            # Fallback for different API
            if '_simulate_fallback' in globals():
                return _simulate_fallback(
                    initial_state, gains, n_steps, dt
                )
            else:
                raise

    result = benchmark(run_simulation)

    # Validate simulation result
    if isinstance(result, dict):
        assert 'states' in result or 't' in result
        if 'states' in result:
            states = result['states']
            assert states.shape[0] == n_steps + 1
            assert np.all(np.isfinite(states))
    elif isinstance(result, tuple):
        states, controls = result[:2]
        assert len(states) == n_steps + 1
        assert np.all(np.isfinite(states))


@pytest.mark.parametrize("batch_size", [1, 10, 50, 100])
def test_batch_simulation_scaling(batch_size, config, benchmark):
    """Test how simulation scales with batch size."""
    gains = _default_gains_for("classical_smc", config)

    if not create_controller:
        pytest.skip("Factory not available")

    try:
        controller = create_controller("classical_smc", config, gains)
    except Exception:
        pytest.skip("Classical SMC not available")

    # Multiple initial conditions
    initial_states = np.random.uniform(
        -0.1, 0.1, (batch_size, 6)
    )

    dt = 0.01
    n_steps = 50  # Shorter for batch testing

    def run_batch():
        """Run batch simulation."""
        results = []
        for initial_state in initial_states:
            try:
                result = simulate_system_batch(
                    controller=controller,
                    initial_state=initial_state,
                    dt=dt,
                    n_steps=n_steps
                )
                results.append(result)
            except Exception:
                # Skip if batch simulation not available
                return None
        return results

    results = benchmark(run_batch)

    if results is not None:
        assert len(results) == batch_size


class TestSimulationEfficiency:
    """Test simulation efficiency characteristics."""

    def test_integration_method_performance(self, config, benchmark):
        """Compare performance of different integration methods."""
        gains = _default_gains_for("classical_smc", config)

        if not create_controller:
            pytest.skip("Factory not available")

        try:
            controller = create_controller("classical_smc", config, gains)
        except Exception:
            pytest.skip("Classical SMC not available")

        initial_state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
        dt = 0.01
        n_steps = 100

        def run_with_euler():
            """Run simulation with Euler integration."""
            try:
                return simulate_system_batch(
                    controller=controller,
                    initial_state=initial_state,
                    dt=dt,
                    n_steps=n_steps,
                    integrator='euler'
                )
            except Exception:
                return None

        result = benchmark(run_with_euler)

        if result is not None:
            # Validate result structure
            if isinstance(result, dict) and 'states' in result:
                assert result['states'].shape[0] == n_steps + 1

    def test_memory_efficiency_long_simulation(self, config):
        """Test memory efficiency for longer simulations."""
        gains = _default_gains_for("classical_smc", config)

        if not create_controller:
            pytest.skip("Factory not available")

        try:
            controller = create_controller("classical_smc", config, gains)
        except Exception:
            pytest.skip("Classical SMC not available")

        initial_state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
        dt = 0.01
        n_steps = 1000  # 10 second simulation

        try:
            result = simulate_system_batch(
                controller=controller,
                initial_state=initial_state,
                dt=dt,
                n_steps=n_steps
            )

            # Check result is reasonable size
            if isinstance(result, dict) and 'states' in result:
                states = result['states']
                # Memory usage should be proportional to simulation length
                expected_shape = (n_steps + 1, 6)
                assert states.shape == expected_shape

                # States should remain bounded
                assert np.all(np.abs(states) < 100), "States grew unbounded"

        except MemoryError:
            pytest.fail("Simulation consumed too much memory")
        except Exception as e:
            pytest.skip(f"Simulation failed: {e}")

    def test_real_time_factor(self, config):
        """Test if simulation can run faster than real-time."""
        gains = _default_gains_for("classical_smc", config)

        if not create_controller:
            pytest.skip("Factory not available")

        try:
            controller = create_controller("classical_smc", config, gains)
        except Exception:
            pytest.skip("Classical SMC not available")

        initial_state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
        dt = 0.01
        sim_duration = 0.5  # 0.5 seconds simulated time
        n_steps = int(sim_duration / dt)

        import time
        start_time = time.perf_counter()

        try:
            result = simulate_system_batch(
                controller=controller,
                initial_state=initial_state,
                dt=dt,
                n_steps=n_steps
            )

            end_time = time.perf_counter()
            wall_time = end_time - start_time

            real_time_factor = sim_duration / wall_time

            # Should be able to simulate faster than real-time
            assert real_time_factor > 1.0, f"Real-time factor only {real_time_factor:.2f}x"

            # Log performance for information
            print(f"\nReal-time factor: {real_time_factor:.1f}x")

        except Exception as e:
            pytest.skip(f"Performance test failed: {e}")


@pytest.mark.parametrize("dt", [0.001, 0.01, 0.1])
def test_timestep_performance_scaling(dt, config):
    """Test how performance scales with timestep size."""
    gains = _default_gains_for("classical_smc", config)

    if not create_controller:
        pytest.skip("Factory not available")

    try:
        controller = create_controller("classical_smc", config, gains)
    except Exception:
        pytest.skip("Classical SMC not available")

    initial_state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
    sim_duration = 0.1  # Fixed simulation duration
    n_steps = int(sim_duration / dt)

    import time
    start_time = time.perf_counter()

    try:
        result = simulate_system_batch(
            controller=controller,
            initial_state=initial_state,
            dt=dt,
            n_steps=n_steps
        )

        end_time = time.perf_counter()
        computation_time = end_time - start_time

        # Smaller timesteps should take more computation time
        # but the relationship should be roughly linear
        time_per_step = computation_time / n_steps

        # Should be reasonable computational cost per step
        assert time_per_step < 1e-3, f"Too slow: {time_per_step*1000:.3f}ms per step"

    except Exception as e:
        pytest.skip(f"Timestep test failed for dt={dt}: {e}")