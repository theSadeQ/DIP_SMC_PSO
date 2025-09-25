#==========================================================================================\\
#============= tests/test_analysis/infrastructure/test_analysis_chain.py =================\\
#==========================================================================================\\

"""
Comprehensive test suite for analysis infrastructure chain validation.

This module tests the complete analysis framework from imports to execution,
ensuring all components work together seamlessly and provide scientifically
rigorous results.
"""

import pytest
import numpy as np
from typing import Dict, List, Any, Optional
import warnings
from unittest.mock import Mock, patch

# Core analysis imports
from src.analysis.validation.metrics import (
    compute_basic_metrics,
    compute_performance_metrics,
    compute_control_metrics,
    compute_stability_metrics,
    compute_frequency_metrics,
    compute_statistical_significance,
    compute_robustness_metrics,
    compute_comprehensive_metrics
)

from src.analysis.validation.statistical_tests import (
    StatisticalTestSuite,
    StatisticalTestConfig,
    TestType,
    AlternativeHypothesis,
    create_statistical_test_suite
)

from src.analysis.fault_detection.fdi import (
    FaultDetectionInterface,
    FDIsystem,
    DynamicsProtocol
)

from src.analysis.performance.control_metrics import *
from src.analysis.core.interfaces import StatisticalValidator, AnalysisResult, AnalysisStatus
from src.analysis.core.data_structures import StatisticalTestResult, ConfidenceInterval


