"""
Statistical benchmarking utilities for the Double Inverted Pendulum project.

This module defines a lightweight harness for running multiple simulation
trials of a controller and reporting aggregate performance metrics.  The
Central Limit Theorem (CLT) implies that the distribution of sample means
approaches normality as the sample size grows.  For skewed distributions a
sample size of at least 25–30 is typically required for the sample mean to
approximate a normal distribution【559538113951338†L77-L84】.  By default
``run_trials`` executes 30 independent trials, which yields reasonably
accurate confidence intervals for the estimated metrics.  Users may increase
``n_trials`` to tighten the confidence bounds at the cost of longer
execution times.

Metrics computed include:

* **Integral of squared error (ISE)** for all state variables, measuring
  cumulative state deviations.
* **Integral of time‑weighted absolute error (ITAE)**, emphasising errors
  that occur later in the trajectory.
* **Root mean square (RMS) control effort** of the input sequence.
* **Maximum overshoot** across angular states (pendulum angles).
* **Constraint violations**, counting the number of times the control
  input exceeds its allowed range.

These metrics provide a comprehensive view of controller performance and
robustness.  The functions in this module are independent of the specific
controller implementation and rely only on the vectorised simulation
interface.
"""

from __future__ import annotations

from typing import Callable, Dict, Any, List, Tuple
import numpy as np

from src.core.vector_sim import simulate_system_batch


def compute_metrics(
    t: np.ndarray,
    x: np.ndarray,
    u: np.ndarray,
    sigma: np.ndarray,
    max_force: float,
) -> Dict[str, float]:
    """Compute performance metrics for a batch of trajectories.

    Parameters
    ----------
    t : np.ndarray
        One‑dimensional array of time stamps of length ``N+1``.
    x : np.ndarray
        Array of shape ``(B, N+1, S)`` containing the state trajectories for
        ``B`` particles over ``S`` state dimensions.
    u : np.ndarray
        Array of shape ``(B, N)`` containing the control inputs.
    sigma : np.ndarray
        Array of shape ``(B, N)`` containing sliding variables or auxiliary
        outputs.
    max_force : float
        Maximum allowable magnitude of the control input.  Used to count
        constraint violations.

    Returns
    -------
    dict
        Mapping of metric names to scalar values.  Each metric is averaged
        across the batch dimension.
    """
    # Compute time step differences and broadcast to batch
    dt = np.diff(t)
    dt_b = dt[None, :]  # shape (1, N)
    if dt_b.size == 0:
        # Degenerate case with one time step
        dt_b = np.array([[1.0]])
    # Integral of squared error over all states
    ise = np.sum((x[:, :-1, :] ** 2) * dt_b[:, :, None], axis=(1, 2))
    # Integral of time‑weighted absolute error
    time_weights = t[:-1]
    itae = np.sum(np.abs(x[:, :-1, :]) * time_weights[None, :, None], axis=(1, 2))
    # RMS control effort
    rms_u = np.sqrt(np.mean(u ** 2, axis=1))
    # Maximum overshoot for angular states (assumes angles at indices 1 and 2)
    try:
        overshoot = np.max(np.abs(x[:, :, 1:3]), axis=(1, 2))
    except Exception:
        overshoot = np.max(np.abs(x), axis=(1, 2))
    # Count constraint violations
    violations = np.sum(np.abs(u) > max_force, axis=1)
    # Average across batch
    return {
        "ise": float(np.mean(ise)),
        "itae": float(np.mean(itae)),
        "rms_u": float(np.mean(rms_u)),
        "overshoot": float(np.mean(overshoot)),
        "violations": float(np.mean(violations)),
    }


def run_trials(
    controller_factory: Callable[[np.ndarray], Any],
    cfg: Any,
    n_trials: int = 30,
    seed: int = 1234,
    randomise_physics: bool = False,
    noise_std: float = 0.0,
) -> Tuple[List[Dict[str, float]], Dict[str, Tuple[float, float]]]:
    """Run multiple simulations and return per‑trial metrics with confidence intervals.

    The function executes ``n_trials`` independent simulations of the
    double inverted pendulum under the supplied controller factory and
    configuration.  For each trial it collects performance metrics and
    computes a 95 % confidence interval for the mean of each metric.  A
    sample size of at least 25–30 trials is recommended to invoke the
    Central Limit Theorem for skewed distributions【559538113951338†L77-L84】.

    Parameters
    ----------
    controller_factory : Callable[[np.ndarray], Any]
        Factory function that returns a controller instance when provided
        with a gain vector.  The returned controller must define an
        ``n_gains`` attribute and may define ``max_force``.
    cfg : Any
        Full configuration object (e.g., ``ConfigSchema``) supplying
        physics and simulation parameters.  Only ``simulation.duration``
        and ``simulation.dt`` are required by this harness.
    n_trials : int, optional
        Number of independent trials to run.  Defaults to 30.
    seed : int, optional
        Base random seed used to initialise each trial.  Individual trials
        draw their seeds from a NumPy generator seeded with this value.
    randomise_physics : bool, optional
        When True, randomly perturb the physical parameters between trials.
        Not implemented in this harness; reserved for future use.
    noise_std : float, optional
        Standard deviation of additive Gaussian noise applied to the state
        trajectories before metric computation.

    Returns
    -------
    list of dict, dict
        A list containing the raw metrics for each trial and a dictionary
        mapping metric names to tuples ``(mean, ci)`` where ``ci`` is
        half the width of the 95 % confidence interval.
    """
    rng = np.random.default_rng(int(seed))
    metrics_list: List[Dict[str, float]] = []
    # Determine maximum allowed control force from a reference controller
    ref_ctrl = controller_factory(np.zeros(controller_factory.n_gains))
    max_force = getattr(ref_ctrl, "max_force", 150.0)
    for _ in range(int(n_trials)):
        trial_seed = int(rng.integers(0, 2**32 - 1))
        # Execute vectorised batch simulation for a single controller
        try:
            t, x_b, u_b, sigma_b = simulate_system_batch(
                controller_factory,
                np.array([np.zeros(controller_factory.n_gains)], dtype=float),
                sim_time=cfg.simulation.duration,
                dt=cfg.simulation.dt,
                u_max=max_force,
                seed=trial_seed,
            )
        except TypeError:
            # Fallback to signature without dt
            t, x_b, u_b, sigma_b = simulate_system_batch(
                controller_factory,
                np.array([np.zeros(controller_factory.n_gains)], dtype=float),
                sim_time=cfg.simulation.duration,
                u_max=max_force,
                seed=trial_seed,
            )
        # Add optional measurement noise
        if float(noise_std) > 0.0:
            noise = rng.normal(0.0, float(noise_std), size=x_b.shape)
            x_noisy = x_b + noise
        else:
            x_noisy = x_b
        # Compute metrics for this trial
        metrics = compute_metrics(t, x_noisy, u_b, sigma_b, max_force=max_force)
        metrics_list.append(metrics)
    # Convert metrics per key into arrays
    keys = metrics_list[0].keys()
    data = {k: np.array([m[k] for m in metrics_list], dtype=float) for k in keys}
    # Compute 95 % confidence intervals using standard error
    z = 1.96  # Quantile for two‑sided 95 % interval of a normal
    ci_results: Dict[str, Tuple[float, float]] = {}
    for k, vals in data.items():
        mean_val = float(np.mean(vals))
        # Sample standard deviation with Bessel’s correction
        sem = float(np.std(vals, ddof=1) / np.sqrt(len(vals)))
        ci_width = float(z * sem)
        ci_results[k] = (mean_val, ci_width)
    return metrics_list, ci_results