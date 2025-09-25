#==========================================================================================\\\
#================== tests/test_numerical_stability_deep.py ==============================\\\
#==========================================================================================\\\

"""
Deep Numerical Stability and Convergence Tests.
COMPREHENSIVE JOB: Test mathematical stability, convergence, and numerical robustness.
"""

import pytest
import numpy as np
import warnings
from typing import List, Tuple, Dict, Callable, Any
from scipy import linalg
import matplotlib.pyplot as plt
from collections import deque


class NumericalStabilityAnalyzer:
    """Analyzer for numerical stability properties."""

    @staticmethod
    def condition_number_analysis(matrix: np.ndarray) -> Dict[str, float]:
        """Analyze condition number and numerical properties."""
        cond_2 = np.linalg.cond(matrix, p=2)  # 2-norm condition number
        cond_frobenius = np.linalg.cond(matrix, p='fro')  # Frobenius norm
        cond_1 = np.linalg.cond(matrix, p=1)  # 1-norm condition number

        eigenvals = np.linalg.eigvals(matrix)
        spectral_radius = np.max(np.abs(eigenvals))

        return {
            'condition_2': cond_2,
            'condition_frobenius': cond_frobenius,
            'condition_1': cond_1,
            'spectral_radius': spectral_radius,
            'well_conditioned': cond_2 < 1e12,
            'eigenvalues_real': np.all(np.isreal(eigenvals)),
            'min_eigenval_magnitude': np.min(np.abs(eigenvals)),
            'max_eigenval_magnitude': np.max(np.abs(eigenvals))
        }

    @staticmethod
    def convergence_analysis(sequence: List[float], tolerance: float = 1e-10) -> Dict[str, Any]:
        """Analyze convergence properties of a sequence."""
        if len(sequence) < 3:
            return {'converged': False, 'reason': 'insufficient_data'}

        sequence = np.array(sequence)
        differences = np.abs(np.diff(sequence))

        # Check for convergence
        recent_changes = differences[-10:] if len(differences) >= 10 else differences
        is_converged = np.all(recent_changes < tolerance)

        # Estimate convergence rate
        if len(differences) > 1:
            ratios = differences[1:] / (differences[:-1] + 1e-15)  # Avoid division by zero
            convergence_rate = np.median(ratios[np.isfinite(ratios)])
        else:
            convergence_rate = np.inf

        return {
            'converged': is_converged,
            'final_value': sequence[-1],
            'final_change': differences[-1] if len(differences) > 0 else np.inf,
            'convergence_rate': convergence_rate,
            'linear_convergence': 0 < convergence_rate < 1,
            'superlinear_convergence': convergence_rate < 0.1,
            'iterations_to_converge': len(sequence),
            'monotonic': np.all(np.diff(sequence) <= 0) or np.all(np.diff(sequence) >= 0)
        }


class MockLyapunovController:
    """Mock controller with Lyapunov stability analysis."""

    def __init__(self, K_gains):
        self.K = np.array(K_gains)
        self.lyapunov_values = []
        self.energy_values = []

    def compute_control_with_lyapunov(self, state, reference=None):
        """Compute control and track Lyapunov function."""
        error = state if reference is None else state - reference

        # Simple Lyapunov function: V = 0.5 * e^T * P * e
        P = np.eye(len(error))  # Simple choice
        lyapunov_value = 0.5 * error.T @ P @ error
        self.lyapunov_values.append(lyapunov_value)

        # Energy tracking
        kinetic_energy = 0.5 * np.sum(state[3:]**2)  # Velocity components
        potential_energy = 0.5 * np.sum(state[:3]**2)  # Position components
        total_energy = kinetic_energy + potential_energy
        self.energy_values.append(total_energy)

        # Control law
        control = -np.dot(self.K, error)
        return control

    def get_lyapunov_analysis(self):
        """Get Lyapunov stability analysis."""
        return NumericalStabilityAnalyzer.convergence_analysis(self.lyapunov_values)

    def get_energy_analysis(self):
        """Get energy analysis."""
        return NumericalStabilityAnalyzer.convergence_analysis(self.energy_values)