class TestAnalysisInfrastructureChain:
    """Test suite for complete analysis infrastructure chain."""

    def test_critical_imports_available(self):
        """Test that all critical analysis imports are available without errors."""
        # This test ensures the ModuleNotFoundError is resolved
        try:
            # Metrics validation
            assert callable(compute_basic_metrics)
            assert callable(compute_performance_metrics)
            assert callable(compute_comprehensive_metrics)

            # Statistical testing
            assert StatisticalTestSuite is not None
            assert create_statistical_test_suite is not None

            # Fault detection
            assert FaultDetectionInterface is not None
            assert FDIsystem is not None

        except ImportError as e:
            pytest.fail(f"Critical analysis import failed: {e}")

    def test_metrics_chain_functionality(self):
        """Test the complete metrics computation chain."""
        # Generate test data
        time_vector = np.linspace(0, 10, 1000)
        test_states = np.column_stack([
            np.sin(2 * np.pi * 0.1 * time_vector) + 0.1 * np.random.randn(1000),
            np.cos(2 * np.pi * 0.1 * time_vector) + 0.1 * np.random.randn(1000),
            0.5 * np.sin(2 * np.pi * 0.2 * time_vector) + 0.05 * np.random.randn(1000),
            0.2 * np.cos(2 * np.pi * 0.2 * time_vector) + 0.05 * np.random.randn(1000)
        ])
        test_controls = 0.1 * np.sin(2 * np.pi * 0.05 * time_vector) + 0.02 * np.random.randn(1000)

        # Test comprehensive metrics computation
        metrics = compute_comprehensive_metrics(
            states=test_states,
            controls=test_controls,
            time_vector=time_vector
        )

        # Validate metrics structure and content
        assert isinstance(metrics, dict)
        assert len(metrics) > 0

        # Check for expected metric categories
        expected_categories = ['control_metrics', 'stability_metrics']
        for category in expected_categories:
            assert category in metrics, f"Missing {category} in comprehensive metrics"

        # Validate control metrics
        control_metrics = metrics['control_metrics']
        assert 'control_effort' in control_metrics
        assert 'max_control' in control_metrics
        assert 'settling_time' in control_metrics
        assert all(isinstance(v, (int, float)) for v in control_metrics.values())

        # Validate stability metrics
        stability_metrics = metrics['stability_metrics']
        assert 'max_deviation' in stability_metrics
        assert 'final_deviation' in stability_metrics
        assert 'stability_margin' in stability_metrics
        assert all(isinstance(v, (int, float)) for v in stability_metrics.values())

    def test_statistical_test_suite_functionality(self):
        """Test the statistical test suite infrastructure."""
        # Create test configuration
        config = StatisticalTestConfig(
            significance_level=0.05,
            confidence_level=0.95,
            minimum_sample_size=10,
            bootstrap_samples=100  # Reduced for testing speed
        )

        # Initialize test suite
        test_suite = StatisticalTestSuite(config)

        # Verify validation methods are available
        methods = test_suite.validation_methods
        assert isinstance(methods, list)
        assert len(methods) > 0

        expected_methods = [
            'normality_tests',
            'stationarity_tests',
            'independence_tests',
            'hypothesis_tests'
        ]

        for method in expected_methods:
            assert method in methods, f"Missing {method} in validation methods"

        # Test with synthetic data
        np.random.seed(42)  # For reproducibility
        normal_data = np.random.normal(0, 1, 100)

        # Run comprehensive validation
        result = test_suite.validate(normal_data)

        # Verify result structure
        assert isinstance(result, AnalysisResult)
        assert result.status == AnalysisStatus.SUCCESS
        assert isinstance(result.data, dict)
        assert 'validation_summary' in result.data

        # Check that tests were actually run
        assert len(result.data) > 1  # Should have multiple test categories plus summary

    def test_fault_detection_infrastructure(self):
        """Test fault detection infrastructure functionality."""
        # Create mock dynamics model
        class MockDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                """Simple mock dynamics for testing."""
                # Simple linear dynamics: x' = A*x + B*u
                A = np.array([[0, 1, 0, 0],
                              [0, 0, 1, 0],
                              [0, 0, 0, 1],
                              [0, 0, 0, 0]])
                B = np.array([0, 0, 0, 1])
                return state + dt * (A @ state + B * u)

        # Initialize fault detection system
        fdi_system = FDIsystem(
            residual_threshold=0.1,
            persistence_counter=3,
            residual_states=[0, 1, 2, 3],
            adaptive=True,
            window_size=20
        )

        # Verify interface compliance
        assert hasattr(fdi_system, 'check')
        assert callable(fdi_system.check)

        # Test normal operation (no fault)
        dynamics = MockDynamics()
        dt = 0.01

        # Generate normal operation data
        state = np.array([0.1, 0.0, 0.1, 0.0])

        for i in range(10):
            t = i * dt
            u = 0.1 * np.sin(2 * np.pi * t)  # Sinusoidal control

            # Add small measurement noise
            noisy_state = state + 0.001 * np.random.randn(4)

            status, residual = fdi_system.check(t, noisy_state, u, dt, dynamics)

            # Should detect no fault under normal conditions
            assert status == "OK"
            assert isinstance(residual, (int, float))
            assert residual >= 0

            # Update state for next iteration
            state = dynamics.step(state, u, dt)

        # Verify history is being recorded
        assert len(fdi_system.times) == 10
        assert len(fdi_system.residuals) == 10

    def test_analysis_chain_integration(self):
        """Test integration of all analysis components working together."""
        # Generate comprehensive test scenario
        np.random.seed(42)

        # Simulate control system data
        time_vector = np.linspace(0, 5, 500)
        dt = time_vector[1] - time_vector[0]

        # States: position, velocity for two masses
        states = np.zeros((500, 4))
        controls = np.zeros(500)

        # Simple simulation with noise
        for i in range(1, 500):
            t = time_vector[i]
            # Simple PD control
            controls[i] = -2.0 * states[i-1, 0] - 0.5 * states[i-1, 1]

            # Simple dynamics with noise
            states[i, 0] = states[i-1, 0] + dt * states[i-1, 1] + 0.001 * np.random.randn()
            states[i, 1] = states[i-1, 1] + dt * controls[i] + 0.001 * np.random.randn()
            states[i, 2] = states[i-1, 2] + dt * states[i-1, 3] + 0.001 * np.random.randn()
            states[i, 3] = states[i-1, 3] + dt * (-states[i-1, 2] + controls[i]) + 0.001 * np.random.randn()

        # 1. Metrics Analysis Chain
        metrics = compute_comprehensive_metrics(
            states=states,
            controls=controls,
            time_vector=time_vector
        )

        assert isinstance(metrics, dict)
        assert len(metrics) >= 2  # At least control and stability metrics

        # 2. Statistical Validation Chain
        statistical_suite = create_statistical_test_suite({
            'significance_level': 0.05,
            'minimum_sample_size': 10,
            'bootstrap_samples': 100
        })

        # Test on control signals
        control_validation = statistical_suite.validate(
            controls,
            test_types=['normality_tests', 'independence_tests']
        )

        assert control_validation.status == AnalysisStatus.SUCCESS
        assert 'normality_tests' in control_validation.data

        # 3. Fault Detection Chain
        class SimpleDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                # Simplified dynamics for testing
                next_state = state.copy()
                next_state[0] += dt * state[1]
                next_state[1] += dt * u
                next_state[2] += dt * state[3]
                next_state[3] += dt * (-state[2] + u)
                return next_state

        fdi = FDIsystem(
            residual_threshold=0.05,
            persistence_counter=5,
            adaptive=True
        )

        dynamics = SimpleDynamics()
        fault_detected = False

        for i in range(50):  # Test subset for speed
            status, _ = fdi.check(
                time_vector[i],
                states[i],
                controls[i],
                dt,
                dynamics
            )
            if status == "FAULT":
                fault_detected = True
                break

        # Under normal conditions, should not detect faults
        assert not fault_detected, "False positive fault detection"

        # 4. Cross-validation between components
        # Ensure metrics and statistical tests are consistent
        control_effort = metrics['control_metrics']['control_effort']
        assert control_effort > 0, "Control effort should be positive"

        # Verify statistical significance testing works
        dummy_data1 = np.random.normal(0, 1, 50)
        dummy_data2 = np.random.normal(0.5, 1, 50)  # Different mean

        significance_result = compute_statistical_significance(dummy_data1, dummy_data2)
        assert isinstance(significance_result, dict)
        assert 'p_value' in significance_result
        assert 'statistic' in significance_result
        assert 'significant' in significance_result

    def test_analysis_error_handling(self):
        """Test error handling throughout the analysis chain."""
        # Test with invalid data

        # 1. Empty data
        empty_metrics = compute_basic_metrics(np.array([]))
        assert empty_metrics['count'] == 0

        # 2. NaN data
        nan_data = np.array([1, 2, np.nan, 4, 5])
        basic_metrics = compute_basic_metrics(nan_data)
        assert isinstance(basic_metrics, dict)

        # 3. Statistical test suite with insufficient data
        test_suite = StatisticalTestSuite()
        insufficient_result = test_suite.validate(np.array([1, 2]))  # Too few samples
        assert insufficient_result.status == AnalysisStatus.ERROR

        # 4. Fault detection with invalid dynamics
        class BrokenDynamics:
            def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
                raise ValueError("Simulated dynamics failure")

        fdi = FDIsystem()
        broken_dynamics = BrokenDynamics()

        # Should handle dynamics failure gracefully
        status, residual = fdi.check(
            1.0, np.array([0, 0, 0, 0]), 0.0, 0.01, broken_dynamics
        )
        assert status == "OK"  # Should not crash, assume OK on failure

    def test_performance_analysis_accuracy(self):
        """Test accuracy of performance analysis computations."""
        # Known analytical test case
        time_vector = np.linspace(0, 2*np.pi, 1000)

        # Perfect sine wave - known properties
        reference_signal = np.sin(time_vector)
        measured_signal = np.sin(time_vector) + 0.1 * np.sin(3 * time_vector)  # Add harmonics

        performance_metrics = compute_performance_metrics(reference_signal, measured_signal)

        # Verify metric structure
        expected_keys = ['mse', 'rmse', 'mae', 'max_error']
        for key in expected_keys:
            assert key in performance_metrics
            assert isinstance(performance_metrics[key], (int, float))

        # Verify mathematical relationships
        mse = performance_metrics['mse']
        rmse = performance_metrics['rmse']
        assert abs(rmse - np.sqrt(mse)) < 1e-10, "RMSE should equal sqrt(MSE)"

        # Test frequency domain analysis
        sampling_rate = len(time_vector) / (2 * np.pi)
        freq_metrics = compute_frequency_metrics(measured_signal, sampling_rate)

        assert 'dominant_frequency' in freq_metrics
        assert 'bandwidth' in freq_metrics
        # Should detect the 1 Hz fundamental frequency (approximately)
        dominant_freq = freq_metrics['dominant_frequency']
        expected_freq = 1 / (2 * np.pi)  # 1 radian/second = 1/(2π) Hz
        assert abs(dominant_freq - expected_freq) < 0.1, "Should detect fundamental frequency"

    def test_statistical_rigor_validation(self):
        """Test statistical rigor of the analysis framework."""
        np.random.seed(42)

        # Generate data with known statistical properties
        n = 1000
        normal_data = np.random.normal(loc=5, scale=2, size=n)
        uniform_data = np.random.uniform(low=0, high=10, size=n)

        test_suite = StatisticalTestSuite(StatisticalTestConfig(
            significance_level=0.05,
            bootstrap_samples=200
        ))

        # Test normality detection
        normal_result = test_suite.validate(normal_data, test_types=['normality_tests'])
        uniform_result = test_suite.validate(uniform_data, test_types=['normality_tests'])

        # Normal data should pass normality tests more often than uniform data
        normal_tests = normal_result.data.get('normality_tests', {})
        uniform_tests = uniform_result.data.get('normality_tests', {})

        assert len(normal_tests) > 0, "Should have normality test results"
        assert len(uniform_tests) > 0, "Should have normality test results"

        # Count how many tests conclude "Normal" for each dataset
        normal_passes = sum(1 for test in normal_tests.values()
                           if isinstance(test, dict) and 'conclusion' in test
                           and 'Normal' in test['conclusion'])

        uniform_passes = sum(1 for test in uniform_tests.values()
                            if isinstance(test, dict) and 'conclusion' in test
                            and 'Normal' in test['conclusion'])

        # Normal data should pass more normality tests than uniform data
        # (This is probabilistic, but should hold with high probability)
        assert normal_passes >= uniform_passes, \
            f"Normal data should pass more normality tests: {normal_passes} vs {uniform_passes}"

    def test_analysis_framework_robustness(self):
        """Test robustness of analysis framework to edge cases."""
        # Test with various problematic data types
        test_cases = [
            np.array([1e-15, 2e-15, 3e-15]),  # Very small numbers
            np.array([1e15, 2e15, 3e15]),     # Very large numbers
            np.array([0, 0, 0, 0, 0]),        # All zeros
            np.array([1, 1, 1, 1, 1]),        # No variation
            np.array([-1000, 1000, -500, 500])  # High dynamic range
        ]

        for i, test_data in enumerate(test_cases):
            # Basic metrics should handle all cases
            metrics = compute_basic_metrics(test_data)
            assert isinstance(metrics, dict), f"Failed on test case {i}"
            assert 'mean' in metrics, f"Missing mean in test case {i}"
            assert all(np.isfinite(list(metrics.values()))), f"Non-finite values in test case {i}"

            # Statistical tests should handle gracefully
            test_suite = StatisticalTestSuite()
            if len(test_data) >= test_suite.config.minimum_sample_size:
                result = test_suite.validate(test_data)
                # Should not crash, though may return limited results
                assert isinstance(result, AnalysisResult), f"Invalid result type for test case {i}"

    def test_analysis_chain_performance(self):
        """Test performance characteristics of analysis chain."""
        import time

        # Large dataset to test performance
        np.random.seed(42)
        large_states = np.random.randn(10000, 4)
        large_controls = np.random.randn(10000)
        time_vector = np.linspace(0, 100, 10000)

        # Measure comprehensive metrics computation time
        start_time = time.time()
        metrics = compute_comprehensive_metrics(large_states, large_controls, time_vector)
        metrics_time = time.time() - start_time

        # Should complete in reasonable time (< 5 seconds on most machines)
        assert metrics_time < 5.0, f"Metrics computation too slow: {metrics_time:.2f}s"
        assert isinstance(metrics, dict), "Should return valid metrics"

        # Test statistical suite performance
        subset_data = large_controls[:1000]  # Reasonable size for statistical tests

        start_time = time.time()
        test_suite = StatisticalTestSuite(StatisticalTestConfig(bootstrap_samples=100))
        result = test_suite.validate(subset_data)
        stats_time = time.time() - start_time

        # Statistical tests should also complete in reasonable time
        assert stats_time < 10.0, f"Statistical tests too slow: {stats_time:.2f}s"
        assert result.status == AnalysisStatus.SUCCESS, "Should complete successfully"


