#==========================================================================================\\\
#============ tests/test_controllers/base/test_control_primitives.py =====================\\\
#==========================================================================================\\\

"""
Tests for Control Primitives.
SINGLE JOB: Test only the control primitive functions for validation and saturation.
"""

import pytest
import numpy as np
import math
import warnings

from src.controllers.base.control_primitives import (
    require_positive,
    require_in_range,
    saturate
)


class TestRequirePositive:
    """Test suite for require_positive validation function."""

    def test_valid_positive_float(self):
        """Test validation of valid positive float values."""
        result = require_positive(5.0, "test_param")
        assert result == 5.0
        assert isinstance(result, float)

    def test_valid_positive_int(self):
        """Test validation of valid positive integer values."""
        result = require_positive(10, "test_param")
        assert result == 10.0
        assert isinstance(result, float)

    def test_zero_not_allowed_by_default(self):
        """Test that zero is rejected by default."""
        with pytest.raises(ValueError, match="test_param must be > 0; got 0"):
            require_positive(0.0, "test_param")

    def test_zero_allowed_when_specified(self):
        """Test that zero is accepted when allow_zero=True."""
        result = require_positive(0.0, "test_param", allow_zero=True)
        assert result == 0.0

    def test_small_positive_value(self):
        """Test validation of very small positive values."""
        small_value = 1e-10
        result = require_positive(small_value, "test_param")
        assert result == small_value

    def test_negative_value_rejected(self):
        """Test that negative values are rejected."""
        with pytest.raises(ValueError, match="test_param must be > 0; got -5.0"):
            require_positive(-5.0, "test_param")

    def test_negative_value_rejected_with_allow_zero(self):
        """Test that negative values are rejected even with allow_zero=True."""
        with pytest.raises(ValueError, match="test_param must be ≥ 0; got -1.0"):
            require_positive(-1.0, "test_param", allow_zero=True)

    def test_none_value_rejected(self):
        """Test that None values are rejected."""
        with pytest.raises(ValueError, match="test_param must be a finite number; got None"):
            require_positive(None, "test_param")

    def test_infinity_rejected(self):
        """Test that infinite values are rejected."""
        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_positive(float('inf'), "test_param")

        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_positive(float('-inf'), "test_param")

    def test_nan_rejected(self):
        """Test that NaN values are rejected."""
        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_positive(float('nan'), "test_param")

    def test_string_rejected(self):
        """Test that string values are rejected."""
        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_positive("5.0", "test_param")

    def test_custom_parameter_name_in_error(self):
        """Test that custom parameter names appear in error messages."""
        with pytest.raises(ValueError, match="control_gain must be > 0"):
            require_positive(-1.0, "control_gain")

    def test_boundary_value_edge_case(self):
        """Test behavior at the boundary of floating point precision."""
        tiny_positive = np.finfo(float).eps
        result = require_positive(tiny_positive, "test_param")
        assert result == tiny_positive

    def test_large_positive_value(self):
        """Test validation of very large positive values."""
        large_value = 1e100
        result = require_positive(large_value, "test_param")
        assert result == large_value


