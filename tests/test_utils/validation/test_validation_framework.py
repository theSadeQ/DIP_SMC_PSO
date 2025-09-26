#==========================================================================================\\\
#============ tests/test_utils/validation/test_validation_framework.py ==================\\\
#==========================================================================================\\\

"""
Validation Framework Tests - System Reliability Foundation

This module provides comprehensive testing of the validation framework used
throughout the system for robust parameter validation, early error detection
with clear error messages, and scientific parameter validation system-wide.

MISSION: Robust parameter validation across entire system
PRIORITY: HIGH (5x ROI - Scientific parameter validation system-wide)
COVERAGE TARGET: 100% (Safety-critical mechanism)
"""

from __future__ import annotations

import pytest
import math
import numpy as np
from typing import Union
from unittest.mock import patch

from src.utils.validation.parameter_validators import (
    require_positive,
    require_finite
)
from src.utils.validation.range_validators import (
    require_in_range,
    require_probability
)


class TestParameterValidators:
    """Test suite for parameter validation functions."""

    def test_require_positive_valid_inputs(self):
        """Test require_positive with valid inputs."""
        # Valid positive float
        result = require_positive(5.5, "test_param")
        assert result == 5.5
        assert isinstance(result, float)

        # Valid positive int (should convert to float)
        result = require_positive(10, "test_param")
        assert result == 10.0
        assert isinstance(result, float)

        # Edge case: very small positive number
        result = require_positive(1e-10, "test_param")
        assert result == 1e-10

        # Edge case: large positive number
        result = require_positive(1e10, "test_param")
        assert result == 1e10

    def test_require_positive_with_allow_zero(self):
        """Test require_positive with allow_zero=True."""
        # Zero should be allowed
        result = require_positive(0.0, "test_param", allow_zero=True)
        assert result == 0.0

        # Positive should still work
        result = require_positive(5.0, "test_param", allow_zero=True)
        assert result == 5.0

        # Negative should still fail
        with pytest.raises(ValueError, match="test_param must be ≥ 0"):
            require_positive(-1.0, "test_param", allow_zero=True)

    def test_require_positive_invalid_inputs(self):
        """Test require_positive with invalid inputs."""
        # None input
        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_positive(None, "test_param")

        # Negative input
        with pytest.raises(ValueError, match="test_param must be > 0"):
            require_positive(-5.0, "test_param")

        # Zero input (without allow_zero)
        with pytest.raises(ValueError, match="test_param must be > 0"):
            require_positive(0.0, "test_param")

        # Infinity
        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_positive(float('inf'), "test_param")

        # NaN
        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_positive(float('nan'), "test_param")

        # String input
        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_positive("5.0", "test_param")

    def test_require_positive_error_messages(self):
        """Test that require_positive provides clear error messages."""
        try:
            require_positive(-2.5, "control_gain")
        except ValueError as e:
            assert "control_gain" in str(e)
            assert "must be > 0" in str(e)
            assert "-2.5" in str(e)

        try:
            require_positive(None, "time_constant")
        except ValueError as e:
            assert "time_constant" in str(e)
            assert "finite number" in str(e)

    def test_require_finite_valid_inputs(self):
        """Test require_finite with valid inputs."""
        # Valid finite float
        result = require_finite(42.5, "test_param")
        assert result == 42.5
        assert isinstance(result, float)

        # Valid finite int
        result = require_finite(42, "test_param")
        assert result == 42.0
        assert isinstance(result, float)

        # Zero is finite
        result = require_finite(0.0, "test_param")
        assert result == 0.0

        # Negative is finite
        result = require_finite(-10.5, "test_param")
        assert result == -10.5

    def test_require_finite_invalid_inputs(self):
        """Test require_finite with invalid inputs."""
        # None input
        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_finite(None, "test_param")

        # Infinity
        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_finite(float('inf'), "test_param")

        # Negative infinity
        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_finite(float('-inf'), "test_param")

        # NaN
        with pytest.raises(ValueError, match="test_param must be a finite number"):
            require_finite(float('nan'), "test_param")

    def test_require_finite_error_messages(self):
        """Test that require_finite provides clear error messages."""
        try:
            require_finite(float('inf'), "measurement_value")
        except ValueError as e:
            assert "measurement_value" in str(e)
            assert "finite number" in str(e)