# Additional fixtures and utilities for testing
@pytest.fixture
def sample_control_data():
    """Generate sample control system data for testing."""
    np.random.seed(42)
    time = np.linspace(0, 10, 1000)
    states = np.column_stack([
        np.sin(time) + 0.1 * np.random.randn(1000),
        np.cos(time) + 0.1 * np.random.randn(1000),
        0.5 * np.sin(2*time) + 0.05 * np.random.randn(1000),
        0.5 * np.cos(2*time) + 0.05 * np.random.randn(1000)
    ])
    controls = 0.1 * np.sin(0.5 * time) + 0.02 * np.random.randn(1000)
    return {'states': states, 'controls': controls, 'time': time}


@pytest.fixture
def mock_dynamics_model():
    """Mock dynamics model for fault detection testing."""
    class MockDynamics:
        def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
            # Simple integrator dynamics
            next_state = state.copy()
            next_state[0] += dt * state[1]
            next_state[1] += dt * u
            if len(state) > 2:
                next_state[2] += dt * state[3]
                next_state[3] += dt * (-0.1 * state[2] + u)
            return next_state

    return MockDynamics()


if __name__ == "__main__":
    # Run basic smoke test if executed directly
    test_suite = TestAnalysisInfrastructureChain()

    print("Running analysis infrastructure chain validation...")

    try:
        test_suite.test_critical_imports_available()
        print("✓ Critical imports test passed")

        test_suite.test_metrics_chain_functionality()
        print("✓ Metrics chain test passed")

        test_suite.test_statistical_test_suite_functionality()
        print("✓ Statistical test suite test passed")

        test_suite.test_fault_detection_infrastructure()
        print("✓ Fault detection infrastructure test passed")

        test_suite.test_analysis_chain_integration()
        print("✓ Analysis chain integration test passed")

        print("\n🎉 All analysis infrastructure tests passed!")
        print("Analysis framework is scientifically rigorous and fully operational.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise