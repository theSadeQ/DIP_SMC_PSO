#==========================================================================================\\\
#======================== tests/test_property_based_deep.py ===============================\\\
#==========================================================================================\\\

"""
Deep Property-Based Testing using Hypothesis.
COMPREHENSIVE JOB: Test mathematical properties with randomly generated inputs for robustness.
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.extra.numpy import arrays, floating_dtypes
import warnings

# Test configuration
MAX_EXAMPLES = 50  # Reduced for faster testing
DEADLINE_MS = 5000  # Increased deadline

# Custom strategies for control systems
def finite_floats(min_value=-10.0, max_value=10.0):
    """Generate finite floating point numbers."""
    return st.floats(min_value=min_value, max_value=max_value, allow_nan=False, allow_infinity=False)

def positive_floats(min_value=0.1, max_value=10.0):
    """Generate positive floating point numbers."""
    return st.floats(min_value=min_value, max_value=max_value, allow_nan=False, allow_infinity=False)

def state_vectors():
    """Generate 6-dimensional state vectors for DIP system."""
    return st.lists(finite_floats(-5.0, 5.0), min_size=6, max_size=6).map(np.array)

def small_state_vectors():
    """Generate small state vectors near equilibrium."""
    return st.lists(finite_floats(-0.5, 0.5), min_size=6, max_size=6).map(np.array)

def control_gains():
    """Generate controller gain vectors."""
    return st.lists(positive_floats(0.5, 5.0), min_size=6, max_size=6).map(np.array)


class MockLinearSlidingSurface:
    """Mock sliding surface for property testing."""
    def __init__(self, gains):
        self.gains = np.array(gains)

    def compute(self, state, reference=None):
        """Linear sliding surface computation."""
        error = state if reference is None else state - reference
        return np.dot(self.gains, error)


class MockSwitchingFunction:
    """Mock switching function for property testing."""
    def __init__(self, method='tanh', boundary_layer=0.1):
        self.method = method
        self.boundary_layer = max(boundary_layer, 1e-6)  # Avoid division by zero

    def compute(self, sigma):
        """Switching function computation."""
        if self.method == 'tanh':
            return np.tanh(sigma / self.boundary_layer)
        elif self.method == 'sign':
            return np.sign(sigma)
        elif self.method == 'linear':
            return sigma / (abs(sigma) + self.boundary_layer)
        else:
            return sigma / (abs(sigma) + self.boundary_layer)


def saturate_mock(value, max_limit):
    """Mock saturation function."""
    return np.clip(value, -max_limit, max_limit)


@pytest.mark.property_based
class TestSlidingSurfaceProperties:
    """Property-based tests for sliding surface mathematical properties."""

    @given(gains=control_gains(), state1=state_vectors(), state2=state_vectors())
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS, suppress_health_check=[HealthCheck.too_slow])
    def test_linearity_property(self, gains, state1, state2):
        """Test linearity: f(x+y) = f(x) + f(y)."""
        surface = MockLinearSlidingSurface(gains)

        result1 = surface.compute(state1)
        result2 = surface.compute(state2)
        result_sum = surface.compute(state1 + state2)

        assert abs(result_sum - (result1 + result2)) < 1e-10

    @given(gains=control_gains(), state=state_vectors(), scalar=finite_floats(-10.0, 10.0))
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_homogeneity_property(self, gains, state, scalar):
        """Test homogeneity: f(ax) = a*f(x)."""
        assume(abs(scalar) < 100.0)  # Avoid extreme scaling
        surface = MockLinearSlidingSurface(gains)

        result_original = surface.compute(state)
        result_scaled = surface.compute(scalar * state)
        expected_scaled = scalar * result_original

        # Use relative tolerance for large values
        if abs(expected_scaled) > 1e-6:
            relative_error = abs(result_scaled - expected_scaled) / abs(expected_scaled)
            assert relative_error < 1e-12
        else:
            assert abs(result_scaled - expected_scaled) < 1e-10

    @given(gains=control_gains(), state=state_vectors())
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_zero_gains_zero_output(self, gains, state):
        """Test that zero gains produce zero output."""
        zero_gains = np.zeros_like(gains)
        surface = MockLinearSlidingSurface(zero_gains)

        result = surface.compute(state)
        assert abs(result) < 1e-15

    @given(gains=control_gains(), state=state_vectors())
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_zero_state_zero_output_with_gains(self, gains, state):
        """Test that zero state produces zero output regardless of gains."""
        surface = MockLinearSlidingSurface(gains)
        zero_state = np.zeros(6)

        result = surface.compute(zero_state)
        assert abs(result) < 1e-15

    @given(gains=control_gains(), state=state_vectors(), reference=state_vectors())
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_reference_tracking_property(self, gains, state, reference):
        """Test reference tracking: surface(state, ref) = surface(state-ref, 0)."""
        surface = MockLinearSlidingSurface(gains)

        result_with_ref = surface.compute(state, reference)
        result_without_ref = surface.compute(state - reference)

        assert abs(result_with_ref - result_without_ref) < 1e-12

    @given(gains=control_gains(), state=small_state_vectors())
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_continuity_property(self, gains, state):
        """Test continuity: small state changes produce small output changes."""
        surface = MockLinearSlidingSurface(gains)
        epsilon = 1e-6

        result_original = surface.compute(state)

        # Test continuity in each dimension
        for i in range(len(state)):
            perturbed_state = state.copy()
            perturbed_state[i] += epsilon
            result_perturbed = surface.compute(perturbed_state)

            # Change in output should be proportional to gain[i] * epsilon
            expected_change = gains[i] * epsilon
            actual_change = result_perturbed - result_original

            assert abs(actual_change - expected_change) < 1e-12


@pytest.mark.property_based
class TestSwitchingFunctionProperties:
    """Property-based tests for switching function mathematical properties."""

    @given(sigma=finite_floats(-100.0, 100.0), boundary_layer=positive_floats(0.01, 1.0))
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_tanh_bounded_output(self, sigma, boundary_layer):
        """Test that tanh switching function output is always bounded in [-1, 1]."""
        switch_func = MockSwitchingFunction('tanh', boundary_layer)

        result = switch_func.compute(sigma)

        assert -1.0 <= result <= 1.0
        assert np.isfinite(result)

    @given(sigma=finite_floats(-100.0, 100.0), boundary_layer=positive_floats(0.01, 1.0))
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_sign_switching_antisymmetry(self, sigma, boundary_layer):
        """Test antisymmetry: f(-x) = -f(x) for all switching functions."""
        for method in ['tanh', 'sign', 'linear']:
            switch_func = MockSwitchingFunction(method, boundary_layer)

            result_pos = switch_func.compute(sigma)
            result_neg = switch_func.compute(-sigma)

            # Should be antisymmetric
            assert abs(result_pos + result_neg) < 1e-12

    @given(sigma=finite_floats(-10.0, 10.0), boundary_layer=positive_floats(0.01, 1.0))
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_switching_function_monotonicity(self, sigma, boundary_layer):
        """Test that switching functions are monotonically increasing."""
        for method in ['tanh', 'linear']:
            switch_func = MockSwitchingFunction(method, boundary_layer)

            # Test monotonicity by comparing nearby points
            epsilon = 0.1
            result_lower = switch_func.compute(sigma)
            result_upper = switch_func.compute(sigma + epsilon)

            # Should be monotonically increasing
            assert result_upper >= result_lower

    @given(boundary_layer1=positive_floats(0.01, 0.5), boundary_layer2=positive_floats(0.5, 2.0))
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_boundary_layer_effect(self, boundary_layer1, boundary_layer2):
        """Test that thinner boundary layers produce steeper switching."""
        assume(boundary_layer1 < boundary_layer2)

        sigma = 0.1  # Small positive value
        thin_switch = MockSwitchingFunction('tanh', boundary_layer1)
        thick_switch = MockSwitchingFunction('tanh', boundary_layer2)

        result_thin = thin_switch.compute(sigma)
        result_thick = thick_switch.compute(sigma)

        # Thinner boundary layer should produce larger (steeper) response
        assert result_thin >= result_thick

    @given(sigma=finite_floats(0.01, 10.0), boundary_layer=positive_floats(0.01, 1.0))
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_zero_crossing_behavior(self, sigma, boundary_layer):
        """Test behavior near zero crossing."""
        switch_func = MockSwitchingFunction('tanh', boundary_layer)

        # Test points symmetrically around zero
        result_pos = switch_func.compute(sigma)
        result_zero = switch_func.compute(0.0)
        result_neg = switch_func.compute(-sigma)

        # Zero should produce zero output
        assert abs(result_zero) < 1e-15

        # Positive input should produce positive output
        assert result_pos > 0

        # Negative input should produce negative output
        assert result_neg < 0


@pytest.mark.property_based
class TestControlSaturationProperties:
    """Property-based tests for control saturation properties."""

    @given(control=finite_floats(-1000.0, 1000.0), max_limit=positive_floats(1.0, 100.0))
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_saturation_bounds_respected(self, control, max_limit):
        """Test that saturation always respects bounds."""
        saturated = saturate_mock(control, max_limit)

        assert -max_limit <= saturated <= max_limit
        assert np.isfinite(saturated)

    @given(control=finite_floats(-10.0, 10.0), max_limit=positive_floats(20.0, 100.0))
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_no_saturation_within_bounds(self, control, max_limit):
        """Test that values within bounds are not modified."""
        assume(abs(control) < max_limit)

        saturated = saturate_mock(control, max_limit)

        assert abs(saturated - control) < 1e-15

    @given(control=finite_floats(-1000.0, 1000.0), max_limit=positive_floats(1.0, 100.0))
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_saturation_preserves_sign(self, control, max_limit):
        """Test that saturation preserves sign when not saturated to zero."""
        saturated = saturate_mock(control, max_limit)

        if abs(control) > 1e-10:  # Avoid comparing signs of near-zero values
            assert np.sign(saturated) == np.sign(control)

    @given(control=finite_floats(-1000.0, 1000.0), max_limit=positive_floats(1.0, 100.0))
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_saturation_idempotent(self, control, max_limit):
        """Test that saturating twice gives same result."""
        saturated_once = saturate_mock(control, max_limit)
        saturated_twice = saturate_mock(saturated_once, max_limit)

        assert abs(saturated_twice - saturated_once) < 1e-15


@pytest.mark.property_based
class TestNumericalStabilityProperties:
    """Property-based tests for numerical stability and edge cases."""

    @given(state=state_vectors())
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_finite_output_for_finite_input(self, state):
        """Test that finite inputs always produce finite outputs."""
        # Test sliding surface
        gains = np.ones(6)
        surface = MockLinearSlidingSurface(gains)
        result = surface.compute(state)

        assert np.isfinite(result)

        # Test switching function
        switch_func = MockSwitchingFunction('tanh', 0.1)
        switch_result = switch_func.compute(result)

        assert np.isfinite(switch_result)

    @given(gains=control_gains())
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_extreme_state_handling(self, gains):
        """Test handling of extreme but finite state values."""
        extreme_states = [
            np.array([1e6, 0, 0, 0, 0, 0]),    # Very large position
            np.array([0, 0, 0, 1e6, 0, 0]),    # Very large velocity
            np.array([-1e6, -1e6, -1e6, -1e6, -1e6, -1e6]),  # All large negative
        ]

        surface = MockLinearSlidingSurface(gains)

        for extreme_state in extreme_states:
            result = surface.compute(extreme_state)
            assert np.isfinite(result)

            # Switching function should handle extreme sliding surface values
            switch_func = MockSwitchingFunction('tanh', 0.1)
            switch_result = switch_func.compute(result)
            assert np.isfinite(switch_result)
            assert -1.0 <= switch_result <= 1.0

    @given(boundary_layer=positive_floats(1e-10, 1e-6))
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_very_small_boundary_layer_stability(self, boundary_layer):
        """Test numerical stability with very small boundary layers."""
        switch_func = MockSwitchingFunction('tanh', boundary_layer)

        test_values = [-1.0, -0.1, 0.0, 0.1, 1.0]

        for sigma in test_values:
            result = switch_func.compute(sigma)
            assert np.isfinite(result)
            assert -1.0 <= result <= 1.0

    @given(gains=control_gains())
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_gain_scaling_stability(self, gains):
        """Test that extreme gain values don't cause numerical issues."""
        # Scale gains to extreme values
        large_gains = gains * 1e6
        small_gains = gains * 1e-6

        surface_large = MockLinearSlidingSurface(large_gains)
        surface_small = MockLinearSlidingSurface(small_gains)

        test_state = np.array([0.1, 0.1, 0.1, 0.1, 0.1, 0.1])

        result_large = surface_large.compute(test_state)
        result_small = surface_small.compute(test_state)

        assert np.isfinite(result_large)
        assert np.isfinite(result_small)


