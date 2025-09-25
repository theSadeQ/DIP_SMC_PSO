#==========================================================================================\\\
#===================== src/analysis/fault_detection/fdi_system.py =======================\\\
#==========================================================================================\\\

"""Enhanced fault detection and isolation system.

This module provides a comprehensive fault detection framework that extends
the basic FDI system with advanced diagnostic capabilities, multiple fault
detection methods, and statistical analysis.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any, Union, Callable
import numpy as np
from scipy import signal, stats
import warnings
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..core.interfaces import FaultDetector, AnalysisResult, AnalysisStatus, DataProtocol
from ..core.data_structures import FaultDetectionResult, StatisticalTestResult, ConfidenceInterval


class FaultType(Enum):
    """Enumeration of fault types."""
    NO_FAULT = "no_fault"
    SENSOR_FAULT = "sensor_fault"
    ACTUATOR_FAULT = "actuator_fault"
    PROCESS_FAULT = "process_fault"
    PARAMETER_DRIFT = "parameter_drift"
    UNKNOWN_FAULT = "unknown_fault"


class DetectionMethod(Enum):
    """Enumeration of detection methods."""
    RESIDUAL_BASED = "residual_based"
    STATISTICAL = "statistical"
    MODEL_BASED = "model_based"
    SIGNAL_BASED = "signal_based"
    MACHINE_LEARNING = "machine_learning"


@dataclass
class FaultDetectionConfig:
    """Configuration for enhanced fault detection system."""
    # Basic detection parameters
    residual_threshold: float = 0.5
    persistence_counter: int = 10
    confidence_level: float = 0.95

    # Adaptive thresholding
    enable_adaptive_threshold: bool = True
    adaptive_window_size: int = 50
    adaptive_factor: float = 3.0

    # CUSUM parameters
    enable_cusum: bool = True
    cusum_threshold: float = 5.0
    cusum_drift_rate: float = 0.5

    # Statistical detection
    enable_statistical_tests: bool = True
    statistical_window_size: int = 100
    change_point_sensitivity: float = 0.05

    # Signal-based detection
    enable_spectral_analysis: bool = True
    frequency_bands: List[Tuple[float, float]] = field(default_factory=lambda: [(0.1, 1.0), (1.0, 10.0), (10.0, 100.0)])

    # Classification parameters
    enable_fault_classification: bool = True
    classification_features: List[str] = field(default_factory=lambda: ['residual_mean', 'residual_std', 'spectral_energy'])

    # Advanced options
    enable_isolation: bool = True
    enable_severity_assessment: bool = True
    enable_prognosis: bool = False


@dataclass
class FaultSignature:
    """Signature for fault identification."""
    fault_type: FaultType
    detection_method: DetectionMethod
    features: Dict[str, float]
    confidence_score: float
    severity_level: float  # 0.0 to 1.0
    description: str


class EnhancedFaultDetector(FaultDetector):
    """Enhanced fault detection and isolation system."""

    def __init__(self, config: Optional[FaultDetectionConfig] = None):
        """Initialize enhanced fault detector.

        Parameters
        ----------
        config : FaultDetectionConfig, optional
            Configuration for fault detection
        """
        self.config = config or FaultDetectionConfig()
        self.reset()

    @property
    def detector_type(self) -> str:
        """Type of fault detector."""
        return "EnhancedFaultDetector"

    def detect(self, data: DataProtocol, **kwargs) -> AnalysisResult:
        """Detect faults in the system.

        Parameters
        ----------
        data : DataProtocol
            Real-time or batch data for fault detection
        **kwargs
            Additional parameters including:
            - dynamics_model: Model for residual generation
            - reference_model: Reference model for comparison
            - fault_signatures: Known fault signatures for classification

        Returns
        -------
        AnalysisResult
            Comprehensive fault detection and diagnosis results
        """
        try:
            results = {}

            # 1. Basic residual-based detection
            residual_detection = self._perform_residual_based_detection(data, **kwargs)
            results['residual_detection'] = residual_detection

            # 2. Statistical fault detection
            if self.config.enable_statistical_tests:
                statistical_detection = self._perform_statistical_detection(data)
                results['statistical_detection'] = statistical_detection

            # 3. Signal-based detection
            if self.config.enable_spectral_analysis:
                signal_detection = self._perform_signal_based_detection(data)
                results['signal_detection'] = signal_detection

            # 4. Change point detection
            change_point_detection = self._perform_change_point_detection(data)
            results['change_point_detection'] = change_point_detection

            # 5. Fault classification and isolation
            if self.config.enable_fault_classification:
                classification_results = self._perform_fault_classification(results, **kwargs)
                results['fault_classification'] = classification_results

            # 6. Severity assessment
            if self.config.enable_severity_assessment:
                severity_assessment = self._assess_fault_severity(results)
                results['severity_assessment'] = severity_assessment

            # 7. Fault isolation
            if self.config.enable_isolation:
                isolation_results = self._perform_fault_isolation(data, results, **kwargs)
                results['fault_isolation'] = isolation_results

            # 8. Overall fault status
            overall_status = self._determine_overall_status(results)
            results['overall_status'] = overall_status

            # 9. Diagnostic summary
            diagnostic_summary = self._generate_diagnostic_summary(results)
            results['diagnostic_summary'] = diagnostic_summary

            return AnalysisResult(
                status=AnalysisStatus.SUCCESS,
                message="Fault detection analysis completed successfully",
                data=results,
                metadata={
                    'detector_type': self.detector_type,
                    'config': self.config.__dict__,
                    'detection_timestamp': datetime.now().isoformat()
                }
            )

        except Exception as e:
            return AnalysisResult(
                status=AnalysisStatus.ERROR,
                message=f"Fault detection failed: {str(e)}",
                data={'error_details': str(e)}
            )

    def reset(self) -> None:
        """Reset detector state for new analysis."""
        self._detection_history: List[Dict[str, Any]] = []
        self._residual_history: List[float] = []
        self._statistical_buffers: Dict[str, List[float]] = {}
        self._last_state: Optional[np.ndarray] = None
        self._cusum_statistic: float = 0.0
        self._fault_state: str = "OK"
        self._fault_start_time: Optional[float] = None
        self._consecutive_violations: int = 0

    def _perform_residual_based_detection(self, data: DataProtocol, **kwargs) -> Dict[str, Any]:
        """Perform residual-based fault detection."""
        dynamics_model = kwargs.get('dynamics_model')

        if dynamics_model is None:
            return self._model_free_residual_detection(data)
        else:
            return self._model_based_residual_detection(data, dynamics_model)

    def _model_free_residual_detection(self, data: DataProtocol) -> Dict[str, Any]:
        """Model-free residual detection using statistical properties."""
        if not hasattr(data, 'states') or len(data.states) == 0:
            return {'error': 'No state data available'}

        states = data.states
        if states.ndim == 1:
            states = states.reshape(-1, 1)

        # Compute innovation-like residuals using differences
        if len(states) < 2:
            return {'residuals': [], 'detections': [], 'status': 'insufficient_data'}

        # Simple difference-based residuals
        state_diffs = np.diff(states, axis=0)
        residual_norms = np.sqrt(np.sum(state_diffs**2, axis=1))

        # Adaptive threshold computation
        if len(residual_norms) >= self.config.adaptive_window_size:
            window_data = residual_norms[-self.config.adaptive_window_size:]
            threshold = np.mean(window_data) + self.config.adaptive_factor * np.std(window_data)
        else:
            threshold = self.config.residual_threshold

        # Detection logic
        violations = residual_norms > threshold
        detections = self._apply_persistence_filter(violations)

        return {
            'residuals': residual_norms.tolist(),
            'threshold': float(threshold),
            'violations': violations.tolist(),
            'detections': detections.tolist(),
            'fault_detected': bool(np.any(detections)),
            'max_residual': float(np.max(residual_norms)),
            'mean_residual': float(np.mean(residual_norms))
        }

    def _model_based_residual_detection(self, data: DataProtocol, dynamics_model) -> Dict[str, Any]:
        """Model-based residual detection using dynamics prediction."""
        if not hasattr(data, 'states') or not hasattr(data, 'times'):
            return {'error': 'Insufficient data for model-based detection'}

        states = data.states
        times = data.times
        controls = getattr(data, 'controls', np.zeros(len(times) - 1))

        if states.ndim == 1:
            states = states.reshape(-1, 1)

        residuals = []
        predictions = []

        for i in range(1, len(states)):
            dt = times[i] - times[i-1]
            if dt <= 0:
                continue

            try:
                # Predict next state
                if i-1 < len(controls):
                    control = controls[i-1] if controls.ndim == 1 else controls[i-1, 0]
                else:
                    control = 0.0

                predicted_state = dynamics_model.step(states[i-1], control, dt)

                # Compute residual
                residual = states[i] - predicted_state
                residual_norm = np.linalg.norm(residual)

                residuals.append(residual_norm)
                predictions.append(predicted_state)

            except Exception as e:
                warnings.warn(f"Model prediction failed at step {i}: {e}")
                continue

        if not residuals:
            return {'error': 'No valid residuals computed'}

        residuals = np.array(residuals)

        # Adaptive threshold
        if len(residuals) >= self.config.adaptive_window_size:
            window_data = residuals[-self.config.adaptive_window_size:]
            threshold = np.mean(window_data) + self.config.adaptive_factor * np.std(window_data)
        else:
            threshold = self.config.residual_threshold

        # CUSUM detection
        cusum_detections = []
        cusum_stat = 0.0
        reference = np.median(residuals) if len(residuals) > 0 else 0.0

        for residual in residuals:
            cusum_stat = max(0.0, cusum_stat + (residual - reference - self.config.cusum_drift_rate))
            cusum_detections.append(cusum_stat > self.config.cusum_threshold)

        # Threshold-based detection
        violations = residuals > threshold
        threshold_detections = self._apply_persistence_filter(violations)

        # Combined detection
        combined_detections = np.logical_or(threshold_detections, cusum_detections)

        return {
            'residuals': residuals.tolist(),
            'predictions': [pred.tolist() for pred in predictions],
            'threshold': float(threshold),
            'violations': violations.tolist(),
            'threshold_detections': threshold_detections.tolist(),
            'cusum_detections': cusum_detections,
            'cusum_statistics': [cusum_stat],  # Would store full history in practice
            'combined_detections': combined_detections.tolist(),
            'fault_detected': bool(np.any(combined_detections)),
            'detection_method': 'model_based'
        }

    def _perform_statistical_detection(self, data: DataProtocol) -> Dict[str, Any]:
        """Perform statistical fault detection."""
        if not hasattr(data, 'states'):
            return {'error': 'No state data available'}

        states = data.states
        if states.ndim == 1:
            states = states.reshape(-1, 1)

        results = {}

        # Statistical tests for each state variable
        for i in range(states.shape[1]):
            state_var = states[:, i]

            # Normality test
            normality_test = self._test_normality(state_var)

            # Stationarity test
            stationarity_test = self._test_stationarity(state_var)

            # Outlier detection
            outlier_detection = self._detect_outliers(state_var)

            # Change point detection
            change_points = self._detect_change_points_statistical(state_var)

            results[f'state_{i}'] = {
                'normality_test': normality_test,
                'stationarity_test': stationarity_test,
                'outlier_detection': outlier_detection,
                'change_points': change_points
            }

        # Overall statistical assessment
        overall_assessment = self._assess_overall_statistical_health(results)
        results['overall_assessment'] = overall_assessment

        return results

    def _perform_signal_based_detection(self, data: DataProtocol) -> Dict[str, Any]:
        """Perform signal-based fault detection using frequency analysis."""
        if not hasattr(data, 'states') or not hasattr(data, 'times'):
            return {'error': 'Insufficient data for signal-based detection'}

        states = data.states
        times = data.times

        if states.ndim == 1:
            states = states.reshape(-1, 1)

        # Compute sampling rate
        dt = np.mean(np.diff(times)) if len(times) > 1 else 0.01
        fs = 1.0 / dt

        results = {}

        for i in range(states.shape[1]):
            state_signal = states[:, i]

            # Power spectral density
            freqs, psd = signal.welch(state_signal, fs=fs, nperseg=min(len(state_signal)//4, 256))

            # Frequency band analysis
            band_analysis = self._analyze_frequency_bands(freqs, psd)

            # Spectral anomaly detection
            spectral_anomalies = self._detect_spectral_anomalies(freqs, psd)

            # Harmonic analysis
            harmonic_analysis = self._analyze_harmonics(state_signal, fs)

            results[f'state_{i}'] = {
                'psd_analysis': {
                    'frequencies': freqs.tolist(),
                    'power_spectral_density': psd.tolist(),
                    'dominant_frequency': float(freqs[np.argmax(psd)]),
                    'total_power': float(np.trapz(psd, freqs))
                },
                'frequency_bands': band_analysis,
                'spectral_anomalies': spectral_anomalies,
                'harmonic_analysis': harmonic_analysis
            }

        return results

    def _perform_change_point_detection(self, data: DataProtocol) -> Dict[str, Any]:
        """Perform change point detection."""
        if not hasattr(data, 'states'):
            return {'error': 'No state data available'}

        states = data.states
        if states.ndim == 1:
            states = states.reshape(-1, 1)

        results = {}

        for i in range(states.shape[1]):
            state_var = states[:, i]

            # CUSUM-based change point detection
            cusum_change_points = self._cusum_change_point_detection(state_var)

            # Variance change detection
            variance_change_points = self._variance_change_detection(state_var)

            # Mean change detection
            mean_change_points = self._mean_change_detection(state_var)

            results[f'state_{i}'] = {
                'cusum_change_points': cusum_change_points,
                'variance_change_points': variance_change_points,
                'mean_change_points': mean_change_points
            }

        return results

    def _perform_fault_classification(self, detection_results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Classify detected faults."""
        fault_signatures = kwargs.get('fault_signatures', {})

        # Extract features from detection results
        features = self._extract_fault_features(detection_results)

        # Classify fault type
        if fault_signatures:
            classification = self._classify_with_signatures(features, fault_signatures)
        else:
            classification = self._classify_heuristic(features)

        return {
            'features': features,
            'classification': classification,
            'confidence': classification.get('confidence', 0.0)
        }

    def _assess_fault_severity(self, detection_results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess fault severity."""
        severity_indicators = {}

        # Residual-based severity
        if 'residual_detection' in detection_results:
            residual_data = detection_results['residual_detection']
            if 'max_residual' in residual_data and 'mean_residual' in residual_data:
                residual_severity = min(1.0, residual_data['max_residual'] / (residual_data['mean_residual'] + 1e-12))
                severity_indicators['residual_severity'] = float(residual_severity)

        # Statistical severity
        if 'statistical_detection' in detection_results:
            statistical_severity = self._compute_statistical_severity(detection_results['statistical_detection'])
            severity_indicators['statistical_severity'] = statistical_severity

        # Overall severity (weighted combination)
        weights = {'residual_severity': 0.4, 'statistical_severity': 0.3, 'spectral_severity': 0.3}
        overall_severity = 0.0
        total_weight = 0.0

        for indicator, value in severity_indicators.items():
            if indicator in weights:
                overall_severity += weights[indicator] * value
                total_weight += weights[indicator]

        if total_weight > 0:
            overall_severity /= total_weight

        return {
            'individual_severities': severity_indicators,
            'overall_severity': float(overall_severity),
            'severity_level': self._categorize_severity(overall_severity)
        }

    def _perform_fault_isolation(self, data: DataProtocol, detection_results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Perform fault isolation to identify fault location."""
        # Simplified fault isolation based on state variables
        if not hasattr(data, 'states'):
            return {'error': 'No state data for isolation'}

        states = data.states
        if states.ndim == 1:
            return {'isolated_components': ['single_state']}

        isolation_results = {}

        # Analyze which states show anomalous behavior
        anomalous_states = []

        for i in range(states.shape[1]):
            state_anomaly_score = self._compute_state_anomaly_score(states[:, i], detection_results)
            isolation_results[f'state_{i}_anomaly_score'] = float(state_anomaly_score)

            if state_anomaly_score > 0.5:  # Threshold for anomaly
                anomalous_states.append(i)

        # Map states to system components (would be system-specific)
        component_mapping = {
            0: 'cart_position',
            1: 'cart_velocity',
            2: 'pendulum_angle',
            3: 'pendulum_velocity'
        }

        isolated_components = [component_mapping.get(i, f'state_{i}') for i in anomalous_states]

        return {
            'state_anomaly_scores': {k: v for k, v in isolation_results.items() if 'anomaly_score' in k},
            'anomalous_states': anomalous_states,
            'isolated_components': isolated_components,
            'isolation_confidence': self._compute_isolation_confidence(isolation_results)
        }

    # Helper methods for specific detection algorithms

    def _apply_persistence_filter(self, violations: np.ndarray) -> np.ndarray:
        """Apply persistence filter to reduce false alarms."""
        detections = np.zeros_like(violations, dtype=bool)
        counter = 0

        for i, violation in enumerate(violations):
            if violation:
                counter += 1
            else:
                counter = 0

            if counter >= self.config.persistence_counter:
                detections[i] = True

        return detections

    def _test_normality(self, data: np.ndarray) -> Dict[str, float]:
        """Test for normality using Shapiro-Wilk test."""
        if len(data) < 3:
            return {'p_value': 1.0, 'is_normal': True, 'test_statistic': 0.0}

        try:
            # Use subset for large datasets (Shapiro-Wilk limitation)
            test_data = data[-min(5000, len(data)):]
            stat, p_value = stats.shapiro(test_data)
            return {
                'test_statistic': float(stat),
                'p_value': float(p_value),
                'is_normal': bool(p_value > 0.05)
            }
        except:
            return {'p_value': 1.0, 'is_normal': True, 'test_statistic': 0.0}

    def _test_stationarity(self, data: np.ndarray) -> Dict[str, Any]:
        """Test for stationarity using simple variance-based test."""
        if len(data) < 20:
            return {'is_stationary': True, 'p_value': 1.0}

        # Split data into chunks and compare variances
        chunk_size = len(data) // 4
        chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size) if len(data[i:i+chunk_size]) >= chunk_size]

        if len(chunks) < 2:
            return {'is_stationary': True, 'p_value': 1.0}

        variances = [np.var(chunk) for chunk in chunks]

        # Levene's test for equal variances
        try:
            stat, p_value = stats.levene(*chunks)
            return {
                'test_statistic': float(stat),
                'p_value': float(p_value),
                'is_stationary': bool(p_value > 0.05),
                'chunk_variances': variances
            }
        except:
            return {'is_stationary': True, 'p_value': 1.0}

    def _detect_outliers(self, data: np.ndarray) -> Dict[str, Any]:
        """Detect outliers using statistical methods."""
        if len(data) < 5:
            return {'outlier_indices': [], 'outlier_count': 0}

        # IQR method
        q1, q3 = np.percentile(data, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outlier_mask = (data < lower_bound) | (data > upper_bound)
        outlier_indices = np.where(outlier_mask)[0].tolist()

        # Z-score method
        z_scores = np.abs(stats.zscore(data))
        z_outliers = np.where(z_scores > 3)[0].tolist()

        return {
            'iqr_outliers': outlier_indices,
            'z_score_outliers': z_outliers,
            'outlier_count': len(outlier_indices),
            'outlier_percentage': len(outlier_indices) / len(data) * 100
        }

    def _detect_change_points_statistical(self, data: np.ndarray) -> List[int]:
        """Detect change points using statistical methods."""
        if len(data) < 10:
            return []

        change_points = []
        window_size = max(10, len(data) // 10)

        for i in range(window_size, len(data) - window_size):
            before = data[i-window_size:i]
            after = data[i:i+window_size]

            # T-test for difference in means
            try:
                _, p_value = stats.ttest_ind(before, after)
                if p_value < self.config.change_point_sensitivity:
                    change_points.append(i)
            except:
                continue

        return change_points

    def _analyze_frequency_bands(self, freqs: np.ndarray, psd: np.ndarray) -> Dict[str, float]:
        """Analyze power in different frequency bands."""
        band_powers = {}

        for i, (low_freq, high_freq) in enumerate(self.config.frequency_bands):
            band_mask = (freqs >= low_freq) & (freqs <= high_freq)
            if np.any(band_mask):
                band_power = np.trapz(psd[band_mask], freqs[band_mask])
            else:
                band_power = 0.0

            band_powers[f'band_{i}_power'] = float(band_power)
            band_powers[f'band_{i}_range'] = f'{low_freq}-{high_freq} Hz'

        return band_powers

    def _detect_spectral_anomalies(self, freqs: np.ndarray, psd: np.ndarray) -> Dict[str, Any]:
        """Detect spectral anomalies."""
        # Find peaks in power spectral density
        peaks, properties = signal.find_peaks(psd, height=np.mean(psd) + 2*np.std(psd))

        anomalies = {
            'peak_frequencies': freqs[peaks].tolist(),
            'peak_powers': psd[peaks].tolist(),
            'num_significant_peaks': len(peaks),
            'dominant_peak_frequency': float(freqs[np.argmax(psd)]),
            'spectral_centroid': float(np.sum(freqs * psd) / np.sum(psd))
        }

        return anomalies

    def _analyze_harmonics(self, signal_data: np.ndarray, fs: float) -> Dict[str, Any]:
        """Analyze harmonic content of signal."""
        # Simple harmonic analysis using FFT
        fft = np.fft.fft(signal_data)
        freqs = np.fft.fftfreq(len(signal_data), 1/fs)

        # Keep only positive frequencies
        positive_freq_mask = freqs > 0
        freqs = freqs[positive_freq_mask]
        fft_magnitude = np.abs(fft[positive_freq_mask])

        # Find fundamental frequency (largest peak)
        fundamental_idx = np.argmax(fft_magnitude)
        fundamental_freq = freqs[fundamental_idx]

        # Look for harmonics
        harmonics = []
        for n in range(2, 6):  # Check up to 5th harmonic
            harmonic_freq = n * fundamental_freq
            # Find closest frequency bin
            closest_idx = np.argmin(np.abs(freqs - harmonic_freq))
            if np.abs(freqs[closest_idx] - harmonic_freq) < fs / len(signal_data):  # Within one bin
                harmonics.append({
                    'order': n,
                    'frequency': float(freqs[closest_idx]),
                    'magnitude': float(fft_magnitude[closest_idx])
                })

        return {
            'fundamental_frequency': float(fundamental_freq),
            'fundamental_magnitude': float(fft_magnitude[fundamental_idx]),
            'harmonics': harmonics,
            'total_harmonic_distortion': self._compute_thd(fft_magnitude[fundamental_idx], harmonics)
        }

    def _compute_thd(self, fundamental_magnitude: float, harmonics: List[Dict[str, Any]]) -> float:
        """Compute total harmonic distortion."""
        if not harmonics:
            return 0.0

        harmonic_power = sum(h['magnitude']**2 for h in harmonics)
        fundamental_power = fundamental_magnitude**2

        if fundamental_power == 0:
            return 0.0

        thd = np.sqrt(harmonic_power / fundamental_power)
        return float(thd)

    def _cusum_change_point_detection(self, data: np.ndarray) -> List[int]:
        """CUSUM-based change point detection."""
        if len(data) < 10:
            return []

        # Simple CUSUM implementation
        mean_estimate = np.mean(data[:len(data)//2])  # Use first half as reference
        cusum_pos = np.zeros(len(data))
        cusum_neg = np.zeros(len(data))

        threshold = 3 * np.std(data)
        change_points = []

        for i in range(1, len(data)):
            cusum_pos[i] = max(0, cusum_pos[i-1] + (data[i] - mean_estimate - 0.5))
            cusum_neg[i] = max(0, cusum_neg[i-1] - (data[i] - mean_estimate + 0.5))

            if cusum_pos[i] > threshold or cusum_neg[i] > threshold:
                change_points.append(i)
                # Reset CUSUM after detection
                cusum_pos[i] = 0
                cusum_neg[i] = 0

        return change_points

    def _variance_change_detection(self, data: np.ndarray) -> List[int]:
        """Detect changes in variance."""
        if len(data) < 20:
            return []

        window_size = max(10, len(data) // 20)
        change_points = []

        for i in range(window_size, len(data) - window_size):
            before_var = np.var(data[i-window_size:i])
            after_var = np.var(data[i:i+window_size])

            # F-test for variance equality
            if before_var > 0 and after_var > 0:
                f_stat = max(before_var, after_var) / min(before_var, after_var)
                # Simplified threshold (would use proper F-distribution in practice)
                if f_stat > 2.0:
                    change_points.append(i)

        return change_points

    def _mean_change_detection(self, data: np.ndarray) -> List[int]:
        """Detect changes in mean."""
        return self._detect_change_points_statistical(data)  # Reuse existing implementation

    def _extract_fault_features(self, detection_results: Dict[str, Any]) -> Dict[str, float]:
        """Extract features for fault classification."""
        features = {}

        # Residual-based features
        if 'residual_detection' in detection_results:
            residual_data = detection_results['residual_detection']
            features['residual_mean'] = residual_data.get('mean_residual', 0.0)
            features['residual_max'] = residual_data.get('max_residual', 0.0)
            features['residual_std'] = np.std(residual_data.get('residuals', [0.0]))

        # Statistical features
        if 'statistical_detection' in detection_results:
            # Count outliers across all states
            outlier_count = 0
            for state_key, state_data in detection_results['statistical_detection'].items():
                if isinstance(state_data, dict) and 'outlier_detection' in state_data:
                    outlier_count += state_data['outlier_detection'].get('outlier_count', 0)
            features['outlier_count'] = float(outlier_count)

        # Spectral features
        if 'signal_detection' in detection_results:
            total_spectral_energy = 0.0
            for state_key, state_data in detection_results['signal_detection'].items():
                if isinstance(state_data, dict) and 'psd_analysis' in state_data:
                    total_spectral_energy += state_data['psd_analysis'].get('total_power', 0.0)
            features['spectral_energy'] = float(total_spectral_energy)

        return features

    def _classify_with_signatures(self, features: Dict[str, float], fault_signatures: Dict[str, FaultSignature]) -> Dict[str, Any]:
        """Classify fault using known signatures."""
        best_match = None
        best_similarity = 0.0

        for signature_name, signature in fault_signatures.items():
            similarity = self._compute_signature_similarity(features, signature.features)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = signature

        if best_match and best_similarity > 0.5:  # Minimum similarity threshold
            return {
                'fault_type': best_match.fault_type.value,
                'detection_method': best_match.detection_method.value,
                'confidence': float(best_similarity),
                'description': best_match.description
            }
        else:
            return {
                'fault_type': FaultType.UNKNOWN_FAULT.value,
                'confidence': 0.0,
                'description': 'No matching fault signature found'
            }

    def _classify_heuristic(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Heuristic fault classification based on features."""
        # Simple heuristic rules
        if features.get('outlier_count', 0) > 10:
            return {
                'fault_type': FaultType.SENSOR_FAULT.value,
                'confidence': 0.7,
                'description': 'High outlier count suggests sensor fault'
            }
        elif features.get('residual_max', 0) > features.get('residual_mean', 0) * 5:
            return {
                'fault_type': FaultType.ACTUATOR_FAULT.value,
                'confidence': 0.6,
                'description': 'Large residual spikes suggest actuator fault'
            }
        else:
            return {
                'fault_type': FaultType.PROCESS_FAULT.value,
                'confidence': 0.5,
                'description': 'General process deviation detected'
            }

    def _compute_signature_similarity(self, features1: Dict[str, float], features2: Dict[str, float]) -> float:
        """Compute similarity between feature sets."""
        common_features = set(features1.keys()) & set(features2.keys())
        if not common_features:
            return 0.0

        differences = []
        for feature in common_features:
            val1 = features1[feature]
            val2 = features2[feature]
            if val1 != 0 or val2 != 0:
                diff = abs(val1 - val2) / (max(abs(val1), abs(val2)) + 1e-12)
            else:
                diff = 0.0
            differences.append(diff)

        similarity = 1.0 - np.mean(differences)
        return max(0.0, similarity)

    def _compute_statistical_severity(self, statistical_results: Dict[str, Any]) -> float:
        """Compute severity based on statistical anomalies."""
        severity_score = 0.0
        total_indicators = 0

        for state_key, state_data in statistical_results.items():
            if isinstance(state_data, dict):
                # Non-normality contributes to severity
                if 'normality_test' in state_data and not state_data['normality_test'].get('is_normal', True):
                    severity_score += 0.3
                    total_indicators += 1

                # Non-stationarity contributes to severity
                if 'stationarity_test' in state_data and not state_data['stationarity_test'].get('is_stationary', True):
                    severity_score += 0.4
                    total_indicators += 1

                # Outliers contribute to severity
                if 'outlier_detection' in state_data:
                    outlier_percentage = state_data['outlier_detection'].get('outlier_percentage', 0)
                    severity_score += min(0.5, outlier_percentage / 100.0)
                    total_indicators += 1

        if total_indicators > 0:
            return severity_score / total_indicators
        else:
            return 0.0

    def _categorize_severity(self, severity_score: float) -> str:
        """Categorize severity score into levels."""
        if severity_score < 0.2:
            return "low"
        elif severity_score < 0.5:
            return "medium"
        elif severity_score < 0.8:
            return "high"
        else:
            return "critical"

    def _compute_state_anomaly_score(self, state_data: np.ndarray, detection_results: Dict[str, Any]) -> float:
        """Compute anomaly score for a specific state."""
        # Simplified anomaly scoring
        anomaly_score = 0.0

        # Statistical anomalies
        z_scores = np.abs(stats.zscore(state_data))
        high_z_score_ratio = np.sum(z_scores > 2) / len(z_scores)
        anomaly_score += high_z_score_ratio * 0.5

        # Variance contribution
        if len(state_data) > 1:
            normalized_variance = np.var(state_data) / (np.mean(np.abs(state_data)) + 1e-12)
            anomaly_score += min(0.5, normalized_variance / 10.0)

        return min(1.0, anomaly_score)

    def _compute_isolation_confidence(self, isolation_results: Dict[str, float]) -> float:
        """Compute confidence in fault isolation."""
        anomaly_scores = [v for k, v in isolation_results.items() if 'anomaly_score' in k]

        if not anomaly_scores:
            return 0.0

        # Confidence is higher when there's a clear distinction between anomalous and normal states
        max_score = max(anomaly_scores)
        min_score = min(anomaly_scores)
        score_range = max_score - min_score

        # High confidence when there's a large gap between highest and lowest scores
        confidence = min(1.0, score_range * 2.0)
        return confidence

    def _determine_overall_status(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Determine overall fault detection status."""
        fault_detected = False
        detection_methods = []
        confidence_scores = []

        # Check residual detection
        if 'residual_detection' in results:
            if results['residual_detection'].get('fault_detected', False):
                fault_detected = True
                detection_methods.append('residual_based')

        # Check statistical detection
        if 'statistical_detection' in results:
            statistical_faults = any(
                not state_data.get('normality_test', {}).get('is_normal', True) or
                not state_data.get('stationarity_test', {}).get('is_stationary', True)
                for key, state_data in results['statistical_detection'].items()
                if isinstance(state_data, dict)
            )
            if statistical_faults:
                fault_detected = True
                detection_methods.append('statistical')

        # Overall confidence
        if 'fault_classification' in results:
            classification_confidence = results['fault_classification'].get('confidence', 0.0)
            confidence_scores.append(classification_confidence)

        overall_confidence = np.mean(confidence_scores) if confidence_scores else 0.5

        return {
            'fault_detected': fault_detected,
            'detection_methods': detection_methods,
            'overall_confidence': float(overall_confidence),
            'status': 'FAULT' if fault_detected else 'OK'
        }

    def _generate_diagnostic_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate diagnostic summary."""
        summary = {
            'detection_timestamp': datetime.now().isoformat(),
            'fault_status': results.get('overall_status', {}).get('status', 'OK'),
            'primary_indicators': [],
            'recommendations': []
        }

        # Identify primary fault indicators
        if results.get('overall_status', {}).get('fault_detected', False):
            detection_methods = results['overall_status'].get('detection_methods', [])

            if 'residual_based' in detection_methods:
                summary['primary_indicators'].append('Model-data mismatch detected')

            if 'statistical' in detection_methods:
                summary['primary_indicators'].append('Statistical anomalies detected')

        # Generate recommendations
        if summary['fault_status'] == 'FAULT':
            summary['recommendations'] = [
                'Investigate identified fault sources',
                'Check sensor and actuator health',
                'Review recent system changes',
                'Consider implementing corrective actions'
            ]

            # Add severity-specific recommendations
            if 'severity_assessment' in results:
                severity_level = results['severity_assessment'].get('severity_level', 'low')
                if severity_level in ['high', 'critical']:
                    summary['recommendations'].insert(0, 'URGENT: System requires immediate attention')

        return summary


def create_enhanced_fault_detector(config: Optional[Dict[str, Any]] = None) -> EnhancedFaultDetector:
    """Factory function to create enhanced fault detector.

    Parameters
    ----------
    config : Dict[str, Any], optional
        Configuration parameters

    Returns
    -------
    EnhancedFaultDetector
        Configured enhanced fault detector
    """
    if config is not None:
        detection_config = FaultDetectionConfig(**config)
    else:
        detection_config = FaultDetectionConfig()

    return EnhancedFaultDetector(detection_config)


# Legacy compatibility: Import the original FDIsystem class
from typing import Protocol as TypingProtocol
import logging


class DynamicsProtocol(TypingProtocol):
    """Protocol defining the expected interface for dynamics models."""
    def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        """Advance the system dynamics by one timestep."""
        ...


@dataclass
class FDIsystem:
    """
    Legacy fault detection and isolation system for backward compatibility.

    This is the original FDI system that provides basic fault detection
    capabilities. For new applications, consider using EnhancedFaultDetector
    which provides more advanced features and better integration with the
    analysis framework.
    """

    residual_threshold: float = 0.5
    persistence_counter: int = 10
    use_ekf_residual: bool = False
    residual_states: List[int] = field(default_factory=lambda: [0, 1, 2])
    residual_weights: Optional[List[float]] = None
    adaptive: bool = False
    window_size: int = 50
    threshold_factor: float = 3.0
    cusum_enabled: bool = False
    cusum_threshold: float = 5.0

    # Internal state
    _counter: int = field(default=0, repr=False, init=False)
    _last_state: Optional[np.ndarray] = field(default=None, repr=False, init=False)
    tripped_at: Optional[float] = field(default=None, repr=False, init=False)
    # For adaptive thresholding and CUSUM
    _residual_window: List[float] = field(default_factory=list, repr=False, init=False)
    _cusum: float = field(default=0.0, repr=False, init=False)

    # History for plotting/analysis
    times: List[float] = field(default_factory=list, repr=False, init=False)
    residuals: List[float] = field(default_factory=list, repr=False, init=False)

    def check(
        self,
        t: float,
        meas: np.ndarray,
        u: float,
        dt: float,
        dynamics_model: DynamicsProtocol,
    ) -> Tuple[str, float]:
        """
        Check for a fault at the current time step.

        Args:
            t: Current simulation time
            meas: Current state measurement
            u: Control input applied
            dt: Time step
            dynamics_model: Model with step(state, u, dt) method for prediction

        Returns:
            Tuple of (status, residual_norm) where status is "OK" or "FAULT"
        """
        if dt <= 0.0:
            raise ValueError("dt must be positive for FDI residual computation.")

        if self.tripped_at is not None:
            return "FAULT", np.inf

        if self._last_state is None:
            self._last_state = meas.copy()
            return "OK", 0.0

        # One-step prediction using the dynamics model
        try:
            predicted_state = dynamics_model.step(self._last_state, u, dt)

            # Check for numerical issues in prediction
            if not np.all(np.isfinite(predicted_state)):
                logging.warning(
                    f"FDI check at t={t:.2f}s: dynamics model returned non-finite values "
                    f"(nan or inf). Skipping residual computation."
                )
                return "OK", 0.0

        except Exception as e:
            # If model fails, cannot compute residual; assume OK for now but log it
            logging.warning(
                f"FDI check at t={t:.2f}s failed: dynamics model step raised "
                f"{type(e).__name__}: {str(e)}. Skipping residual computation."
            )
            return "OK", 0.0

        # Residual is the difference between prediction and measurement
        residual = meas - predicted_state

        # Compute weighted norm using specified indices and optional weights
        try:
            sub = residual[self.residual_states]
            weights = self.residual_weights
            if weights is not None:
                sub = sub * np.asarray(weights, dtype=float)
            residual_norm = float(np.linalg.norm(sub))
        except Exception:
            logging.error(
                f"FDI configuration error: residual_states {self.residual_states} or weights invalid "
                f"for state vector of size {len(residual)}"
            )
            residual_norm = float(np.linalg.norm(residual))

        # Store history for analysis
        self.times.append(t)
        self.residuals.append(residual_norm)

        # Append to residual window for adaptive thresholding
        self._residual_window.append(residual_norm)
        if len(self._residual_window) > self.window_size:
            self._residual_window.pop(0)

        # Compute adaptive threshold when enabled and enough samples collected
        dynamic_threshold = self.residual_threshold
        mu = None
        sigma = None
        if self.adaptive and len(self._residual_window) >= self.window_size:
            mu = float(np.mean(self._residual_window))
            sigma = float(np.std(self._residual_window))
            if sigma > 1e-12:
                dynamic_threshold = mu + self.threshold_factor * sigma
            else:
                dynamic_threshold = mu

        # CUSUM drift detection: update cumulative sum of deviations
        if self.cusum_enabled:
            ref = mu if (self.adaptive and mu is not None) else self.residual_threshold
            self._cusum = max(0.0, self._cusum + (residual_norm - ref))
            if self._cusum > self.cusum_threshold:
                self.tripped_at = t
                logging.info(
                    f"FDI CUSUM fault detected at t={t:.2f}s (cusum={self._cusum:.4f} > threshold={self.cusum_threshold})"
                )
                return "FAULT", residual_norm

        # Update persistence counter using dynamic threshold
        if residual_norm > dynamic_threshold:
            self._counter += 1
        else:
            self._counter = 0  # Reset on any good measurement

        # Check for fault condition based on persistence count
        if self._counter >= self.persistence_counter:
            self.tripped_at = t
            threshold_used = dynamic_threshold
            logging.info(
                f"FDI fault detected at t={t:.2f}s after {self._counter} consecutive "
                f"violations (residual_norm={residual_norm:.4f} > threshold={threshold_used:.4f})"
            )
            return "FAULT", residual_norm

        # Update state for next prediction
        self._last_state = meas.copy()
        return "OK", residual_norm


# Create alias for backward compatibility
FaultDetectionInterface = FDIsystem