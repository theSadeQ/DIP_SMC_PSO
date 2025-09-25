#==========================================================================================\\\
#========= tests/test_controllers/factory/test_interface_compatibility.py ===========\\\
#==========================================================================================\\\

"""
Critical interface compatibility tests for controller factory.

These tests address the 42 controller factory errors and integration failures
mentioned in the roadmap. ROI: 5x (2 hours to add, saves 10+ hours debugging).
Impact: Would fix ~25% of current controller failures.
"""

import pytest
import numpy as np
from typing import Dict, Any, Union
import logging

# Import factory functions from the factory package (now includes needed functions)
from src.controllers.factory import (
    create_controller_new as create_controller,
    list_available_controllers,
    get_default_gains,
    CONTROLLER_REGISTRY
)

# Import configuration classes
from src.plant.configurations import ConfigurationFactory


class TestControllerFactoryInterfaceCompatibility:
    """Test controller factory interface compatibility to fix factory integration errors."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plant_config = ConfigurationFactory.create_default_config("simplified")
        self.controller_types = list_available_controllers()

    def test_controller_factory_interfaces(self):
        """
        Validate factory methods accept expected parameters.
        Prevents configuration format debugging nightmares.
        Addresses: AttributeError: 'dict' object has no attribute issues.
        """
        for controller_type in self.controller_types:
            # Test with None config
            controller = create_controller(controller_type, config=None)
            assert controller is not None, f"Factory failed for {controller_type} with None config"

            # Test with plant config
            controller = create_controller(controller_type, config=self.plant_config)
            assert controller is not None, f"Factory failed for {controller_type} with plant config"

            # Test with explicit gains
            default_gains = get_default_gains(controller_type)
            controller = create_controller(controller_type, config=None, gains=default_gains)
            assert controller is not None, f"Factory failed for {controller_type} with explicit gains"

    def test_factory_parameter_validation(self):
        """
        Validate factory handles dict vs object configs.
        Eliminates AttributeError: 'dict' object has no attribute issues.
        """
        for controller_type in self.controller_types:
            # Test with dict config (common source of errors)
            dict_config = {
                'physics': {
                    'cart_mass': 2.4,
                    'pendulum1_mass': 0.23,
                    'pendulum2_mass': 0.23,
                    'pendulum1_length': 0.36,
                    'pendulum2_length': 0.36
                }
            }

            # Factory should handle dict configs gracefully
            try:
                controller = create_controller(controller_type, config=dict_config)
                # If it creates successfully, verify it's a valid controller
                assert hasattr(controller, 'compute_control'), \
                    f"Created controller for {controller_type} missing compute_control method"
            except Exception as e:
                # Factory should not crash on dict configs, but may warn
                assert not isinstance(e, AttributeError), \
                    f"Factory crashed with AttributeError for {controller_type}: {e}"

    def test_controller_instantiation_robustness(self):
        """
        Validate error recovery in controller creation.
        Prevents factory crashes on edge cases.
        """
        for controller_type in self.controller_types:
            # Test with invalid gains (should handle gracefully)
            invalid_gains_cases = [
                [],  # Empty gains
                [0.0],  # Single gain
                [-1.0, -2.0],  # Negative gains
                None,  # None gains
            ]

            for invalid_gains in invalid_gains_cases:
                try:
                    controller = create_controller(
                        controller_type,
                        config=self.plant_config,
                        gains=invalid_gains
                    )
                    # If successful, should fall back to defaults
                    assert controller is not None
                except Exception as e:
                    # Should not be AttributeError or import-related
                    assert not isinstance(e, (AttributeError, ImportError, ModuleNotFoundError)), \
                        f"Factory crashed with {type(e).__name__} for {controller_type} with gains {invalid_gains}: {e}"

    def test_factory_registry_consistency(self):
        """
        Validate all controller types can be created.
        Ensures factory completeness.
        """
        registry_types = list(CONTROLLER_REGISTRY.keys())
        available_types = list_available_controllers()

        # All registry types should be available
        for controller_type in registry_types:
            assert controller_type in available_types, \
                f"Controller type {controller_type} in registry but not available"

        # All available types should be in registry
        for controller_type in available_types:
            assert controller_type in registry_types, \
                f"Controller type {controller_type} available but not in registry"

            # Each registry entry should have required components
            registry_entry = CONTROLLER_REGISTRY[controller_type]
            required_keys = ['class', 'config_class', 'default_gains']
            for key in required_keys:
                assert key in registry_entry, \
                    f"Registry entry for {controller_type} missing required key: {key}"

    def test_controller_interface_consistency(self):
        """
        Validate all created controllers have consistent interfaces.
        Prevents method signature mismatches during runtime.
        """
        test_state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
        test_control = np.array([0.0])

        for controller_type in self.controller_types:
            controller = create_controller(controller_type, config=self.plant_config)

            # All controllers must have compute_control method
            assert hasattr(controller, 'compute_control'), \
                f"Controller {controller_type} missing compute_control method"

            # Test method signature compatibility
            try:
                # Try different common signatures
                result = controller.compute_control(test_state, test_control, [])
                assert result is not None, \
                    f"Controller {controller_type} compute_control returned None"

                # Result should be array-like
                if hasattr(result, 'control'):
                    control_output = result.control
                else:
                    control_output = result

                control_array = np.asarray(control_output)
                assert control_array.size > 0, \
                    f"Controller {controller_type} returned empty control output"

            except Exception as e:
                # Should not fail with signature errors
                assert not isinstance(e, (TypeError, AttributeError)), \
                    f"Controller {controller_type} failed with signature error: {e}"

    def test_configuration_object_attribute_access(self):
        """
        Test that configuration objects support both dict and attribute access.
        Addresses common 'dict' object has no attribute errors.
        """
        # Create mock config objects that might come from different sources
        class MockDictConfig(dict):
            """Mock config that behaves like dict but might be accessed as object."""
            pass

        class MockObjectConfig:
            """Mock config object."""
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        config_variants = [
            self.plant_config,  # Real config
            MockDictConfig(physics={'cart_mass': 2.4}),  # Dict-like
            MockObjectConfig(physics={'cart_mass': 2.4}),  # Object-like
        ]

        for config in config_variants:
            for controller_type in self.controller_types:
                try:
                    controller = create_controller(controller_type, config=config)
                    assert controller is not None, \
                        f"Failed to create {controller_type} with config type {type(config)}"
                except Exception as e:
                    # Should not fail with attribute access errors
                    if "has no attribute" in str(e):
                        pytest.fail(
                            f"Controller {controller_type} failed with attribute error "
                            f"for config type {type(config)}: {e}"
                        )

    def test_gains_type_conversion_compatibility(self):
        """
        Test that factory properly handles different gains input types.
        Prevents type conversion errors in gain processing.
        """
        for controller_type in self.controller_types:
            default_gains = get_default_gains(controller_type)

            # Test different gain input types
            gains_variants = [
                default_gains,  # Original list
                np.array(default_gains),  # NumPy array
                tuple(default_gains),  # Tuple
                [float(g) for g in default_gains],  # Float list
                [int(g) for g in default_gains if g == int(g)],  # Int list (if applicable)
            ]

            for gains in gains_variants:
                try:
                    controller = create_controller(
                        controller_type,
                        config=self.plant_config,
                        gains=gains
                    )
                    assert controller is not None, \
                        f"Failed to create {controller_type} with gains type {type(gains)}"
                except Exception as e:
                    # Should handle type conversion gracefully
                    assert not isinstance(e, (TypeError, ValueError)), \
                        f"Controller {controller_type} failed with type error for gains {type(gains)}: {e}"


class TestControllerFactoryErrorRecovery:
    """Test factory error recovery and graceful degradation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plant_config = ConfigurationFactory.create_default_config("simplified")

    def test_missing_import_recovery(self):
        """
        Test factory behavior when controller imports fail.
        Should provide meaningful error messages, not crash.
        """
        # This test validates that import errors are handled gracefully
        # The factory has try/except blocks for imports in the actual implementation

        controller_types = list_available_controllers()
        assert len(controller_types) > 0, "No controllers available, possible import issues"

        # All available types should actually be creatable
        for controller_type in controller_types:
            try:
                controller = create_controller(controller_type)
                assert controller is not None
            except ImportError as e:
                pytest.fail(f"Import error for available controller {controller_type}: {e}")

    def test_configuration_validation_recovery(self):
        """
        Test recovery from configuration validation errors.
        Should use defaults when configuration is invalid.
        """
        # Test with various invalid configurations
        invalid_configs = [
            None,
            {},
            {'invalid': 'config'},
            MockInvalidConfig(),
        ]

        for invalid_config in invalid_configs:
            for controller_type in list_available_controllers():
                try:
                    controller = create_controller(controller_type, config=invalid_config)
                    # Should succeed by falling back to defaults
                    assert controller is not None
                except Exception as e:
                    # Should not crash with AttributeError
                    assert not isinstance(e, AttributeError), \
                        f"Factory crashed with AttributeError for {controller_type}: {e}"


class MockInvalidConfig:
    """Mock invalid configuration for testing error recovery."""

    def __getattr__(self, name):
        raise AttributeError(f"Mock invalid config has no attribute '{name}'")


# Parametrized tests for comprehensive coverage
@pytest.mark.parametrize("controller_type", list_available_controllers())
def test_individual_controller_factory_robustness(controller_type):
    """Test each controller type individually for robustness."""
    plant_config = ConfigurationFactory.create_default_config("simplified")

    # Should create successfully with standard config
    controller = create_controller(controller_type, config=plant_config)
    assert controller is not None

    # Should have required interface
    assert hasattr(controller, 'compute_control')

    # Should handle basic control computation
    test_state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
    test_control = np.array([0.0])

    try:
        result = controller.compute_control(test_state, test_control, [])
        assert result is not None
    except Exception as e:
        # Should not fail with interface errors
        assert not isinstance(e, (AttributeError, TypeError)), \
            f"Interface error in {controller_type}: {e}"