from benchmarks.benchmark.integration_benchmark import IntegrationBenchmark

bench = IntegrationBenchmark()
res = bench.rk4_integrate(sim_time=10.0, dt=0.01, use_controller=False)
energy_analysis = bench.energy_analyzer.analyze_energy_conservation(res)
print('initial energy', bench.energy_analyzer.compute_total_energy(res['states'][0]))
print('max drift', energy_analysis.max_energy_drift)
print('relative error', energy_analysis.relative_energy_error)
