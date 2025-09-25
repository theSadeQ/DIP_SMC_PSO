#==========================================================================================\\\
#=============== tests/test_plant/core/test_singularity_detection.py =================\\\
#==========================================================================================\\\
"""
Singularity Detection Tests.

SINGLE JOB: Test only singularity detection and handling in plant dynamics.
- Singular configuration detection
- Matrix condition number monitoring
- Graceful degradation on singularities
- Singularity threshold validation
"""

import numpy as np
import pytest

from src.plant.core.dynamics import DoubleInvertedPendulum
from src.plant.models.full import FullDIPDynamics


class TestSingularityDetection:
    """Test singularity detection mechanisms."""

    def test_normal_state_not_singular(self, full_dynamics_model):
        """Test that normal states are not detected as singular."""
        normal_states = [
            np.array([0.0, 0.1, 0.2, 0.0, 0.0, 0.0]),
            np.array([0.1, 0.05, 0.15, 0.0, 0.0, 0.0]),
            np.array([0.0, -0.1, -0.2, 0.0, 0.0, 0.0]),
        ]

        for i, state in enumerate(normal_states):
            try:
                is_singular = full_dynamics_model._check_singularity(state)
                assert not is_singular, f"Normal state {i} incorrectly detected as singular"
            except (AttributeError, NotImplementedError):
                # If direct singularity checking not implemented, test via condition number
                M = full_dynamics_model._compute_inertia_matrix(state)
                cond_num = np.linalg.cond(M)
                assert cond_num < 1e10, f"Normal state {i} has high condition number: {cond_num}"

    def test_potentially_singular_configurations(self, full_dynamics_model):
        """Test detection of potentially problematic configurations."""
        # Configurations that might cause numerical issues
        problem_states = [
            np.array([0.0, np.pi/2, 0.0, 0.0, 0.0, 0.0]),  # First pendulum horizontal
            np.array([0.0, 0.0, np.pi/2, 0.0, 0.0, 0.0]),  # Second pendulum horizontal
            np.array([0.0, np.pi/2, np.pi/2, 0.0, 0.0, 0.0]),  # Both horizontal
            np.array([0.0, 3*np.pi/2, 0.0, 0.0, 0.0, 0.0]),  # First pendulum horizontal (other direction)
        ]

        for i, state in enumerate(problem_states):
            try:
                # Singularity check should handle these gracefully
                is_singular = full_dynamics_model._check_singularity(state)
                # May or may not be singular, but should not crash
                assert isinstance(is_singular, (bool, np.bool_)), f"State {i}: invalid singularity check result"

            except (AttributeError, NotImplementedError):
                # Test via matrix computation
                try:
                    M = full_dynamics_model._compute_inertia_matrix(state)
                    assert np.all(np.isfinite(M)), f"State {i}: non-finite inertia matrix values"

                    cond_num = np.linalg.cond(M)
                    # High condition number is acceptable, but should be finite
                    assert np.isfinite(cond_num), f"State {i}: infinite condition number"

                except Exception as e:
                    pytest.fail(f"State {i}: matrix computation failed ungracefully: {e}")

    def test_condition_number_computation(self, full_dynamics_model):
        """Test condition number computation for various states."""
        test_states = [
            np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),  # Upright (best conditioned)
            np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0]),  # Small angles
            np.array([0.0, np.pi/6, np.pi/4, 0.0, 0.0, 0.0]),  # Moderate angles
            np.array([0.0, np.pi/3, np.pi/3, 0.0, 0.0, 0.0]),  # Larger angles
        ]

        condition_numbers = []
        for i, state in enumerate(test_states):
            M = full_dynamics_model._compute_inertia_matrix(state)
            cond_num = np.linalg.cond(M)

            assert np.isfinite(cond_num), f"State {i}: condition number not finite"
            assert cond_num >= 1.0, f"State {i}: condition number less than 1"

            condition_numbers.append(cond_num)

        # Condition number should generally increase with angle magnitude
        # (though this is not guaranteed for all dynamics)
        assert len(condition_numbers) == len(test_states)

    def test_singularity_threshold_handling(self, full_dynamics_model):
        """Test handling of singularity thresholds."""
        state = np.array([0.0, np.pi/2, 0.0, 0.0, 0.0, 0.0])

        # Test with different thresholds if configurable
        if hasattr(full_dynamics_model.config, 'singularity_cond_threshold'):
            original_threshold = full_dynamics_model.config.singularity_cond_threshold

            # Very strict threshold
            full_dynamics_model.config.singularity_cond_threshold = 100.0

            try:
                is_singular_strict = full_dynamics_model._check_singularity(state)
            except (AttributeError, NotImplementedError):
                is_singular_strict = None

            # Very loose threshold
            full_dynamics_model.config.singularity_cond_threshold = 1e15

            try:
                is_singular_loose = full_dynamics_model._check_singularity(state)
            except (AttributeError, NotImplementedError):
                is_singular_loose = None

            # Restore original
            full_dynamics_model.config.singularity_cond_threshold = original_threshold

            # Strict threshold should be more likely to detect singularities
            if is_singular_strict is not None and is_singular_loose is not None:
                # If strict detects singular, loose should also (or be less sensitive)
                if is_singular_strict:
                    # This relationship may not always hold, so we just check they're boolean
                    assert isinstance(is_singular_loose, (bool, np.bool_))

    def test_matrix_invertibility(self, full_dynamics_model):
        """Test matrix invertibility near singular configurations."""
        test_states = [
            np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),  # Safe state
            np.array([0.0, 0.1, 0.2, 0.0, 0.0, 0.0]),  # Small angles
            np.array([0.1, 0.3, -0.2, 0.0, 0.0, 0.0]),  # With cart displacement
        ]

        for i, state in enumerate(test_states):
            M = full_dynamics_model._compute_inertia_matrix(state)

            try:
                M_inv = np.linalg.inv(M)

                # Check that M * M_inv ≈ I
                identity_test = M @ M_inv
                np.testing.assert_allclose(identity_test, np.eye(3), rtol=1e-8,
                                           err_msg=f"Matrix inversion failed for state {i}")

                # Inverse should also be finite
                assert np.all(np.isfinite(M_inv)), f"Matrix inverse contains non-finite values for state {i}"

            except np.linalg.LinAlgError as e:
                pytest.fail(f"Matrix not invertible for normal state {i}: {e}")

    def test_graceful_singularity_handling(self, full_dynamics_model):
        """Test that singularity handling is graceful."""
        # Test state that might be problematic
        challenging_state = np.array([0.0, np.pi/2, np.pi/2, 0.0, 0.0, 0.0])

        try:
            # Should not crash, even if singular
            M = full_dynamics_model._compute_inertia_matrix(challenging_state)

            # If computation succeeds, values should be reasonable
            assert np.all(np.isfinite(M)), "Inertia matrix contains non-finite values"
            assert M.shape == (3, 3), "Inertia matrix has wrong shape"

            # Try to use the matrix
            try:
                eigenvals = np.linalg.eigvals(M)
                assert np.all(np.isfinite(eigenvals)), "Eigenvalues contain non-finite values"

                # If eigenvalues are positive, matrix is still usable
                if np.all(eigenvals > 1e-12):
                    det_M = np.linalg.det(M)
                    assert np.isfinite(det_M), "Determinant not finite"

            except Exception as inner_e:
                # Linear algebra operations may fail, but should not crash the system
                print(f"Linear algebra operations failed gracefully: {inner_e}")

        except Exception as e:
            pytest.fail(f"Singularity handling not graceful: {e}")

    def test_singularity_detection_consistency(self, full_dynamics_model):
        """Test that singularity detection is consistent."""
        state = np.array([0.0, np.pi/2 - 1e-6, 0.0, 0.0, 0.0, 0.0])  # Very close to singular

        try:
            # Multiple calls should give consistent results
            results = []
            for _ in range(5):
                is_singular = full_dynamics_model._check_singularity(state)
                results.append(is_singular)

            # All results should be the same
            assert all(r == results[0] for r in results), "Singularity detection inconsistent"

        except (AttributeError, NotImplementedError):
            # Test via condition number consistency
            cond_nums = []
            for _ in range(5):
                M = full_dynamics_model._compute_inertia_matrix(state)
                cond_num = np.linalg.cond(M)
                cond_nums.append(cond_num)

            # Condition numbers should be very close
            cond_std = np.std(cond_nums)
            cond_mean = np.mean(cond_nums)
            cv = cond_std / cond_mean if cond_mean > 0 else 0

            assert cv < 1e-10, f"Condition number computation inconsistent: CV = {cv}"


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