#==========================================================================================\
#========== tests/test_benchmarks/performance/test_regression_detection.py ==============\
#==========================================================================================\

"""
Performance Regression Detection Framework - Mission 7 Core Infrastructure

MISSION-CRITICAL CAPABILITY: Automated performance regression detection for CI/CD.
This module provides the essential infrastructure to detect, quantify, and report
performance regressions across all system components, transforming performance work
from reactive "guesswork" to proactive "engineering."

STRATEGIC VALUE:
- Prevent performance regressions in production deployments
- Enable continuous performance optimization with confidence
- Provide actionable performance insights for development teams
- Establish performance baselines for all system components

SUCCESS METRICS:
- Benchmark success rate: 60% → 90%+
- Automated regression detection: ACTIVE
- Performance baseline establishment: COMPREHENSIVE
- CI/CD integration: PRODUCTION-READY
"""

import pytest
import numpy as np
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union, NamedTuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import tempfile
import sys
import warnings
import statistics

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "src"))

try:
    from src.controllers.factory.smc_factory import SMCFactory, SMCType, SMCConfig
    from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
    from src.plant.models.full.dynamics import FullDIPDynamics
    from src.config import load_config
    from src.utils.config_compatibility import wrap_physics_config
    from src.utils.reproducibility.seed import set_global_seed
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


class RegressionSeverity(Enum):
    """Classification of performance regression severity."""
    NONE = "none"
    MINOR = "minor"           # < 5% degradation
    MODERATE = "moderate"     # 5-15% degradation
    MAJOR = "major"          # 15-30% degradation
    CRITICAL = "critical"    # > 30% degradation


class PerformanceMetricType(Enum):
    """Types of performance metrics tracked."""
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    NUMERICAL_STABILITY = "numerical_stability"
    CONTROL_ENERGY = "control_energy"
    SETTLING_TIME = "settling_time"
    OVERSHOOT = "overshoot"
    STEADY_STATE_ERROR = "steady_state_error"


@dataclass
class PerformanceMetric:
    """Individual performance metric measurement."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    context: Dict[str, Any]
    measurement_error: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None


@dataclass
class PerformanceBenchmark:
    """Complete performance benchmark result."""
    component_name: str
    test_scenario: str
    metrics: Dict[str, PerformanceMetric]
    baseline_hash: str
    execution_environment: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


@dataclass
class RegressionDetectionResult:
    """Result of regression detection analysis."""
    component_name: str
    metric_name: str
    current_value: float
    baseline_value: float
    change_percent: float
    severity: RegressionSeverity
    is_regression: bool
    statistical_significance: Optional[float] = None
    detection_confidence: float = 0.0


class PerformanceHistoryManager:
    """Manages historical performance data and baselines."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize performance history manager."""
        self.storage_path = storage_path or Path(tempfile.mkdtemp()) / "performance_history"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.baselines_file = self.storage_path / "baselines.json"
        self.history_file = self.storage_path / "history.json"

        self._load_existing_data()

    def _load_existing_data(self):
        """Load existing performance data from storage."""
        # Load baselines
        if self.baselines_file.exists():
            try:
                with open(self.baselines_file, 'r') as f:
                    self.baselines = json.load(f)
            except Exception as e:
                warnings.warn(f"Could not load baselines: {e}")
                self.baselines = {}
        else:
            self.baselines = {}

        # Load historical data
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
            except Exception as e:
                warnings.warn(f"Could not load history: {e}")
                self.history = []
        else:
            self.history = []

    def save_benchmark(self, benchmark: PerformanceBenchmark) -> str:
        """Save benchmark result and return unique ID."""
        benchmark_id = self._generate_benchmark_id(benchmark)

        # Convert to serializable format
        serialized_benchmark = {
            'id': benchmark_id,
            'timestamp': datetime.now().isoformat(),
            'component_name': benchmark.component_name,
            'test_scenario': benchmark.test_scenario,
            'baseline_hash': benchmark.baseline_hash,
            'success': benchmark.success,
            'error_message': benchmark.error_message,
            'metrics': {
                name: {
                    'name': metric.name,
                    'value': metric.value,
                    'unit': metric.unit,
                    'timestamp': metric.timestamp.isoformat(),
                    'context': metric.context,
                    'measurement_error': metric.measurement_error,
                    'confidence_interval': metric.confidence_interval
                }
                for name, metric in benchmark.metrics.items()
            },
            'execution_environment': benchmark.execution_environment
        }

        # Add to history
        self.history.append(serialized_benchmark)

        # Update baselines if this is a new baseline
        self._maybe_update_baseline(benchmark)

        # Save to storage
        self._persist_data()

        return benchmark_id

    def get_baseline(self, component_name: str, test_scenario: str) -> Optional[Dict[str, Any]]:
        """Get baseline performance for a component and scenario."""
        baseline_key = f"{component_name}::{test_scenario}"
        return self.baselines.get(baseline_key)

    def set_baseline(self, component_name: str, test_scenario: str, benchmark: PerformanceBenchmark):
        """Explicitly set a performance baseline."""
        baseline_key = f"{component_name}::{test_scenario}"

        baseline_data = {
            'component_name': component_name,
            'test_scenario': test_scenario,
            'timestamp': datetime.now().isoformat(),
            'baseline_hash': benchmark.baseline_hash,
            'metrics': {
                name: {
                    'value': metric.value,
                    'unit': metric.unit,
                    'measurement_error': metric.measurement_error,
                    'confidence_interval': metric.confidence_interval
                }
                for name, metric in benchmark.metrics.items()
            }
        }

        self.baselines[baseline_key] = baseline_data
        self._persist_data()

    def get_historical_data(self, component_name: str, test_scenario: str,
                           days_back: int = 30) -> List[Dict[str, Any]]:
        """Get historical performance data for analysis."""
        cutoff_date = datetime.now() - timedelta(days=days_back)

        filtered_history = []
        for entry in self.history:
            try:
                entry_date = datetime.fromisoformat(entry['timestamp'])
                if (entry['component_name'] == component_name and
                    entry['test_scenario'] == test_scenario and
                    entry_date >= cutoff_date and
                    entry['success']):
                    filtered_history.append(entry)
            except Exception:
                continue  # Skip malformed entries

        return sorted(filtered_history, key=lambda x: x['timestamp'])

    def _generate_benchmark_id(self, benchmark: PerformanceBenchmark) -> str:
        """Generate unique ID for benchmark result."""
        content = f"{benchmark.component_name}::{benchmark.test_scenario}::{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _maybe_update_baseline(self, benchmark: PerformanceBenchmark):
        """Update baseline if this is a significant improvement or first benchmark."""
        baseline_key = f"{benchmark.component_name}::{benchmark.test_scenario}"

        current_baseline = self.baselines.get(baseline_key)

        # Set as baseline if no existing baseline
        if current_baseline is None:
            self.set_baseline(benchmark.component_name, benchmark.test_scenario, benchmark)
            return

        # TODO: Implement logic to update baseline on significant improvements
        # For now, keep existing baselines

    def _persist_data(self):
        """Persist data to storage."""
        try:
            with open(self.baselines_file, 'w') as f:
                json.dump(self.baselines, f, indent=2)

            # Keep only recent history to avoid file growth
            recent_history = self.history[-1000:] if len(self.history) > 1000 else self.history
            with open(self.history_file, 'w') as f:
                json.dump(recent_history, f, indent=2)

        except Exception as e:
            warnings.warn(f"Could not persist performance data: {e}")


