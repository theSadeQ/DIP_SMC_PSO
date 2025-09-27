#==========================================================================================\\\
#================ tests/test_integration_end_to_end_deep.py ===============================\\\
#==========================================================================================\\\

"""
Deep Integration and End-to-End Tests.
COMPREHENSIVE JOB: Test complete workflows, system integration, and end-to-end functionality.
"""

import pytest
import numpy as np
import time
import json
import tempfile
import os
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import warnings


@dataclass
class SimulationResult:
    """Comprehensive simulation result container."""
    states: np.ndarray
    controls: np.ndarray
    times: np.ndarray
    performance_metrics: Dict[str, float]
    stability_analysis: Dict[str, Any]
    success: bool
    error_messages: List[str]


@dataclass
class ControllerConfig:
    """Controller configuration."""
    controller_type: str
    gains: List[float]
    max_force: float
    dt: float
    parameters: Dict[str, Any]


class MockCompleteControlSystem:
    """Complete mock control system for integration testing."""

    def __init__(self, plant_config: Dict, controller_config: ControllerConfig):
        self.plant_config = plant_config
        self.controller_config = controller_config
        self.reset()

    def reset(self):
        """Reset system state."""
        self.time = 0.0
        self.state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])  # Initial deviation
        self.control_history = []
        self.state_history = []
        self.time_history = []
        self.performance_data = {
            'settling_time': None,
            'overshoot': None,
            'steady_state_error': None,
            'control_effort': 0.0,
            'stability_margin': None
        }

    def simulate_step(self, reference: Optional[np.ndarray] = None) -> bool:
        """Simulate one time step."""
        try:
            # Controller computation
            control = self._compute_control(self.state, reference)

            # Plant dynamics
            new_state = self._simulate_plant_dynamics(self.state, control)

            # Update history
            self.control_history.append(control)
            self.state_history.append(self.state.copy())
            self.time_history.append(self.time)

            # Update state and time
            self.state = new_state
            self.time += self.controller_config.dt

            return True

        except Exception as e:
            warnings.warn(f"Simulation step failed: {e}")
            return False

    def _compute_control(self, state: np.ndarray, reference: Optional[np.ndarray]) -> float:
        """Compute control based on controller type."""
        error = state if reference is None else state - reference

        if self.controller_config.controller_type == "classical_smc":
            return self._classical_smc_control(error)
        elif self.controller_config.controller_type == "adaptive_smc":
            return self._adaptive_smc_control(error)
        elif self.controller_config.controller_type == "pid":
            return self._pid_control(error)
        else:
            return self._default_control(error)

    def _classical_smc_control(self, error: np.ndarray) -> float:
        """Classical sliding mode control."""
        gains = np.array(self.controller_config.gains)
        sigma = np.dot(gains, error)

        # Switching function with boundary layer
        boundary_layer = self.controller_config.parameters.get('boundary_layer', 0.01)
        if abs(sigma) <= boundary_layer:
            switching = sigma / boundary_layer
        else:
            switching = np.sign(sigma)

        control = -switching * 10.0  # Control gain
        return np.clip(control, -self.controller_config.max_force, self.controller_config.max_force)

    def _adaptive_smc_control(self, error: np.ndarray) -> float:
        """Adaptive sliding mode control."""
        gains = np.array(self.controller_config.gains)
        sigma = np.dot(gains, error)

        # Adaptive law (simplified)
        adaptation_rate = self.controller_config.parameters.get('adaptation_rate', 0.1)
        control_gain = 10.0 + adaptation_rate * abs(sigma)

        switching = np.tanh(sigma / 0.01)  # Smooth switching
        control = -switching * control_gain

        return np.clip(control, -self.controller_config.max_force, self.controller_config.max_force)

    def _pid_control(self, error: np.ndarray) -> float:
        """PID control."""
        # Simple PID on first state (cart position)
        kp, ki, kd = self.controller_config.gains[:3]

        # Proportional term
        proportional = kp * error[0]

        # Derivative term (velocity)
        derivative = kd * error[3] if len(error) > 3 else 0

        # Integral term (simplified)
        integral = ki * error[0] * self.controller_config.dt

        control = proportional + integral + derivative
        return np.clip(control, -self.controller_config.max_force, self.controller_config.max_force)

    def _default_control(self, error: np.ndarray) -> float:
        """Default control law."""
        return -np.sum(self.controller_config.gains[:len(error)] * error)

    def _simulate_plant_dynamics(self, state: np.ndarray, control: float) -> np.ndarray:
        """Simulate plant dynamics."""
        # Mock double inverted pendulum dynamics
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # Simplified dynamics
        m_cart = self.plant_config.get('cart_mass', 1.0)
        m1 = self.plant_config.get('pendulum1_mass', 0.5)
        m2 = self.plant_config.get('pendulum2_mass', 0.3)
        l1 = self.plant_config.get('pendulum1_length', 0.5)
        l2 = self.plant_config.get('pendulum2_length', 0.3)
        g = self.plant_config.get('gravity', 9.81)

        # Simplified equations (linearized around upright)
        x_ddot = control / (m_cart + m1 + m2)
        theta1_ddot = -g/l1 * theta1 - 0.1 * theta1_dot  # Damping
        theta2_ddot = -g/l2 * theta2 - 0.1 * theta2_dot  # Damping

        # Add coupling effects
        theta1_ddot += 0.1 * x_ddot  # Cart acceleration affects pendulum
        theta2_ddot += 0.05 * theta1_ddot  # First pendulum affects second

        # Integration (Euler method)
        dt = self.controller_config.dt
        new_state = np.array([
            x + x_dot * dt,
            theta1 + theta1_dot * dt,
            theta2 + theta2_dot * dt,
            x_dot + x_ddot * dt,
            theta1_dot + theta1_ddot * dt,
            theta2_dot + theta2_ddot * dt
        ])

        return new_state

    def run_simulation(self, duration: float, reference: Optional[np.ndarray] = None) -> SimulationResult:
        """Run complete simulation."""
        n_steps = int(duration / self.controller_config.dt)
        success = True
        error_messages = []

        for step in range(n_steps):
            if not self.simulate_step(reference):
                success = False
                error_messages.append(f"Step {step} failed")
                break

            # Safety checks
            if np.any(np.abs(self.state) > 100):  # Blow-up detection
                success = False
                error_messages.append("System blew up")
                break

        # Convert histories to arrays
        states = np.array(self.state_history)
        controls = np.array(self.control_history)
        times = np.array(self.time_history)

        # Compute performance metrics
        performance_metrics = self._compute_performance_metrics(states, controls, times, reference)

        # Stability analysis
        stability_analysis = self._analyze_stability(states, controls, times)

        return SimulationResult(
            states=states,
            controls=controls,
            times=times,
            performance_metrics=performance_metrics,
            stability_analysis=stability_analysis,
            success=success,
            error_messages=error_messages
        )

    def _compute_performance_metrics(self, states: np.ndarray, controls: np.ndarray,
                                   times: np.ndarray, reference: Optional[np.ndarray]) -> Dict[str, float]:
        """Compute comprehensive performance metrics."""
        metrics = {}

        if len(states) == 0:
            return metrics

        # Settling time analysis (2% criteria)
        reference_value = 0.0 if reference is None else reference[0]
        position_error = np.abs(states[:, 0] - reference_value)
        settling_tolerance = 0.02 * (np.max(position_error) + 1e-6)

        settled_indices = np.where(position_error <= settling_tolerance)[0]
        if len(settled_indices) > 0:
            # Find last unsettled point
            for i in range(len(settled_indices) - 1, -1, -1):
                if settled_indices[i] == len(position_error) - 1:
                    continue
                if i == 0 or settled_indices[i] - settled_indices[i-1] > 10:  # Gap indicates unsettled
                    metrics['settling_time'] = times[settled_indices[i]]
                    break

        # Overshoot analysis
        max_position = np.max(states[:, 0])
        metrics['overshoot'] = (max_position - reference_value) / (reference_value + 1e-6) if reference_value != 0 else max_position

        # Steady-state error
        if len(states) > 10:
            steady_state_error = np.mean(np.abs(states[-10:, 0] - reference_value))
            metrics['steady_state_error'] = steady_state_error

        # Control effort (RMS)
        metrics['control_effort_rms'] = np.sqrt(np.mean(controls**2))
        metrics['control_effort_total'] = np.sum(np.abs(controls)) * self.controller_config.dt

        # Rise time (10% to 90%)
        if reference_value != 0:
            ten_percent = 0.1 * reference_value
            ninety_percent = 0.9 * reference_value

            ten_percent_time = None
            ninety_percent_time = None

            for i, pos in enumerate(states[:, 0]):
                if ten_percent_time is None and pos >= ten_percent:
                    ten_percent_time = times[i]
                if ninety_percent_time is None and pos >= ninety_percent:
                    ninety_percent_time = times[i]
                    break

            if ten_percent_time is not None and ninety_percent_time is not None:
                metrics['rise_time'] = ninety_percent_time - ten_percent_time

        return metrics

    def _analyze_stability(self, states: np.ndarray, controls: np.ndarray, times: np.ndarray) -> Dict[str, Any]:
        """Analyze system stability."""
        analysis = {}

        if len(states) == 0:
            return analysis

        # Bounded input bounded output (BIBO) stability
        max_state_norm = np.max(np.linalg.norm(states, axis=1))
        max_control = np.max(np.abs(controls))

        analysis['bibo_stable'] = max_state_norm < 100 and max_control < self.controller_config.max_force * 1.1

        # Lyapunov-like stability (energy analysis)
        if len(states) > 1:
            # Simple energy function
            kinetic_energy = 0.5 * np.sum(states[:, 3:]**2, axis=1)  # Velocity terms
            potential_energy = 0.5 * np.sum(states[:, :3]**2, axis=1)  # Position terms
            total_energy = kinetic_energy + potential_energy

            energy_decrease = total_energy[0] - total_energy[-1]
            analysis['energy_dissipated'] = energy_decrease > 0
            analysis['final_energy'] = total_energy[-1]

        # Oscillation analysis
        if len(states) > 20:
            position = states[:, 0]
            # Simple oscillation detection using zero crossings
            zero_crossings = np.sum(np.diff(np.sign(position)) != 0)
            analysis['oscillatory'] = zero_crossings > 5
            analysis['damping_effective'] = np.std(position[-10:]) < np.std(position[:10])

        return analysis


