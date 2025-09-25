#==========================================================================================\\\
#================= tests/test_controllers/smc/test_fixtures.py =======================\\\
#==========================================================================================\\\
"""
Shared test fixtures and utilities for SMC testing.

This module provides common test utilities, mock objects, and fixtures
used across all SMC test modules to ensure consistency and reduce duplication.
"""

from __future__ import annotations

import numpy as np
import pytest
from typing import Tuple, Dict, Any
from dataclasses import dataclass

# Test imports for modular controllers
from src.controllers.smc.algorithms import (
    # Classical SMC
    ModularClassicalSMC, ClassicalSMCConfig,

    # Adaptive SMC
    ModularAdaptiveSMC, AdaptiveSMCConfig,
    AdaptationLaw, ModifiedAdaptationLaw,
    UncertaintyEstimator, ParameterIdentifier, CombinedEstimator,

    # Super-Twisting SMC
    ModularSuperTwistingSMC, SuperTwistingSMCConfig,
    SuperTwistingAlgorithm,

    # Hybrid SMC
    ModularHybridSMC, HybridSMCConfig,
    HybridSwitchingLogic, SwitchingDecision, ControllerState,
    HybridMode, SwitchingCriterion
)

# Test imports for core components
from src.controllers.smc.core import (
    LinearSlidingSurface,
    SwitchingFunction,
    EquivalentControl,
    validate_smc_gains,
    SMCGainValidator
)


@dataclass
class TestSystemState:
    """Test system state for SMC testing."""
    position: np.ndarray
    velocity: np.ndarray
    time: float = 0.0


class MockDynamics:
    """Mock dynamics model for testing SMC controllers."""

    def __init__(self, n_dof: int = 3):
        self.n_dof = n_dof

    def _compute_physics_matrices(self, state: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute test physics matrices."""
        # Simple diagonal inertia matrix
        M = np.eye(self.n_dof)
        # Small damping
        C = 0.1 * np.eye(self.n_dof)
        # Zero gravity for simplicity
        G = np.zeros(self.n_dof)
        return M, C, G


@pytest.fixture
def mock_dynamics():
    """Fixture providing mock dynamics for testing."""
    return MockDynamics()


@pytest.fixture
def test_state():
    """Fixture providing test system state."""
    return TestSystemState(
        position=np.array([0.1, 0.05, 0.02]),
        velocity=np.array([0.2, -0.1, 0.15])
    )


@pytest.fixture
def classical_smc_config():
    """Fixture providing classical SMC configuration."""
    return ClassicalSMCConfig(
        sliding_gains=np.array([5.0, 3.0, 4.0]),
        switching_gains=np.array([10.0, 8.0, 12.0]),
        boundary_layer_thickness=0.1,
        enable_chattering_reduction=True
    )


@pytest.fixture
def adaptive_smc_config():
    """Fixture providing adaptive SMC configuration."""
    return AdaptiveSMCConfig(
        sliding_gains=np.array([5.0, 3.0, 4.0]),
        initial_adaptation_gains=np.array([1.0, 1.0, 1.0]),
        adaptation_rate=0.5,
        uncertainty_bound=2.0,
        enable_parameter_projection=True
    )


@pytest.fixture
def super_twisting_config():
    """Fixture providing super-twisting SMC configuration."""
    return SuperTwistingSMCConfig(
        alpha=np.array([2.0, 2.0, 2.0]),
        beta=np.array([1.0, 1.0, 1.0]),
        lambda_gain=np.array([5.0, 5.0, 5.0]),
        enable_finite_time_convergence=True
    )


@pytest.fixture
def hybrid_smc_config():
    """Fixture providing hybrid SMC configuration."""
    return HybridSMCConfig(
        switching_thresholds={'position': 0.1, 'velocity': 0.2},
        mode_timeouts={'classical': 5.0, 'adaptive': 10.0},
        enable_mode_memory=True,
        stability_margin=0.05
    )


def create_test_reference(t: float) -> np.ndarray:
    """Create test reference trajectory."""
    return np.array([
        0.5 * np.sin(t),
        0.3 * np.cos(t),
        0.2 * np.sin(0.5 * t)
    ])


def validate_control_output(control: np.ndarray, max_force: float = 50.0) -> bool:
    """Validate control output is within reasonable bounds."""
    return np.all(np.abs(control) <= max_force)


def compute_tracking_error(state: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Compute tracking error for test validation."""
    pos = state[:3]  # Assuming first 3 elements are positions
    return pos - reference