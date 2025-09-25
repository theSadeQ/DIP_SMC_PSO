#==========================================================================================\\\
#======================== src/analysis/validation/core.py ========================\\\
#==========================================================================================\\\
"""
Core validation and trial execution utilities.

This module provides the core infrastructure for running validation trials,
managing experimental configurations, and coordinating statistical benchmarks.
"""

from typing import Dict, List, Any, Optional, Callable, Union, Tuple
import numpy as np
import time
import logging
import warnings
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial

logger = logging.getLogger(__name__)


class TrialConfiguration:
    """Configuration for validation trials."""

    def __init__(
        self,
        name: str,
        parameters: Dict[str, Any],
        repetitions: int = 10,
        timeout: Optional[float] = None,
        parallel: bool = False,
        random_seed: Optional[int] = None
    ):
        """
        Initialize trial configuration.

        Args:
            name: Name of the trial configuration
            parameters: Dictionary of trial parameters
            repetitions: Number of repetitions to run
            timeout: Optional timeout for each trial
            parallel: Whether to run trials in parallel
            random_seed: Optional random seed for reproducibility
        """
        self.name = name
        self.parameters = parameters
        self.repetitions = repetitions
        self.timeout = timeout
        self.parallel = parallel
        self.random_seed = random_seed

    def __repr__(self) -> str:
        return f"TrialConfiguration(name='{self.name}', repetitions={self.repetitions})"


class TrialResult:
    """Result from a single trial execution."""

    def __init__(
        self,
        trial_id: int,
        success: bool,
        metrics: Dict[str, Any],
        execution_time: float,
        error_message: Optional[str] = None
    ):
        """
        Initialize trial result.

        Args:
            trial_id: Unique identifier for this trial
            success: Whether the trial completed successfully
            metrics: Dictionary of computed metrics
            execution_time: Time taken to execute trial
            error_message: Optional error message if trial failed
        """
        self.trial_id = trial_id
        self.success = success
        self.metrics = metrics
        self.execution_time = execution_time
        self.error_message = error_message

    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"TrialResult(id={self.trial_id}, status={status}, time={self.execution_time:.3f}s)"


class TrialBatch:
    """Collection of trial results with analysis methods."""

    def __init__(self, configuration: TrialConfiguration, results: List[TrialResult]):
        """
        Initialize trial batch.

        Args:
            configuration: Configuration used for these trials
            results: List of trial results
        """
        self.configuration = configuration
        self.results = results

    @property
    def success_rate(self) -> float:
        """Get success rate for this batch."""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.success) / len(self.results)

    @property
    def successful_results(self) -> List[TrialResult]:
        """Get only successful results."""
        return [r for r in self.results if r.success]

    @property
    def failed_results(self) -> List[TrialResult]:
        """Get only failed results."""
        return [r for r in self.results if not r.success]

    def get_metric_values(self, metric_name: str) -> List[float]:
        """Get all values for a specific metric from successful trials."""
        values = []
        for result in self.successful_results:
            if metric_name in result.metrics:
                value = result.metrics[metric_name]
                if isinstance(value, (int, float)):
                    values.append(float(value))
        return values

    def get_summary_statistics(self, metric_name: str) -> Dict[str, float]:
        """Get summary statistics for a metric."""
        values = self.get_metric_values(metric_name)
        if not values:
            return {'count': 0, 'mean': 0.0, 'std': 0.0, 'min': 0.0, 'max': 0.0}

        return {
            'count': len(values),
            'mean': float(np.mean(values)),
            'std': float(np.std(values)),
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'median': float(np.median(values))
        }

    def __repr__(self) -> str:
        return f"TrialBatch(config={self.configuration.name}, results={len(self.results)}, success_rate={self.success_rate:.1%})"


