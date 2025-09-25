#==========================================================================================\\
#============= tests/test_controllers/smc/core/test_equivalent_control.py ================\\
#==========================================================================================\\
"""
Tests for Equivalent Control Computation.
SINGLE JOB: Test only equivalent control mathematical computation and error handling.
"""

import pytest
import numpy as np
from unittest.mock import Mock

from src.controllers.smc.core.equivalent_control import EquivalentControl
from src.controllers.smc.core.sliding_surface import LinearSlidingSurface


class TestEquivalentControlInitialization:
    """Test EquivalentControl initialization and configuration."""

    def test_initialization_default_parameters(self):
        """Test initialization with default parameters."""
        eq_control = EquivalentControl()
        
        assert eq_control.dynamics_model is None
        assert eq_control.regularization == 1e-10
        assert eq_control.controllability_threshold == 1e-4
        np.testing.assert_array_equal(eq_control.B, [1.0, 0.0, 0.0])

    def test_initialization_custom_parameters(self):
        """Test initialization with custom parameters."""
        mock_dynamics = Mock()
        eq_control = EquivalentControl(
            dynamics_model=mock_dynamics,
            regularization=1e-8,
            controllability_threshold=1e-3
        )
        
        assert eq_control.dynamics_model == mock_dynamics
        assert eq_control.regularization == 1e-8
        assert eq_control.controllability_threshold == 1e-3

    def test_logger_initialization(self):
        """Test logger is properly initialized."""
        eq_control = EquivalentControl()
        assert hasattr(eq_control, 'logger')
        assert eq_control.logger.name == 'EquivalentControl'