class MockSMCWithChattering:
    """Mock SMC controller with chattering analysis."""

    def __init__(self, gains, boundary_layer=0.01):
        self.gains = np.array(gains)
        self.boundary_layer = boundary_layer
        self.sigma_history = []
        self.control_history = []
        self.chattering_metrics = []

    def compute_control(self, state, reference=None):
        """Compute SMC control with chattering tracking."""
        error = state if reference is None else state - reference
        sigma = np.dot(self.gains, error)
        self.sigma_history.append(sigma)

        # Switching function with boundary layer
        if abs(sigma) <= self.boundary_layer:
            switching = sigma / self.boundary_layer
        else:
            switching = np.sign(sigma)

        control = -switching
        self.control_history.append(control)

        # Chattering analysis
        if len(self.control_history) > 1:
            control_variation = abs(control - self.control_history[-2])
            self.chattering_metrics.append(control_variation)

        return control

    def get_chattering_analysis(self):
        """Analyze chattering behavior."""
        if len(self.chattering_metrics) < 10:
            return {'insufficient_data': True}

        metrics = np.array(self.chattering_metrics)
        return {
            'mean_chattering': np.mean(metrics),
            'max_chattering': np.max(metrics),
            'chattering_variance': np.var(metrics),
            'high_frequency_content': np.sum(metrics > np.mean(metrics) * 2),
            'boundary_layer_effective': np.mean(metrics) < 0.1,
            'chattering_reduced': np.mean(metrics[-10:]) < np.mean(metrics[:10]) if len(metrics) >= 20 else False
        }


