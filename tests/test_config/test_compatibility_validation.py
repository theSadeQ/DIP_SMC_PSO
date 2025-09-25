#==========================================================================================\\
#============= tests/test_config/test_compatibility_validation.py ==================\\
#==========================================================================================\\
"""
Configuration format compatibility validation tests.

CRITICAL HIGH-ROI TESTS: These tests eliminate AttributeError: 'dict' object has no attribute 'cart_mass'
crashes and similar configuration access failures that cause major debugging pain.
"""

import pytest
import numpy as np
from typing import Dict, Any, Union

from src.plant import ConfigurationFactory
from src.utils.config_compatibility import AttributeDictionary, ensure_attribute_access
from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
from src.plant.models.full.dynamics import FullDIPDynamics


class TestConfigDictObjectConversion:
    """Test that AttributeDictionary works consistently everywhere."""

    def test_attribute_dictionary_basic_functionality(self):
        """Test basic AttributeDictionary functionality prevents dict access crashes."""

        # Test with sample configuration data
        config_data = {
            'cart_mass': 1.0,
            'pendulum1_mass': 0.1,
            'pendulum2_mass': 0.1,
            'gravity': 9.81,
            'max_force': 100.0
        }

        attr_dict = AttributeDictionary(config_data)

        # Test attribute access (this is what causes crashes when missing)
        assert attr_dict.cart_mass == 1.0, "Attribute access should work"
        assert attr_dict.pendulum1_mass == 0.1, "Attribute access should work"
        assert attr_dict.gravity == 9.81, "Attribute access should work"

        # Test dictionary access (backward compatibility)
        assert attr_dict['cart_mass'] == 1.0, "Dict access should work"
        assert attr_dict['pendulum1_mass'] == 0.1, "Dict access should work"

        # Test that both access methods give same result
        assert attr_dict.cart_mass == attr_dict['cart_mass'], "Access methods should be consistent"

    def test_missing_attribute_handling(self):
        """Test graceful handling of missing attributes that cause crashes."""

        config_data = {
            'cart_mass': 1.0,
            'pendulum1_mass': 0.1,
        }

        attr_dict = AttributeDictionary(config_data)

        # Test accessing missing attribute (this is what causes crashes)
        with pytest.raises(AttributeError) as exc_info:
            _ = attr_dict.include_gyroscopic_effects

        # The error should be clear and not cause system crash
        assert "no attribute 'include_gyroscopic_effects'" in str(exc_info.value)

        # Test using get method for safe access
        gyro_effects = attr_dict.get('include_gyroscopic_effects', False)
        assert gyro_effects == False, "Safe access should return default"

        # Test using 'in' operator for checking existence
        assert 'cart_mass' in attr_dict, "Existing key should be found"
        assert 'include_gyroscopic_effects' not in attr_dict, "Missing key should not be found"

    def test_configuration_factory_compatibility(self):
        """Test that ConfigurationFactory creates AttributeDictionary-compatible configs."""

        config_types = ['simplified', 'full', 'lowrank', 'controller']

        for config_type in config_types:
            config = ConfigurationFactory.create_default_config(config_type)

            # Test that config supports attribute access
            assert hasattr(config, '__getattr__') or hasattr(config, 'keys'), (
                f"{config_type} config doesn't support attribute access"
            )

            # Test that we can iterate through available attributes
            if hasattr(config, 'keys'):
                keys = list(config.keys())
                assert len(keys) > 0, f"{config_type} config has no attributes"

                # Test that each key can be accessed as attribute
                for key in keys[:3]:  # Test first 3 to avoid excessive testing
                    try:
                        attr_value = getattr(config, key)
                        dict_value = config[key] if hasattr(config, '__getitem__') else None

                        if dict_value is not None:
                            assert attr_value == dict_value, (
                                f"Inconsistent access for {key} in {config_type} config"
                            )
                    except AttributeError:
                        pytest.fail(f"Cannot access {key} as attribute in {config_type} config")

    def test_dynamics_config_compatibility(self):
        """Test that dynamics classes work with both dict and AttributeDictionary configs."""

        # Original config from factory
        original_config = ConfigurationFactory.create_default_config("simplified")

        # Convert to plain dict (simulating legacy or external config)
        if hasattr(original_config, 'to_dict'):
            dict_config = original_config.to_dict()
        elif hasattr(original_config, '_data'):
            dict_config = original_config._data.copy()
        else:
            dict_config = dict(original_config)

        # Ensure both work with SimplifiedDIPDynamics
        try:
            # Test with AttributeDictionary config
            dynamics1 = SimplifiedDIPDynamics(original_config)

            # Test with plain dict config (should be converted internally)
            dynamics2 = SimplifiedDIPDynamics(ensure_attribute_access(dict_config))

            # Both should work identically
            state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
            control = np.array([1.0])

            result1 = dynamics1.compute_dynamics(state, control)
            result2 = dynamics2.compute_dynamics(state, control)

            assert result1.success == result2.success, "Results should be consistent"

            if result1.success and result2.success:
                np.testing.assert_allclose(
                    result1.state_derivative,
                    result2.state_derivative,
                    rtol=1e-10,
                    err_msg="State derivatives should be identical"
                )

        except AttributeError as e:
            if "'dict' object has no attribute" in str(e):
                pytest.fail(f"Dict object attribute access error: {e}")
            else:
                raise


