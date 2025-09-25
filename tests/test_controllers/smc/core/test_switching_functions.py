#==========================================================================================\\\
#============== tests/test_controllers/smc/core/test_switching_functions.py ==============\\\
#==========================================================================================\\\

"""
Tests for SMC Switching Functions.
SINGLE JOB: Test only switching functions for chattering reduction and SMC control law.
"""

import pytest
import numpy as np
import warnings

from src.controllers.smc.core.switching_functions import (
    SwitchingMethod,
    SwitchingFunction,
    tanh_switching,
    linear_switching,
    sign_switching,
    adaptive_boundary_layer,
    power_rate_reaching_law
)


class TestSwitchingMethod:
    """Test SwitchingMethod enumeration."""

    def test_enum_values(self):
        """Test that all expected enumeration values exist."""
        assert SwitchingMethod.TANH.value == "tanh"
        assert SwitchingMethod.LINEAR.value == "linear"
        assert SwitchingMethod.SIGN.value == "sign"
        assert SwitchingMethod.SIGMOID.value == "sigmoid"

    def test_enum_completeness(self):
        """Test that enum contains expected number of methods."""
        methods = list(SwitchingMethod)
        assert len(methods) == 4


class TestSwitchingFunctionClass:
    """Test suite for SwitchingFunction class."""

    def test_initialization_with_string(self):
        """Test initialization with string method names."""
        switch_func = SwitchingFunction("tanh")
        assert switch_func.method == SwitchingMethod.TANH

    def test_initialization_with_enum(self):
        """Test initialization with enum values."""
        switch_func = SwitchingFunction(SwitchingMethod.LINEAR)
        assert switch_func.method == SwitchingMethod.LINEAR

    def test_initialization_case_insensitive(self):
        """Test that method names are case insensitive."""
        switch_func = SwitchingFunction("TANH")
        assert switch_func.method == SwitchingMethod.TANH

        switch_func = SwitchingFunction("Linear")
        assert switch_func.method == SwitchingMethod.LINEAR

    def test_initialization_default_method(self):
        """Test default initialization uses tanh method."""
        switch_func = SwitchingFunction()
        assert switch_func.method == SwitchingMethod.TANH

    def test_initialization_invalid_method(self):
        """Test error with invalid method name."""
        with pytest.raises(ValueError, match="Unknown switching method"):
            SwitchingFunction("invalid_method")

    def test_tanh_switching_basic(self):
        """Test basic tanh switching function."""
        switch_func = SwitchingFunction(SwitchingMethod.TANH)

        result = switch_func.compute(1.0, 1.0)
        expected = np.tanh(1.0)

        assert abs(result - expected) < 1e-10

    def test_tanh_switching_zero_surface(self):
        """Test tanh switching with zero surface value."""
        switch_func = SwitchingFunction(SwitchingMethod.TANH)

        result = switch_func.compute(0.0, 1.0)
        assert result == 0.0

    def test_tanh_switching_zero_epsilon(self):
        """Test tanh switching with zero boundary layer."""
        switch_func = SwitchingFunction(SwitchingMethod.TANH)

        result = switch_func.compute(1.0, 0.0)
        assert result == 1.0  # Should fall back to sign function

        result = switch_func.compute(-1.0, 0.0)
        assert result == -1.0

    def test_tanh_switching_large_surface(self):
        """Test tanh switching with large surface values."""
        switch_func = SwitchingFunction(SwitchingMethod.TANH)

        result_pos = switch_func.compute(100.0, 1.0)
        result_neg = switch_func.compute(-100.0, 1.0)

        assert 0.999 <= result_pos <= 1.0  # Should approach 1
        assert -1.0 <= result_neg <= -0.999  # Should approach -1

    def test_linear_switching_basic(self):
        """Test basic linear switching function."""
        switch_func = SwitchingFunction(SwitchingMethod.LINEAR)

        # Inside boundary layer
        result = switch_func.compute(0.5, 1.0)
        assert result == 0.5

    def test_linear_switching_saturation(self):
        """Test linear switching saturation behavior."""
        switch_func = SwitchingFunction(SwitchingMethod.LINEAR)

        # Outside boundary layer - should saturate
        result_pos = switch_func.compute(2.0, 1.0)
        result_neg = switch_func.compute(-2.0, 1.0)

        assert result_pos == 1.0
        assert result_neg == -1.0

    def test_linear_switching_zero_epsilon(self):
        """Test linear switching with zero boundary layer."""
        switch_func = SwitchingFunction(SwitchingMethod.LINEAR)

        result = switch_func.compute(0.5, 0.0)
        assert result == 1.0  # Should fall back to sign function

    def test_sign_switching_basic(self):
        """Test basic sign switching function."""
        switch_func = SwitchingFunction(SwitchingMethod.SIGN)

        result_pos = switch_func.compute(1.0, 1.0)
        result_neg = switch_func.compute(-1.0, 1.0)
        result_zero = switch_func.compute(0.0, 1.0)

        assert result_pos == 1.0
        assert result_neg == -1.0
        assert result_zero == 0.0

    def test_sign_switching_ignores_epsilon(self):
        """Test that sign switching ignores boundary layer parameter."""
        switch_func = SwitchingFunction(SwitchingMethod.SIGN)

        result1 = switch_func.compute(1.0, 0.1)
        result2 = switch_func.compute(1.0, 10.0)

        assert result1 == result2 == 1.0

    def test_sigmoid_switching_basic(self):
        """Test basic sigmoid switching function."""
        switch_func = SwitchingFunction(SwitchingMethod.SIGMOID)

        result_zero = switch_func.compute(0.0, 1.0)
        result_pos = switch_func.compute(1.0, 1.0)
        result_neg = switch_func.compute(-1.0, 1.0)

        assert result_zero == 0.0
        assert result_pos > 0.0
        assert result_neg < 0.0

    def test_sigmoid_switching_bounds(self):
        """Test sigmoid switching bounds."""
        switch_func = SwitchingFunction(SwitchingMethod.SIGMOID)

        result_large_pos = switch_func.compute(100.0, 1.0)
        result_large_neg = switch_func.compute(-100.0, 1.0)

        # Should approach ±1 but not exceed
        assert 0.999 <= result_large_pos <= 1.0
        assert -1.0 <= result_large_neg <= -0.999

    def test_sigmoid_switching_zero_epsilon(self):
        """Test sigmoid switching with zero boundary layer."""
        switch_func = SwitchingFunction(SwitchingMethod.SIGMOID)

        result = switch_func.compute(1.0, 0.0)
        assert result == 1.0  # Should fall back to sign function


