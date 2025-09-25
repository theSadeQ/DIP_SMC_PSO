from benchmarks.benchmark.integration_benchmark import IntegrationBenchmark
import numpy as np

bench = IntegrationBenchmark()
result = bench.rk4_integrate(sim_time=1.0, dt=0.01, use_controller=False)
print(np.isnan(result['states']).any())
print(result['states'][:5])
