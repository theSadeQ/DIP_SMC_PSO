#==========================================================================================\\\
#==================== benchmarks/benchmark/__init__.py ==================================\\\
#==========================================================================================\\\
"""
Benchmark orchestration package for integration method testing.

This package provides high-level benchmarking classes that orchestrate
comprehensive testing and analysis of numerical integration methods.

Key Components:
* **IntegrationBenchmark**: Main benchmark orchestration class
* **Legacy API Support**: Backward compatibility with original interface
* **Enhanced Analysis**: Advanced comparison and profiling capabilities
"""

from __future__ import annotations

from .integration_benchmark import IntegrationBenchmark

__all__ = [
    'IntegrationBenchmark'
]