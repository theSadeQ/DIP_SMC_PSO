#==========================================================================================\\\
#================= src/analysis/fault_detection/residual_generators.py ==================\\\
#==========================================================================================\\\

"""Model-based residual generation for fault detection.

This module provides various residual generation methods for fault detection
including observer-based, parity-based, and parameter estimation approaches.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any, Protocol, Callable
import numpy as np
from scipy import linalg, signal
import warnings
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from ..core.interfaces import DataProtocol


class SystemModel(Protocol):
    """Protocol for system models used in residual generation."""

    def predict(self, state: np.ndarray, control: np.ndarray, dt: float) -> np.ndarray:
        """Predict next state given current state and control."""
        ...

    def observe(self, state: np.ndarray) -> np.ndarray:
        """Compute output from state."""
        ...


@dataclass
class ResidualGeneratorConfig:
    """Configuration for residual generators."""
    # Observer parameters
    observer_poles: Optional[List[complex]] = None
    observer_bandwidth: float = 10.0

    # Kalman filter parameters
    process_noise_cov: Optional[np.ndarray] = None
    measurement_noise_cov: Optional[np.ndarray] = None
    initial_state_cov: Optional[np.ndarray] = None

    # Parity space parameters
    parity_order: int = 3
    parity_window_size: int = 20

    # Parameter estimation parameters
    estimation_window_size: int = 50
    forgetting_factor: float = 0.95
    parameter_bounds: Optional[Dict[str, Tuple[float, float]]] = None


class ResidualGenerator(ABC):
    """Abstract base class for residual generators."""

    @abstractmethod
    def generate_residual(self, data: DataProtocol, system_model: SystemModel) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Generate residual from data and system model.

        Parameters
        ----------
        data : DataProtocol
            System measurement data
        system_model : SystemModel
            System model for prediction

        Returns
        -------
        Tuple[np.ndarray, Dict[str, Any]]
            Residual vector and metadata
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset generator state."""
        pass


