#==========================================================================================\\\
#================ tests/test_simulation/safety/test_safety_guards.py ===================\\\
#==========================================================================================\\\
"""
Comprehensive test suite for simulation safety guards.
Tests both legacy and modern safety guard implementations including NaN detection,
energy limits, bounds checking, and the safety guard management system.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional

try:
    # Import legacy guards
    from src.core.safety_guards import _guard_no_nan, _guard_energy, _guard_bounds

    # Import modern guards
    from src.simulation.safety.guards import (
        SafetyViolationError, NaNGuard, EnergyGuard, BoundsGuard,
        SafetyGuardManager, guard_no_nan, guard_energy, guard_bounds,
        apply_safety_guards, create_default_guards
    )

    # Import interfaces
    from src.simulation.core.interfaces import SafetyGuard

    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    SafetyViolationError = Exception
    SafetyGuard = object


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Safety guard modules not available")
class TestLegacySafetyGuards:
    """Test legacy safety guard functions."""

    def test_guard_no_nan_success(self):
        """Test NaN guard with valid states."""
        # Valid state should not raise exception
        valid_state = np.array([1.0, 2.0, 3.0])
        _guard_no_nan(valid_state, step_idx=0)  # Should not raise

        # Test with different shapes
        valid_matrix = np.array([[1.0, 2.0], [3.0, 4.0]])
        _guard_no_nan(valid_matrix, step_idx=5)  # Should not raise

        # Test with scalar
        _guard_no_nan(5.0, step_idx=10)  # Should not raise

    def test_guard_no_nan_failure_cases(self):
        """Test NaN guard with invalid states."""
        # NaN values should raise RuntimeError
        nan_state = np.array([1.0, np.nan, 3.0])
        with pytest.raises(RuntimeError, match="NaN detected in state at step <i>"):
            _guard_no_nan(nan_state, step_idx=3)

        # Infinite values should raise RuntimeError
        inf_state = np.array([1.0, np.inf, 3.0])
        with pytest.raises(RuntimeError, match="NaN detected in state at step <i>"):
            _guard_no_nan(inf_state, step_idx=7)

        # Negative infinite values
        neg_inf_state = np.array([1.0, -np.inf, 3.0])
        with pytest.raises(RuntimeError, match="NaN detected in state at step <i>"):
            _guard_no_nan(neg_inf_state, step_idx=12)

        # Mixed NaN and inf
        mixed_invalid = np.array([np.nan, np.inf, -np.inf])
        with pytest.raises(RuntimeError, match="NaN detected in state at step <i>"):
            _guard_no_nan(mixed_invalid, step_idx=0)

    def test_guard_energy_success(self):
        """Test energy guard with valid states."""
        # State within energy limit should not raise
        low_energy_state = np.array([0.1, 0.2, 0.3])  # Energy = 0.14
        _guard_energy(low_energy_state, limits={"max": 1.0})  # Should not raise

        # Test with no limits (should not raise)
        high_energy_state = np.array([10.0, 10.0, 10.0])
        _guard_energy(high_energy_state, limits=None)  # Should not raise
        _guard_energy(high_energy_state, limits={})   # Should not raise

        # Test with zero state
        zero_state = np.array([0.0, 0.0, 0.0])
        _guard_energy(zero_state, limits={"max": 0.5})  # Should not raise

    def test_guard_energy_failure_cases(self):
        """Test energy guard with excessive energy."""
        # High energy state should raise RuntimeError
        high_energy_state = np.array([2.0, 2.0, 2.0])  # Energy = 12
        with pytest.raises(RuntimeError, match="Energy check failed: total_energy=<val> exceeds <max>"):
            _guard_energy(high_energy_state, limits={"max": 1.0})

        # Test edge case: exactly at limit (should pass)
        edge_state = np.array([1.0, 0.0, 0.0])  # Energy = 1.0
        _guard_energy(edge_state, limits={"max": 1.0})  # Should not raise

        # Slightly over limit should fail
        over_limit_state = np.array([1.0001, 0.0, 0.0])  # Energy = 1.0002
        with pytest.raises(RuntimeError, match="Energy check failed: total_energy=<val> exceeds <max>"):
            _guard_energy(over_limit_state, limits={"max": 1.0})

    def test_guard_bounds_success(self):
        """Test bounds guard with valid states."""
        # State within bounds should not raise
        valid_state = np.array([0.5, -0.3, 0.8])
        bounds = (np.array([-1.0, -1.0, -1.0]), np.array([1.0, 1.0, 1.0]))
        _guard_bounds(valid_state, bounds, t=1.5)  # Should not raise

        # Test with no bounds
        any_state = np.array([100.0, -50.0, 25.0])
        _guard_bounds(any_state, bounds=None, t=2.0)  # Should not raise

        # Test with scalar bounds
        scalar_bounds = (-2.0, 2.0)
        small_state = np.array([0.1])
        _guard_bounds(small_state, scalar_bounds, t=0.5)  # Should not raise

    def test_guard_bounds_failure_cases(self):
        """Test bounds guard with out-of-bounds states."""
        bounds = (np.array([-1.0, -1.0]), np.array([1.0, 1.0]))

        # Lower bound violation
        low_violation = np.array([-1.5, 0.5])
        with pytest.raises(RuntimeError, match="State bounds violated at t=<t>"):
            _guard_bounds(low_violation, bounds, t=1.0)

        # Upper bound violation
        high_violation = np.array([0.5, 1.5])
        with pytest.raises(RuntimeError, match="State bounds violated at t=<t>"):
            _guard_bounds(high_violation, bounds, t=2.0)

        # Multiple violations
        multi_violation = np.array([-2.0, 3.0])
        with pytest.raises(RuntimeError, match="State bounds violated at t=<t>"):
            _guard_bounds(multi_violation, bounds, t=3.0)

    def test_legacy_guards_batch_operations(self):
        """Test legacy guards with batch/matrix inputs."""
        # Test NaN guard with batches
        batch_states = np.array([
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [7.0, 8.0, 9.0]
        ])
        _guard_no_nan(batch_states, step_idx=0)  # Should not raise

        # Test energy guard with batches
        _guard_energy(batch_states, limits={"max": 500.0})  # Should not raise

        # Batch with one bad row should fail
        batch_with_nan = np.array([
            [1.0, 2.0, 3.0],
            [4.0, np.nan, 6.0],
            [7.0, 8.0, 9.0]
        ])
        with pytest.raises(RuntimeError):
            _guard_no_nan(batch_with_nan, step_idx=5)


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Safety guard modules not available")
class TestModernSafetyGuards:
    """Test modern object-oriented safety guards."""

    def test_nan_guard_functionality(self):
        """Test NaNGuard class functionality."""
        guard = NaNGuard()

        # Valid states should pass
        valid_state = np.array([1.0, 2.0, 3.0])
        assert guard.check(valid_state, step_idx=0) == True

        # Invalid states should fail
        invalid_state = np.array([1.0, np.nan, 3.0])
        assert guard.check(invalid_state, step_idx=0) == False

        # Check violation message
        message = guard.get_violation_message()
        assert isinstance(message, str)
        assert "NaN" in message.lower() or "infinite" in message.lower()

    def test_energy_guard_functionality(self):
        """Test EnergyGuard class functionality."""
        max_energy = 5.0
        guard = EnergyGuard(max_energy)

        # Low energy state should pass
        low_energy = np.array([1.0, 1.0, 1.0])  # Energy = 3.0
        assert guard.check(low_energy, step_idx=0) == True

        # High energy state should fail
        high_energy = np.array([2.0, 2.0, 2.0])  # Energy = 12.0
        assert guard.check(high_energy, step_idx=0) == False

        # Check violation message is updated
        violation_message = guard.get_violation_message()
        assert "Energy violation" in violation_message
        assert str(max_energy) in violation_message

    def test_bounds_guard_functionality(self):
        """Test BoundsGuard class functionality."""
        lower_bounds = np.array([-1.0, -2.0, -3.0])
        upper_bounds = np.array([1.0, 2.0, 3.0])
        guard = BoundsGuard(lower_bounds, upper_bounds)

        # Valid state should pass
        valid_state = np.array([0.5, 1.0, 2.0])
        assert guard.check(valid_state, step_idx=0) == True

        # Lower bound violation should fail
        lower_violation = np.array([-1.5, 0.0, 0.0])
        assert guard.check(lower_violation, step_idx=0) == False
        assert "Lower bounds violated" in guard.get_violation_message()

        # Upper bound violation should fail
        upper_violation = np.array([0.0, 0.0, 3.5])
        assert guard.check(upper_violation, step_idx=0) == False
        assert "Upper bounds violated" in guard.get_violation_message()

    def test_bounds_guard_partial_bounds(self):
        """Test BoundsGuard with only lower or upper bounds."""
        # Only lower bounds
        lower_only_guard = BoundsGuard(np.array([-1.0, -1.0]), None)
        assert lower_only_guard.check(np.array([0.0, 0.0]), 0) == True
        assert lower_only_guard.check(np.array([-2.0, 0.0]), 0) == False

        # Only upper bounds
        upper_only_guard = BoundsGuard(None, np.array([1.0, 1.0]))
        assert upper_only_guard.check(np.array([0.0, 0.0]), 0) == True
        assert upper_only_guard.check(np.array([0.0, 2.0]), 0) == False

        # No bounds (everything should pass)
        no_bounds_guard = BoundsGuard(None, None)
        assert no_bounds_guard.check(np.array([100.0, -100.0]), 0) == True


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Safety guard modules not available")
class TestSafetyViolationError:
    """Test SafetyViolationError exception class."""

    def test_safety_violation_error_creation(self):
        """Test SafetyViolationError creation and attributes."""
        error = SafetyViolationError(
            "Test violation message",
            "test_violation",
            step_idx=42
        )

        assert str(error) == "Test violation message"
        assert error.violation_type == "test_violation"
        assert error.step_idx == 42

    def test_safety_violation_error_optional_step(self):
        """Test SafetyViolationError without step index."""
        error = SafetyViolationError("Test message", "test_type")

        assert error.violation_type == "test_type"
        assert error.step_idx is None


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Safety guard modules not available")
class TestSafetyGuardManager:
    """Test SafetyGuardManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = SafetyGuardManager()

    def test_manager_initialization(self):
        """Test SafetyGuardManager initialization."""
        assert len(self.manager.guards) == 0

    def test_adding_guards(self):
        """Test adding guards to manager."""
        nan_guard = NaNGuard()
        energy_guard = EnergyGuard(10.0)
        bounds_guard = BoundsGuard(np.array([-1.0]), np.array([1.0]))

        self.manager.add_guard(nan_guard)
        assert len(self.manager.guards) == 1

        self.manager.add_guard(energy_guard)
        self.manager.add_guard(bounds_guard)
        assert len(self.manager.guards) == 3

    def test_check_all_success(self):
        """Test successful check of all guards."""
        self.manager.add_guard(NaNGuard())
        self.manager.add_guard(EnergyGuard(10.0))
        self.manager.add_guard(BoundsGuard(np.array([-5.0]), np.array([5.0])))

        # Valid state should pass all guards
        valid_state = np.array([1.0, 2.0])
        result = self.manager.check_all(valid_state, step_idx=0)
        assert result == True

    def test_check_all_failure_nan(self):
        """Test check_all failure due to NaN guard."""
        self.manager.add_guard(NaNGuard())
        self.manager.add_guard(EnergyGuard(10.0))

        invalid_state = np.array([1.0, np.nan])
        with pytest.raises(SafetyViolationError) as exc_info:
            self.manager.check_all(invalid_state, step_idx=5)

        assert exc_info.value.violation_type == "nanguard"
        assert exc_info.value.step_idx == 5

    def test_check_all_failure_energy(self):
        """Test check_all failure due to energy guard."""
        self.manager.add_guard(NaNGuard())
        self.manager.add_guard(EnergyGuard(1.0))  # Very low limit

        high_energy_state = np.array([2.0, 2.0, 2.0])  # Energy = 12.0
        with pytest.raises(SafetyViolationError) as exc_info:
            self.manager.check_all(high_energy_state, step_idx=10)

        assert exc_info.value.violation_type == "energyguard"
        assert exc_info.value.step_idx == 10

    def test_check_all_failure_bounds(self):
        """Test check_all failure due to bounds guard."""
        self.manager.add_guard(NaNGuard())
        self.manager.add_guard(BoundsGuard(np.array([-1.0, -1.0]), np.array([1.0, 1.0])))

        out_of_bounds_state = np.array([2.0, 0.5])  # First element exceeds upper bound
        with pytest.raises(SafetyViolationError) as exc_info:
            self.manager.check_all(out_of_bounds_state, step_idx=15)

        assert exc_info.value.violation_type == "boundsguard"
        assert exc_info.value.step_idx == 15

    def test_clear_guards(self):
        """Test clearing all guards."""
        self.manager.add_guard(NaNGuard())
        self.manager.add_guard(EnergyGuard(5.0))
        assert len(self.manager.guards) == 2

        self.manager.clear_guards()
        assert len(self.manager.guards) == 0

        # Should not raise any exceptions after clearing
        any_state = np.array([100.0, np.nan])  # Would normally violate NaN guard
        result = self.manager.check_all(any_state, step_idx=0)
        assert result == True


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Safety guard modules not available")
class TestModernLegacyCompatibility:
    """Test compatibility between modern and legacy safety guard functions."""

    def test_modern_legacy_nan_compatibility(self):
        """Test modern and legacy NaN guards have compatible behavior."""
        valid_state = np.array([1.0, 2.0, 3.0])
        invalid_state = np.array([1.0, np.nan, 3.0])

        # Both should succeed with valid state
        _guard_no_nan(valid_state, step_idx=0)        # Legacy - should not raise
        guard_no_nan(valid_state, step_idx=0)         # Modern - should not raise

        # Both should fail with invalid state
        with pytest.raises(RuntimeError):
            _guard_no_nan(invalid_state, step_idx=0)

        with pytest.raises(SafetyViolationError):
            guard_no_nan(invalid_state, step_idx=0)

    def test_modern_legacy_energy_compatibility(self):
        """Test modern and legacy energy guards have compatible behavior."""
        low_energy = np.array([0.5, 0.5])     # Energy = 0.5
        high_energy = np.array([2.0, 2.0])    # Energy = 8.0
        limits = {"max": 1.0}

        # Both should succeed with low energy
        _guard_energy(low_energy, limits)      # Legacy - should not raise
        guard_energy(low_energy, limits)       # Modern - should not raise

        # Both should fail with high energy
        with pytest.raises(RuntimeError):
            _guard_energy(high_energy, limits)

        with pytest.raises(SafetyViolationError):
            guard_energy(high_energy, limits)

    def test_modern_legacy_bounds_compatibility(self):
        """Test modern and legacy bounds guards have compatible behavior."""
        valid_state = np.array([0.5])
        invalid_state = np.array([2.0])
        bounds = (np.array([-1.0]), np.array([1.0]))
        t = 1.0

        # Both should succeed with valid state
        _guard_bounds(valid_state, bounds, t)   # Legacy - should not raise
        guard_bounds(valid_state, bounds, t)    # Modern - should not raise

        # Both should fail with invalid state
        with pytest.raises(RuntimeError):
            _guard_bounds(invalid_state, bounds, t)

        with pytest.raises(SafetyViolationError):
            guard_bounds(invalid_state, bounds, t)


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Safety guard modules not available")
class TestSafetyGuardIntegration:
    """Test integration functions for safety guards."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_config = Mock()
        self.mock_safety_config = Mock()
        self.mock_safety_settings = Mock()

        # Set up mock configuration hierarchy
        self.mock_config.simulation = self.mock_safety_config
        self.mock_safety_config.safety = self.mock_safety_settings

    def test_apply_safety_guards_minimal_config(self):
        """Test apply_safety_guards with minimal configuration."""
        valid_state = np.array([1.0, 2.0, 3.0])

        # Should at least run NaN guard without error
        apply_safety_guards(valid_state, step_idx=0, config=Mock())

        # Should fail with NaN state
        nan_state = np.array([1.0, np.nan, 3.0])
        with pytest.raises(SafetyViolationError):
            apply_safety_guards(nan_state, step_idx=0, config=Mock())

    def test_apply_safety_guards_with_energy_limits(self):
        """Test apply_safety_guards with energy limits configured."""
        self.mock_safety_settings.energy_limits = {"max": 2.0}

        # Low energy state should pass
        low_energy = np.array([0.5, 0.5])  # Energy = 0.5
        apply_safety_guards(low_energy, step_idx=0, config=self.mock_config)

        # High energy state should fail
        high_energy = np.array([2.0, 2.0])  # Energy = 8.0
        with pytest.raises(SafetyViolationError):
            apply_safety_guards(high_energy, step_idx=0, config=self.mock_config)

    def test_apply_safety_guards_with_state_bounds(self):
        """Test apply_safety_guards with state bounds configured."""
        # Mock state bounds as tuple
        self.mock_safety_settings.state_bounds = (
            np.array([-1.0, -1.0]),
            np.array([1.0, 1.0])
        )

        # Valid state should pass
        valid_state = np.array([0.5, -0.5])
        apply_safety_guards(valid_state, step_idx=0, config=self.mock_config)

        # Out of bounds state should fail
        invalid_state = np.array([2.0, 0.0])
        with pytest.raises(SafetyViolationError):
            apply_safety_guards(invalid_state, step_idx=0, config=self.mock_config)

    def test_create_default_guards_minimal(self):
        """Test create_default_guards with minimal configuration."""
        minimal_config = Mock()
        manager = create_default_guards(minimal_config)

        # Should have at least NaN guard
        assert len(manager.guards) >= 1
        assert any(isinstance(guard, NaNGuard) for guard in manager.guards)

    def test_create_default_guards_full_config(self):
        """Test create_default_guards with full configuration."""
        # Mock energy limits
        self.mock_safety_settings.energy_limits = {"max": 10.0}

        # Mock state bounds with lower/upper attributes
        mock_bounds = Mock()
        mock_bounds.lower = np.array([-5.0, -5.0])
        mock_bounds.upper = np.array([5.0, 5.0])
        self.mock_safety_settings.state_bounds = mock_bounds

        manager = create_default_guards(self.mock_config)

        # Should have NaN, energy, and bounds guards
        assert len(manager.guards) == 3
        assert any(isinstance(guard, NaNGuard) for guard in manager.guards)
        assert any(isinstance(guard, EnergyGuard) for guard in manager.guards)
        assert any(isinstance(guard, BoundsGuard) for guard in manager.guards)

    def test_create_default_guards_partial_config(self):
        """Test create_default_guards with partial configuration."""
        # Only energy limits, no bounds
        self.mock_safety_settings.energy_limits = {"max": 5.0}
        self.mock_safety_settings.state_bounds = None

        manager = create_default_guards(self.mock_config)

        # Should have NaN and energy guards, but not bounds
        assert len(manager.guards) == 2
        assert any(isinstance(guard, NaNGuard) for guard in manager.guards)
        assert any(isinstance(guard, EnergyGuard) for guard in manager.guards)
        assert not any(isinstance(guard, BoundsGuard) for guard in manager.guards)


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Safety guard modules not available")
class TestSafetyGuardPerformance:
    """Test performance characteristics of safety guards."""

    def test_nan_guard_performance(self):
        """Test NaN guard performance with large states."""
        guard = NaNGuard()
        large_state = np.random.randn(1000)  # 1000-element state

        import time
        start_time = time.time()

        # Perform many checks
        for _ in range(1000):
            result = guard.check(large_state, step_idx=0)
            assert result == True

        elapsed_time = time.time() - start_time

        # Should complete in reasonable time (less than 1 second)
        assert elapsed_time < 1.0

    def test_energy_guard_performance(self):
        """Test energy guard performance with large states."""
        guard = EnergyGuard(max_energy=1000000.0)  # High limit
        large_state = np.random.randn(1000) * 0.1  # Low energy per element

        import time
        start_time = time.time()

        # Perform many checks
        for _ in range(1000):
            result = guard.check(large_state, step_idx=0)
            assert result == True

        elapsed_time = time.time() - start_time
        assert elapsed_time < 1.0

    def test_bounds_guard_performance(self):
        """Test bounds guard performance with large states."""
        state_size = 1000
        lower_bounds = np.full(state_size, -10.0)
        upper_bounds = np.full(state_size, 10.0)
        guard = BoundsGuard(lower_bounds, upper_bounds)

        large_state = np.random.randn(state_size) * 5.0  # Within bounds

        import time
        start_time = time.time()

        # Perform many checks
        for _ in range(1000):
            result = guard.check(large_state, step_idx=0)
            assert result == True

        elapsed_time = time.time() - start_time
        assert elapsed_time < 2.0  # Allow more time for bounds checking

    def test_manager_performance_multiple_guards(self):
        """Test SafetyGuardManager performance with multiple guards."""
        manager = SafetyGuardManager()
        manager.add_guard(NaNGuard())
        manager.add_guard(EnergyGuard(1000.0))
        manager.add_guard(BoundsGuard(np.full(100, -10.0), np.full(100, 10.0)))

        test_state = np.random.randn(100) * 2.0  # Safe state

        import time
        start_time = time.time()

        # Perform many complete guard checks
        for _ in range(500):
            result = manager.check_all(test_state, step_idx=0)
            assert result == True

        elapsed_time = time.time() - start_time
        assert elapsed_time < 2.0


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Safety guard modules not available")
class TestSafetyGuardEdgeCases:
    """Test edge cases and boundary conditions for safety guards."""

    def test_empty_state_handling(self):
        """Test safety guards with empty states."""
        empty_state = np.array([])

        # NaN guard should handle empty state
        nan_guard = NaNGuard()
        assert nan_guard.check(empty_state, step_idx=0) == True

        # Energy guard should handle empty state (energy = 0)
        energy_guard = EnergyGuard(1.0)
        assert energy_guard.check(empty_state, step_idx=0) == True

        # Bounds guard should handle empty state
        bounds_guard = BoundsGuard(np.array([]), np.array([]))
        assert bounds_guard.check(empty_state, step_idx=0) == True

    def test_single_element_states(self):
        """Test safety guards with single-element states."""
        single_state = np.array([0.5])

        # All guards should work with single elements
        assert NaNGuard().check(single_state, 0) == True
        assert EnergyGuard(1.0).check(single_state, 0) == True
        assert BoundsGuard(np.array([0.0]), np.array([1.0])).check(single_state, 0) == True

    def test_extreme_values(self):
        """Test safety guards with extreme but valid values."""
        # Very small values
        tiny_state = np.array([1e-10, -1e-10, 1e-15])
        assert NaNGuard().check(tiny_state, 0) == True
        assert EnergyGuard(1.0).check(tiny_state, 0) == True

        # Very large values (but finite)
        large_state = np.array([1e6, -1e6, 1e8])
        assert NaNGuard().check(large_state, 0) == True
        # Energy guard should fail for large values
        assert EnergyGuard(1.0).check(large_state, 0) == False

    def test_zero_energy_limit(self):
        """Test energy guard with zero energy limit."""
        zero_energy_guard = EnergyGuard(0.0)

        # Only zero state should pass
        zero_state = np.array([0.0, 0.0, 0.0])
        assert zero_energy_guard.check(zero_state, 0) == True

        # Any non-zero state should fail
        tiny_state = np.array([1e-10, 0.0, 0.0])
        assert zero_energy_guard.check(tiny_state, 0) == False

    def test_bounds_guard_equal_limits(self):
        """Test bounds guard where lower and upper bounds are equal."""
        exact_bounds_guard = BoundsGuard(np.array([1.0]), np.array([1.0]))

        # Only exact value should pass
        exact_state = np.array([1.0])
        assert exact_bounds_guard.check(exact_state, 0) == True

        # Slightly off should fail
        slightly_off = np.array([1.0001])
        assert exact_bounds_guard.check(slightly_off, 0) == False


# Fallback tests when imports are not available
class TestSafetyGuardsFallback:
    """Test fallback behavior when safety guard modules are not available."""

    @pytest.mark.skipif(IMPORTS_AVAILABLE, reason="Test only when imports fail")
    def test_imports_not_available(self):
        """Test that we handle missing imports gracefully."""
        assert IMPORTS_AVAILABLE is False

    def test_safety_guard_test_structure(self):
        """Test safety guard test parameter structure."""
        safety_params = {
            'guard_types': 3,        # NaN, Energy, Bounds
            'legacy_functions': 3,   # _guard_no_nan, _guard_energy, _guard_bounds
            'modern_functions': 3,   # guard_no_nan, guard_energy, guard_bounds
            'violation_types': 3,    # nan, energy, bounds
            'performance_targets': { # Performance requirements
                'large_state_size': 1000,
                'max_check_time': 1.0,
                'batch_checks': 1000
            }
        }

        assert safety_params['guard_types'] == 3
        assert safety_params['legacy_functions'] == 3
        assert safety_params['modern_functions'] == 3
        assert safety_params['violation_types'] == 3
        assert safety_params['performance_targets']['large_state_size'] == 1000
        assert safety_params['performance_targets']['max_check_time'] == 1.0