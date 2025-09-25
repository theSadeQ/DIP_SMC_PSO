#==========================================================================================\\\
#============ tests/test_benchmarks/test_modular_framework.py =============================\\\
#==========================================================================================\\\
"""
Tests for the modular benchmarking framework capabilities.

This module tests the enhanced capabilities provided by the modular
architecture, including comprehensive comparisons, performance profiling,
and advanced analysis features.

Test Categories:
* **Comprehensive Comparison**: Multi-scenario testing framework
* **Performance Profiling**: Computational efficiency analysis
* **Modular Integration**: Component interaction validation
* **Enhanced Analytics**: Advanced analysis capabilities
"""

from __future__ import annotations

from typing import List
import numpy as np
import pytest

from benchmarks.benchmark import IntegrationBenchmark
from benchmarks.comparison import ComparisonScenario


def test_comprehensive_method_comparison(integration_benchmark: IntegrationBenchmark, test_scenarios: List[ComparisonScenario]):
    """Test comprehensive comparison framework with custom scenarios.

    This test verifies that the comprehensive comparison framework
    works correctly with user-defined test scenarios.

    Parameters
    ----------
    benchmark : IntegrationBenchmark
        Configured benchmark instance from pytest fixture
    test_scenarios : list of ComparisonScenario
        Test scenarios from pytest fixture
    """
    results = integration_benchmark.comprehensive_comparison(test_scenarios)

    # Verify results structure
    assert len(results) == len(test_scenarios)

    for scenario in test_scenarios:
        assert scenario.name in results
        result = results[scenario.name]

        # Check for required result components
        assert hasattr(result, 'rankings')
        assert hasattr(result, 'method_results')
        assert hasattr(result, 'accuracy_analysis')
        assert hasattr(result, 'performance_profile')

        # Check ranking categories
        assert 'accuracy' in result.rankings
        assert 'speed' in result.rankings
        assert 'efficiency' in result.rankings

        # Verify method results exist for tested methods
        assert len(result.method_results) > 0


def test_performance_profiling(integration_benchmark: IntegrationBenchmark, integration_methods: List[str]):
    """Test performance profiling capabilities.

    This test verifies that performance profiling works correctly
    and provides meaningful timing and efficiency metrics.

    Parameters
    ----------
    benchmark : IntegrationBenchmark
        Configured benchmark instance from pytest fixture
    integration_methods : list of str
        Available integration methods from pytest fixture
    """
    # Test with subset of methods for faster execution
    test_methods = ['Euler', 'RK4']
    profile = integration_benchmark.profile_performance(
        methods=test_methods, sim_time=1.0, dt=0.01
    )

    # Verify profile structure
    for method in test_methods:
        assert method in profile
        method_profile = profile[method]

        # Check required performance metrics
        assert 'execution_time' in method_profile
        assert 'steps_per_second' in method_profile
        assert 'function_evaluations' in method_profile
        assert 'total_steps' in method_profile

        # Verify reasonable values
        assert method_profile['execution_time'] > 0
        assert method_profile['steps_per_second'] > 0
        assert method_profile['total_steps'] > 0


def test_default_comprehensive_comparison(integration_benchmark: IntegrationBenchmark):
    """Test comprehensive comparison with default scenarios.

    This test verifies that the framework works with its built-in
    default test scenarios.

    Parameters
    ----------
    benchmark : IntegrationBenchmark
        Configured benchmark instance from pytest fixture
    """
    # Use default scenarios (should be quick subset for testing)
    results = integration_benchmark.comprehensive_comparison()

    # Should have at least one scenario
    assert len(results) > 0

    # Check that all results have proper structure
    for scenario_name, result in results.items():
        assert isinstance(scenario_name, str)
        assert hasattr(result, 'rankings')
        assert hasattr(result, 'summary_statistics')


