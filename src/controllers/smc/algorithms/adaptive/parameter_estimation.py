#==========================================================================================\\\
#========== src/controllers/smc/algorithms/adaptive/parameter_estimation.py ==========\\\
#==========================================================================================\\\

"""
Parameter and Uncertainty Estimation for Adaptive SMC.

Implements online estimation of system uncertainties and disturbance bounds
to improve adaptive gain selection and overall controller performance.

Mathematical Background:
- Uncertainty bound estimation: η̂ = max{|disturbance|, model_error}
- Sliding mode observer: estimate unknown dynamics components
- Recursive least squares: parameter identification
"""

from typing import List, Optional, Union, Dict, Any
import numpy as np
from collections import deque


class UncertaintyEstimator:
    """
    Online uncertainty estimation for adaptive SMC.

    Estimates bounds on system uncertainties and disturbances
    to improve adaptive gain selection.
    """

    def __init__(self,
                 window_size: int = 50,
                 forgetting_factor: float = 0.95,
                 initial_estimate: float = 1.0,
                 estimation_gain: float = 0.1):
        """
        Initialize uncertainty estimator.

        Args:
            window_size: Size of sliding window for estimation
            forgetting_factor: λ ∈ (0,1] for exponential forgetting
            initial_estimate: Initial uncertainty bound estimate
            estimation_gain: Learning rate for uncertainty adaptation
        """
        if not (0 < forgetting_factor <= 1):
            raise ValueError("Forgetting factor must be in (0, 1]")
        if window_size <= 0:
            raise ValueError("Window size must be positive")
        if initial_estimate <= 0:
            raise ValueError("Initial estimate must be positive")
        if estimation_gain <= 0:
            raise ValueError("Estimation gain must be positive")

        self.window_size = window_size
        self.lambda_forget = forgetting_factor
        self.eta_hat = initial_estimate
        self.alpha = estimation_gain

        # History buffers
        self._surface_history = deque(maxlen=window_size)
        self._control_history = deque(maxlen=window_size)
        self._surface_derivative_history = deque(maxlen=window_size)
        self._uncertainty_estimates = deque(maxlen=window_size)

    def update_estimate(self, surface_value: float, surface_derivative: float,
                       control_input: float, dt: float) -> float:
        """
        Update uncertainty estimate based on sliding surface behavior.

        Args:
            surface_value: Current sliding surface s
            surface_derivative: Surface derivative ṡ
            control_input: Applied control u
            dt: Time step

        Returns:
            Updated uncertainty bound estimate η̂
        """
        # Store history
        self._surface_history.append(surface_value)
        self._surface_derivative_history.append(surface_derivative)
        self._control_history.append(control_input)

        # Estimate uncertainty from sliding surface behavior
        uncertainty_indicator = self._compute_uncertainty_indicator(
            surface_value, surface_derivative, control_input
        )

        # Update estimate with forgetting factor
        self.eta_hat = (self.lambda_forget * self.eta_hat +
                       self.alpha * uncertainty_indicator)

        # Store estimate
        self._uncertainty_estimates.append(self.eta_hat)

        return self.eta_hat

    def _compute_uncertainty_indicator(self, s: float, s_dot: float, u: float) -> float:
        """
        Compute uncertainty indicator from surface behavior.

        High uncertainty is indicated by:
        - Large |ṡ| despite control effort
        - Persistent surface magnitude |s|
        - High control effort with poor surface reduction
        """
        # Method 1: Surface derivative magnitude (indicates reaching law violation)
        reaching_violation = abs(s_dot) + abs(s)  # Should be negative for reaching

        # Method 2: Control effectiveness (high u with large |s| indicates uncertainty)
        if abs(u) > 1e-6:
            control_effectiveness = abs(s) / (abs(u) + 1e-6)
        else:
            control_effectiveness = abs(s)

        # Method 3: Sliding condition violation
        sliding_condition = s * s_dot  # Should be negative for sliding

        # Combine indicators
        uncertainty_indicator = (0.4 * reaching_violation +
                               0.4 * control_effectiveness +
                               0.2 * max(0, sliding_condition))

        return uncertainty_indicator

    def get_uncertainty_bound(self) -> float:
        """Get current uncertainty bound estimate."""
        return self.eta_hat

    def get_confidence_interval(self, confidence: float = 0.95) -> tuple[float, float]:
        """
        Get confidence interval for uncertainty estimate.

        Args:
            confidence: Confidence level (0, 1)

        Returns:
            (lower_bound, upper_bound) for uncertainty estimate
        """
        if len(self._uncertainty_estimates) < 2:
            margin = 0.1 * self.eta_hat
            return (self.eta_hat - margin, self.eta_hat + margin)

        estimates = np.array(self._uncertainty_estimates)
        std_dev = np.std(estimates)

        # Simple confidence interval (assuming normal distribution)
        from scipy.stats import norm
        z_score = norm.ppf((1 + confidence) / 2)
        margin = z_score * std_dev

        return (self.eta_hat - margin, self.eta_hat + margin)

    def analyze_estimation_quality(self) -> dict:
        """Analyze quality of uncertainty estimation."""
        if len(self._uncertainty_estimates) < 10:
            return {'error': 'Insufficient data for analysis'}

        estimates = np.array(self._uncertainty_estimates)

        return {
            'estimate_statistics': {
                'current_estimate': float(self.eta_hat),
                'mean_estimate': float(np.mean(estimates)),
                'std_estimate': float(np.std(estimates)),
                'min_estimate': float(np.min(estimates)),
                'max_estimate': float(np.max(estimates))
            },
            'convergence_metrics': {
                'estimate_trend': float(np.polyfit(range(len(estimates)), estimates, 1)[0]),
                'recent_variance': float(np.var(estimates[-min(20, len(estimates)):])),
                'stability_indicator': float(np.std(estimates[-10:]) / (np.mean(estimates[-10:]) + 1e-6))
            },
            'estimation_health': {
                'data_availability': len(estimates) / self.window_size,
                'estimate_bounds_reasonable': 0.1 <= self.eta_hat <= 100.0,
                'convergence_detected': np.std(estimates[-10:]) < 0.1 * np.mean(estimates[-10:])
            }
        }