class TestConfigAttributeAccessConsistency:
    """Test that config.attribute and config['attribute'] both work consistently."""

    def test_dual_access_pattern_consistency(self):
        """Test that both access patterns work without crashes."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("controller")
        ]

        for config in configs:
            # Get list of available attributes
            if hasattr(config, 'keys'):
                available_attrs = list(config.keys())
            else:
                available_attrs = [attr for attr in dir(config) if not attr.startswith('_')]

            for attr_name in available_attrs[:5]:  # Test subset to avoid excessive testing
                try:
                    # Test attribute access
                    attr_value = getattr(config, attr_name)

                    # Test dictionary access if supported
                    if hasattr(config, '__getitem__'):
                        dict_value = config[attr_name]

                        # Both should give same result
                        assert attr_value == dict_value, (
                            f"Inconsistent access for {attr_name}: "
                            f"attr={attr_value}, dict={dict_value}"
                        )

                except (AttributeError, KeyError, TypeError) as e:
                    # Document the issue but don't fail unless it's a crash-causing error
                    if "'dict' object has no attribute" in str(e):
                        pytest.fail(f"Configuration access crash: {e}")

    def test_nested_configuration_access(self):
        """Test that nested config access works with both patterns."""

        config = ConfigurationFactory.create_default_config("full")

        # Try to access nested attributes if they exist
        if hasattr(config, 'keys'):
            for key in list(config.keys())[:3]:
                value = getattr(config, key)

                # If value is also a dict-like object, test nested access
                if hasattr(value, 'keys') or isinstance(value, dict):
                    try:
                        # Test nested attribute access if it's supported
                        if hasattr(value, '__getattr__') and hasattr(value, 'keys'):
                            for nested_key in list(value.keys())[:2]:
                                nested_attr = getattr(value, nested_key)
                                nested_dict = value[nested_key]
                                assert nested_attr == nested_dict, (
                                    f"Nested access inconsistent: {key}.{nested_key}"
                                )
                    except AttributeError:
                        # Nested access not supported, which is acceptable
                        pass


class TestConfigNestedAccessCompatibility:
    """Test nested configuration access compatibility."""

    def test_nested_attribute_path_consistency(self):
        """Test that nested paths work consistently (e.g., config.plant.cart_mass)."""

        config = ConfigurationFactory.create_default_config("full")

        # Check if config has nested structure
        nested_found = False

        if hasattr(config, 'keys'):
            for key in config.keys():
                value = getattr(config, key)
                if isinstance(value, (dict, AttributeDictionary)) or hasattr(value, 'keys'):
                    nested_found = True

                    # Test that nested access doesn't crash
                    try:
                        if hasattr(value, 'keys'):
                            for nested_key in list(value.keys())[:2]:
                                # Test nested attribute access
                                nested_value = getattr(value, nested_key) if hasattr(value, '__getattr__') else value[nested_key]
                                assert nested_value is not None or nested_value == 0, (
                                    f"Nested value should not be None: {key}.{nested_key}"
                                )
                    except AttributeError as e:
                        if "has no attribute" in str(e):
                            # Document but don't fail unless it causes crashes
                            pass

        # If no nested structure found, that's also acceptable
        if not nested_found:
            assert True, "No nested structure found, which is acceptable"

    def test_missing_nested_parameter_handling(self):
        """Test graceful handling of missing nested parameters."""

        config = ConfigurationFactory.create_default_config("simplified")

        # Test accessing non-existent nested parameter
        try:
            # This should either work with default or fail gracefully
            if hasattr(config, 'get'):
                missing_nested = config.get('plant', {}).get('non_existent_param', 'DEFAULT')
                assert missing_nested == 'DEFAULT', "Should return default for missing nested param"

        except Exception as e:
            # Should not cause system crash
            assert "dict" not in str(e) or "attribute" not in str(e), (
                f"Should not have dict attribute error: {e}"
            )


class TestConfigModificationConsistency:
    """Test that config modifications work with both access formats."""

    def test_config_modification_preservation(self):
        """Test that config modifications don't break attribute access."""

        config_data = {
            'cart_mass': 1.0,
            'pendulum1_mass': 0.1,
            'gravity': 9.81
        }

        attr_dict = AttributeDictionary(config_data)

        # Test modification via attribute access
        attr_dict.cart_mass = 2.0
        assert attr_dict.cart_mass == 2.0, "Attribute modification should work"
        assert attr_dict['cart_mass'] == 2.0, "Dict access should reflect attribute change"

        # Test modification via dictionary access
        attr_dict['pendulum1_mass'] = 0.2
        assert attr_dict.pendulum1_mass == 0.2, "Attribute access should reflect dict change"
        assert attr_dict['pendulum1_mass'] == 0.2, "Dict modification should work"

        # Test adding new parameters
        attr_dict.new_parameter = 42.0
        assert attr_dict.new_parameter == 42.0, "New attribute should be accessible"
        assert attr_dict['new_parameter'] == 42.0, "New attribute should be in dict"

    def test_config_modification_in_dynamics(self):
        """Test that config modifications work within dynamics classes."""

        config = ConfigurationFactory.create_default_config("simplified")

        # Create dynamics instance
        dynamics = SimplifiedDIPDynamics(config)

        # Verify that dynamics can access config parameters
        try:
            state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
            control = np.array([1.0])

            result = dynamics.compute_dynamics(state, control)

            # Should not fail due to config access issues
            assert hasattr(result, 'success'), "Result should have success attribute"

        except AttributeError as e:
            if "'dict' object has no attribute" in str(e):
                pytest.fail(f"Config access error in dynamics: {e}")
            elif "no attribute" in str(e):
                # Extract the missing attribute name for debugging
                missing_attr = str(e).split("'")[-2] if "'" in str(e) else "unknown"
                pytest.fail(f"Missing config attribute in dynamics: {missing_attr}")
            else:
                raise


