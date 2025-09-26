#==========================================================================================\\
#============= tests/test_interfaces/test_parameter_compatibility.py ================\\
#==========================================================================================\\
"""
Parameter compatibility validation tests.

HIGH-ROI TESTS: These tests prevent signature mismatch and parameter unpacking errors
that eliminate the "not enough values to unpack (expected 1, got 0)" category of failures.
"""

import pytest
import numpy as np
from typing import Tuple, Any, Dict

from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
from src.plant.models.full.dynamics import FullDIPDynamics
from src.plant.models.lowrank.dynamics import LowRankDIPDynamics
from src.plant import ConfigurationFactory


class TestDynamicsParameterConsistency:
    """Test that all dynamics classes accept consistent parameter formats."""

    def test_state_vector_format_consistency(self):
        """Test that all dynamics classes accept the same state vector format."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        dynamics_classes = [SimplifiedDIPDynamics, FullDIPDynamics, LowRankDIPDynamics]

        # Standard state vector format: [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
        test_states = [
            np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),           # Equilibrium
            np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0]),           # Position offset
            np.array([0.0, 0.0, 0.0, 1.0, 0.5, 0.8]),           # Velocity offset
            np.array([0.1, 0.1, 0.1, 0.1, 0.1, 0.1]),           # Small perturbation
        ]

        for dynamics_class, config in zip(dynamics_classes, configs):
            dynamics = dynamics_class(config)

            for state in test_states:
                try:
                    # Test state validation
                    is_valid = dynamics.validate_state(state)
                    assert isinstance(is_valid, bool), (
                        f"{dynamics_class.__name__}: validate_state should return bool"
                    )

                    # Test state dimension consistency
                    expected_dim = dynamics.get_state_dimension()
                    assert len(state) == expected_dim, (
                        f"{dynamics_class.__name__}: state dimension mismatch. "
                        f"Expected {expected_dim}, got {len(state)}"
                    )

                    # Test that compute_dynamics accepts this state format
                    control = np.array([1.0])
                    result = dynamics.compute_dynamics(state, control)

                    # Result should have consistent format
                    assert hasattr(result, 'state_derivative'), "Missing state_derivative"
                    assert hasattr(result, 'success'), "Missing success flag"

                    if result.success:
                        assert isinstance(result.state_derivative, np.ndarray), (
                            "state_derivative should be ndarray"
                        )
                        assert result.state_derivative.shape == state.shape, (
                            f"State derivative shape mismatch: {result.state_derivative.shape} vs {state.shape}"
                        )

                except Exception as e:
                    pytest.fail(
                        f"{dynamics_class.__name__} failed with state {state}: {e}"
                    )

    def test_control_input_format_consistency(self):
        """Test that all dynamics classes accept the same control input format."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        dynamics_classes = [SimplifiedDIPDynamics, FullDIPDynamics, LowRankDIPDynamics]

        # Test different control input formats
        test_controls = [
            np.array([0.0]),          # Zero control
            np.array([10.0]),         # Positive control
            np.array([-10.0]),        # Negative control
            np.array([100.0]),        # Large control
        ]

        state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])

        for dynamics_class, config in zip(dynamics_classes, configs):
            dynamics = dynamics_class(config)

            for control in test_controls:
                try:
                    # Test control dimension consistency
                    expected_dim = dynamics.get_control_dimension()
                    assert len(control) == expected_dim, (
                        f"{dynamics_class.__name__}: control dimension mismatch. "
                        f"Expected {expected_dim}, got {len(control)}"
                    )

                    # Test that compute_dynamics accepts this control format
                    result = dynamics.compute_dynamics(state, control)

                    # Should not fail due to control format issues
                    assert hasattr(result, 'success'), "Missing success flag"

                    if not result.success and 'control' in str(result.info):
                        pytest.fail(
                            f"{dynamics_class.__name__} rejected valid control {control}: {result.info}"
                        )

                except Exception as e:
                    pytest.fail(
                        f"{dynamics_class.__name__} failed with control {control}: {e}"
                    )

    def test_time_parameter_consistency(self):
        """Test that all dynamics classes handle time parameter consistently."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        dynamics_classes = [SimplifiedDIPDynamics, FullDIPDynamics, LowRankDIPDynamics]

        state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
        control = np.array([1.0])

        # Test different time values
        test_times = [0.0, 0.1, 1.0, 10.0, 100.0]

        for dynamics_class, config in zip(dynamics_classes, configs):
            dynamics = dynamics_class(config)

            for time in test_times:
                try:
                    # Test with explicit time parameter
                    result = dynamics.compute_dynamics(state, control, time)
                    assert hasattr(result, 'success'), "Missing success flag"

                    # Test with default time (should work the same)
                    result_default = dynamics.compute_dynamics(state, control)
                    assert hasattr(result_default, 'success'), "Missing success flag"

                    # For time-invariant systems, results should be similar
                    if result.success and result_default.success:
                        if hasattr(dynamics, 'is_time_invariant') and dynamics.is_time_invariant:
                            np.testing.assert_allclose(
                                result.state_derivative,
                                result_default.state_derivative,
                                rtol=1e-10,
                                err_msg=f"Time-invariant system gave different results for time={time}"
                            )

                except Exception as e:
                    pytest.fail(
                        f"{dynamics_class.__name__} failed with time {time}: {e}"
                    )


class TestControllerParameterConsistency:
    """Test that all controllers accept consistent configuration formats."""

    def test_controller_gains_parameter_consistency(self):
        """Test that controllers accept consistent gain parameter formats."""
        from src.controllers.factory import create_controller

        # Controller types with appropriate gain counts
        controller_configs = {
            'classical_smc': [10.0, 5.0, 8.0, 3.0, 15.0, 2.0],  # 6 gains
            'adaptive_smc': [10.0, 8.0, 5.0, 4.0, 1.0],         # 5 gains
            'sta_smc': [5.0, 3.0, 4.0, 4.0, 0.4, 0.4]           # 6 gains
        }

        # Create a simple config object for controllers (they don't use plant configuration)
        class SimpleConfig:
            def __init__(self):
                self.max_force = 150.0
                self.dt = 0.001

            def to_dict(self):
                return {'max_force': self.max_force, 'dt': self.dt}

        controller_config = SimpleConfig()

        for controller_type, base_gains in controller_configs.items():
            # Test both list and array formats
            test_gains = [
                base_gains,                    # List format
                np.array(base_gains),          # Numpy array format
            ]

            for gains in test_gains:
                try:
                    controller = create_controller(controller_type, controller_config, gains)
                    assert controller is not None, f"Failed to create {controller_type} with gains {type(gains)}"

                    # Test that controller can use these gains
                    state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
                    control = np.array([0.0])
                    history = []

                    control_output = controller.compute_control(state, control, history)

                    # Should have consistent output format
                    if isinstance(control_output, dict):
                        # Dictionary interface - check for 'u' key (control signal)
                        assert 'u' in control_output, "Missing 'u' key in control output"
                        control_signal = control_output['u']
                    else:
                        # Object interface - check for control_signal attribute
                        assert hasattr(control_output, 'control_signal'), "Missing control_signal"
                        control_signal = control_output.control_signal

                    # Control signal should be a scalar or array
                    if isinstance(control_signal, np.ndarray):
                        assert control_signal.shape in [(1,), ()], "control_signal should be scalar or 1D array"
                    else:
                        assert isinstance(control_signal, (int, float, np.number)), (
                            "control_signal should be numeric"
                        )

                except Exception as e:
                    pytest.fail(
                        f"Controller {controller_type} failed with gains {gains}: {e}"
                    )

    def test_controller_config_parameter_consistency(self):
        """Test that controllers accept consistent configuration parameter formats."""
        from src.controllers.factory import create_controller

        # Test different configuration formats
        class SimpleConfig:
            def __init__(self):
                self.max_force = 150.0
                self.dt = 0.001

            def to_dict(self):
                return {'max_force': self.max_force, 'dt': self.dt}

        controller_config = SimpleConfig()

        # Controller types with appropriate gain counts
        controller_configs = {
            'classical_smc': [10.0, 5.0, 8.0, 3.0, 15.0, 2.0],  # 6 gains
            'adaptive_smc': [10.0, 8.0, 5.0, 4.0, 1.0],         # 5 gains
            'sta_smc': [5.0, 3.0, 4.0, 4.0, 0.4, 0.4]           # 6 gains
        }

        for controller_type, gains in controller_configs.items():
            try:
                # Test with AttributeDictionary config (from ConfigurationFactory)
                controller1 = create_controller(controller_type, controller_config, gains)

                # Test with plain dict config (conversion should work)
                dict_config = controller_config.to_dict() if hasattr(controller_config, 'to_dict') else dict(controller_config)
                controller2 = create_controller(controller_type, dict_config, gains)

                # Both should work without signature errors
                assert controller1 is not None, f"Failed with AttributeDictionary config"
                assert controller2 is not None, f"Failed with dict config"

                # Both should have same interface
                for controller in [controller1, controller2]:
                    assert hasattr(controller, 'compute_control'), "Missing compute_control method"
                    # Not all controllers implement reset - that's ok for interface compatibility

            except Exception as e:
                pytest.fail(
                    f"Controller {controller_type} config compatibility error: {e}"
                )


class TestIntegratorParameterCompatibility:
    """Test that integrators work with all dynamics parameter formats."""

    def test_integration_parameter_unpacking_compatibility(self):
        """Test that prevents 'not enough values to unpack' errors in integration."""
        from src.simulation.integrators import IntegratorFactory

        # Get dynamics instances
        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        dynamics_classes = [SimplifiedDIPDynamics, FullDIPDynamics, LowRankDIPDynamics]

        integrator_types = ['euler', 'rk4']

        for dynamics_class, config in zip(dynamics_classes, configs):
            dynamics = dynamics_class(config)

            for integrator_type in integrator_types:
                try:
                    integrator = IntegratorFactory.create_integrator(integrator_type, dt=0.01)

                    state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
                    control = np.array([1.0])
                    dt = 0.01

                    # Create dynamics function with proper signature
                    def dynamics_func(state, t):
                        result = dynamics.compute_dynamics(state, control, t)
                        if result.success:
                            return result.state_derivative
                        else:
                            raise ValueError(f"Dynamics failed: {result.info}")

                    # Test integration step - this is where unpacking errors typically occur
                    next_state = integrator.integrate_step(dynamics_func, state, 0.0, dt)

                    # Validate result format
                    assert isinstance(next_state, np.ndarray), "Integration should return ndarray"
                    assert next_state.shape == state.shape, (
                        f"State shape mismatch: {next_state.shape} vs {state.shape}"
                    )
                    assert np.all(np.isfinite(next_state)), "Next state should be finite"

                except ValueError as e:
                    if "not enough values to unpack" in str(e):
                        pytest.fail(
                            f"Parameter unpacking error: {dynamics_class.__name__} + {integrator_type}: {e}"
                        )
                    else:
                        # Other ValueError types are acceptable (e.g., numerical issues)
                        pass
                except Exception as e:
                    pytest.fail(
                        f"Integration error: {dynamics_class.__name__} + {integrator_type}: {e}"
                    )

    def test_multi_step_integration_parameter_consistency(self):
        """Test parameter consistency over multiple integration steps."""
        from src.simulation.integrators import IntegratorFactory

        config = ConfigurationFactory.create_default_config("simplified")
        dynamics = SimplifiedDIPDynamics(config)
        integrator = IntegratorFactory.create_integrator("rk4", dt=0.01)

        state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
        control = np.array([1.0])
        dt = 0.01
        n_steps = 10

        def dynamics_func(state, t):
            result = dynamics.compute_dynamics(state, control, t)
            if result.success:
                return result.state_derivative
            else:
                raise ValueError(f"Dynamics failed: {result.info}")

        current_state = state.copy()
        current_time = 0.0

        try:
            for step in range(n_steps):
                # Each step should maintain parameter format consistency
                next_state = integrator.integrate_step(dynamics_func, current_state, current_time, dt)

                assert isinstance(next_state, np.ndarray), f"Step {step}: not ndarray"
                assert next_state.shape == current_state.shape, f"Step {step}: shape mismatch"
                assert np.all(np.isfinite(next_state)), f"Step {step}: not finite"

                current_state = next_state
                current_time += dt

        except Exception as e:
            pytest.fail(f"Multi-step integration failed at step {step}: {e}")


class TestConfigurationParameterConsistency:
    """Test that configuration parameters are consistently accessible."""

    def test_config_attribute_vs_dict_access_consistency(self):
        """Test that config parameters can be accessed both ways consistently."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank"),
            ConfigurationFactory.create_default_config("controller")
        ]

        for config in configs:
            try:
                # Get available attributes/keys
                if hasattr(config, 'keys'):
                    available_keys = list(config.keys())
                elif hasattr(config, '_data') and hasattr(config._data, 'keys'):
                    available_keys = list(config._data.keys())
                else:
                    available_keys = [attr for attr in dir(config) if not attr.startswith('_')]

                # Test that each key can be accessed both ways
                for key in available_keys[:5]:  # Test first 5 to avoid excessive testing
                    if hasattr(config, key):
                        # Test attribute access
                        attr_value = getattr(config, key)

                        # Test dictionary access if available
                        if hasattr(config, '__getitem__'):
                            dict_value = config[key]
                            assert attr_value == dict_value, (
                                f"Inconsistent access for {key}: attr={attr_value}, dict={dict_value}"
                            )

            except Exception as e:
                pytest.fail(f"Configuration access consistency error: {e}")

    def test_missing_parameter_handling_consistency(self):
        """Test that missing parameters are handled consistently across configurations."""

        configs = [
            ConfigurationFactory.create_default_config("simplified"),
            ConfigurationFactory.create_default_config("full"),
            ConfigurationFactory.create_default_config("lowrank")
        ]

        # Test accessing a parameter that likely doesn't exist
        missing_parameter = "non_existent_parameter_xyz"

        for config in configs:
            try:
                # Test attribute access to missing parameter
                try:
                    value = getattr(config, missing_parameter)
                    # If it succeeds, it should return None or a reasonable default
                    assert value is None or isinstance(value, (int, float, str, bool)), (
                        f"Missing parameter returned unexpected type: {type(value)}"
                    )
                except AttributeError:
                    # This is expected behavior - missing attribute should raise AttributeError
                    pass

                # Test dictionary access if available
                if hasattr(config, 'get'):
                    default_value = config.get(missing_parameter, 'DEFAULT')
                    assert default_value == 'DEFAULT', "get() method should return default"

            except Exception as e:
                pytest.fail(f"Missing parameter handling error in {type(config).__name__}: {e}")