def test_enhanced_analysis_integration(integration_benchmark: IntegrationBenchmark):
    """Test integration between enhanced analysis components.

    This test verifies that the different modular components work
    together correctly and produce consistent results.

    Parameters
    ----------
    benchmark : IntegrationBenchmark
        Configured benchmark instance from pytest fixture
    """
    # Test method accuracy analysis
    accuracy_results = integration_benchmark.analyze_method_accuracy(
        method_name='RK4',
        sim_time=1.0,
        dt_values=[0.01]
    )

    assert 0.01 in accuracy_results
    result = accuracy_results[0.01]

    # Verify accuracy analysis structure
    assert 'energy_drift' in result
    assert 'max_drift' in result
    assert 'mean_drift' in result
    assert 'relative_error' in result
    assert 'conservation_violated' in result
    assert 'execution_time' in result

    # Test performance profiling integration
    profile = integration_benchmark.profile_performance(
        methods=['RK4'], sim_time=1.0, dt=0.01
    )

    assert 'RK4' in profile

    # Cross-validate timing measurements
    profile_time = profile['RK4']['execution_time']
    accuracy_time = result['execution_time']

    # Times should be reasonably close (within order of magnitude)
    assert abs(np.log10(profile_time) - np.log10(accuracy_time)) < 1.0


def test_conservation_validation_methods(integration_benchmark: IntegrationBenchmark):
    """Test conservation validation across different methods.

    This test ensures conservation validation works for all
    supported integration methods.

    Parameters
    ----------
    benchmark : IntegrationBenchmark
        Configured benchmark instance from pytest fixture
    """
    methods = ['Euler', 'RK4', 'RK45']

    for method in methods:
        validation_results = integration_benchmark.validate_conservation_laws(
            method_name=method, sim_time=2.0, dt=0.01
        )

        # Verify validation structure
        assert validation_results['method'] == method
        assert 'energy_analysis' in validation_results
        assert 'hamiltonian_analysis' in validation_results
        assert validation_results['physics_conservative'] is True

        # Energy analysis should have required attributes
        energy_analysis = validation_results['energy_analysis']
        assert hasattr(energy_analysis, 'method_name')
        assert energy_analysis.method_name == method


@pytest.mark.parametrize("scenario_type", ["small_angles", "high_energy"])
def test_custom_scenario_creation(integration_benchmark: IntegrationBenchmark, scenario_type: str):
    """Test creation and execution of custom test scenarios.

    This parametrized test verifies that custom scenarios can be
    created and executed successfully.

    Parameters
    ----------
    benchmark : IntegrationBenchmark
        Configured benchmark instance from pytest fixture
    scenario_type : str
        Type of scenario to create and test
    """
    if scenario_type == "small_angles":
        x0 = np.array([0.0, 0.05, 0.05, 0.0, 0.0, 0.0])
        description = "Small angle test scenario"
    elif scenario_type == "high_energy":
        x0 = np.array([0.0, 0.1, 0.1, 1.0, 1.0, 1.0])
        description = "High energy test scenario"

    scenario = ComparisonScenario(
        name=scenario_type,
        x0=x0,
        sim_time=1.0,
        dt_values=[0.01],
        description=description
    )

    # Test that scenario can be executed
    results = integration_benchmark.comprehensive_comparison([scenario])

    assert scenario_type in results
    result = results[scenario_type]
    assert hasattr(result, 'scenario_name')
    assert result.scenario_name == scenario_type


def test_modular_component_isolation(integration_benchmark: IntegrationBenchmark):
    """Test that modular components can be used independently.

    This test verifies that individual components of the modular
    framework can be used in isolation without requiring the full
    benchmark orchestration.

    Parameters
    ----------
    benchmark : IntegrationBenchmark
        Configured benchmark instance from pytest fixture
    """
    # Test direct use of integrators
    euler_result = integration_benchmark.euler_integrator.integrate(
        integration_benchmark.x0, sim_time=1.0, dt=0.01, controller=None
    )
    assert hasattr(euler_result, 'method')
    assert euler_result.method == 'Euler'

    # Test direct use of energy analyzer
    energy_drift = integration_benchmark.energy_analyzer.compute_energy_drift(euler_result)
    assert isinstance(energy_drift, np.ndarray)
    assert len(energy_drift) > 0

    # Test direct use of analysis
    accuracy_analysis = integration_benchmark.energy_analyzer.analyze_energy_conservation(euler_result)
    assert hasattr(accuracy_analysis, 'method_name')
    assert accuracy_analysis.method_name == 'Euler'