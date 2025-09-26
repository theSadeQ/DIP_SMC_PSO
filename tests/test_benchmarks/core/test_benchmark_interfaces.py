#==========================================================================================\\
#============== tests/test_benchmarks/core/test_benchmark_interfaces.py ================\\
#==========================================================================================\\

"""
Benchmark Interface Compatibility Tests - Mission 7 Critical Infrastructure

COMPREHENSIVE JOB: Ensure all components can be benchmarked together seamlessly.
This module validates that benchmarking framework works correctly with ALL:
- Controller types (Classical SMC, Adaptive SMC, STA-SMC, Hybrid)
- Plant dynamics models (Simplified, Full nonlinear)
- Integration methods (Euler, RK4, RK45)
- Parameter ranges (Realistic bounds validation)

CRITICAL SUCCESS CRITERIA:
- 90%+ benchmark success rate (target: eliminate interface failures)
- All controller types are benchmarkable consistently
- Realistic parameter validation ensures meaningful results
- Cross-component integration workflows validated
"""

import pytest
import numpy as np
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "src"))

try:
    from src.controllers.factory.smc_factory import SMCFactory, SMCType, SMCConfig
    from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
    from src.plant.models.full.dynamics import FullDIPDynamics
    from src.simulation.engines.simulation_runner import SimulationRunner
    from src.config import load_config
    from src.utils.config_compatibility import wrap_physics_config
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


@dataclass
class BenchmarkableComponent:
    """Represents a component that can be benchmarked."""
    name: str
    component: Any
    expected_interface: List[str]  # Required methods/attributes
    parameter_bounds: Optional[Dict[str, Tuple[float, float]]] = None


@dataclass
class InterfaceCompatibilityResult:
    """Results of interface compatibility validation."""
    component_name: str
    controller_type: str
    dynamics_type: str
    success: bool
    interface_errors: List[str]
    parameter_errors: List[str]
    performance_metrics: Dict[str, float]
    execution_time: float


