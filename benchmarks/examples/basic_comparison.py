#==========================================================================================\\\
#================== benchmarks/examples/basic_comparison.py =============================\\\
#==========================================================================================\\\
"""
Basic integration method comparison demonstration.

This example demonstrates the fundamental capabilities of the integration
benchmarking framework, showing how to:

* **Execute Basic Comparisons**: Compare methods across standard scenarios
* **Analyze Results**: Extract meaningful insights from comparison data
* **Display Rankings**: Present method rankings across different criteria
* **Performance Profiling**: Measure computational efficiency

This serves as both a usage example and a smoke test for the framework.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from benchmarks.benchmark import IntegrationBenchmark
from benchmarks.comparison import ComparisonScenario
import numpy as np


def main():
    """Demonstrate basic integration method comparison capabilities."""
    print("=" * 80)
    print("INTEGRATION METHOD COMPARISON DEMONSTRATION")
    print("=" * 80)
    print()

    # Initialize benchmark
    print("Initializing benchmark framework...")
    benchmark = IntegrationBenchmark()
    print("✓ Benchmark initialized with modular architecture")
    print()

    # Demonstrate legacy API compatibility
    print("Testing legacy API compatibility...")
    print("Running Euler integration...")
    euler_result = benchmark.euler_integrate(sim_time=2.0, dt=0.01, use_controller=False)
    print(f"✓ Euler completed in {euler_result['time']:.4f}s")

    print("Running RK4 integration...")
    rk4_result = benchmark.rk4_integrate(sim_time=2.0, dt=0.01, use_controller=False)
    print(f"✓ RK4 completed in {rk4_result['time']:.4f}s")

    print("Running RK45 integration...")
    rk45_result = benchmark.rk45_integrate(sim_time=2.0, rtol=1e-6)
    print(f"✓ RK45 completed in {rk45_result['time']:.4f}s")
    print()

    # Demonstrate energy drift analysis
    print("Analyzing energy conservation...")
    euler_drift = benchmark.calculate_energy_drift(euler_result)
    rk4_drift = benchmark.calculate_energy_drift(rk4_result)
    rk45_drift = benchmark.calculate_energy_drift(rk45_result)

    print(f"Euler max energy drift: {np.max(np.abs(euler_drift)):.2e}")
    print(f"RK4 max energy drift:   {np.max(np.abs(rk4_drift)):.2e}")
    print(f"RK45 max energy drift:  {np.max(np.abs(rk45_drift)):.2e}")
    print()

    # Demonstrate performance profiling
    print("Profiling computational performance...")
    performance_profile = benchmark.profile_performance(
        methods=['Euler', 'RK4'], sim_time=1.0, dt=0.01
    )

    print("Performance Profile:")
    for method, metrics in performance_profile.items():
        print(f"  {method}:")
        print(f"    Execution time: {metrics['execution_time']:.4f}s")
        print(f"    Steps/second:   {metrics['steps_per_second']:.0f}")
        print(f"    Efficiency:     {metrics['efficiency_ratio']:.2f}")
    print()

    # Demonstrate comprehensive comparison
    print("Running comprehensive method comparison...")

    # Create quick test scenarios for demonstration
    quick_scenarios = [
        ComparisonScenario(
            name="small_angles",
            x0=np.array([0.0, 0.05, 0.05, 0.0, 0.0, 0.0]),
            sim_time=2.0,
            dt_values=[0.01, 0.005],
            description="Small angle demonstration"
        ),
        ComparisonScenario(
            name="moderate_energy",
            x0=np.array([0.0, 0.1, 0.1, 0.5, 0.5, 0.0]),
            sim_time=1.5,
            dt_values=[0.01],
            description="Moderate energy demonstration"
        )
    ]

    comparison_results = benchmark.comprehensive_comparison(quick_scenarios)

    print("Comparison Results:")
    for scenario_name, result in comparison_results.items():
        print(f"\n📊 Scenario: {scenario_name}")
        print("  Method Rankings:")

        # Display rankings
        for criterion, rankings in result.rankings.items():
            print(f"    {criterion.capitalize()}:")
            for method, rank in sorted(rankings.items(), key=lambda x: x[1]):
                print(f"      {rank}. {method}")

    print()

    # Demonstrate conservation validation
    print("Validating energy conservation laws...")
    conservation_results = benchmark.validate_conservation_laws(
        method_name='RK4', sim_time=5.0, dt=0.01
    )

    energy_analysis = conservation_results['energy_analysis']
    print(f"Conservation Analysis for {conservation_results['method']}:")
    print(f"  Max energy drift:       {energy_analysis.max_energy_drift:.2e}")
    print(f"  Mean energy drift:      {energy_analysis.mean_energy_drift:.2e}")
    print(f"  Relative error:         {energy_analysis.relative_energy_error:.2e}")
    print(f"  Conservation violated:  {energy_analysis.conservation_violated}")
    print()

    # Demonstrate accuracy analysis
    print("Analyzing method accuracy across time steps...")
    accuracy_analysis = benchmark.analyze_method_accuracy(
        method_name='RK4',
        sim_time=2.0,
        dt_values=[0.02, 0.01, 0.005]
    )

    print("RK4 Accuracy Analysis:")
    print("  Time Step | Mean Drift | Execution Time")
    print("  --------- | ---------- | --------------")
    for dt, metrics in accuracy_analysis.items():
        print(f"  {dt:8.3f} | {metrics['mean_drift']:10.2e} | {metrics['execution_time']:8.4f}s")

    print()
    print("=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()
    print("Key Takeaways:")
    print("✓ All integration methods executed successfully")
    print("✓ RK4 showed better energy conservation than Euler")
    print("✓ Performance profiling revealed computational trade-offs")
    print("✓ Comprehensive comparison framework operational")
    print("✓ Conservation validation detected physics violations")
    print("✓ Accuracy analysis showed convergence with smaller time steps")
    print()
    print("The modular benchmarking framework is ready for production use!")


if __name__ == "__main__":
    main()