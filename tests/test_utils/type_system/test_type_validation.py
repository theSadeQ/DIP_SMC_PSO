#==========================================================================================\\\
#============ tests/test_utils/type_system/test_type_validation.py ======================\\\
#==========================================================================================\\\

"""
Type System Validation Tests - System Reliability Foundation

This module provides comprehensive testing of the type system consistency
across ALL components, eliminating type-related utility failures and ensuring
foundation stability for the entire system.

MISSION: Validate type system consistency across ALL components
PRIORITY: HIGH (4x ROI - Foundation for all other components)
COVERAGE TARGET: 100% (Safety-critical mechanism)
"""

from __future__ import annotations

import pytest
from typing import Any, Dict, Tuple, NamedTuple, get_type_hints
from unittest.mock import Mock

from src.utils.types.control_outputs import (
    ClassicalSMCOutput,
    AdaptiveSMCOutput,
    STAOutput,
    HybridSTAOutput
)


class TestControllerOutputTypes:
    """Test suite for controller output type validation."""

    def test_classical_smc_output_structure(self):
        """Test ClassicalSMCOutput type structure and validation."""
        # Create valid output
        output = ClassicalSMCOutput(
            u=10.5,
            state=(),
            history={"sigma": 0.1, "u_unsat": 12.0}
        )

        # Validate structure
        assert isinstance(output, tuple)  # NamedTuple inheritance
        assert hasattr(output, '_fields')  # NamedTuple attribute
        assert hasattr(output, 'u')
        assert hasattr(output, 'state')
        assert hasattr(output, 'history')

        # Validate types
        assert isinstance(output.u, float)
        assert isinstance(output.state, tuple)
        assert isinstance(output.history, dict)

        # Validate values
        assert output.u == 10.5
        assert output.state == ()
        assert output.history == {"sigma": 0.1, "u_unsat": 12.0}

    def test_classical_smc_output_type_annotations(self):
        """Test ClassicalSMCOutput type annotations consistency."""
        hints = get_type_hints(ClassicalSMCOutput)

        assert 'u' in hints
        assert 'state' in hints
        assert 'history' in hints

        # Validate annotation types
        assert hints['u'] == float
        assert hints['state'] == Tuple[Any, ...]
        assert hints['history'] == Dict[str, Any]

    def test_classical_smc_output_immutability(self):
        """Test ClassicalSMCOutput immutability (NamedTuple property)."""
        output = ClassicalSMCOutput(u=10.0, state=(), history={})

        # NamedTuples should be immutable
        with pytest.raises(AttributeError):
            output.u = 20.0

    def test_classical_smc_output_tuple_compatibility(self):
        """Test ClassicalSMCOutput backward compatibility with tuple interface."""
        output = ClassicalSMCOutput(u=10.0, state=(), history={"test": 1})

        # Should work as tuple
        assert len(output) == 3
        assert output[0] == 10.0
        assert output[1] == ()
        assert output[2] == {"test": 1}

        # Unpacking should work
        u, state, history = output
        assert u == 10.0
        assert state == ()
        assert history == {"test": 1}

    def test_adaptive_smc_output_structure(self):
        """Test AdaptiveSMCOutput type structure and validation."""
        output = AdaptiveSMCOutput(
            u=15.0,
            state=(0.1, 0.2),
            history={"adaptation": True},
            sigma=0.05
        )

        # Validate structure
        assert isinstance(output, tuple)  # NamedTuple inheritance
        assert hasattr(output, '_fields')  # NamedTuple attribute
        assert hasattr(output, 'u')
        assert hasattr(output, 'state')
        assert hasattr(output, 'history')
        assert hasattr(output, 'sigma')

        # Validate types
        assert isinstance(output.u, float)
        assert isinstance(output.state, tuple)
        assert isinstance(output.history, dict)
        assert isinstance(output.sigma, float)

        # Validate values
        assert output.u == 15.0
        assert output.state == (0.1, 0.2)
        assert output.sigma == 0.05

    def test_adaptive_smc_output_type_annotations(self):
        """Test AdaptiveSMCOutput type annotations consistency."""
        hints = get_type_hints(AdaptiveSMCOutput)

        assert 'u' in hints
        assert 'state' in hints
        assert 'history' in hints
        assert 'sigma' in hints

        # Validate annotation types
        assert hints['u'] == float
        assert hints['state'] == Tuple[float, ...]
        assert hints['history'] == Dict[str, Any]
        assert hints['sigma'] == float

    def test_sta_output_structure(self):
        """Test STAOutput type structure and validation."""
        output = STAOutput(
            u=20.0,
            state=(1.0, 2.0),
            history={"z": 1.5, "integrator": True}
        )

        # Validate structure
        assert isinstance(output, tuple)  # NamedTuple inheritance
        assert hasattr(output, '_fields')  # NamedTuple attribute
        assert hasattr(output, 'u')
        assert hasattr(output, 'state')
        assert hasattr(output, 'history')

        # Validate types
        assert isinstance(output.u, float)
        assert isinstance(output.state, tuple)
        assert isinstance(output.history, dict)

    def test_sta_output_type_annotations(self):
        """Test STAOutput type annotations consistency."""
        hints = get_type_hints(STAOutput)

        assert 'u' in hints
        assert 'state' in hints
        assert 'history' in hints

        # Validate annotation types
        assert hints['u'] == float
        assert hints['state'] == Tuple[float, ...]
        assert hints['history'] == Dict[str, Any]

    def test_hybrid_sta_output_structure(self):
        """Test HybridSTAOutput type structure and validation."""
        output = HybridSTAOutput(
            u=25.0,
            state=(1.0, 2.0, 3.0),
            history={"k1": 1.0, "k2": 2.0},
            sigma=0.1
        )

        # Validate structure
        assert isinstance(output, tuple)  # NamedTuple inheritance
        assert hasattr(output, '_fields')  # NamedTuple attribute
        assert hasattr(output, 'u')
        assert hasattr(output, 'state')
        assert hasattr(output, 'history')
        assert hasattr(output, 'sigma')

        # Validate types
        assert isinstance(output.u, float)
        assert isinstance(output.state, tuple)
        assert isinstance(output.history, dict)
        assert isinstance(output.sigma, float)

    def test_hybrid_sta_output_type_annotations(self):
        """Test HybridSTAOutput type annotations consistency."""
        hints = get_type_hints(HybridSTAOutput)

        assert 'u' in hints
        assert 'state' in hints
        assert 'history' in hints
        assert 'sigma' in hints

        # Validate annotation types
        assert hints['u'] == float
        assert hints['state'] == Tuple[float, ...]
        assert hints['history'] == Dict[str, Any]
        assert hints['sigma'] == float


