#==========================================================================================\\\
#=============== tests/test_plant/core/test_inertia_matrix.py ========================\\\
#==========================================================================================\\\
"""
Inertia Matrix Properties Tests.

SINGLE JOB: Test only inertia matrix mathematical properties and computation.
- Matrix symmetry verification
- Positive definiteness testing
- Configuration dependence
- Mass parameter scaling
"""

import numpy as np
import pytest

from src.plant.core.dynamics import DoubleInvertedPendulum
from src.plant.models.full import FullDIPDynamics


class TestInertiaMatrixSymmetry:
    """Test inertia matrix symmetry properties."""

    def test_inertia_matrix_symmetry(self, full_dynamics_model):
        """Test that the inertia matrix is symmetric."""
        state = np.array([0.0, 0.1, 0.2, 0.0, 0.0, 0.0])

        M = full_dynamics_model._compute_inertia_matrix(state)

        # Check symmetry
        np.testing.assert_allclose(M, M.T, rtol=1e-10, atol=1e-12,
                                   err_msg="Inertia matrix should be symmetric")

    def test_symmetry_across_configurations(self, full_dynamics_model):
        """Test symmetry holds for different configurations."""
        test_states = [
            np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),  # Upright
            np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0]),  # Angled
            np.array([0.0, np.pi/2, 0.0, 0.0, 0.0, 0.0]),  # First pendulum horizontal
            np.array([0.0, 0.0, np.pi/2, 0.0, 0.0, 0.0]),  # Second pendulum horizontal
        ]

        for i, state in enumerate(test_states):
            M = full_dynamics_model._compute_inertia_matrix(state)

            np.testing.assert_allclose(M, M.T, rtol=1e-10, atol=1e-12,
                                       err_msg=f"Inertia matrix not symmetric for state {i}")

    def test_symmetry_with_extreme_angles(self, full_dynamics_model):
        """Test symmetry with extreme pendulum angles."""
        extreme_states = [
            np.array([0.0, np.pi, 0.0, 0.0, 0.0, 0.0]),  # First pendulum down
            np.array([0.0, 0.0, np.pi, 0.0, 0.0, 0.0]),  # Second pendulum down
            np.array([0.0, np.pi, np.pi, 0.0, 0.0, 0.0]),  # Both down
            np.array([2.0, 2*np.pi, -np.pi, 0.0, 0.0, 0.0]),  # Large cart displacement
        ]

        for i, state in enumerate(extreme_states):
            M = full_dynamics_model._compute_inertia_matrix(state)

            np.testing.assert_allclose(M, M.T, rtol=1e-10, atol=1e-12,
                                       err_msg=f"Inertia matrix not symmetric for extreme state {i}")


class TestInertiaMatrixPositiveDefiniteness:
    """Test inertia matrix positive definiteness."""

    def test_positive_definiteness(self, full_dynamics_model):
        """Test that inertia matrix is positive definite."""
        state = np.array([0.0, 0.1, 0.2, 0.0, 0.0, 0.0])

        M = full_dynamics_model._compute_inertia_matrix(state)

        # Check positive definiteness (all eigenvalues > 0)
        eigenvalues = np.linalg.eigvals(M)
        assert np.all(eigenvalues > 0), f"Inertia matrix should be positive definite, got eigenvalues: {eigenvalues}"

    def test_positive_definiteness_multiple_states(self, full_dynamics_model):
        """Test positive definiteness across multiple configurations."""
        test_states = [
            np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0]),
            np.array([0.0, np.pi/4, np.pi/6, 0.0, 0.0, 0.0]),
            np.array([0.5, np.pi/3, -np.pi/4, 0.0, 0.0, 0.0]),
        ]

        for i, state in enumerate(test_states):
            M = full_dynamics_model._compute_inertia_matrix(state)
            eigenvalues = np.linalg.eigvals(M)

            assert np.all(eigenvalues > 0), f"State {i}: eigenvalues {eigenvalues} not all positive"

    def test_minimum_eigenvalue_bounds(self, full_dynamics_model):
        """Test that minimum eigenvalue is reasonably bounded."""
        state = np.array([0.0, 0.1, 0.2, 0.0, 0.0, 0.0])

        M = full_dynamics_model._compute_inertia_matrix(state)
        eigenvalues = np.linalg.eigvals(M)
        min_eigenvalue = np.min(eigenvalues)

        # Should be bounded away from zero
        assert min_eigenvalue > 1e-6, f"Minimum eigenvalue too small: {min_eigenvalue}"

    def test_condition_number_bounds(self, full_dynamics_model):
        """Test that condition number is reasonable."""
        state = np.array([0.0, 0.1, 0.2, 0.0, 0.0, 0.0])

        M = full_dynamics_model._compute_inertia_matrix(state)
        cond_num = np.linalg.cond(M)

        # Should be well-conditioned for normal states
        assert cond_num < 1e8, f"Condition number too high: {cond_num}"


