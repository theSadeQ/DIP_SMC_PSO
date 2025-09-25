#==========================================================================================\\
#============== tests/test_interfaces/test_method_signatures.py =====================\\
#==========================================================================================\\
"""
Interface method signature validation tests.

CRITICAL HIGH-ROI TESTS: These tests prevent 'SimplifiedDIPDynamics' object has no attribute
'_rhs_core' errors and similar interface mismatches that cause 25-30% of current failures.
"""

import pytest
import numpy as np
import inspect
from typing import get_type_hints

from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
from src.plant.models.full.dynamics import FullDIPDynamics
from src.plant.models.lowrank.dynamics import LowRankDIPDynamics
from src.plant.models.base.dynamics_interface import BaseDynamicsModel, DynamicsModel
from src.plant import ConfigurationFactory


class TestDynamicsInterfaceConsistency:
    """Test that all dynamics classes have consistent method signatures."""

    def test_all_dynamics_implement_base_interface(self):
        """Validate all dynamics classes implement required interface methods."""

        # Get all dynamics classes
        dynamics_classes = [SimplifiedDIPDynamics, FullDIPDynamics, LowRankDIPDynamics]

        # Required interface methods from BaseDynamicsModel and DynamicsModel protocol
        required_methods = [
            'compute_dynamics',
            'get_physics_matrices',
            'validate_state',
            'get_state_dimension',
            'get_control_dimension'
        ]

        for dynamics_class in dynamics_classes:
            for method_name in required_methods:
                assert hasattr(dynamics_class, method_name), (
                    f"{dynamics_class.__name__} missing required method: {method_name}"
                )

                # Verify method is callable
                method = getattr(dynamics_class, method_name)
                assert callable(method), (
                    f"{dynamics_class.__name__}.{method_name} is not callable"
                )

    def test_compute_dynamics_signature_consistency(self):
        """Validate compute_dynamics method signatures are consistent across all dynamics classes."""

        # Get configs for each dynamics type
        simplified_config = ConfigurationFactory.create_default_config("simplified")
        full_config = ConfigurationFactory.create_default_config("full")
        lowrank_config = ConfigurationFactory.create_default_config("lowrank")

        # Create instances
        dynamics_instances = [
            SimplifiedDIPDynamics(simplified_config),
            FullDIPDynamics(full_config),
            LowRankDIPDynamics(lowrank_config)
        ]

        # Get reference signature from base class
        base_signature = inspect.signature(BaseDynamicsModel.compute_dynamics)

        for dynamics in dynamics_instances:
            method_signature = inspect.signature(dynamics.compute_dynamics)

            # Compare parameter names and types
            base_params = list(base_signature.parameters.keys())[1:]  # Skip 'self'
            method_params = list(method_signature.parameters.keys())[1:]  # Skip 'self'

            assert base_params == method_params, (
                f"{dynamics.__class__.__name__}.compute_dynamics has different parameter names: "
                f"expected {base_params}, got {method_params}"
            )

            # Test that method can be called with standard parameters
            state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
            control = np.array([1.0])
            time = 0.0

            # This should not raise AttributeError or signature mismatch
            try:
                result = dynamics.compute_dynamics(state, control, time)
                assert hasattr(result, 'success'), "Result missing 'success' attribute"
                assert hasattr(result, 'state_derivative'), "Result missing 'state_derivative' attribute"
            except AttributeError as e:
                pytest.fail(
                    f"{dynamics.__class__.__name__}.compute_dynamics failed with AttributeError: {e}"
                )

    def test_get_physics_matrices_signature_consistency(self):
        """Validate get_physics_matrices method signatures are consistent."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        dynamics_classes = [SimplifiedDIPDynamics, FullDIPDynamics, LowRankDIPDynamics]

        for dynamics_class, config in zip(dynamics_classes, configs):
            dynamics = dynamics_class(config)

            # Test that method exists and can be called
            state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])

            try:
                M, C, G = dynamics.get_physics_matrices(state)

                # Validate return format
                assert isinstance(M, np.ndarray), f"{dynamics_class.__name__}: M matrix not ndarray"
                assert isinstance(C, np.ndarray), f"{dynamics_class.__name__}: C matrix not ndarray"
                assert isinstance(G, np.ndarray), f"{dynamics_class.__name__}: G matrix not ndarray"

                # Validate matrix shapes are consistent
                assert M.shape[0] == M.shape[1], f"{dynamics_class.__name__}: M matrix not square"
                assert M.shape[0] == 3, f"{dynamics_class.__name__}: M matrix wrong dimension"

            except AttributeError as e:
                pytest.fail(
                    f"{dynamics_class.__name__}.get_physics_matrices failed with AttributeError: {e}"
                )

    def test_missing_rhs_core_method_prevention(self):
        """Test that prevents '_rhs_core' attribute errors by validating actual method names."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        dynamics_classes = [SimplifiedDIPDynamics, FullDIPDynamics, LowRankDIPDynamics]

        for dynamics_class, config in zip(dynamics_classes, configs):
            dynamics = dynamics_class(config)

            # Check what RHS-related methods actually exist
            methods = [method for method in dir(dynamics) if 'rhs' in method.lower()]

            # Document available methods for debugging
            print(f"\n{dynamics_class.__name__} RHS methods: {methods}")

            # Ensure that any code expecting '_rhs_core' knows what method to actually call
            if hasattr(dynamics, '_rhs_core'):
                # If _rhs_core exists, test it
                state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
                control = np.array([1.0])
                try:
                    result = dynamics._rhs_core(state, control)
                    assert isinstance(result, np.ndarray), "_rhs_core should return ndarray"
                except Exception as e:
                    pytest.fail(f"_rhs_core method failed: {e}")
            else:
                # If _rhs_core doesn't exist, compute_dynamics should work
                state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
                control = np.array([1.0])
                result = dynamics.compute_dynamics(state, control)
                assert result.success, "compute_dynamics should succeed when _rhs_core missing"