class ObserverBasedGenerator(ResidualGenerator):
    """Observer-based residual generator using Luenberger observers."""

    def __init__(self, config: ResidualGeneratorConfig, A: np.ndarray, C: np.ndarray):
        """Initialize observer-based generator.

        Parameters
        ----------
        config : ResidualGeneratorConfig
            Configuration parameters
        A : np.ndarray
            System matrix
        C : np.ndarray
            Output matrix
        """
        self.config = config
        self.A = A
        self.C = C
        self._design_observer()
        self.reset()

    def _design_observer(self) -> None:
        """Design observer gain matrix."""
        n = self.A.shape[0]

        if self.config.observer_poles is not None:
            # Place poles at specified locations
            desired_poles = np.array(self.config.observer_poles)
            if len(desired_poles) != n:
                warnings.warn(f"Number of poles ({len(desired_poles)}) doesn't match system order ({n})")
                desired_poles = np.repeat(desired_poles[0], n)
        else:
            # Place poles based on bandwidth
            bandwidth = self.config.observer_bandwidth
            desired_poles = np.full(n, -bandwidth, dtype=complex)

        try:
            # Check observability
            obsv_matrix = signal.place_poles(self.A.T, self.C.T, desired_poles).gain_matrix.T
            self.L = obsv_matrix
        except Exception as e:
            warnings.warn(f"Observer design failed: {e}. Using default gain.")
            self.L = np.eye(n, self.C.shape[0])

    def generate_residual(self, data: DataProtocol, system_model: SystemModel) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Generate observer-based residual."""
        if not hasattr(data, 'states') or not hasattr(data, 'times'):
            raise ValueError("Data must contain states and times")

        states = data.states
        times = data.times
        controls = getattr(data, 'controls', np.zeros((len(times)-1, 1)))

        if states.ndim == 1:
            states = states.reshape(-1, 1)
        if controls.ndim == 1:
            controls = controls.reshape(-1, 1)

        residuals = []
        observer_states = []

        # Initialize observer state
        if self._observer_state is None:
            self._observer_state = states[0].copy()

        for i in range(1, len(states)):
            dt = times[i] - times[i-1]
            if dt <= 0:
                continue

            # Get control input
            u = controls[min(i-1, len(controls)-1)]

            # Predict observer state
            try:
                predicted_state = system_model.predict(self._observer_state, u, dt)
                predicted_output = system_model.observe(predicted_state)
            except Exception as e:
                warnings.warn(f"Model prediction failed at step {i}: {e}")
                continue

            # Measurement
            actual_output = system_model.observe(states[i])

            # Innovation (output residual)
            innovation = actual_output - predicted_output

            # Update observer state
            self._observer_state = predicted_state + self.L @ innovation

            # Store results
            residuals.append(innovation)
            observer_states.append(self._observer_state.copy())

        residuals = np.array(residuals) if residuals else np.array([]).reshape(0, self.C.shape[0])

        metadata = {
            'method': 'observer_based',
            'observer_poles': self.config.observer_poles,
            'observer_gain': self.L.tolist(),
            'observer_states': [state.tolist() for state in observer_states]
        }

        return residuals, metadata

    def reset(self) -> None:
        """Reset observer state."""
        self._observer_state: Optional[np.ndarray] = None


class KalmanFilterGenerator(ResidualGenerator):
    """Kalman filter-based residual generator."""

    def __init__(self, config: ResidualGeneratorConfig, A: np.ndarray, B: np.ndarray,
                 C: np.ndarray, D: Optional[np.ndarray] = None):
        """Initialize Kalman filter generator.

        Parameters
        ----------
        config : ResidualGeneratorConfig
            Configuration parameters
        A, B, C, D : np.ndarray
            State-space matrices
        """
        self.config = config
        self.A = A
        self.B = B
        self.C = C
        self.D = D if D is not None else np.zeros((C.shape[0], B.shape[1]))

        # Initialize noise covariances
        n = A.shape[0]
        m = C.shape[0]

        self.Q = config.process_noise_cov if config.process_noise_cov is not None else np.eye(n) * 0.01
        self.R = config.measurement_noise_cov if config.measurement_noise_cov is not None else np.eye(m) * 0.1
        self.P0 = config.initial_state_cov if config.initial_state_cov is not None else np.eye(n)

        self.reset()

    def generate_residual(self, data: DataProtocol, system_model: SystemModel) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Generate Kalman filter innovation residual."""
        if not hasattr(data, 'states') or not hasattr(data, 'times'):
            raise ValueError("Data must contain states and times")

        states = data.states
        times = data.times
        controls = getattr(data, 'controls', np.zeros((len(times)-1, self.B.shape[1])))

        if states.ndim == 1:
            states = states.reshape(-1, 1)
        if controls.ndim == 1:
            controls = controls.reshape(-1, 1)

        residuals = []
        innovations_cov = []
        estimated_states = []

        # Initialize if needed
        if self._x_hat is None:
            self._x_hat = states[0].copy()
            self._P = self.P0.copy()

        for i in range(1, len(states)):
            dt = times[i] - times[i-1]
            if dt <= 0:
                continue

            # Get control input
            u = controls[min(i-1, len(controls)-1)]

            # Prediction step
            try:
                # Discrete-time state transition (simplified)
                F = np.eye(self.A.shape[0]) + self.A * dt
                G = self.B * dt

                x_pred = F @ self._x_hat + G @ u
                P_pred = F @ self._P @ F.T + self.Q * dt

                # Measurement prediction
                y_pred = self.C @ x_pred + self.D @ u

            except Exception as e:
                warnings.warn(f"Kalman prediction failed at step {i}: {e}")
                continue

            # Measurement
            y_actual = system_model.observe(states[i])

            # Innovation
            innovation = y_actual - y_pred

            # Innovation covariance
            S = self.C @ P_pred @ self.C.T + self.R

            # Update step
            try:
                K = P_pred @ self.C.T @ linalg.inv(S)
                self._x_hat = x_pred + K @ innovation
                self._P = (np.eye(len(self._x_hat)) - K @ self.C) @ P_pred
            except Exception as e:
                warnings.warn(f"Kalman update failed at step {i}: {e}")
                self._x_hat = x_pred
                self._P = P_pred

            # Store results
            residuals.append(innovation)
            innovations_cov.append(S)
            estimated_states.append(self._x_hat.copy())

        residuals = np.array(residuals) if residuals else np.array([]).reshape(0, self.C.shape[0])

        metadata = {
            'method': 'kalman_filter',
            'process_noise_cov': self.Q.tolist(),
            'measurement_noise_cov': self.R.tolist(),
            'innovation_covariances': [cov.tolist() for cov in innovations_cov],
            'estimated_states': [state.tolist() for state in estimated_states]
        }

        return residuals, metadata

    def reset(self) -> None:
        """Reset Kalman filter state."""
        self._x_hat: Optional[np.ndarray] = None
        self._P: Optional[np.ndarray] = None


