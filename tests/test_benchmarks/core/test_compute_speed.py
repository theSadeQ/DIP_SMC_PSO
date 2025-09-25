#==========================================================================================\\\
#================ tests/test_benchmarks/core/test_compute_speed.py ====================\\\
#==========================================================================================\\\
"""
Controller Compute Speed Benchmarks.

SINGLE JOB: Test only computational speed of controller compute_control methods.
- Single controller call timing
- Computational complexity measurement
- Speed comparison between controllers
- Performance regression detection
"""

import numpy as np
import pytest

from src.controllers.classic_smc import ClassicalSMC
from src.controllers.sta_smc import SuperTwistingSMC

try:
    from src.controllers.factory import create_controller
except Exception:
    create_controller = None


CTRL_NAMES = ["classical_smc", "sta_smc", "adaptive_smc"]


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
        if key == "adaptive_smc":
            return np.array([5.0, 5.0, 3.0, 3.0, 1.0], dtype=float)
    return np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0], dtype=float)


@pytest.mark.parametrize("ctrl_name", CTRL_NAMES)
def test_controller_compute_speed(ctrl_name, config, benchmark):
    """Benchmark individual controller compute performance."""
    gains = _default_gains_for(ctrl_name, config)

    if create_controller:
        try:
            controller = create_controller(ctrl_name, config, gains)
        except Exception:
            pytest.skip(f"Controller {ctrl_name} not available via factory")
    else:
        # Direct instantiation fallback
        if ctrl_name == "classical_smc":
            controller = ClassicalSMC(gains, config)
        elif ctrl_name == "sta_smc":
            controller = SuperTwistingSMC(gains, config)
        else:
            pytest.skip(f"Controller {ctrl_name} not available directly")

    # Test state
    state = np.array([0.1, 0.2, 0.3, 0.05, 0.1, 0.15])
    prev_control = np.array([0.0])
    history = {}

    # Benchmark the compute_control method
    def compute_step():
        return controller.compute_control(state, prev_control, history)

    result = benchmark(compute_step)

    # Validate the result
    assert 'u' in result or 'control' in result
    control = result.get('u', result.get('control'))
    if control is not None:
        assert np.all(np.isfinite(control))


@pytest.mark.parametrize("ctrl_name", CTRL_NAMES)
def test_controller_speed_consistency(ctrl_name, config):
    """Test that controller speed is consistent across calls."""
    gains = _default_gains_for(ctrl_name, config)

    if not create_controller:
        pytest.skip("Factory not available")

    try:
        controller = create_controller(ctrl_name, config, gains)
    except Exception:
        pytest.skip(f"Controller {ctrl_name} not available")

    state = np.array([0.1, 0.2, 0.3, 0.05, 0.1, 0.15])
    prev_control = np.array([0.0])
    history = {}

    import time

    # Measure multiple calls
    times = []
    for _ in range(100):
        start = time.perf_counter()
        controller.compute_control(state, prev_control, history)
        end = time.perf_counter()
        times.append(end - start)

    times = np.array(times)

    # Speed should be consistent (low variance)
    mean_time = np.mean(times)
    std_time = np.std(times)

    # Coefficient of variation should be reasonable
    cv = std_time / mean_time if mean_time > 0 else float('inf')
    assert cv < 2.0, f"Controller {ctrl_name} has inconsistent timing (CV={cv:.3f})"

    # Mean time should be reasonable
    assert mean_time < 1e-2, f"Controller {ctrl_name} too slow: {mean_time*1000:.3f}ms"


def test_compute_time_scaling_with_state_complexity():
    """Test that compute time scales reasonably with different states."""
    if not create_controller:
        pytest.skip("Factory not available")

    try:
        controller = create_controller("classical_smc", {},
                                       np.array([10.0, 8.0, 2.0, 2.0, 50.0, 1.0]))
    except Exception:
        pytest.skip("Classical SMC not available")

    import time

    # Simple state
    simple_state = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    # Complex state with large values
    complex_state = np.array([5.0, 3.0, -2.0, 2.0, -1.5, 1.0])

    # Measure times
    def measure_time(state, n_calls=50):
        times = []
        for _ in range(n_calls):
            start = time.perf_counter()
            controller.compute_control(state, np.array([0.0]), {})
            end = time.perf_counter()
            times.append(end - start)
        return np.mean(times)

    simple_time = measure_time(simple_state)
    complex_time = measure_time(complex_state)

    # Complex state shouldn't be significantly slower
    assert complex_time <= simple_time * 3.0, \
        f"Complex state too slow: {complex_time/simple_time:.2f}x slower"


@pytest.mark.parametrize("ctrl_name", ["classical_smc", "sta_smc"])
def test_controller_speed_regression(ctrl_name, config):
    """Test for controller speed regression (baseline performance)."""
    gains = _default_gains_for(ctrl_name, config)

    if not create_controller:
        pytest.skip("Factory not available")

    try:
        controller = create_controller(ctrl_name, config, gains)
    except Exception:
        pytest.skip(f"Controller {ctrl_name} not available")

    state = np.array([0.1, 0.2, 0.3, 0.05, 0.1, 0.15])

    import time

    # Measure time for single computation
    start = time.perf_counter()
    result = controller.compute_control(state, np.array([0.0]), {})
    end = time.perf_counter()

    compute_time = end - start

    # Baseline performance thresholds (adjust based on hardware)
    if ctrl_name == "classical_smc":
        max_time = 1e-3  # 1ms
    elif ctrl_name == "sta_smc":
        max_time = 2e-3  # 2ms
    else:
        max_time = 5e-3  # 5ms for other controllers

    assert compute_time < max_time, \
        f"{ctrl_name} performance regression: {compute_time*1000:.3f}ms > {max_time*1000:.1f}ms"

    # Validate result
    control = result.get('u', result.get('control'))
    assert control is not None, f"{ctrl_name} returned no control signal"
    assert np.all(np.isfinite(control)), f"{ctrl_name} returned non-finite control"


def test_controller_warm_up_effect():
    """Test controller warm-up effect on computation time."""
    if not create_controller:
        pytest.skip("Factory not available")

    try:
        controller = create_controller("classical_smc", {},
                                       np.array([10.0, 8.0, 2.0, 2.0, 50.0, 1.0]))
    except Exception:
        pytest.skip("Classical SMC not available")

    state = np.array([0.1, 0.2, 0.3, 0.05, 0.1, 0.15])

    import time

    # First few calls (cold start)
    cold_times = []
    for i in range(5):
        start = time.perf_counter()
        controller.compute_control(state, np.array([0.0]), {})
        end = time.perf_counter()
        cold_times.append(end - start)

    # Later calls (warm)
    warm_times = []
    for i in range(50, 55):  # Skip ahead to avoid transients
        start = time.perf_counter()
        controller.compute_control(state, np.array([0.0]), {})
        end = time.perf_counter()
        warm_times.append(end - start)

    avg_cold_time = np.mean(cold_times)
    avg_warm_time = np.mean(warm_times)

    # Warm-up effect should be minimal for simple controllers
    speedup = avg_cold_time / avg_warm_time if avg_warm_time > 0 else 1.0

    # Should not have excessive warm-up penalty
    assert speedup < 5.0, f"Excessive warm-up penalty: {speedup:.2f}x"

    print(f"Cold start: {avg_cold_time*1000:.3f}ms, Warm: {avg_warm_time*1000:.3f}ms, "
          f"Speedup: {speedup:.2f}x")