class TestInertiaMatrixShape:
    """Test inertia matrix shape and structure."""

    def test_matrix_shape(self, full_dynamics_model):
        """Test that inertia matrix has correct shape."""
        state = np.array([0.0, 0.1, 0.2, 0.0, 0.0, 0.0])

        M = full_dynamics_model._compute_inertia_matrix(state)

        # Should be 3x3 for cart + 2 pendulums
        assert M.shape == (3, 3), f"Expected 3x3 inertia matrix, got {M.shape}"

    def test_matrix_data_type(self, full_dynamics_model):
        """Test that inertia matrix has correct data type."""
        state = np.array([0.0, 0.1, 0.2, 0.0, 0.0, 0.0])

        M = full_dynamics_model._compute_inertia_matrix(state)

        assert isinstance(M, np.ndarray), "Inertia matrix should be numpy array"
        assert np.issubdtype(M.dtype, np.floating), "Inertia matrix should have floating point type"

    def test_finite_values(self, full_dynamics_model):
        """Test that all matrix elements are finite."""
        state = np.array([0.0, 0.1, 0.2, 0.0, 0.0, 0.0])

        M = full_dynamics_model._compute_inertia_matrix(state)

        assert np.all(np.isfinite(M)), "All inertia matrix elements should be finite"

    def test_non_zero_diagonal(self, full_dynamics_model):
        """Test that diagonal elements are non-zero."""
        state = np.array([0.0, 0.1, 0.2, 0.0, 0.0, 0.0])

        M = full_dynamics_model._compute_inertia_matrix(state)

        diagonal = np.diag(M)
        assert np.all(diagonal > 0), f"Diagonal elements should be positive: {diagonal}"


class TestInertiaMatrixScaling:
    """Test inertia matrix scaling properties."""

    def test_mass_scaling_proportionality(self, full_dynamics_model):
        """Test that inertia matrix scales proportionally with mass."""
        state = np.array([0.0, 0.1, 0.2, 0.0, 0.0, 0.0])

        # Get baseline inertia matrix
        M_baseline = full_dynamics_model._compute_inertia_matrix(state)

        # Scale all masses by factor of 2
        original_cart_mass = full_dynamics_model.config.cart_mass
        original_pend1_mass = full_dynamics_model.config.pendulum1_mass
        original_pend2_mass = full_dynamics_model.config.pendulum2_mass

        scale_factor = 2.0
        full_dynamics_model.config.cart_mass *= scale_factor
        full_dynamics_model.config.pendulum1_mass *= scale_factor
        full_dynamics_model.config.pendulum2_mass *= scale_factor

        M_scaled = full_dynamics_model._compute_inertia_matrix(state)

        # Restore original values
        full_dynamics_model.config.cart_mass = original_cart_mass
        full_dynamics_model.config.pendulum1_mass = original_pend1_mass
        full_dynamics_model.config.pendulum2_mass = original_pend2_mass

        # Check proportional scaling
        np.testing.assert_allclose(M_scaled, scale_factor * M_baseline, rtol=1e-10,
                                   err_msg="Inertia matrix should scale proportionally with mass")

    def test_individual_mass_effects(self, full_dynamics_model):
        """Test effects of scaling individual masses."""
        state = np.array([0.0, 0.1, 0.2, 0.0, 0.0, 0.0])

        # Baseline matrix
        M_baseline = full_dynamics_model._compute_inertia_matrix(state)

        # Scale only cart mass
        original_cart_mass = full_dynamics_model.config.cart_mass
        full_dynamics_model.config.cart_mass *= 2.0

        M_cart_scaled = full_dynamics_model._compute_inertia_matrix(state)
        full_dynamics_model.config.cart_mass = original_cart_mass

        # Matrices should be different
        assert not np.allclose(M_baseline, M_cart_scaled, rtol=1e-6), \
            "Cart mass scaling should affect inertia matrix"

        # Cart affects primarily the first diagonal element
        assert M_cart_scaled[0, 0] > M_baseline[0, 0], \
            "Cart mass should increase first diagonal element"


@pytest.fixture
def full_dynamics_model():
    """Fixture providing full dynamics model for testing."""
    try:
        from src.plant.models.full import FullDIPDynamics
        from src.plant.configurations import create_default_config

        config = create_default_config("full")
        return FullDIPDynamics(config)

    except ImportError:
        pytest.skip("Full dynamics model not available")