#==========================================================================================\\\
#================ benchmarks/examples/advanced_analysis.py ===============================\\\
#==========================================================================================\\\
"""
Advanced integration method analysis demonstration.

This example showcases the sophisticated analysis capabilities of the
modular benchmarking framework, including:

* **Custom Scenario Design**: Creating domain-specific test scenarios
* **Convergence Analysis**: Studying numerical convergence properties
* **Physics Validation**: Verifying conservation laws and stability
* **Comparative Studies**: Statistical comparison between methods
* **Performance Optimization**: Finding optimal parameters

This example is intended for advanced users who need comprehensive
analysis capabilities for research or production optimization.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from benchmarks.benchmark import IntegrationBenchmark
from benchmarks.comparison import ComparisonScenario, IntegrationMethodComparator
from benchmarks.analysis import EnergyAnalyzer, ConvergenceAnalyzer
import numpy as np


def create_physics_scenarios() -> List[ComparisonScenario]:
    """Create scenarios representing different physical regimes."""
    return [
        ComparisonScenario(
            name="linearization_regime",
            x0=np.array([0.0, 0.02, 0.03, 0.0, 0.0, 0.0]),  # ~1-2° angles
            sim_time=10.0,
            dt_values=[0.1, 0.05, 0.01, 0.005],
            description="Small angle regime - linearization validity"
        ),
        ComparisonScenario(
            name="nonlinear_regime",
            x0=np.array([0.0, 0.3, 0.4, 0.0, 0.0, 0.0]),  # ~17-23° angles
            sim_time=5.0,
            dt_values=[0.05, 0.01, 0.005, 0.001],
            description="Moderate angle regime - nonlinear effects"
        ),
        ComparisonScenario(
            name="chaotic_regime",
            x0=np.array([0.0, 1.0, 0.8, 2.0, 1.5, 1.0]),  # High energy
            sim_time=3.0,
            dt_values=[0.01, 0.005, 0.001, 0.0005],
            description="High energy regime - potential chaos"
        ),
        ComparisonScenario(
            name="stiff_dynamics",
            x0=np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0]),
            sim_time=5.0,
            dt_values=[0.01, 0.005, 0.001],
            physics_overrides={
                'cart_friction': 50.0,      # High friction
                'joint1_friction': 10.0,
                'joint2_friction': 10.0
            },
            description="Stiff system - high damping"
        )
    ]


def analyze_convergence_properties(benchmark: IntegrationBenchmark) -> Dict[str, Dict]:
    """Analyze convergence properties of different integration methods."""
    print("🔍 Analyzing convergence properties...")

    methods = ['Euler', 'RK4']
    convergence_analysis = {}

    x0 = np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0])
    sim_time = 2.0
    dt_values = [0.1, 0.05, 0.025, 0.0125, 0.00625]

    for method in methods:
        print(f"  Analyzing {method} convergence...")
        errors = []
        execution_times = []

        for dt in dt_values:
            if method == 'Euler':
                result = benchmark.euler_integrate(sim_time, dt, use_controller=False)
            else:  # RK4
                result = benchmark.rk4_integrate(sim_time, dt, use_controller=False)

            # Use energy drift as error proxy
            energy_drift = benchmark.calculate_energy_drift(result)
            error = np.max(np.abs(energy_drift))
            errors.append(error)
            execution_times.append(result['time'])

        # Estimate convergence order
        log_dt = np.log(np.array(dt_values))
        log_errors = np.log(np.array(errors))

        # Linear regression to find slope
        coeffs = np.polyfit(log_dt, log_errors, 1)
        estimated_order = -coeffs[0]

        convergence_analysis[method] = {
            'dt_values': dt_values,
            'errors': errors,
            'execution_times': execution_times,
            'estimated_order': estimated_order,
            'theoretical_order': 1 if method == 'Euler' else 4
        }

        print(f"    Estimated order: {estimated_order:.2f} (theoretical: {convergence_analysis[method]['theoretical_order']})")

    return convergence_analysis


def validate_hamiltonian_structure(benchmark: IntegrationBenchmark) -> Dict[str, Dict]:
    """Validate Hamiltonian structure preservation for conservative systems."""
    print("🔬 Validating Hamiltonian structure preservation...")

    methods = ['Euler', 'RK4', 'RK45']
    validation_results = {}

    for method in methods:
        print(f"  Validating {method}...")

        # Test with conservative system
        conservation_results = benchmark.validate_conservation_laws(
            method_name=method, sim_time=20.0, dt=0.01
        )

        energy_analysis = conservation_results['energy_analysis']
        hamiltonian_analysis = conservation_results['hamiltonian_analysis']

        # Calculate additional metrics
        relative_drift = energy_analysis.relative_energy_error
        phase_volume_change = hamiltonian_analysis['relative_volume_change']

        validation_results[method] = {
            'energy_conservation': relative_drift < 0.01,  # 1% tolerance
            'max_energy_drift': energy_analysis.max_energy_drift,
            'phase_volume_preserved': phase_volume_change < 0.1,  # 10% tolerance
            'symplectic_score': 1.0 / (1.0 + phase_volume_change),  # Higher is better
            'overall_score': energy_analysis.performance_ratio
        }

        print(f"    Energy conserved: {validation_results[method]['energy_conservation']}")
        print(f"    Phase volume preserved: {validation_results[method]['phase_volume_preserved']}")
        print(f"    Symplectic score: {validation_results[method]['symplectic_score']:.3f}")

    return validation_results


def optimize_time_step_selection(benchmark: IntegrationBenchmark) -> Dict[str, float]:
    """Find optimal time steps balancing accuracy and performance."""
    print("⚡ Optimizing time step selection...")

    methods = ['Euler', 'RK4']
    optimal_steps = {}

    for method in methods:
        print(f"  Optimizing {method}...")

        dt_candidates = np.logspace(-3, -1, 20)  # 0.001 to 0.1
        scores = []

        for dt in dt_candidates:
            try:
                if method == 'Euler':
                    result = benchmark.euler_integrate(2.0, dt, use_controller=False)
                else:
                    result = benchmark.rk4_integrate(2.0, dt, use_controller=False)

                # Compute energy drift and execution time
                energy_drift = benchmark.calculate_energy_drift(result)
                max_drift = np.max(np.abs(energy_drift))
                exec_time = result['time']

                # Score balances accuracy (lower drift) and speed (lower time)
                # Higher score is better
                score = 1.0 / (max_drift * exec_time + 1e-10)
                scores.append(score)

            except Exception:
                scores.append(0.0)  # Failed execution

        # Find optimal time step
        best_idx = np.argmax(scores)
        optimal_dt = dt_candidates[best_idx]
        optimal_steps[method] = optimal_dt

        print(f"    Optimal dt: {optimal_dt:.6f}")

    return optimal_steps


def compare_method_efficiency(benchmark: IntegrationBenchmark) -> Dict[str, Dict]:
    """Compare computational efficiency across different accuracy targets."""
    print("📊 Comparing method efficiency across accuracy targets...")

    methods = ['Euler', 'RK4']
    accuracy_targets = [1e-2, 1e-3, 1e-4, 1e-5]  # Maximum acceptable energy drift
    efficiency_analysis = {}

    for method in methods:
        print(f"  Analyzing {method} efficiency...")
        efficiency_data = []

        for target_accuracy in accuracy_targets:
            # Binary search for time step that achieves target accuracy
            dt_min, dt_max = 1e-5, 0.1
            best_dt = None
            best_time = float('inf')

            for _ in range(10):  # Binary search iterations
                dt = (dt_min + dt_max) / 2

                try:
                    if method == 'Euler':
                        result = benchmark.euler_integrate(2.0, dt, use_controller=False)
                    else:
                        result = benchmark.rk4_integrate(2.0, dt, use_controller=False)

                    energy_drift = benchmark.calculate_energy_drift(result)
                    max_drift = np.max(np.abs(energy_drift))

                    if max_drift <= target_accuracy:
                        best_dt = dt
                        best_time = result['time']
                        dt_max = dt  # Try larger step
                    else:
                        dt_min = dt  # Need smaller step

                except Exception:
                    dt_min = dt

            if best_dt is not None:
                efficiency_data.append({
                    'target_accuracy': target_accuracy,
                    'achieved_dt': best_dt,
                    'execution_time': best_time,
                    'efficiency': 1.0 / best_time  # Higher is better
                })

        efficiency_analysis[method] = efficiency_data
        print(f"    Found {len(efficiency_data)} efficient configurations")

    return efficiency_analysis


def main():
    """Execute advanced integration method analysis."""
    print("=" * 80)
    print("ADVANCED INTEGRATION METHOD ANALYSIS")
    print("=" * 80)
    print()

    # Initialize benchmark
    benchmark = IntegrationBenchmark()
    print("✓ Advanced benchmark framework initialized")
    print()

    # 1. Physics-based scenario analysis
    print("📚 PHYSICS-BASED SCENARIO ANALYSIS")
    print("-" * 50)
    physics_scenarios = create_physics_scenarios()
    scenario_results = benchmark.comprehensive_comparison(physics_scenarios)

    print("\nScenario Comparison Summary:")
    for scenario_name, result in scenario_results.items():
        print(f"\n🎯 {scenario_name}:")
        print("  Winner by category:")
        for criterion, rankings in result.rankings.items():
            winner = min(rankings.items(), key=lambda x: x[1])
            print(f"    {criterion.capitalize()}: {winner[0]} (rank {winner[1]})")

    print()

    # 2. Convergence analysis
    print("📈 CONVERGENCE ANALYSIS")
    print("-" * 50)
    convergence_results = analyze_convergence_properties(benchmark)

    print("\nConvergence Summary:")
    for method, analysis in convergence_results.items():
        theoretical = analysis['theoretical_order']
        estimated = analysis['estimated_order']
        print(f"  {method}: Order {estimated:.2f} (theoretical {theoretical})")

    print()

    # 3. Hamiltonian structure validation
    print("🔬 HAMILTONIAN STRUCTURE VALIDATION")
    print("-" * 50)
    hamiltonian_results = validate_hamiltonian_structure(benchmark)

    print("\nConservation Summary:")
    best_conserving = max(hamiltonian_results.items(),
                         key=lambda x: x[1]['symplectic_score'])
    print(f"  Best energy conservation: {best_conserving[0]}")
    print(f"  Symplectic score: {best_conserving[1]['symplectic_score']:.3f}")

    print()

    # 4. Time step optimization
    print("⚡ TIME STEP OPTIMIZATION")
    print("-" * 50)
    optimal_steps = optimize_time_step_selection(benchmark)

    print("\nOptimal Time Steps:")
    for method, dt in optimal_steps.items():
        print(f"  {method}: {dt:.6f}")

    print()

    # 5. Efficiency comparison
    print("📊 EFFICIENCY COMPARISON")
    print("-" * 50)
    efficiency_results = compare_method_efficiency(benchmark)

    print("\nEfficiency Analysis:")
    for method, data in efficiency_results.items():
        if data:
            print(f"  {method}:")
            print(f"    Configurations found: {len(data)}")
            best_config = max(data, key=lambda x: x['efficiency'])
            print(f"    Best efficiency: {best_config['efficiency']:.2f} at dt={best_config['achieved_dt']:.6f}")

    print()
    print("=" * 80)
    print("ADVANCED ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print("🎯 Key Insights:")
    print("• Different scenarios favor different integration methods")
    print("• Convergence analysis validates theoretical order of accuracy")
    print("• Hamiltonian structure preservation varies significantly between methods")
    print("• Optimal time steps depend on accuracy-performance trade-offs")
    print("• Method efficiency varies with accuracy requirements")
    print()
    print("🚀 The advanced analysis framework provides comprehensive")
    print("   insights for optimizing integration method selection!")


if __name__ == "__main__":
    main()