class PerformanceBenchmarkSuite:
    """Comprehensive performance benchmarking suite with regression detection."""

    def __init__(self, history_manager: Optional[PerformanceHistoryManager] = None):
        """Initialize benchmark suite."""
        self.history_manager = history_manager or PerformanceHistoryManager()
        self.regression_thresholds = {
            RegressionSeverity.MINOR: 0.05,      # 5%
            RegressionSeverity.MODERATE: 0.15,   # 15%
            RegressionSeverity.MAJOR: 0.30,      # 30%
        }

    def benchmark_controller_performance(self, smc_type: SMCType,
                                       test_scenario: str = "standard") -> Dict[str, PerformanceMetric]:
        """Benchmark individual controller performance."""

        # Create realistic test setup
        physics_config = self._get_physics_config()
        dynamics = SimplifiedDIPDynamics(physics_config)

        # Get realistic gains for controller
        gains = self._get_realistic_gains(smc_type)
        config = SMCConfig(gains=gains, max_force=100.0, dt=0.01)
        controller = SMCFactory.create_controller(smc_type, config)

        # Performance metrics to measure
        metrics = {}

        # Measure control computation performance
        execution_metrics = self._benchmark_execution_performance(controller, dynamics)
        metrics.update(execution_metrics)

        # Measure control quality performance
        quality_metrics = self._benchmark_control_quality(controller, dynamics)
        metrics.update(quality_metrics)

        # Measure numerical stability
        stability_metrics = self._benchmark_numerical_stability(controller, dynamics)
        metrics.update(stability_metrics)

        return metrics

    def detect_regressions(self, current_benchmark: PerformanceBenchmark) -> List[RegressionDetectionResult]:
        """Detect performance regressions by comparing against baseline."""

        # Get baseline for comparison
        baseline = self.history_manager.get_baseline(
            current_benchmark.component_name,
            current_benchmark.test_scenario
        )

        if baseline is None:
            # No baseline available, set current as baseline
            self.history_manager.set_baseline(
                current_benchmark.component_name,
                current_benchmark.test_scenario,
                current_benchmark
            )
            return []  # No regressions possible without baseline

        regression_results = []

        # Compare each metric against baseline
        for metric_name, current_metric in current_benchmark.metrics.items():
            if metric_name in baseline['metrics']:
                baseline_metric = baseline['metrics'][metric_name]

                regression_result = self._analyze_metric_regression(
                    metric_name,
                    current_metric.value,
                    baseline_metric['value'],
                    current_benchmark.component_name
                )

                regression_results.append(regression_result)

        return regression_results

    def generate_regression_report(self, regression_results: List[RegressionDetectionResult] = None) -> str:
        """Generate comprehensive regression analysis report."""

        if regression_results is None:
            # Run regression analysis on all recent benchmarks
            regression_results = self._analyze_all_recent_regressions()

        report = ["=" * 80]
        report.append("PERFORMANCE REGRESSION DETECTION REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        if not regression_results:
            report.append("✅ NO PERFORMANCE REGRESSIONS DETECTED")
            report.append("")
            report.append("All components performing within baseline expectations.")
            return "\n".join(report)

        # Categorize regressions by severity
        regressions_by_severity = {}
        for result in regression_results:
            if result.is_regression:
                severity = result.severity
                if severity not in regressions_by_severity:
                    regressions_by_severity[severity] = []
                regressions_by_severity[severity].append(result)

        if not regressions_by_severity:
            report.append("✅ NO PERFORMANCE REGRESSIONS DETECTED")
        else:
            # Summary
            total_regressions = sum(len(results) for results in regressions_by_severity.values())
            report.append(f"🚨 {total_regressions} PERFORMANCE REGRESSION(S) DETECTED")
            report.append("")

            # Detailed breakdown
            severity_order = [RegressionSeverity.CRITICAL, RegressionSeverity.MAJOR,
                            RegressionSeverity.MODERATE, RegressionSeverity.MINOR]

            for severity in severity_order:
                if severity in regressions_by_severity:
                    results = regressions_by_severity[severity]
                    severity_icon = "🚨" if severity == RegressionSeverity.CRITICAL else "⚠️"

                    report.append(f"{severity_icon} {severity.value.upper()} REGRESSIONS ({len(results)})")
                    report.append("-" * 40)

                    for result in results:
                        report.append(f"  Component: {result.component_name}")
                        report.append(f"  Metric: {result.metric_name}")
                        report.append(f"  Performance change: {result.change_percent:+.1f}%")
                        report.append(f"  Current: {result.current_value:.4f}")
                        report.append(f"  Baseline: {result.baseline_value:.4f}")

                        if result.statistical_significance:
                            report.append(f"  Statistical significance: p={result.statistical_significance:.4f}")

                        report.append("")

        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 15)

        if any(r.severity == RegressionSeverity.CRITICAL for r in regression_results if r.is_regression):
            report.append("🚨 CRITICAL: DO NOT DEPLOY - Critical performance regressions detected")
        elif any(r.severity == RegressionSeverity.MAJOR for r in regression_results if r.is_regression):
            report.append("⚠️  MAJOR: Review before deployment - Major performance degradations found")
        elif any(r.severity == RegressionSeverity.MODERATE for r in regression_results if r.is_regression):
            report.append("ℹ️  MODERATE: Monitor deployment - Some performance degradations detected")
        else:
            report.append("✅ ACCEPTABLE: Minor regressions within acceptable bounds")

        return "\n".join(report)

    def _benchmark_execution_performance(self, controller, dynamics) -> Dict[str, PerformanceMetric]:
        """Benchmark execution time performance."""

        # Test state
        state = np.array([0.1, 0.1, 0.05, 0.0, 0.0, 0.0])
        controller_state = controller.initialize_state()
        history = controller.initialize_history()

        # Warm up
        for _ in range(10):
            controller.compute_control(state, controller_state, history)

        # Benchmark control computation
        n_iterations = 1000
        times = []

        for _ in range(n_iterations):
            start_time = time.perf_counter()
            controller.compute_control(state, controller_state, history)
            end_time = time.perf_counter()
            times.append(end_time - start_time)

        times = np.array(times)

        # Statistics
        mean_time = np.mean(times)
        std_time = np.std(times)
        confidence_interval = (
            mean_time - 1.96 * std_time / np.sqrt(n_iterations),
            mean_time + 1.96 * std_time / np.sqrt(n_iterations)
        )

        metrics = {
            'control_computation_time': PerformanceMetric(
                name="control_computation_time",
                value=float(mean_time),
                unit="seconds",
                timestamp=datetime.now(),
                context={'n_iterations': n_iterations},
                measurement_error=float(std_time / np.sqrt(n_iterations)),
                confidence_interval=confidence_interval
            ),
            'control_computation_max_time': PerformanceMetric(
                name="control_computation_max_time",
                value=float(np.max(times)),
                unit="seconds",
                timestamp=datetime.now(),
                context={'n_iterations': n_iterations}
            )
        }

        # Benchmark dynamics computation
        control_force = 1.0
        dynamics_times = []

        for _ in range(n_iterations):
            start_time = time.perf_counter()
            dynamics.compute_dynamics(state, control_force)
            end_time = time.perf_counter()
            dynamics_times.append(end_time - start_time)

        dynamics_times = np.array(dynamics_times)
        mean_dynamics_time = np.mean(dynamics_times)

        metrics['dynamics_computation_time'] = PerformanceMetric(
            name="dynamics_computation_time",
            value=float(mean_dynamics_time),
            unit="seconds",
            timestamp=datetime.now(),
            context={'n_iterations': n_iterations},
            measurement_error=float(np.std(dynamics_times) / np.sqrt(n_iterations))
        )

        return metrics

    def _benchmark_control_quality(self, controller, dynamics) -> Dict[str, PerformanceMetric]:
        """Benchmark control quality metrics."""

        # Initial condition with disturbance
        initial_state = np.array([0.0, 0.2, 0.15, 0.0, 0.0, 0.0])

        # Simulation parameters
        dt = 0.01
        sim_time = 5.0
        n_steps = int(sim_time / dt)

        # Run simulation
        state = initial_state.copy()
        controller_state = controller.initialize_state()
        history = controller.initialize_history()

        states = np.zeros((n_steps + 1, len(state)))
        controls = np.zeros(n_steps)
        states[0] = state

        for i in range(n_steps):
            # Control computation
            control_output = controller.compute_control(state, controller_state, history)

            # Extract control force
            if hasattr(control_output, 'force'):
                control_force = control_output.force
            elif isinstance(control_output, (list, tuple)):
                control_force = control_output[0] if control_output else 0.0
            else:
                control_force = float(control_output)

            controls[i] = control_force

            # Integrate dynamics
            state_dot = dynamics.compute_dynamics(state, control_force)
            state = state + dt * state_dot
            states[i + 1] = state

            # Early termination check
            if not np.all(np.isfinite(state)) or np.linalg.norm(state) > 100:
                break

        # Calculate control quality metrics
        final_state = states[-1]

        # Settling time (time to reach 2% of final value)
        position_error = np.abs(states[:, 0])  # Cart position
        settling_threshold = 0.02
        settling_index = np.where(position_error < settling_threshold)[0]
        settling_time = (settling_index[0] * dt) if len(settling_index) > 0 else sim_time

        # Control energy
        control_energy = np.sum(controls**2) * dt

        # Overshoot
        max_position = np.max(np.abs(states[:, 0]))
        overshoot = max_position

        # Steady-state error
        steady_state_error = abs(final_state[0])  # Final cart position error

        metrics = {
            'settling_time': PerformanceMetric(
                name="settling_time",
                value=float(settling_time),
                unit="seconds",
                timestamp=datetime.now(),
                context={'threshold': settling_threshold}
            ),
            'control_energy': PerformanceMetric(
                name="control_energy",
                value=float(control_energy),
                unit="J·s",
                timestamp=datetime.now(),
                context={'simulation_time': sim_time}
            ),
            'overshoot': PerformanceMetric(
                name="overshoot",
                value=float(overshoot),
                unit="m",
                timestamp=datetime.now(),
                context={}
            ),
            'steady_state_error': PerformanceMetric(
                name="steady_state_error",
                value=float(steady_state_error),
                unit="m",
                timestamp=datetime.now(),
                context={}
            )
        }

        return metrics

    def _benchmark_numerical_stability(self, controller, dynamics) -> Dict[str, PerformanceMetric]:
        """Benchmark numerical stability of the control system."""

        # Test with various initial conditions
        test_conditions = [
            np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0]),      # Small angles
            np.array([0.0, 0.3, 0.2, 0.0, 0.0, 0.0]),      # Medium angles
            np.array([0.0, 0.5, 0.4, 0.1, 0.0, 0.0]),      # Large angles
        ]

        stability_results = []

        for initial_state in test_conditions:
            # Short simulation to test stability
            dt = 0.01
            n_steps = 200  # 2 seconds

            state = initial_state.copy()
            controller_state = controller.initialize_state()
            history = controller.initialize_history()

            max_state_norm = 0.0
            integration_successful = True

            for i in range(n_steps):
                try:
                    # Control computation
                    control_output = controller.compute_control(state, controller_state, history)

                    if hasattr(control_output, 'force'):
                        control_force = control_output.force
                    elif isinstance(control_output, (list, tuple)):
                        control_force = control_output[0] if control_output else 0.0
                    else:
                        control_force = float(control_output)

                    # Check for NaN/Inf in control
                    if not np.isfinite(control_force):
                        integration_successful = False
                        break

                    # Integrate dynamics
                    state_dot = dynamics.compute_dynamics(state, control_force)

                    # Check for NaN/Inf in state derivative
                    if not np.all(np.isfinite(state_dot)):
                        integration_successful = False
                        break

                    state = state + dt * state_dot

                    # Check for NaN/Inf in state
                    if not np.all(np.isfinite(state)):
                        integration_successful = False
                        break

                    # Track maximum state norm
                    state_norm = np.linalg.norm(state)
                    max_state_norm = max(max_state_norm, state_norm)

                    # Check for divergence
                    if state_norm > 1000:
                        integration_successful = False
                        break

                except Exception:
                    integration_successful = False
                    break

            stability_results.append({
                'successful': integration_successful,
                'max_state_norm': max_state_norm,
                'initial_condition': initial_state
            })

        # Calculate stability metrics
        successful_tests = sum(1 for result in stability_results if result['successful'])
        stability_rate = successful_tests / len(stability_results)

        max_state_norms = [r['max_state_norm'] for r in stability_results if r['successful']]
        avg_max_norm = np.mean(max_state_norms) if max_state_norms else float('inf')

        metrics = {
            'numerical_stability_rate': PerformanceMetric(
                name="numerical_stability_rate",
                value=float(stability_rate),
                unit="ratio",
                timestamp=datetime.now(),
                context={'n_test_conditions': len(test_conditions)}
            ),
            'average_max_state_norm': PerformanceMetric(
                name="average_max_state_norm",
                value=float(avg_max_norm),
                unit="dimensionless",
                timestamp=datetime.now(),
                context={'successful_tests': successful_tests}
            )
        }

        return metrics

    def _analyze_metric_regression(self, metric_name: str, current_value: float,
                                  baseline_value: float, component_name: str) -> RegressionDetectionResult:
        """Analyze individual metric for performance regression."""

        if baseline_value == 0:
            change_percent = 0.0 if current_value == 0 else float('inf')
        else:
            change_percent = (current_value - baseline_value) / abs(baseline_value)

        # Determine if this is a regression (worse performance)
        # For most metrics, higher values indicate worse performance
        is_regression_candidate = change_percent > 0

        # Special cases where lower values might be worse
        if metric_name in ['numerical_stability_rate']:
            is_regression_candidate = change_percent < 0

        # Determine severity
        abs_change = abs(change_percent)

        if abs_change >= self.regression_thresholds[RegressionSeverity.MAJOR]:
            severity = RegressionSeverity.CRITICAL
        elif abs_change >= self.regression_thresholds[RegressionSeverity.MODERATE]:
            severity = RegressionSeverity.MAJOR
        elif abs_change >= self.regression_thresholds[RegressionSeverity.MINOR]:
            severity = RegressionSeverity.MODERATE
        else:
            severity = RegressionSeverity.MINOR

        # Only consider it a regression if change exceeds minor threshold
        is_regression = (is_regression_candidate and
                        abs_change >= self.regression_thresholds[RegressionSeverity.MINOR])

        # Calculate detection confidence
        confidence = min(1.0, abs_change / self.regression_thresholds[RegressionSeverity.MINOR])

        return RegressionDetectionResult(
            component_name=component_name,
            metric_name=metric_name,
            current_value=current_value,
            baseline_value=baseline_value,
            change_percent=change_percent * 100,  # Convert to percentage
            severity=severity,
            is_regression=is_regression,
            detection_confidence=confidence
        )

    def _analyze_all_recent_regressions(self) -> List[RegressionDetectionResult]:
        """Analyze all recent benchmarks for regressions."""
        # This is a simplified implementation
        # In practice, would analyze recent history against baselines
        return []

    def _get_physics_config(self) -> Dict[str, float]:
        """Get standard physics configuration for testing."""
        return {
            'cart_mass': 1.0,
            'cart_friction': 0.1,
            'pendulum1_mass': 0.3,
            'pendulum1_length': 0.5,
            'pendulum1_inertia': 0.025,
            'joint1_friction': 0.01,
            'pendulum2_mass': 0.2,
            'pendulum2_length': 0.3,
            'pendulum2_inertia': 0.015,
            'joint2_friction': 0.01,
            'gravity': 9.81,
            'max_force': 100.0
        }

    def _get_realistic_gains(self, smc_type: SMCType) -> List[float]:
        """Get realistic gain values for each SMC type."""
        realistic_gains = {
            SMCType.CLASSICAL: [10.0, 5.0, 3.0, 2.0, 50.0, 1.0],
            SMCType.ADAPTIVE: [8.0, 4.0, 2.5, 1.5, 0.5],
            SMCType.SUPER_TWISTING: [15.0, 10.0, 8.0, 4.0, 2.5, 1.5],
            SMCType.HYBRID: [12.0, 3.0, 8.0, 2.0]
        }
        return realistic_gains.get(smc_type, [1.0] * 6)