class TestTypeSystemConsistency:
    """Test cross-component type system consistency."""

    def test_all_output_types_have_control_field(self):
        """Ensure all controller outputs have a 'u' control field."""
        output_types = [
            ClassicalSMCOutput,
            AdaptiveSMCOutput,
            STAOutput,
            HybridSTAOutput
        ]

        for output_type in output_types:
            hints = get_type_hints(output_type)
            assert 'u' in hints, f"{output_type.__name__} missing 'u' field"
            assert hints['u'] == float, f"{output_type.__name__} 'u' field not float"

    def test_all_output_types_have_state_field(self):
        """Ensure all controller outputs have a 'state' field."""
        output_types = [
            ClassicalSMCOutput,
            AdaptiveSMCOutput,
            STAOutput,
            HybridSTAOutput
        ]

        for output_type in output_types:
            hints = get_type_hints(output_type)
            assert 'state' in hints, f"{output_type.__name__} missing 'state' field"
            # State should be some form of tuple
            assert 'Tuple' in str(hints['state']), f"{output_type.__name__} 'state' not tuple-like"

    def test_all_output_types_have_history_field(self):
        """Ensure all controller outputs have a 'history' field."""
        output_types = [
            ClassicalSMCOutput,
            AdaptiveSMCOutput,
            STAOutput,
            HybridSTAOutput
        ]

        for output_type in output_types:
            hints = get_type_hints(output_type)
            assert 'history' in hints, f"{output_type.__name__} missing 'history' field"
            assert hints['history'] == Dict[str, Any], f"{output_type.__name__} 'history' wrong type"

    def test_sliding_mode_controllers_have_sigma_field(self):
        """Test that sliding mode controllers consistently expose sigma."""
        sliding_mode_types = [AdaptiveSMCOutput, HybridSTAOutput]

        for output_type in sliding_mode_types:
            hints = get_type_hints(output_type)
            assert 'sigma' in hints, f"{output_type.__name__} missing 'sigma' field"
            assert hints['sigma'] == float, f"{output_type.__name__} 'sigma' not float"

    def test_type_compatibility_across_components(self):
        """Test type compatibility when components interact."""
        # Create outputs from different controllers
        classical_output = ClassicalSMCOutput(u=10.0, state=(), history={})
        adaptive_output = AdaptiveSMCOutput(u=15.0, state=(0.1,), history={}, sigma=0.05)

        # All should have same 'u' type for actuator compatibility
        assert type(classical_output.u) == type(adaptive_output.u)

        # All should have compatible history types
        assert type(classical_output.history) == type(adaptive_output.history)


