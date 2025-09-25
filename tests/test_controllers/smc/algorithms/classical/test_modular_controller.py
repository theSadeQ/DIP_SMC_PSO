#==========================================================================================\\
#======== tests/test_controllers/smc/algorithms/classical/test_modular_controller.py ====\\
#==========================================================================================\\
"""
Tests for Modular Classical SMC Controller.
SINGLE JOB: Test only modular classical SMC controller integration and interfaces.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

# Test imports with fallback
try:
    from src.controllers.smc.algorithms.classical.controller import (
        ModularClassicalSMC, ClassicalSMC
    )
    from src.controllers.smc.algorithms.classical.config import ClassicalSMCConfig
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    ModularClassicalSMC = None
    ClassicalSMC = None
    ClassicalSMCConfig = None


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Classical SMC modules not available")
class TestModularClassicalSMC:
    """Test modular classical SMC controller."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=ClassicalSMCConfig)
        config.gains = [2.0, 1.5, 3.0, 2.5, 5.0, 0.1]
        config.max_force = 100.0
        config.boundary_layer = 0.1
        config.K = 5.0
        config.kd = 0.1
        config.lam1 = 3.0
        config.lam2 = 2.5
        config.dynamics_model = None
        config.regularization = 1e-10
        config.boundary_layer_slope = 1.0
        config.switch_method = 'tanh'
        
        # Mock methods
        config.get_surface_gains.return_value = [2.0, 1.5, 3.0, 2.5]
        config.get_effective_controllability_threshold.return_value = 1e-4
        
        return config

    @pytest.fixture
    def modular_smc(self, mock_config):
        """Create modular classical SMC controller."""
        with patch('src.controllers.smc.algorithms.classical.controller.LinearSlidingSurface'), \
             patch('src.controllers.smc.algorithms.classical.controller.EquivalentControl'), \
             patch('src.controllers.smc.algorithms.classical.controller.BoundaryLayer'):
            return ModularClassicalSMC(mock_config)

    def test_initialization(self, mock_config, modular_smc):
        """Test modular controller initialization."""
        assert modular_smc.config == mock_config
        assert hasattr(modular_smc, '_surface')
        assert hasattr(modular_smc, '_equivalent')
        assert hasattr(modular_smc, '_boundary_layer')
        assert hasattr(modular_smc, 'logger')

    def test_compute_control_basic(self, modular_smc):
        """Test basic control computation."""
        state = np.array([0.1, 0.2, 0.05, 0.1, -0.03, -0.05])
        state_vars = Mock()
        history = {}
        
        # Mock component responses
        modular_smc._surface.compute.return_value = 0.5
        modular_smc._equivalent.compute.return_value = 2.0
        modular_smc._boundary_layer.compute_switching_control.return_value = -1.0
        modular_smc._boundary_layer.is_in_boundary_layer.return_value = False
        
        result = modular_smc.compute_control(state, state_vars, history)
        
        # Check result structure
        assert isinstance(result, dict)
        assert 'u' in result
        assert 'surface_value' in result
        assert 'equivalent_control' in result
        assert 'switching_control' in result
        assert 'derivative_control' in result
        assert 'controller_type' in result
        
        # Check controller type
        assert result['controller_type'] == 'classical_smc'

    def test_compute_control_with_saturation(self, modular_smc):
        """Test control computation with saturation."""
        state = np.array([0.1, 0.2, 0.05, 0.1, -0.03, -0.05])
        state_vars = Mock()
        history = {}
        
        # Mock large control components that exceed max_force
        modular_smc._surface.compute.return_value = 0.5
        modular_smc._equivalent.compute.return_value = 80.0  # Large equivalent control
        modular_smc._boundary_layer.compute_switching_control.return_value = 50.0  # Large switching
        modular_smc._boundary_layer.is_in_boundary_layer.return_value = False
        
        result = modular_smc.compute_control(state, state_vars, history)
        
        # Should be saturated to max_force
        assert abs(result['u']) <= modular_smc.config.max_force
        assert result['saturation_active'] == True
        assert result['total_before_saturation'] > modular_smc.config.max_force

    def test_gains_property(self, modular_smc):
        """Test gains property access."""
        gains = modular_smc.gains
        assert gains == modular_smc.config.gains
        assert isinstance(gains, list)

    def test_get_parameters(self, modular_smc):
        """Test parameter retrieval."""
        # Mock component parameter methods
        modular_smc._surface.get_coefficients.return_value = {'k1': 2.0, 'k2': 1.5}
        modular_smc._boundary_layer.get_parameters.return_value = {'thickness': 0.1}
        modular_smc.config.to_dict.return_value = {'gains': [2.0, 1.5, 3.0, 2.5]}
        
        params = modular_smc.get_parameters()
        
        assert isinstance(params, dict)
        assert 'gains' in params
        assert 'config' in params
        assert 'surface_params' in params
        assert 'boundary_layer_params' in params

    def test_error_handling(self, modular_smc):
        """Test error handling in control computation."""
        state = np.array([0.1, 0.2, 0.05, 0.1, -0.03, -0.05])
        state_vars = Mock()
        history = {}
        
        # Mock component failure
        modular_smc._surface.compute.side_effect = Exception("Surface computation failed")
        
        result = modular_smc.compute_control(state, state_vars, history)
        
        # Should return error result
        assert isinstance(result, dict)
        assert 'error' in result
        assert result['safe_mode'] is True
        assert result['u'] == 0.0


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Classical SMC modules not available")
class TestClassicalSMCBackwardCompatibility:
    """Test backward compatibility facade."""

    def test_initialization_legacy_interface(self):
        """Test initialization with legacy interface."""
        gains = [2.0, 1.5, 3.0, 2.5, 5.0, 0.1]
        max_force = 100.0
        boundary_layer = 0.1
        
        with patch('src.controllers.smc.algorithms.classical.controller.ModularClassicalSMC'):
            controller = ClassicalSMC(gains, max_force, boundary_layer)
            
            assert hasattr(controller, '_controller')
            assert hasattr(controller, 'gains')
            assert hasattr(controller, 'compute_control')

    def test_gains_property_delegation(self):
        """Test gains property delegates to modular controller."""
        gains = [2.0, 1.5, 3.0, 2.5, 5.0, 0.1]
        
        with patch('src.controllers.smc.algorithms.classical.controller.ModularClassicalSMC') as mock_modular:
            mock_modular.return_value.gains = gains
            controller = ClassicalSMC(gains, 100.0, 0.1)
            
            assert controller.gains == gains

    def test_compute_control_delegation(self):
        """Test compute_control delegates to modular controller."""
        gains = [2.0, 1.5, 3.0, 2.5, 5.0, 0.1]
        expected_result = {'u': 5.0, 'controller_type': 'classical_smc'}
        
        with patch('src.controllers.smc.algorithms.classical.controller.ModularClassicalSMC') as mock_modular:
            mock_modular.return_value.compute_control.return_value = expected_result
            controller = ClassicalSMC(gains, 100.0, 0.1)
            
            state = np.zeros(6)
            result = controller.compute_control(state, None, {})
            
            assert result == expected_result


class TestModularClassicalSMCFallback:
    """Test fallback behavior when imports are not available."""
    
    @pytest.mark.skipif(IMPORTS_AVAILABLE, reason="Test only when imports fail")
    def test_imports_not_available(self):
        """Test that we handle missing imports gracefully."""
        assert ModularClassicalSMC is None
        assert ClassicalSMC is None
        assert ClassicalSMCConfig is None
        assert IMPORTS_AVAILABLE is False