@pytest.mark.numerical_stability
class TestNumericalStability:
    """Test numerical stability properties."""

    def test_matrix_conditioning_stability(self):
        """Test numerical stability of matrix operations."""
        # Well-conditioned matrix
        well_conditioned = np.array([
            [2, 1, 0, 0, 0, 0],
            [1, 2, 1, 0, 0, 0],
            [0, 1, 2, 1, 0, 0],
            [0, 0, 1, 2, 1, 0],
            [0, 0, 0, 1, 2, 1],
            [0, 0, 0, 0, 1, 2]
        ])

        analysis = NumericalStabilityAnalyzer.condition_number_analysis(well_conditioned)

        assert analysis['well_conditioned']
        assert analysis['condition_2'] < 100  # Should be well-conditioned
        assert analysis['eigenvalues_real']

        # Test with ill-conditioned matrix (Hilbert-like)
        n = 6
        ill_conditioned = np.array([[1.0/(i+j-1) for j in range(1, n+1)] for i in range(1, n+1)])

        ill_analysis = NumericalStabilityAnalyzer.condition_number_analysis(ill_conditioned)

        assert not ill_analysis['well_conditioned']
        assert ill_analysis['condition_2'] > 1e6  # Should be ill-conditioned

    def test_eigenvalue_stability_analysis(self):
        """Test eigenvalue analysis for system stability."""
        # Stable system matrix (negative real parts)
        stable_matrix = np.array([
            [-1, 0.5, 0, 0, 0, 0],
            [0, -2, 1, 0, 0, 0],
            [0, 0, -1.5, 0.5, 0, 0],
            [1, 0, 0, -0.5, 0.2, 0],
            [0, 1, 0, 0, -1, 0.1],
            [0, 0, 1, 0, 0, -2]
        ])

        eigenvals = np.linalg.eigvals(stable_matrix)

        # All eigenvalues should have negative real parts for stability
        real_parts = np.real(eigenvals)
        assert np.all(real_parts < 0), f"Unstable eigenvalues: {eigenvals[real_parts >= 0]}"

        # Check spectral radius
        spectral_radius = np.max(np.abs(eigenvals))
        assert spectral_radius < 10  # Reasonable spectral radius

    def test_numerical_precision_limits(self):
        """Test behavior at numerical precision limits."""
        # Test with very small numbers
        tiny_values = np.array([1e-15, 1e-14, 1e-13, 1e-12])
        gains = np.ones(4)

        for tiny_val in tiny_values:
            state = np.ones(4) * tiny_val
            result = np.dot(gains, state)

            assert np.isfinite(result)
            assert abs(result - 4 * tiny_val) < 1e-14

        # Test with very large numbers
        large_values = np.array([1e12, 1e13, 1e14])

        for large_val in large_values:
            state = np.ones(4) * large_val
            result = np.dot(gains, state)

            assert np.isfinite(result)
            # Should maintain relative precision
            relative_error = abs(result - 4 * large_val) / (4 * large_val)
            assert relative_error < 1e-12

    def test_iterative_algorithm_stability(self):
        """Test stability of iterative algorithms."""
        # Newton-like iteration for solving x^2 = 2 (should converge to sqrt(2))
        def newton_sqrt2_iteration(x):
            return 0.5 * (x + 2/x)

        # Test convergence from different starting points
        starting_points = [0.1, 1.0, 2.0, 10.0]
        target = np.sqrt(2)

        for x0 in starting_points:
            sequence = [x0]
            x = x0

            for _ in range(50):  # Maximum iterations
                x_new = newton_sqrt2_iteration(x)
                sequence.append(x_new)
                x = x_new

                if abs(x - target) < 1e-12:
                    break

            analysis = NumericalStabilityAnalyzer.convergence_analysis(sequence, tolerance=1e-10)

            assert analysis['converged'], f"Failed to converge from starting point {x0}"
            assert abs(analysis['final_value'] - target) < 1e-10
            assert analysis['superlinear_convergence']  # Newton's method should be superlinear

    def test_matrix_exponential_stability(self):
        """Test matrix exponential computation stability."""
        # Test with stable matrix
        A_stable = np.array([
            [-2, 1, 0],
            [0, -1, 1],
            [0, 0, -3]
        ])

        # Compute matrix exponential for different time steps
        time_steps = [0.01, 0.1, 1.0, 10.0]

        for dt in time_steps:
            exp_A = linalg.expm(A_stable * dt)

            # Matrix exponential should be well-conditioned
            cond = np.linalg.cond(exp_A)
            assert cond < 1e12, f"Matrix exponential ill-conditioned at dt={dt}"

            # Eigenvalues of exp(A*dt) should be exp(eigenvals(A)*dt)
            eigenvals_A = np.linalg.eigvals(A_stable)
            eigenvals_exp = np.linalg.eigvals(exp_A)

            expected_eigenvals = np.exp(eigenvals_A * dt)

            # Sort for comparison
            eigenvals_exp_sorted = np.sort(eigenvals_exp)
            expected_sorted = np.sort(expected_eigenvals)

            assert np.allclose(eigenvals_exp_sorted, expected_sorted, rtol=1e-10)