class TestRangeValidators:
    """Test suite for range validation functions."""

    def test_require_in_range_valid_inputs(self):
        """Test require_in_range with valid inputs."""
        # Value within range (inclusive bounds)
        result = require_in_range(5.0, "test_param", minimum=0.0, maximum=10.0)
        assert result == 5.0

        # Value at lower bound
        result = require_in_range(0.0, "test_param", minimum=0.0, maximum=10.0)
        assert result == 0.0

        # Value at upper bound
        result = require_in_range(10.0, "test_param", minimum=0.0, maximum=10.0)
        assert result == 10.0

        # Int input should convert to float
        result = require_in_range(5, "test_param", minimum=0.0, maximum=10.0)
        assert result == 5.0
        assert isinstance(result, float)

    def test_require_in_range_exclusive_bounds(self):
        """Test require_in_range with exclusive bounds."""
        # Value within range (exclusive bounds)
        result = require_in_range(5.0, "test_param", minimum=0.0, maximum=10.0, allow_equal=False)
        assert result == 5.0

        # Value at bounds should fail
        with pytest.raises(ValueError, match="must satisfy 0.0 < test_param < 10.0"):
            require_in_range(0.0, "test_param", minimum=0.0, maximum=10.0, allow_equal=False)

        with pytest.raises(ValueError, match="must satisfy 0.0 < test_param < 10.0"):
            require_in_range(10.0, "test_param", minimum=0.0, maximum=10.0, allow_equal=False)

    def test_require_in_range_invalid_inputs(self):
        """Test require_in_range with invalid inputs."""
        # Value below range
        with pytest.raises(ValueError, match="must be in the interval \\[0.0, 10.0\\]"):
            require_in_range(-1.0, "test_param", minimum=0.0, maximum=10.0)

        # Value above range
        with pytest.raises(ValueError, match="must be in the interval \\[0.0, 10.0\\]"):
            require_in_range(11.0, "test_param", minimum=0.0, maximum=10.0)

        # None input
        with pytest.raises(ValueError, match="must be a finite number"):
            require_in_range(None, "test_param", minimum=0.0, maximum=10.0)

        # Infinity
        with pytest.raises(ValueError, match="must be a finite number"):
            require_in_range(float('inf'), "test_param", minimum=0.0, maximum=10.0)

        # NaN
        with pytest.raises(ValueError, match="must be a finite number"):
            require_in_range(float('nan'), "test_param", minimum=0.0, maximum=10.0)

    def test_require_probability_valid_inputs(self):
        """Test require_probability with valid inputs."""
        # Valid probabilities
        assert require_probability(0.0, "prob") == 0.0
        assert require_probability(0.5, "prob") == 0.5
        assert require_probability(1.0, "prob") == 1.0

        # Edge cases
        assert require_probability(1e-10, "prob") == 1e-10
        assert require_probability(1.0 - 1e-10, "prob") == 1.0 - 1e-10

    def test_require_probability_invalid_inputs(self):
        """Test require_probability with invalid inputs."""
        # Below range
        with pytest.raises(ValueError, match="must be in the interval \\[0.0, 1.0\\]"):
            require_probability(-0.1, "prob")

        # Above range
        with pytest.raises(ValueError, match="must be in the interval \\[0.0, 1.0\\]"):
            require_probability(1.1, "prob")

        # Invalid types
        with pytest.raises(ValueError):
            require_probability(None, "prob")

    def test_require_in_range_error_messages(self):
        """Test that require_in_range provides clear error messages."""
        try:
            require_in_range(15.0, "gain_value", minimum=0.0, maximum=10.0)
        except ValueError as e:
            assert "gain_value" in str(e)
            assert "[0.0, 10.0]" in str(e)
            assert "15.0" in str(e)