class BenchmarkInterfaceValidator:
    """Validates interface compatibility across all benchmarkable components."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize with system configuration."""
        self.config_path = config_path or "config.yaml"
        self.load_system_config()
        self.results: List[InterfaceCompatibilityResult] = []

    def load_system_config(self):
        """Load and prepare system configuration."""
        try:
            self.config = load_config(self.config_path, allow_unknown=True)
            self.physics_config = wrap_physics_config(self.config.physics.model_dump())
        except Exception as e:
            # Fallback to minimal config for testing
            self.physics_config = self._create_minimal_physics_config()

    def _create_minimal_physics_config(self):
        """Create minimal physics configuration for testing."""
        return {
            # Cart parameters
            'cart_mass': 1.0,
            'cart_friction': 0.1,

            # Pendulum 1 (bottom)
            'pendulum1_mass': 0.3,
            'pendulum1_length': 0.5,
            'pendulum1_inertia': 0.025,
            'joint1_friction': 0.01,

            # Pendulum 2 (top)
            'pendulum2_mass': 0.2,
            'pendulum2_length': 0.3,
            'pendulum2_inertia': 0.015,
            'joint2_friction': 0.01,

            # Environmental
            'gravity': 9.81,
            'max_force': 100.0
        }

    def validate_controller_interfaces(self) -> Dict[str, List[InterfaceCompatibilityResult]]:
        """Validate all controller types can be benchmarked."""
        results = {}

        # Test all SMC controller types
        for smc_type in SMCType:
            controller_results = []

            # Test with different dynamics models
            dynamics_models = [
                ("SimplifiedDIP", lambda: SimplifiedDIPDynamics(self.physics_config)),
                ("FullDIP", lambda: FullDIPDynamics(self.physics_config))
            ]

            for dynamics_name, dynamics_factory in dynamics_models:
                try:
                    result = self._test_controller_dynamics_compatibility(
                        smc_type, dynamics_name, dynamics_factory
                    )
                    controller_results.append(result)
                except Exception as e:
                    # Record failure
                    result = InterfaceCompatibilityResult(
                        component_name="Controller-Dynamics Interface",
                        controller_type=smc_type.value,
                        dynamics_type=dynamics_name,
                        success=False,
                        interface_errors=[str(e)],
                        parameter_errors=[],
                        performance_metrics={},
                        execution_time=0.0
                    )
                    controller_results.append(result)

            results[smc_type.value] = controller_results

        return results

    def _test_controller_dynamics_compatibility(
        self,
        smc_type: SMCType,
        dynamics_name: str,
        dynamics_factory
    ) -> InterfaceCompatibilityResult:
        """Test compatibility between controller and dynamics."""
        start_time = time.perf_counter()
        interface_errors = []
        parameter_errors = []
        performance_metrics = {}

        try:
            # Create dynamics instance
            dynamics = dynamics_factory()

            # Validate dynamics interface
            required_dynamics_methods = ['compute_dynamics', 'state_dim', 'control_dim']
            for method in required_dynamics_methods:
                if not hasattr(dynamics, method):
                    interface_errors.append(f"Dynamics missing required method: {method}")

            # Create controller with realistic parameters
            realistic_gains = self._get_realistic_gains(smc_type)
            config = SMCConfig(
                gains=realistic_gains,
                max_force=self.physics_config.get('max_force', 100.0),
                dt=0.01
            )

            controller = SMCFactory.create_controller(smc_type, config)

            # Validate controller interface
            required_controller_methods = ['compute_control', 'initialize_state', 'initialize_history']
            for method in required_controller_methods:
                if not hasattr(controller, method):
                    interface_errors.append(f"Controller missing required method: {method}")

            # Test actual integration
            if not interface_errors:
                try:
                    performance_metrics = self._benchmark_integration_performance(
                        controller, dynamics
                    )
                except Exception as e:
                    interface_errors.append(f"Integration failed: {str(e)}")

        except Exception as e:
            interface_errors.append(f"Component creation failed: {str(e)}")

        execution_time = time.perf_counter() - start_time

        return InterfaceCompatibilityResult(
            component_name="Controller-Dynamics Integration",
            controller_type=smc_type.value,
            dynamics_type=dynamics_name,
            success=len(interface_errors) == 0 and len(parameter_errors) == 0,
            interface_errors=interface_errors,
            parameter_errors=parameter_errors,
            performance_metrics=performance_metrics,
            execution_time=execution_time
        )

    def _benchmark_integration_performance(
        self,
        controller,
        dynamics
    ) -> Dict[str, float]:
        """Benchmark basic integration performance."""
        performance = {}

        # Initialize test state
        state = np.array([0.1, 0.1, 0.05, 0.0, 0.0, 0.0])  # Small perturbation
        controller_state = controller.initialize_state()
        history = controller.initialize_history()

        # Benchmark control computation speed
        n_control_tests = 100
        start_time = time.perf_counter()

        for _ in range(n_control_tests):
            control_output = controller.compute_control(state, controller_state, history)
            # Extract control force (handle different return formats)
            if hasattr(control_output, 'force'):
                control_force = control_output.force
            elif isinstance(control_output, (list, tuple)):
                control_force = control_output[0] if control_output else 0.0
            elif isinstance(control_output, (int, float)):
                control_force = control_output
            else:
                control_force = 0.0

        control_time = time.perf_counter() - start_time
        performance['avg_control_time'] = control_time / n_control_tests

        # Benchmark dynamics computation speed
        n_dynamics_tests = 100
        start_time = time.perf_counter()

        for _ in range(n_dynamics_tests):
            state_dot = dynamics.compute_dynamics(state, control_force)

        dynamics_time = time.perf_counter() - start_time
        performance['avg_dynamics_time'] = dynamics_time / n_dynamics_tests

        # Test numerical stability
        performance['control_magnitude'] = abs(float(control_force))
        performance['state_derivative_norm'] = float(np.linalg.norm(state_dot))

        return performance

    def _get_realistic_gains(self, smc_type: SMCType) -> List[float]:
        """Get realistic gain values for each SMC type."""
        realistic_gains = {
            SMCType.CLASSICAL: [10.0, 5.0, 3.0, 2.0, 50.0, 1.0],
            SMCType.ADAPTIVE: [8.0, 4.0, 2.5, 1.5, 0.5],
            SMCType.SUPER_TWISTING: [15.0, 10.0, 8.0, 4.0, 2.5, 1.5],
            SMCType.HYBRID: [12.0, 3.0, 8.0, 2.0]
        }

        return realistic_gains.get(smc_type, [1.0] * 6)

    def validate_parameter_bounds(self) -> Dict[str, bool]:
        """Validate that all components work within realistic parameter bounds."""
        validation_results = {}

        for smc_type in SMCType:
            spec = SMCFactory.get_gain_specification(smc_type)
            bounds = spec.gain_bounds

            # Test boundary values
            boundary_tests = [
                ("min_bounds", [bound[0] for bound in bounds]),
                ("max_bounds", [bound[1] for bound in bounds]),
                ("mid_bounds", [(bound[0] + bound[1]) / 2 for bound in bounds])
            ]

            smc_results = {}
            for test_name, gains in boundary_tests:
                try:
                    config = SMCConfig(gains=gains, max_force=100.0)
                    controller = SMCFactory.create_controller(smc_type, config)
                    smc_results[test_name] = True
                except Exception:
                    smc_results[test_name] = False

            validation_results[smc_type.value] = all(smc_results.values())

        return validation_results

    def validate_cross_component_workflows(self) -> Dict[str, InterfaceCompatibilityResult]:
        """Validate complete workflows across components."""
        workflow_results = {}

        # Test complete simulation workflows
        for smc_type in SMCType:
            try:
                result = self._test_complete_simulation_workflow(smc_type)
                workflow_results[f"{smc_type.value}_workflow"] = result
            except Exception as e:
                workflow_results[f"{smc_type.value}_workflow"] = InterfaceCompatibilityResult(
                    component_name="Complete Workflow",
                    controller_type=smc_type.value,
                    dynamics_type="Workflow",
                    success=False,
                    interface_errors=[str(e)],
                    parameter_errors=[],
                    performance_metrics={},
                    execution_time=0.0
                )

        return workflow_results

    def _test_complete_simulation_workflow(self, smc_type: SMCType) -> InterfaceCompatibilityResult:
        """Test a complete simulation workflow from start to finish."""
        start_time = time.perf_counter()
        interface_errors = []
        performance_metrics = {}

        try:
            # Create components
            dynamics = SimplifiedDIPDynamics(self.physics_config)
            gains = self._get_realistic_gains(smc_type)
            config = SMCConfig(gains=gains, max_force=100.0, dt=0.01)
            controller = SMCFactory.create_controller(smc_type, config)

            # Initialize simulation
            initial_state = np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0])
            sim_time = 1.0  # Short simulation for testing
            dt = 0.01

            # Run simulation loop
            state = initial_state.copy()
            controller_state = controller.initialize_state()
            history = controller.initialize_history()

            n_steps = int(sim_time / dt)
            states = np.zeros((n_steps + 1, len(state)))
            controls = np.zeros(n_steps)
            states[0] = state

            loop_times = []

            for i in range(n_steps):
                step_start = time.perf_counter()

                # Control computation
                control_output = controller.compute_control(state, controller_state, history)
                if hasattr(control_output, 'force'):
                    control_force = control_output.force
                elif isinstance(control_output, (list, tuple)):
                    control_force = control_output[0] if control_output else 0.0
                else:
                    control_force = float(control_output)

                controls[i] = control_force

                # Dynamics integration (simple Euler)
                state_dot = dynamics.compute_dynamics(state, control_force)
                state = state + dt * state_dot
                states[i + 1] = state

                step_time = time.perf_counter() - step_start
                loop_times.append(step_time)

                # Check for numerical issues
                if not np.all(np.isfinite(state)):
                    interface_errors.append(f"Numerical instability at step {i}")
                    break

                if np.linalg.norm(state) > 100:  # Reasonable bounds check
                    interface_errors.append(f"State diverged at step {i}")
                    break

            # Compute performance metrics
            if not interface_errors:
                performance_metrics = {
                    'simulation_success': True,
                    'avg_step_time': np.mean(loop_times),
                    'max_step_time': np.max(loop_times),
                    'final_state_norm': float(np.linalg.norm(state)),
                    'max_control': float(np.max(np.abs(controls))),
                    'control_energy': float(np.sum(controls**2) * dt),
                    'steps_completed': len(loop_times)
                }

        except Exception as e:
            interface_errors.append(f"Workflow execution failed: {str(e)}")

        execution_time = time.perf_counter() - start_time

        return InterfaceCompatibilityResult(
            component_name="Complete Simulation Workflow",
            controller_type=smc_type.value,
            dynamics_type="SimplifiedDIP",
            success=len(interface_errors) == 0,
            interface_errors=interface_errors,
            parameter_errors=[],
            performance_metrics=performance_metrics,
            execution_time=execution_time
        )

    def generate_compatibility_report(self) -> str:
        """Generate comprehensive compatibility report."""
        report = ["=" * 80]
        report.append("BENCHMARK INTERFACE COMPATIBILITY REPORT")
        report.append("=" * 80)

        # Test all compatibility aspects
        controller_results = self.validate_controller_interfaces()
        parameter_results = self.validate_parameter_bounds()
        workflow_results = self.validate_cross_component_workflows()

        # Summary statistics
        total_tests = sum(len(results) for results in controller_results.values()) + len(workflow_results)
        successful_tests = sum(
            sum(1 for result in results if result.success)
            for results in controller_results.values()
        ) + sum(1 for result in workflow_results.values() if result.success)

        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        report.append(f"Overall Success Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")
        report.append("")

        # Controller Interface Results
        report.append("CONTROLLER INTERFACE COMPATIBILITY")
        report.append("-" * 40)
        for controller_type, results in controller_results.items():
            passed = sum(1 for r in results if r.success)
            total = len(results)
            report.append(f"{controller_type}: {passed}/{total} dynamics models compatible")

            for result in results:
                if not result.success:
                    report.append(f"  ❌ {result.dynamics_type}: {', '.join(result.interface_errors)}")
                else:
                    avg_time = result.performance_metrics.get('avg_control_time', 0) * 1e6
                    report.append(f"  ✅ {result.dynamics_type}: {avg_time:.1f}μs avg control time")

        report.append("")

        # Parameter Bounds Results
        report.append("PARAMETER BOUNDS VALIDATION")
        report.append("-" * 30)
        for controller_type, valid in parameter_results.items():
            status = "✅ PASS" if valid else "❌ FAIL"
            report.append(f"{controller_type}: {status}")

        report.append("")

        # Workflow Results
        report.append("CROSS-COMPONENT WORKFLOW VALIDATION")
        report.append("-" * 40)
        for workflow_name, result in workflow_results.items():
            if result.success:
                steps = result.performance_metrics.get('steps_completed', 0)
                energy = result.performance_metrics.get('control_energy', 0)
                report.append(f"✅ {workflow_name}: {steps} steps, energy={energy:.2f}")
            else:
                report.append(f"❌ {workflow_name}: {', '.join(result.interface_errors)}")

        return "\n".join(report)


