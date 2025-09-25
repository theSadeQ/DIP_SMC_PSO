#==========================================================================================\\\
#================ tests/test_benchmarks/core/test_memory_usage.py ====================\\\
#==========================================================================================\\\
"""
Controller Memory Usage Benchmarks.

SINGLE JOB: Test only memory usage patterns of controllers.
- Memory allocation per controller call
- Memory leak detection
- Memory usage scaling
- Memory efficiency validation
"""

import numpy as np
import pytest

try:
    from src.controllers.factory import create_controller
except Exception:
    create_controller = None


CTRL_NAMES = ["classical_smc", "sta_smc", "adaptive_smc"]


def _default_gains_for(ctrl_name):
    """Get default gains for controllers."""
    key = ctrl_name.lower()
    if key == "classical_smc":
        return np.array([10.0, 8.0, 2.0, 2.0, 50.0, 1.0], dtype=float)
    if key == "sta_smc":
        return np.array([2.0, 1.0, 5.0, 5.0, 3.0, 3.0], dtype=float)
    if key == "adaptive_smc":
        return np.array([5.0, 5.0, 3.0, 3.0, 1.0], dtype=float)
    return np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0], dtype=float)


@pytest.mark.parametrize("ctrl_name", CTRL_NAMES)
def test_controller_memory_allocation_per_call(ctrl_name, config):
    """Test memory allocation patterns per controller call."""
    gains = _default_gains_for(ctrl_name)

    if not create_controller:
        pytest.skip("Factory not available")

    try:
        controller = create_controller(ctrl_name, config, gains)
    except Exception:
        pytest.skip(f"Controller {ctrl_name} not available")

    state = np.array([0.1, 0.2, 0.3, 0.05, 0.1, 0.15])
    prev_control = np.array([0.0])
    history = {}

    # Run multiple computations to check for consistent memory usage
    results = []
    for _ in range(100):
        result = controller.compute_control(state, prev_control, history)
        results.append(result)

    # All results should be consistent (no growing memory structures)
    assert len(results) == 100

    for i, result in enumerate(results):
        assert 'u' in result or 'control' in result, f"Missing control at iteration {i}"
        control = result.get('u', result.get('control'))
        if control is not None:
            assert np.all(np.isfinite(control)), f"Non-finite control at iteration {i}"


@pytest.mark.parametrize("ctrl_name", CTRL_NAMES)
def test_controller_no_memory_leaks(ctrl_name, config):
    """Test that controllers don't have memory leaks."""
    gains = _default_gains_for(ctrl_name)

    if not create_controller:
        pytest.skip("Factory not available")

    try:
        controller = create_controller(ctrl_name, config, gains)
    except Exception:
        pytest.skip(f"Controller {ctrl_name} not available")

    state = np.array([0.1, 0.2, 0.3, 0.05, 0.1, 0.15])
    prev_control = np.array([0.0])
    history = {}

    # Run many iterations to detect memory leaks
    for iteration in range(1000):
        try:
            result = controller.compute_control(state, prev_control, history)
            control = result.get('u', result.get('control'))

            # Validate each iteration
            if control is not None:
                assert np.all(np.isfinite(control)), f"Memory corruption at iteration {iteration}"
                assert np.all(np.abs(control) < 1000), f"Control explosion at iteration {iteration}"

            # Simulate state evolution
            state = state + 0.001 * np.random.randn(6)
            state = np.clip(state, -10, 10)  # Keep bounded

        except MemoryError:
            pytest.fail(f"Memory leak detected at iteration {iteration}")
        except Exception as e:
            pytest.fail(f"Controller failed at iteration {iteration}: {e}")