class TestValidationFrameworkIntegration:
    """Test validation framework integration across system components."""

    def test_control_parameter_validation_patterns(self):
        """Test common control parameter validation patterns."""
        # Typical control gains (must be positive)
        k_p = require_positive(10.0, "proportional_gain")
        k_d = require_positive(2.0, "derivative_gain")

        # Saturation limits (must be positive)
        u_max = require_positive(50.0, "control_saturation")

        # Time constants (must be positive)
        tau = require_positive(0.1, "time_constant")

        # Adaptation rates (must be in reasonable range)
        alpha = require_in_range(0.01, "adaptation_rate", minimum=1e-6, maximum=1.0)

        assert k_p == 10.0
        assert k_d == 2.0
        assert u_max == 50.0
        assert tau == 0.1
        assert alpha == 0.01

    def test_physics_parameter_validation_patterns(self):
        """Test physics parameter validation patterns."""
        # Masses (must be positive)
        m1 = require_positive(1.5, "cart_mass")
        m2 = require_positive(0.5, "pendulum_mass")

        # Lengths (must be positive)
        l = require_positive(0.8, "pendulum_length")

        # Friction coefficients (non-negative)
        b = require_positive(0.1, "friction_coefficient", allow_zero=True)

        # Initial conditions (finite)
        x0 = require_finite(0.0, "initial_position")
        theta0 = require_finite(0.1, "initial_angle")

        assert m1 == 1.5
        assert m2 == 0.5
        assert l == 0.8
        assert b == 0.1
        assert x0 == 0.0
        assert theta0 == 0.1

    def test_optimization_parameter_validation_patterns(self):
        """Test optimization parameter validation patterns."""
        # Population size (must be positive integer-like)
        pop_size = require_positive(30, "population_size")

        # Probability parameters (0 to 1) - this should fail
        with pytest.raises(ValueError):
            require_probability(2.0, "cognitive_parameter")

        # Correct probability
        mutation_rate = require_probability(0.1, "mutation_rate")

        # Iteration limits (positive)
        max_iter = require_positive(100, "max_iterations")

        # Tolerance (positive, can be very small)
        tol = require_positive(1e-6, "convergence_tolerance")

        assert pop_size == 30.0
        assert mutation_rate == 0.1
        assert max_iter == 100.0
        assert tol == 1e-6

    def test_simulation_parameter_validation_patterns(self):
        """Test simulation parameter validation patterns."""
        # Time parameters (must be positive)
        dt = require_positive(0.01, "time_step")
        t_final = require_positive(10.0, "simulation_time")

        # Integration bounds
        atol = require_positive(1e-8, "absolute_tolerance")
        rtol = require_positive(1e-6, "relative_tolerance")

        # Sample rates (positive)
        fs = require_positive(1000.0, "sampling_frequency")

        assert dt == 0.01
        assert t_final == 10.0
        assert atol == 1e-8
        assert rtol == 1e-6
        assert fs == 1000.0


class TestValidationPerformance:
    """Test validation framework performance characteristics."""

    def test_validation_performance_overhead(self):
        """Test that validation has minimal performance overhead."""
        import time

        # Time validation operations
        start_time = time.perf_counter()

        for i in range(1000):
            require_positive(10.0 + i * 0.1, f"param_{i}")
            require_finite(i * 0.5, f"finite_{i}")
            require_in_range(i * 0.01, f"range_{i}", minimum=0.0, maximum=100.0)

        validation_time = time.perf_counter() - start_time

        # Should be very fast (< 10ms for 3000 validations)
        assert validation_time < 0.01, f"Validation too slow: {validation_time:.6f}s"

    def test_error_message_generation_performance(self):
        """Test error message generation performance."""
        import time

        start_time = time.perf_counter()

        # Generate error messages
        for i in range(100):
            try:
                require_positive(-1.0, f"param_{i}")
            except ValueError:
                pass  # Expected

        error_time = time.perf_counter() - start_time

        # Error generation should still be reasonably fast
        assert error_time < 0.01, f"Error generation too slow: {error_time:.6f}s"


