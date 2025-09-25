#==========================================================================================\\
#=========== src/optimization/algorithms/gradient_based/nelder_mead.py ==============\\
#==========================================================================================\\

"""Nelder-Mead simplex optimization algorithm."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, Tuple
import numpy as np
import warnings
from dataclasses import dataclass

from ..base import OptimizationAlgorithm
from ...core.interfaces import OptimizationProblem, ParameterSpace, OptimizationResult
from ...core.parameters import ContinuousParameterSpace


@dataclass
class NelderMeadConfig:
    """Configuration for Nelder-Mead algorithm."""
    max_iterations: int = 1000
    max_evaluations: int = 10000
    tolerance: float = 1e-6
    reflection_coeff: float = 1.0
    expansion_coeff: float = 2.0
    contraction_coeff: float = 0.5
    shrinkage_coeff: float = 0.5
    initial_step_size: float = 0.1
    adaptive_parameters: bool = True
    random_seed: Optional[int] = None


class NelderMeadSimplex:
    """Nelder-Mead simplex data structure."""

    def __init__(self, vertices: List[np.ndarray], function_values: List[float]):
        self.vertices = vertices
        self.function_values = function_values
        self.dimension = len(vertices[0])

        # Sort vertices by function value
        self._sort_vertices()

    def _sort_vertices(self):
        """Sort vertices by function value (best first)."""
        sorted_indices = np.argsort(self.function_values)
        self.vertices = [self.vertices[i] for i in sorted_indices]
        self.function_values = [self.function_values[i] for i in sorted_indices]

    @property
    def best_vertex(self) -> np.ndarray:
        """Get the best vertex."""
        return self.vertices[0]

    @property
    def best_value(self) -> float:
        """Get the best function value."""
        return self.function_values[0]

    @property
    def worst_vertex(self) -> np.ndarray:
        """Get the worst vertex."""
        return self.vertices[-1]

    @property
    def worst_value(self) -> float:
        """Get the worst function value."""
        return self.function_values[-1]

    @property
    def second_worst_vertex(self) -> np.ndarray:
        """Get the second worst vertex."""
        return self.vertices[-2]

    @property
    def second_worst_value(self) -> float:
        """Get the second worst function value."""
        return self.function_values[-2]

    def centroid(self, exclude_worst: bool = True) -> np.ndarray:
        """Calculate centroid of simplex."""
        if exclude_worst:
            vertices = self.vertices[:-1]  # Exclude worst vertex
        else:
            vertices = self.vertices

        return np.mean(vertices, axis=0)

    def replace_worst(self, new_vertex: np.ndarray, new_value: float):
        """Replace worst vertex with new vertex."""
        self.vertices[-1] = new_vertex
        self.function_values[-1] = new_value
        self._sort_vertices()

    def shrink_simplex(self, shrinkage_coeff: float):
        """Shrink simplex towards best vertex."""
        best = self.best_vertex
        for i in range(1, len(self.vertices)):
            self.vertices[i] = best + shrinkage_coeff * (self.vertices[i] - best)

    def volume(self) -> float:
        """Calculate simplex volume."""
        # Simplified volume calculation using standard deviation of vertices
        vertices_array = np.array(self.vertices)
        return np.std(vertices_array)


class NelderMead(OptimizationAlgorithm):
    """Nelder-Mead simplex optimization algorithm.

    The Nelder-Mead algorithm is a direct search method that uses a simplex
    (n+1 vertices in n dimensions) to navigate the parameter space. It uses
    reflection, expansion, contraction, and shrinkage operations to adapt
    the simplex shape and converge to the optimum.

    Features:
    - Derivative-free optimization
    - Adaptive simplex operations
    - Boundary constraint handling
    - Convergence detection
    - Robust parameter adaptation
    """

    def __init__(self, config: Optional[NelderMeadConfig] = None):
        """Initialize Nelder-Mead algorithm.

        Parameters
        ----------
        config : NelderMeadConfig, optional
            Algorithm configuration. If None, uses default values.
        """
        super().__init__()
        self.config = config if config is not None else NelderMeadConfig()

        # Initialize random number generator
        if self.config.random_seed is not None:
            np.random.seed(self.config.random_seed)

        # Algorithm state
        self.simplex: Optional[NelderMeadSimplex] = None
        self.iteration = 0
        self.n_evaluations = 0
        self.convergence_history: List[float] = []
        self.simplex_volume_history: List[float] = []

        # Adaptive parameters
        self.current_reflection = self.config.reflection_coeff
        self.current_expansion = self.config.expansion_coeff
        self.current_contraction = self.config.contraction_coeff
        self.current_shrinkage = self.config.shrinkage_coeff

    def optimize(self,
                problem: OptimizationProblem,
                parameter_space: ParameterSpace,
                initial_guess: Optional[np.ndarray] = None,
                **kwargs) -> OptimizationResult:
        """Run Nelder-Mead optimization.

        Parameters
        ----------
        problem : OptimizationProblem
            The optimization problem to solve
        parameter_space : ParameterSpace
            Parameter space defining bounds and constraints
        initial_guess : np.ndarray, optional
            Initial parameter guess

        Returns
        -------
        OptimizationResult
            Optimization results
        """
        if not isinstance(parameter_space, ContinuousParameterSpace):
            raise ValueError("NelderMead currently only supports ContinuousParameterSpace")

        self.problem = problem
        self.parameter_space = parameter_space
        self.dimension = len(parameter_space.lower_bounds)

        # Initialize simplex
        self._initialize_simplex(initial_guess)

        # Optimization loop
        while not self._check_termination():
            self._perform_iteration()
            self.iteration += 1

        # Create result
        result = self._create_result()
        return result

    def _initialize_simplex(self, initial_guess: Optional[np.ndarray] = None):
        """Initialize the simplex."""
        if initial_guess is not None:
            # Validate initial guess
            initial_guess = np.clip(initial_guess,
                                  self.parameter_space.lower_bounds,
                                  self.parameter_space.upper_bounds)
            start_point = initial_guess
        else:
            # Random start point within bounds
            start_point = np.random.uniform(
                self.parameter_space.lower_bounds,
                self.parameter_space.upper_bounds
            )

        # Create initial simplex vertices
        vertices = [start_point.copy()]
        step_size = self.config.initial_step_size

        # Calculate appropriate step sizes for each dimension
        ranges = self.parameter_space.upper_bounds - self.parameter_space.lower_bounds
        step_sizes = step_size * ranges

        # Create n additional vertices by perturbing each dimension
        for i in range(self.dimension):
            new_vertex = start_point.copy()
            perturbation = step_sizes[i]

            # Try positive perturbation first
            new_vertex[i] = min(start_point[i] + perturbation,
                               self.parameter_space.upper_bounds[i])

            # If at boundary, try negative perturbation
            if new_vertex[i] >= self.parameter_space.upper_bounds[i]:
                new_vertex[i] = max(start_point[i] - perturbation,
                                   self.parameter_space.lower_bounds[i])

            vertices.append(new_vertex)

        # Evaluate initial vertices
        function_values = []
        for vertex in vertices:
            value = self._safe_evaluate(vertex)
            function_values.append(value)

        # Create simplex
        self.simplex = NelderMeadSimplex(vertices, function_values)
        self.convergence_history.append(self.simplex.best_value)
        self.simplex_volume_history.append(self.simplex.volume())

    def _perform_iteration(self):
        """Perform one iteration of Nelder-Mead algorithm."""
        # Calculate centroid (excluding worst vertex)
        centroid = self.simplex.centroid(exclude_worst=True)

        # Reflection
        reflected_point = self._reflect(centroid, self.simplex.worst_vertex)
        reflected_value = self._safe_evaluate(reflected_point)

        if self.simplex.best_value <= reflected_value < self.simplex.second_worst_value:
            # Accept reflection
            self.simplex.replace_worst(reflected_point, reflected_value)

        elif reflected_value < self.simplex.best_value:
            # Try expansion
            expanded_point = self._expand(centroid, reflected_point)
            expanded_value = self._safe_evaluate(expanded_point)

            if expanded_value < reflected_value:
                # Accept expansion
                self.simplex.replace_worst(expanded_point, expanded_value)
            else:
                # Accept reflection
                self.simplex.replace_worst(reflected_point, reflected_value)

        else:
            # Try contraction
            if reflected_value < self.simplex.worst_value:
                # Outside contraction
                contracted_point = self._contract_outside(centroid, reflected_point)
                contracted_value = self._safe_evaluate(contracted_point)

                if contracted_value <= reflected_value:
                    self.simplex.replace_worst(contracted_point, contracted_value)
                else:
                    self._shrink_simplex()
            else:
                # Inside contraction
                contracted_point = self._contract_inside(centroid, self.simplex.worst_vertex)
                contracted_value = self._safe_evaluate(contracted_point)

                if contracted_value < self.simplex.worst_value:
                    self.simplex.replace_worst(contracted_point, contracted_value)
                else:
                    self._shrink_simplex()

        # Update history
        self.convergence_history.append(self.simplex.best_value)
        self.simplex_volume_history.append(self.simplex.volume())

        # Adaptive parameter adjustment
        if self.config.adaptive_parameters:
            self._update_adaptive_parameters()

    def _reflect(self, centroid: np.ndarray, worst_vertex: np.ndarray) -> np.ndarray:
        """Perform reflection operation."""
        reflected = centroid + self.current_reflection * (centroid - worst_vertex)
        return self._apply_bounds(reflected)

    def _expand(self, centroid: np.ndarray, reflected_point: np.ndarray) -> np.ndarray:
        """Perform expansion operation."""
        expanded = centroid + self.current_expansion * (reflected_point - centroid)
        return self._apply_bounds(expanded)

    def _contract_outside(self, centroid: np.ndarray, reflected_point: np.ndarray) -> np.ndarray:
        """Perform outside contraction."""
        contracted = centroid + self.current_contraction * (reflected_point - centroid)
        return self._apply_bounds(contracted)

    def _contract_inside(self, centroid: np.ndarray, worst_vertex: np.ndarray) -> np.ndarray:
        """Perform inside contraction."""
        contracted = centroid + self.current_contraction * (worst_vertex - centroid)
        return self._apply_bounds(contracted)

    def _shrink_simplex(self):
        """Shrink the entire simplex."""
        self.simplex.shrink_simplex(self.current_shrinkage)

        # Re-evaluate all vertices except the best one
        for i in range(1, len(self.simplex.vertices)):
            self.simplex.vertices[i] = self._apply_bounds(self.simplex.vertices[i])
            self.simplex.function_values[i] = self._safe_evaluate(self.simplex.vertices[i])

        self.simplex._sort_vertices()

    def _apply_bounds(self, point: np.ndarray) -> np.ndarray:
        """Apply parameter bounds to a point."""
        return np.clip(point,
                      self.parameter_space.lower_bounds,
                      self.parameter_space.upper_bounds)

    def _safe_evaluate(self, point: np.ndarray) -> float:
        """Safely evaluate objective function."""
        try:
            value = self.problem.evaluate(point)
            self.n_evaluations += 1
            return value
        except Exception as e:
            warnings.warn(f"Evaluation failed: {e}")
            return float('inf')

    def _update_adaptive_parameters(self):
        """Update adaptive algorithm parameters."""
        # Adjust parameters based on convergence progress
        if len(self.convergence_history) > 10:
            recent_improvement = (self.convergence_history[-10] -
                                self.convergence_history[-1])

            if recent_improvement < 1e-8:
                # Slow convergence - increase exploration
                self.current_reflection = min(self.current_reflection * 1.1, 2.0)
                self.current_expansion = min(self.current_expansion * 1.05, 3.0)
                self.current_contraction = max(self.current_contraction * 0.95, 0.1)
            else:
                # Good convergence - reset to default values
                self.current_reflection = self.config.reflection_coeff
                self.current_expansion = self.config.expansion_coeff
                self.current_contraction = self.config.contraction_coeff

    def _check_termination(self) -> bool:
        """Check termination conditions."""
        # Maximum iterations
        if self.iteration >= self.config.max_iterations:
            return True

        # Maximum evaluations
        if self.n_evaluations >= self.config.max_evaluations:
            return True

        # Convergence tolerance
        if self.simplex is not None and len(self.convergence_history) > 1:
            # Function value tolerance
            function_range = (self.simplex.worst_value - self.simplex.best_value)
            if abs(function_range) < self.config.tolerance:
                return True

            # Simplex size tolerance
            if self.simplex.volume() < self.config.tolerance:
                return True

            # Stagnation check
            if len(self.convergence_history) > 20:
                recent_change = abs(self.convergence_history[-1] - self.convergence_history[-20])
                if recent_change < self.config.tolerance:
                    return True

        return False

    def _create_result(self) -> OptimizationResult:
        """Create optimization result."""
        if self.simplex is None:
            return OptimizationResult(
                best_parameters=np.array([]),
                best_value=float('inf'),
                n_evaluations=self.n_evaluations,
                convergence_history=[],
                success=False,
                algorithm_info={'algorithm': 'NelderMead'}
            )

        return OptimizationResult(
            best_parameters=self.simplex.best_vertex.copy(),
            best_value=self.simplex.best_value,
            n_evaluations=self.n_evaluations,
            convergence_history=self.convergence_history.copy(),
            success=np.isfinite(self.simplex.best_value),
            algorithm_info={
                'algorithm': 'NelderMead',
                'iterations': self.iteration,
                'final_simplex_volume': self.simplex.volume(),
                'function_range': self.simplex.worst_value - self.simplex.best_value,
                'adaptive_reflection': self.current_reflection,
                'adaptive_expansion': self.current_expansion,
                'adaptive_contraction': self.current_contraction
            }
        )

    def get_simplex_info(self) -> Dict[str, Any]:
        """Get information about current simplex."""
        if self.simplex is None:
            return {}

        return {
            'iteration': self.iteration,
            'n_evaluations': self.n_evaluations,
            'best_vertex': self.simplex.best_vertex.tolist(),
            'best_value': self.simplex.best_value,
            'worst_value': self.simplex.worst_value,
            'function_range': self.simplex.worst_value - self.simplex.best_value,
            'simplex_volume': self.simplex.volume(),
            'centroid': self.simplex.centroid().tolist(),
            'convergence_rate': self._estimate_convergence_rate()
        }

    def _estimate_convergence_rate(self) -> float:
        """Estimate convergence rate."""
        if len(self.convergence_history) < 10:
            return 0.0

        # Calculate exponential convergence rate
        recent_history = self.convergence_history[-10:]
        if len(set(recent_history)) <= 1:  # All values the same
            return 0.0

        try:
            # Fit exponential decay
            x = np.arange(len(recent_history))
            y = np.array(recent_history)

            # Avoid log of non-positive numbers
            y_shifted = y - np.min(y) + 1e-10
            log_y = np.log(y_shifted)

            slope, _ = np.polyfit(x, log_y, 1)
            return abs(slope)
        except:
            return 0.0

    def restart_simplex(self, perturbation_factor: float = 0.1):
        """Restart simplex with perturbation."""
        if self.simplex is None:
            return

        # Keep best vertex, perturb others
        best_vertex = self.simplex.best_vertex.copy()
        ranges = self.parameter_space.upper_bounds - self.parameter_space.lower_bounds
        perturbation = perturbation_factor * ranges

        new_vertices = [best_vertex]
        for i in range(self.dimension):
            new_vertex = best_vertex.copy()
            new_vertex[i] += np.random.normal(0, perturbation[i])
            new_vertex = self._apply_bounds(new_vertex)
            new_vertices.append(new_vertex)

        # Evaluate new vertices
        function_values = []
        for vertex in new_vertices:
            value = self._safe_evaluate(vertex)
            function_values.append(value)

        self.simplex = NelderMeadSimplex(new_vertices, function_values)