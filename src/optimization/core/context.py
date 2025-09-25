#==========================================================================================\\\
#========================== src/optimization/core/context.py ==========================\\\
#==========================================================================================\\\

"""Optimization context and configuration management."""

from __future__ import annotations

from typing import Any, Dict, Optional, Union
import numpy as np
from pathlib import Path

from .interfaces import OptimizationProblem, Optimizer, ConvergenceMonitor


class OptimizationContext:
    """Context manager for optimization runs."""

    def __init__(self,
                 random_seed: Optional[int] = None,
                 working_directory: Optional[Union[str, Path]] = None,
                 config: Optional[Dict[str, Any]] = None):
        """Initialize optimization context.

        Parameters
        ----------
        random_seed : int, optional
            Random seed for reproducibility
        working_directory : str or Path, optional
            Working directory for output files
        config : dict, optional
            Configuration dictionary
        """
        self.random_seed = random_seed
        self.working_directory = Path(working_directory) if working_directory else Path.cwd()
        self.config = config or {}

        # Initialize random number generator
        if random_seed is not None:
            self.rng = np.random.default_rng(random_seed)
        else:
            self.rng = np.random.default_rng()

        # Optimization components
        self.problem = None
        self.optimizer = None
        self.convergence_monitor = None

        # Results and state
        self.results = {}
        self.iteration_data = []

    def set_problem(self, problem: OptimizationProblem) -> 'OptimizationContext':
        """Set optimization problem."""
        self.problem = problem
        return self

    def set_optimizer(self, optimizer: Optimizer) -> 'OptimizationContext':
        """Set optimizer."""
        self.optimizer = optimizer
        return self

    def set_convergence_monitor(self, monitor: ConvergenceMonitor) -> 'OptimizationContext':
        """Set convergence monitor."""
        self.convergence_monitor = monitor
        if self.optimizer:
            self.optimizer.set_convergence_monitor(monitor)
        return self

    def run_optimization(self, **kwargs) -> 'OptimizationResult':
        """Run optimization with current configuration."""
        if self.problem is None:
            raise ValueError("Optimization problem must be set")
        if self.optimizer is None:
            raise ValueError("Optimizer must be set")

        # Set up callback to collect iteration data
        self.iteration_data = []

        def iteration_callback(iteration, best_value, parameters, **cb_kwargs):
            self.iteration_data.append({
                'iteration': iteration,
                'best_value': best_value,
                'parameters': parameters.copy(),
                **cb_kwargs
            })

        self.optimizer.set_callback(iteration_callback)

        # Run optimization
        result = self.optimizer.optimize(self.problem, rng=self.rng, **kwargs)

        # Store results
        self.results = {
            'optimization_result': result,
            'iteration_data': self.iteration_data,
            'problem_name': self.problem.name,
            'algorithm_name': self.optimizer.algorithm_name,
            'random_seed': self.random_seed
        }

        return result

    def save_results(self, filepath: Optional[Union[str, Path]] = None) -> Path:
        """Save optimization results to file."""
        import json
        import pickle

        if filepath is None:
            filepath = self.working_directory / "optimization_results.pkl"
        else:
            filepath = Path(filepath)

        # Save detailed results with pickle
        with open(filepath, 'wb') as f:
            pickle.dump(self.results, f)

        # Also save JSON summary
        json_path = filepath.with_suffix('.json')
        summary = self._create_results_summary()

        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2)

        return filepath

    def load_results(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """Load optimization results from file."""
        import pickle

        filepath = Path(filepath)
        with open(filepath, 'rb') as f:
            self.results = pickle.load(f)

        return self.results

    def _create_results_summary(self) -> Dict[str, Any]:
        """Create JSON-serializable results summary."""
        if not self.results:
            return {}

        result = self.results['optimization_result']

        summary = {
            'problem_name': self.results.get('problem_name', 'Unknown'),
            'algorithm_name': self.results.get('algorithm_name', 'Unknown'),
            'random_seed': self.results.get('random_seed'),
            'optimization_result': {
                'success': result.success,
                'status': result.status.value,
                'message': result.message,
                'optimal_value': float(result.fun),
                'optimal_parameters': result.x.tolist(),
                'iterations': result.nit,
                'function_evaluations': result.nfev
            },
            'convergence_summary': {
                'total_iterations': len(self.iteration_data),
                'best_value_history': [float(data['best_value']) for data in self.iteration_data[-100:]],  # Last 100
                'final_parameters': self.iteration_data[-1]['parameters'].tolist() if self.iteration_data else None
            }
        }

        return summary

    def create_optimizer_factory(self, algorithm_name: str, **kwargs) -> Optimizer:
        """Factory method to create optimizers."""
        algorithm_name = algorithm_name.lower()

        if algorithm_name == 'pso':
            from ..algorithms.swarm.pso import ParticleSwarmOptimizer
            return ParticleSwarmOptimizer(self.problem.parameter_space, **kwargs)

        elif algorithm_name == 'ga':
            from ..algorithms.evolutionary.genetic import GeneticAlgorithm
            return GeneticAlgorithm(self.problem.parameter_space, **kwargs)

        elif algorithm_name == 'de':
            from ..algorithms.evolutionary.differential import DifferentialEvolution
            return DifferentialEvolution(self.problem.parameter_space, **kwargs)

        elif algorithm_name == 'cma_es':
            from ..algorithms.evolutionary.cma_es import CMAES
            return CMAES(self.problem.parameter_space, **kwargs)

        elif algorithm_name == 'nelder_mead':
            from ..algorithms.gradient.simplex import NelderMead
            return NelderMead(self.problem.parameter_space, **kwargs)

        elif algorithm_name == 'bayesian':
            from ..algorithms.bayesian.gaussian_process import BayesianOptimization
            return BayesianOptimization(self.problem.parameter_space, **kwargs)

        else:
            raise ValueError(f"Unknown algorithm: {algorithm_name}")

    def get_available_algorithms(self) -> List[str]:
        """Get list of available optimization algorithms."""
        return [
            'pso',           # Particle Swarm Optimization
            'ga',            # Genetic Algorithm
            'de',            # Differential Evolution
            'cma_es',        # CMA-ES
            'nelder_mead',   # Nelder-Mead Simplex
            'bayesian'       # Bayesian Optimization
        ]


# Convenience function for quick optimization
def optimize(problem: OptimizationProblem,
            algorithm: str = 'pso',
            random_seed: Optional[int] = None,
            **kwargs) -> 'OptimizationResult':
    """Quick optimization function.

    Parameters
    ----------
    problem : OptimizationProblem
        Problem to optimize
    algorithm : str, optional
        Algorithm name (default: 'pso')
    random_seed : int, optional
        Random seed
    **kwargs
        Algorithm-specific parameters

    Returns
    -------
    OptimizationResult
        Optimization results
    """
    context = OptimizationContext(random_seed=random_seed)
    context.set_problem(problem)

    optimizer = context.create_optimizer_factory(algorithm, **kwargs)
    context.set_optimizer(optimizer)

    return context.run_optimization()