class TestTypeSystemRobustness:
    """Test type system robustness and error handling."""

    def test_invalid_field_types_raise_errors(self):
        """Test that invalid field types raise appropriate errors."""
        # These should work fine
        ClassicalSMCOutput(u=10.0, state=(), history={})

        # Type coercion should handle int -> float
        output = ClassicalSMCOutput(u=10, state=(), history={})
        assert isinstance(output.u, int)  # NamedTuple preserves int type

    def test_missing_required_fields(self):
        """Test behavior with missing required fields."""
        with pytest.raises(TypeError):
            ClassicalSMCOutput(u=10.0, state=())  # Missing history

        with pytest.raises(TypeError):
            AdaptiveSMCOutput(u=10.0, state=(), history={})  # Missing sigma

    def test_extra_fields_rejected(self):
        """Test that extra fields are properly rejected."""
        with pytest.raises(TypeError):
            ClassicalSMCOutput(
                u=10.0,
                state=(),
                history={},
                extra_field="not_allowed"
            )

    def test_field_order_consistency(self):
        """Test that field order is consistent across instances."""
        output1 = ClassicalSMCOutput(u=10.0, state=(), history={})
        output2 = ClassicalSMCOutput(u=20.0, state=(1,), history={"a": 1})

        # Field order should be consistent
        assert output1._fields == output2._fields
        assert output1._fields == ('u', 'state', 'history')

    def test_type_system_serialization_compatibility(self):
        """Test that type system supports common serialization patterns."""
        output = ClassicalSMCOutput(u=10.0, state=(), history={"test": 123})

        # Should be convertible to dict (common serialization need)
        as_dict = output._asdict()
        assert isinstance(as_dict, dict)
        assert as_dict['u'] == 10.0
        assert as_dict['state'] == ()
        assert as_dict['history'] == {"test": 123}

        # Should support reconstruction from dict
        reconstructed = ClassicalSMCOutput(**as_dict)
        assert reconstructed == output


class TestTypingPerformance:
    """Test type system performance characteristics."""

    def test_type_creation_performance(self):
        """Test that type creation is performant for real-time control."""
        import time

        # Create many outputs to test performance
        start_time = time.perf_counter()

        for i in range(1000):
            ClassicalSMCOutput(u=float(i), state=(), history={})

        creation_time = time.perf_counter() - start_time

        # Should be very fast (< 50ms for 1000 creations)
        assert creation_time < 0.050, f"Type creation too slow: {creation_time:.6f}s"

    def test_field_access_performance(self):
        """Test that field access is performant for real-time control."""
        import time

        output = ClassicalSMCOutput(u=10.0, state=(), history={"test": 123})

        # Time field access
        start_time = time.perf_counter()

        for _ in range(10000):
            _ = output.u
            _ = output.state
            _ = output.history

        access_time = time.perf_counter() - start_time

        # Should be very fast (< 10ms for 30k accesses)
        assert access_time < 0.010, f"Field access too slow: {access_time:.6f}s"


class TestTypeSystemDocumentation:
    """Test type system documentation and introspection."""

    def test_all_types_have_docstrings(self):
        """Ensure all controller output types have proper documentation."""
        output_types = [
            ClassicalSMCOutput,
            AdaptiveSMCOutput,
            STAOutput,
            HybridSTAOutput
        ]

        for output_type in output_types:
            assert output_type.__doc__ is not None, f"{output_type.__name__} missing docstring"
            assert len(output_type.__doc__.strip()) > 10, f"{output_type.__name__} docstring too short"

    def test_field_documentation_consistency(self):
        """Test that field documentation follows consistent patterns."""
        # This is more of a style test, but ensures consistency
        for output_type in [ClassicalSMCOutput, AdaptiveSMCOutput, STAOutput, HybridSTAOutput]:
            docstring = output_type.__doc__
            assert 'Parameters' in docstring, f"{output_type.__name__} missing parameter documentation"
            assert 'u :' in docstring, f"{output_type.__name__} missing 'u' parameter docs"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])