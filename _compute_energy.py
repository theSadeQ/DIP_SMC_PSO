from benchmarks.benchmark.integration_benchmark import IntegrationBenchmark
bench = IntegrationBenchmark()
result = bench.rk4_integrate(sim_time=10.0, dt=0.01, use_controller=False)
energy_analysis = bench.energy_analyzer.analyze_energy_conservation(result)
print('max_drift', energy_analysis.max_energy_drift)
print('mean_drift', energy_analysis.mean_energy_drift)
print('relative_error', energy_analysis.relative_energy_error)