class ParitySpaceGenerator(ResidualGenerator):
    """Parity space-based residual generator."""

    def __init__(self, config: ResidualGeneratorConfig, A: np.ndarray, B: np.ndarray, C: np.ndarray):
        """Initialize parity space generator.

        Parameters
        ----------
        config : ResidualGeneratorConfig
            Configuration parameters
        A, B, C : np.ndarray
            System matrices
        """
        self.config = config
        self.A = A
        self.B = B
        self.C = C
        self._compute_parity_matrices()
        self.reset()

    def _compute_parity_matrices(self) -> None:
        """Compute parity space matrices."""
        s = self.config.parity_order
        n = self.A.shape[0]
        m = self.C.shape[0]
        p = self.B.shape[1]

        # Build observability matrix
        O = np.zeros((m * (s + 1), n))
        for i in range(s + 1):
            O[i*m:(i+1)*m, :] = self.C @ linalg.matrix_power(self.A, i)

        # Build control influence matrix
        Gamma = np.zeros((m * (s + 1), p * s))
        for i in range(s):
            for j in range(i + 1):
                row_start = (i + 1) * m
                row_end = (i + 2) * m
                col_start = (i - j) * p
                col_end = (i - j + 1) * p

                if row_start < O.shape[0] and col_start < Gamma.shape[1]:
                    Gamma[row_start:row_end, col_start:col_end] = self.C @ linalg.matrix_power(self.A, j) @ self.B

        # Compute parity vector (left null space of observability matrix)
        try:
            U, s_vals, Vt = linalg.svd(O)

            # Find null space
            tol = 1e-10
            null_space_dim = np.sum(s_vals < tol)

            if null_space_dim > 0:
                self.parity_vector = U[:, -null_space_dim:].T
            else:
                # If no null space, use last row as parity vector
                self.parity_vector = U[-1:, :].T

        except Exception as e:
            warnings.warn(f"Parity space computation failed: {e}")
            self.parity_vector = np.ones((1, m * (s + 1))) / np.sqrt(m * (s + 1))

        self.control_matrix = Gamma

    def generate_residual(self, data: DataProtocol, system_model: SystemModel) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Generate parity space residual."""
        if not hasattr(data, 'states') or not hasattr(data, 'times'):
            raise ValueError("Data must contain states and times")

        states = data.states
        times = data.times
        controls = getattr(data, 'controls', np.zeros((len(times)-1, self.B.shape[1])))

        if states.ndim == 1:
            states = states.reshape(-1, 1)
        if controls.ndim == 1:
            controls = controls.reshape(-1, 1)

        residuals = []
        s = self.config.parity_order

        # Need at least s+1 measurements
        for i in range(s, len(states)):
            # Collect measurement vector
            y_vector = []
            u_vector = []

            for j in range(s + 1):
                if i - s + j < len(states):
                    y_meas = system_model.observe(states[i - s + j])
                    y_vector.extend(y_meas.flatten())

            for j in range(s):
                if i - s + j < len(controls):
                    u_vector.extend(controls[i - s + j].flatten())

            if len(y_vector) == self.parity_vector.shape[1] and len(u_vector) == self.control_matrix.shape[1]:
                y_vector = np.array(y_vector)
                u_vector = np.array(u_vector)

                # Compute parity residual
                parity_residual = self.parity_vector @ (y_vector - self.control_matrix @ u_vector)
                residuals.append(parity_residual.flatten())

        residuals = np.array(residuals) if residuals else np.array([]).reshape(0, self.parity_vector.shape[0])

        metadata = {
            'method': 'parity_space',
            'parity_order': self.config.parity_order,
            'parity_vector': self.parity_vector.tolist(),
            'null_space_dimension': self.parity_vector.shape[0]
        }

        return residuals, metadata

    def reset(self) -> None:
        """Reset parity space generator state."""
        pass  # Parity space is stateless


class ParameterEstimationGenerator(ResidualGenerator):
    """Parameter estimation-based residual generator."""

    def __init__(self, config: ResidualGeneratorConfig, nominal_parameters: Dict[str, float]):
        """Initialize parameter estimation generator.

        Parameters
        ----------
        config : ResidualGeneratorConfig
            Configuration parameters
        nominal_parameters : Dict[str, float]
            Nominal parameter values
        """
        self.config = config
        self.nominal_parameters = nominal_parameters
        self.parameter_names = list(nominal_parameters.keys())
        self.reset()

    def generate_residual(self, data: DataProtocol, system_model: SystemModel) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Generate parameter estimation residual."""
        if not hasattr(data, 'states') or not hasattr(data, 'times'):
            raise ValueError("Data must contain states and times")

        states = data.states
        times = data.times
        controls = getattr(data, 'controls', np.zeros((len(times)-1, 1)))

        if states.ndim == 1:
            states = states.reshape(-1, 1)
        if controls.ndim == 1:
            controls = controls.reshape(-1, 1)

        residuals = []
        estimated_parameters = []

        window_size = self.config.estimation_window_size

        for i in range(window_size, len(states)):
            # Extract window data
            window_states = states[i-window_size:i+1]
            window_controls = controls[max(0, i-window_size):i]
            window_times = times[i-window_size:i+1]

            # Estimate parameters using least squares
            try:
                params = self._estimate_parameters(window_states, window_controls, window_times)

                # Compute parameter residual
                param_residual = []
                for param_name in self.parameter_names:
                    nominal_val = self.nominal_parameters[param_name]
                    estimated_val = params.get(param_name, nominal_val)
                    residual = estimated_val - nominal_val
                    param_residual.append(residual)

                residuals.append(param_residual)
                estimated_parameters.append(params)

            except Exception as e:
                warnings.warn(f"Parameter estimation failed at step {i}: {e}")
                continue

        residuals = np.array(residuals) if residuals else np.array([]).reshape(0, len(self.parameter_names))

        metadata = {
            'method': 'parameter_estimation',
            'nominal_parameters': self.nominal_parameters,
            'estimated_parameters': estimated_parameters,
            'parameter_names': self.parameter_names
        }

        return residuals, metadata

    def _estimate_parameters(self, states: np.ndarray, controls: np.ndarray, times: np.ndarray) -> Dict[str, float]:
        """Estimate parameters from data window."""
        # Simplified parameter estimation using finite differences
        # In practice, would use more sophisticated methods like recursive least squares

        if len(states) < 3:
            return self.nominal_parameters.copy()

        # Compute state derivatives using finite differences
        dt = np.mean(np.diff(times))
        state_derivatives = np.gradient(states, dt, axis=0)

        # Simple linear regression for demonstration
        # This would be replaced with proper system identification
        estimated_params = {}

        for param_name, nominal_value in self.nominal_parameters.items():
            # Placeholder estimation - would implement proper identification
            # For now, add some noise to nominal value
            noise = np.random.normal(0, 0.01 * abs(nominal_value))
            estimated_params[param_name] = nominal_value + noise

        return estimated_params

    def reset(self) -> None:
        """Reset parameter estimation state."""
        self._parameter_history: List[Dict[str, float]] = []


