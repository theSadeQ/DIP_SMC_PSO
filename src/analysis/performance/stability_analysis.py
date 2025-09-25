#==========================================================================================\\\
#=================== src/analysis/performance/stability_analysis.py ====================\\\
#==========================================================================================\\\

"""Stability analysis tools for control systems.

This module provides comprehensive stability analysis capabilities including
Lyapunov analysis, eigenvalue analysis, and stability margin computation.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
from scipy import linalg, signal
import warnings
from dataclasses import dataclass

from ..core.interfaces import PerformanceAnalyzer, AnalysisResult, AnalysisStatus, DataProtocol
from ..core.data_structures import MetricResult, PerformanceMetrics


@dataclass
class StabilityAnalysisConfig:
    """Configuration for stability analysis."""
    eigenvalue_tolerance: float = 1e-8
    lyapunov_method: str = "continuous"  # "continuous" or "discrete"
    frequency_range: Tuple[float, float] = (0.01, 1000.0)
    num_frequency_points: int = 1000
    include_robustness_analysis: bool = True
    uncertainty_bounds: Optional[Dict[str, float]] = None


class StabilityAnalyzer(PerformanceAnalyzer):
    """Comprehensive stability analysis for linear and nonlinear systems."""

    def __init__(self, config: Optional[StabilityAnalysisConfig] = None):
        """Initialize stability analyzer.

        Parameters
        ----------
        config : StabilityAnalysisConfig, optional
            Configuration for stability analysis
        """
        self.config = config or StabilityAnalysisConfig()

    @property
    def analyzer_name(self) -> str:
        """Name of the analyzer."""
        return "StabilityAnalyzer"

    @property
    def required_data_fields(self) -> List[str]:
        """Required data fields for analysis."""
        return ['times', 'states']

    def analyze(self, data: DataProtocol, **kwargs) -> AnalysisResult:
        """Perform comprehensive stability analysis.

        Parameters
        ----------
        data : DataProtocol
            Simulation data
        **kwargs
            Additional parameters including:
            - system_matrices: (A, B, C, D) for linear analysis
            - linearization_point: equilibrium point for linearization
            - parameter_uncertainties: uncertainty ranges for robustness

        Returns
        -------
        AnalysisResult
            Comprehensive stability analysis results
        """
        try:
            results = {}

            # 1. Empirical stability analysis from simulation data
            empirical_analysis = self._analyze_empirical_stability(data)
            results['empirical_stability'] = empirical_analysis

            # 2. Linear stability analysis (if system matrices provided)
            system_matrices = kwargs.get('system_matrices')
            if system_matrices is not None:
                linear_analysis = self._analyze_linear_stability(system_matrices)
                results['linear_stability'] = linear_analysis

                # 3. Frequency domain stability analysis
                frequency_analysis = self._analyze_frequency_domain_stability(system_matrices)
                results['frequency_stability'] = frequency_analysis

                # 4. Robustness analysis (if enabled)
                if self.config.include_robustness_analysis:
                    uncertainties = kwargs.get('parameter_uncertainties')
                    robustness_analysis = self._analyze_robustness(system_matrices, uncertainties)
                    results['robustness'] = robustness_analysis

            # 5. Lyapunov stability analysis
            lyapunov_analysis = self._analyze_lyapunov_stability(data, system_matrices)
            results['lyapunov_stability'] = lyapunov_analysis

            # 6. Bounded-input bounded-output (BIBO) stability
            bibo_analysis = self._analyze_bibo_stability(data)
            results['bibo_stability'] = bibo_analysis

            # 7. Overall stability assessment
            overall_assessment = self._generate_overall_assessment(results)
            results['overall_assessment'] = overall_assessment

            return AnalysisResult(
                status=AnalysisStatus.SUCCESS,
                message="Stability analysis completed successfully",
                data=results,
                metadata={
                    'analyzer': self.analyzer_name,
                    'config': self.config.__dict__
                }
            )

        except Exception as e:
            return AnalysisResult(
                status=AnalysisStatus.ERROR,
                message=f"Stability analysis failed: {str(e)}",
                data={'error_details': str(e)}
            )

    def _analyze_empirical_stability(self, data: DataProtocol) -> Dict[str, Any]:
        """Analyze stability from simulation data."""
        results = {}

        # State boundedness analysis
        boundedness = self._check_state_boundedness(data.states)
        results['boundedness'] = boundedness

        # Trajectory convergence analysis
        convergence = self._analyze_trajectory_convergence(data)
        results['convergence'] = convergence

        # Energy dissipation analysis
        energy_analysis = self._analyze_energy_dissipation(data)
        results['energy_dissipation'] = energy_analysis

        # Stability indicators from time series
        time_series_indicators = self._compute_time_series_stability_indicators(data)
        results['time_series_indicators'] = time_series_indicators

        return results

    def _analyze_linear_stability(self, system_matrices: Tuple[np.ndarray, ...]) -> Dict[str, Any]:
        """Analyze stability of linear system."""
        A, B, C, D = system_matrices
        results = {}

        # Eigenvalue analysis
        eigenvalues = linalg.eigvals(A)
        eigenvalue_analysis = self._analyze_eigenvalues(eigenvalues)
        results['eigenvalues'] = eigenvalue_analysis

        # Controllability and observability
        controllability = self._check_controllability(A, B)
        observability = self._check_observability(A, C)
        results['controllability'] = controllability
        results['observability'] = observability

        # Stability margins for continuous-time systems
        if self.config.lyapunov_method == "continuous":
            stability_margins = self._compute_continuous_stability_margins(A)
            results['stability_margins'] = stability_margins

        # Discrete-time stability analysis
        elif self.config.lyapunov_method == "discrete":
            discrete_stability = self._analyze_discrete_stability(A)
            results['discrete_stability'] = discrete_stability

        return results

    def _analyze_frequency_domain_stability(self, system_matrices: Tuple[np.ndarray, ...]) -> Dict[str, Any]:
        """Analyze stability in frequency domain."""
        A, B, C, D = system_matrices
        results = {}

        try:
            # Create state-space system
            sys = signal.StateSpace(A, B, C, D)

            # Frequency response
            frequencies = np.logspace(
                np.log10(self.config.frequency_range[0]),
                np.log10(self.config.frequency_range[1]),
                self.config.num_frequency_points
            )

            w, H = signal.freqresp(sys, frequencies)

            # Nyquist stability analysis
            nyquist_analysis = self._analyze_nyquist_stability(w, H)
            results['nyquist'] = nyquist_analysis

            # Bode stability analysis
            bode_analysis = self._analyze_bode_stability(w, H)
            results['bode'] = bode_analysis

            # Gain and phase margins
            margins = self._compute_stability_margins(w, H)
            results['margins'] = margins

        except Exception as e:
            results['error'] = f"Frequency domain analysis failed: {str(e)}"

        return results

    def _analyze_robustness(self, system_matrices: Tuple[np.ndarray, ...],
                          uncertainties: Optional[Dict[str, float]]) -> Dict[str, Any]:
        """Analyze robustness to parameter uncertainties."""
        A, B, C, D = system_matrices
        results = {}

        if uncertainties is None:
            uncertainties = self.config.uncertainty_bounds or {}

        # Structured singular value analysis (simplified)
        if uncertainties:
            robustness_margins = self._compute_robustness_margins(A, uncertainties)
            results['robustness_margins'] = robustness_margins

        # Sensitivity analysis
        sensitivity_analysis = self._compute_sensitivity_analysis(A)
        results['sensitivity'] = sensitivity_analysis

        # Monte Carlo robustness analysis
        if uncertainties:
            monte_carlo_results = self._monte_carlo_robustness(A, uncertainties)
            results['monte_carlo'] = monte_carlo_results

        return results

    def _analyze_lyapunov_stability(self, data: DataProtocol,
                                  system_matrices: Optional[Tuple[np.ndarray, ...]]) -> Dict[str, Any]:
        """Analyze Lyapunov stability."""
        results = {}

        # Empirical Lyapunov function estimation
        empirical_lyapunov = self._estimate_empirical_lyapunov_function(data)
        results['empirical_lyapunov'] = empirical_lyapunov

        # Analytical Lyapunov analysis (if linear system available)
        if system_matrices is not None:
            A, B, C, D = system_matrices
            analytical_lyapunov = self._analyze_analytical_lyapunov(A)
            results['analytical_lyapunov'] = analytical_lyapunov

        return results

    def _analyze_bibo_stability(self, data: DataProtocol) -> Dict[str, Any]:
        """Analyze bounded-input bounded-output stability."""
        results = {}

        # Check input boundedness
        if hasattr(data, 'controls'):
            input_bounded = self._check_signal_boundedness(data.controls)
            results['input_bounded'] = input_bounded

        # Check output boundedness
        output_bounded = self._check_signal_boundedness(data.states)
        results['output_bounded'] = output_bounded

        # BIBO stability conclusion
        if hasattr(data, 'controls'):
            bibo_stable = input_bounded['is_bounded'] and output_bounded['is_bounded']
            results['bibo_stable'] = bibo_stable
        else:
            results['bibo_stable'] = output_bounded['is_bounded']

        return results

    def _check_state_boundedness(self, states: np.ndarray) -> Dict[str, Any]:
        """Check if states remain bounded."""
        if states.ndim == 1:
            states = states.reshape(-1, 1)

        results = {}
        for i in range(states.shape[1]):
            state = states[:, i]
            state_analysis = {
                'max_value': float(np.max(state)),
                'min_value': float(np.min(state)),
                'range': float(np.ptp(state)),
                'is_bounded': bool(np.all(np.isfinite(state))),
                'growth_rate': self._estimate_growth_rate(state)
            }
            results[f'state_{i}'] = state_analysis

        # Overall boundedness
        all_bounded = all(state_info['is_bounded'] for state_info in results.values())
        results['overall_bounded'] = all_bounded

        return results

    def _analyze_trajectory_convergence(self, data: DataProtocol) -> Dict[str, Any]:
        """Analyze trajectory convergence properties."""
        states = data.states
        times = data.times

        if states.ndim == 1:
            states = states.reshape(-1, 1)

        results = {}

        # Compute state magnitude trajectory
        state_magnitude = np.sqrt(np.sum(states**2, axis=1))

        # Convergence analysis
        convergence_info = {
            'initial_magnitude': float(state_magnitude[0]),
            'final_magnitude': float(state_magnitude[-1]),
            'convergence_ratio': float(state_magnitude[-1] / (state_magnitude[0] + 1e-12)),
            'is_converging': bool(state_magnitude[-1] < state_magnitude[0])
        }

        # Estimate convergence rate
        convergence_rate = self._estimate_convergence_rate(times, state_magnitude)
        convergence_info['convergence_rate'] = convergence_rate

        # Asymptotic behavior
        asymptotic_analysis = self._analyze_asymptotic_behavior(times, state_magnitude)
        convergence_info.update(asymptotic_analysis)

        results['magnitude_convergence'] = convergence_info

        return results

    def _analyze_energy_dissipation(self, data: DataProtocol) -> Dict[str, Any]:
        """Analyze energy dissipation properties."""
        states = data.states
        times = data.times

        if states.ndim == 1:
            states = states.reshape(-1, 1)

        # Compute energy (quadratic Lyapunov function)
        energy = 0.5 * np.sum(states**2, axis=1)

        # Energy dissipation analysis
        initial_energy = energy[0]
        final_energy = energy[-1]
        energy_change = final_energy - initial_energy

        # Energy derivative (dissipation rate)
        if len(times) > 1:
            dt = np.mean(np.diff(times))
            energy_derivative = np.gradient(energy, dt)
            avg_dissipation_rate = np.mean(energy_derivative[energy_derivative < 0])
        else:
            avg_dissipation_rate = 0.0

        results = {
            'initial_energy': float(initial_energy),
            'final_energy': float(final_energy),
            'energy_change': float(energy_change),
            'energy_dissipated': bool(energy_change < 0),
            'avg_dissipation_rate': float(avg_dissipation_rate),
            'energy_trajectory': energy.tolist()
        }

        return results

    def _compute_time_series_stability_indicators(self, data: DataProtocol) -> Dict[str, Any]:
        """Compute stability indicators from time series."""
        states = data.states
        if states.ndim == 1:
            states = states.reshape(-1, 1)

        results = {}

        # Largest Lyapunov exponent estimation (simplified)
        lyapunov_exponent = self._estimate_largest_lyapunov_exponent(states)
        results['largest_lyapunov_exponent'] = lyapunov_exponent

        # Stability index based on variance growth
        stability_index = self._compute_stability_index(states)
        results['stability_index'] = stability_index

        # Recurrence analysis
        recurrence_analysis = self._analyze_recurrence(states)
        results['recurrence'] = recurrence_analysis

        return results

    def _analyze_eigenvalues(self, eigenvalues: np.ndarray) -> Dict[str, Any]:
        """Analyze eigenvalue properties for stability."""
        results = {}

        # Real parts
        real_parts = np.real(eigenvalues)
        imaginary_parts = np.imag(eigenvalues)

        # Stability criteria
        max_real_part = np.max(real_parts)
        is_stable = max_real_part < -self.config.eigenvalue_tolerance
        is_marginally_stable = abs(max_real_part) <= self.config.eigenvalue_tolerance

        results['eigenvalues'] = {
            'values': eigenvalues.tolist(),
            'real_parts': real_parts.tolist(),
            'imaginary_parts': imaginary_parts.tolist(),
            'max_real_part': float(max_real_part),
            'is_stable': is_stable,
            'is_marginally_stable': is_marginally_stable,
            'stability_margin': float(-max_real_part)
        }

        # Dominant eigenvalues
        dominant_eigenvalue = eigenvalues[np.argmax(real_parts)]
        results['dominant_eigenvalue'] = {
            'value': complex(dominant_eigenvalue),
            'real_part': float(np.real(dominant_eigenvalue)),
            'imaginary_part': float(np.imag(dominant_eigenvalue)),
            'magnitude': float(np.abs(dominant_eigenvalue)),
            'damping_ratio': self._compute_damping_ratio_from_eigenvalue(dominant_eigenvalue)
        }

        return results

    def _check_controllability(self, A: np.ndarray, B: np.ndarray) -> Dict[str, Any]:
        """Check system controllability."""
        n = A.shape[0]

        # Controllability matrix
        C_matrix = B.copy()
        for i in range(1, n):
            C_matrix = np.hstack([C_matrix, np.linalg.matrix_power(A, i) @ B])

        # Rank test
        rank = np.linalg.matrix_rank(C_matrix)
        is_controllable = rank == n

        return {
            'is_controllable': is_controllable,
            'controllability_rank': int(rank),
            'required_rank': int(n),
            'controllability_matrix_condition': float(np.linalg.cond(C_matrix))
        }

    def _check_observability(self, A: np.ndarray, C: np.ndarray) -> Dict[str, Any]:
        """Check system observability."""
        n = A.shape[0]

        # Observability matrix
        O_matrix = C.copy()
        for i in range(1, n):
            O_matrix = np.vstack([O_matrix, C @ np.linalg.matrix_power(A, i)])

        # Rank test
        rank = np.linalg.matrix_rank(O_matrix)
        is_observable = rank == n

        return {
            'is_observable': is_observable,
            'observability_rank': int(rank),
            'required_rank': int(n),
            'observability_matrix_condition': float(np.linalg.cond(O_matrix))
        }

    def _compute_continuous_stability_margins(self, A: np.ndarray) -> Dict[str, Any]:
        """Compute stability margins for continuous-time systems."""
        eigenvalues = linalg.eigvals(A)
        real_parts = np.real(eigenvalues)

        # Stability margin (distance to imaginary axis)
        stability_margin = -np.max(real_parts)

        # Relative stability (smallest distance relative to largest eigenvalue magnitude)
        max_magnitude = np.max(np.abs(eigenvalues))
        relative_margin = stability_margin / (max_magnitude + 1e-12)

        return {
            'absolute_margin': float(stability_margin),
            'relative_margin': float(relative_margin),
            'critical_eigenvalue': complex(eigenvalues[np.argmax(real_parts)])
        }

    def _analyze_discrete_stability(self, A: np.ndarray) -> Dict[str, Any]:
        """Analyze stability for discrete-time systems."""
        eigenvalues = linalg.eigvals(A)
        magnitudes = np.abs(eigenvalues)

        # Stability criteria (all eigenvalues inside unit circle)
        max_magnitude = np.max(magnitudes)
        is_stable = max_magnitude < 1.0 - self.config.eigenvalue_tolerance
        is_marginally_stable = abs(max_magnitude - 1.0) <= self.config.eigenvalue_tolerance

        # Stability margin (distance to unit circle)
        stability_margin = 1.0 - max_magnitude

        return {
            'eigenvalue_magnitudes': magnitudes.tolist(),
            'max_magnitude': float(max_magnitude),
            'is_stable': is_stable,
            'is_marginally_stable': is_marginally_stable,
            'stability_margin': float(stability_margin)
        }

    def _analyze_nyquist_stability(self, frequencies: np.ndarray, H: np.ndarray) -> Dict[str, Any]:
        """Analyze stability using Nyquist criterion."""
        # Simplified Nyquist analysis
        # Full implementation would require careful encirclement counting

        real_parts = np.real(H.flatten())
        imag_parts = np.imag(H.flatten())

        # Critical point analysis (-1, 0)
        distances_to_critical = np.abs(H.flatten() + 1.0)
        min_distance = np.min(distances_to_critical)

        return {
            'min_distance_to_critical_point': float(min_distance),
            'nyquist_real': real_parts.tolist(),
            'nyquist_imag': imag_parts.tolist(),
            'frequencies': frequencies.tolist()
        }

    def _analyze_bode_stability(self, frequencies: np.ndarray, H: np.ndarray) -> Dict[str, Any]:
        """Analyze stability from Bode plots."""
        magnitude_db = 20 * np.log10(np.abs(H.flatten()))
        phase_deg = np.angle(H.flatten()) * 180 / np.pi

        # Find gain crossover frequency (|H| = 1, or 0 dB)
        gain_crossover_indices = np.where(np.diff(np.sign(magnitude_db)))[0]

        if len(gain_crossover_indices) > 0:
            gain_crossover_freq = frequencies[gain_crossover_indices[0]]
            phase_at_crossover = phase_deg[gain_crossover_indices[0]]
        else:
            gain_crossover_freq = np.nan
            phase_at_crossover = np.nan

        return {
            'magnitude_db': magnitude_db.tolist(),
            'phase_deg': phase_deg.tolist(),
            'gain_crossover_frequency': float(gain_crossover_freq),
            'phase_at_gain_crossover': float(phase_at_crossover)
        }

    def _compute_stability_margins(self, frequencies: np.ndarray, H: np.ndarray) -> Dict[str, Any]:
        """Compute gain and phase margins."""
        magnitude_db = 20 * np.log10(np.abs(H.flatten()))
        phase_deg = np.angle(H.flatten()) * 180 / np.pi

        # Gain margin (at phase crossover frequency where phase = -180°)
        phase_crossover_indices = np.where(
            np.abs(phase_deg + 180.0) < 5.0  # Within 5 degrees of -180°
        )[0]

        if len(phase_crossover_indices) > 0:
            gain_margin_db = -magnitude_db[phase_crossover_indices[0]]
            phase_crossover_freq = frequencies[phase_crossover_indices[0]]
        else:
            gain_margin_db = np.inf
            phase_crossover_freq = np.nan

        # Phase margin (at gain crossover frequency where |H| = 1)
        gain_crossover_indices = np.where(np.abs(magnitude_db) < 1.0)[0]

        if len(gain_crossover_indices) > 0:
            phase_margin_deg = 180.0 + phase_deg[gain_crossover_indices[0]]
            gain_crossover_freq = frequencies[gain_crossover_indices[0]]
        else:
            phase_margin_deg = np.inf
            gain_crossover_freq = np.nan

        return {
            'gain_margin_db': float(gain_margin_db),
            'phase_margin_deg': float(phase_margin_deg),
            'gain_crossover_frequency': float(gain_crossover_freq),
            'phase_crossover_frequency': float(phase_crossover_freq)
        }

    def _estimate_growth_rate(self, signal: np.ndarray) -> float:
        """Estimate growth rate of a signal."""
        if len(signal) < 2:
            return 0.0

        # Fit exponential growth: y = A * exp(λt)
        try:
            log_signal = np.log(np.abs(signal) + 1e-12)
            time_indices = np.arange(len(signal))
            growth_rate = np.polyfit(time_indices, log_signal, 1)[0]
            return float(growth_rate)
        except:
            return 0.0

    def _estimate_convergence_rate(self, times: np.ndarray, magnitude: np.ndarray) -> float:
        """Estimate convergence rate from trajectory magnitude."""
        if len(magnitude) < 10:
            return 0.0

        try:
            # Fit exponential decay in the latter half
            half_point = len(magnitude) // 2
            t_fit = times[half_point:] - times[half_point]
            y_fit = magnitude[half_point:]

            # Avoid log of zero
            y_fit = y_fit[y_fit > 1e-12]
            t_fit = t_fit[:len(y_fit)]

            if len(y_fit) < 3:
                return 0.0

            log_y = np.log(y_fit)
            convergence_rate = -np.polyfit(t_fit, log_y, 1)[0]
            return float(max(0.0, convergence_rate))

        except:
            return 0.0

    def _analyze_asymptotic_behavior(self, times: np.ndarray, magnitude: np.ndarray) -> Dict[str, float]:
        """Analyze asymptotic behavior of trajectory."""
        if len(magnitude) < 10:
            return {'asymptotic_value': float(magnitude[-1]), 'convergence_quality': 0.0}

        # Estimate asymptotic value
        window_size = min(len(magnitude) // 4, 50)
        asymptotic_value = np.mean(magnitude[-window_size:])

        # Convergence quality (variance in final portion)
        convergence_quality = 1.0 / (1.0 + np.var(magnitude[-window_size:]))

        return {
            'asymptotic_value': float(asymptotic_value),
            'convergence_quality': float(convergence_quality)
        }

    def _check_signal_boundedness(self, signal: np.ndarray) -> Dict[str, Any]:
        """Check if a signal is bounded."""
        if signal.ndim > 1:
            signal_norm = np.sqrt(np.sum(signal**2, axis=1))
        else:
            signal_norm = np.abs(signal)

        is_bounded = np.all(np.isfinite(signal_norm))
        max_value = np.max(signal_norm) if is_bounded else np.inf

        return {
            'is_bounded': is_bounded,
            'max_value': float(max_value),
            'signal_norm': signal_norm.tolist()
        }

    def _estimate_empirical_lyapunov_function(self, data: DataProtocol) -> Dict[str, Any]:
        """Estimate empirical Lyapunov function from data."""
        states = data.states
        if states.ndim == 1:
            states = states.reshape(-1, 1)

        # Simple quadratic Lyapunov function candidate
        V = 0.5 * np.sum(states**2, axis=1)

        # Compute derivative
        if len(data.times) > 1:
            dt = np.mean(np.diff(data.times))
            dV_dt = np.gradient(V, dt)

            # Check negative definiteness
            negative_derivative_ratio = np.sum(dV_dt < 0) / len(dV_dt)
        else:
            dV_dt = np.array([0.0])
            negative_derivative_ratio = 0.0

        return {
            'lyapunov_function_values': V.tolist(),
            'derivative_values': dV_dt.tolist(),
            'negative_derivative_ratio': float(negative_derivative_ratio),
            'is_decreasing': bool(negative_derivative_ratio > 0.8)
        }

    def _analyze_analytical_lyapunov(self, A: np.ndarray) -> Dict[str, Any]:
        """Analyze Lyapunov stability analytically."""
        try:
            # Solve Lyapunov equation: A^T P + P A = -Q
            Q = np.eye(A.shape[0])  # Positive definite matrix
            P = linalg.solve_lyapunov(A.T, -Q)

            # Check if P is positive definite
            eigenvals_P = linalg.eigvals(P)
            is_positive_definite = np.all(eigenvals_P > self.config.eigenvalue_tolerance)

            # Stability conclusion
            is_stable = is_positive_definite

            return {
                'lyapunov_matrix_P': P.tolist(),
                'P_eigenvalues': eigenvals_P.tolist(),
                'is_positive_definite': is_positive_definite,
                'is_stable': is_stable,
                'condition_number': float(np.linalg.cond(P))
            }

        except Exception as e:
            return {
                'error': f"Lyapunov analysis failed: {str(e)}",
                'is_stable': False
            }

    def _estimate_largest_lyapunov_exponent(self, states: np.ndarray) -> float:
        """Estimate largest Lyapunov exponent (simplified method)."""
        # This is a very simplified estimation
        # Production code would use more sophisticated methods

        if states.shape[0] < 10 or states.shape[1] == 0:
            return 0.0

        try:
            # Use first state variable
            x = states[:, 0]

            # Compute divergence rate
            diffs = np.abs(np.diff(x))
            valid_diffs = diffs[diffs > 1e-12]

            if len(valid_diffs) > 0:
                log_diffs = np.log(valid_diffs)
                return float(np.mean(log_diffs))
            else:
                return 0.0

        except:
            return 0.0

    def _compute_stability_index(self, states: np.ndarray) -> float:
        """Compute stability index based on variance growth."""
        if states.shape[0] < 2:
            return 1.0

        # Compute variance over time
        window_size = max(10, states.shape[0] // 10)
        n_windows = states.shape[0] // window_size

        if n_windows < 2:
            return 1.0

        variances = []
        for i in range(n_windows):
            start_idx = i * window_size
            end_idx = min((i + 1) * window_size, states.shape[0])
            window_data = states[start_idx:end_idx]
            variances.append(np.var(window_data))

        # Stability index (1 = stable, 0 = unstable)
        if len(variances) > 1:
            variance_trend = np.polyfit(range(len(variances)), variances, 1)[0]
            stability_index = 1.0 / (1.0 + abs(variance_trend))
        else:
            stability_index = 1.0

        return float(stability_index)

    def _analyze_recurrence(self, states: np.ndarray) -> Dict[str, float]:
        """Analyze recurrence properties (simplified)."""
        if states.shape[0] < 10:
            return {'recurrence_rate': 0.0, 'determinism': 0.0}

        # Simplified recurrence analysis
        # In production, would use proper recurrence quantification analysis

        # Compute state magnitude
        magnitude = np.sqrt(np.sum(states**2, axis=1))

        # Simple recurrence measure
        threshold = 0.1 * np.std(magnitude)
        recurrence_count = 0

        for i in range(len(magnitude)):
            for j in range(i + 1, len(magnitude)):
                if abs(magnitude[i] - magnitude[j]) < threshold:
                    recurrence_count += 1

        max_possible_recurrences = len(magnitude) * (len(magnitude) - 1) / 2
        recurrence_rate = recurrence_count / max_possible_recurrences

        return {
            'recurrence_rate': float(recurrence_rate),
            'determinism': float(min(1.0, 2.0 * recurrence_rate))  # Simplified
        }

    def _compute_damping_ratio_from_eigenvalue(self, eigenvalue: complex) -> float:
        """Compute damping ratio from complex eigenvalue."""
        real_part = np.real(eigenvalue)
        imag_part = np.imag(eigenvalue)

        if abs(imag_part) < 1e-12:
            # Real eigenvalue
            return 1.0 if real_part < 0 else 0.0
        else:
            # Complex eigenvalue
            magnitude = abs(eigenvalue)
            if magnitude > 1e-12:
                damping_ratio = -real_part / magnitude
                return float(max(0.0, min(1.0, damping_ratio)))
            else:
                return 0.0

    def _compute_robustness_margins(self, A: np.ndarray, uncertainties: Dict[str, float]) -> Dict[str, float]:
        """Compute robustness margins (simplified)."""
        # Simplified robustness analysis
        # Production code would implement proper structured singular value analysis

        base_eigenvalues = linalg.eigvals(A)
        base_stability_margin = -np.max(np.real(base_eigenvalues))

        # Estimate how uncertainty affects stability
        uncertainty_magnitude = np.sqrt(sum(v**2 for v in uncertainties.values()))
        estimated_margin_reduction = uncertainty_magnitude * np.max(np.abs(base_eigenvalues))

        robust_stability_margin = base_stability_margin - estimated_margin_reduction

        return {
            'nominal_stability_margin': float(base_stability_margin),
            'robust_stability_margin': float(robust_stability_margin),
            'margin_reduction': float(estimated_margin_reduction),
            'is_robustly_stable': bool(robust_stability_margin > 0)
        }

    def _compute_sensitivity_analysis(self, A: np.ndarray) -> Dict[str, float]:
        """Compute sensitivity of eigenvalues to parameter changes."""
        eigenvalues = linalg.eigvals(A)

        # Eigenvalue condition numbers (simplified)
        try:
            # This is a simplified measure
            condition_numbers = []
            for eigval in eigenvalues:
                # Condition number related to how sensitive eigenvalue is to A
                cond_num = 1.0 / abs(np.real(eigval)) if abs(np.real(eigval)) > 1e-12 else np.inf
                condition_numbers.append(cond_num)

            max_sensitivity = np.max(condition_numbers)
            avg_sensitivity = np.mean(condition_numbers)

        except:
            max_sensitivity = np.inf
            avg_sensitivity = np.inf

        return {
            'max_eigenvalue_sensitivity': float(max_sensitivity),
            'average_eigenvalue_sensitivity': float(avg_sensitivity)
        }

    def _monte_carlo_robustness(self, A: np.ndarray, uncertainties: Dict[str, float],
                              n_samples: int = 100) -> Dict[str, Any]:
        """Monte Carlo robustness analysis."""
        stable_count = 0
        stability_margins = []

        for _ in range(n_samples):
            # Perturb system matrix (simplified)
            perturbation = np.random.normal(0, 0.01, A.shape)  # 1% random perturbation
            A_perturbed = A + perturbation

            # Check stability
            eigenvalues = linalg.eigvals(A_perturbed)
            max_real_part = np.max(np.real(eigenvalues))

            if max_real_part < 0:
                stable_count += 1

            stability_margins.append(-max_real_part)

        robust_stability_probability = stable_count / n_samples

        return {
            'robust_stability_probability': float(robust_stability_probability),
            'stability_margins_distribution': stability_margins,
            'mean_stability_margin': float(np.mean(stability_margins)),
            'std_stability_margin': float(np.std(stability_margins))
        }

    def _generate_overall_assessment(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall stability assessment."""
        assessment = {
            'overall_stable': True,
            'confidence_level': 'high',
            'key_findings': [],
            'recommendations': [],
            'stability_score': 85.0  # Placeholder scoring system
        }

        # Analyze empirical stability
        if 'empirical_stability' in results:
            empirical = results['empirical_stability']
            if not empirical.get('boundedness', {}).get('overall_bounded', True):
                assessment['overall_stable'] = False
                assessment['key_findings'].append('States are not bounded')

        # Analyze linear stability
        if 'linear_stability' in results:
            linear = results['linear_stability']
            eigenvalue_analysis = linear.get('eigenvalues', {})
            if not eigenvalue_analysis.get('is_stable', True):
                assessment['overall_stable'] = False
                assessment['key_findings'].append('System has unstable eigenvalues')

        # Analyze robustness
        if 'robustness' in results:
            robustness = results['robustness']
            if robustness.get('robustness_margins', {}).get('is_robustly_stable', True) == False:
                assessment['confidence_level'] = 'low'
                assessment['recommendations'].append('Improve robustness margins')

        # Generate recommendations based on findings
        if not assessment['overall_stable']:
            assessment['recommendations'].extend([
                'Redesign controller to ensure stability',
                'Check system parameters and operating conditions'
            ])

        return assessment


def create_stability_analyzer(config: Optional[Dict[str, Any]] = None) -> StabilityAnalyzer:
    """Factory function to create stability analyzer.

    Parameters
    ----------
    config : Dict[str, Any], optional
        Configuration parameters

    Returns
    -------
    StabilityAnalyzer
        Configured stability analyzer
    """
    if config is not None:
        analysis_config = StabilityAnalysisConfig(**config)
    else:
        analysis_config = StabilityAnalysisConfig()

    return StabilityAnalyzer(analysis_config)