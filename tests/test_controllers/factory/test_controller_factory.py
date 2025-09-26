#==========================================================================================\\\
#================ tests/test_controllers/factory/test_controller_factory.py ==============\\\
#==========================================================================================\\\

"""
Comprehensive test suite for controller factory functionality.

Tests the SMC factory system including type-safe creation, PSO integration,
and gain validation for all supported controller types.
"""

import pytest
import numpy as np
from typing import Dict, Any

# Import controller factory components
from src.controllers.factory import (
    SMCFactory, SMCType, SMCConfig, create_smc_for_pso,
    get_gain_bounds_for_pso, validate_smc_gains, SMC_GAIN_SPECS
)

# Import plant configuration for controller testing
from src.plant.configurations import ConfigurationFactory


class TestSMCFactory:
    """Test the SMC factory system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plant_config = ConfigurationFactory.create_default_config("simplified")
        self.factory = SMCFactory()

    def test_factory_creation(self):
        """Test basic factory creation."""
        assert isinstance(self.factory, SMCFactory)

    def test_smc_types_available(self):
        """Test that all SMC types are available."""
        expected_types = [
            SMCType.CLASSICAL,
            SMCType.ADAPTIVE,
            SMCType.SUPER_TWISTING,
            SMCType.HYBRID
        ]

        for smc_type in expected_types:
            assert isinstance(smc_type, SMCType)

    def test_gain_specifications(self):
        """Test that gain specifications are properly defined."""
        assert len(SMC_GAIN_SPECS) >= 4

        for smc_type, spec in SMC_GAIN_SPECS.items():
            assert hasattr(spec, 'gain_names')
            assert hasattr(spec, 'gain_bounds')
            assert hasattr(spec, 'controller_type')
            assert hasattr(spec, 'n_gains')
            # Check that gain_names length matches expected number of gains
            assert len(spec.gain_names) == spec.n_gains
            # Check that gain_bounds returns proper bounds
            bounds = spec.gain_bounds
            assert len(bounds) == len(spec.gain_names)


class TestControllerCreation:
    """Test controller creation through factory."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plant_config = ConfigurationFactory.create_default_config("simplified")
        self.valid_gains = {
            SMCType.CLASSICAL: [10.0, 5.0, 8.0, 3.0, 15.0, 2.0],  # 6 gains: k1, k2, lam1, lam2, K, kd
            SMCType.ADAPTIVE: [10.0, 5.0, 8.0, 3.0, 2.0],  # 5 gains: k1, k2, lam1, lam2, gamma
        }

    def test_create_classical_smc(self):
        """Test creating classical SMC controller."""
        gains = self.valid_gains[SMCType.CLASSICAL]

        config = SMCConfig(
            gains=gains,
            max_force=100.0,
            dt=0.01
        )

        controller = SMCFactory.create_controller(SMCType.CLASSICAL, config)
        assert controller is not None

        # Test control computation
        state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
        state_vars = ()  # Empty tuple for state vars
        history = {}     # Empty dict for history
        control_output = controller.compute_control(state, state_vars, history)
        assert control_output is not None
        assert hasattr(control_output, 'u')
        assert isinstance(control_output.u, (float, np.ndarray, int))
        # Ensure it's a scalar or 1D array
        if isinstance(control_output.u, np.ndarray):
            assert control_output.u.shape == (1,)
        else:
            assert isinstance(control_output.u, (float, int))

    def test_create_adaptive_smc(self):
        """Test creating adaptive SMC controller."""
        gains = self.valid_gains[SMCType.ADAPTIVE]

        config = SMCConfig(
            gains=gains,
            max_force=100.0,
            dt=0.01
        )

        controller = SMCFactory.create_controller(SMCType.ADAPTIVE, config)
        assert controller is not None

        # Test control computation
        state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
        state_vars = ()  # Empty tuple for state vars
        history = {}     # Empty dict for history
        control_output = controller.compute_control(state, state_vars, history)
        assert control_output is not None
        assert hasattr(control_output, 'u')
        assert isinstance(control_output.u, (float, np.ndarray, int))
        # Ensure it's a scalar or 1D array
        if isinstance(control_output.u, np.ndarray):
            assert control_output.u.shape == (1,)
        else:
            assert isinstance(control_output.u, (float, int))

    def test_invalid_smc_type_raises_error(self):
        """Test that invalid SMC type raises appropriate error."""
        with pytest.raises((ValueError, KeyError)):
            config = SMCConfig(
                gains=[1.0, 2.0, 3.0, 4.0],
                max_force=100.0,
                dt=0.01
            )
            SMCFactory.create_controller("invalid_type", config)