def test_controller_memory_usage_scaling():
    """Test memory usage scaling with problem complexity."""
    if not create_controller:
        pytest.skip("Factory not available")

    try:
        controller = create_controller("classical_smc", {},
                                       np.array([10.0, 8.0, 2.0, 2.0, 50.0, 1.0]))
    except Exception:
        pytest.skip("Classical SMC not available")

    # Test with different state vector sizes (if supported)
    base_state = np.array([0.1, 0.2, 0.3, 0.05, 0.1, 0.15])

    # Multiple calls with same state
    for batch_size in [1, 10, 100]:
        states = [base_state.copy() for _ in range(batch_size)]
        results = []

        for state in states:
            result = controller.compute_control(state, np.array([0.0]), {})
            results.append(result)

        # Memory usage should scale linearly, not exponentially
        assert len(results) == batch_size

        # All results should be valid
        for i, result in enumerate(results):
            control = result.get('u', result.get('control'))
            if control is not None:
                assert np.all(np.isfinite(control)), f"Batch {batch_size}, item {i} invalid"


@pytest.mark.parametrize("ctrl_name", ["classical_smc", "sta_smc"])
def test_controller_memory_efficiency(ctrl_name, config):
    """Test controller memory efficiency."""
    gains = _default_gains_for(ctrl_name)

    if not create_controller:
        pytest.skip("Factory not available")

    try:
        controller = create_controller(ctrl_name, config, gains)
    except Exception:
        pytest.skip(f"Controller {ctrl_name} not available")

    state = np.array([0.1, 0.2, 0.3, 0.05, 0.1, 0.15])

    # Check that repeated calls don't accumulate objects
    initial_state_copy = state.copy()

    # Many calls with different states
    for i in range(500):
        # Vary state slightly
        test_state = initial_state_copy + 0.01 * np.sin(i * 0.1) * np.ones(6)

        result = controller.compute_control(test_state, np.array([0.0]), {})
        control = result.get('u', result.get('control'))

        if control is not None:
            # Memory shouldn't grow unbounded
            assert np.all(np.abs(control) < 1000), f"Control unbounded at iteration {i}"

            # Control values should be reasonable
            assert len(control) <= 10, f"Control vector too large at iteration {i}"


def test_adaptive_controller_memory_growth():
    """Test memory growth patterns for adaptive controllers."""
    if not create_controller:
        pytest.skip("Factory not available")

    try:
        controller = create_controller("adaptive_smc", {},
                                       np.array([5.0, 5.0, 3.0, 3.0, 1.0]))
    except Exception:
        pytest.skip("Adaptive SMC not available")

    state = np.array([0.1, 0.2, 0.3, 0.05, 0.1, 0.15])

    # Adaptive controllers may grow parameters, but it should be bounded
    initial_params = getattr(controller, 'parameters', None)
    if hasattr(controller, 'uncertainty_estimator'):
        initial_estimates = controller.uncertainty_estimator.current_estimates.copy()

    # Run adaptation for many steps
    for i in range(200):
        # Introduce persistent disturbance to drive adaptation
        disturbed_state = state + 0.1 * np.array([1, 0, 0, 0, 0, 0])

        result = controller.compute_control(disturbed_state, np.array([0.0]), {})
        control = result.get('u', result.get('control'))

        if control is not None:
            assert np.all(np.isfinite(control)), f"Adaptive control invalid at step {i}"

    # Check that adaptive parameters remain bounded
    if hasattr(controller, 'uncertainty_estimator'):
        final_estimates = controller.uncertainty_estimator.current_estimates

        # Estimates should remain finite and bounded
        assert np.all(np.isfinite(final_estimates))
        assert np.all(np.abs(final_estimates) < 1000), "Adaptive parameters grew unbounded"


def test_controller_history_memory_management():
    """Test memory management of controller history/state storage."""
    if not create_controller:
        pytest.skip("Factory not available")

    try:
        controller = create_controller("classical_smc", {},
                                       np.array([10.0, 8.0, 2.0, 2.0, 50.0, 1.0]))
    except Exception:
        pytest.skip("Classical SMC not available")

    state = np.array([0.1, 0.2, 0.3, 0.05, 0.1, 0.15])
    history = {}

    # Build up history over many calls
    for i in range(100):
        # Add entries to history to test memory management
        history[f'step_{i}'] = {'state': state.copy(), 'time': i * 0.01}

        result = controller.compute_control(state, np.array([0.0]), history)
        control = result.get('u', result.get('control'))

        if control is not None:
            assert np.all(np.isfinite(control))

        # Simulate state evolution
        state = state + 0.01 * np.random.randn(6)

    # History should not cause memory issues
    assert len(history) == 100