class ParameterIdentifier:
    """
    Online parameter identification using recursive least squares.

    Identifies unknown system parameters to improve model accuracy
    and reduce uncertainty bounds.
    """

    def __init__(self, n_parameters: int, forgetting_factor: float = 0.98,
                 initial_covariance: float = 100.0):
        """
        Initialize parameter identifier.

        Args:
            n_parameters: Number of parameters to identify
            forgetting_factor: RLS forgetting factor λ ∈ (0,1]
            initial_covariance: Initial covariance matrix scaling
        """
        if n_parameters <= 0:
            raise ValueError("Number of parameters must be positive")
        if not (0 < forgetting_factor <= 1):
            raise ValueError("Forgetting factor must be in (0, 1]")

        self.n_params = n_parameters
        self.lambda_rls = forgetting_factor

        # RLS state
        self.theta_hat = np.zeros(n_parameters)  # Parameter estimates
        self.P = initial_covariance * np.eye(n_parameters)  # Covariance matrix

        # History
        self._parameter_history = []

    def update_parameters(self, regressor: np.ndarray, measurement: float) -> np.ndarray:
        """
        Update parameter estimates using RLS algorithm.

        RLS equations:
        K(k) = P(k-1)φ(k) / [λ + φ(k)ᵀP(k-1)φ(k)]
        θ̂(k) = θ̂(k-1) + K(k)[y(k) - φ(k)ᵀθ̂(k-1)]
        P(k) = [P(k-1) - K(k)φ(k)ᵀP(k-1)] / λ

        Args:
            regressor: φ(k) regressor vector
            measurement: y(k) measurement

        Returns:
            Updated parameter estimates θ̂(k)
        """
        if len(regressor) != self.n_params:
            raise ValueError(f"Regressor size {len(regressor)} != n_parameters {self.n_params}")

        phi = np.asarray(regressor).reshape(-1, 1)
        y = float(measurement)

        # RLS gain vector
        numerator = self.P @ phi
        denominator = self.lambda_rls + phi.T @ self.P @ phi
        K = numerator / (denominator + 1e-10)  # Small regularization

        # Prediction error
        y_pred = phi.T @ self.theta_hat
        error = y - y_pred

        # Parameter update
        self.theta_hat = self.theta_hat + (K * error).flatten()

        # Covariance update
        self.P = (self.P - K @ phi.T @ self.P) / self.lambda_rls

        # Store history
        self._parameter_history.append({
            'step': len(self._parameter_history),
            'parameters': self.theta_hat.copy(),
            'prediction_error': float(error),
            'gain_norm': float(np.linalg.norm(K)),
            'covariance_trace': float(np.trace(self.P))
        })

        return self.theta_hat.copy()

    def get_parameter_estimates(self) -> np.ndarray:
        """Get current parameter estimates."""
        return self.theta_hat.copy()

    def get_parameter_covariance(self) -> np.ndarray:
        """Get parameter covariance matrix."""
        return self.P.copy()

    def get_parameter_confidence(self, confidence: float = 0.95) -> np.ndarray:
        """
        Get confidence intervals for parameters.

        Args:
            confidence: Confidence level

        Returns:
            Array of (lower, upper) bounds for each parameter
        """
        from scipy.stats import norm
        z_score = norm.ppf((1 + confidence) / 2)

        std_devs = np.sqrt(np.diag(self.P))
        margins = z_score * std_devs

        lower_bounds = self.theta_hat - margins
        upper_bounds = self.theta_hat + margins

        return np.column_stack([lower_bounds, upper_bounds])

    def reset_identifier(self, initial_covariance: float = 100.0) -> None:
        """Reset parameter identifier state."""
        self.theta_hat = np.zeros(self.n_params)
        self.P = initial_covariance * np.eye(self.n_params)
        self._parameter_history.clear()