class TestSwitchingFunctionDerivatives:
    """Test derivative computation for switching functions."""

    def test_tanh_derivative_basic(self):
        """Test tanh switching function derivative."""
        switch_func = SwitchingFunction(SwitchingMethod.TANH)

        s, epsilon = 1.0, 1.0
        derivative = switch_func.get_derivative(s, epsilon)

        # Analytical: d/ds tanh(s/ε) = (1 - tanh²(s/ε))/ε
        tanh_val = np.tanh(s / epsilon)
        expected = (1.0 - tanh_val**2) / epsilon

        assert abs(derivative - expected) < 1e-10

    def test_tanh_derivative_zero_surface(self):
        """Test tanh derivative at zero surface value."""
        switch_func = SwitchingFunction(SwitchingMethod.TANH)

        derivative = switch_func.get_derivative(0.0, 1.0)
        expected = 1.0 / 1.0  # Maximum derivative at s=0

        assert abs(derivative - expected) < 1e-10

    def test_tanh_derivative_zero_epsilon(self):
        """Test tanh derivative with zero boundary layer."""
        switch_func = SwitchingFunction(SwitchingMethod.TANH)

        derivative = switch_func.get_derivative(1.0, 0.0)
        assert derivative == 0.0  # Sign function has zero derivative

    def test_linear_derivative_inside_boundary(self):
        """Test linear switching derivative inside boundary layer."""
        switch_func = SwitchingFunction(SwitchingMethod.LINEAR)

        derivative = switch_func.get_derivative(0.5, 1.0)  # Inside boundary
        expected = 1.0 / 1.0  # Constant slope inside boundary

        assert derivative == expected

    def test_linear_derivative_outside_boundary(self):
        """Test linear switching derivative outside boundary layer."""
        switch_func = SwitchingFunction(SwitchingMethod.LINEAR)

        derivative = switch_func.get_derivative(2.0, 1.0)  # Outside boundary
        assert derivative == 0.0  # Zero slope in saturation region

    def test_linear_derivative_at_boundary(self):
        """Test linear switching derivative exactly at boundary."""
        switch_func = SwitchingFunction(SwitchingMethod.LINEAR)

        derivative = switch_func.get_derivative(1.0, 1.0)  # At boundary
        assert derivative == 0.0  # Zero slope at boundary

    def test_sigmoid_derivative_basic(self):
        """Test sigmoid switching function derivative."""
        switch_func = SwitchingFunction(SwitchingMethod.SIGMOID)

        s, epsilon = 1.0, 1.0
        derivative = switch_func.get_derivative(s, epsilon)

        # Should be positive and finite
        assert derivative > 0.0
        assert np.isfinite(derivative)

    def test_sigmoid_derivative_zero_surface(self):
        """Test sigmoid derivative at zero surface value."""
        switch_func = SwitchingFunction(SwitchingMethod.SIGMOID)

        derivative = switch_func.get_derivative(0.0, 1.0)
        expected = (4.0 / 1.0) * 0.25  # Maximum derivative at s=0

        assert abs(derivative - expected) < 1e-10

    def test_sign_derivative(self):
        """Test sign function derivative (should be zero)."""
        switch_func = SwitchingFunction(SwitchingMethod.SIGN)

        derivative = switch_func.get_derivative(1.0, 1.0)
        assert derivative == 0.0


