#==========================================================================================\\\
#=================== src/benchmarks/statistical_benchmarks_v2.py ========================\\\
#==========================================================================================\\\
"""
Statistical benchmarking utilities for the Double Inverted Pendulum project.

This is the refactored version using modular architecture while maintaining
full backward compatibility with the original statistical_benchmarks.py.

The module now delegates to specialized submodules:
- **metrics/**: Performance metric calculations
- **core/**: Trial execution and orchestration
- **statistics/**: Confidence interval analysis

This refactoring provides:
* **Modularity**: Clear separation of concerns
* **Extensibility**: Easy addition of new metrics or analysis methods
* **Maintainability**: Smaller, focused modules
* **Testability**: Individual components can be tested in isolation
* **Compatibility**: Original API preserved for existing code

Usage remains identical to the original:
    from src.benchmarks.statistical_benchmarks_v2 import run_trials

    metrics_list, ci_results = run_trials(controller_factory, cfg)
"""

from __future__ import annotations

from typing import Callable, Dict, Any, List, Tuple, Optional
import numpy as np

# Import from new modular structure
from .metrics import compute_basic_metrics
from .core import run_multiple_trials, validate_trial_configuration
from .statistics import compute_basic_confidence_intervals


def compute_metrics(
    t: np.ndarray,
    x: np.ndarray,
    u: np.ndarray,
    sigma: np.ndarray,
    max_force: float,
) -> Dict[str, float]:
    """Compute performance metrics for a batch of trajectories.

    This function maintains exact compatibility with the original
    implementation while delegating to the new modular structure.

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
        outputs. (Not used in basic metrics but preserved for compatibility)
    max_force : float
        Maximum allowable magnitude of the control input.  Used to count
        constraint violations.

    Returns
    -------
    dict
        Mapping of metric names to scalar values.  Each metric is averaged
        across the batch dimension.
    """
    # Delegate to new modular metrics system
    return compute_basic_metrics(t, x, u, max_force)


def run_trials(
    controller_factory: Callable[[np.ndarray], Any],
    cfg: Any,
    n_trials: int = 30,
    seed: int = 1234,
    randomise_physics: bool = False,
    noise_std: float = 0.0,
) -> Tuple[List[Dict[str, float]], Dict[str, Tuple[float, float]]]:
    """Run multiple simulations and return per‑trial metrics with confidence intervals.

    This function maintains exact compatibility with the original implementation
    while using the new modular architecture under the hood.

    The function executes ``n_trials`` independent simulations of the
    double inverted pendulum under the supplied controller factory and
    configuration.  For each trial it collects performance metrics and
    computes a 95 % confidence interval for the mean of each metric.  A
    sample size of at least 25–30 trials is recommended to invoke the
    Central Limit Theorem for skewed distributions.

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
        half the width of the 95 % confidence interval.
    """
    # Validate configuration before starting
    validate_trial_configuration(controller_factory, cfg, n_trials)

    # Execute trials using new modular core
    metrics_list = run_multiple_trials(
        controller_factory=controller_factory,
        cfg=cfg,
        n_trials=n_trials,
        seed=seed,
        randomise_physics=randomise_physics,
        noise_std=noise_std
    )

    # Compute confidence intervals using new statistics module
    ci_results = compute_basic_confidence_intervals(
        metrics_list=metrics_list,
        confidence_level=0.95
    )

    return metrics_list, ci_results


# Convenience functions for advanced analysis using new modules
def run_trials_with_advanced_statistics(
    controller_factory: Callable[[np.ndarray], Any],
    cfg: Any,
    n_trials: int = 30,
    seed: int = 1234,
    confidence_level: float = 0.95,
    use_bootstrap: bool = False,
    **kwargs
) -> Tuple[List[Dict[str, float]], Dict[str, Any]]:
    """Run trials with advanced statistical analysis.

    This function extends the original capability with additional
    statistical analysis options.

    Parameters
    ----------
    controller_factory, cfg, n_trials, seed :
        Same as run_trials()
    confidence_level : float, optional
        Confidence level for intervals (default 0.95)
    use_bootstrap : bool, optional
        Whether to use bootstrap confidence intervals
    **kwargs :
        Additional arguments passed to trial runner

    Returns
    -------
    list of dict, dict
        Metrics list and comprehensive statistical analysis results
    """
    from .statistics import (
        compute_t_confidence_intervals,
        compute_bootstrap_confidence_intervals,
        perform_statistical_tests
    )

    # Run trials
    metrics_list = run_multiple_trials(
        controller_factory=controller_factory,
        cfg=cfg,
        n_trials=n_trials,
        seed=seed,
        **kwargs
    )

    # Advanced statistical analysis
    if use_bootstrap:
        ci_results = compute_bootstrap_confidence_intervals(
            metrics_list, confidence_level=confidence_level
        )
    else:
        ci_results = compute_t_confidence_intervals(
            metrics_list, confidence_level=confidence_level
        )

    # Additional statistical tests
    test_results = perform_statistical_tests(metrics_list)

    # Combine results
    analysis_results = {
        "confidence_intervals": ci_results,
        "statistical_tests": test_results,
        "sample_size": len(metrics_list),
        "confidence_level": confidence_level,
        "method": "bootstrap" if use_bootstrap else "t-distribution"
    }

    return metrics_list, analysis_results


def compare_controllers(
    controller_factory_a: Callable[[np.ndarray], Any],
    controller_factory_b: Callable[[np.ndarray], Any],
    cfg: Any,
    n_trials: int = 30,
    seed: int = 1234,
    **kwargs
) -> Dict[str, Any]:
    """Compare two controllers using statistical analysis.

    Parameters
    ----------
    controller_factory_a, controller_factory_b : Callable
        Controller factories to compare
    cfg : Any
        Configuration object
    n_trials : int, optional
        Number of trials per controller
    seed : int, optional
        Base random seed
    **kwargs :
        Additional arguments

    Returns
    -------
    dict
        Comprehensive comparison results
    """
    from .statistics import compare_metric_distributions

    # Run trials for both controllers
    metrics_a = run_multiple_trials(controller_factory_a, cfg, n_trials, seed, **kwargs)
    metrics_b = run_multiple_trials(controller_factory_b, cfg, n_trials, seed + 1000, **kwargs)

    # Statistical comparison
    comparison_results = compare_metric_distributions(metrics_a, metrics_b)

    return {
        "controller_a_metrics": metrics_a,
        "controller_b_metrics": metrics_b,
        "statistical_comparison": comparison_results,
        "n_trials_per_controller": n_trials
    }