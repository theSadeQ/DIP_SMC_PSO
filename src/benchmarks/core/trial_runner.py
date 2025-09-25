#==========================================================================================\\\
#================= src/benchmarks/core/trial_runner.py ===================================\\\
#==========================================================================================\\\
"""
Core trial execution engine for statistical benchmarking.

This module implements the trial execution logic for running multiple
independent simulations of control systems. It handles:
- Batch simulation execution
- Randomization and seeding
- Error handling and fallbacks
- Trial orchestration and coordination

The Central Limit Theorem implies that for skewed distributions, a sample
size of at least 25–30 trials is required for the sample mean to approximate
a normal distribution. By default, 30 trials are executed.
"""

from __future__ import annotations

from typing import Callable, Any, List, Dict, Tuple, Optional
import numpy as np

from src.core.vector_sim import simulate_system_batch
from ..metrics import compute_basic_metrics


def execute_single_trial(
    controller_factory: Callable[[np.ndarray], Any],
    trial_seed: int,
    sim_duration: float,
    sim_dt: Optional[float],
    max_force: float,
    noise_std: float = 0.0
) -> Dict[str, float]:
    """Execute a single simulation trial with the given parameters.

    Parameters
    ----------
    controller_factory : Callable
        Factory function that creates controller instances
    trial_seed : int
        Random seed for this specific trial
    sim_duration : float
        Simulation duration in seconds
    sim_dt : float, optional
        Simulation time step. If None, use default from simulator
    max_force : float
        Maximum control force magnitude
    noise_std : float, optional
        Standard deviation of measurement noise

    Returns
    -------
    dict
        Performance metrics for this trial

    Raises
    ------
    RuntimeError
        If simulation fails and no fallback succeeds
    """
    rng = np.random.default_rng(trial_seed)

    # Execute vectorized batch simulation with single controller
    controller_gains = np.array([np.zeros(controller_factory.n_gains)], dtype=float)

    try:
        # Try with explicit dt parameter
        t, x_b, u_b, sigma_b = simulate_system_batch(
            controller_factory,
            controller_gains,
            sim_time=sim_duration,
            dt=sim_dt,
            u_max=max_force,
            seed=trial_seed,
        )
    except TypeError:
        # Fallback to signature without dt parameter
        try:
            t, x_b, u_b, sigma_b = simulate_system_batch(
                controller_factory,
                controller_gains,
                sim_time=sim_duration,
                u_max=max_force,
                seed=trial_seed,
            )
        except Exception as e:
            raise RuntimeError(f"Simulation failed for trial with seed {trial_seed}: {e}")

    # Add optional measurement noise to state trajectories
    if float(noise_std) > 0.0:
        noise = rng.normal(0.0, float(noise_std), size=x_b.shape)
        x_noisy = x_b + noise
    else:
        x_noisy = x_b

    # Compute performance metrics for this trial
    metrics = compute_basic_metrics(t, x_noisy, u_b, max_force)

    return metrics


def run_multiple_trials(
    controller_factory: Callable[[np.ndarray], Any],
    cfg: Any,
    n_trials: int = 30,
    seed: int = 1234,
    randomise_physics: bool = False,
    noise_std: float = 0.0,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[Dict[str, float]]:
    """Execute multiple independent simulation trials.

    This function runs n_trials independent simulations and collects
    performance metrics from each trial. Each trial uses a different
    random seed to ensure statistical independence.

    Parameters
    ----------
    controller_factory : Callable[[np.ndarray], Any]
        Factory function that returns controller instances when provided
        with gain vectors. Must have 'n_gains' attribute.
    cfg : Any
        Configuration object with 'simulation.duration' and optionally
        'simulation.dt' attributes
    n_trials : int, optional
        Number of independent trials to execute. Default is 30.
    seed : int, optional
        Base random seed for trial generation
    randomise_physics : bool, optional
        Whether to randomize physical parameters (reserved for future use)
    noise_std : float, optional
        Standard deviation of measurement noise
    progress_callback : callable, optional
        Callback function called with (current_trial, total_trials)

    Returns
    -------
    list of dict
        List containing metrics dictionary for each trial

    Notes
    -----
    The randomise_physics parameter is included for future extensibility
    but is not currently implemented. It would allow testing controller
    robustness against parameter uncertainties.
    """
    rng = np.random.default_rng(int(seed))
    metrics_list: List[Dict[str, float]] = []

    # Determine simulation parameters from configuration
    sim_duration = cfg.simulation.duration
    sim_dt = getattr(cfg.simulation, 'dt', None)

    # Determine maximum control force from reference controller
    ref_ctrl = controller_factory(np.zeros(controller_factory.n_gains))
    max_force = getattr(ref_ctrl, "max_force", 150.0)

    # Execute trials sequentially
    for trial_idx in range(int(n_trials)):
        # Generate unique seed for this trial
        trial_seed = int(rng.integers(0, 2**32 - 1))

        # Execute single trial
        try:
            metrics = execute_single_trial(
                controller_factory=controller_factory,
                trial_seed=trial_seed,
                sim_duration=sim_duration,
                sim_dt=sim_dt,
                max_force=max_force,
                noise_std=noise_std
            )
            metrics_list.append(metrics)

        except RuntimeError as e:
            print(f"Warning: Trial {trial_idx + 1} failed: {e}")
            # Could implement retry logic or fallback here
            continue

        # Optional progress reporting
        if progress_callback:
            progress_callback(trial_idx + 1, n_trials)

    if len(metrics_list) == 0:
        raise RuntimeError("All trials failed - no metrics collected")

    return metrics_list


def validate_trial_configuration(
    controller_factory: Callable[[np.ndarray], Any],
    cfg: Any,
    n_trials: int
) -> None:
    """Validate configuration before starting trial execution.

    Parameters
    ----------
    controller_factory : Callable
        Controller factory to validate
    cfg : Any
        Configuration object to validate
    n_trials : int
        Number of trials to validate

    Raises
    ------
    ValueError
        If configuration is invalid
    """
    # Validate controller factory
    if not hasattr(controller_factory, 'n_gains'):
        raise ValueError("Controller factory must have 'n_gains' attribute")

    # Validate configuration
    if not hasattr(cfg, 'simulation'):
        raise ValueError("Configuration must have 'simulation' attribute")

    if not hasattr(cfg.simulation, 'duration'):
        raise ValueError("Configuration must specify simulation.duration")

    if cfg.simulation.duration <= 0:
        raise ValueError("Simulation duration must be positive")

    # Validate trial count
    if n_trials <= 0:
        raise ValueError("Number of trials must be positive")

    if n_trials < 5:
        print("Warning: Less than 5 trials may not provide reliable statistics")

    # Test controller instantiation
    try:
        test_gains = np.zeros(controller_factory.n_gains)
        test_ctrl = controller_factory(test_gains)
    except Exception as e:
        raise ValueError(f"Failed to create test controller: {e}")