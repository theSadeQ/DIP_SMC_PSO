#==========================================================================================\\\
#=================== tests/test_benchmarks/conftest.py ==================================\\\
#==========================================================================================\\\
"""
Pytest configuration and fixtures for integration method testing.

This module provides shared fixtures for testing integration methods,
ensuring consistent test environments and reducing code duplication.

Key Fixtures:
* **integration_benchmark**: IntegrationBenchmark instance for testing (renamed to avoid conflict with pytest-benchmark)
* **test_scenarios**: Standard test scenarios for method comparison
* **conservative_physics**: Physics parameters for energy conservation tests
"""

from __future__ import annotations

from typing import List, Dict
import numpy as np
import pytest

from benchmarks.benchmark import IntegrationBenchmark
from benchmarks.comparison import ComparisonScenario


@pytest.fixture
def integration_benchmark() -> IntegrationBenchmark:
    """Provides a reusable instance of the IntegrationBenchmark class for tests.

    Returns
    -------
    IntegrationBenchmark
        Configured benchmark instance with default parameters
    """
    return IntegrationBenchmark()


@pytest.fixture
def test_scenarios() -> List[ComparisonScenario]:
    """Provides standard test scenarios for integration method comparison.

    Returns
    -------
    list of ComparisonScenario
        Quick test scenarios suitable for unit testing
    """
    return [
        ComparisonScenario(
            name="quick_test",
            x0=np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0]),
            sim_time=1.0,
            dt_values=[0.01, 0.005],
            description="Quick test scenario for unit tests"
        ),
        ComparisonScenario(
            name="accuracy_test",
            x0=np.array([0.0, 0.05, 0.05, 0.0, 0.0, 0.0]),
            sim_time=2.0,
            dt_values=[0.05, 0.01],
            description="Accuracy comparison test"
        )
    ]


@pytest.fixture
def conservative_physics() -> Dict[str, float]:
    """Provides physics parameters for conservative system testing.

    Returns
    -------
    dict
        Physics parameters with zero friction for energy conservation tests
    """
    return {
        'cart_friction': 0.0,
        'joint1_friction': 0.0,
        'joint2_friction': 0.0
    }


@pytest.fixture
def integration_methods() -> List[str]:
    """Provides list of available integration methods for testing.

    Returns
    -------
    list of str
        Names of integration methods available for testing
    """
    return ['Euler', 'RK4', 'RK45']


@pytest.fixture
def simulation_parameters() -> Dict[str, float]:
    """Provides standard simulation parameters for testing.

    Returns
    -------
    dict
        Standard simulation parameters for consistent testing
    """
    return {
        'sim_time': 5.0,
        'dt': 0.01,
        'rtol': 1e-8
    }