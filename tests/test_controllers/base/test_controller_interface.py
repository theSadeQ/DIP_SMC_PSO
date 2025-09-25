#==========================================================================================\\\
#============ tests/test_controllers/base/test_controller_interface.py ===================\\\
#==========================================================================================\\\

"""
Tests for Controller Base Interface.
SINGLE JOB: Test only the abstract controller interface contract and base functionality.
"""

import pytest
import numpy as np
from abc import ABC
from typing import Optional

from src.controllers.base.controller_interface import ControllerInterface


class TestControllerInterface:
    """Test suite for ControllerInterface abstract base class."""

    def test_abstract_class_instantiation_fails(self):
        """Test that ControllerInterface cannot be directly instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ControllerInterface()

    def test_abstract_methods_defined(self):
        """Test that all required abstract methods are defined."""
        abstract_methods = ControllerInterface.__abstractmethods__

        expected_methods = {'compute_control', 'reset'}
        assert abstract_methods == expected_methods

    def test_inheritance_structure(self):
        """Test that ControllerInterface properly inherits from ABC."""
        assert issubclass(ControllerInterface, ABC)
        assert hasattr(ControllerInterface, '__abstractmethods__')


class ConcreteTestController(ControllerInterface):
    """Minimal concrete implementation for testing base functionality."""

    def __init__(self, max_force: float = 20.0, dt: float = 0.01):
        super().__init__(max_force, dt)
        self.last_control = 0.0
        self.call_count = 0

    def compute_control(self, state: np.ndarray, reference: Optional[np.ndarray] = None) -> float:
        """Simple test implementation: return negative state[0]."""
        self.call_count += 1
        control = -state[0]  # Simple proportional control on cart position
        self.last_control = control
        return control

    def reset(self) -> None:
        """Reset test controller state."""
        self.last_control = 0.0
        self.call_count = 0
        self._reset_state()

    def step(self, state, reference=None):
        """Step method with saturation."""
        control_raw = self.compute_control(state, reference)
        # Simple saturation
        control = max(-self.max_force, min(self.max_force, control_raw))
        saturated = abs(control_raw) > self.max_force

        return control, {
            'control_raw': control_raw,
            'saturated': saturated
        }

    def _reset_state(self):
        """Reset internal state (placeholder for base class method)."""
        pass

    @property
    def parameters(self):
        """Get controller parameters."""
        return {
            'max_force': self.max_force,
            'dt': self.dt
        }


class TestConcreteControllerBase:
    """Test base controller functionality through concrete implementation."""

    @pytest.fixture
    def controller(self):
        """Create a test controller instance."""
        return ConcreteTestController()

    @pytest.fixture
    def test_state(self):
        """Create a valid test state vector."""
        return np.array([0.1, 0.0, 0.05, 0.0, -0.02, 0.0])

    def test_initialization_default_parameters(self):
        """Test controller initialization with default parameters."""
        controller = ConcreteTestController()

        assert controller.max_force == 20.0
        assert controller.dt == 0.01
        assert controller.last_control == 0.0
        assert controller.call_count == 0

    def test_initialization_custom_parameters(self):
        """Test controller initialization with custom parameters."""
        max_force = 15.0
        dt = 0.02

        controller = ConcreteTestController(max_force=max_force, dt=dt)

        assert controller.max_force == max_force
        assert controller.dt == dt

    def test_compute_control_basic_functionality(self, controller, test_state):
        """Test basic compute_control functionality."""
        control = controller.compute_control(test_state)

        # Should return -state[0] based on our test implementation
        assert control == -test_state[0]
        assert controller.call_count == 1
        assert controller.last_control == control

    def test_compute_control_with_reference(self, controller, test_state):
        """Test compute_control with reference state."""
        reference = np.zeros(6)  # Upright equilibrium

        control = controller.compute_control(test_state, reference)

        # Reference is passed but our simple implementation ignores it
        assert control == -test_state[0]
        assert controller.call_count == 1

    def test_step_basic_functionality(self, controller, test_state):
        """Test step method basic functionality."""
        control, info = controller.step(test_state)

        # Should return control value and info dict
        expected_control = -test_state[0]  # Based on our implementation
        assert control == expected_control
        assert isinstance(info, dict)
        assert 'saturated' in info
        assert 'control_raw' in info
        assert info['control_raw'] == expected_control
        assert info['saturated'] == False  # Small control value shouldn't saturate

    def test_step_with_reference(self, controller, test_state):
        """Test step method with reference state."""
        reference = np.zeros(6)

        control, info = controller.step(test_state, reference)

        assert control == -test_state[0]
        assert info['control_raw'] == -test_state[0]

    def test_force_saturation_positive(self, controller):
        """Test control force saturation for positive values."""
        large_state = np.array([50.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # Large positive position

        control, info = controller.step(large_state)

        # Should be saturated to -max_force (negative because of our -state[0] implementation)
        assert control == -controller.max_force
        assert info['saturated'] == True
        assert info['control_raw'] == -large_state[0]  # Raw value before saturation

    def test_force_saturation_negative(self, controller):
        """Test control force saturation for negative values."""
        large_state = np.array([-50.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # Large negative position

        control, info = controller.step(large_state)

        # Should be saturated to +max_force (positive because of our -state[0] implementation)
        assert control == controller.max_force
        assert info['saturated'] == True
        assert info['control_raw'] == -large_state[0]  # Raw value before saturation

    def test_force_saturation_boundary(self, controller):
        """Test force saturation exactly at boundaries."""
        # Test exactly at positive boundary
        boundary_state = np.array([-20.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        control, info = controller.step(boundary_state)

        assert control == controller.max_force
        assert info['saturated'] == True

        # Test exactly at negative boundary
        boundary_state = np.array([20.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        control, info = controller.step(boundary_state)

        assert control == -controller.max_force
        assert info['saturated'] == True

    def test_reset_functionality(self, controller, test_state):
        """Test controller reset functionality."""
        # Change controller state
        controller.compute_control(test_state)
        assert controller.call_count == 1
        assert controller.last_control != 0.0

        # Reset and verify state is cleared
        controller.reset()
        assert controller.call_count == 0
        assert controller.last_control == 0.0

    def test_parameters_property(self, controller):
        """Test parameters property returns correct values."""
        params = controller.parameters

        assert isinstance(params, dict)
        assert params['max_force'] == controller.max_force
        assert params['dt'] == controller.dt
        assert len(params) == 2

    def test_string_representation(self, controller):
        """Test string representation of controller."""
        repr_str = repr(controller)

        assert 'ConcreteTestController' in repr_str
        assert f'max_force={controller.max_force}' in repr_str
        assert f'dt={controller.dt}' in repr_str

    def test_custom_max_force_saturation(self):
        """Test saturation with custom max_force value."""
        max_force = 10.0
        controller = ConcreteTestController(max_force=max_force)
        large_state = np.array([50.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        control, info = controller.step(large_state)

        assert control == -max_force  # Should saturate to custom limit
        assert info['saturated'] == True


class TestControllerInterfaceEdgeCases:
    """Test edge cases and error conditions for controller interface."""

    @pytest.fixture
    def controller(self):
        """Create a test controller instance."""
        return ConcreteTestController()

    def test_invalid_state_dimensions(self, controller):
        """Test behavior with invalid state dimensions."""
        # Too few dimensions
        invalid_state = np.array([0.1, 0.2])

        # Should still work but may produce unexpected results
        # (Input validation is controller-specific, not interface requirement)
        control = controller.compute_control(invalid_state)
        assert isinstance(control, (float, np.floating))

    def test_nan_state_handling(self, controller):
        """Test behavior with NaN values in state."""
        nan_state = np.array([np.nan, 0.0, 0.0, 0.0, 0.0, 0.0])

        # Should handle NaN (result depends on implementation)
        control = controller.compute_control(nan_state)
        # NaN input should produce NaN output in our test implementation
        assert np.isnan(control)

    def test_infinite_state_handling(self, controller):
        """Test behavior with infinite values in state."""
        inf_state = np.array([np.inf, 0.0, 0.0, 0.0, 0.0, 0.0])

        control, info = controller.step(inf_state)

        # Step method should still saturate infinite control values
        assert np.isfinite(control)
        assert abs(control) <= controller.max_force
        assert info['saturated'] == True

    def test_zero_max_force_edge_case(self):
        """Test edge case with zero max_force."""
        controller = ConcreteTestController(max_force=0.0)
        test_state = np.array([0.1, 0.0, 0.0, 0.0, 0.0, 0.0])

        control, info = controller.step(test_state)

        # Should saturate to zero
        assert control == 0.0
        assert info['saturated'] == True  # Any non-zero control would be saturated

    def test_negative_max_force_behavior(self):
        """Test behavior with negative max_force (edge case)."""
        controller = ConcreteTestController(max_force=-5.0)
        test_state = np.array([0.1, 0.0, 0.0, 0.0, 0.0, 0.0])

        control, info = controller.step(test_state)

        # np.clip with inverted bounds should handle this appropriately
        assert abs(control) <= abs(controller.max_force)


class TestControllerInterfaceDocumentation:
    """Test that controller interface is properly documented."""

    def test_class_docstring_exists(self):
        """Test that ControllerInterface has proper docstring."""
        assert ControllerInterface.__doc__ is not None
        assert len(ControllerInterface.__doc__.strip()) > 0
        assert 'Abstract base class' in ControllerInterface.__doc__

    def test_abstract_methods_documented(self):
        """Test that abstract methods have docstrings."""
        assert ControllerInterface.compute_control.__doc__ is not None
        assert ControllerInterface.reset.__doc__ is not None

        # Check for parameter documentation
        compute_control_doc = ControllerInterface.compute_control.__doc__
        assert 'Parameters' in compute_control_doc
        assert 'Returns' in compute_control_doc
        assert 'state' in compute_control_doc

    def test_concrete_methods_documented(self):
        """Test that concrete methods have docstrings."""
        assert ControllerInterface.step.__doc__ is not None
        assert ControllerInterface.parameters.__doc__ is not None

        # Check step method documentation
        step_doc = ControllerInterface.step.__doc__
        assert 'Parameters' in step_doc
        assert 'Returns' in step_doc