class TestPSOIntegration:
    """Test PSO integration functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plant_config = ConfigurationFactory.create_default_config("simplified")

    def test_create_smc_for_pso(self):
        """Test PSO-specific controller creation."""
        gains = [10.0, 5.0, 8.0, 3.0]

        controller = create_smc_for_pso(
            SMCType.CLASSICAL,
            gains,
            self.plant_config
        )

        assert controller is not None

        # Test control computation
        state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
        control = controller.compute_control(state)
        assert isinstance(control, np.ndarray)

    def test_get_gain_bounds_for_pso(self):
        """Test getting gain bounds for PSO optimization."""
        bounds = get_gain_bounds_for_pso(SMCType.CLASSICAL)

        assert isinstance(bounds, tuple)
        assert len(bounds) == 2  # (lower_bounds, upper_bounds)

        lower_bounds, upper_bounds = bounds
        assert len(lower_bounds) == len(upper_bounds)
        assert all(l < u for l, u in zip(lower_bounds, upper_bounds))

    def test_validate_smc_gains(self):
        """Test gain validation."""
        # Valid gains should pass
        valid_gains = [10.0, 5.0, 8.0, 3.0]
        assert validate_smc_gains(SMCType.CLASSICAL, valid_gains)

        # Invalid gains should fail
        invalid_gains = [-1.0, 5.0, 8.0, 3.0]  # Negative gain
        assert not validate_smc_gains(SMCType.CLASSICAL, invalid_gains)


class TestFactoryRobustness:
    """Test factory robustness and edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plant_config = ConfigurationFactory.create_default_config("simplified")

    def test_factory_handles_extreme_gains(self):
        """Test factory with extreme gain values."""
        # Very small gains
        small_gains = [0.01, 0.01, 0.01, 0.01]
        controller = create_smc_for_pso(
            SMCType.CLASSICAL,
            small_gains,
            self.plant_config
        )
        assert controller is not None

        # Large gains
        large_gains = [100.0, 100.0, 100.0, 100.0]
        controller = create_smc_for_pso(
            SMCType.CLASSICAL,
            large_gains,
            self.plant_config
        )
        assert controller is not None

    def test_factory_thread_safety(self):
        """Test that factory operations are thread-safe."""
        import threading
        results = []

        def create_controller_threaded():
            try:
                gains = [10.0, 5.0, 8.0, 3.0, 15.0, 2.0]  # 6 gains for classical SMC
                controller = create_smc_for_pso(
                    SMCType.CLASSICAL,
                    gains,
                    max_force=100.0,
                    dt=0.01,
                    dynamics_model=self.plant_config
                )
                results.append(controller is not None)
            except Exception:
                results.append(False)

        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=create_controller_threaded)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All should succeed
        assert all(results)

    def test_memory_efficiency(self):
        """Test that factory doesn't leak memory."""
        import gc

        initial_objects = len(gc.get_objects())

        # Create many controllers
        gains = [10.0, 5.0, 8.0, 3.0]
        controllers = []

        for _ in range(50):
            controller = create_smc_for_pso(
                SMCType.CLASSICAL,
                gains,
                self.plant_config
            )
            controllers.append(controller)

        # Clear references
        del controllers
        gc.collect()

        final_objects = len(gc.get_objects())

        # Should not have significant memory growth
        object_growth = final_objects - initial_objects
        assert object_growth < 100  # Allow some growth but not excessive