class TestConvenienceFunctions:
    """Test standalone convenience functions."""

    def test_tanh_switching_function(self):
        """Test standalone tanh switching function."""
        result = tanh_switching(1.0, 1.0)
        expected = np.tanh(1.0)

        assert abs(result - expected) < 1e-10

    def test_tanh_switching_zero_epsilon(self):
        """Test tanh switching with zero epsilon."""
        result_pos = tanh_switching(1.0, 0.0)
        result_neg = tanh_switching(-1.0, 0.0)

        assert result_pos == 1.0
        assert result_neg == -1.0

    def test_linear_switching_function(self):
        """Test standalone linear switching function."""
        result_inside = linear_switching(0.5, 1.0)
        result_outside = linear_switching(2.0, 1.0)

        assert result_inside == 0.5
        assert result_outside == 1.0

    def test_linear_switching_zero_epsilon(self):
        """Test linear switching with zero epsilon."""
        result = linear_switching(0.5, 0.0)
        assert result == 1.0  # Should default to sign function

    def test_sign_switching_function(self):
        """Test standalone sign switching function."""
        result_pos = sign_switching(1.0)
        result_neg = sign_switching(-1.0)
        result_zero = sign_switching(0.0)

        assert result_pos == 1.0
        assert result_neg == -1.0
        assert result_zero == 0.0

    def test_sign_switching_ignores_epsilon(self):
        """Test that sign switching ignores epsilon parameter."""
        result1 = sign_switching(1.0, 0.1)
        result2 = sign_switching(1.0, 10.0)

        assert result1 == result2 == 1.0


class TestAdaptiveBoundaryLayer:
    """Test adaptive boundary layer functionality."""

    def test_adaptive_boundary_basic(self):
        """Test basic adaptive boundary layer computation."""
        base_epsilon = 0.1
        adaptation_gain = 0.05
        surface_value = 1.0
        surface_derivative = 2.0

        result = adaptive_boundary_layer(surface_value, surface_derivative,
                                       base_epsilon, adaptation_gain)

        expected = base_epsilon + adaptation_gain * abs(surface_derivative)
        assert abs(result - expected) < 1e-10

    def test_adaptive_boundary_zero_derivative(self):
        """Test adaptive boundary with zero surface derivative."""
        result = adaptive_boundary_layer(1.0, 0.0, 0.1, 0.05)
        expected = 0.1  # Should equal base epsilon

        assert result == expected

    def test_adaptive_boundary_negative_derivative(self):
        """Test adaptive boundary with negative surface derivative."""
        result = adaptive_boundary_layer(1.0, -2.0, 0.1, 0.05)
        expected = 0.1 + 0.05 * 2.0  # Uses absolute value

        assert abs(result - expected) < 1e-10

    def test_adaptive_boundary_large_derivative(self):
        """Test adaptive boundary with large surface derivative."""
        result = adaptive_boundary_layer(1.0, 100.0, 0.1, 0.01)
        expected = 0.1 + 0.01 * 100.0

        assert result == expected
        assert result > 0.1  # Should increase boundary layer