class TestValidationRobustness:
    """Test validation framework robustness and edge cases."""

    def test_extreme_value_handling(self):
        """Test handling of extreme values."""
        # Very small positive values
        result = require_positive(1e-15, "tiny_value")
        assert result == 1e-15

        # Very large positive values (but finite)
        result = require_positive(1e15, "large_value")
        assert result == 1e15

        # Precision edge cases
        result = require_in_range(1e-10, "precise", minimum=0.0, maximum=1e-9)
        assert result == 1e-10

    def test_numerical_precision_edge_cases(self):
        """Test numerical precision edge cases."""
        # Floating point precision near boundaries
        epsilon = 1e-15

        # Should work at boundary + epsilon
        result = require_in_range(
            1.0 + epsilon,
            "boundary_test",
            minimum=0.0,
            maximum=1.0 + 2*epsilon
        )
        assert result == 1.0 + epsilon

        # Should handle floating point representation issues
        value = 0.1 + 0.2  # Known to be 0.30000000000000004
        result = require_in_range(value, "fp_test", minimum=0.0, maximum=1.0)
        assert abs(result - 0.3) < 1e-10

    def test_unicode_parameter_names(self):
        """Test that parameter names with unicode work correctly."""
        # Unicode in parameter names
        result = require_positive(5.0, "θ_angle")
        assert result == 5.0

        try:
            require_positive(-1.0, "τ_time_constant")
        except ValueError as e:
            assert "τ_time_constant" in str(e)

    def test_long_parameter_names(self):
        """Test handling of very long parameter names."""
        long_name = "very_long_parameter_name_that_describes_something_important_" * 5
        result = require_positive(1.0, long_name)
        assert result == 1.0

        try:
            require_positive(-1.0, long_name)
        except ValueError as e:
            assert long_name[:50] in str(e)  # Should contain part of the name


class TestValidationDocumentation:
    """Test validation framework documentation and introspection."""

    def test_validation_functions_have_docstrings(self):
        """Ensure all validation functions have proper documentation."""
        validation_functions = [
            require_positive,
            require_finite,
            require_in_range,
            require_probability
        ]

        for func in validation_functions:
            assert func.__doc__ is not None, f"{func.__name__} missing docstring"
            assert len(func.__doc__.strip()) > 50, f"{func.__name__} docstring too short"

    def test_parameter_documentation_consistency(self):
        """Test that parameter documentation follows consistent patterns."""
        for func in [require_positive, require_finite, require_in_range]:
            docstring = func.__doc__
            assert 'Parameters' in docstring, f"{func.__name__} missing parameter section"
            assert 'Returns' in docstring, f"{func.__name__} missing returns section"
            assert 'Raises' in docstring, f"{func.__name__} missing raises section"


class TestValidationErrorRecovery:
    """Test validation framework error recovery and debugging support."""

    def test_validation_error_context(self):
        """Test that validation errors provide sufficient context for debugging."""
        try:
            require_positive(-5.0, "critical_gain")
        except ValueError as e:
            error_str = str(e)
            # Should contain parameter name
            assert "critical_gain" in error_str
            # Should contain actual value
            assert "-5.0" in error_str
            # Should contain constraint
            assert "> 0" in error_str

    def test_chained_validation_errors(self):
        """Test error handling in chained validation scenarios."""
        def validate_control_params(kp, kd, ki):
            kp = require_positive(kp, "proportional_gain")
            kd = require_positive(kd, "derivative_gain")
            ki = require_positive(ki, "integral_gain")
            return kp, kd, ki

        # Should handle first error
        with pytest.raises(ValueError, match="proportional_gain"):
            validate_control_params(-1.0, 2.0, 3.0)

        # Should handle middle error if first passes
        with pytest.raises(ValueError, match="derivative_gain"):
            validate_control_params(1.0, -2.0, 3.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])