def validate_trial_configuration(config: TrialConfiguration) -> List[str]:
    """
    Validate trial configuration for common issues.

    Args:
        config: Configuration to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not config.name or not config.name.strip():
        errors.append("Trial name cannot be empty")

    if config.repetitions < 1:
        errors.append("Repetitions must be at least 1")

    if config.repetitions > 10000:
        errors.append("Repetitions should not exceed 10000 for practical reasons")

    if config.timeout is not None and config.timeout <= 0:
        errors.append("Timeout must be positive if specified")

    if not isinstance(config.parameters, dict):
        errors.append("Parameters must be a dictionary")

    return errors


def run_single_trial(
    trial_function: Callable,
    trial_id: int,
    parameters: Dict[str, Any],
    timeout: Optional[float] = None,
    random_seed: Optional[int] = None
) -> TrialResult:
    """
    Run a single trial with error handling and timing.

    Args:
        trial_function: Function to execute for this trial
        trial_id: Unique identifier for this trial
        parameters: Parameters to pass to trial function
        timeout: Optional timeout for execution
        random_seed: Optional random seed

    Returns:
        TrialResult with execution results
    """
    start_time = time.time()

    try:
        # Set random seed if provided
        if random_seed is not None:
            np.random.seed(random_seed + trial_id)

        # Execute trial function
        if timeout is not None:
            # Note: Real timeout implementation would require more complex setup
            # This is a simplified version
            metrics = trial_function(**parameters)
        else:
            metrics = trial_function(**parameters)

        execution_time = time.time() - start_time

        # Validate metrics
        if not isinstance(metrics, dict):
            return TrialResult(
                trial_id=trial_id,
                success=False,
                metrics={},
                execution_time=execution_time,
                error_message="Trial function must return a dictionary of metrics"
            )

        return TrialResult(
            trial_id=trial_id,
            success=True,
            metrics=metrics,
            execution_time=execution_time
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.warning(f"Trial {trial_id} failed: {str(e)}")

        return TrialResult(
            trial_id=trial_id,
            success=False,
            metrics={},
            execution_time=execution_time,
            error_message=str(e)
        )


def run_multiple_trials(
    trial_function: Callable,
    configuration: TrialConfiguration,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> TrialBatch:
    """
    Run multiple trials according to configuration.

    Args:
        trial_function: Function to execute for each trial
        configuration: Trial configuration
        progress_callback: Optional callback for progress updates

    Returns:
        TrialBatch containing all results
    """
    # Validate configuration
    validation_errors = validate_trial_configuration(configuration)
    if validation_errors:
        raise ValueError(f"Invalid trial configuration: {', '.join(validation_errors)}")

    logger.info(f"Running {configuration.repetitions} trials for '{configuration.name}'")

    results = []

    if configuration.parallel and configuration.repetitions > 1:
        # Run trials in parallel
        max_workers = min(configuration.repetitions, 4)  # Reasonable limit

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all trials
            futures = []
            for i in range(configuration.repetitions):
                future = executor.submit(
                    run_single_trial,
                    trial_function,
                    i,
                    configuration.parameters,
                    configuration.timeout,
                    configuration.random_seed
                )
                futures.append(future)

            # Collect results
            for i, future in enumerate(futures):
                try:
                    result = future.result()
                    results.append(result)

                    if progress_callback:
                        progress_callback(i + 1, configuration.repetitions)

                except Exception as e:
                    logger.error(f"Failed to get result from trial {i}: {str(e)}")
                    results.append(TrialResult(
                        trial_id=i,
                        success=False,
                        metrics={},
                        execution_time=0.0,
                        error_message=f"Execution error: {str(e)}"
                    ))
    else:
        # Run trials sequentially
        for i in range(configuration.repetitions):
            result = run_single_trial(
                trial_function,
                i,
                configuration.parameters,
                configuration.timeout,
                configuration.random_seed
            )
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, configuration.repetitions)

    batch = TrialBatch(configuration, results)
    logger.info(f"Completed {configuration.name}: {len(results)} trials, {batch.success_rate:.1%} success rate")

    return batch


def compare_trial_batches(
    batch1: TrialBatch,
    batch2: TrialBatch,
    metric_name: str
) -> Dict[str, Any]:
    """
    Compare two trial batches for a specific metric.

    Args:
        batch1: First batch of trials
        batch2: Second batch of trials
        metric_name: Name of metric to compare

    Returns:
        Dictionary containing comparison statistics
    """
    values1 = batch1.get_metric_values(metric_name)
    values2 = batch2.get_metric_values(metric_name)

    if not values1 or not values2:
        return {
            'comparison_possible': False,
            'reason': 'Insufficient data for comparison'
        }

    # Basic statistics
    stats1 = batch1.get_summary_statistics(metric_name)
    stats2 = batch2.get_summary_statistics(metric_name)

    # Simple comparison
    mean_difference = stats2['mean'] - stats1['mean']
    relative_change = (mean_difference / stats1['mean']) if stats1['mean'] != 0 else 0.0

    return {
        'comparison_possible': True,
        'batch1_stats': stats1,
        'batch2_stats': stats2,
        'mean_difference': mean_difference,
        'relative_change': relative_change,
        'batch1_name': batch1.configuration.name,
        'batch2_name': batch2.configuration.name
    }


def create_standard_trial_configurations() -> List[TrialConfiguration]:
    """
    Create standard trial configurations for common validation scenarios.

    Returns:
        List of standard trial configurations
    """
    configurations = [
        TrialConfiguration(
            name="quick_validation",
            parameters={'duration': 1.0, 'tolerance': 0.1},
            repetitions=5,
            timeout=10.0
        ),
        TrialConfiguration(
            name="standard_validation",
            parameters={'duration': 5.0, 'tolerance': 0.05},
            repetitions=20,
            timeout=30.0
        ),
        TrialConfiguration(
            name="extended_validation",
            parameters={'duration': 10.0, 'tolerance': 0.01},
            repetitions=50,
            timeout=60.0,
            parallel=True
        ),
        TrialConfiguration(
            name="stress_test",
            parameters={'duration': 20.0, 'tolerance': 0.001},
            repetitions=100,
            timeout=120.0,
            parallel=True
        )
    ]

    return configurations


def mock_trial_function(**parameters) -> Dict[str, float]:
    """
    Mock trial function for testing validation infrastructure.

    Args:
        **parameters: Trial parameters

    Returns:
        Dictionary of mock metrics
    """
    duration = parameters.get('duration', 1.0)
    tolerance = parameters.get('tolerance', 0.1)

    # Simulate some work
    time.sleep(min(duration * 0.001, 0.01))  # Very short sleep

    # Generate mock metrics
    base_performance = 1.0 - tolerance * np.random.random()
    noise = 0.1 * np.random.randn()

    return {
        'performance': base_performance + noise,
        'error': abs(noise),
        'duration': duration,
        'success_metric': 1.0 if abs(noise) < tolerance else 0.0
    }