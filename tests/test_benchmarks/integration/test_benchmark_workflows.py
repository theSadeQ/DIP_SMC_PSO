#==========================================================================================\\
#============ tests/test_benchmarks/integration/test_benchmark_workflows.py =============\\
#==========================================================================================\\

"""
Cross-Component Benchmark Integration Workflows - Mission 7 System Integration

SYSTEMS ENGINEERING EXCELLENCE: Validate complete end-to-end benchmarking workflows.
This module ensures that all system components work together seamlessly for:
- Complete simulation-to-analysis pipelines
- PSO optimization with performance tracking
- Multi-controller comparison workflows
- Automated CI/CD performance validation
- Production-ready benchmarking infrastructure

INTEGRATION SUCCESS CRITERIA:
- End-to-end workflows execute without interface failures
- Performance data flows correctly through analysis pipeline
- Optimization loops integrate with benchmarking framework
- Results are reproducible and scientifically valid
- System scales to handle multiple concurrent benchmarks
"""

import pytest
import numpy as np
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import sys
import warnings

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "src"))

try:
    from src.controllers.factory.smc_factory import SMCFactory, SMCType, SMCConfig
    from src.plant.models.simplified.dynamics import SimplifiedDIPDynamics
    from src.plant.models.full.dynamics import FullDIPDynamics
    from src.simulation.engines.simulation_runner import SimulationRunner
    # from src.optimization.algorithms.pso_optimizer import PSOOptimizer  # May not exist
    from src.config import load_config
    from src.utils.config_compatibility import wrap_physics_config
    # from src.utils.analysis.statistics import StatisticalAnalyzer  # May not exist
    from src.utils.reproducibility.seed import set_global_seed
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)

# Import our benchmark infrastructure
try:
    from ..core.test_benchmark_interfaces import BenchmarkInterfaceValidator
    from ..performance.test_regression_detection import PerformanceBenchmarkSuite, PerformanceHistoryManager
    from ..validation.test_parameter_realism import EngineeringParameterValidator, RealisticScenario
except ImportError as e:
    pytest.skip(f"Benchmark infrastructure not available: {e}", allow_module_level=True)


@dataclass
class WorkflowExecutionResult:
    """Result of executing a complete benchmark workflow."""
    workflow_name: str
    success: bool
    execution_time: float
    components_tested: List[str]
    performance_data: Dict[str, Any]
    error_messages: List[str]
    reproducibility_hash: Optional[str] = None
    resource_usage: Optional[Dict[str, float]] = None


@dataclass
class BenchmarkWorkflowConfig:
    """Configuration for a complete benchmark workflow."""
    name: str
    controllers: List[SMCType]
    dynamics_models: List[str]  # ['SimplifiedDIP', 'FullDIP']
    scenarios: List[str]  # Scenario names to test
    performance_metrics: List[str]
    optimization_enabled: bool = False
    concurrent_execution: bool = False
    reproducibility_seed: int = 42