# ============================================================================
# PYTEST TEST CASES
# ============================================================================

@pytest.fixture
def interface_validator():
    """Create interface validator for testing."""
    return BenchmarkInterfaceValidator()


class TestBenchmarkInterfaceCompatibility:
    """Test suite for benchmark interface compatibility."""

    def test_all_controller_types_have_compatible_interfaces(self, interface_validator):
        """Test that all SMC controller types have compatible interfaces."""
        results = interface_validator.validate_controller_interfaces()

        # Every controller type should be testable
        assert len(results) == len(SMCType), "Not all controller types were tested"

        # Track failures for detailed reporting
        failures = []
        for controller_type, controller_results in results.items():
            for result in controller_results:
                if not result.success:
                    failures.append(f"{controller_type}-{result.dynamics_type}: {result.interface_errors}")

        success_rate = (
            sum(sum(1 for r in results if r.success) for results in results.values()) /
            sum(len(results) for results in results.values()) * 100
        )

        # Assert 90%+ success rate (Mission 7 target)
        assert success_rate >= 90.0, f"Interface compatibility success rate {success_rate:.1f}% < 90%. Failures: {failures}"

    def test_realistic_parameter_bounds_validation(self, interface_validator):
        """Test that all controllers work with realistic parameter bounds."""
        results = interface_validator.validate_parameter_bounds()

        # All controller types should handle their specified bounds
        failed_controllers = [controller for controller, valid in results.items() if not valid]

        assert len(failed_controllers) == 0, f"Controllers failed bounds validation: {failed_controllers}"
        assert len(results) == len(SMCType), "Not all controller types tested for bounds"

    def test_cross_component_integration_workflows(self, interface_validator):
        """Test that complete workflows work across all components."""
        results = interface_validator.validate_cross_component_workflows()

        # Should have workflow test for each controller type
        expected_workflows = len(SMCType)
        assert len(results) >= expected_workflows, f"Expected {expected_workflows} workflow tests, got {len(results)}"

        # Track workflow failures
        failed_workflows = []
        for workflow_name, result in results.items():
            if not result.success:
                failed_workflows.append(f"{workflow_name}: {result.interface_errors}")

        workflow_success_rate = sum(1 for result in results.values() if result.success) / len(results) * 100

        # Assert 90%+ workflow success rate
        assert workflow_success_rate >= 90.0, f"Workflow success rate {workflow_success_rate:.1f}% < 90%. Failures: {failed_workflows}"

    def test_performance_baseline_establishment(self, interface_validator):
        """Test that performance baselines can be established for all components."""
        results = interface_validator.validate_controller_interfaces()

        performance_data = {}
        for controller_type, controller_results in results.items():
            for result in controller_results:
                if result.success and result.performance_metrics:
                    key = f"{controller_type}_{result.dynamics_type}"
                    performance_data[key] = result.performance_metrics

        # Should have performance data for successful combinations
        assert len(performance_data) > 0, "No performance baseline data collected"

        # Validate that we have essential metrics
        required_metrics = ['avg_control_time', 'avg_dynamics_time']
        for key, metrics in performance_data.items():
            missing_metrics = [m for m in required_metrics if m not in metrics]
            assert len(missing_metrics) == 0, f"{key} missing metrics: {missing_metrics}"

            # Performance sanity checks
            assert 0 < metrics['avg_control_time'] < 1e-3, f"{key} control time unrealistic: {metrics['avg_control_time']}"
            assert 0 < metrics['avg_dynamics_time'] < 1e-3, f"{key} dynamics time unrealistic: {metrics['avg_dynamics_time']}"

    def test_benchmark_framework_integration(self, interface_validator):
        """Test that the benchmark framework integrates properly with real components."""
        # This test validates that we can create a complete benchmarking setup

        # Test SMC factory integration
        for smc_type in SMCType:
            gains = interface_validator._get_realistic_gains(smc_type)
            config = SMCConfig(gains=gains, max_force=100.0, dt=0.01)

            # Should be able to create controller without errors
            controller = SMCFactory.create_controller(smc_type, config)
            assert controller is not None, f"Failed to create {smc_type.value} controller"

            # Controller should have required interface
            required_methods = ['compute_control', 'initialize_state', 'initialize_history']
            for method in required_methods:
                assert hasattr(controller, method), f"{smc_type.value} missing {method}"

        # Test dynamics integration
        dynamics = SimplifiedDIPDynamics(interface_validator.physics_config)
        assert hasattr(dynamics, 'compute_dynamics'), "Dynamics missing compute_dynamics method"
        assert hasattr(dynamics, 'state_dim'), "Dynamics missing state_dim property"

        # Test that dynamics and controllers can work together
        state = np.array([0.1, 0.1, 0.05, 0.0, 0.0, 0.0])
        control_force = 1.0

        state_dot = dynamics.compute_dynamics(state, control_force)
        assert np.all(np.isfinite(state_dot)), "Dynamics produced non-finite derivatives"
        assert len(state_dot) == len(state), "Dynamics state derivative dimension mismatch"

    def test_benchmark_success_rate_target(self, interface_validator):
        """Test that overall benchmark success rate meets the 60% → 90%+ improvement target."""
        # Generate full compatibility report
        report = interface_validator.generate_compatibility_report()

        # Extract success rate from report
        import re
        match = re.search(r'Overall Success Rate: ([\d.]+)%', report)
        assert match, "Could not extract success rate from compatibility report"

        success_rate = float(match.group(1))

        # Mission 7 target: 60% → 90%+ success rate
        assert success_rate >= 90.0, f"Benchmark success rate {success_rate}% did not meet 90%+ target"

        # Print report for debugging
        print("\n" + report)


if __name__ == "__main__":
    # Run standalone validation
    validator = BenchmarkInterfaceValidator()
    report = validator.generate_compatibility_report()
    print(report)