class TestRequireInRange:
    """Test suite for require_in_range validation function."""

    def test_value_within_range(self):
        """Test validation of value within range."""
        result = require_in_range(5.0, "test_param", minimum=0.0, maximum=10.0)
        assert result == 5.0
        assert isinstance(result, float)

    def test_value_at_boundaries_inclusive(self):
        """Test validation at boundaries with inclusive bounds."""
        # Test lower boundary
        result = require_in_range(0.0, "test_param", minimum=0.0, maximum=10.0, allow_equal=True)
        assert result == 0.0

        # Test upper boundary
        result = require_in_range(10.0, "test_param", minimum=0.0, maximum=10.0, allow_equal=True)
        assert result == 10.0

    def test_value_at_boundaries_exclusive(self):
        """Test validation at boundaries with exclusive bounds."""
        # Test lower boundary rejection
        with pytest.raises(ValueError, match="test_param must satisfy 0.0 < test_param < 10.0"):
            require_in_range(0.0, "test_param", minimum=0.0, maximum=10.0, allow_equal=False)

        # Test upper boundary rejection
        with pytest.raises(ValueError, match="test_param must satisfy 0.0 < test_param < 10.0"):
            require_in_range(10.0, "test_param", minimum=0.0, maximum=10.0, allow_equal=False)

    def test_value_below_minimum(self):
        """Test rejection of values below minimum."""
        with pytest.raises(ValueError, match="test_param must be in the interval \\[0.0, 10.0\\]"):
            require_in_range(-1.0, "test_param", minimum=0.0, maximum=10.0)

    def test_value_above_maximum(self):
        """Test rejection of values above maximum."""
        with pytest.raises(ValueError, match="test_param must be in the interval \\[0.0, 10.0\\]"):
            require_in_range(11.0, "test_param", minimum=0.0, maximum=10.0)

    def test_integer_input_converted_to_float(self):
        """Test that integer inputs are converted to float."""
        result = require_in_range(5, "test_param", minimum=0.0, maximum=10.0)
        assert result == 5.0
        assert isinstance(result, float)

    def test_none_value_rejected(self):
        """Test that None values are rejected."""
        with pytest.raises(ValueError, match="test_param must be a finite number; got None"):
            require_in_range(None, "test_param", minimum=0.0, maximum=10.0)

    def test_infinite_values_rejected(self):
        """Test that infinite values are rejected."""
        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_in_range(float('inf'), "test_param", minimum=0.0, maximum=10.0)

    def test_nan_values_rejected(self):
        """Test that NaN values are rejected."""
        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_in_range(float('nan'), "test_param", minimum=0.0, maximum=10.0)

    def test_negative_range(self):
        """Test validation with negative ranges."""
        result = require_in_range(-5.0, "test_param", minimum=-10.0, maximum=-1.0)
        assert result == -5.0

    def test_zero_width_range_exclusive(self):
        """Test behavior with zero-width range and exclusive bounds."""
        with pytest.raises(ValueError):
            require_in_range(5.0, "test_param", minimum=5.0, maximum=5.0, allow_equal=False)

    def test_zero_width_range_inclusive(self):
        """Test behavior with zero-width range and inclusive bounds."""
        result = require_in_range(5.0, "test_param", minimum=5.0, maximum=5.0, allow_equal=True)
        assert result == 5.0

    def test_inverted_bounds_edge_case(self):
        """Test edge case where minimum > maximum."""
        # This should fail since no value can satisfy min > max
        with pytest.raises(ValueError):
            require_in_range(5.0, "test_param", minimum=10.0, maximum=5.0)

    def test_custom_parameter_name_in_error(self):
        """Test that custom parameter names appear in error messages."""
        with pytest.raises(ValueError, match="adaptation_gain must be in the interval"):
            require_in_range(15.0, "adaptation_gain", minimum=0.0, maximum=10.0)