@pytest.mark.convergence
class TestConvergenceProperties:
    """Test convergence properties of control algorithms."""

    def test_lyapunov_stability_convergence(self):
        """Test Lyapunov-based stability convergence."""
        controller = MockLyapunovController([2, 4, 1, 1, 2, 0.5])

        # Simulate closed-loop system
        state = np.array([1.0, 0.5, 0.3, 0.2, 0.1, 0.0])  # Initial deviation
        reference = np.zeros(6)

        for i in range(200):  # Simulation steps
            control = controller.compute_control_with_lyapunov(state, reference)

            # Simple mock dynamics (stable system)
            A = np.array([
                [0, 0, 0, 1, 0, 0],
                [0, 0, 0, 0, 1, 0],
                [0, 0, 0, 0, 0, 1],
                [-2, -1, 0, -1, 0, 0],
                [0, -3, -1, 0, -1, 0],
                [0, 0, -2, 0, 0, -1]
            ])
            B = np.array([0, 0, 0, 1, 0, 0])

            state_dot = A @ state + B * control
            state = state + state_dot * 0.01  # Euler integration

        # Analyze convergence
        lyapunov_analysis = controller.get_lyapunov_analysis()
        energy_analysis = controller.get_energy_analysis()

        assert lyapunov_analysis['converged'], "Lyapunov function should decrease to zero"
        assert lyapunov_analysis['final_value'] < 0.01, "Should converge close to zero"

        # Lyapunov function should be decreasing (monotonic for this stable system)
        lyapunov_values = controller.lyapunov_values
        # Allow some numerical tolerance for strict monotonicity
        non_increasing_violations = sum(1 for i in range(1, len(lyapunov_values))
                                       if lyapunov_values[i] > lyapunov_values[i-1] + 1e-10)
        assert non_increasing_violations < len(lyapunov_values) * 0.05  # Less than 5% violations

    def test_smc_chattering_reduction(self):
        """Test sliding mode controller chattering reduction."""
        # Test with different boundary layers
        boundary_layers = [0.001, 0.01, 0.1, 0.5]
        chattering_results = []

        for boundary_layer in boundary_layers:
            controller = MockSMCWithChattering([5, 3, 2, 1, 1, 0.5], boundary_layer)

            # Simulate with noise to test chattering
            np.random.seed(42)
            state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])

            for i in range(100):
                # Add measurement noise
                noisy_state = state + np.random.normal(0, 0.001, 6)
                control = controller.compute_control(noisy_state)

                # Simple dynamics update
                state = state * 0.98 + np.random.normal(0, 0.01, 6)

            analysis = controller.get_chattering_analysis()
            if not analysis.get('insufficient_data', False):
                chattering_results.append({
                    'boundary_layer': boundary_layer,
                    'mean_chattering': analysis['mean_chattering'],
                    'max_chattering': analysis['max_chattering'],
                    'boundary_layer_effective': analysis['boundary_layer_effective']
                })

        # Larger boundary layers should reduce chattering
        if len(chattering_results) >= 2:
            # Compare smallest and largest boundary layer results
            min_bl_result = min(chattering_results, key=lambda x: x['boundary_layer'])
            max_bl_result = max(chattering_results, key=lambda x: x['boundary_layer'])

            assert max_bl_result['mean_chattering'] <= min_bl_result['mean_chattering']

    def test_optimization_convergence(self):
        """Test optimization algorithm convergence."""
        # Simple quadratic optimization: minimize x^T Q x
        Q = np.array([
            [2, 0.5, 0, 0, 0, 0],
            [0.5, 3, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0],
            [0, 0, 0, 2, 0.2, 0],
            [0, 0, 0, 0.2, 1.5, 0],
            [0, 0, 0, 0, 0, 4]
        ])

        def objective(x):
            return 0.5 * x.T @ Q @ x

        def gradient(x):
            return Q @ x

        # Gradient descent
        x = np.random.randn(6)  # Starting point
        learning_rate = 0.01
        objective_values = []

        for i in range(1000):
            obj_val = objective(x)
            objective_values.append(obj_val)

            grad = gradient(x)
            x = x - learning_rate * grad

            # Check for convergence
            if i > 10 and abs(objective_values[-1] - objective_values[-10]) < 1e-12:
                break

        # Analyze convergence
        analysis = NumericalStabilityAnalyzer.convergence_analysis(objective_values)

        assert analysis['converged'], "Optimization should converge"
        assert analysis['final_value'] < 0.1, "Should converge to near-optimal value"
        assert analysis['linear_convergence'], "Gradient descent should show linear convergence"

    def test_fixed_point_iteration_stability(self):
        """Test fixed point iteration stability."""
        # Fixed point iteration for solving g(x) = x where g(x) = 0.5(x + 2/x)
        # This should converge to sqrt(2)

        def g(x):
            if abs(x) < 1e-10:
                return 1.0  # Avoid division by zero
            return 0.5 * (x + 2/x)

        # Test different starting points
        starting_points = [0.5, 1.0, 2.0, 4.0]
        target = np.sqrt(2)

        for x0 in starting_points:
            sequence = [x0]
            x = x0

            for iteration in range(100):
                x_new = g(x)
                sequence.append(x_new)

                if abs(x_new - x) < 1e-12:
                    break

                x = x_new

            analysis = NumericalStabilityAnalyzer.convergence_analysis(sequence)

            assert analysis['converged'], f"Fixed point iteration failed from x0={x0}"
            assert abs(analysis['final_value'] - target) < 1e-10
            assert analysis['iterations_to_converge'] < 50, "Should converge quickly"

    def test_control_system_step_response_convergence(self):
        """Test step response convergence for control systems."""
        # Second-order system with controller
        class MockSecondOrderSystem:
            def __init__(self, wn=2.0, zeta=0.7):
                self.wn = wn  # Natural frequency
                self.zeta = zeta  # Damping ratio
                self.state = np.array([0.0, 0.0])  # [position, velocity]

            def step(self, control, dt=0.01):
                """Simulate one time step."""
                x, x_dot = self.state

                # Second-order dynamics: x_ddot = -2*zeta*wn*x_dot - wn^2*x + control
                x_ddot = -2*self.zeta*self.wn*x_dot - self.wn**2*x + control

                # Euler integration
                self.state[0] += x_dot * dt
                self.state[1] += x_ddot * dt

                return self.state.copy()

        # Test step response
        system = MockSecondOrderSystem()
        reference = 1.0  # Step input
        Kp, Kd = 10.0, 4.0  # PD controller gains

        positions = []
        times = []
        dt = 0.01

        for i in range(1000):  # 10 seconds
            t = i * dt
            times.append(t)

            # PD controller
            error = reference - system.state[0]
            error_dot = -system.state[1]  # Assume reference derivative is zero
            control = Kp * error + Kd * error_dot

            system.step(control, dt)
            positions.append(system.state[0])

        # Analyze step response convergence
        analysis = NumericalStabilityAnalyzer.convergence_analysis(positions[-100:])  # Last 1 second

        assert analysis['converged'], "Step response should converge"
        assert abs(analysis['final_value'] - reference) < 0.05, "Should converge to reference"

        # Check for overshoot and settling characteristics
        max_position = max(positions)
        overshoot = (max_position - reference) / reference if reference > 0 else 0

        assert overshoot < 0.3, "Overshoot should be reasonable (< 30%)"

        # Check settling time (2% criteria)
        settling_tolerance = 0.02 * reference
        settled_index = None

        for i in reversed(range(len(positions))):
            if abs(positions[i] - reference) > settling_tolerance:
                settled_index = i + 1
                break

        if settled_index is not None:
            settling_time = settled_index * dt
            assert settling_time < 5.0, "Should settle within 5 seconds"