@pytest.mark.integration
class TestSystemIntegration:
    """Integration tests for complete control system."""

    @pytest.fixture
    def plant_config(self):
        """Standard plant configuration."""
        return {
            'cart_mass': 1.0,
            'pendulum1_mass': 0.5,
            'pendulum2_mass': 0.3,
            'pendulum1_length': 0.5,
            'pendulum2_length': 0.3,
            'gravity': 9.81
        }

    @pytest.fixture
    def smc_controller_config(self):
        """SMC controller configuration."""
        return ControllerConfig(
            controller_type="classical_smc",
            gains=[5.0, 15.0, 10.0, 2.0, 8.0, 3.0],
            max_force=20.0,
            dt=0.01,
            parameters={'boundary_layer': 0.01}
        )

    def test_complete_smc_workflow(self, plant_config, smc_controller_config):
        """Test complete SMC control workflow."""
        system = MockCompleteControlSystem(plant_config, smc_controller_config)

        # Run simulation
        duration = 5.0  # 5 seconds
        result = system.run_simulation(duration)

        # Verify basic success
        assert result.success, f"Simulation failed: {result.error_messages}"
        assert len(result.states) > 0, "No simulation data generated"
        assert len(result.controls) == len(result.states), "Mismatched data lengths"

        # Performance verification
        assert result.performance_metrics['control_effort_rms'] < 50.0, "Control effort too high"
        assert result.performance_metrics['steady_state_error'] < 0.1, "Poor steady-state performance"

        # Stability verification
        assert result.stability_analysis['bibo_stable'], "System not BIBO stable"

        # System should converge
        final_state_norm = np.linalg.norm(result.states[-1])
        assert final_state_norm < 1.0, "System did not converge"

    def test_controller_comparison_integration(self, plant_config):
        """Test integration of multiple controllers."""
        controller_configs = {
            'smc': ControllerConfig(
                controller_type="classical_smc",
                gains=[5.0, 15.0, 10.0, 2.0, 8.0, 3.0],
                max_force=20.0,
                dt=0.01,
                parameters={'boundary_layer': 0.01}
            ),
            'adaptive': ControllerConfig(
                controller_type="adaptive_smc",
                gains=[3.0, 10.0, 8.0, 1.5, 5.0, 2.0],
                max_force=20.0,
                dt=0.01,
                parameters={'adaptation_rate': 0.1}
            ),
            'pid': ControllerConfig(
                controller_type="pid",
                gains=[10.0, 2.0, 5.0, 0, 0, 0],
                max_force=20.0,
                dt=0.01,
                parameters={}
            )
        }

        results = {}
        duration = 3.0

        for name, config in controller_configs.items():
            system = MockCompleteControlSystem(plant_config, config)
            result = system.run_simulation(duration)

            assert result.success, f"{name} controller failed: {result.error_messages}"
            results[name] = result

        # Compare performance
        performance_comparison = {}
        for name, result in results.items():
            performance_comparison[name] = {
                'settling_time': result.performance_metrics.get('settling_time', duration),
                'overshoot': result.performance_metrics.get('overshoot', 0),
                'control_effort': result.performance_metrics['control_effort_rms'],
                'final_error': np.linalg.norm(result.states[-1])
            }

        # All controllers should achieve reasonable performance
        for name, perf in performance_comparison.items():
            assert perf['final_error'] < 0.5, f"{name} controller has poor final accuracy"
            assert perf['control_effort'] < 50.0, f"{name} controller uses excessive control effort"

    def test_disturbance_rejection_integration(self, plant_config, smc_controller_config):
        """Test system integration with disturbances."""
        system = MockCompleteControlSystem(plant_config, smc_controller_config)

        # Add disturbance to plant dynamics
        original_dynamics = system._simulate_plant_dynamics

        def dynamics_with_disturbance(state, control):
            # Add periodic disturbance
            disturbance = 0.5 * np.sin(2 * np.pi * system.time)  # 1 Hz disturbance
            modified_control = control + disturbance
            return original_dynamics(state, modified_control)

        system._simulate_plant_dynamics = dynamics_with_disturbance

        # Run simulation
        duration = 8.0  # Longer duration to see disturbance effects
        result = system.run_simulation(duration)

        assert result.success, f"Disturbed simulation failed: {result.error_messages}"

        # SMC should still achieve reasonable performance despite disturbances
        assert result.performance_metrics['steady_state_error'] < 0.2, "Poor disturbance rejection"
        assert result.stability_analysis['bibo_stable'], "Lost stability under disturbance"

        # Final state should still be bounded
        final_state_norm = np.linalg.norm(result.states[-1])
        assert final_state_norm < 2.0, "System did not handle disturbance well"

    def test_reference_tracking_integration(self, plant_config, smc_controller_config):
        """Test reference tracking integration."""
        system = MockCompleteControlSystem(plant_config, smc_controller_config)

        # Step reference
        reference = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # 1m cart position

        duration = 6.0
        result = system.run_simulation(duration, reference)

        assert result.success, f"Reference tracking failed: {result.error_messages}"

        # Should track reference
        final_position = result.states[-1, 0]
        tracking_error = abs(final_position - reference[0])
        assert tracking_error < 0.1, f"Poor reference tracking: error = {tracking_error}"

        # Should have reasonable settling time
        settling_time = result.performance_metrics.get('settling_time')
        if settling_time is not None:
            assert settling_time < 5.0, "Settling time too slow"

    def test_parameter_variation_robustness(self, plant_config, smc_controller_config):
        """Test system robustness to parameter variations."""
        nominal_system = MockCompleteControlSystem(plant_config, smc_controller_config)
        nominal_result = nominal_system.run_simulation(3.0)

        assert nominal_result.success, "Nominal system should work"

        # Test with parameter variations
        variations = [
            {'cart_mass': 1.5},         # +50% cart mass
            {'pendulum1_mass': 0.3},    # -40% pendulum mass
            {'gravity': 8.0},           # Different gravity
        ]

        for variation in variations:
            varied_config = plant_config.copy()
            varied_config.update(variation)

            varied_system = MockCompleteControlSystem(varied_config, smc_controller_config)
            varied_result = varied_system.run_simulation(3.0)

            assert varied_result.success, f"System failed with variation {variation}"

            # Performance should degrade gracefully
            nominal_error = np.linalg.norm(nominal_result.states[-1])
            varied_error = np.linalg.norm(varied_result.states[-1])

            # Error shouldn't increase by more than factor of 3
            assert varied_error < nominal_error * 3, f"Poor robustness to {variation}"