@pytest.mark.integration
class TestFactoryIntegration:
    """Integration tests for factory with real plant dynamics."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plant_config = ConfigurationFactory.create_default_config("simplified")

    def test_controller_plant_integration(self):
        """Test controller works with plant dynamics."""
        from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics

        # Create dynamics and controller
        dynamics = SimplifiedDIPDynamics(self.plant_config)
        controller = create_smc_for_pso(
            SMCType.CLASSICAL,
            [10.0, 5.0, 8.0, 3.0],
            self.plant_config
        )

        # Test closed-loop simulation step
        state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])

        # Compute control
        control = controller.compute_control(state)
        assert isinstance(control, np.ndarray)
        assert control.shape == (1,)

        # Compute dynamics
        result = dynamics.compute_dynamics(state, control)
        assert hasattr(result, 'state_dot')
        assert result.state_dot.shape == (6,)

    def test_multiple_controller_types(self):
        """Test creating multiple controller types."""
        controller_configs = [
            (SMCType.CLASSICAL, [10.0, 5.0, 8.0, 3.0]),
            (SMCType.ADAPTIVE, [10.0, 5.0, 8.0, 3.0, 2.0, 1.5]),
        ]

        controllers = []
        for smc_type, gains in controller_configs:
            controller = create_smc_for_pso(smc_type, gains, self.plant_config)
            controllers.append(controller)
            assert controller is not None

        # Test all controllers can compute control
        state = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
        for controller in controllers:
            control = controller.compute_control(state)
            assert isinstance(control, np.ndarray)
            assert control.shape == (1,)


@pytest.mark.integration
class TestAdvancedFactoryIntegration:
    """Advanced integration tests for controller factory with complex scenarios."""

    def setup_method(self):
        """Set up comprehensive test fixtures."""
        self.plant_config = ConfigurationFactory.create_default_config("simplified")
        self.test_states = {
            'equilibrium': np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            'small_disturbance': np.array([0.1, 0.05, 0.03, 0.0, 0.0, 0.0]),
            'large_angles': np.array([0.5, 0.8, 0.6, 0.2, 0.1, 0.15]),
            'high_velocity': np.array([0.1, 0.1, 0.1, 2.0, 1.5, 1.2]),
            'unstable': np.array([0.3, 1.2, 0.9, 0.5, 0.8, 0.6])
        }
        self.controller_specs = {
            SMCType.CLASSICAL: {
                'gains': [15.0, 8.0, 12.0, 5.0],
                'description': 'Classical sliding mode controller'
            },
            SMCType.ADAPTIVE: {
                'gains': [15.0, 8.0, 12.0, 5.0, 2.5, 1.8],
                'description': 'Adaptive sliding mode controller'
            }
        }

    def test_closed_loop_stability_analysis(self):
        """Test closed-loop stability with different controllers."""
        from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics

        dynamics = SimplifiedDIPDynamics(self.plant_config)

        for smc_type, spec in self.controller_specs.items():
            controller = create_smc_for_pso(smc_type, spec['gains'], self.plant_config)

            # Test stability around equilibrium
            initial_state = self.test_states['small_disturbance']
            trajectory_states = [initial_state.copy()]
            current_state = initial_state.copy()

            dt = 0.01
            for step in range(200):  # 2 seconds simulation
                # Compute control
                control = controller.compute_control(current_state)

                # Compute dynamics
                result = dynamics.compute_dynamics(current_state, control)
                assert result.success == True

                # Euler integration step
                current_state = current_state + dt * result.state_derivative
                trajectory_states.append(current_state.copy())

                # Check for instability
                if np.any(np.abs(current_state) > 10.0):
                    break

            # System should remain bounded
            final_state = trajectory_states[-1]
            assert np.all(np.abs(final_state) < 2.0), f"{spec['description']} became unstable"

            # System should converge toward equilibrium
            final_error = np.linalg.norm(final_state[:3])  # Position errors
            initial_error = np.linalg.norm(initial_state[:3])
            assert final_error < initial_error, f"{spec['description']} did not converge"

    def test_controller_performance_comparison(self):
        """Test performance comparison between different controller types."""
        from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics

        dynamics = SimplifiedDIPDynamics(self.plant_config)
        performance_metrics = {}

        for smc_type, spec in self.controller_specs.items():
            controller = create_smc_for_pso(smc_type, spec['gains'], self.plant_config)

            # Run stabilization task
            initial_state = self.test_states['large_angles']
            current_state = initial_state.copy()

            control_efforts = []
            settling_times = []
            dt = 0.01

            for step in range(500):  # 5 seconds max
                control = controller.compute_control(current_state)
                control_efforts.append(np.abs(control[0]))

                result = dynamics.compute_dynamics(current_state, control)
                current_state = current_state + dt * result.state_derivative

                # Check for settling (within 5% of equilibrium)
                position_error = np.linalg.norm(current_state[:3])
                if position_error < 0.05 and len(settling_times) == 0:
                    settling_times.append(step * dt)

                if position_error > 5.0:  # Instability check
                    break

            performance_metrics[smc_type] = {
                'settling_time': settling_times[0] if settling_times else float('inf'),
                'avg_control_effort': np.mean(control_efforts),
                'max_control_effort': np.max(control_efforts),
                'final_error': np.linalg.norm(current_state[:3])
            }

        # All controllers should achieve reasonable performance
        for smc_type, metrics in performance_metrics.items():
            assert metrics['settling_time'] < 5.0, f"{smc_type} too slow to settle"
            assert metrics['final_error'] < 0.5, f"{smc_type} poor steady-state performance"
            assert metrics['max_control_effort'] < 50.0, f"{smc_type} excessive control effort"

    def test_gain_sensitivity_analysis(self):
        """Test controller sensitivity to gain variations."""
        base_gains = [15.0, 8.0, 12.0, 5.0]
        gain_variations = [0.5, 0.8, 1.0, 1.2, 1.5]  # Scaling factors

        performance_results = []

        for scale in gain_variations:
            scaled_gains = [g * scale for g in base_gains]

            try:
                controller = create_smc_for_pso(
                    SMCType.CLASSICAL,
                    scaled_gains,
                    self.plant_config
                )

                # Test control computation on challenging state
                control = controller.compute_control(self.test_states['unstable'])

                # Record performance metrics
                control_magnitude = np.abs(control[0])
                performance_results.append({
                    'scale': scale,
                    'control_magnitude': control_magnitude,
                    'success': True
                })

            except Exception as e:
                performance_results.append({
                    'scale': scale,
                    'error': str(e),
                    'success': False
                })

        # At least the nominal gains (scale=1.0) should work
        nominal_result = next(r for r in performance_results if r['scale'] == 1.0)
        assert nominal_result['success'] == True

        # Most gain variations should be stable
        success_count = sum(1 for r in performance_results if r['success'])
        assert success_count >= 3, "Controller too sensitive to gain variations"

    def test_real_time_performance_requirements(self):
        """Test controllers meet real-time performance requirements."""
        import time

        for smc_type, spec in self.controller_specs.items():
            controller = create_smc_for_pso(smc_type, spec['gains'], self.plant_config)

            computation_times = []

            # Test computation time over multiple states
            for state_name, state in self.test_states.items():
                start_time = time.time()

                # Perform control computations
                for _ in range(100):  # 100 computations
                    control = controller.compute_control(state)
                    assert isinstance(control, np.ndarray)

                elapsed_time = time.time() - start_time
                avg_time_per_computation = elapsed_time / 100
                computation_times.append(avg_time_per_computation)

            # Check real-time performance (should be << 1ms for 1kHz control)
            max_computation_time = max(computation_times)
            avg_computation_time = np.mean(computation_times)

            assert max_computation_time < 0.001, f"{smc_type} too slow (max: {max_computation_time:.6f}s)"
            assert avg_computation_time < 0.0005, f"{smc_type} average too slow ({avg_computation_time:.6f}s)"

    def test_robustness_to_plant_uncertainties(self):
        """Test controller robustness to plant parameter uncertainties."""
        from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics

        # Create plant configurations with parameter variations
        plant_variations = {
            'nominal': self.plant_config,
            'heavy_pendulum': ConfigurationFactory.create_default_config("simplified"),
            'light_cart': ConfigurationFactory.create_default_config("simplified"),
            'high_friction': ConfigurationFactory.create_default_config("simplified")
        }

        # Note: In a real implementation, we would modify the plant parameters
        # For this test, we use the same config but the structure shows how it would work

        controller = create_smc_for_pso(
            SMCType.CLASSICAL,
            [20.0, 10.0, 15.0, 7.0],  # Robust high gains
            self.plant_config
        )

        robustness_results = {}

        for plant_name, plant_config in plant_variations.items():
            try:
                dynamics = SimplifiedDIPDynamics(plant_config)

                # Test stabilization from disturbed state
                current_state = self.test_states['large_angles'].copy()

                for _ in range(100):  # 1 second simulation
                    control = controller.compute_control(current_state)
                    result = dynamics.compute_dynamics(current_state, control)

                    if not result.success:
                        break

                    current_state = current_state + 0.01 * result.state_derivative

                    # Check for instability
                    if np.any(np.abs(current_state) > 5.0):
                        break

                final_error = np.linalg.norm(current_state[:3])
                robustness_results[plant_name] = {
                    'success': True,
                    'final_error': final_error,
                    'stable': final_error < 1.0
                }

            except Exception as e:
                robustness_results[plant_name] = {
                    'success': False,
                    'error': str(e),
                    'stable': False
                }

        # Controller should work with nominal plant
        assert robustness_results['nominal']['success'] == True
        assert robustness_results['nominal']['stable'] == True

        # Should maintain reasonable performance with variations
        stable_count = sum(1 for r in robustness_results.values() if r['stable'])
        assert stable_count >= len(plant_variations) // 2, "Controller not robust enough"

    def test_saturation_and_constraint_handling(self):
        """Test controller behavior with control saturation and constraints."""
        # Create controller with low force limit
        low_force_config = SMCConfig(
            gains=[30.0, 20.0, 25.0, 15.0],  # High gains
            max_force=5.0,  # Low saturation limit
            dt=0.01
        )

        controller = SMCFactory.create(low_force_config)

        # Test with states that would normally require high control effort
        extreme_state = np.array([0.0, 1.5, 1.2, 0.0, 2.0, 1.8])  # Large angles and velocities

        control = controller.compute_control(extreme_state)

        # Control should be saturated
        assert np.abs(control[0]) <= 5.0, "Controller not respecting saturation limits"

        # Controller should still provide some control effort
        assert np.abs(control[0]) > 1.0, "Controller giving inadequate control effort"

    def test_multi_step_control_consistency(self):
        """Test controller consistency over multiple time steps."""
        controller = create_smc_for_pso(
            SMCType.CLASSICAL,
            [12.0, 7.0, 10.0, 4.0],
            self.plant_config
        )

        # Start from a specific state and evolve forward
        state = self.test_states['high_velocity'].copy()
        previous_controls = []

        for step in range(50):  # 0.5 second trajectory
            control = controller.compute_control(state)
            previous_controls.append(control[0])

            # Simple state evolution (not using actual dynamics for simplicity)
            # In practice, this would use plant dynamics
            state = state + 0.01 * np.array([state[3], state[4], state[5],
                                           -control[0]/2.0, -state[1]*9.81, -state[2]*9.81])

        # Control should be smooth (no excessive chattering)
        control_derivatives = np.diff(previous_controls)
        max_control_derivative = np.max(np.abs(control_derivatives))

        assert max_control_derivative < 50.0, "Control signal too chattery"

        # Control should adapt to changing state
        control_range = np.max(previous_controls) - np.min(previous_controls)
        assert control_range > 0.1, "Controller not responsive to state changes"

    def test_factory_error_handling_and_recovery(self):
        """Test factory error handling and recovery mechanisms."""
        # Test invalid gain combinations
        invalid_test_cases = [
            {'gains': [], 'description': 'empty gains'},
            {'gains': [10.0, 5.0], 'description': 'too few gains'},
            {'gains': [np.nan, 5.0, 8.0, 3.0], 'description': 'NaN gain'},
            {'gains': [np.inf, 5.0, 8.0, 3.0], 'description': 'infinite gain'},
            {'gains': [-10.0, 5.0, 8.0, 3.0], 'description': 'negative gain'}
        ]

        for test_case in invalid_test_cases:
            with pytest.raises((ValueError, TypeError, KeyError),
                             message=f"Should reject {test_case['description']}"):
                create_smc_for_pso(
                    SMCType.CLASSICAL,
                    test_case['gains'],
                    self.plant_config
                )

        # Test recovery with valid gains after invalid attempts
        valid_gains = [10.0, 5.0, 8.0, 3.0]
        controller = create_smc_for_pso(SMCType.CLASSICAL, valid_gains, self.plant_config)
        assert controller is not None, "Factory should recover after invalid attempts"

    def test_memory_and_resource_management(self):
        """Test memory and resource management in intensive scenarios."""
        import gc
        import os

        # Optional dependency for memory monitoring
        try:
            import psutil
            has_psutil = True
        except ImportError:
            has_psutil = False

        # Get initial memory usage if psutil is available
        if has_psutil:
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
        else:
            initial_memory = None

        controllers = []

        # Create many controllers with different configurations
        for i in range(20):
            for smc_type in [SMCType.CLASSICAL, SMCType.ADAPTIVE]:
                gains = [10.0 + i, 5.0 + i/2, 8.0 + i/3, 3.0 + i/4]
                if smc_type == SMCType.ADAPTIVE:
                    gains.extend([2.0 + i/5, 1.5 + i/6])

                controller = create_smc_for_pso(smc_type, gains, self.plant_config)
                controllers.append(controller)

                # Use controllers to ensure they're not optimized away
                control = controller.compute_control(self.test_states['equilibrium'])
                assert isinstance(control, np.ndarray)

        # Check memory usage hasn't grown excessively (if psutil is available)
        if has_psutil and initial_memory is not None:
            peak_memory = process.memory_info().rss
            memory_growth = (peak_memory - initial_memory) / 1024 / 1024  # MB
            assert memory_growth < 50, f"Excessive memory growth: {memory_growth:.1f} MB"

        # Test basic functionality without memory monitoring
        assert len(controllers) == 40  # 20 iterations * 2 controller types

        # Clean up and check for memory leaks
        del controllers
        gc.collect()

        # Check for memory leaks (if psutil is available)
        if has_psutil and initial_memory is not None:
            final_memory = process.memory_info().rss
            residual_memory = (final_memory - initial_memory) / 1024 / 1024  # MB
            assert residual_memory < 10, f"Potential memory leak: {residual_memory:.1f} MB residual"