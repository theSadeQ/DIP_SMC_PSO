from benchmarks.benchmark.integration_benchmark import IntegrationBenchmark
import numpy as np

bench = IntegrationBenchmark()
res = bench.rk4_integrate(sim_time=1.0, dt=0.01, use_controller=False)
states = res['states']
nan_index = np.argwhere(np.isnan(states))
print(nan_index[:5])
print(nan_index[-5:])