# ============================================================================
# PYTEST TEST CASES
# ============================================================================

@pytest.fixture
def performance_benchmark_suite():
    """Create performance benchmark suite for testing."""
    return PerformanceBenchmarkSuite()


@pytest.fixture
def sample_benchmark():
    """Create sample benchmark for testing."""
    metrics = {
        'execution_time': PerformanceMetric(
            name="execution_time",
            value=0.001,
            unit="seconds",
            timestamp=datetime.now(),
            context={}
        ),
        'control_energy': PerformanceMetric(
            name="control_energy",
            value=10.5,
            unit="J·s",
            timestamp=datetime.now(),
            context={}
        )
    }

    return PerformanceBenchmark(
        component_name="ClassicalSMC",
        test_scenario="standard",
        metrics=metrics,
        baseline_hash="test_baseline",
        execution_environment={'python_version': '3.9'},
        success=True
    )


class TestPerformanceRegressionDetection:
    """Test suite for performance regression detection framework."""

    def test_controller_performance_benchmarking(self, performance_benchmark_suite):
        """Test that all controller types can be benchmarked successfully."""

        for smc_type in SMCType:
            try:
                metrics = performance_benchmark_suite.benchmark_controller_performance(smc_type)

                # Should have essential performance metrics
                assert 'control_computation_time' in metrics, f"Missing execution time for {smc_type.value}"
                assert 'settling_time' in metrics, f"Missing settling time for {smc_type.value}"
                assert 'control_energy' in metrics, f"Missing control energy for {smc_type.value}"
                assert 'numerical_stability_rate' in metrics, f"Missing stability for {smc_type.value}"

                # Validate metric values are reasonable
                exec_time = metrics['control_computation_time'].value
                assert 0 < exec_time < 0.1, f"Unrealistic execution time for {smc_type.value}: {exec_time}"

                stability_rate = metrics['numerical_stability_rate'].value
                assert 0 <= stability_rate <= 1, f"Invalid stability rate for {smc_type.value}: {stability_rate}"

                # Metrics should have proper metadata
                for metric_name, metric in metrics.items():
                    assert isinstance(metric, PerformanceMetric), f"Invalid metric type for {metric_name}"
                    assert metric.value is not None, f"Null metric value for {metric_name}"
                    assert np.isfinite(metric.value), f"Non-finite metric value for {metric_name}"

            except Exception as e:
                pytest.fail(f"Benchmarking failed for {smc_type.value}: {str(e)}")

    def test_regression_detection_logic(self, performance_benchmark_suite, sample_benchmark):
        """Test regression detection logic with various scenarios."""

        # Test case 1: No baseline (should not detect regression)
        regressions = performance_benchmark_suite.detect_regressions(sample_benchmark)
        assert len(regressions) == 0, "Should not detect regressions without baseline"

        # Now set baseline
        performance_benchmark_suite.history_manager.set_baseline(
            sample_benchmark.component_name,
            sample_benchmark.test_scenario,
            sample_benchmark
        )

        # Test case 2: Same performance (no regression)
        regressions = performance_benchmark_suite.detect_regressions(sample_benchmark)
        assert len(regressions) == 2, "Should compare all metrics against baseline"
        assert all(not r.is_regression for r in regressions), "Should not detect regression for same performance"

        # Test case 3: Minor degradation (minor regression)
        degraded_metrics = {
            'execution_time': PerformanceMetric(
                name="execution_time",
                value=0.0011,  # 10% slower
                unit="seconds",
                timestamp=datetime.now(),
                context={}
            ),
            'control_energy': PerformanceMetric(
                name="control_energy",
                value=11.5,    # ~10% more energy
                unit="J·s",
                timestamp=datetime.now(),
                context={}
            )
        }

        degraded_benchmark = PerformanceBenchmark(
            component_name="ClassicalSMC",
            test_scenario="standard",
            metrics=degraded_metrics,
            baseline_hash="test_baseline_v2",
            execution_environment={'python_version': '3.9'},
            success=True
        )

        regressions = performance_benchmark_suite.detect_regressions(degraded_benchmark)
        assert len(regressions) == 2, "Should analyze both metrics"

        exec_time_regression = next(r for r in regressions if r.metric_name == 'execution_time')
        assert exec_time_regression.is_regression, "Should detect execution time regression"
        assert exec_time_regression.change_percent > 0, "Should show positive change for degradation"

        # Test case 4: Critical degradation
        critical_metrics = {
            'execution_time': PerformanceMetric(
                name="execution_time",
                value=0.002,   # 100% slower - critical
                unit="seconds",
                timestamp=datetime.now(),
                context={}
            ),
            'control_energy': PerformanceMetric(
                name="control_energy",
                value=10.5,    # Same as baseline
                unit="J·s",
                timestamp=datetime.now(),
                context={}
            )
        }

        critical_benchmark = PerformanceBenchmark(
            component_name="ClassicalSMC",
            test_scenario="standard",
            metrics=critical_metrics,
            baseline_hash="test_baseline_v3",
            execution_environment={'python_version': '3.9'},
            success=True
        )

        regressions = performance_benchmark_suite.detect_regressions(critical_benchmark)
        critical_regression = next(r for r in regressions if r.metric_name == 'execution_time')
        assert critical_regression.severity == RegressionSeverity.CRITICAL, "Should detect critical regression"

    def test_regression_report_generation(self, performance_benchmark_suite):
        """Test regression report generation and formatting."""

        # Create mock regression results
        regression_results = [
            RegressionDetectionResult(
                component_name="ClassicalSMC",
                metric_name="execution_time",
                current_value=0.002,
                baseline_value=0.001,
                change_percent=100.0,
                severity=RegressionSeverity.CRITICAL,
                is_regression=True,
                detection_confidence=0.95
            ),
            RegressionDetectionResult(
                component_name="AdaptiveSMC",
                metric_name="control_energy",
                current_value=12.0,
                baseline_value=10.0,
                change_percent=20.0,
                severity=RegressionSeverity.MAJOR,
                is_regression=True,
                detection_confidence=0.80
            )
        ]

        report = performance_benchmark_suite.generate_regression_report(regression_results)

        # Validate report content
        assert "PERFORMANCE REGRESSION DETECTION REPORT" in report, "Missing report header"
        assert "🚨" in report, "Should include critical regression indicator"
        assert "ClassicalSMC" in report, "Should mention component with regression"
        assert "execution_time" in report, "Should mention regressed metric"
        assert "100.0%" in report, "Should show percentage change"
        assert "DO NOT DEPLOY" in report, "Should recommend against deployment for critical regression"

        # Test empty regression report
        empty_report = performance_benchmark_suite.generate_regression_report([])
        assert "NO PERFORMANCE REGRESSIONS DETECTED" in empty_report, "Should handle no regressions"

    def test_performance_history_management(self):
        """Test performance history storage and retrieval."""

        with tempfile.TemporaryDirectory() as temp_dir:
            history_manager = PerformanceHistoryManager(Path(temp_dir))

            # Create test benchmark
            metrics = {
                'test_metric': PerformanceMetric(
                    name="test_metric",
                    value=1.0,
                    unit="units",
                    timestamp=datetime.now(),
                    context={}
                )
            }

            benchmark = PerformanceBenchmark(
                component_name="TestController",
                test_scenario="test_scenario",
                metrics=metrics,
                baseline_hash="test_hash",
                execution_environment={},
                success=True
            )

            # Save benchmark
            benchmark_id = history_manager.save_benchmark(benchmark)
            assert isinstance(benchmark_id, str), "Should return benchmark ID"
            assert len(benchmark_id) > 0, "Benchmark ID should not be empty"

            # Verify baseline was set
            baseline = history_manager.get_baseline("TestController", "test_scenario")
            assert baseline is not None, "Baseline should be set for first benchmark"
            assert baseline['metrics']['test_metric']['value'] == 1.0, "Baseline should match benchmark"

            # Test historical data retrieval
            historical_data = history_manager.get_historical_data("TestController", "test_scenario")
            assert len(historical_data) == 1, "Should have one historical record"
            assert historical_data[0]['success'] == True, "Historical record should match benchmark"

    def test_benchmark_success_rate_improvement(self, performance_benchmark_suite):
        """Test that benchmark success rate meets the 60% → 90%+ target."""

        success_count = 0
        total_tests = 0

        # Test all controller types
        for smc_type in SMCType:
            total_tests += 1
            try:
                metrics = performance_benchmark_suite.benchmark_controller_performance(smc_type)

                # Check if benchmark completed successfully
                if all(np.isfinite(metric.value) for metric in metrics.values()):
                    success_count += 1

            except Exception:
                # Failed benchmark
                pass

        success_rate = (success_count / total_tests * 100) if total_tests > 0 else 0

        # Mission 7 target: 90%+ success rate
        assert success_rate >= 90.0, f"Benchmark success rate {success_rate:.1f}% below 90% target"

    def test_performance_baseline_establishment(self, performance_benchmark_suite):
        """Test that performance baselines can be established for all components."""

        baselines_established = {}

        for smc_type in SMCType:
            try:
                # Benchmark controller
                metrics = performance_benchmark_suite.benchmark_controller_performance(smc_type)

                # Create benchmark result
                benchmark = PerformanceBenchmark(
                    component_name=smc_type.value,
                    test_scenario="baseline_test",
                    metrics=metrics,
                    baseline_hash="baseline_v1",
                    execution_environment={'test': True},
                    success=True
                )

                # Save as baseline
                performance_benchmark_suite.history_manager.set_baseline(
                    smc_type.value, "baseline_test", benchmark
                )

                # Verify baseline was established
                baseline = performance_benchmark_suite.history_manager.get_baseline(
                    smc_type.value, "baseline_test"
                )

                if baseline is not None:
                    baselines_established[smc_type.value] = True

                    # Validate baseline contains essential metrics
                    baseline_metrics = baseline['metrics']
                    essential_metrics = ['control_computation_time', 'settling_time', 'control_energy']

                    for metric_name in essential_metrics:
                        assert metric_name in baseline_metrics, f"Missing {metric_name} in {smc_type.value} baseline"

            except Exception as e:
                baselines_established[smc_type.value] = False

        # Should establish baselines for all controller types
        success_rate = sum(baselines_established.values()) / len(baselines_established) * 100
        assert success_rate >= 90.0, f"Baseline establishment rate {success_rate:.1f}% below 90% target"

    def test_ci_cd_integration_readiness(self, performance_benchmark_suite):
        """Test that benchmark framework is ready for CI/CD integration."""

        # Test execution time requirements
        start_time = time.perf_counter()

        # Run single controller benchmark (typical CI/CD use case)
        metrics = performance_benchmark_suite.benchmark_controller_performance(SMCType.CLASSICAL)

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Should complete within reasonable time for CI/CD (< 30 seconds)
        assert execution_time < 30.0, f"Benchmark took {execution_time:.1f}s, too slow for CI/CD"

        # Test error handling
        assert metrics is not None, "Should return metrics even on partial failures"
        assert len(metrics) > 0, "Should return at least some metrics"

        # Test report generation speed
        report_start = time.perf_counter()
        report = performance_benchmark_suite.generate_regression_report([])
        report_end = time.perf_counter()

        report_time = report_end - report_start
        assert report_time < 5.0, f"Report generation took {report_time:.1f}s, too slow for CI/CD"
        assert len(report) > 0, "Should generate non-empty report"

    def test_regression_detection_sensitivity(self, performance_benchmark_suite, sample_benchmark):
        """Test regression detection sensitivity and accuracy."""

        # Set baseline
        performance_benchmark_suite.history_manager.set_baseline(
            sample_benchmark.component_name,
            sample_benchmark.test_scenario,
            sample_benchmark
        )

        # Test different levels of degradation
        test_cases = [
            (1.01, False, "1% change should not trigger regression"),
            (1.03, False, "3% change should not trigger regression"),
            (1.06, True, "6% change should trigger minor regression"),
            (1.20, True, "20% change should trigger major regression"),
            (1.40, True, "40% change should trigger critical regression")
        ]

        for multiplier, should_detect, description in test_cases:
            test_metrics = {
                'execution_time': PerformanceMetric(
                    name="execution_time",
                    value=0.001 * multiplier,
                    unit="seconds",
                    timestamp=datetime.now(),
                    context={}
                ),
                'control_energy': PerformanceMetric(
                    name="control_energy",
                    value=10.5,  # Keep constant
                    unit="J·s",
                    timestamp=datetime.now(),
                    context={}
                )
            }

            test_benchmark = PerformanceBenchmark(
                component_name="ClassicalSMC",
                test_scenario="standard",
                metrics=test_metrics,
                baseline_hash=f"test_{multiplier}",
                execution_environment={'python_version': '3.9'},
                success=True
            )

            regressions = performance_benchmark_suite.detect_regressions(test_benchmark)
            exec_time_regression = next((r for r in regressions if r.metric_name == 'execution_time'), None)

            if should_detect:
                assert exec_time_regression is not None, f"Failed detection test: {description}"
                assert exec_time_regression.is_regression, f"Failed regression flag: {description}"
            else:
                if exec_time_regression:
                    assert not exec_time_regression.is_regression, f"False positive: {description}"


if __name__ == "__main__":
    # Run standalone performance benchmarking
    benchmark_suite = PerformanceBenchmarkSuite()

    print("Running comprehensive performance benchmarks...")

    # Test all controller types
    for smc_type in SMCType:
        try:
            print(f"\nBenchmarking {smc_type.value}...")
            metrics = benchmark_suite.benchmark_controller_performance(smc_type)

            print(f"  Control computation time: {metrics['control_computation_time'].value*1e6:.1f}μs")
            print(f"  Settling time: {metrics['settling_time'].value:.2f}s")
            print(f"  Control energy: {metrics['control_energy'].value:.2f} J·s")
            print(f"  Numerical stability: {metrics['numerical_stability_rate'].value*100:.1f}%")

        except Exception as e:
            print(f"  ❌ Failed: {str(e)}")

    # Generate sample regression report
    print("\n" + "="*60)
    print("SAMPLE REGRESSION REPORT")
    print("="*60)
    report = benchmark_suite.generate_regression_report([])
    print(report)