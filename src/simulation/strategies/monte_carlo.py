#==========================================================================================\\\
#====================== src/simulation/strategies/monte_carlo.py ====================\\\
#==========================================================================================\\\

"""Monte Carlo simulation strategy for statistical analysis."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
import numpy as np

from ..core.interfaces import SimulationStrategy
from ..orchestrators.parallel import ParallelOrchestrator


class MonteCarloStrategy(SimulationStrategy):
    """Monte Carlo simulation strategy for statistical analysis."""

    def __init__(self, n_samples: int = 1000, parallel: bool = True, max_workers: Optional[int] = None):
        """Initialize Monte Carlo strategy.

        Parameters
        ----------
        n_samples : int, optional
            Number of Monte Carlo samples
        parallel : bool, optional
            Whether to use parallel execution
        max_workers : int, optional
            Maximum number of parallel workers
        """
        self.n_samples = n_samples
        self.parallel = parallel
        self.max_workers = max_workers

    def analyze(self,
               simulation_fn: Callable,
               parameters: Dict[str, Any],
               **kwargs) -> Dict[str, Any]:
        """Perform Monte Carlo analysis.

        Parameters
        ----------
        simulation_fn : callable
            Simulation function to analyze
        parameters : dict
            Analysis parameters including distributions
        **kwargs
            Additional options

        Returns
        -------
        dict
            Monte Carlo analysis results
        """
        # Extract parameter distributions
        param_distributions = parameters.get('distributions', {})
        fixed_params = parameters.get('fixed', {})

        # Generate samples
        samples = self._generate_samples(param_distributions)

        # Run simulations
        if self.parallel:
            results = self._run_parallel_simulations(simulation_fn, samples, fixed_params, **kwargs)
        else:
            results = self._run_sequential_simulations(simulation_fn, samples, fixed_params, **kwargs)

        # Analyze results
        analysis = self._analyze_results(results, samples)

        return analysis

    def _generate_samples(self, distributions: Dict[str, Any]) -> List[Dict[str, float]]:
        """Generate Monte Carlo parameter samples."""
        samples = []

        for _ in range(self.n_samples):
            sample = {}
            for param_name, distribution in distributions.items():
                if distribution['type'] == 'normal':
                    sample[param_name] = np.random.normal(
                        distribution['mean'], distribution['std']
                    )
                elif distribution['type'] == 'uniform':
                    sample[param_name] = np.random.uniform(
                        distribution['low'], distribution['high']
                    )
                elif distribution['type'] == 'constant':
                    sample[param_name] = distribution['value']
                else:
                    raise ValueError(f"Unknown distribution type: {distribution['type']}")

            samples.append(sample)

        return samples

    def _run_parallel_simulations(self,
                                 simulation_fn: Callable,
                                 samples: List[Dict[str, float]],
                                 fixed_params: Dict[str, Any],
                                 **kwargs) -> List[Any]:
        """Run simulations in parallel."""
        # This would integrate with the parallel orchestrator
        # For now, simplified implementation
        results = []
        for sample in samples:
            combined_params = {**fixed_params, **sample}
            try:
                result = simulation_fn(combined_params, **kwargs)
                results.append(result)
            except Exception as e:
                results.append(None)  # Failed simulation

        return results

    def _run_sequential_simulations(self,
                                   simulation_fn: Callable,
                                   samples: List[Dict[str, float]],
                                   fixed_params: Dict[str, Any],
                                   **kwargs) -> List[Any]:
        """Run simulations sequentially."""
        results = []
        for sample in samples:
            combined_params = {**fixed_params, **sample}
            try:
                result = simulation_fn(combined_params, **kwargs)
                results.append(result)
            except Exception as e:
                results.append(None)  # Failed simulation

        return results

    def _analyze_results(self, results: List[Any], samples: List[Dict[str, float]]) -> Dict[str, Any]:
        """Analyze Monte Carlo results."""
        # Filter successful results
        successful_results = [r for r in results if r is not None]
        success_rate = len(successful_results) / len(results)

        if not successful_results:
            return {
                'success_rate': 0.0,
                'error': 'No successful simulations'
            }

        # Extract metrics from results
        metrics = self._extract_metrics(successful_results)

        # Compute statistics
        statistics = {}
        for metric_name, values in metrics.items():
            statistics[metric_name] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values),
                'percentiles': {
                    '5': np.percentile(values, 5),
                    '25': np.percentile(values, 25),
                    '50': np.percentile(values, 50),
                    '75': np.percentile(values, 75),
                    '95': np.percentile(values, 95)
                }
            }

        return {
            'success_rate': success_rate,
            'n_successful': len(successful_results),
            'n_total': len(results),
            'statistics': statistics,
            'raw_results': successful_results if len(successful_results) < 100 else None
        }

    def _extract_metrics(self, results: List[Any]) -> Dict[str, List[float]]:
        """Extract metrics from simulation results."""
        metrics = {}

        for result in results:
            if hasattr(result, 'get_states'):
                states = result.get_states()
                if len(states) > 0:
                    # Final state metrics
                    final_state = states[-1]
                    for i, value in enumerate(final_state):
                        key = f'final_state_{i}'
                        if key not in metrics:
                            metrics[key] = []
                        metrics[key].append(float(value))

                    # Trajectory metrics
                    if 'max_deviation' not in metrics:
                        metrics['max_deviation'] = []
                    metrics['max_deviation'].append(float(np.max(np.abs(states))))

        return metrics