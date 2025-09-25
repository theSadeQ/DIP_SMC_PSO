#==========================================================================================\\
#============== src/optimization/algorithms/gradient_based/bfgs.py ==================\\
#==========================================================================================\\

"""BFGS quasi-Newton optimization algorithm with numerical gradients."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, Tuple
import numpy as np
import warnings
from dataclasses import dataclass

from ..base import OptimizationAlgorithm
from ...core.interfaces import OptimizationProblem, ParameterSpace, OptimizationResult
from ...core.parameters import ContinuousParameterSpace


@dataclass
class BFGSConfig:
    """Configuration for BFGS algorithm."""
    max_iterations: int = 1000
    max_evaluations: int = 10000
    gradient_tolerance: float = 1e-6
    function_tolerance: float = 1e-9
    step_tolerance: float = 1e-8
    initial_step_size: float = 1.0
    gradient_epsilon: float = 1e-8
    line_search_max_iter: int = 50
    wolfe_c1: float = 1e-4
    wolfe_c2: float = 0.9
    gradient_method: str = 'central'
    hessian_reset_threshold: float = 1e-8
    random_seed: Optional[int] = None


class BFGSOptimizer(OptimizationAlgorithm):
    """BFGS quasi-Newton optimization algorithm.

    The BFGS (Broyden-Fletcher-Goldfarb-Shanno) algorithm is a quasi-Newton
    method that approximates the Hessian matrix using gradient information.
    It builds up curvature information iteratively to achieve superlinear
    convergence near the optimum.

    Features:
    - Numerical gradient computation (forward, backward, central differences)
    - Line search with Wolfe conditions
    - Hessian approximation updates
    - Boundary constraint handling
    - Robust convergence criteria
    """

    def __init__(self, config: Optional[BFGSConfig] = None):
        """Initialize BFGS algorithm.

        Parameters
        ----------
        config : BFGSConfig, optional
            Algorithm configuration. If None, uses default values.
        """
        super().__init__()
        self.config = config if config is not None else BFGSConfig()

        # Initialize random number generator
        if self.config.random_seed is not None:
            np.random.seed(self.config.random_seed)

        # Algorithm state
        self.iteration = 0
        self.n_evaluations = 0
        self.convergence_history: List[float] = []
        self.gradient_norm_history: List[float] = []
        self.step_size_history: List[float] = []

        # Current optimization state
        self.current_x: Optional[np.ndarray] = None
        self.current_f: Optional[float] = None
        self.current_gradient: Optional[np.ndarray] = None
        self.hessian_inv: Optional[np.ndarray] = None

    def optimize(self,
                problem: OptimizationProblem,
                parameter_space: ParameterSpace,
                initial_guess: Optional[np.ndarray] = None,
                **kwargs) -> OptimizationResult:
        """Run BFGS optimization.

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
            raise ValueError("BFGS currently only supports ContinuousParameterSpace")

        self.problem = problem
        self.parameter_space = parameter_space
        self.dimension = len(parameter_space.lower_bounds)

        # Initialize optimization
        self._initialize_optimization(initial_guess)

        # Optimization loop
        while not self._check_termination():
            self._perform_iteration()
            self.iteration += 1

        # Create result
        result = self._create_result()
        return result

    def _initialize_optimization(self, initial_guess: Optional[np.ndarray] = None):
        """Initialize optimization state."""
        # Set initial point
        if initial_guess is not None:
            self.current_x = np.clip(initial_guess,
                                   self.parameter_space.lower_bounds,
                                   self.parameter_space.upper_bounds)
        else:
            # Random start point within bounds
            self.current_x = np.random.uniform(
                self.parameter_space.lower_bounds,
                self.parameter_space.upper_bounds
            )

        # Evaluate initial point
        self.current_f = self._safe_evaluate(self.current_x)
        self.current_gradient = self._compute_numerical_gradient(self.current_x)

        # Initialize inverse Hessian approximation as identity
        self.hessian_inv = np.eye(self.dimension)

        # Initialize history
        self.convergence_history.append(self.current_f)
        self.gradient_norm_history.append(np.linalg.norm(self.current_gradient))

    def _perform_iteration(self):
        """Perform one BFGS iteration."""
        # Compute search direction
        search_direction = -self.hessian_inv @ self.current_gradient

        # Ensure descent direction
        if np.dot(search_direction, self.current_gradient) >= 0:
            # If not descent direction, reset Hessian and use steepest descent
            warnings.warn("Non-descent direction detected, resetting Hessian")
            self.hessian_inv = np.eye(self.dimension)
            search_direction = -self.current_gradient

        # Line search
        step_size, new_x, new_f = self._line_search(
            self.current_x, self.current_f, self.current_gradient, search_direction
        )

        if step_size == 0 or new_x is None:
            # Line search failed
            warnings.warn("Line search failed")
            return

        # Compute new gradient
        new_gradient = self._compute_numerical_gradient(new_x)

        # BFGS update
        self._update_hessian_inverse(
            self.current_x, new_x, self.current_gradient, new_gradient
        )

        # Update current state
        self.current_x = new_x
        self.current_f = new_f
        self.current_gradient = new_gradient

        # Update history
        self.convergence_history.append(self.current_f)
        self.gradient_norm_history.append(np.linalg.norm(self.current_gradient))
        self.step_size_history.append(step_size)

    def _compute_numerical_gradient(self, x: np.ndarray) -> np.ndarray:
        """Compute numerical gradient using finite differences."""
        gradient = np.zeros(self.dimension)
        epsilon = self.config.gradient_epsilon

        if self.config.gradient_method == 'forward':
            f_x = self._safe_evaluate(x)
            for i in range(self.dimension):
                x_plus = x.copy()
                x_plus[i] = min(x_plus[i] + epsilon, self.parameter_space.upper_bounds[i])
                f_plus = self._safe_evaluate(x_plus)
                gradient[i] = (f_plus - f_x) / (x_plus[i] - x[i])

        elif self.config.gradient_method == 'backward':
            f_x = self._safe_evaluate(x)
            for i in range(self.dimension):
                x_minus = x.copy()
                x_minus[i] = max(x_minus[i] - epsilon, self.parameter_space.lower_bounds[i])
                f_minus = self._safe_evaluate(x_minus)
                gradient[i] = (f_x - f_minus) / (x[i] - x_minus[i])

        else:  # central differences (default)
            for i in range(self.dimension):
                x_plus = x.copy()
                x_minus = x.copy()

                h_plus = min(epsilon, self.parameter_space.upper_bounds[i] - x[i])
                h_minus = min(epsilon, x[i] - self.parameter_space.lower_bounds[i])

                x_plus[i] = x[i] + h_plus
                x_minus[i] = x[i] - h_minus

                f_plus = self._safe_evaluate(x_plus)
                f_minus = self._safe_evaluate(x_minus)

                gradient[i] = (f_plus - f_minus) / (h_plus + h_minus)

        return gradient

    def _update_hessian_inverse(self,
                               x_old: np.ndarray,
                               x_new: np.ndarray,
                               grad_old: np.ndarray,
                               grad_new: np.ndarray):
        """Update inverse Hessian approximation using BFGS formula."""
        s = x_new - x_old  # Step vector
        y = grad_new - grad_old  # Gradient change

        sy = np.dot(s, y)

        # Check curvature condition
        if abs(sy) < self.config.hessian_reset_threshold:
            warnings.warn("Curvature condition violated, resetting Hessian")
            self.hessian_inv = np.eye(self.dimension)
            return

        # BFGS update formula
        rho = 1.0 / sy
        I = np.eye(self.dimension)

        # Two-step BFGS update
        V = I - rho * np.outer(s, y)
        self.hessian_inv = V.T @ self.hessian_inv @ V + rho * np.outer(s, s)

        # Ensure positive definiteness
        eigenvals = np.linalg.eigvals(self.hessian_inv)
        if np.any(eigenvals <= 0):
            warnings.warn("Hessian approximation not positive definite, regularizing")
            min_eigenval = np.min(eigenvals)
            regularization = abs(min_eigenval) + 1e-6
            self.hessian_inv += regularization * I

    def _line_search(self,
                    x: np.ndarray,
                    f: float,
                    gradient: np.ndarray,
                    direction: np.ndarray) -> Tuple[float, Optional[np.ndarray], Optional[float]]:
        """Line search with Wolfe conditions."""
        # Initial step size
        alpha = self.config.initial_step_size
        gradient_dot_direction = np.dot(gradient, direction)

        # Check if direction is descent
        if gradient_dot_direction >= 0:
            return 0.0, None, None

        # Backtracking line search
        for i in range(self.config.line_search_max_iter):
            # Compute trial point
            x_trial = x + alpha * direction

            # Apply bounds
            x_trial = np.clip(x_trial,
                             self.parameter_space.lower_bounds,
                             self.parameter_space.upper_bounds)

            # Evaluate trial point
            f_trial = self._safe_evaluate(x_trial)

            # Check Armijo condition (sufficient decrease)
            armijo_condition = (f_trial <= f + self.config.wolfe_c1 * alpha * gradient_dot_direction)

            if armijo_condition:
                # Check curvature condition if needed
                if self.config.wolfe_c2 < 1.0:
                    gradient_trial = self._compute_numerical_gradient(x_trial)
                    curvature_condition = (np.dot(gradient_trial, direction) >=
                                         self.config.wolfe_c2 * gradient_dot_direction)

                    if curvature_condition:
                        return alpha, x_trial, f_trial
                else:
                    return alpha, x_trial, f_trial

            # Reduce step size
            alpha *= 0.5

            if alpha < 1e-16:
                break

        # If line search failed, try smaller step
        alpha = 1e-8
        x_trial = x + alpha * direction
        x_trial = np.clip(x_trial,
                         self.parameter_space.lower_bounds,
                         self.parameter_space.upper_bounds)
        f_trial = self._safe_evaluate(x_trial)

        return alpha, x_trial, f_trial

    def _safe_evaluate(self, x: np.ndarray) -> float:
        """Safely evaluate objective function."""
        try:
            value = self.problem.evaluate(x)
            self.n_evaluations += 1
            return value
        except Exception as e:
            warnings.warn(f"Evaluation failed: {e}")
            return float('inf')

    def _check_termination(self) -> bool:
        """Check termination conditions."""
        # Maximum iterations
        if self.iteration >= self.config.max_iterations:
            return True

        # Maximum evaluations
        if self.n_evaluations >= self.config.max_evaluations:
            return True

        # Gradient norm tolerance
        if self.current_gradient is not None:
            gradient_norm = np.linalg.norm(self.current_gradient)
            if gradient_norm < self.config.gradient_tolerance:
                return True

        # Function tolerance
        if len(self.convergence_history) > 1:
            function_change = abs(self.convergence_history[-1] - self.convergence_history[-2])
            if function_change < self.config.function_tolerance:
                return True

        # Step tolerance
        if len(self.step_size_history) > 1:
            if self.step_size_history[-1] < self.config.step_tolerance:
                return True

        return False

    def _create_result(self) -> OptimizationResult:
        """Create optimization result."""
        if self.current_x is None:
            return OptimizationResult(
                best_parameters=np.array([]),
                best_value=float('inf'),
                n_evaluations=self.n_evaluations,
                convergence_history=[],
                success=False,
                algorithm_info={'algorithm': 'BFGS'}
            )

        return OptimizationResult(
            best_parameters=self.current_x.copy(),
            best_value=self.current_f,
            n_evaluations=self.n_evaluations,
            convergence_history=self.convergence_history.copy(),
            success=(self.current_f is not None and
                    np.isfinite(self.current_f) and
                    np.linalg.norm(self.current_gradient) < self.config.gradient_tolerance),
            algorithm_info={
                'algorithm': 'BFGS',
                'iterations': self.iteration,
                'final_gradient_norm': np.linalg.norm(self.current_gradient) if self.current_gradient is not None else float('inf'),
                'gradient_method': self.config.gradient_method,
                'hessian_condition_number': self._compute_hessian_condition_number(),
                'average_step_size': np.mean(self.step_size_history) if self.step_size_history else 0.0
            }
        )

    def _compute_hessian_condition_number(self) -> float:
        """Compute condition number of Hessian approximation."""
        if self.hessian_inv is None:
            return float('inf')

        try:
            eigenvals = np.linalg.eigvals(self.hessian_inv)
            eigenvals = eigenvals[eigenvals > 0]  # Only positive eigenvalues
            if len(eigenvals) > 0:
                return np.max(eigenvals) / np.min(eigenvals)
            else:
                return float('inf')
        except:
            return float('inf')

    def get_optimization_info(self) -> Dict[str, Any]:
        """Get detailed optimization information."""
        info = {
            'iteration': self.iteration,
            'n_evaluations': self.n_evaluations,
            'current_function_value': self.current_f,
            'gradient_norm': np.linalg.norm(self.current_gradient) if self.current_gradient is not None else None,
            'hessian_condition_number': self._compute_hessian_condition_number(),
            'convergence_rate': self._estimate_convergence_rate()
        }

        if self.current_x is not None:
            info['current_parameters'] = self.current_x.tolist()

        if self.step_size_history:
            info['last_step_size'] = self.step_size_history[-1]
            info['average_step_size'] = np.mean(self.step_size_history)

        return info

    def _estimate_convergence_rate(self) -> float:
        """Estimate convergence rate from function value history."""
        if len(self.convergence_history) < 10:
            return 0.0

        try:
            # Estimate linear convergence rate
            recent_history = self.convergence_history[-10:]
            if len(set(recent_history)) <= 1:  # All values the same
                return float('inf')  # Already converged

            # Compute successive ratios
            ratios = []
            for i in range(1, len(recent_history)):
                if abs(recent_history[i-1]) > 1e-12:
                    ratio = abs(recent_history[i]) / abs(recent_history[i-1])
                    ratios.append(ratio)

            if ratios:
                return np.mean(ratios)
            else:
                return 0.0
        except:
            return 0.0

    def reset_hessian(self):
        """Reset Hessian approximation to identity."""
        if self.dimension > 0:
            self.hessian_inv = np.eye(self.dimension)

    def get_hessian_eigenvalues(self) -> np.ndarray:
        """Get eigenvalues of current Hessian approximation."""
        if self.hessian_inv is None:
            return np.array([])

        try:
            return np.linalg.eigvals(self.hessian_inv)
        except:
            return np.array([])

    def get_search_direction(self) -> Optional[np.ndarray]:
        """Get current search direction."""
        if self.hessian_inv is None or self.current_gradient is None:
            return None

        return -self.hessian_inv @ self.current_gradient