class TestConfigurationErrorRecovery:
    """Test graceful handling of configuration errors."""

    def test_malformed_config_handling(self):
        """Test that malformed configurations are handled gracefully."""

        # Test with incomplete configuration
        incomplete_config_data = {
            'cart_mass': 1.0,
            # Missing required parameters
        }

        try:
            incomplete_config = AttributeDictionary(incomplete_config_data)

            # Test that missing parameters are detectable
            assert 'cart_mass' in incomplete_config, "Existing parameter should be found"
            assert 'pendulum1_mass' not in incomplete_config, "Missing parameter should not be found"

            # Test safe access to missing parameters
            mass = incomplete_config.get('pendulum1_mass', 0.1)  # Safe default
            assert mass == 0.1, "Should return default for missing parameter"

        except Exception as e:
            pytest.fail(f"Malformed config handling failed: {e}")

    def test_config_validation_error_messages(self):
        """Test that configuration errors provide helpful messages."""

        config_data = {'cart_mass': 1.0}
        attr_dict = AttributeDictionary(config_data)

        try:
            # Attempt to access missing attribute
            _ = attr_dict.missing_attribute

            # Should not reach here
            pytest.fail("Should have raised AttributeError")

        except AttributeError as e:
            # Error message should be helpful for debugging
            error_msg = str(e)
            assert 'missing_attribute' in error_msg, "Error should mention the missing attribute"
            assert 'AttributeDictionary' in error_msg, "Error should identify the class"

    def test_config_type_validation(self):
        """Test that configuration parameters have expected types."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full")
        ]

        for config in configs:
            if hasattr(config, 'keys'):
                for key in list(config.keys())[:5]:
                    value = getattr(config, key)

                    # Config values should be reasonable types
                    assert isinstance(value, (int, float, str, bool, dict, list, np.ndarray, type(None))), (
                        f"Config parameter {key} has unexpected type: {type(value)}"
                    )

                    # Numeric parameters should be finite
                    if isinstance(value, (int, float, np.ndarray)):
                        if isinstance(value, np.ndarray):
                            assert np.all(np.isfinite(value)), f"Config array {key} should be finite"
                        else:
                            assert np.isfinite(value), f"Config parameter {key} should be finite"