class CombinedEstimator:
    """
    Combined uncertainty estimation and parameter identification.

    Integrates uncertainty estimation with parameter identification
    for improved adaptive SMC performance.
    """

    def __init__(self, n_parameters: int = 4, **kwargs):
        """
        Initialize combined estimator.

        Args:
            n_parameters: Number of system parameters to identify
            **kwargs: Parameters for sub-estimators
        """
        self.uncertainty_estimator = UncertaintyEstimator(**kwargs)
        self.parameter_identifier = ParameterIdentifier(n_parameters, **kwargs)

        self._estimation_active = True

    def update_estimates(self, surface_value: float, surface_derivative: float,
                        control_input: float, regressor: np.ndarray,
                        measurement: float, dt: float) -> dict:
        """
        Update both uncertainty and parameter estimates.

        Args:
            surface_value: Sliding surface value
            surface_derivative: Surface derivative
            control_input: Applied control
            regressor: Parameter identification regressor
            measurement: Parameter identification measurement
            dt: Time step

        Returns:
            Combined estimation results
        """
        results = {}

        if self._estimation_active:
            # Update uncertainty estimate
            uncertainty_bound = self.uncertainty_estimator.update_estimate(
                surface_value, surface_derivative, control_input, dt
            )

            # Update parameter estimates
            parameters = self.parameter_identifier.update_parameters(regressor, measurement)

            results = {
                'uncertainty_bound': uncertainty_bound,
                'parameters': parameters,
                'parameter_covariance': self.parameter_identifier.get_parameter_covariance(),
                'estimation_active': True
            }
        else:
            results = {
                'uncertainty_bound': self.uncertainty_estimator.get_uncertainty_bound(),
                'parameters': self.parameter_identifier.get_parameter_estimates(),
                'estimation_active': False
            }

        return results

    def set_estimation_active(self, active: bool) -> None:
        """Enable/disable online estimation."""
        self._estimation_active = active

    def get_combined_analysis(self) -> dict:
        """Get comprehensive analysis of estimation performance."""
        uncertainty_analysis = self.uncertainty_estimator.analyze_estimation_quality()

        return {
            'uncertainty_analysis': uncertainty_analysis,
            'parameter_estimates': self.parameter_identifier.get_parameter_estimates(),
            'parameter_confidence': self.parameter_identifier.get_parameter_confidence(),
            'estimation_status': {
                'active': self._estimation_active,
                'parameter_history_length': len(self.parameter_identifier._parameter_history),
                'uncertainty_history_length': len(self.uncertainty_estimator._uncertainty_estimates)
            }
        }