class TestPowerRateReachingLaw:
    """Test power rate reaching law functionality."""

    def test_power_rate_basic(self):
        """Test basic power rate reaching law computation."""
        s = 2.0
        K = 1.0
        alpha = 0.5
        epsilon = 0.01

        result = power_rate_reaching_law(s, K, alpha, epsilon)

        # Expected: -K * |s|^α * tanh(s/ε)
        s_abs_power = np.power(abs(s), alpha)
        sign_approx = np.tanh(s / epsilon)
        expected = -K * s_abs_power * sign_approx

        assert abs(result - expected) < 1e-10

    def test_power_rate_zero_surface(self):
        """Test power rate reaching law with zero surface."""
        result = power_rate_reaching_law(0.0, 1.0, 0.5, 0.01)
        assert result == 0.0

    def test_power_rate_negative_surface(self):
        """Test power rate reaching law with negative surface."""
        result = power_rate_reaching_law(-2.0, 1.0, 0.5, 0.01)

        # Should be positive (opposite sign of surface)
        assert result > 0.0

    def test_power_rate_alpha_one(self):
        """Test power rate reaching law with α = 1 (linear)."""
        s = 2.0
        result = power_rate_reaching_law(s, 1.0, 1.0, 0.01)

        # Should equal -|s| * tanh(s/ε) = -2 * tanh(200)
        expected = -2.0 * np.tanh(200.0)
        assert abs(result - expected) < 1e-10

    def test_power_rate_small_alpha(self):
        """Test power rate reaching law with small α (fast convergence)."""
        result = power_rate_reaching_law(4.0, 1.0, 0.1, 0.01)

        # With α = 0.1, |4|^0.1 ≈ 1.148
        s_abs_power = np.power(4.0, 0.1)
        sign_approx = np.tanh(400.0)  # ≈ 1
        expected = -1.0 * s_abs_power * sign_approx

        assert abs(result - expected) < 1e-6

    def test_power_rate_invalid_K(self):
        """Test error with invalid K parameter."""
        with pytest.raises(ValueError, match="gain K must be positive"):
            power_rate_reaching_law(1.0, 0.0, 0.5, 0.01)

        with pytest.raises(ValueError, match="gain K must be positive"):
            power_rate_reaching_law(1.0, -1.0, 0.5, 0.01)

    def test_power_rate_invalid_alpha(self):
        """Test error with invalid α parameter."""
        # α = 0 not allowed
        with pytest.raises(ValueError, match="must be in \\(0, 1\\]"):
            power_rate_reaching_law(1.0, 1.0, 0.0, 0.01)

        # α > 1 not allowed for finite-time stability
        with pytest.raises(ValueError, match="must be in \\(0, 1\\]"):
            power_rate_reaching_law(1.0, 1.0, 1.5, 0.01)

        # Negative α not allowed
        with pytest.raises(ValueError, match="must be in \\(0, 1\\]"):
            power_rate_reaching_law(1.0, 1.0, -0.5, 0.01)

    def test_power_rate_boundary_alpha(self):
        """Test power rate reaching law at boundary α values."""
        # α = 1 should work
        result = power_rate_reaching_law(1.0, 1.0, 1.0, 0.01)
        assert np.isfinite(result)

        # Very small α should work
        result = power_rate_reaching_law(1.0, 1.0, 0.001, 0.01)
        assert np.isfinite(result)


class TestSwitchingFunctionNumericalProperties:
    """Test numerical properties and edge cases."""

    def test_switching_function_bounds(self):
        """Test that all switching functions maintain proper bounds."""
        methods = [SwitchingMethod.TANH, SwitchingMethod.LINEAR,
                  SwitchingMethod.SIGN, SwitchingMethod.SIGMOID]

        large_values = [-100.0, -10.0, -1.0, 0.0, 1.0, 10.0, 100.0]

        for method in methods:
            switch_func = SwitchingFunction(method)
            for s in large_values:
                result = switch_func.compute(s, 1.0)

                # All methods should produce bounded output
                assert -1.0 <= result <= 1.0, f"Method {method} produced {result} for input {s}"

    def test_switching_function_continuity(self):
        """Test switching function continuity."""
        switch_func = SwitchingFunction(SwitchingMethod.TANH)

        # Test continuity around zero
        epsilon = 1e-8
        result_neg = switch_func.compute(-epsilon, 1.0)
        result_pos = switch_func.compute(epsilon, 1.0)
        result_zero = switch_func.compute(0.0, 1.0)

        # Should be continuous at zero
        assert abs(result_neg - result_zero) < 1e-6
        assert abs(result_pos - result_zero) < 1e-6

    def test_switching_function_monotonicity(self):
        """Test that switching functions are monotonically increasing."""
        switch_func = SwitchingFunction(SwitchingMethod.TANH)

        values = [-2.0, -1.0, 0.0, 1.0, 2.0]
        results = [switch_func.compute(v, 1.0) for v in values]

        # Results should be monotonically increasing
        for i in range(len(results) - 1):
            assert results[i] < results[i + 1], f"Non-monotonic: {results[i]} >= {results[i+1]}"

    def test_switching_function_antisymmetry(self):
        """Test switching function antisymmetry: f(-x) = -f(x)."""
        methods = [SwitchingMethod.TANH, SwitchingMethod.LINEAR,
                  SwitchingMethod.SIGN, SwitchingMethod.SIGMOID]

        test_values = [0.5, 1.0, 2.0, 10.0]

        for method in methods:
            switch_func = SwitchingFunction(method)
            for s in test_values:
                result_pos = switch_func.compute(s, 1.0)
                result_neg = switch_func.compute(-s, 1.0)

                # Should satisfy f(-x) = -f(x)
                assert abs(result_pos + result_neg) < 1e-10, f"Method {method} failed antisymmetry test"

    def test_epsilon_scaling_effects(self):
        """Test effects of different epsilon values."""
        switch_func = SwitchingFunction(SwitchingMethod.TANH)

        surface_value = 1.0
        epsilons = [0.1, 1.0, 10.0]

        results = [switch_func.compute(surface_value, eps) for eps in epsilons]

        # Smaller epsilon should give results closer to ±1
        # Larger epsilon should give results closer to 0
        assert abs(results[0]) > abs(results[1]) > abs(results[2])