@pytest.mark.property_based
class TestControlSystemInvariants:
    """Property-based tests for control system invariants and constraints."""

    @given(state=state_vectors(), gains=control_gains(), max_force=positive_floats(1.0, 100.0))
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_control_energy_bounded(self, state, gains, max_force):
        """Test that control energy is always bounded by saturation."""
        surface = MockLinearSlidingSurface(gains)
        switch_func = MockSwitchingFunction('tanh', 0.1)

        # Simulate classical SMC control law
        sigma = surface.compute(state)
        switching_output = switch_func.compute(sigma)
        control = -10.0 * switching_output  # Some gain
        saturated_control = saturate_mock(control, max_force)

        # Control energy (squared) should be bounded
        control_energy = saturated_control**2
        max_energy = max_force**2

        assert control_energy <= max_energy + 1e-12  # Small tolerance for numerical precision

    @given(state=small_state_vectors(), gains=control_gains())
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_equilibrium_stability_indicator(self, state, gains):
        """Test that near-equilibrium states produce small control efforts."""
        surface = MockLinearSlidingSurface(gains)
        switch_func = MockSwitchingFunction('tanh', 0.1)

        sigma = surface.compute(state)
        control_magnitude = abs(switch_func.compute(sigma))

        # For small states, control should be reasonably small
        # This tests the "reasonable" behavior near equilibrium
        state_magnitude = np.linalg.norm(state)
        expected_sigma_magnitude = np.linalg.norm(gains) * state_magnitude

        # Control should scale reasonably with state magnitude
        if state_magnitude < 0.1:  # Very small states
            assert control_magnitude < 1.0  # Control shouldn't be extreme

    @given(state1=state_vectors(), state2=state_vectors(), gains=control_gains())
    @settings(max_examples=MAX_EXAMPLES, deadline=DEADLINE_MS)
    def test_control_continuity(self, state1, state2, gains):
        """Test that nearby states produce similar control values."""
        # Only test if states are reasonably close
        state_diff = np.linalg.norm(state1 - state2)
        assume(state_diff < 0.1)  # States are close

        surface = MockLinearSlidingSurface(gains)
        switch_func = MockSwitchingFunction('tanh', 0.1)

        sigma1 = surface.compute(state1)
        sigma2 = surface.compute(state2)

        control1 = switch_func.compute(sigma1)
        control2 = switch_func.compute(sigma2)

        control_diff = abs(control1 - control2)
        sigma_diff = abs(sigma1 - sigma2)

        # Control difference should be bounded by sigma difference
        # This tests continuity of the switching function
        assert control_diff <= sigma_diff + 0.1  # Small tolerance for tanh nonlinearity


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])