class TestSaturate:
    """Test suite for saturate function."""

    def test_tanh_saturation_basic(self):
        """Test basic tanh saturation functionality."""
        result = saturate(1.0, epsilon=1.0, method="tanh")
        expected = np.tanh(1.0)
        assert abs(result - expected) < 1e-10

    def test_linear_saturation_basic(self):
        """Test basic linear saturation functionality."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # Suppress expected warning
            result = saturate(1.5, epsilon=1.0, method="linear")
            assert result == 1.0  # Should clip to 1.0

    def test_linear_saturation_warning(self):
        """Test that linear saturation issues a warning."""
        with pytest.warns(RuntimeWarning, match="linear.*chattering performance"):
            saturate(1.0, epsilon=1.0, method="linear")

    def test_zero_input_tanh(self):
        """Test tanh saturation with zero input."""
        result = saturate(0.0, epsilon=1.0, method="tanh")
        assert result == 0.0

    def test_zero_input_linear(self):
        """Test linear saturation with zero input."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            result = saturate(0.0, epsilon=1.0, method="linear")
            assert result == 0.0

    def test_array_input_tanh(self):
        """Test tanh saturation with array input."""
        sigma = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
        epsilon = 1.0
        result = saturate(sigma, epsilon, method="tanh")
        expected = np.tanh(sigma / epsilon)

        assert isinstance(result, np.ndarray)
        assert result.shape == sigma.shape
        np.testing.assert_array_almost_equal(result, expected)

    def test_array_input_linear(self):
        """Test linear saturation with array input."""
        sigma = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
        epsilon = 1.0

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            result = saturate(sigma, epsilon, method="linear")

        expected = np.array([-1.0, -1.0, 0.0, 1.0, 1.0])

        assert isinstance(result, np.ndarray)
        assert result.shape == sigma.shape
        np.testing.assert_array_almost_equal(result, expected)

    def test_different_epsilon_values(self):
        """Test saturation with different epsilon values."""
        sigma = 2.0

        # Smaller epsilon should result in stronger saturation
        result_small = saturate(sigma, epsilon=0.5, method="tanh")
        result_large = saturate(sigma, epsilon=2.0, method="tanh")

        # Both should be positive, but result_small should be closer to 1.0
        assert result_small > result_large
        assert 0 < result_large < result_small < 1.0

    def test_saturation_bounds_tanh(self):
        """Test that tanh saturation stays within bounds."""
        large_sigma = np.array([-100.0, -10.0, 10.0, 100.0])
        result = saturate(large_sigma, epsilon=1.0, method="tanh")

        # Tanh output should be in [-1, 1] (inclusive bounds for numerical precision)
        assert np.all(result >= -1.0)
        assert np.all(result <= 1.0)
        # For very large inputs, tanh approaches ±1, so we accept values very close to ±1
        assert np.all(np.abs(result) <= 1.0)

    def test_saturation_bounds_linear(self):
        """Test that linear saturation clips to bounds."""
        large_sigma = np.array([-100.0, -10.0, 10.0, 100.0])

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            result = saturate(large_sigma, epsilon=1.0, method="linear")

        # Linear output should be exactly [-1, -1, 1, 1]
        expected = np.array([-1.0, -1.0, 1.0, 1.0])
        np.testing.assert_array_equal(result, expected)

    def test_negative_epsilon_error(self):
        """Test that negative epsilon raises error."""
        with pytest.raises(ValueError, match="boundary layer epsilon must be positive"):
            saturate(1.0, epsilon=-0.5, method="tanh")

    def test_zero_epsilon_error(self):
        """Test that zero epsilon raises error."""
        with pytest.raises(ValueError, match="boundary layer epsilon must be positive"):
            saturate(1.0, epsilon=0.0, method="tanh")

    def test_invalid_method_error(self):
        """Test that invalid method raises error."""
        with pytest.raises(ValueError, match="unknown saturation method"):
            saturate(1.0, epsilon=1.0, method="invalid")

    def test_small_epsilon_behavior(self):
        """Test saturation behavior with very small epsilon."""
        sigma = 0.1
        epsilon = 1e-6

        result = saturate(sigma, epsilon, method="tanh")
        # With very small epsilon, result should be close to sign(sigma) = 1
        assert abs(result - 1.0) < 0.01

    def test_large_epsilon_behavior(self):
        """Test saturation behavior with very large epsilon."""
        sigma = 1.0
        epsilon = 100.0

        result = saturate(sigma, epsilon, method="tanh")
        # With very large epsilon, result should be close to sigma/epsilon
        expected = sigma / epsilon
        assert abs(result - expected) < 0.01

    def test_multidimensional_arrays(self):
        """Test saturation with multidimensional arrays."""
        sigma = np.array([[1.0, -1.0], [2.0, -2.0]])
        epsilon = 1.0

        result = saturate(sigma, epsilon, method="tanh")
        expected = np.tanh(sigma)

        assert result.shape == sigma.shape
        np.testing.assert_array_almost_equal(result, expected)

    def test_type_preservation(self):
        """Test that input types are preserved appropriately."""
        # Float input should return float
        result_float = saturate(1.0, epsilon=1.0, method="tanh")
        assert isinstance(result_float, (float, np.floating))

        # Array input should return array
        result_array = saturate(np.array([1.0]), epsilon=1.0, method="tanh")
        assert isinstance(result_array, np.ndarray)