class TestEquivalentControlComputation:
    """Test equivalent control computation functionality."""

    @pytest.fixture
    def mock_dynamics_valid(self):
        """Create mock dynamics model that returns valid matrices."""
        dynamics = Mock()
        dynamics.get_dynamics.return_value = (
            np.array([[2.0, 0.5, 0.3], [0.5, 1.0, 0.2], [0.3, 0.2, 0.8]]),  # M matrix
            np.array([0.1, -0.2, 0.05])  # F vector
        )
        return dynamics

    @pytest.fixture
    def sliding_surface(self):
        """Create sliding surface for testing."""
        return LinearSlidingSurface([1.0, 2.0, 0.5, 1.5])

    @pytest.fixture
    def test_state(self):
        """Standard test state."""
        return np.array([0.1, 0.2, 0.05, 0.1, -0.03, -0.05])

    def test_compute_no_dynamics_model(self, sliding_surface, test_state):
        """Test compute returns zero when no dynamics model provided."""
        eq_control = EquivalentControl(dynamics_model=None)
        result = eq_control.compute(test_state, sliding_surface)
        
        assert result == 0.0

    def test_compute_valid_dynamics(self, mock_dynamics_valid, sliding_surface, test_state):
        """Test compute with valid dynamics model."""
        eq_control = EquivalentControl(dynamics_model=mock_dynamics_valid)
        result = eq_control.compute(test_state, sliding_surface)
        
        assert isinstance(result, float)
        assert np.isfinite(result)
        # Verify dynamics was called
        mock_dynamics_valid.get_dynamics.assert_called_once_with(test_state)

    def test_compute_singular_matrix_returns_zero(self, sliding_surface, test_state):
        """Test compute returns zero for singular matrices."""
        mock_dynamics = Mock()
        # Return singular matrix (zero determinant)
        mock_dynamics.get_dynamics.return_value = (
            np.array([[1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [3.0, 6.0, 9.0]]),  # Singular M
            np.array([0.1, -0.2, 0.05])
        )
        
        eq_control = EquivalentControl(dynamics_model=mock_dynamics)
        result = eq_control.compute(test_state, sliding_surface)
        
        # Should handle singular matrix gracefully (allow small values due to regularization)
        assert abs(result) < 0.1

    def test_compute_dynamics_extraction_failure(self, sliding_surface, test_state):
        """Test compute handles dynamics extraction failure."""
        mock_dynamics = Mock()
        mock_dynamics.get_dynamics.side_effect = Exception("Dynamics failed")
        
        eq_control = EquivalentControl(dynamics_model=mock_dynamics)
        result = eq_control.compute(test_state, sliding_surface)
        
        assert result == 0.0

    def test_compute_poor_controllability(self, sliding_surface, test_state):
        """Test compute with poor controllability."""
        mock_dynamics = Mock()
        # Return matrices that result in poor controllability
        mock_dynamics.get_dynamics.return_value = (
            np.array([[1000.0, 0.0, 0.0], [0.0, 1000.0, 0.0], [0.0, 0.0, 1000.0]]),  # Large M
            np.array([0.001, 0.001, 0.001])  # Small F
        )
        
        eq_control = EquivalentControl(
            dynamics_model=mock_dynamics,
            controllability_threshold=1.0  # High threshold
        )
        result = eq_control.compute(test_state, sliding_surface)
        
        # Should return zero for poor controllability
        assert result == 0.0

    def test_compute_non_finite_result(self, sliding_surface, test_state):
        """Test compute handles non-finite results."""
        mock_dynamics = Mock()
        # Return matrices that could cause numerical issues
        mock_dynamics.get_dynamics.return_value = (
            np.array([[1e-20, 0.0, 0.0], [0.0, 1e-20, 0.0], [0.0, 0.0, 1e-20]]),
            np.array([1e20, 1e20, 1e20])  # Very large forces
        )
        
        eq_control = EquivalentControl(dynamics_model=mock_dynamics)
        result = eq_control.compute(test_state, sliding_surface)
        
        # Should handle non-finite results gracefully
        assert result == 0.0


class TestEquivalentControlMatrixExtraction:
    """Test dynamics matrix extraction methods."""

    def test_extract_dynamics_get_dynamics_interface(self):
        """Test extraction via get_dynamics interface."""
        mock_dynamics = Mock()
        mock_dynamics.get_dynamics.return_value = (
            np.eye(3), np.array([1, 2, 3])
        )
        
        eq_control = EquivalentControl(dynamics_model=mock_dynamics)
        M, F = eq_control._extract_dynamics_matrices(np.zeros(6))
        
        np.testing.assert_array_equal(M, np.eye(3))
        np.testing.assert_array_equal(F, [1, 2, 3])

    def test_extract_dynamics_direct_attributes(self):
        """Test extraction via direct M, F attributes."""
        mock_dynamics = Mock()
        del mock_dynamics.get_dynamics  # Remove get_dynamics method
        mock_dynamics.M = np.eye(3)
        mock_dynamics.F = np.array([4, 5, 6])
        
        eq_control = EquivalentControl(dynamics_model=mock_dynamics)
        M, F = eq_control._extract_dynamics_matrices(np.zeros(6))
        
        np.testing.assert_array_equal(M, np.eye(3))
        np.testing.assert_array_equal(F, [4, 5, 6])

    def test_extract_dynamics_no_interface_returns_none(self):
        """Test extraction returns None for unrecognized interface."""
        mock_dynamics = Mock(spec=[])  # Empty spec, no methods
        
        eq_control = EquivalentControl(dynamics_model=mock_dynamics)
        M, F = eq_control._extract_dynamics_matrices(np.zeros(6))
        
        assert M is None
        assert F is None


class TestEquivalentControlControllabilityAnalysis:
    """Test controllability analysis functionality."""

    def test_check_controllability_no_model(self):
        """Test controllability check with no dynamics model."""
        eq_control = EquivalentControl(dynamics_model=None)
        sliding_surface = LinearSlidingSurface([1.0, 2.0, 0.5, 1.5])
        
        result = eq_control.check_controllability(np.zeros(6), sliding_surface)
        
        assert result['controllable'] is False
        assert result['LM_inv_B'] == 0.0
        assert result['condition_number'] == np.inf
        assert result['rank_deficient'] is True

    def test_set_controllability_threshold_valid(self):
        """Test setting valid controllability threshold."""
        eq_control = EquivalentControl()
        eq_control.set_controllability_threshold(1e-3)
        
        assert eq_control.controllability_threshold == 1e-3

    def test_set_controllability_threshold_invalid(self):
        """Test setting invalid controllability threshold."""
        eq_control = EquivalentControl()
        
        with pytest.raises(ValueError, match="threshold must be positive"):
            eq_control.set_controllability_threshold(-1e-3)

    def test_get_dynamics_info_no_model(self):
        """Test dynamics info with no model."""
        eq_control = EquivalentControl(dynamics_model=None)
        
        info = eq_control.get_dynamics_info(np.zeros(6))
        
        assert info['has_model'] is False
        assert info['M_shape'] is None
        assert info['F_shape'] is None
        assert info['M_condition'] == np.inf
        assert info['M_determinant'] == 0.0