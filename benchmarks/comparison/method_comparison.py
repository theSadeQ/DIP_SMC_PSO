#==========================================================================================\\\
#================ benchmarks/comparison/method_comparison.py =============================\\\
#==========================================================================================\\\
"""
Comprehensive comparison framework for numerical integration methods.

This module provides systematic comparison capabilities for evaluating
different integration schemes across multiple criteria:

Comparison Dimensions:
* **Accuracy**: Energy conservation, global error, convergence order
* **Performance**: Execution time, computational efficiency
* **Stability**: Numerical stability limits, step size restrictions
* **Robustness**: Behavior under varying conditions and parameters

The framework supports both open-loop and closed-loop comparisons,
with automatic test case generation and statistical analysis.
"""

from __future__ import annotations

import time
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass, field

from ..integration.numerical_methods import (
    EulerIntegrator, RK4Integrator, AdaptiveRK45Integrator, IntegrationResult
)
from ..analysis.accuracy_metrics import EnergyAnalyzer, ConvergenceAnalyzer, PerformanceProfiler
from src.core.dynamics import DIPDynamics


@dataclass
class ComparisonScenario:
    """Configuration for a single comparison scenario."""
    name: str
    x0: np.ndarray
    sim_time: float
    dt_values: List[float]
    use_controller: bool = False
    controller: Optional[Any] = None
    physics_overrides: Dict[str, float] = field(default_factory=dict)
    description: str = ""


@dataclass
class MethodComparisonResult:
    """Container for comprehensive method comparison results."""
    scenario_name: str
    method_results: Dict[str, Any]
    accuracy_analysis: Dict[str, Any]
    performance_profile: Dict[str, Any]
    rankings: Dict[str, Dict[str, int]]
    summary_statistics: Dict[str, float]


