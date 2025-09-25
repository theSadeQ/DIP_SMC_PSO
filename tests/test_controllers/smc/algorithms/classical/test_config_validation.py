#==========================================================================================\\\
#========= tests/test_controllers/smc/algorithms/classical/test_config_validation.py ========\\\
#==========================================================================================\\\
"""
Classical SMC Configuration Validation Tests.

SINGLE JOB: Test only configuration validation for Classical SMC controllers.
- Parameter validation rules
- Gain array validation
- Boundary layer validation
- Invalid configuration rejection
"""

import numpy as np
import pytest

from tests.test_controllers.smc.test_fixtures import MockDynamics
from src.controllers.smc.algorithms import ClassicalSMCConfig


class TestClassicalSMCConfigValidation:
    """Test configuration validation for Classical SMC."""

    def test_valid_config_acceptance(self):
        """Test that valid configurations are accepted."""
        valid_config = ClassicalSMCConfig(
            gains=[1.0, 1.0, 1.0, 1.0, 10.0, 0.5],
            max_force=50.0,
            boundary_layer=0.1,
            dynamics_model=MockDynamics()
        )

        assert len(valid_config.gains) == 6
        assert valid_config.max_force > 0
        assert valid_config.boundary_layer > 0

    def test_invalid_gains_length_rejection(self):
        """Test rejection of incorrect gains array length."""
        with pytest.raises(ValueError):
            ClassicalSMCConfig(
                gains=[1.0, 1.0, 1.0, 1.0, 10.0],  # Wrong length (should be 6)
                max_force=50.0,
                boundary_layer=0.1
            )

    def test_negative_max_force_rejection(self):
        """Test rejection of negative max force."""
        with pytest.raises(ValueError):
            ClassicalSMCConfig(
                gains=[1.0, 1.0, 1.0, 1.0, 10.0, 0.5],
                max_force=-50.0,  # Invalid negative value
                boundary_layer=0.1
            )

    def test_zero_boundary_layer_rejection(self):
        """Test rejection of zero boundary layer."""
        with pytest.raises(ValueError):
            ClassicalSMCConfig(
                gains=[1.0, 1.0, 1.0, 1.0, 10.0, 0.5],
                max_force=50.0,
                boundary_layer=0.0  # Invalid zero value
            )

    def test_negative_boundary_layer_rejection(self):
        """Test rejection of negative boundary layer."""
        with pytest.raises(ValueError):
            ClassicalSMCConfig(
                gains=[1.0, 1.0, 1.0, 1.0, 10.0, 0.5],
                max_force=50.0,
                boundary_layer=-0.1  # Invalid negative value
            )

    def test_nan_gains_rejection(self):
        """Test rejection of NaN values in gains."""
        with pytest.raises(ValueError):
            ClassicalSMCConfig(
                gains=[1.0, 1.0, np.nan, 1.0, 10.0, 0.5],  # Contains NaN
                max_force=50.0,
                boundary_layer=0.1
            )

    def test_infinite_gains_rejection(self):
        """Test rejection of infinite values in gains."""
        with pytest.raises(ValueError):
            ClassicalSMCConfig(
                gains=[1.0, 1.0, np.inf, 1.0, 10.0, 0.5],  # Contains inf
                max_force=50.0,
                boundary_layer=0.1
            )

    def test_gain_bounds_validation(self):
        """Test that gains are within reasonable bounds."""
        # Very large gains should be rejected
        with pytest.raises(ValueError):
            ClassicalSMCConfig(
                gains=[1e6, 1.0, 1.0, 1.0, 10.0, 0.5],  # Extremely large gain
                max_force=50.0,
                boundary_layer=0.1
            )

    def test_gain_signs_validation(self):
        """Test validation of gain signs."""
        # Some gains might need to be positive
        with pytest.raises(ValueError):
            ClassicalSMCConfig(
                gains=[1.0, 1.0, 1.0, 1.0, -10.0, 0.5],  # Negative switching gain
                max_force=50.0,
                boundary_layer=0.1
            )