class AdaptiveResidualGenerator(ResidualGenerator):
    """Adaptive residual generator that combines multiple methods."""

    def __init__(self, generators: List[ResidualGenerator], weights: Optional[List[float]] = None):
        """Initialize adaptive generator.

        Parameters
        ----------
        generators : List[ResidualGenerator]
            List of residual generators to combine
        weights : List[float], optional
            Weights for combining generators
        """
        self.generators = generators
        self.weights = weights if weights is not None else [1.0] * len(generators)

        if len(self.weights) != len(self.generators):
            raise ValueError("Number of weights must match number of generators")

        self.reset()

    def generate_residual(self, data: DataProtocol, system_model: SystemModel) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Generate adaptive residual by combining multiple methods."""
        all_residuals = []
        all_metadata = []

        for i, generator in enumerate(self.generators):
            try:
                residual, metadata = generator.generate_residual(data, system_model)
                all_residuals.append(residual)
                all_metadata.append(metadata)
            except Exception as e:
                warnings.warn(f"Generator {i} failed: {e}")
                continue

        if not all_residuals:
            return np.array([]).reshape(0, 1), {'error': 'All generators failed'}

        # Combine residuals (simplified approach)
        # In practice, would use more sophisticated fusion methods
        combined_residual = self._combine_residuals(all_residuals)

        combined_metadata = {
            'method': 'adaptive_combination',
            'individual_methods': all_metadata,
            'weights': self.weights,
            'num_successful_generators': len(all_residuals)
        }

        return combined_residual, combined_metadata

    def _combine_residuals(self, residuals: List[np.ndarray]) -> np.ndarray:
        """Combine residuals from multiple generators."""
        if not residuals:
            return np.array([]).reshape(0, 1)

        # Find common length
        min_length = min(len(r) for r in residuals)

        # Truncate all residuals to common length
        truncated_residuals = [r[:min_length] for r in residuals]

        # Weighted combination
        combined = np.zeros_like(truncated_residuals[0])
        total_weight = 0.0

        for i, residual in enumerate(truncated_residuals):
            weight = self.weights[i] if i < len(self.weights) else 1.0
            combined += weight * residual
            total_weight += weight

        if total_weight > 0:
            combined /= total_weight

        return combined

    def reset(self) -> None:
        """Reset all generators."""
        for generator in self.generators:
            generator.reset()


def create_residual_generator(method: str, config: Optional[ResidualGeneratorConfig] = None, **kwargs) -> ResidualGenerator:
    """Factory function to create residual generators.

    Parameters
    ----------
    method : str
        Type of generator ('observer', 'kalman', 'parity', 'parameter_estimation', 'adaptive')
    config : ResidualGeneratorConfig, optional
        Configuration parameters
    **kwargs
        Additional parameters specific to each method

    Returns
    -------
    ResidualGenerator
        Configured residual generator
    """
    if config is None:
        config = ResidualGeneratorConfig()

    if method == 'observer':
        A = kwargs.get('A')
        C = kwargs.get('C')
        if A is None or C is None:
            raise ValueError("Observer method requires A and C matrices")
        return ObserverBasedGenerator(config, A, C)

    elif method == 'kalman':
        A = kwargs.get('A')
        B = kwargs.get('B')
        C = kwargs.get('C')
        D = kwargs.get('D')
        if A is None or B is None or C is None:
            raise ValueError("Kalman method requires A, B, and C matrices")
        return KalmanFilterGenerator(config, A, B, C, D)

    elif method == 'parity':
        A = kwargs.get('A')
        B = kwargs.get('B')
        C = kwargs.get('C')
        if A is None or B is None or C is None:
            raise ValueError("Parity method requires A, B, and C matrices")
        return ParitySpaceGenerator(config, A, B, C)

    elif method == 'parameter_estimation':
        nominal_parameters = kwargs.get('nominal_parameters')
        if nominal_parameters is None:
            raise ValueError("Parameter estimation method requires nominal_parameters")
        return ParameterEstimationGenerator(config, nominal_parameters)

    elif method == 'adaptive':
        generators = kwargs.get('generators')
        weights = kwargs.get('weights')
        if generators is None:
            raise ValueError("Adaptive method requires list of generators")
        return AdaptiveResidualGenerator(generators, weights)

    else:
        raise ValueError(f"Unknown residual generation method: {method}")


class ResidualGeneratorFactory:
    """
    Factory class for creating residual generators.

    This class provides a unified interface for creating different types of
    residual generators used in fault detection systems.
    """

    @staticmethod
    def create_generator(method: str, config: Optional[ResidualGeneratorConfig] = None, **kwargs) -> ResidualGenerator:
        """
        Create a residual generator of the specified type.

        Parameters
        ----------
        method : str
            Type of generator ('observer', 'kalman', 'parity', 'parameter_estimation', 'adaptive')
        config : ResidualGeneratorConfig, optional
            Configuration parameters
        **kwargs
            Additional parameters specific to each method

        Returns
        -------
        ResidualGenerator
            Configured residual generator
        """
        return create_residual_generator(method, config, **kwargs)

    @staticmethod
    def get_available_methods() -> List[str]:
        """Get list of available residual generation methods."""
        return ['observer', 'kalman', 'parity', 'parameter_estimation', 'adaptive']

    @classmethod
    def create_default_observer(cls, A: np.ndarray, C: np.ndarray) -> ObserverBasedGenerator:
        """Create observer-based generator with default configuration."""
        return cls.create_generator('observer', A=A, C=C)

    @classmethod
    def create_default_kalman(cls, A: np.ndarray, B: np.ndarray, C: np.ndarray, D: Optional[np.ndarray] = None) -> KalmanFilterGenerator:
        """Create Kalman filter generator with default configuration."""
        return cls.create_generator('kalman', A=A, B=B, C=C, D=D)