class IntegrationMethodComparator:
    """Comprehensive comparison framework for integration methods."""

    def __init__(self, physics_params: Dict, config_path: str = None):
        """Initialize comparator with physical parameters.

        Parameters
        ----------
        physics_params : dict
            Physical parameters for the system dynamics
        config_path : str, optional
            Path to configuration file for additional settings
        """
        self.physics = physics_params.copy()
        self.dynamics = DIPDynamics(self.physics)

        # Initialize analyzers
        self.energy_analyzer = EnergyAnalyzer(self.physics)
        self.convergence_analyzer = ConvergenceAnalyzer(self.physics)

        # Available integration methods
        self.methods = {
            'Euler': EulerIntegrator(self.dynamics),
            'RK4': RK4Integrator(self.dynamics),
            'RK45': AdaptiveRK45Integrator(self.dynamics)
        }

    def create_standard_scenarios(self) -> List[ComparisonScenario]:
        """Create a set of standard test scenarios for comprehensive comparison.

        Returns
        -------
        list of ComparisonScenario
            Standard test scenarios covering various dynamic conditions
        """
        scenarios = []

        # Scenario 1: Small angle approximation validity
        scenarios.append(ComparisonScenario(
            name="small_angles",
            x0=np.array([0.0, 0.05, 0.05, 0.0, 0.0, 0.0]),  # 2.9° angles
            sim_time=5.0,
            dt_values=[0.1, 0.05, 0.01, 0.005, 0.001],
            description="Small angle regime - tests linearization validity"
        ))

        # Scenario 2: Large angle nonlinear dynamics
        scenarios.append(ComparisonScenario(
            name="large_angles",
            x0=np.array([0.0, 0.5, 0.3, 0.0, 0.0, 0.0]),  # ~28° and 17° angles
            sim_time=3.0,
            dt_values=[0.05, 0.01, 0.005, 0.001],
            description="Large angle regime - tests nonlinear accuracy"
        ))

        # Scenario 3: High energy initial conditions
        scenarios.append(ComparisonScenario(
            name="high_energy",
            x0=np.array([0.0, 0.1, 0.1, 2.0, 3.0, 1.5]),  # High initial velocities
            sim_time=2.0,
            dt_values=[0.01, 0.005, 0.001, 0.0005],
            description="High energy dynamics - tests numerical stability"
        ))

        # Scenario 4: Frictionless conservative system
        conservative_physics = self.physics.copy()
        conservative_physics.update({
            'cart_friction': 0.0,
            'joint1_friction': 0.0,
            'joint2_friction': 0.0
        })
        scenarios.append(ComparisonScenario(
            name="conservative",
            x0=np.array([0.0, 0.2, 0.1, 0.0, 0.0, 0.0]),
            sim_time=10.0,
            dt_values=[0.05, 0.01, 0.005],
            physics_overrides=conservative_physics,
            description="Conservative system - tests energy conservation"
        ))

        # Scenario 5: Stiff dynamics (high friction)
        stiff_physics = self.physics.copy()
        stiff_physics.update({
            'cart_friction': 50.0,
            'joint1_friction': 10.0,
            'joint2_friction': 10.0
        })
        scenarios.append(ComparisonScenario(
            name="stiff_system",
            x0=np.array([0.0, 0.3, 0.2, 0.0, 0.0, 0.0]),
            sim_time=3.0,
            dt_values=[0.01, 0.005, 0.001],
            physics_overrides=stiff_physics,
            description="Stiff system - tests numerical stability limits"
        ))

        return scenarios

    def run_single_comparison(self, scenario: ComparisonScenario) -> MethodComparisonResult:
        """Execute comparison for a single scenario across all methods.

        Parameters
        ----------
        scenario : ComparisonScenario
            Test scenario configuration

        Returns
        -------
        MethodComparisonResult
            Comprehensive comparison results
        """
        # Update physics parameters if overrides specified
        if scenario.physics_overrides:
            temp_physics = self.physics.copy()
            temp_physics.update(scenario.physics_overrides)
            temp_dynamics = DIPDynamics(temp_physics)
            temp_energy_analyzer = EnergyAnalyzer(temp_physics)
        else:
            temp_dynamics = self.dynamics
            temp_energy_analyzer = self.energy_analyzer

        method_results = {}
        accuracy_analyses = {}

        # Test each integration method
        for method_name, integrator in self.methods.items():
            if scenario.physics_overrides:
                # Create temporary integrator with modified physics
                if method_name == 'Euler':
                    integrator = EulerIntegrator(temp_dynamics)
                elif method_name == 'RK4':
                    integrator = RK4Integrator(temp_dynamics)
                elif method_name == 'RK45':
                    integrator = AdaptiveRK45Integrator(temp_dynamics)

            method_results[method_name] = {}
            accuracy_analyses[method_name] = {}

            # Test at different time steps
            for dt in scenario.dt_values:
                try:
                    if method_name == 'RK45':
                        # Adaptive method - use relative tolerance corresponding to dt
                        rtol = dt * 1e-3
                        result = integrator.integrate_open_loop(
                            scenario.x0, scenario.sim_time, rtol=rtol
                        )
                    else:
                        # Fixed-step methods
                        result = integrator.integrate(
                            scenario.x0, scenario.sim_time, dt,
                            controller=scenario.controller
                        )

                    method_results[method_name][dt] = result

                    # Analyze accuracy
                    accuracy = temp_energy_analyzer.analyze_energy_conservation(result)
                    accuracy_analyses[method_name][dt] = accuracy

                except Exception as e:
                    print(f"Warning: {method_name} failed for dt={dt}: {e}")
                    continue

        # Create performance profile
        all_results = [
            result for method_dict in method_results.values()
            for result in method_dict.values()
        ]
        performance_profile = PerformanceProfiler.create_performance_profile(all_results)

        # Rank methods by different criteria
        rankings = self._rank_methods(method_results, accuracy_analyses, performance_profile)

        # Compute summary statistics
        summary_stats = self._compute_summary_statistics(accuracy_analyses, performance_profile)

        return MethodComparisonResult(
            scenario_name=scenario.name,
            method_results=method_results,
            accuracy_analysis=accuracy_analyses,
            performance_profile=performance_profile,
            rankings=rankings,
            summary_statistics=summary_stats
        )

    def run_comprehensive_comparison(self,
                                   scenarios: Optional[List[ComparisonScenario]] = None) -> Dict[str, MethodComparisonResult]:
        """Run comprehensive comparison across multiple scenarios.

        Parameters
        ----------
        scenarios : list of ComparisonScenario, optional
            Test scenarios. If None, uses standard scenarios.

        Returns
        -------
        dict
            Mapping from scenario names to comparison results
        """
        if scenarios is None:
            scenarios = self.create_standard_scenarios()

        results = {}

        for scenario in scenarios:
            print(f"Running comparison for scenario: {scenario.name}")
            try:
                result = self.run_single_comparison(scenario)
                results[scenario.name] = result
            except Exception as e:
                print(f"Warning: Scenario {scenario.name} failed: {e}")
                continue

        return results

    def _rank_methods(self, method_results: Dict, accuracy_analyses: Dict,
                     performance_profile: Dict) -> Dict[str, Dict[str, int]]:
        """Rank methods by different criteria."""
        rankings = {
            'accuracy': {},
            'speed': {},
            'efficiency': {},
            'robustness': {}
        }

        methods = list(method_results.keys())

        # Accuracy ranking (based on minimum energy drift)
        accuracy_scores = {}
        for method in methods:
            min_drift = float('inf')
            for dt, analysis in accuracy_analyses[method].items():
                if analysis.mean_energy_drift < min_drift:
                    min_drift = analysis.mean_energy_drift
            accuracy_scores[method] = min_drift

        accuracy_sorted = sorted(accuracy_scores.items(), key=lambda x: x[1])
        for rank, (method, _) in enumerate(accuracy_sorted, 1):
            rankings['accuracy'][method] = rank

        # Speed ranking (based on execution time)
        speed_scores = {method: profile['execution_time']
                       for method, profile in performance_profile.items()}
        speed_sorted = sorted(speed_scores.items(), key=lambda x: x[1])
        for rank, (method, _) in enumerate(speed_sorted, 1):
            rankings['speed'][method] = rank

        # Efficiency ranking (accuracy per unit time)
        efficiency_scores = {}
        for method in methods:
            best_accuracy = accuracy_scores[method]
            exec_time = performance_profile[method]['execution_time']
            efficiency = 1.0 / (best_accuracy * exec_time) if best_accuracy > 0 else 0
            efficiency_scores[method] = efficiency

        efficiency_sorted = sorted(efficiency_scores.items(), key=lambda x: x[1], reverse=True)
        for rank, (method, _) in enumerate(efficiency_sorted, 1):
            rankings['efficiency'][method] = rank

        # Robustness ranking (success rate across different time steps)
        robustness_scores = {}
        for method in methods:
            total_tests = len(accuracy_analyses[method])
            successful_tests = sum(1 for analysis in accuracy_analyses[method].values()
                                 if not analysis.conservation_violated)
            robustness_scores[method] = successful_tests / total_tests if total_tests > 0 else 0

        robustness_sorted = sorted(robustness_scores.items(), key=lambda x: x[1], reverse=True)
        for rank, (method, _) in enumerate(robustness_sorted, 1):
            rankings['robustness'][method] = rank

        return rankings

    def _compute_summary_statistics(self, accuracy_analyses: Dict,
                                  performance_profile: Dict) -> Dict[str, float]:
        """Compute summary statistics across all methods and conditions."""
        all_drifts = []
        all_times = []

        for method_analyses in accuracy_analyses.values():
            for analysis in method_analyses.values():
                all_drifts.append(analysis.mean_energy_drift)

        for profile in performance_profile.values():
            all_times.append(profile['execution_time'])

        return {
            'mean_energy_drift': np.mean(all_drifts) if all_drifts else 0,
            'std_energy_drift': np.std(all_drifts) if all_drifts else 0,
            'mean_execution_time': np.mean(all_times) if all_times else 0,
            'std_execution_time': np.std(all_times) if all_times else 0,
            'total_comparisons': len(all_drifts),
            'methods_tested': len(performance_profile)
        }

    def generate_comparison_report(self, results: Dict[str, MethodComparisonResult]) -> str:
        """Generate a comprehensive text report of comparison results.

        Parameters
        ----------
        results : dict
            Comparison results from run_comprehensive_comparison

        Returns
        -------
        str
            Formatted comparison report
        """
        report = []
        report.append("=" * 80)
        report.append("NUMERICAL INTEGRATION METHODS COMPARISON REPORT")
        report.append("=" * 80)
        report.append("")

        for scenario_name, result in results.items():
            report.append(f"SCENARIO: {scenario_name.upper()}")
            report.append("-" * 50)

            # Rankings summary
            report.append("Method Rankings:")
            for criterion, rankings in result.rankings.items():
                report.append(f"  {criterion.capitalize()}:")
                for method, rank in sorted(rankings.items(), key=lambda x: x[1]):
                    report.append(f"    {rank}. {method}")

            # Best accuracy
            best_accuracy = min(
                min(analyses.values(), key=lambda x: x.mean_energy_drift)
                for analyses in result.accuracy_analysis.values()
            )
            report.append(f"  Best accuracy: {best_accuracy.method_name} "
                         f"(drift: {best_accuracy.mean_energy_drift:.2e})")

            # Fastest method
            fastest = min(result.performance_profile.items(),
                         key=lambda x: x[1]['execution_time'])
            report.append(f"  Fastest method: {fastest[0]} "
                         f"(time: {fastest[1]['execution_time']:.4f}s)")

            report.append("")

        return "\n".join(report)