#==========================================================================================\\
#============ src/optimization/algorithms/evolutionary/genetic.py ===================\\
#==========================================================================================\\

"""Genetic Algorithm implementation for control parameter optimization."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, Tuple, Union
import numpy as np
import warnings
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

from ..base import OptimizationAlgorithm
from ...core.interfaces import OptimizationProblem, ParameterSpace, OptimizationResult
from ...core.parameters import ContinuousParameterSpace


@dataclass
class GeneticAlgorithmConfig:
    """Configuration for Genetic Algorithm."""
    population_size: int = 50
    max_generations: int = 100
    elite_ratio: float = 0.1
    crossover_probability: float = 0.8
    mutation_probability: float = 0.2
    mutation_strength: float = 0.1
    tournament_size: int = 3
    crossover_method: str = 'uniform'
    mutation_method: str = 'gaussian'
    selection_method: str = 'tournament'
    diversity_preservation: bool = True
    adaptive_parameters: bool = False
    parallel_evaluation: bool = True
    random_seed: Optional[int] = None


class Individual:
    """Individual in the genetic algorithm population."""

    def __init__(self, genes: np.ndarray, fitness: Optional[float] = None):
        self.genes = genes.copy()
        self.fitness = fitness
        self.age = 0
        self.id = np.random.randint(0, 1000000)

    def copy(self) -> 'Individual':
        """Create a copy of the individual."""
        copy_ind = Individual(self.genes, self.fitness)
        copy_ind.age = self.age
        copy_ind.id = self.id
        return copy_ind

    def __str__(self) -> str:
        return f"Individual(genes={self.genes[:3]}..., fitness={self.fitness})"


class GeneticAlgorithm(OptimizationAlgorithm):
    """Genetic Algorithm for parameter optimization.

    A population-based evolutionary algorithm that uses selection, crossover,
    and mutation operators to evolve a population of candidate solutions.

    Features:
    - Multiple selection methods (tournament, roulette, rank)
    - Various crossover operators (uniform, single-point, arithmetic)
    - Adaptive mutation strategies
    - Elitist preservation
    - Diversity maintenance
    - Parallel fitness evaluation
    """

    def __init__(self, config: Optional[GeneticAlgorithmConfig] = None):
        """Initialize Genetic Algorithm.

        Parameters
        ----------
        config : GeneticAlgorithmConfig, optional
            Algorithm configuration. If None, uses default values.
        """
        super().__init__()
        self.config = config if config is not None else GeneticAlgorithmConfig()

        # Initialize random number generator
        if self.config.random_seed is not None:
            np.random.seed(self.config.random_seed)

        # Algorithm state
        self.population: List[Individual] = []
        self.generation = 0
        self.best_individual: Optional[Individual] = None
        self.fitness_history: List[float] = []
        self.diversity_history: List[float] = []

        # Adaptive parameters
        self.current_mutation_strength = self.config.mutation_strength
        self.current_crossover_prob = self.config.crossover_probability
        self.stagnation_counter = 0

    def optimize(self,
                problem: OptimizationProblem,
                parameter_space: ParameterSpace,
                **kwargs) -> OptimizationResult:
        """Run genetic algorithm optimization.

        Parameters
        ----------
        problem : OptimizationProblem
            The optimization problem to solve
        parameter_space : ParameterSpace
            Parameter space defining bounds and constraints

        Returns
        -------
        OptimizationResult
            Optimization results including best parameters and convergence history
        """
        if not isinstance(parameter_space, ContinuousParameterSpace):
            raise ValueError("GeneticAlgorithm currently only supports ContinuousParameterSpace")

        self.problem = problem
        self.parameter_space = parameter_space
        self.dimension = len(parameter_space.lower_bounds)

        # Initialize algorithm
        self._initialize_population()
        self._evaluate_population()

        # Evolution loop
        for generation in range(self.config.max_generations):
            self.generation = generation

            # Create new generation
            new_population = self._create_new_generation()

            # Evaluate new population
            self.population = new_population
            self._evaluate_population()

            # Update algorithm state
            self._update_algorithm_state()

            # Check convergence
            if self._check_convergence():
                break

        # Create result
        result = self._create_result()
        return result

    def _initialize_population(self) -> None:
        """Initialize the population randomly."""
        self.population = []

        for _ in range(self.config.population_size):
            # Generate random genes within bounds
            genes = np.random.uniform(
                self.parameter_space.lower_bounds,
                self.parameter_space.upper_bounds
            )

            individual = Individual(genes)
            self.population.append(individual)

    def _evaluate_population(self) -> None:
        """Evaluate fitness for all individuals in population."""
        if self.config.parallel_evaluation and len(self.population) > 4:
            self._evaluate_population_parallel()
        else:
            self._evaluate_population_serial()

        # Update best individual
        self._update_best_individual()

    def _evaluate_population_serial(self) -> None:
        """Evaluate population serially."""
        for individual in self.population:
            if individual.fitness is None:
                try:
                    individual.fitness = self.problem.evaluate(individual.genes)
                except Exception as e:
                    warnings.warn(f"Evaluation failed for individual: {e}")
                    individual.fitness = float('inf')

    def _evaluate_population_parallel(self) -> None:
        """Evaluate population in parallel."""
        try:
            with ProcessPoolExecutor(max_workers=mp.cpu_count()) as executor:
                # Submit evaluation jobs
                futures = []
                for individual in self.population:
                    if individual.fitness is None:
                        future = executor.submit(self._safe_evaluate, individual.genes)
                        futures.append((individual, future))

                # Collect results
                for individual, future in futures:
                    try:
                        individual.fitness = future.result(timeout=30)
                    except Exception as e:
                        warnings.warn(f"Parallel evaluation failed: {e}")
                        individual.fitness = float('inf')

        except Exception as e:
            # Fall back to serial evaluation
            warnings.warn(f"Parallel evaluation setup failed, using serial: {e}")
            self._evaluate_population_serial()

    def _safe_evaluate(self, genes: np.ndarray) -> float:
        """Safe evaluation wrapper for parallel processing."""
        try:
            return self.problem.evaluate(genes)
        except Exception:
            return float('inf')

    def _create_new_generation(self) -> List[Individual]:
        """Create new generation using selection, crossover, and mutation."""
        new_population = []

        # Elitism - preserve best individuals
        elite_count = max(1, int(self.config.elite_ratio * self.config.population_size))
        elite_individuals = self._select_elite(elite_count)
        new_population.extend([ind.copy() for ind in elite_individuals])

        # Generate offspring to fill remaining population
        while len(new_population) < self.config.population_size:
            # Selection
            parent1 = self._select_individual()
            parent2 = self._select_individual()

            # Crossover
            if np.random.random() < self.current_crossover_prob:
                child1, child2 = self._crossover(parent1, parent2)
            else:
                child1, child2 = parent1.copy(), parent2.copy()

            # Mutation
            if np.random.random() < self.config.mutation_probability:
                child1 = self._mutate(child1)
            if np.random.random() < self.config.mutation_probability:
                child2 = self._mutate(child2)

            # Add children to new population
            new_population.extend([child1, child2])

        # Trim population to exact size
        new_population = new_population[:self.config.population_size]

        # Age individuals
        for individual in new_population:
            individual.age += 1

        return new_population

    def _select_elite(self, count: int) -> List[Individual]:
        """Select elite individuals (best fitness)."""
        sorted_population = sorted(self.population, key=lambda x: x.fitness or float('inf'))
        return sorted_population[:count]

    def _select_individual(self) -> Individual:
        """Select individual based on selection method."""
        if self.config.selection_method == 'tournament':
            return self._tournament_selection()
        elif self.config.selection_method == 'roulette':
            return self._roulette_selection()
        elif self.config.selection_method == 'rank':
            return self._rank_selection()
        else:
            # Default to tournament
            return self._tournament_selection()

    def _tournament_selection(self) -> Individual:
        """Tournament selection."""
        tournament_size = min(self.config.tournament_size, len(self.population))
        tournament = np.random.choice(self.population, tournament_size, replace=False)
        winner = min(tournament, key=lambda x: x.fitness or float('inf'))
        return winner.copy()

    def _roulette_selection(self) -> Individual:
        """Roulette wheel selection."""
        # Convert fitness to selection probabilities (lower is better)
        fitnesses = np.array([ind.fitness or float('inf') for ind in self.population])

        # Handle infinite fitness
        if np.any(np.isinf(fitnesses)):
            finite_mask = np.isfinite(fitnesses)
            if not np.any(finite_mask):
                # All infinite - random selection
                return np.random.choice(self.population).copy()
            fitnesses[~finite_mask] = np.max(fitnesses[finite_mask]) * 10

        # Convert to probabilities (invert for minimization)
        max_fitness = np.max(fitnesses)
        if max_fitness > 0:
            weights = (max_fitness - fitnesses) + 1e-10
        else:
            weights = np.ones_like(fitnesses)

        probabilities = weights / np.sum(weights)
        selected_idx = np.random.choice(len(self.population), p=probabilities)
        return self.population[selected_idx].copy()

    def _rank_selection(self) -> Individual:
        """Rank-based selection."""
        # Sort by fitness (best first)
        sorted_indices = np.argsort([ind.fitness or float('inf') for ind in self.population])

        # Assign ranks (higher rank = better fitness)
        ranks = np.zeros(len(self.population))
        for i, idx in enumerate(sorted_indices):
            ranks[idx] = len(self.population) - i

        # Selection probabilities based on ranks
        probabilities = ranks / np.sum(ranks)
        selected_idx = np.random.choice(len(self.population), p=probabilities)
        return self.population[selected_idx].copy()

    def _crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """Perform crossover between two parents."""
        if self.config.crossover_method == 'uniform':
            return self._uniform_crossover(parent1, parent2)
        elif self.config.crossover_method == 'single_point':
            return self._single_point_crossover(parent1, parent2)
        elif self.config.crossover_method == 'arithmetic':
            return self._arithmetic_crossover(parent1, parent2)
        else:
            return self._uniform_crossover(parent1, parent2)

    def _uniform_crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """Uniform crossover - each gene has 50% chance of coming from either parent."""
        mask = np.random.random(self.dimension) < 0.5

        child1_genes = np.where(mask, parent1.genes, parent2.genes)
        child2_genes = np.where(mask, parent2.genes, parent1.genes)

        child1 = Individual(child1_genes)
        child2 = Individual(child2_genes)

        return child1, child2

    def _single_point_crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """Single-point crossover."""
        if self.dimension <= 1:
            return parent1.copy(), parent2.copy()

        crossover_point = np.random.randint(1, self.dimension)

        child1_genes = np.concatenate([parent1.genes[:crossover_point], parent2.genes[crossover_point:]])
        child2_genes = np.concatenate([parent2.genes[:crossover_point], parent1.genes[crossover_point:]])

        child1 = Individual(child1_genes)
        child2 = Individual(child2_genes)

        return child1, child2

    def _arithmetic_crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """Arithmetic crossover - weighted average of parents."""
        alpha = np.random.random()

        child1_genes = alpha * parent1.genes + (1 - alpha) * parent2.genes
        child2_genes = (1 - alpha) * parent1.genes + alpha * parent2.genes

        child1 = Individual(child1_genes)
        child2 = Individual(child2_genes)

        return child1, child2

    def _mutate(self, individual: Individual) -> Individual:
        """Mutate an individual."""
        if self.config.mutation_method == 'gaussian':
            return self._gaussian_mutation(individual)
        elif self.config.mutation_method == 'uniform':
            return self._uniform_mutation(individual)
        elif self.config.mutation_method == 'polynomial':
            return self._polynomial_mutation(individual)
        else:
            return self._gaussian_mutation(individual)

    def _gaussian_mutation(self, individual: Individual) -> Individual:
        """Gaussian mutation - add normally distributed noise."""
        mutated_genes = individual.genes.copy()

        # Add Gaussian noise
        noise = np.random.normal(0, self.current_mutation_strength, self.dimension)
        mutated_genes += noise * (self.parameter_space.upper_bounds - self.parameter_space.lower_bounds)

        # Clip to bounds
        mutated_genes = np.clip(mutated_genes,
                               self.parameter_space.lower_bounds,
                               self.parameter_space.upper_bounds)

        return Individual(mutated_genes)

    def _uniform_mutation(self, individual: Individual) -> Individual:
        """Uniform mutation - replace with random value in range."""
        mutated_genes = individual.genes.copy()

        # Randomly select genes to mutate
        mutation_mask = np.random.random(self.dimension) < 0.1  # 10% of genes

        # Replace selected genes with random values
        random_values = np.random.uniform(self.parameter_space.lower_bounds,
                                        self.parameter_space.upper_bounds)
        mutated_genes[mutation_mask] = random_values[mutation_mask]

        return Individual(mutated_genes)

    def _polynomial_mutation(self, individual: Individual) -> Individual:
        """Polynomial mutation."""
        eta = 20.0  # Distribution index
        mutated_genes = individual.genes.copy()

        for i in range(self.dimension):
            if np.random.random() < (1.0 / self.dimension):
                y = mutated_genes[i]
                yl = self.parameter_space.lower_bounds[i]
                yu = self.parameter_space.upper_bounds[i]

                delta1 = (y - yl) / (yu - yl)
                delta2 = (yu - y) / (yu - yl)

                rand = np.random.random()
                mut_pow = 1.0 / (eta + 1.0)

                if rand <= 0.5:
                    xy = 1.0 - delta1
                    val = 2.0 * rand + (1.0 - 2.0 * rand) * (xy ** (eta + 1.0))
                    deltaq = val ** mut_pow - 1.0
                else:
                    xy = 1.0 - delta2
                    val = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * (xy ** (eta + 1.0))
                    deltaq = 1.0 - (val ** mut_pow)

                y = y + deltaq * (yu - yl)
                y = max(yl, min(y, yu))
                mutated_genes[i] = y

        return Individual(mutated_genes)

    def _update_algorithm_state(self) -> None:
        """Update algorithm state after each generation."""
        # Update fitness history
        best_fitness = min(ind.fitness or float('inf') for ind in self.population)
        self.fitness_history.append(best_fitness)

        # Update diversity history
        diversity = self._calculate_diversity()
        self.diversity_history.append(diversity)

        # Adaptive parameters
        if self.config.adaptive_parameters:
            self._update_adaptive_parameters()

    def _update_best_individual(self) -> None:
        """Update the best individual found so far."""
        current_best = min(self.population, key=lambda x: x.fitness or float('inf'))

        if (self.best_individual is None or
            (current_best.fitness or float('inf')) < (self.best_individual.fitness or float('inf'))):
            self.best_individual = current_best.copy()
            self.stagnation_counter = 0
        else:
            self.stagnation_counter += 1

    def _calculate_diversity(self) -> float:
        """Calculate population diversity."""
        if len(self.population) < 2:
            return 0.0

        # Calculate average pairwise distance
        distances = []
        for i in range(len(self.population)):
            for j in range(i + 1, len(self.population)):
                distance = np.linalg.norm(self.population[i].genes - self.population[j].genes)
                distances.append(distance)

        return np.mean(distances) if distances else 0.0

    def _update_adaptive_parameters(self) -> None:
        """Update adaptive algorithm parameters."""
        # Increase mutation if stagnating
        if self.stagnation_counter > 10:
            self.current_mutation_strength = min(self.current_mutation_strength * 1.1, 0.5)
        else:
            self.current_mutation_strength = max(self.current_mutation_strength * 0.99,
                                               self.config.mutation_strength)

        # Adjust crossover probability based on diversity
        if len(self.diversity_history) > 5:
            recent_diversity = np.mean(self.diversity_history[-5:])
            if recent_diversity < 0.01:  # Low diversity
                self.current_crossover_prob = min(self.current_crossover_prob * 1.05, 0.95)
            else:
                self.current_crossover_prob = max(self.current_crossover_prob * 0.99,
                                                self.config.crossover_probability)

    def _check_convergence(self) -> bool:
        """Check if algorithm has converged."""
        # Check if fitness improvement has stagnated
        if len(self.fitness_history) > 20:
            recent_improvement = abs(self.fitness_history[-1] - self.fitness_history[-20])
            if recent_improvement < 1e-6:
                return True

        # Check if diversity is too low
        if self.config.diversity_preservation and len(self.diversity_history) > 10:
            recent_diversity = np.mean(self.diversity_history[-10:])
            if recent_diversity < 1e-8:
                return True

        return False

    def _create_result(self) -> OptimizationResult:
        """Create optimization result."""
        return OptimizationResult(
            best_parameters=self.best_individual.genes.copy() if self.best_individual else np.array([]),
            best_value=self.best_individual.fitness if self.best_individual else float('inf'),
            n_evaluations=len(self.fitness_history) * self.config.population_size,
            convergence_history=self.fitness_history.copy(),
            success=self.best_individual is not None and np.isfinite(self.best_individual.fitness),
            algorithm_info={
                'algorithm': 'GeneticAlgorithm',
                'generations': self.generation + 1,
                'population_size': self.config.population_size,
                'final_diversity': self.diversity_history[-1] if self.diversity_history else 0.0,
                'stagnation_counter': self.stagnation_counter,
                'adaptive_mutation_strength': self.current_mutation_strength,
                'adaptive_crossover_prob': self.current_crossover_prob
            }
        )

    def get_population_statistics(self) -> Dict[str, Any]:
        """Get statistics about current population."""
        if not self.population:
            return {}

        fitnesses = [ind.fitness for ind in self.population if ind.fitness is not None]
        if not fitnesses:
            return {}

        stats = {
            'generation': self.generation,
            'population_size': len(self.population),
            'best_fitness': min(fitnesses),
            'worst_fitness': max(fitnesses),
            'mean_fitness': np.mean(fitnesses),
            'std_fitness': np.std(fitnesses),
            'diversity': self._calculate_diversity(),
            'convergence_rate': self._estimate_convergence_rate(),
            'selection_pressure': self._calculate_selection_pressure()
        }

        return stats

    def _estimate_convergence_rate(self) -> float:
        """Estimate convergence rate from fitness history."""
        if len(self.fitness_history) < 10:
            return 0.0

        # Linear regression on log fitness improvement
        recent_history = self.fitness_history[-10:]
        x = np.arange(len(recent_history))
        y = np.log(np.maximum(recent_history, 1e-10))

        try:
            slope, _ = np.polyfit(x, y, 1)
            return abs(slope)
        except:
            return 0.0

    def _calculate_selection_pressure(self) -> float:
        """Calculate selection pressure in population."""
        fitnesses = [ind.fitness for ind in self.population if ind.fitness is not None]
        if len(fitnesses) < 2:
            return 0.0

        best_fitness = min(fitnesses)
        mean_fitness = np.mean(fitnesses)

        if mean_fitness > 0:
            return (mean_fitness - best_fitness) / mean_fitness
        else:
            return 0.0