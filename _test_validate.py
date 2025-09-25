from benchmarks.benchmark.integration_benchmark import IntegrationBenchmark

bench = IntegrationBenchmark()
res = bench.validate_conservation_laws(method_name='RK4', sim_time=10.0, dt=0.01)
analysis = res['energy_analysis']
print('relative error', analysis.relative_energy_error)
print('max drift', analysis.max_energy_drift)
print('mean drift', analysis.mean_energy_drift)
print('duration used', res['test_duration'])
print('time step used', res['time_step'])
