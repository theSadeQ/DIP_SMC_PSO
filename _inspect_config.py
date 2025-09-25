from benchmarks.benchmark.integration_benchmark import IntegrationBenchmark
bench = IntegrationBenchmark()
print(type(bench.dynamics.config))
print(hasattr(bench.dynamics.config, 'cart_friction'))
print(bench.dynamics.config.cart_friction)
print(repr(bench.dynamics.config))
