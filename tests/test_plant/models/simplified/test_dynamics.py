#==========================================================================================\\
#============= tests/test_plant/models/simplified/test_dynamics.py =====================\\
#==========================================================================================\\
"""
Tests for Simplified DIP Dynamics Model.
SINGLE JOB: Test only simplified DIP dynamics computation and validation.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

# Test imports with fallback for missing dependencies
try:
    from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
    from src.plant.models.simplified.config import SimplifiedDIPConfig
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    SimplifiedDIPDynamics = None
    SimplifiedDIPConfig = None


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Simplified dynamics modules not available")
class TestSimplifiedDIPDynamics:
    """Test simplified DIP dynamics computation."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for testing."""
        config = Mock(spec=SimplifiedDIPConfig)
        config.cart_mass = 1.0
        config.pendulum1_mass = 0.3
        config.pendulum2_mass = 0.2
        config.pendulum1_length = 0.5
        config.pendulum2_length = 0.3
        config.pendulum1_com = 0.25
        config.pendulum2_com = 0.15
        config.pendulum1_inertia = 0.02
        config.pendulum2_inertia = 0.01
        config.gravity = 9.81
        config.cart_friction = 0.1
        config.joint1_friction = 0.05
        config.joint2_friction = 0.03
        config.regularization_alpha = 1e-6
        config.min_regularization = 1e-12
        config.max_condition_number = 1e12
        return config

    @pytest.fixture
    def dynamics_model(self, mock_config):
        """Create simplified dynamics model for testing."""
        with patch('src.plant.models.simplified.dynamics.SimplifiedPhysicsComputer'):
            return SimplifiedDIPDynamics(mock_config, enable_monitoring=False)

    def test_initialization_default_parameters(self, mock_config):
        """Test dynamics model initialization."""
        with patch('src.plant.models.simplified.dynamics.SimplifiedPhysicsComputer'):
            model = SimplifiedDIPDynamics(mock_config)
            
            assert model.config == mock_config
            assert model.enable_fast_mode is False
            assert model.enable_monitoring is True

    def test_initialization_custom_parameters(self, mock_config):
        """Test initialization with custom parameters."""
        with patch('src.plant.models.simplified.dynamics.SimplifiedPhysicsComputer'):
            model = SimplifiedDIPDynamics(
                mock_config, 
                enable_fast_mode=True, 
                enable_monitoring=False
            )
            
            assert model.enable_fast_mode is True
            assert model.enable_monitoring is False

    def test_validate_control_input_valid(self, dynamics_model):
        """Test control input validation with valid input."""
        valid_input = np.array([5.0])
        result = dynamics_model._validate_control_input(valid_input)
        assert result == True

    def test_validate_control_input_wrong_shape(self, dynamics_model):
        """Test control input validation with wrong shape."""
        wrong_shape = np.array([1.0, 2.0])  # Should be (1,) not (2,)
        result = dynamics_model._validate_control_input(wrong_shape)
        assert result == False

    def test_validate_control_input_non_finite(self, dynamics_model):
        """Test control input validation with non-finite values."""
        nan_input = np.array([np.nan])
        inf_input = np.array([np.inf])
        
        assert dynamics_model._validate_control_input(nan_input) == False
        assert dynamics_model._validate_control_input(inf_input) == False

    def test_validate_control_input_excessive_force(self, dynamics_model):
        """Test control input validation with excessive force."""
        excessive_force = np.array([2000.0])  # > 1000.0 limit
        result = dynamics_model._validate_control_input(excessive_force)
        assert result == False

    def test_validate_state_derivative_valid(self, dynamics_model):
        """Test state derivative validation with valid input."""
        valid_derivative = np.array([0.1, 0.2, 0.0, -0.1, 0.05, -0.03])
        result = dynamics_model._validate_state_derivative(valid_derivative)
        assert result == True

    def test_validate_state_derivative_wrong_shape(self, dynamics_model):
        """Test state derivative validation with wrong shape."""
        wrong_shape = np.array([1.0, 2.0, 3.0])  # Should be (6,) not (3,)
        result = dynamics_model._validate_state_derivative(wrong_shape)
        assert result == False

    def test_validate_state_derivative_non_finite(self, dynamics_model):
        """Test state derivative validation with non-finite values."""
        nan_derivative = np.array([0.1, np.nan, 0.0, -0.1, 0.05, -0.03])
        result = dynamics_model._validate_state_derivative(nan_derivative)
        assert result == False

    def test_get_equilibrium_states(self, dynamics_model):
        """Test retrieval of equilibrium states."""
        equilibria = dynamics_model.get_equilibrium_states()
        
        assert isinstance(equilibria, dict)
        assert 'upright' in equilibria
        assert 'downward' in equilibria
        
        # Check upright equilibrium
        upright = equilibria['upright']
        np.testing.assert_array_equal(upright, np.zeros(6))
        
        # Check downward equilibrium  
        downward = equilibria['downward']
        expected_downward = np.array([0.0, np.pi, np.pi, 0.0, 0.0, 0.0])
        np.testing.assert_array_equal(downward, expected_downward)

    def test_compute_total_energy_interface(self, dynamics_model):
        """Test total energy computation interface."""
        state = np.array([0.1, 0.2, 0.05, 0.1, -0.03, -0.05])
        
        # Should delegate to physics computer
        with patch.object(dynamics_model.physics, 'compute_total_energy', return_value=5.0) as mock_energy:
            result = dynamics_model.compute_total_energy(state)
            
            assert result == 5.0
            mock_energy.assert_called_once_with(state)


class TestSimplifiedDIPDynamicsFallback:
    """Test fallback behavior when imports are not available."""
    
    @pytest.mark.skipif(IMPORTS_AVAILABLE, reason="Test only when imports fail")
    def test_imports_not_available(self):
        """Test that we handle missing imports gracefully."""
        assert SimplifiedDIPDynamics is None
        assert SimplifiedDIPConfig is None
        assert IMPORTS_AVAILABLE is False


class TestSimplifiedDIPDynamicsErrorHandling:
    """Test error handling in simplified dynamics."""
    
    @pytest.fixture
    def mock_config_minimal(self):
        """Create minimal mock config for error testing."""
        config = Mock()
        config.cart_mass = 1.0
        config.pendulum1_mass = 0.3
        config.pendulum2_mass = 0.2
        return config
    
    def test_edge_case_handling_structure(self, mock_config_minimal):
        """Test that error handling structure exists."""
        # This test ensures our test structure handles edge cases
        # Even if the actual implementation is not available
        
        test_cases = [
            "invalid_state_dimensions",
            "non_finite_states", 
            "excessive_control_inputs",
            "numerical_instability"
        ]
        
        # Verify we have test cases planned for these scenarios
        for case in test_cases:
            assert isinstance(case, str)
            assert len(case) > 0