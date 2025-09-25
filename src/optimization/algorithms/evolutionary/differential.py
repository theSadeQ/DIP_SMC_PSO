#==========================================================================================\\\
#============ src/optimization/algorithms/evolutionary/differential.py =================\\\
#==========================================================================================\\\

"""Differential Evolution optimization algorithm."""

from __future__ import annotations

import numpy as np
from typing import Any, Dict, Optional, Tuple
import logging

from ...core.interfaces import (
    PopulationBasedOptimizer, OptimizationProblem, OptimizationResult,
    ConvergenceStatus, ParameterSpace
)


class DifferentialEvolution(PopulationBasedOptimizer):
    """Differential Evolution algorithm for global optimization.

    DE is a robust evolutionary algorithm particularly effective for
    continuous optimization problems with multimodal landscapes.
    """

    def __init__(self,
                 parameter_space: ParameterSpace,
                 population_size: int = 50,
                 mutation_factor: float = 0.8,
                 crossover_probability: float = 0.7,
                 strategy: str = 'best/1/bin',
                 max_iterations: int = 1000,
                 tolerance: float = 1e-6,
                 adaptive_parameters: bool = False,
                 **kwargs):
        """Initialize Differential Evolution optimizer.

        Parameters
        ----------
        parameter_space : ParameterSpace
            Parameter space to optimize over
        population_size : int, optional
            Population size (should be at least 4 * dimensions)
        mutation_factor : float, optional
            Differential weight F (0 < F <= 2)
        crossover_probability : float, optional
            Crossover probability CR (0 <= CR <= 1)
        strategy : str, optional
            DE strategy ('rand/1/bin', 'best/1/bin', 'currentToBest/1/bin', etc.)
        max_iterations : int, optional
            Maximum number of iterations
        tolerance : float, optional
            Convergence tolerance
        adaptive_parameters : bool, optional
            Whether to adapt F and CR during evolution
        **kwargs
            Additional parameters
        """
        # Ensure minimum population size
        min_pop_size = max(4 * parameter_space.dimensions, 15)
        if population_size < min_pop_size:
            population_size = min_pop_size

        super().__init__(parameter_space, population_size, **kwargs)

        self.mutation_factor = mutation_factor
        self.crossover_probability = crossover_probability
        self.strategy = strategy
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.adaptive_parameters = adaptive_parameters

        # Validate parameters
        if not 0 < mutation_factor <= 2:
            raise ValueError("Mutation factor must be in (0, 2]")
        if not 0 <= crossover_probability <= 1:
            raise ValueError("Crossover probability must be in [0, 1]")

        # State variables
        self.population = None
        self.fitness = None
        self.best_index = None
        self.best_fitness = np.inf
        self.best_individual = None

        # Statistics
        self.iteration_count = 0
        self.fitness_history = []

    @property
    def algorithm_name(self) -> str:
        """Algorithm name."""
        return "Differential Evolution"

    @property
    def supports_constraints(self) -> bool:
        """DE can handle constraints through penalty methods."""
        return True

    @property
    def supports_bounds(self) -> bool:
        """DE naturally supports parameter bounds."""
        return True

    def optimize(self, problem: OptimizationProblem, **kwargs) -> OptimizationResult:
        """Perform DE optimization."""
        # Extract options
        rng = kwargs.get('rng', np.random.default_rng())
        max_iter = kwargs.get('max_iterations', self.max_iterations)
        verbose = kwargs.get('verbose', False)

        # Initialize population
        self.initialize_population(rng)

        # Evaluate initial population
        self.fitness = problem.evaluate_objective_batch(self.population)
        self._update_best()

        # Evolution loop
        self.iteration_count = 0
        converged = False
        status = ConvergenceStatus.RUNNING

        for iteration in range(max_iter):
            self.iteration_count = iteration

            # Adaptive parameter adjustment
            if self.adaptive_parameters:
                self._adapt_parameters(iteration, max_iter)

            # Create new generation
            trial_population = self._create_trial_population(rng)

            # Evaluate trial population
            trial_fitness = problem.evaluate_objective_batch(trial_population)

            # Apply constraints if present
            if problem.constraints:
                trial_fitness = self._apply_constraint_penalties(trial_fitness, trial_population, problem)
                self.fitness = self._apply_constraint_penalties(self.fitness, self.population, problem)

            # Selection
            self._selection(trial_population, trial_fitness)

            # Update best
            self._update_best()

            # Record statistics
            self.fitness_history.append(self.best_fitness)

            # Check convergence
            if self.convergence_monitor:
                self.convergence_monitor.update(
                    iteration, self.best_fitness, self.best_individual,
                    population=self.population.copy(),
                    fitness=self.fitness.copy()
                )
                converged, status, message = self.convergence_monitor.check_convergence()
            else:
                # Simple convergence check
                if len(self.fitness_history) > 20:
                    recent_improvement = (
                        self.fitness_history[-20] - self.best_fitness
                    )
                    if recent_improvement < self.tolerance:
                        converged = True
                        status = ConvergenceStatus.TOLERANCE_REACHED
                        message = "Tolerance reached"

            # Callback
            if self._callback:
                self._callback(
                    iteration, self.best_fitness, self.best_individual,
                    population=self.population.copy(),
                    fitness=self.fitness.copy()
                )

            # Verbose output
            if verbose and iteration % 50 == 0:
                logging.info(f"Generation {iteration}: Best fitness = {self.best_fitness:.6f}")

            if converged:
                break

        # Determine final status
        if not converged:
            status = ConvergenceStatus.MAX_ITERATIONS
            message = "Maximum iterations reached"

        # Create result
        result = OptimizationResult(
            x=self.best_individual.copy(),
            fun=self.best_fitness,
            success=converged or status == ConvergenceStatus.MAX_ITERATIONS,
            status=status,
            message=message,
            nit=self.iteration_count + 1,
            nfev=(self.iteration_count + 1) * self.population_size,
            fitness_history=self.fitness_history.copy(),
            final_population=self.population.copy(),
            final_fitness=self.fitness.copy()
        )

        return result

    def initialize_population(self, rng: np.random.Generator) -> np.ndarray:
        """Initialize population randomly within bounds."""
        self.population = self.parameter_space.sample(self.population_size, rng)
        return self.population

    def update_population(self, population: np.ndarray, fitness: np.ndarray, **kwargs) -> np.ndarray:
        """Update population (used by base class interface)."""
        self.population = population
        self.fitness = fitness
        self._update_best()
        return self.population

    def _create_trial_population(self, rng: np.random.Generator) -> np.ndarray:
        """Create trial population using DE mutation and crossover."""
        trial_population = np.zeros_like(self.population)

        for i in range(self.population_size):
            # Mutation
            mutant = self._mutate(i, rng)

            # Crossover
            trial_population[i] = self._crossover(self.population[i], mutant, rng)

        return trial_population

    def _mutate(self, target_index: int, rng: np.random.Generator) -> np.ndarray:
        """Apply DE mutation strategy."""
        strategy = self.strategy.lower()

        if strategy == 'rand/1/bin':
            # DE/rand/1: Xi = Xr1 + F * (Xr2 - Xr3)
            indices = self._select_random_indices(target_index, 3, rng)
            r1, r2, r3 = indices
            mutant = self.population[r1] + self.mutation_factor * (
                self.population[r2] - self.population[r3]
            )

        elif strategy == 'best/1/bin':
            # DE/best/1: Xi = Xbest + F * (Xr1 - Xr2)
            indices = self._select_random_indices(target_index, 2, rng)
            r1, r2 = indices
            mutant = self.best_individual + self.mutation_factor * (
                self.population[r1] - self.population[r2]
            )

        elif strategy == 'currenttobest/1/bin':
            # DE/current-to-best/1: Xi = Xi + F * (Xbest - Xi) + F * (Xr1 - Xr2)
            indices = self._select_random_indices(target_index, 2, rng)
            r1, r2 = indices
            mutant = (self.population[target_index] +
                     self.mutation_factor * (self.best_individual - self.population[target_index]) +
                     self.mutation_factor * (self.population[r1] - self.population[r2]))

        else:
            raise ValueError(f"Unknown DE strategy: {self.strategy}")

        # Ensure mutant is within bounds
        return self.parameter_space.clip(mutant)

    def _crossover(self, target: np.ndarray, mutant: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """Apply binomial crossover."""
        trial = target.copy()

        # Ensure at least one parameter comes from mutant
        j_rand = rng.integers(0, len(target))

        # Binomial crossover
        for j in range(len(target)):
            if rng.random() < self.crossover_probability or j == j_rand:
                trial[j] = mutant[j]

        return trial

    def _select_random_indices(self, exclude: int, count: int, rng: np.random.Generator) -> np.ndarray:
        """Select random indices excluding the target index."""
        available = list(range(self.population_size))
        available.remove(exclude)
        return rng.choice(available, size=count, replace=False)

    def _selection(self, trial_population: np.ndarray, trial_fitness: np.ndarray) -> None:
        """Selection between current and trial populations."""
        improved = trial_fitness < self.fitness
        self.population[improved] = trial_population[improved]
        self.fitness[improved] = trial_fitness[improved]

    def _update_best(self) -> None:
        """Update best individual and fitness."""
        self.best_index = np.argmin(self.fitness)
        self.best_fitness = self.fitness[self.best_index]
        self.best_individual = self.population[self.best_index].copy()

    def _adapt_parameters(self, iteration: int, max_iterations: int) -> None:
        """Adapt F and CR parameters during evolution."""
        # Simple linear adaptation
        progress = iteration / max_iterations

        # Decrease F over time (exploration -> exploitation)
        self.mutation_factor = 0.9 - 0.4 * progress

        # Increase CR over time (more aggressive crossover)
        self.crossover_probability = 0.1 + 0.8 * progress

    def _apply_constraint_penalties(self,
                                  fitness: np.ndarray,
                                  population: np.ndarray,
                                  problem: OptimizationProblem) -> np.ndarray:
        """Apply constraint penalties to fitness values."""
        penalized_fitness = fitness.copy()

        for i, individual in enumerate(population):
            satisfied, violations = problem.check_constraints(individual)
            if not satisfied:
                penalty = sum(max(0, violation) for violation in violations)
                penalized_fitness[i] += 1000 * penalty

        return penalized_fitness

    def get_population_statistics(self) -> Dict[str, Any]:
        """Get detailed population statistics."""
        return {
            'iteration': self.iteration_count,
            'best_fitness': self.best_fitness,
            'best_individual': self.best_individual.copy() if self.best_individual is not None else None,
            'fitness_history': self.fitness_history.copy(),
            'current_mutation_factor': self.mutation_factor,
            'current_crossover_probability': self.crossover_probability,
            'population_diversity': np.std(self.population, axis=0).mean() if self.population is not None else 0.0,
            'population_size': self.population_size,
            'strategy': self.strategy
        }