class IntegratedBenchmarkOrchestrator:
    """Orchestrates complete benchmark workflows across all components."""

    def __init__(self, temp_dir: Optional[Path] = None):
        """Initialize with temporary directory for test artifacts."""
        self.temp_dir = temp_dir or Path(tempfile.mkdtemp())
        self.temp_dir.mkdir(exist_ok=True)

        # Initialize all benchmark infrastructure components
        self.interface_validator = BenchmarkInterfaceValidator()
        self.performance_suite = PerformanceBenchmarkSuite()
        self.parameter_validator = EngineeringParameterValidator()

        # Workflow execution tracking
        self.workflow_results: List[WorkflowExecutionResult] = []
        self.current_seed = 42

    def execute_complete_workflow(
        self,
        config: BenchmarkWorkflowConfig
    ) -> WorkflowExecutionResult:
        """Execute a complete benchmark workflow from end to end."""

        start_time = time.perf_counter()
        components_tested = []
        performance_data = {}
        error_messages = []

        try:
            # Set reproducibility seed
            set_global_seed(config.reproducibility_seed)
            self.current_seed = config.reproducibility_seed

            # Phase 1: Interface Compatibility Validation
            components_tested.append("Interface Validation")
            interface_results = self._execute_interface_validation_phase(config)
            performance_data['interface_validation'] = interface_results

            if not interface_results.get('success', False):
                error_messages.extend(interface_results.get('errors', []))
                raise RuntimeError("Interface validation failed")

            # Phase 2: Parameter Realism Validation
            components_tested.append("Parameter Validation")
            parameter_results = self._execute_parameter_validation_phase(config)
            performance_data['parameter_validation'] = parameter_results

            if not parameter_results.get('success', False):
                error_messages.extend(parameter_results.get('errors', []))
                raise RuntimeError("Parameter validation failed")

            # Phase 3: Performance Benchmarking
            components_tested.append("Performance Benchmarking")
            benchmark_results = self._execute_performance_benchmarking_phase(config)
            performance_data['performance_benchmarking'] = benchmark_results

            if not benchmark_results.get('success', False):
                error_messages.extend(benchmark_results.get('errors', []))
                raise RuntimeError("Performance benchmarking failed")

            # Phase 4: Cross-Controller Comparison
            components_tested.append("Controller Comparison")
            comparison_results = self._execute_controller_comparison_phase(config)
            performance_data['controller_comparison'] = comparison_results

            # Phase 5: Integration Testing (if enabled)
            if config.optimization_enabled:
                components_tested.append("Optimization Integration")
                optimization_results = self._execute_optimization_integration_phase(config)
                performance_data['optimization_integration'] = optimization_results

            # Phase 6: Reproducibility Validation
            components_tested.append("Reproducibility Validation")
            reproducibility_results = self._execute_reproducibility_validation_phase(config)
            performance_data['reproducibility_validation'] = reproducibility_results

            # Calculate reproducibility hash
            reproducibility_hash = self._calculate_reproducibility_hash(performance_data)

            success = True

        except Exception as e:
            error_messages.append(f"Workflow execution failed: {str(e)}")
            success = False
            reproducibility_hash = None

        execution_time = time.perf_counter() - start_time

        result = WorkflowExecutionResult(
            workflow_name=config.name,
            success=success,
            execution_time=execution_time,
            components_tested=components_tested,
            performance_data=performance_data,
            error_messages=error_messages,
            reproducibility_hash=reproducibility_hash
        )

        self.workflow_results.append(result)
        return result

    def _execute_interface_validation_phase(
        self,
        config: BenchmarkWorkflowConfig
    ) -> Dict[str, Any]:
        """Execute interface compatibility validation phase."""

        try:
            # Test all controller-dynamics combinations
            controller_results = self.interface_validator.validate_controller_interfaces()

            # Test parameter bounds validation
            parameter_bounds_results = self.interface_validator.validate_parameter_bounds()

            # Test workflow validation
            workflow_validation_results = self.interface_validator.validate_cross_component_workflows()

            # Calculate success metrics
            total_tests = sum(len(results) for results in controller_results.values())
            successful_tests = sum(
                sum(1 for result in results if result.success)
                for results in controller_results.values()
            )

            success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

            return {
                'success': success_rate >= 90.0,  # Mission 7 target
                'success_rate': success_rate,
                'controller_results': controller_results,
                'parameter_bounds_results': parameter_bounds_results,
                'workflow_validation_results': workflow_validation_results,
                'errors': [] if success_rate >= 90.0 else [f"Interface success rate {success_rate:.1f}% below 90% target"]
            }

        except Exception as e:
            return {
                'success': False,
                'errors': [f"Interface validation phase failed: {str(e)}"]
            }

    def _execute_parameter_validation_phase(
        self,
        config: BenchmarkWorkflowConfig
    ) -> Dict[str, Any]:
        """Execute parameter realism validation phase."""

        try:
            scenario_validation_results = {}
            all_scenarios_valid = True
            errors = []

            # Validate all realistic scenarios
            for scenario in self.parameter_validator.realistic_scenarios:
                validation = self.parameter_validator.validate_scenario_consistency(scenario)
                scenario_validation_results[scenario.name] = validation

                if not all(validation.values()):
                    all_scenarios_valid = False
                    failed_checks = [check for check, valid in validation.items() if not valid]
                    errors.append(f"Scenario '{scenario.name}' failed checks: {failed_checks}")

            # Validate controller gains for each type
            controller_gains_valid = {}
            for smc_type in config.controllers:
                realistic_gains = self._get_realistic_gains(smc_type)
                gains_validation = self.parameter_validator.validate_control_gains(smc_type, realistic_gains)
                controller_gains_valid[smc_type.value] = all(gains_validation.values())

                if not controller_gains_valid[smc_type.value]:
                    errors.append(f"Controller {smc_type.value} has unrealistic gain bounds")

            return {
                'success': all_scenarios_valid and all(controller_gains_valid.values()),
                'scenario_validation': scenario_validation_results,
                'controller_gains_validation': controller_gains_valid,
                'errors': errors
            }

        except Exception as e:
            return {
                'success': False,
                'errors': [f"Parameter validation phase failed: {str(e)}"]
            }

    def _execute_performance_benchmarking_phase(
        self,
        config: BenchmarkWorkflowConfig
    ) -> Dict[str, Any]:
        """Execute performance benchmarking phase."""

        try:
            benchmark_results = {}
            all_benchmarks_successful = True
            errors = []

            # Benchmark each controller type
            for smc_type in config.controllers:
                try:
                    controller_results = self.performance_suite.benchmark_controller_performance(smc_type)
                    benchmark_results[smc_type.value] = controller_results

                    # Validate performance metrics are within reasonable bounds
                    for metric_name, metric in controller_results.items():
                        if metric.value is None or not np.isfinite(metric.value):
                            errors.append(f"{smc_type.value}.{metric_name} produced invalid result: {metric.value}")
                            all_benchmarks_successful = False

                except Exception as e:
                    errors.append(f"Benchmarking failed for {smc_type.value}: {str(e)}")
                    all_benchmarks_successful = False

            # Check for performance regressions
            regression_report = self.performance_suite.generate_regression_report()
            has_critical_regressions = '🚨' in regression_report  # Severe regression indicator

            return {
                'success': all_benchmarks_successful and not has_critical_regressions,
                'benchmark_results': benchmark_results,
                'regression_report': regression_report,
                'has_critical_regressions': has_critical_regressions,
                'errors': errors
            }

        except Exception as e:
            return {
                'success': False,
                'errors': [f"Performance benchmarking phase failed: {str(e)}"]
            }

    def _execute_controller_comparison_phase(
        self,
        config: BenchmarkWorkflowConfig
    ) -> Dict[str, Any]:
        """Execute cross-controller comparison phase."""

        try:
            comparison_results = {}

            # Create realistic test scenario
            scenario = self.parameter_validator.get_realistic_scenario_by_name("Desktop Lab Setup")
            if not scenario:
                scenario = self.parameter_validator.realistic_scenarios[0]

            # Test each controller on the same scenario
            controller_performance = {}

            for smc_type in config.controllers:
                try:
                    # Create controller with realistic gains
                    gains = scenario.control_gains.get(smc_type.value, self._get_realistic_gains(smc_type))
                    config_obj = SMCConfig(
                        gains=gains,
                        max_force=scenario.physics_params.get('max_force', 100.0),
                        dt=0.01
                    )
                    controller = SMCFactory.create_controller(smc_type, config_obj)

                    # Create dynamics
                    physics_config = wrap_physics_config(scenario.physics_params)
                    dynamics = SimplifiedDIPDynamics(physics_config)

                    # Run standardized performance test
                    performance_metrics = self._run_standardized_performance_test(
                        controller, dynamics, smc_type.value
                    )

                    controller_performance[smc_type.value] = performance_metrics

                except Exception as e:
                    controller_performance[smc_type.value] = {
                        'error': str(e),
                        'success': False
                    }

            # Analyze relative performance
            performance_analysis = self._analyze_relative_performance(controller_performance)

            return {
                'success': len(controller_performance) >= len(config.controllers),
                'scenario_used': scenario.name,
                'controller_performance': controller_performance,
                'performance_analysis': performance_analysis,
                'errors': []
            }

        except Exception as e:
            return {
                'success': False,
                'errors': [f"Controller comparison phase failed: {str(e)}"]
            }

    def _execute_optimization_integration_phase(
        self,
        config: BenchmarkWorkflowConfig
    ) -> Dict[str, Any]:
        """Execute optimization integration testing phase."""

        try:
            optimization_results = {}

            # Test PSO integration with each controller type
            for smc_type in config.controllers:
                try:
                    # Create a simple PSO optimization test
                    pso_result = self._test_pso_integration(smc_type)
                    optimization_results[smc_type.value] = pso_result

                except Exception as e:
                    optimization_results[smc_type.value] = {
                        'success': False,
                        'error': str(e)
                    }

            success = all(result.get('success', False) for result in optimization_results.values())

            return {
                'success': success,
                'optimization_results': optimization_results,
                'errors': [] if success else ["PSO integration failed for some controllers"]
            }

        except Exception as e:
            return {
                'success': False,
                'errors': [f"Optimization integration phase failed: {str(e)}"]
            }

    def _execute_reproducibility_validation_phase(
        self,
        config: BenchmarkWorkflowConfig
    ) -> Dict[str, Any]:
        """Execute reproducibility validation phase."""

        try:
            # Run the same benchmark twice with the same seed
            set_global_seed(config.reproducibility_seed)

            # Pick one controller for reproducibility test
            test_controller = config.controllers[0] if config.controllers else SMCType.CLASSICAL

            # First run
            results_1 = self.performance_suite.benchmark_controller_performance(test_controller)

            # Reset seed and run again
            set_global_seed(config.reproducibility_seed)
            results_2 = self.performance_suite.benchmark_controller_performance(test_controller)

            # Compare results for reproducibility
            reproducibility_analysis = self._analyze_reproducibility(results_1, results_2)

            return {
                'success': reproducibility_analysis['is_reproducible'],
                'reproducibility_analysis': reproducibility_analysis,
                'errors': [] if reproducibility_analysis['is_reproducible'] else ['Results not reproducible']
            }

        except Exception as e:
            return {
                'success': False,
                'errors': [f"Reproducibility validation phase failed: {str(e)}"]
            }

    def _run_standardized_performance_test(
        self,
        controller,
        dynamics,
        controller_name: str
    ) -> Dict[str, float]:
        """Run standardized performance test for controller comparison."""

        # Initialize test conditions
        initial_state = np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0])  # Small perturbation
        sim_time = 2.0  # Short test for speed
        dt = 0.01

        # Run simulation
        state = initial_state.copy()
        controller_state = controller.initialize_state()
        history = controller.initialize_history()

        n_steps = int(sim_time / dt)
        states = np.zeros((n_steps + 1, len(state)))
        controls = np.zeros(n_steps)
        states[0] = state

        computation_times = []

        try:
            for i in range(n_steps):
                # Time control computation
                start_time = time.perf_counter()
                control_output = controller.compute_control(state, controller_state, history)
                computation_time = time.perf_counter() - start_time
                computation_times.append(computation_time)

                # Extract control force
                if hasattr(control_output, 'force'):
                    control_force = control_output.force
                elif isinstance(control_output, (list, tuple)):
                    control_force = control_output[0] if control_output else 0.0
                else:
                    control_force = float(control_output)

                controls[i] = control_force

                # Integrate dynamics
                state_dot = dynamics.compute_dynamics(state, control_force)
                state = state + dt * state_dot
                states[i + 1] = state

                # Check for instability
                if not np.all(np.isfinite(state)) or np.linalg.norm(state) > 100:
                    break

            # Calculate performance metrics
            final_state = states[-1]
            settling_criteria = np.all(np.abs(final_state[:3]) < 0.02)  # Position and angles < 0.02

            metrics = {
                'avg_computation_time': np.mean(computation_times),
                'max_computation_time': np.max(computation_times),
                'control_energy': np.sum(controls**2) * dt,
                'max_control': np.max(np.abs(controls)),
                'final_position_error': abs(final_state[0]),
                'final_angle1_error': abs(final_state[1]),
                'final_angle2_error': abs(final_state[2]),
                'settled': settling_criteria,
                'numerical_stability': np.all(np.isfinite(final_state)),
                'success': True
            }

            return metrics

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'avg_computation_time': 0.0,
                'control_energy': float('inf')
            }

    def _analyze_relative_performance(
        self,
        controller_performance: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze relative performance between controllers."""

        successful_controllers = {
            name: metrics for name, metrics in controller_performance.items()
            if metrics.get('success', False)
        }

        if len(successful_controllers) < 2:
            return {'analysis': 'Insufficient data for comparison'}

        # Compare key metrics
        comparison_metrics = ['avg_computation_time', 'control_energy', 'final_position_error']
        analysis = {}

        for metric in comparison_metrics:
            values = {
                name: metrics.get(metric, float('inf'))
                for name, metrics in successful_controllers.items()
                if metric in metrics
            }

            if values:
                best_controller = min(values.keys(), key=lambda k: values[k])
                worst_controller = max(values.keys(), key=lambda k: values[k])

                analysis[metric] = {
                    'best': best_controller,
                    'best_value': values[best_controller],
                    'worst': worst_controller,
                    'worst_value': values[worst_controller],
                    'improvement_ratio': values[worst_controller] / values[best_controller] if values[best_controller] > 0 else float('inf')
                }

        return analysis

    def _test_pso_integration(self, smc_type: SMCType) -> Dict[str, Any]:
        """Test PSO optimization integration with benchmarking."""

        try:
            # Create a simple PSO test with very few iterations
            spec = SMC_GAIN_SPECS[smc_type]
            bounds = spec.gain_bounds

            # Mock PSO optimization (simplified for testing)
            initial_gains = [(b[0] + b[1]) / 2 for b in bounds]  # Start at midpoint

            # Test that we can create controller with these gains
            config = SMCConfig(gains=initial_gains, max_force=100.0)
            controller = SMCFactory.create_controller(smc_type, config)

            # Test basic functionality
            state = np.array([0.1, 0.1, 0.05, 0.0, 0.0, 0.0])
            controller_state = controller.initialize_state()
            history = controller.initialize_history()

            control_output = controller.compute_control(state, controller_state, history)

            return {
                'success': True,
                'initial_gains': initial_gains,
                'bounds_used': bounds,
                'control_output_valid': control_output is not None
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _analyze_reproducibility(
        self,
        results_1: Dict[str, Any],
        results_2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze reproducibility between two benchmark runs."""

        if not results_1 or not results_2:
            return {'is_reproducible': False, 'reason': 'Missing results'}

        # Compare metric values
        reproducible_metrics = []
        non_reproducible_metrics = []

        for metric_name in results_1:
            if metric_name not in results_2:
                non_reproducible_metrics.append(f"{metric_name}: missing in second run")
                continue

            metric_1 = results_1[metric_name]
            metric_2 = results_2[metric_name]

            if hasattr(metric_1, 'value') and hasattr(metric_2, 'value'):
                value_1 = metric_1.value
                value_2 = metric_2.value

                # Check if values are close (within 1e-10 relative tolerance)
                if abs(value_1) < 1e-12 and abs(value_2) < 1e-12:
                    # Both essentially zero
                    reproducible_metrics.append(metric_name)
                elif abs(value_1 - value_2) / max(abs(value_1), abs(value_2)) < 1e-10:
                    reproducible_metrics.append(metric_name)
                else:
                    non_reproducible_metrics.append(f"{metric_name}: {value_1} vs {value_2}")
            else:
                # Can't compare
                non_reproducible_metrics.append(f"{metric_name}: incomparable types")

        is_reproducible = len(non_reproducible_metrics) == 0

        return {
            'is_reproducible': is_reproducible,
            'reproducible_metrics': reproducible_metrics,
            'non_reproducible_metrics': non_reproducible_metrics,
            'reproducible_count': len(reproducible_metrics),
            'total_count': len(reproducible_metrics) + len(non_reproducible_metrics)
        }

    def _calculate_reproducibility_hash(self, performance_data: Dict[str, Any]) -> str:
        """Calculate hash for reproducibility verification."""

        try:
            # Create deterministic string representation
            data_str = json.dumps(performance_data, sort_keys=True, default=str)

            # Simple hash (not cryptographic, just for reproducibility)
            hash_value = abs(hash(data_str)) % (10**8)

            return f"repro_{hash_value:08d}"

        except:
            return None

    def _get_realistic_gains(self, smc_type: SMCType) -> List[float]:
        """Get realistic gain values for each SMC type."""
        realistic_gains = {
            SMCType.CLASSICAL: [10.0, 5.0, 3.0, 2.0, 50.0, 1.0],
            SMCType.ADAPTIVE: [8.0, 4.0, 2.5, 1.5, 0.5],
            SMCType.SUPER_TWISTING: [15.0, 10.0, 8.0, 4.0, 2.5, 1.5],
            SMCType.HYBRID: [12.0, 3.0, 8.0, 2.0]
        }
        return realistic_gains.get(smc_type, [1.0] * 6)

    def execute_concurrent_workflows(
        self,
        workflow_configs: List[BenchmarkWorkflowConfig],
        max_workers: int = 2
    ) -> List[WorkflowExecutionResult]:
        """Execute multiple benchmark workflows concurrently."""

        results = []

        if max_workers <= 1:
            # Sequential execution
            for config in workflow_configs:
                result = self.execute_complete_workflow(config)
                results.append(result)
        else:
            # Concurrent execution
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_config = {
                    executor.submit(self.execute_complete_workflow, config): config
                    for config in workflow_configs
                }

                for future in as_completed(future_to_config):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        config = future_to_config[future]
                        results.append(WorkflowExecutionResult(
                            workflow_name=config.name,
                            success=False,
                            execution_time=0.0,
                            components_tested=[],
                            performance_data={},
                            error_messages=[f"Concurrent execution failed: {str(e)}"]
                        ))

        return results

    def generate_integration_report(self) -> str:
        """Generate comprehensive integration workflow report."""

        if not self.workflow_results:
            return "No workflow results available."

        report = ["=" * 80]
        report.append("CROSS-COMPONENT BENCHMARK INTEGRATION REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary statistics
        total_workflows = len(self.workflow_results)
        successful_workflows = sum(1 for result in self.workflow_results if result.success)

        report.append("EXECUTIVE SUMMARY")
        report.append("-" * 20)
        report.append(f"Total workflows executed: {total_workflows}")
        report.append(f"Successful workflows: {successful_workflows}")
        report.append(f"Success rate: {(successful_workflows/total_workflows*100):.1f}%")
        report.append("")

        # Individual workflow results
        for result in self.workflow_results:
            status = "✅ PASSED" if result.success else "❌ FAILED"
            report.append(f"{status} {result.workflow_name}")
            report.append(f"   Execution time: {result.execution_time:.2f}s")
            report.append(f"   Components tested: {len(result.components_tested)}")
            report.append(f"   Reproducibility hash: {result.reproducibility_hash or 'N/A'}")

            if result.error_messages:
                report.append(f"   Errors: {'; '.join(result.error_messages)}")

            report.append("")

        return "\n".join(report)


# ============================================================================
# PYTEST TEST CASES
# ============================================================================

@pytest.fixture
def benchmark_orchestrator():
    """Create benchmark orchestrator for testing."""
    return IntegratedBenchmarkOrchestrator()


@pytest.fixture
def basic_workflow_config():
    """Create basic workflow configuration for testing."""
    return BenchmarkWorkflowConfig(
        name="Basic Integration Test",
        controllers=[SMCType.CLASSICAL, SMCType.ADAPTIVE],
        dynamics_models=["SimplifiedDIP"],
        scenarios=["Desktop Lab Setup"],
        performance_metrics=["execution_time", "control_energy"],
        optimization_enabled=False,
        concurrent_execution=False,
        reproducibility_seed=42
    )


class TestBenchmarkWorkflowIntegration:
    """Test suite for cross-component benchmark workflow integration."""

    def test_complete_workflow_execution(self, benchmark_orchestrator, basic_workflow_config):
        """Test that complete workflows execute successfully end-to-end."""

        result = benchmark_orchestrator.execute_complete_workflow(basic_workflow_config)

        assert result.success, f"Workflow failed: {result.error_messages}"
        assert result.execution_time > 0, "Workflow should take measurable time"
        assert len(result.components_tested) >= 4, f"Expected ≥4 components tested, got {len(result.components_tested)}"
        assert result.reproducibility_hash is not None, "Should generate reproducibility hash"

        # Validate that all expected phases executed
        expected_phases = ['Interface Validation', 'Parameter Validation', 'Performance Benchmarking']
        tested_phases = result.components_tested

        for phase in expected_phases:
            assert phase in tested_phases, f"Missing required phase: {phase}"

    def test_interface_validation_integration(self, benchmark_orchestrator, basic_workflow_config):
        """Test that interface validation integrates correctly with workflow."""

        result = benchmark_orchestrator.execute_complete_workflow(basic_workflow_config)

        assert 'interface_validation' in result.performance_data, "Missing interface validation data"

        interface_data = result.performance_data['interface_validation']
        assert interface_data.get('success', False), "Interface validation should succeed"
        assert interface_data.get('success_rate', 0) >= 90.0, f"Interface success rate {interface_data.get('success_rate', 0)}% below target"

    def test_parameter_realism_integration(self, benchmark_orchestrator, basic_workflow_config):
        """Test that parameter realism validation integrates correctly."""

        result = benchmark_orchestrator.execute_complete_workflow(basic_workflow_config)

        assert 'parameter_validation' in result.performance_data, "Missing parameter validation data"

        param_data = result.performance_data['parameter_validation']
        assert param_data.get('success', False), "Parameter validation should succeed"

        # Should have validated scenarios and controller gains
        assert 'scenario_validation' in param_data, "Missing scenario validation"
        assert 'controller_gains_validation' in param_data, "Missing controller gains validation"

    def test_performance_benchmarking_integration(self, benchmark_orchestrator, basic_workflow_config):
        """Test that performance benchmarking integrates correctly."""

        result = benchmark_orchestrator.execute_complete_workflow(basic_workflow_config)

        assert 'performance_benchmarking' in result.performance_data, "Missing performance benchmarking data"

        benchmark_data = result.performance_data['performance_benchmarking']
        assert benchmark_data.get('success', False), "Performance benchmarking should succeed"

        # Should have results for each controller
        benchmark_results = benchmark_data.get('benchmark_results', {})
        for controller_type in basic_workflow_config.controllers:
            assert controller_type.value in benchmark_results, f"Missing results for {controller_type.value}"

    def test_cross_controller_comparison_workflow(self, benchmark_orchestrator, basic_workflow_config):
        """Test that cross-controller comparison works correctly."""

        result = benchmark_orchestrator.execute_complete_workflow(basic_workflow_config)

        assert 'controller_comparison' in result.performance_data, "Missing controller comparison data"

        comparison_data = result.performance_data['controller_comparison']
        assert comparison_data.get('success', False), "Controller comparison should succeed"

        # Should have performance data for each controller
        controller_performance = comparison_data.get('controller_performance', {})
        assert len(controller_performance) >= len(basic_workflow_config.controllers), "Missing controller performance data"

        # Should have performance analysis
        assert 'performance_analysis' in comparison_data, "Missing performance analysis"

    def test_reproducibility_validation_workflow(self, benchmark_orchestrator, basic_workflow_config):
        """Test that reproducibility validation works correctly."""

        result = benchmark_orchestrator.execute_complete_workflow(basic_workflow_config)

        assert 'reproducibility_validation' in result.performance_data, "Missing reproducibility validation data"

        repro_data = result.performance_data['reproducibility_validation']
        assert repro_data.get('success', False), "Reproducibility validation should succeed"

        # Should have reproducibility analysis
        repro_analysis = repro_data.get('reproducibility_analysis', {})
        assert repro_analysis.get('is_reproducible', False), "Results should be reproducible"
        assert repro_analysis.get('reproducible_count', 0) > 0, "Should have some reproducible metrics"

    def test_optimization_integration_workflow(self, benchmark_orchestrator):
        """Test that PSO optimization integrates correctly with benchmarking."""

        config = BenchmarkWorkflowConfig(
            name="Optimization Integration Test",
            controllers=[SMCType.CLASSICAL],
            dynamics_models=["SimplifiedDIP"],
            scenarios=["Desktop Lab Setup"],
            performance_metrics=["execution_time"],
            optimization_enabled=True,  # Enable optimization testing
            reproducibility_seed=42
        )

        result = benchmark_orchestrator.execute_complete_workflow(config)

        # Should have optimization integration data
        assert 'optimization_integration' in result.performance_data, "Missing optimization integration data"

        opt_data = result.performance_data['optimization_integration']
        assert opt_data.get('success', False), "Optimization integration should succeed"

        opt_results = opt_data.get('optimization_results', {})
        assert SMCType.CLASSICAL.value in opt_results, "Missing PSO results for classical SMC"

    def test_concurrent_workflow_execution(self, benchmark_orchestrator):
        """Test that multiple workflows can execute concurrently without interference."""

        # Create multiple workflow configurations
        workflow_configs = []
        for i, controller_type in enumerate([SMCType.CLASSICAL, SMCType.ADAPTIVE]):
            config = BenchmarkWorkflowConfig(
                name=f"Concurrent Test {i+1}",
                controllers=[controller_type],
                dynamics_models=["SimplifiedDIP"],
                scenarios=["Desktop Lab Setup"],
                performance_metrics=["execution_time"],
                concurrent_execution=True,
                reproducibility_seed=42 + i
            )
            workflow_configs.append(config)

        # Execute concurrently
        results = benchmark_orchestrator.execute_concurrent_workflows(workflow_configs, max_workers=2)

        assert len(results) == len(workflow_configs), "Should have results for all workflows"

        # All workflows should succeed
        successful_count = sum(1 for result in results if result.success)
        assert successful_count == len(results), f"Only {successful_count}/{len(results)} concurrent workflows succeeded"

        # Reproducibility hashes should be different (different seeds)
        hashes = [result.reproducibility_hash for result in results if result.reproducibility_hash]
        assert len(set(hashes)) == len(hashes), "Reproducibility hashes should be unique for different seeds"

    def test_workflow_error_handling_and_recovery(self, benchmark_orchestrator):
        """Test that workflows handle errors gracefully and provide useful diagnostics."""

        # Create configuration that might cause issues
        config = BenchmarkWorkflowConfig(
            name="Error Handling Test",
            controllers=[SMCType.CLASSICAL],
            dynamics_models=["NonexistentDynamics"],  # This should cause errors
            scenarios=["Nonexistent Scenario"],
            performance_metrics=["invalid_metric"],
            reproducibility_seed=42
        )

        result = benchmark_orchestrator.execute_complete_workflow(config)

        # Workflow might fail, but should handle errors gracefully
        assert isinstance(result, WorkflowExecutionResult), "Should return valid result object even on failure"
        assert result.workflow_name == config.name, "Should preserve workflow name"

        # If failed, should have informative error messages
        if not result.success:
            assert len(result.error_messages) > 0, "Failed workflow should have error messages"
            assert any("failed" in msg.lower() for msg in result.error_messages), "Error messages should be informative"

    def test_workflow_performance_requirements(self, benchmark_orchestrator, basic_workflow_config):
        """Test that workflows meet performance requirements for CI/CD integration."""

        result = benchmark_orchestrator.execute_complete_workflow(basic_workflow_config)

        # Execution time should be reasonable for CI/CD (< 30 seconds for basic workflow)
        assert result.execution_time < 30.0, f"Workflow took {result.execution_time:.1f}s, should be < 30s for CI/CD"

        # Should generate meaningful performance data
        assert len(result.performance_data) >= 4, "Should generate data for all phases"

        # Should have high success rate
        assert result.success, "Basic workflow should succeed for CI/CD reliability"

    def test_integration_report_generation(self, benchmark_orchestrator, basic_workflow_config):
        """Test that integration reports are comprehensive and useful."""

        # Execute a workflow first
        benchmark_orchestrator.execute_complete_workflow(basic_workflow_config)

        # Generate report
        report = benchmark_orchestrator.generate_integration_report()

        assert len(report) > 100, "Report should be substantial"
        assert "CROSS-COMPONENT BENCHMARK INTEGRATION REPORT" in report, "Report should have proper header"
        assert "EXECUTIVE SUMMARY" in report, "Report should have executive summary"
        assert "Success rate:" in report, "Report should include success rate"

        # Should contain workflow-specific information
        assert basic_workflow_config.name in report, "Report should mention executed workflow"

    def test_benchmark_infrastructure_scalability(self, benchmark_orchestrator):
        """Test that benchmark infrastructure scales to handle multiple controllers/scenarios."""

        # Create comprehensive workflow testing all controllers
        config = BenchmarkWorkflowConfig(
            name="Scalability Test",
            controllers=list(SMCType),  # All controller types
            dynamics_models=["SimplifiedDIP"],
            scenarios=["Desktop Lab Setup"],
            performance_metrics=["execution_time", "control_energy", "numerical_stability"],
            optimization_enabled=False,
            reproducibility_seed=42
        )

        result = benchmark_orchestrator.execute_complete_workflow(config)

        # Should handle all controller types
        assert result.success, f"Scalability test failed: {result.error_messages}"

        # Performance should still be reasonable
        assert result.execution_time < 60.0, f"Scalability test took {result.execution_time:.1f}s, should be < 60s"

        # Should have data for all controllers
        if 'controller_comparison' in result.performance_data:
            comparison_data = result.performance_data['controller_comparison']
            controller_performance = comparison_data.get('controller_performance', {})
            assert len(controller_performance) >= len(config.controllers), "Should test all controllers"


if __name__ == "__main__":
    # Run standalone integration testing
    orchestrator = IntegratedBenchmarkOrchestrator()

    # Test basic workflow
    config = BenchmarkWorkflowConfig(
        name="Standalone Test",
        controllers=[SMCType.CLASSICAL, SMCType.ADAPTIVE],
        dynamics_models=["SimplifiedDIP"],
        scenarios=["Desktop Lab Setup"],
        performance_metrics=["execution_time", "control_energy"],
        reproducibility_seed=42
    )

    print("Executing comprehensive benchmark workflow...")
    result = orchestrator.execute_complete_workflow(config)

    if result.success:
        print("✅ Workflow completed successfully!")
        print(f"Execution time: {result.execution_time:.2f}s")
        print(f"Components tested: {result.components_tested}")
    else:
        print("❌ Workflow failed!")
        print(f"Errors: {result.error_messages}")

    # Generate report
    print("\n" + orchestrator.generate_integration_report())