class TestControllerInterfaceConsistency:
    """Test that controller interfaces are consistent."""

    def test_controller_factory_compatibility(self):
        """Test that controller factory can create all controller types without signature errors."""
        from src.controllers.factory import create_controller

        # Standard controller configurations
        controller_types = ['classical_smc', 'adaptive_smc', 'sta_smc']

        for controller_type in controller_types:
            try:
                # This should not fail due to interface mismatches
                controller_config = ConfigurationFactory.create_default_config("controller")
                gains = [10.0, 5.0, 8.0, 3.0, 15.0, 2.0]  # Standard gain structure

                controller = create_controller(controller_type, controller_config, gains)
                assert controller is not None, f"Failed to create {controller_type} controller"

                # Test that controller has required interface methods
                required_methods = ['compute_control', 'reset']
                for method_name in required_methods:
                    assert hasattr(controller, method_name), (
                        f"{controller_type} missing required method: {method_name}"
                    )

            except (AttributeError, KeyError, TypeError) as e:
                pytest.fail(f"Controller {controller_type} interface error: {e}")


class TestIntegratorInterfaceRequirements:
    """Test that integrator requirements are met by dynamics classes."""

    def test_integrator_parameter_compatibility(self):
        """Test that integrators can work with all dynamics parameter formats."""
        from src.simulation.integrators import IntegratorFactory

        # Get dynamics instances
        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        dynamics_classes = [SimplifiedDIPDynamics, FullDIPDynamics, LowRankDIPDynamics]

        for dynamics_class, config in zip(dynamics_classes, configs):
            dynamics = dynamics_class(config)

            # Test with RK4 integrator
            integrator = IntegratorFactory.create_integrator("rk4", dt=0.01)

            state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
            control = np.array([1.0])
            dt = 0.01

            try:
                # This should not fail with "not enough values to unpack" error
                def dynamics_func(state, t):
                    result = dynamics.compute_dynamics(state, control, t)
                    if result.success:
                        return result.state_derivative
                    else:
                        raise ValueError(f"Dynamics computation failed: {result.info}")

                next_state = integrator.integrate_step(dynamics_func, state, 0.0, dt)

                assert isinstance(next_state, np.ndarray), "Integration should return ndarray"
                assert next_state.shape == state.shape, "State shape should be preserved"
                assert np.all(np.isfinite(next_state)), "Next state should be finite"

            except (ValueError, TypeError) as e:
                if "not enough values to unpack" in str(e):
                    pytest.fail(
                        f"Parameter unpacking error with {dynamics_class.__name__}: {e}"
                    )
                else:
                    pytest.fail(f"Integration failed with {dynamics_class.__name__}: {e}")


class TestAnalysisInterfaceCompatibility:
    """Test that analysis modules work with all dynamics classes."""

    def test_energy_analysis_interface_compatibility(self):
        """Test that energy analysis works with all dynamics implementations."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        dynamics_classes = [SimplifiedDIPDynamics, FullDIPDynamics, LowRankDIPDynamics]

        for dynamics_class, config in zip(dynamics_classes, configs):
            dynamics = dynamics_class(config)

            state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])

            # Test energy computation interface
            try:
                if hasattr(dynamics, 'compute_total_energy'):
                    total_energy = dynamics.compute_total_energy(state)
                    assert isinstance(total_energy, (int, float)), "Total energy should be numeric"
                    assert np.isfinite(total_energy), "Total energy should be finite"

                if hasattr(dynamics, 'compute_kinetic_energy'):
                    kinetic_energy = dynamics.compute_kinetic_energy(state)
                    assert isinstance(kinetic_energy, (int, float)), "Kinetic energy should be numeric"
                    assert kinetic_energy >= 0, "Kinetic energy should be non-negative"

                if hasattr(dynamics, 'compute_potential_energy'):
                    potential_energy = dynamics.compute_potential_energy(state)
                    assert isinstance(potential_energy, (int, float)), "Potential energy should be numeric"

            except AttributeError as e:
                pytest.fail(f"Energy analysis interface error with {dynamics_class.__name__}: {e}")

    def test_benchmark_interface_compatibility(self):
        """Test that benchmarks work with all dynamics implementations."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        dynamics_classes = [SimplifiedDIPDynamics, FullDIPDynamics, LowRankDIPDynamics]

        for dynamics_class, config in zip(dynamics_classes, configs):
            dynamics = dynamics_class(config)

            # Test that dynamics can be used in benchmark scenarios
            state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
            control = np.array([1.0])

            try:
                # Simulate typical benchmark operations
                result = dynamics.compute_dynamics(state, control)
                assert result.success, "Dynamics computation should succeed in benchmarks"

                # Test state validation for benchmarks
                is_valid = dynamics.validate_state(state)
                assert isinstance(is_valid, bool), "State validation should return boolean"

                # Test physics matrices for benchmarks
                M, C, G = dynamics.get_physics_matrices(state)
                assert all(isinstance(matrix, np.ndarray) for matrix in [M, C, G]), (
                    "Physics matrices should be numpy arrays"
                )

            except Exception as e:
                pytest.fail(f"Benchmark interface error with {dynamics_class.__name__}: {e}")