@pytest.mark.end_to_end
class TestEndToEndWorkflows:
    """End-to-end workflow tests."""

    def test_configuration_to_simulation_workflow(self):
        """Test complete workflow from configuration to simulation results."""

        # Configuration phase
        config_data = {
            'plant': {
                'cart_mass': 1.2,
                'pendulum1_mass': 0.6,
                'pendulum2_mass': 0.4,
                'pendulum1_length': 0.6,
                'pendulum2_length': 0.4,
                'gravity': 9.81
            },
            'controller': {
                'type': 'classical_smc',
                'gains': [6.0, 18.0, 12.0, 2.5, 9.0, 3.5],
                'max_force': 25.0,
                'dt': 0.005,
                'parameters': {
                    'boundary_layer': 0.02
                }
            },
            'simulation': {
                'duration': 4.0,
                'initial_state': [0.2, 0.15, 0.1, 0.0, 0.0, 0.0],
                'reference': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            }
        }

        # Create system from configuration
        controller_config = ControllerConfig(
            controller_type=config_data['controller']['type'],
            gains=config_data['controller']['gains'],
            max_force=config_data['controller']['max_force'],
            dt=config_data['controller']['dt'],
            parameters=config_data['controller']['parameters']
        )

        system = MockCompleteControlSystem(config_data['plant'], controller_config)

        # Set initial state
        system.state = np.array(config_data['simulation']['initial_state'])

        # Run simulation
        reference = np.array(config_data['simulation']['reference'])
        result = system.run_simulation(config_data['simulation']['duration'], reference)

        # Verify workflow completion
        assert result.success, "End-to-end workflow failed"
        assert len(result.states) > 0, "No simulation data"

        # Results should be reasonable
        assert result.performance_metrics['control_effort_rms'] < 100.0
        assert result.stability_analysis['bibo_stable']

    def test_optimization_workflow_simulation(self):
        """Test simulation workflow for optimization scenarios."""

        # Mock optimization process
        def objective_function(gains):
            """Objective function for optimization."""
            controller_config = ControllerConfig(
                controller_type="classical_smc",
                gains=gains.tolist(),
                max_force=20.0,
                dt=0.01,
                parameters={'boundary_layer': 0.01}
            )

            plant_config = {
                'cart_mass': 1.0,
                'pendulum1_mass': 0.5,
                'pendulum2_mass': 0.3,
                'pendulum1_length': 0.5,
                'pendulum2_length': 0.3,
                'gravity': 9.81
            }

            system = MockCompleteControlSystem(plant_config, controller_config)
            result = system.run_simulation(2.0)

            if not result.success:
                return 1e6  # Large penalty for failure

            # Multi-objective cost
            settling_time = result.performance_metrics.get('settling_time', 10.0)
            control_effort = result.performance_metrics['control_effort_rms']
            final_error = np.linalg.norm(result.states[-1])

            cost = settling_time + 0.1 * control_effort + 10 * final_error
            return cost

        # Test multiple gain sets (simulating optimization iterations)
        gain_sets = [
            np.array([5.0, 15.0, 10.0, 2.0, 8.0, 3.0]),  # Initial guess
            np.array([6.0, 18.0, 12.0, 2.5, 9.0, 3.5]),  # Iteration 1
            np.array([4.5, 12.0, 8.0, 1.8, 7.0, 2.5]),   # Iteration 2
        ]

        costs = []
        for gains in gain_sets:
            cost = objective_function(gains)
            costs.append(cost)

            # Each evaluation should succeed
            assert cost < 1e5, f"Optimization evaluation failed for gains {gains}"

        # Should show some variation in performance
        cost_range = max(costs) - min(costs)
        assert cost_range > 0.1, "No performance variation detected"

    def test_batch_simulation_workflow(self):
        """Test batch simulation workflow."""
        # Configuration for batch runs
        base_plant_config = {
            'cart_mass': 1.0,
            'pendulum1_mass': 0.5,
            'pendulum2_mass': 0.3,
            'pendulum1_length': 0.5,
            'pendulum2_length': 0.3,
            'gravity': 9.81
        }

        controller_config = ControllerConfig(
            controller_type="classical_smc",
            gains=[5.0, 15.0, 10.0, 2.0, 8.0, 3.0],
            max_force=20.0,
            dt=0.01,
            parameters={'boundary_layer': 0.01}
        )

        # Batch variations
        initial_conditions = [
            [0.1, 0.1, 0.1, 0.0, 0.0, 0.0],
            [0.2, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.3, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.2, 0.0, 0.0, 0.0],
            [0.15, 0.15, 0.15, 0.0, 0.0, 0.0],
        ]

        batch_results = []
        duration = 3.0

        for i, initial_state in enumerate(initial_conditions):
            system = MockCompleteControlSystem(base_plant_config, controller_config)
            system.state = np.array(initial_state)

            result = system.run_simulation(duration)

            assert result.success, f"Batch run {i} failed: {result.error_messages}"
            batch_results.append(result)

        # Analyze batch results
        final_errors = [np.linalg.norm(result.states[-1]) for result in batch_results]
        control_efforts = [result.performance_metrics['control_effort_rms'] for result in batch_results]

        # All runs should converge
        assert all(error < 0.5 for error in final_errors), "Some batch runs failed to converge"

        # Control effort should be reasonable for all runs
        assert all(effort < 50.0 for effort in control_efforts), "Excessive control effort in batch runs"

        # Statistical analysis
        mean_final_error = np.mean(final_errors)
        std_final_error = np.std(final_errors)

        assert mean_final_error < 0.2, "Poor average performance across batch"
        assert std_final_error < 0.3, "Inconsistent performance across batch"

    def test_configuration_file_workflow(self):
        """Test complete workflow with configuration file I/O."""

        # Create temporary configuration file
        config_data = {
            'experiment_name': 'test_smc_control',
            'plant_parameters': {
                'cart_mass': 1.1,
                'pendulum1_mass': 0.55,
                'pendulum2_mass': 0.35,
                'pendulum1_length': 0.55,
                'pendulum2_length': 0.35,
                'gravity': 9.81
            },
            'controller_parameters': {
                'type': 'classical_smc',
                'gains': [5.5, 16.0, 11.0, 2.2, 8.5, 3.2],
                'max_force': 22.0,
                'dt': 0.008,
                'boundary_layer': 0.015
            },
            'simulation_settings': {
                'duration': 3.5,
                'save_results': True,
                'plot_results': False
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f, indent=2)
            config_file_path = f.name

        try:
            # Load configuration
            with open(config_file_path, 'r') as f:
                loaded_config = json.load(f)

            # Create system from loaded configuration
            controller_config = ControllerConfig(
                controller_type=loaded_config['controller_parameters']['type'],
                gains=loaded_config['controller_parameters']['gains'],
                max_force=loaded_config['controller_parameters']['max_force'],
                dt=loaded_config['controller_parameters']['dt'],
                parameters={'boundary_layer': loaded_config['controller_parameters']['boundary_layer']}
            )

            system = MockCompleteControlSystem(loaded_config['plant_parameters'], controller_config)

            # Run simulation based on loaded settings
            result = system.run_simulation(loaded_config['simulation_settings']['duration'])

            # Verify workflow
            assert result.success, "Configuration file workflow failed"

            # Save results if requested
            if loaded_config['simulation_settings']['save_results']:
                results_data = {
                    'experiment_name': loaded_config['experiment_name'],
                    'success': result.success,
                    'performance_metrics': result.performance_metrics,
                    'stability_analysis': result.stability_analysis,
                    'final_state': result.states[-1].tolist() if len(result.states) > 0 else None
                }

                with tempfile.NamedTemporaryFile(mode='w', suffix='_results.json', delete=False) as rf:
                    json.dump(results_data, rf, indent=2, default=str)  # default=str for numpy types
                    results_file_path = rf.name

                # Verify results file
                with open(results_file_path, 'r') as rf:
                    loaded_results = json.load(rf)

                assert loaded_results['success'] == True
                assert 'performance_metrics' in loaded_results
                assert 'stability_analysis' in loaded_results

                os.unlink(results_file_path)

        finally:
            # Cleanup
            os.unlink(config_file_path)

    def test_real_time_simulation_workflow(self):
        """Test real-time simulation workflow with timing constraints."""
        controller_config = ControllerConfig(
            controller_type="classical_smc",
            gains=[5.0, 15.0, 10.0, 2.0, 8.0, 3.0],
            max_force=20.0,
            dt=0.01,  # 100 Hz
            parameters={'boundary_layer': 0.01}
        )

        plant_config = {
            'cart_mass': 1.0,
            'pendulum1_mass': 0.5,
            'pendulum2_mass': 0.3,
            'pendulum1_length': 0.5,
            'pendulum2_length': 0.3,
            'gravity': 9.81
        }

        system = MockCompleteControlSystem(plant_config, controller_config)

        # Real-time simulation with timing checks
        duration = 1.0  # 1 second
        n_steps = int(duration / controller_config.dt)

        computation_times = []
        wall_clock_start = time.perf_counter()

        for step in range(n_steps):
            step_start = time.perf_counter()

            # Single simulation step
            success = system.simulate_step()
            assert success, f"Real-time step {step} failed"

            step_end = time.perf_counter()
            computation_time = step_end - step_start
            computation_times.append(computation_time)

            # Real-time constraint: computation should be much faster than time step
            assert computation_time < controller_config.dt * 0.1, f"Step {step} too slow: {computation_time:.6f}s"

        wall_clock_end = time.perf_counter()
        total_wall_time = wall_clock_end - wall_clock_start

        # Overall timing analysis
        mean_computation_time = np.mean(computation_times)
        max_computation_time = np.max(computation_times)

        # Real-time performance metrics
        real_time_factor = duration / total_wall_time  # Should be < 1 for real-time capable

        assert real_time_factor > 0.1, "System too slow for real-time operation"
        assert mean_computation_time < controller_config.dt * 0.05, "Average computation time too high"
        assert max_computation_time < controller_config.dt * 0.2, "Worst-case computation time too high"

        # System should remain stable during real-time operation
        final_state_norm = np.linalg.norm(system.state)
        assert final_state_norm < 10.0, "System became unstable during real-time operation"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])