@pytest.mark.numerical_robustness
class TestNumericalRobustness:
    """Test numerical robustness against edge cases."""

    def test_division_by_zero_robustness(self):
        """Test robustness against division by zero."""

        def safe_division(a, b, epsilon=1e-15):
            """Safe division with regularization."""
            return a / (b + epsilon * np.sign(b) if b != 0 else epsilon)

        # Test cases that could cause division by zero
        test_cases = [
            (1.0, 0.0),
            (0.0, 0.0),
            (1e-20, 1e-20),
            (-1.0, 0.0),
            (np.inf, 0.0),
        ]

        for numerator, denominator in test_cases:
            result = safe_division(numerator, denominator)
            assert np.isfinite(result), f"Division {numerator}/{denominator} produced non-finite result"

    def test_logarithm_stability(self):
        """Test logarithm computation stability."""

        def safe_log(x, min_value=1e-15):
            """Safe logarithm with regularization."""
            return np.log(np.maximum(x, min_value))

        # Test edge cases for logarithm
        test_values = [0.0, 1e-20, 1e-10, 1e-5, 1.0, 1e5, np.inf]

        for x in test_values:
            if np.isfinite(x):
                result = safe_log(x)
                assert np.isfinite(result), f"Safe log of {x} produced non-finite result"

    def test_matrix_inversion_robustness(self):
        """Test matrix inversion robustness."""

        def safe_matrix_inverse(A, regularization=1e-12):
            """Safe matrix inversion with regularization."""
            n = A.shape[0]
            regularized = A + regularization * np.eye(n)
            return np.linalg.inv(regularized)

        # Test with nearly singular matrices
        near_singular = np.array([
            [1, 1, 1],
            [1, 1.000001, 1],
            [1, 1, 1.000001]
        ])

        inv_result = safe_matrix_inverse(near_singular)

        # Check that we get a reasonable result
        assert np.all(np.isfinite(inv_result))

        # Check that A * inv(A) ≈ I (within tolerance)
        identity_check = near_singular @ inv_result
        identity_error = np.max(np.abs(identity_check - np.eye(3)))
        assert identity_error < 1e-6, "Matrix inversion accuracy check failed"

    def test_numerical_derivative_stability(self):
        """Test numerical derivative computation stability."""

        def numerical_derivative(f, x, h=1e-8):
            """Compute numerical derivative using central difference."""
            return (f(x + h) - f(x - h)) / (2 * h)

        # Test functions with known derivatives
        test_functions = [
            (lambda x: x**2, lambda x: 2*x, 1.0),      # f(x) = x^2, f'(x) = 2x
            (lambda x: np.sin(x), lambda x: np.cos(x), np.pi/4),  # f(x) = sin(x), f'(x) = cos(x)
            (lambda x: np.exp(x), lambda x: np.exp(x), 0.0),      # f(x) = exp(x), f'(x) = exp(x)
        ]

        for func, true_derivative, test_point in test_functions:
            numerical_result = numerical_derivative(func, test_point)
            analytical_result = true_derivative(test_point)

            relative_error = abs(numerical_result - analytical_result) / (abs(analytical_result) + 1e-15)
            assert relative_error < 1e-6, f"Numerical derivative error too large: {relative_error}"

    def test_integration_stability(self):
        """Test numerical integration stability."""

        def trapezoidal_integration(f, a, b, n=1000):
            """Trapezoidal rule integration."""
            h = (b - a) / n
            x = np.linspace(a, b, n+1)
            y = f(x)
            return h * (0.5*y[0] + np.sum(y[1:-1]) + 0.5*y[-1])

        # Test functions with known integrals
        test_cases = [
            (lambda x: x**2, 0, 1, 1/3),           # ∫₀¹ x² dx = 1/3
            (lambda x: np.sin(x), 0, np.pi, 2),    # ∫₀^π sin(x) dx = 2
            (lambda x: np.exp(-x**2), -2, 2, None), # Gaussian (no closed form, but should be stable)
        ]

        for func, a, b, expected in test_cases:
            result = trapezoidal_integration(func, a, b)

            assert np.isfinite(result), "Integration produced non-finite result"

            if expected is not None:
                relative_error = abs(result - expected) / expected
                assert relative_error < 0.01, f"Integration error too large: {relative_error}"

    def test_eigenvalue_computation_stability(self):
        """Test eigenvalue computation stability for various matrix types."""

        # Test matrices with different properties
        matrices = {
            'symmetric_positive_definite': np.array([[2, 1], [1, 2]]),
            'symmetric_indefinite': np.array([[1, 2], [2, 1]]),
            'nonsymmetric': np.array([[1, 2], [3, 4]]),
            'nearly_singular': np.array([[1, 1], [1, 1.000001]]),
        }

        for name, matrix in matrices.items():
            eigenvals = np.linalg.eigvals(matrix)

            # All eigenvalues should be finite
            assert np.all(np.isfinite(eigenvals)), f"Non-finite eigenvalues in {name} matrix"

            # Check that eigenvalues satisfy basic properties
            trace = np.trace(matrix)
            eigenval_sum = np.sum(eigenvals)
            assert abs(trace - eigenval_sum) < 1e-10, f"Trace-eigenvalue mismatch in {name} matrix"

            determinant = np.linalg.det(matrix)
            eigenval_product = np.prod(eigenvals)
            assert abs(determinant - eigenval_product) < 1e-10, f"Det-eigenvalue mismatch in {name} matrix"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])