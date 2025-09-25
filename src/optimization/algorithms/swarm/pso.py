#==========================================================================================\\\
#======================= src/optimization/algorithms/swarm/pso.py =====================\\\
#==========================================================================================\\\

"""Enhanced Particle Swarm Optimization with framework integration."""

from __future__ import annotations

import numpy as np
from typing import Any, Callable, Dict, Optional, Tuple
import logging

from ...core.interfaces import (
    PopulationBasedOptimizer, OptimizationProblem, OptimizationResult,
    ConvergenceStatus, ParameterSpace
)


class ParticleSwarmOptimizer(PopulationBasedOptimizer):
    """Professional Particle Swarm Optimization algorithm.

    This implementation provides a modern, framework-integrated PSO algorithm
    with advanced features for control engineering applications.
    """

    def __init__(self,
                 parameter_space: ParameterSpace,
                 population_size: int = 50,
                 inertia_weight: float = 0.729,
                 cognitive_weight: float = 1.49445,
                 social_weight: float = 1.49445,
                 max_iterations: int = 1000,
                 tolerance: float = 1e-6,
                 adaptive_weights: bool = True,
                 velocity_clamping: bool = True,
                 **kwargs):
        """Initialize PSO optimizer.

        Parameters
        ----------
        parameter_space : ParameterSpace
            Parameter space to optimize over
        population_size : int, optional
            Number of particles in swarm
        inertia_weight : float, optional
            Inertia weight (w)
        cognitive_weight : float, optional
            Cognitive acceleration coefficient (c1)
        social_weight : float, optional
            Social acceleration coefficient (c2)
        max_iterations : int, optional
            Maximum number of iterations
        tolerance : float, optional
            Convergence tolerance
        adaptive_weights : bool, optional
            Whether to use adaptive weight adjustment
        velocity_clamping : bool, optional
            Whether to clamp particle velocities
        **kwargs
            Additional parameters
        """
        super().__init__(parameter_space, population_size, **kwargs)

        # PSO Parameters
        self.inertia_weight = inertia_weight
        self.cognitive_weight = cognitive_weight
        self.social_weight = social_weight
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.adaptive_weights = adaptive_weights
        self.velocity_clamping = velocity_clamping

        # Adaptive parameters
        self.initial_inertia = inertia_weight
        self.final_inertia = 0.4
        self.initial_c1 = cognitive_weight
        self.final_c1 = 0.5
        self.initial_c2 = social_weight
        self.final_c2 = 2.5

        # State variables
        self.positions = None
        self.velocities = None
        self.personal_best_positions = None
        self.personal_best_fitness = None
        self.global_best_position = None
        self.global_best_fitness = None

        # Statistics
        self.iteration_count = 0
        self.fitness_history = []
        self.diversity_history = []

    @property
    def algorithm_name(self) -> str:
        """Algorithm name."""
        return "Particle Swarm Optimization"

    @property
    def supports_constraints(self) -> bool:
        """PSO can handle constraints through penalty methods."""
        return True

    @property
    def supports_bounds(self) -> bool:
        """PSO naturally supports parameter bounds."""
        return True

    def optimize(self, problem: OptimizationProblem, **kwargs) -> OptimizationResult:
        """Perform PSO optimization.

        Parameters
        ----------
        problem : OptimizationProblem
            Problem to optimize
        **kwargs
            Additional options (rng, max_iterations, etc.)

        Returns
        -------
        OptimizationResult
            Optimization results
        """
        # Extract options
        rng = kwargs.get('rng', np.random.default_rng())
        max_iter = kwargs.get('max_iterations', self.max_iterations)
        verbose = kwargs.get('verbose', False)

        # Initialize swarm
        self.initialize_population(rng)

        # Evaluate initial population
        fitness = problem.evaluate_objective_batch(self.positions)
        self._update_personal_bests(fitness)
        self._update_global_best()

        # Optimization loop
        self.iteration_count = 0
        converged = False
        status = ConvergenceStatus.RUNNING

        for iteration in range(max_iter):
            self.iteration_count = iteration

            # Update PSO parameters if adaptive
            if self.adaptive_weights:
                self._update_adaptive_parameters(iteration, max_iter)

            # Update velocities and positions
            self._update_velocities(rng)
            self._update_positions()

            # Evaluate new positions
            fitness = problem.evaluate_objective_batch(self.positions)

            # Apply constraints if present
            if problem.constraints:
                fitness = self._apply_constraint_penalties(fitness, problem)

            # Update personal and global bests
            self._update_personal_bests(fitness)
            self._update_global_best()

            # Record statistics
            self.fitness_history.append(self.global_best_fitness)
            diversity = self._calculate_diversity()
            self.diversity_history.append(diversity)

            # Check convergence
            if self.convergence_monitor:
                self.convergence_monitor.update(
                    iteration, self.global_best_fitness, self.global_best_position,
                    diversity=diversity, positions=self.positions.copy()
                )
                converged, status, message = self.convergence_monitor.check_convergence()
            else:
                # Simple convergence check
                if len(self.fitness_history) > 10:
                    recent_improvement = (
                        self.fitness_history[-10] - self.global_best_fitness
                    )
                    if recent_improvement < self.tolerance:
                        converged = True
                        status = ConvergenceStatus.TOLERANCE_REACHED
                        message = "Tolerance reached"

            # Callback
            if self._callback:
                self._callback(
                    iteration, self.global_best_fitness, self.global_best_position,
                    swarm_positions=self.positions.copy(),
                    swarm_fitness=fitness.copy(),
                    diversity=diversity
                )

            # Verbose output
            if verbose and iteration % 10 == 0:
                logging.info(f"Iteration {iteration}: Best fitness = {self.global_best_fitness:.6f}")

            # Check termination
            if converged:
                break

        # Determine final status
        if not converged:
            status = ConvergenceStatus.MAX_ITERATIONS
            message = "Maximum iterations reached"

        # Create result
        result = OptimizationResult(
            x=self.global_best_position.copy(),
            fun=self.global_best_fitness,
            success=converged or status == ConvergenceStatus.MAX_ITERATIONS,
            status=status,
            message=message,
            nit=self.iteration_count + 1,
            nfev=(self.iteration_count + 1) * self.population_size,
            fitness_history=self.fitness_history.copy(),
            diversity_history=self.diversity_history.copy(),
            final_positions=self.positions.copy(),
            final_fitness=fitness.copy()
        )

        return result

    def initialize_population(self, rng: np.random.Generator) -> np.ndarray:
        """Initialize particle positions and velocities."""
        # Initialize positions
        self.positions = self.parameter_space.sample(self.population_size, rng)

        # Initialize velocities (small random values)
        bounds = self.parameter_space.bounds
        velocity_range = (bounds[1] - bounds[0]) * 0.1  # 10% of parameter range
        self.velocities = rng.uniform(
            -velocity_range, velocity_range,
            size=(self.population_size, self.parameter_space.dimensions)
        )

        # Initialize personal bests
        self.personal_best_positions = self.positions.copy()
        self.personal_best_fitness = np.full(self.population_size, np.inf)

        # Initialize global best
        self.global_best_position = None
        self.global_best_fitness = np.inf

        return self.positions

    def update_population(self, population: np.ndarray, fitness: np.ndarray, **kwargs) -> np.ndarray:
        """Update population (used by base class interface)."""
        self.positions = population
        self._update_personal_bests(fitness)
        self._update_global_best()
        return self.positions

    def _update_velocities(self, rng: np.random.Generator) -> None:
        """Update particle velocities."""
        # Random components
        r1 = rng.random((self.population_size, self.parameter_space.dimensions))
        r2 = rng.random((self.population_size, self.parameter_space.dimensions))

        # Cognitive component
        cognitive = self.cognitive_weight * r1 * (
            self.personal_best_positions - self.positions
        )

        # Social component
        social = self.social_weight * r2 * (
            self.global_best_position - self.positions
        )

        # Update velocities
        self.velocities = (
            self.inertia_weight * self.velocities + cognitive + social
        )

        # Velocity clamping
        if self.velocity_clamping:
            bounds = self.parameter_space.bounds
            max_velocity = (bounds[1] - bounds[0]) * 0.5  # 50% of parameter range
            self.velocities = np.clip(self.velocities, -max_velocity, max_velocity)

    def _update_positions(self) -> None:
        """Update particle positions."""
        self.positions = self.positions + self.velocities

        # Ensure positions stay within bounds
        self.positions = self.parameter_space.clip(self.positions)

    def _update_personal_bests(self, fitness: np.ndarray) -> None:
        """Update personal best positions and fitness."""
        improved = fitness < self.personal_best_fitness
        self.personal_best_fitness = np.where(improved, fitness, self.personal_best_fitness)
        self.personal_best_positions[improved] = self.positions[improved]

    def _update_global_best(self) -> None:
        """Update global best position and fitness."""
        best_idx = np.argmin(self.personal_best_fitness)
        best_fitness = self.personal_best_fitness[best_idx]

        if best_fitness < self.global_best_fitness:
            self.global_best_fitness = best_fitness
            self.global_best_position = self.personal_best_positions[best_idx].copy()

    def _update_adaptive_parameters(self, iteration: int, max_iterations: int) -> None:
        """Update PSO parameters adaptively."""
        progress = iteration / max_iterations

        # Linear adaptation of inertia weight
        self.inertia_weight = (
            self.initial_inertia - (self.initial_inertia - self.final_inertia) * progress
        )

        # Adaptation of acceleration coefficients
        self.cognitive_weight = (
            self.initial_c1 - (self.initial_c1 - self.final_c1) * progress
        )
        self.social_weight = (
            self.initial_c2 + (self.final_c2 - self.initial_c2) * progress
        )

    def _calculate_diversity(self) -> float:
        """Calculate swarm diversity."""
        if self.global_best_position is None:
            return 0.0

        # Average distance from global best
        distances = np.linalg.norm(
            self.positions - self.global_best_position, axis=1
        )
        return float(np.mean(distances))

    def _apply_constraint_penalties(self,
                                  fitness: np.ndarray,
                                  problem: OptimizationProblem) -> np.ndarray:
        """Apply constraint penalties to fitness values."""
        penalized_fitness = fitness.copy()

        for i, position in enumerate(self.positions):
            satisfied, violations = problem.check_constraints(position)
            if not satisfied:
                # Add penalty proportional to constraint violations
                penalty = sum(max(0, violation) for violation in violations)
                penalized_fitness[i] += 1000 * penalty  # Large penalty factor

        return penalized_fitness

    def get_swarm_statistics(self) -> Dict[str, Any]:
        """Get detailed swarm statistics."""
        return {
            'iteration': self.iteration_count,
            'global_best_fitness': self.global_best_fitness,
            'global_best_position': self.global_best_position.copy() if self.global_best_position is not None else None,
            'diversity': self.diversity_history[-1] if self.diversity_history else 0.0,
            'fitness_history': self.fitness_history.copy(),
            'diversity_history': self.diversity_history.copy(),
            'current_inertia': self.inertia_weight,
            'current_cognitive': self.cognitive_weight,
            'current_social': self.social_weight,
            'population_size': self.population_size
        }


# Import and re-export the original PSOTuner for backward compatibility
from ..pso_optimizer import PSOTuner

__all__ = ["ParticleSwarmOptimizer", "PSOTuner"]