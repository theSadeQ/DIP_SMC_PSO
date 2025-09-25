#==========================================================================================\\\
#================ tests/test_controllers/smc/core/test_sliding_surface.py ================\\\
#==========================================================================================\\\

"""
Tests for Sliding Surface Calculations.
SINGLE JOB: Test only sliding surface mathematical computations and properties.
"""

import pytest
import numpy as np

from src.controllers.smc.core.sliding_surface import (
    SlidingSurface,
    LinearSlidingSurface,
    HigherOrderSlidingSurface,
    create_sliding_surface
)


class TestSlidingSurfaceAbstractBase:
    """Test abstract base class behavior."""

    def test_abstract_class_cannot_be_instantiated(self):
        """Test that abstract SlidingSurface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            SlidingSurface([1.0, 2.0, 3.0, 4.0])

    def test_abstract_methods_defined(self):
        """Test that required abstract methods are defined."""
        abstract_methods = SlidingSurface.__abstractmethods__
        expected_methods = {'_validate_gains', 'compute', 'compute_derivative'}
        assert abstract_methods == expected_methods


class TestLinearSlidingSurface:
    """Test suite for LinearSlidingSurface implementation."""

    @pytest.fixture
    def valid_gains(self):
        """Standard valid gains for testing."""
        return [2.0, 1.5, 3.0, 2.5]  # [k1, k2, lam1, lam2]

    @pytest.fixture
    def surface(self, valid_gains):
        """Create LinearSlidingSurface instance."""
        return LinearSlidingSurface(valid_gains)

    @pytest.fixture
    def test_state(self):
        """Standard test state vector."""
        return np.array([0.1, 0.2, 0.05, 0.1, -0.03, -0.05])  # [x, x_dot, θ1, θ1_dot, θ2, θ2_dot]

    def test_initialization_valid_gains(self, valid_gains):
        """Test successful initialization with valid gains."""
        surface = LinearSlidingSurface(valid_gains)

        assert surface.k1 == valid_gains[0]
        assert surface.k2 == valid_gains[1]
        assert surface.lam1 == valid_gains[2]
        assert surface.lam2 == valid_gains[3]
        np.testing.assert_array_equal(surface.gains, valid_gains)

    def test_initialization_array_gains(self):
        """Test initialization with numpy array gains."""
        gains_array = np.array([1.0, 2.0, 3.0, 4.0])
        surface = LinearSlidingSurface(gains_array)

        assert surface.k1 == 1.0
        assert surface.k2 == 2.0
        assert surface.lam1 == 3.0
        assert surface.lam2 == 4.0

    def test_initialization_insufficient_gains(self):
        """Test error with insufficient gains."""
        insufficient_gains = [1.0, 2.0, 3.0]  # Only 3 gains, need 4

        with pytest.raises(ValueError, match="requires at least 4 gains"):
            LinearSlidingSurface(insufficient_gains)

    def test_initialization_zero_gains_rejected(self):
        """Test that zero gains are rejected."""
        zero_gains = [0.0, 1.0, 2.0, 3.0]

        with pytest.raises(ValueError, match="must be positive"):
            LinearSlidingSurface(zero_gains)

    def test_initialization_negative_gains_rejected(self):
        """Test that negative gains are rejected."""
        negative_gains = [1.0, -2.0, 3.0, 4.0]

        with pytest.raises(ValueError, match="must be positive"):
            LinearSlidingSurface(negative_gains)

    def test_compute_basic_functionality(self, surface, test_state):
        """Test basic sliding surface computation."""
        result = surface.compute(test_state)

        # Expected: lam1*theta1_dot + k1*theta1 + lam2*theta2_dot + k2*theta2
        # = 3.0*0.1 + 2.0*0.05 + 2.5*(-0.05) + 1.5*(-0.03)
        # = 0.3 + 0.1 - 0.125 - 0.045 = 0.23
        expected = 3.0*0.1 + 2.0*0.05 + 2.5*(-0.05) + 1.5*(-0.03)

        assert isinstance(result, float)
        assert abs(result - expected) < 1e-10

    def test_compute_zero_state(self, surface):
        """Test computation with zero state (equilibrium)."""
        zero_state = np.zeros(6)
        result = surface.compute(zero_state)

        assert result == 0.0

    def test_compute_insufficient_state_dimensions(self, surface):
        """Test error with insufficient state dimensions."""
        short_state = np.array([0.1, 0.2, 0.05])  # Only 3 elements

        with pytest.raises(ValueError, match="at least 6 elements"):
            surface.compute(short_state)

    def test_compute_positive_angles(self, surface):
        """Test computation with positive joint angles."""
        state = np.array([0.0, 0.0, 0.1, 0.2, 0.15, 0.3])  # Positive θ1, θ2

        result = surface.compute(state)

        # Expected: 3.0*0.2 + 2.0*0.1 + 2.5*0.3 + 1.5*0.15
        expected = 3.0*0.2 + 2.0*0.1 + 2.5*0.3 + 1.5*0.15
        assert abs(result - expected) < 1e-10

    def test_compute_negative_angles(self, surface):
        """Test computation with negative joint angles."""
        state = np.array([0.0, 0.0, -0.1, -0.2, -0.15, -0.3])  # Negative θ1, θ2

        result = surface.compute(state)

        # Expected: 3.0*(-0.2) + 2.0*(-0.1) + 2.5*(-0.3) + 1.5*(-0.15)
        expected = 3.0*(-0.2) + 2.0*(-0.1) + 2.5*(-0.3) + 1.5*(-0.15)
        assert abs(result - expected) < 1e-10

    def test_compute_derivative_basic(self, surface, test_state):
        """Test sliding surface derivative computation."""
        # State derivative vector [x_dot, x_ddot, θ1_dot, θ1_ddot, θ2_dot, θ2_ddot]
        state_dot = np.array([0.2, 0.5, 0.1, 0.8, -0.05, -0.6])

        result = surface.compute_derivative(test_state, state_dot)

        # Expected: lam1*theta1_ddot + k1*theta1_dot + lam2*theta2_ddot + k2*theta2_dot
        # = 3.0*0.8 + 2.0*0.1 + 2.5*(-0.6) + 1.5*(-0.05)
        # = 2.4 + 0.2 - 1.5 - 0.075 = 1.025
        expected = 3.0*0.8 + 2.0*0.1 + 2.5*(-0.6) + 1.5*(-0.05)

        assert isinstance(result, float)
        assert abs(result - expected) < 1e-10

    def test_compute_derivative_zero_state_dot(self, surface, test_state):
        """Test derivative computation with zero accelerations."""
        state_dot = np.zeros(6)
        result = surface.compute_derivative(test_state, state_dot)

        # Only velocity terms contribute: k1*theta1_dot + k2*theta2_dot
        expected = 2.0*0.1 + 1.5*(-0.05)
        assert abs(result - expected) < 1e-10

    def test_compute_derivative_insufficient_dimensions(self, surface, test_state):
        """Test error with insufficient state_dot dimensions."""
        short_state_dot = np.array([0.1, 0.2, 0.05])

        with pytest.raises(ValueError, match="at least 6 elements"):
            surface.compute_derivative(test_state, short_state_dot)

    def test_get_coefficients(self, surface, valid_gains):
        """Test retrieval of surface coefficients."""
        coeffs = surface.get_coefficients()

        expected_coeffs = {
            'k1': valid_gains[0],
            'k2': valid_gains[1],
            'lambda1': valid_gains[2],
            'lambda2': valid_gains[3]
        }

        assert coeffs == expected_coeffs
        assert isinstance(coeffs, dict)
        assert len(coeffs) == 4

    def test_linearity_property(self, surface):
        """Test that surface computation is linear in state."""
        state1 = np.array([0.1, 0.2, 0.05, 0.1, -0.03, -0.05])
        state2 = np.array([0.2, 0.3, 0.10, 0.2, -0.06, -0.10])

        result1 = surface.compute(state1)
        result2 = surface.compute(state2)
        result_sum = surface.compute(state1 + state2)

        # Linearity: f(x1 + x2) = f(x1) + f(x2)
        assert abs(result_sum - (result1 + result2)) < 1e-10

    def test_scaling_property(self, surface):
        """Test that surface computation scales correctly."""
        state = np.array([0.1, 0.2, 0.05, 0.1, -0.03, -0.05])
        scale_factor = 3.0

        result_original = surface.compute(state)
        result_scaled = surface.compute(scale_factor * state)

        # Scaling: f(α·x) = α·f(x)
        assert abs(result_scaled - scale_factor * result_original) < 1e-10

    def test_extra_gains_ignored(self):
        """Test that extra gains beyond first 4 are handled correctly."""
        gains_with_extra = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]  # 6 gains, only first 4 used
        surface = LinearSlidingSurface(gains_with_extra)

        assert surface.k1 == 1.0
        assert surface.k2 == 2.0
        assert surface.lam1 == 3.0
        assert surface.lam2 == 4.0


class TestHigherOrderSlidingSurface:
    """Test suite for HigherOrderSlidingSurface implementation."""

    def test_initialization_order_2(self):
        """Test initialization with order 2 (super-twisting)."""
        gains = [1.0, 2.0, 3.0, 4.0]  # 4 gains for order 2
        surface = HigherOrderSlidingSurface(gains, order=2)

        assert surface.order == 2
        np.testing.assert_array_equal(surface.gains, gains)

    def test_initialization_invalid_order(self):
        """Test error with invalid order."""
        gains = [1.0, 2.0, 3.0, 4.0]

        with pytest.raises(ValueError, match="order must be >= 1"):
            HigherOrderSlidingSurface(gains, order=0)

    def test_initialization_insufficient_gains_for_order(self):
        """Test error with insufficient gains for given order."""
        gains = [1.0, 2.0]  # Only 2 gains
        order = 3  # Requires 6 gains (2 * 3)

        with pytest.raises(ValueError, match="Order 3 surface requires at least 6 gains"):
            HigherOrderSlidingSurface(gains, order=order)

    def test_initialization_negative_gains_rejected(self):
        """Test that negative gains are rejected."""
        gains = [1.0, -2.0, 3.0, 4.0]

        with pytest.raises(ValueError, match="must be positive"):
            HigherOrderSlidingSurface(gains)

    def test_compute_falls_back_to_linear(self):
        """Test that compute method falls back to linear surface."""
        gains = [2.0, 1.5, 3.0, 2.5]
        higher_order_surface = HigherOrderSlidingSurface(gains, order=2)
        linear_surface = LinearSlidingSurface(gains)

        test_state = np.array([0.1, 0.2, 0.05, 0.1, -0.03, -0.05])

        result_ho = higher_order_surface.compute(test_state)
        result_linear = linear_surface.compute(test_state)

        assert abs(result_ho - result_linear) < 1e-10

    def test_compute_derivative_falls_back_to_linear(self):
        """Test that compute_derivative method falls back to linear surface."""
        gains = [2.0, 1.5, 3.0, 2.5]
        higher_order_surface = HigherOrderSlidingSurface(gains, order=2)
        linear_surface = LinearSlidingSurface(gains)

        test_state = np.array([0.1, 0.2, 0.05, 0.1, -0.03, -0.05])
        state_dot = np.array([0.2, 0.5, 0.1, 0.8, -0.05, -0.6])

        result_ho = higher_order_surface.compute_derivative(test_state, state_dot)
        result_linear = linear_surface.compute_derivative(test_state, state_dot)

        assert abs(result_ho - result_linear) < 1e-10

    def test_insufficient_gains_returns_zero(self):
        """Test behavior with insufficient gains for linear fallback."""
        gains = [1.0, 2.0]  # Only 2 gains, less than 4 needed
        surface = HigherOrderSlidingSurface(gains, order=1)

        test_state = np.array([0.1, 0.2, 0.05, 0.1, -0.03, -0.05])

        result = surface.compute(test_state)
        assert result == 0.0


class TestCreateSlidingSurfaceFactory:
    """Test suite for sliding surface factory function."""

    def test_create_linear_surface(self):
        """Test creation of linear sliding surface."""
        gains = [1.0, 2.0, 3.0, 4.0]
        surface = create_sliding_surface("linear", gains)

        assert isinstance(surface, LinearSlidingSurface)
        assert surface.k1 == 1.0
        assert surface.k2 == 2.0

    def test_create_higher_order_surface(self):
        """Test creation of higher-order sliding surface."""
        gains = [1.0, 2.0, 3.0, 4.0]
        surface = create_sliding_surface("higher_order", gains)

        assert isinstance(surface, HigherOrderSlidingSurface)
        assert surface.order == 2  # Default order

    def test_create_higher_order_surface_alternative_name(self):
        """Test creation with alternative naming."""
        gains = [1.0, 2.0, 3.0, 4.0]
        surface = create_sliding_surface("higher-order", gains)

        assert isinstance(surface, HigherOrderSlidingSurface)

    def test_case_insensitive_surface_type(self):
        """Test that surface type is case insensitive."""
        gains = [1.0, 2.0, 3.0, 4.0]

        surface_upper = create_sliding_surface("LINEAR", gains)
        surface_mixed = create_sliding_surface("Linear", gains)

        assert isinstance(surface_upper, LinearSlidingSurface)
        assert isinstance(surface_mixed, LinearSlidingSurface)

    def test_unknown_surface_type_error(self):
        """Test error with unknown surface type."""
        gains = [1.0, 2.0, 3.0, 4.0]

        with pytest.raises(ValueError, match="Unknown surface type: unknown"):
            create_sliding_surface("unknown", gains)


class TestSlidingSurfaceMathematicalProperties:
    """Test mathematical properties and edge cases."""

    @pytest.fixture
    def surface(self):
        """Create surface with known gains for mathematical tests."""
        return LinearSlidingSurface([1.0, 1.0, 1.0, 1.0])  # Unit gains for simplicity

    def test_surface_zero_at_equilibrium(self, surface):
        """Test that surface equals zero at upright equilibrium."""
        equilibrium_state = np.zeros(6)  # All angles and velocities zero
        result = surface.compute(equilibrium_state)

        assert result == 0.0

    def test_surface_symmetry(self, surface):
        """Test surface symmetry properties."""
        state_positive = np.array([0.0, 0.0, 0.1, 0.2, 0.1, 0.2])
        state_negative = -state_positive

        result_pos = surface.compute(state_positive)
        result_neg = surface.compute(state_negative)

        # Should be opposite signs due to linearity
        assert abs(result_pos + result_neg) < 1e-10

    def test_surface_continuity(self, surface):
        """Test surface continuity by checking small perturbations."""
        base_state = np.array([0.1, 0.2, 0.05, 0.1, -0.03, -0.05])
        small_perturbation = 1e-8 * np.ones(6)

        result_base = surface.compute(base_state)
        result_perturbed = surface.compute(base_state + small_perturbation)

        # Results should be very close for small perturbations
        assert abs(result_perturbed - result_base) < 1e-6

    def test_derivative_consistency(self, surface):
        """Test numerical vs analytical derivative consistency."""
        state = np.array([0.1, 0.2, 0.05, 0.1, -0.03, -0.05])
        state_dot = np.array([0.2, 0.5, 0.1, 0.8, -0.05, -0.6])

        # Analytical derivative
        analytical_deriv = surface.compute_derivative(state, state_dot)

        # Numerical derivative using finite differences
        dt = 1e-6
        state_next = state + dt * state_dot
        numerical_deriv = (surface.compute(state_next) - surface.compute(state)) / dt

        # Should be close (within numerical precision)
        assert abs(analytical_deriv - numerical_deriv) < 1e-6

    def test_large_state_values(self, surface):
        """Test surface computation with large state values."""
        large_state = np.array([100.0, 50.0, 1.0, 10.0, -2.0, -20.0])
        result = surface.compute(large_state)

        # Should handle large values without overflow
        assert np.isfinite(result)
        assert isinstance(result, float)

    def test_very_small_state_values(self, surface):
        """Test surface computation with very small state values."""
        tiny_state = np.array([1e-10, 1e-11, 1e-12, 1e-13, -1e-14, -1e-15])
        result = surface.compute(tiny_state)

        # Should handle tiny values without underflow
        assert np.isfinite(result)
        assert abs(result) < 1e-10  # Result should be proportionally small

    def test_nan_state_handling(self, surface):
        """Test behavior with NaN values in state."""
        nan_state = np.array([0.1, 0.2, np.nan, 0.1, -0.03, -0.05])
        result = surface.compute(nan_state)

        # NaN input should produce NaN output
        assert np.isnan(result)

    def test_infinite_state_handling(self, surface):
        """Test behavior with infinite values in state."""
        inf_state = np.array([0.1, 0.2, np.inf, 0.1, -0.03, -0.05])
        result = surface.compute(inf_state)

        # Infinite input should produce infinite result
        assert np.isinf(result)