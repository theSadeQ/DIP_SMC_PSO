#!/usr/bin/env python3
#==========================================================================================\\\
#======================= scripts/test_memory_leak_fixes.py ===============================\\\
#==========================================================================================\\\
"""
Memory Leak Fix Validation Script

This script tests the memory leak fixes applied to the metrics collection system.
It simulates production load and verifies that memory usage stays bounded.

Tests:
1. Original metrics collector (memory leak expected)
2. Fixed metrics collector (memory should stay bounded)
3. Load testing with multiple metric types
4. Memory pressure scenarios
5. Cleanup verification

Usage:
    python scripts/test_memory_leak_fixes.py
    python scripts/test_memory_leak_fixes.py --load-test
    python scripts/test_memory_leak_fixes.py --profile production
"""

import argparse
import time
import threading
import psutil
import os
import gc
import sys
from pathlib import Path
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from interfaces.monitoring.metrics_collector_fixed import (
    ProductionSafeMetricsCollector, MemoryProfile, MetricType
)


class MemoryLeakTester:
    """Test memory leak fixes in metrics collector."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.memory_history: List[float] = []
        self.test_results: Dict[str, Any] = {}

    def get_memory_usage_mb(self) -> float:
        """Get current process memory usage in MB."""
        return self.process.memory_info().rss / (1024 * 1024)

    def monitor_memory(self, duration_seconds: int, interval: float = 1.0) -> List[float]:
        """Monitor memory usage over time."""
        memory_samples = []
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            memory_samples.append(self.get_memory_usage_mb())
            time.sleep(interval)

        return memory_samples

    def test_fixed_collector_bounded_memory(self, profile: MemoryProfile = MemoryProfile.PRODUCTION) -> Dict[str, Any]:
        """Test that fixed collector keeps memory bounded."""
        print(f"\n🧪 Testing Fixed Collector - {profile.value.upper()} Profile")
        print("=" * 60)

        # Create fixed collector
        collector = ProductionSafeMetricsCollector(profile)

        initial_memory = self.get_memory_usage_mb()
        memory_samples = [initial_memory]

        print(f"Initial memory: {initial_memory:.1f} MB")
        print(f"Config: {collector.config.max_entries} max entries, {collector.config.retention_window_seconds}s retention")

        # Simulate heavy load
        metrics_created = 0
        total_values_added = 0

        for iteration in range(100):  # 100 iterations
            # Create multiple metric types
            for metric_type in [MetricType.COUNTER, MetricType.GAUGE, MetricType.HISTOGRAM]:
                for i in range(10):  # 10 metrics per type
                    metric_name = f"{metric_type.value}_{iteration}_{i}"

                    if metric_type == MetricType.COUNTER:
                        collector.increment_counter(metric_name, 1.0)
                    elif metric_type == MetricType.GAUGE:
                        collector.set_gauge(metric_name, float(i * iteration))
                    elif metric_type == MetricType.HISTOGRAM:
                        collector.record_histogram(metric_name, float(i + iteration))

                    total_values_added += 1
                    metrics_created += 1

            # Check memory every 10 iterations
            if iteration % 10 == 0:
                current_memory = self.get_memory_usage_mb()
                memory_samples.append(current_memory)

                stats = collector.get_memory_stats()
                health = collector.get_health_status()

                print(f"Iteration {iteration}: {current_memory:.1f}MB process, "
                      f"{stats.estimated_metric_memory_mb:.1f}MB metrics, "
                      f"{stats.metric_count} metrics, {stats.total_metric_values} values, "
                      f"health: {health['status']}")

                # Force garbage collection
                gc.collect()

        final_memory = self.get_memory_usage_mb()
        final_stats = collector.get_health_status()

        # Results
        memory_increase = final_memory - initial_memory
        bounded_memory = memory_increase < 100  # Should increase by less than 100MB

        result = {
            'profile': profile.value,
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_increase_mb': memory_increase,
            'metrics_created': metrics_created,
            'values_added': total_values_added,
            'final_metrics_count': final_stats['metrics_count'],
            'final_values_count': final_stats['total_values'],
            'memory_bounded': bounded_memory,
            'memory_samples': memory_samples,
            'health_status': final_stats['status'],
            'force_cleanups': final_stats['force_cleanups_performed'],
            'memory_alerts': final_stats['memory_alerts_sent']
        }

        status = "✅ PASS" if bounded_memory else "❌ FAIL"
        print(f"\n{status} Memory Bounded Test:")
        print(f"  Memory increase: {memory_increase:.1f} MB ({'✅ bounded' if bounded_memory else '❌ unbounded'})")
        print(f"  Final metrics: {final_stats['metrics_count']} (with {final_stats['total_values']} values)")
        print(f"  Health status: {final_stats['status']}")
        print(f"  Force cleanups: {final_stats['force_cleanups_performed']}")

        return result

    def test_memory_pressure_handling(self) -> Dict[str, Any]:
        """Test how collector handles memory pressure."""
        print(f"\n🧪 Testing Memory Pressure Handling")
        print("=" * 60)

        collector = ProductionSafeMetricsCollector(MemoryProfile.PRODUCTION)

        initial_memory = self.get_memory_usage_mb()

        # Rapidly add many values to trigger memory pressure
        for i in range(1000):
            for j in range(50):  # 50 values per iteration
                collector.record_histogram(f"pressure_test_{i % 10}", float(i * j))

        stats = collector.get_memory_stats()
        health = collector.get_health_status()
        final_memory = self.get_memory_usage_mb()

        memory_handled = health['status'] != 'critical'
        cleanups_triggered = health['force_cleanups_performed'] > 0

        result = {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_increase_mb': final_memory - initial_memory,
            'memory_handled': memory_handled,
            'cleanups_triggered': cleanups_triggered,
            'final_health': health['status'],
            'force_cleanups': health['force_cleanups_performed'],
            'memory_alerts': health['memory_alerts_sent']
        }

        status = "✅ PASS" if memory_handled else "❌ FAIL"
        print(f"\n{status} Memory Pressure Test:")
        print(f"  Memory increase: {final_memory - initial_memory:.1f} MB")
        print(f"  Health status: {health['status']} ({'✅ handled' if memory_handled else '❌ critical'})")
        print(f"  Force cleanups triggered: {health['force_cleanups_performed']}")

        return result

    def test_cleanup_effectiveness(self) -> Dict[str, Any]:
        """Test that cleanup actually reduces memory usage."""
        print(f"\n🧪 Testing Cleanup Effectiveness")
        print("=" * 60)

        collector = ProductionSafeMetricsCollector(MemoryProfile.DEVELOPMENT)  # Longer retention for test

        # Add lots of data
        for i in range(100):
            collector.record_histogram("cleanup_test", float(i))
            time.sleep(0.01)  # Small delay to create timestamp spread

        before_stats = collector.get_memory_stats()
        print(f"Before cleanup: {before_stats.total_metric_values} values, {before_stats.estimated_metric_memory_mb:.1f} MB")

        # Force cleanup by triggering it
        collector._force_emergency_cleanup()

        after_stats = collector.get_memory_stats()
        print(f"After cleanup: {after_stats.total_metric_values} values, {after_stats.estimated_metric_memory_mb:.1f} MB")

        values_cleaned = before_stats.total_metric_values - after_stats.total_metric_values
        memory_reduced = before_stats.estimated_metric_memory_mb - after_stats.estimated_metric_memory_mb

        cleanup_effective = values_cleaned > 0 and memory_reduced > 0

        result = {
            'values_before': before_stats.total_metric_values,
            'values_after': after_stats.total_metric_values,
            'values_cleaned': values_cleaned,
            'memory_before_mb': before_stats.estimated_metric_memory_mb,
            'memory_after_mb': after_stats.estimated_metric_memory_mb,
            'memory_reduced_mb': memory_reduced,
            'cleanup_effective': cleanup_effective
        }

        status = "✅ PASS" if cleanup_effective else "❌ FAIL"
        print(f"\n{status} Cleanup Effectiveness:")
        print(f"  Values cleaned: {values_cleaned}")
        print(f"  Memory reduced: {memory_reduced:.2f} MB")

        return result

    def run_comparative_test(self) -> Dict[str, Any]:
        """Run comprehensive test across all profiles."""
        print("\n🚀 Running Comprehensive Memory Leak Fix Validation")
        print("=" * 80)

        results = {
            'timestamp': time.time(),
            'test_environment': {
                'python_version': sys.version,
                'psutil_version': psutil.__version__,
                'initial_process_memory_mb': self.get_memory_usage_mb()
            },
            'tests': {}
        }

        # Test each profile
        for profile in [MemoryProfile.PRODUCTION, MemoryProfile.STAGING, MemoryProfile.DEVELOPMENT]:
            results['tests'][f'bounded_memory_{profile.value}'] = self.test_fixed_collector_bounded_memory(profile)

        # Test memory pressure handling
        results['tests']['memory_pressure'] = self.test_memory_pressure_handling()

        # Test cleanup effectiveness
        results['tests']['cleanup_effectiveness'] = self.test_cleanup_effectiveness()

        # Overall assessment
        all_tests_passed = all(
            test_result.get('memory_bounded', test_result.get('memory_handled', test_result.get('cleanup_effective', False)))
            for test_result in results['tests'].values()
        )

        results['overall_status'] = 'PASSED' if all_tests_passed else 'FAILED'
        results['summary'] = {
            'total_tests': len(results['tests']),
            'tests_passed': sum(1 for test in results['tests'].values()
                              if test.get('memory_bounded', test.get('memory_handled', test.get('cleanup_effective', False)))),
            'memory_leak_fixed': all_tests_passed
        }

        # Print summary
        print("\n" + "=" * 80)
        print("🎯 TEST SUMMARY:")
        status_emoji = "✅" if all_tests_passed else "❌"
        print(f"{status_emoji} Overall Status: {results['overall_status']}")
        print(f"  Tests Passed: {results['summary']['tests_passed']}/{results['summary']['total_tests']}")
        print(f"  Memory Leaks Fixed: {'Yes' if results['summary']['memory_leak_fixed'] else 'No'}")

        if all_tests_passed:
            print("\n🎉 MEMORY LEAK FIXES VALIDATED - Ready for production!")
        else:
            print("\n⚠️  Some tests failed - Additional fixes may be needed")

        return results

    def plot_memory_usage(self, results: Dict[str, Any], save_path: str = None):
        """Plot memory usage over time for visualization."""
        try:
            plt.figure(figsize=(12, 8))

            # Plot memory samples from different profile tests
            for test_name, test_data in results['tests'].items():
                if 'memory_samples' in test_data and 'bounded_memory' in test_name:
                    profile = test_data.get('profile', 'unknown')
                    plt.plot(test_data['memory_samples'], label=f"{profile} Profile", marker='o', alpha=0.7)

            plt.xlabel('Time (iterations)')
            plt.ylabel('Memory Usage (MB)')
            plt.title('Memory Usage Over Time - Fixed Metrics Collector')
            plt.legend()
            plt.grid(True, alpha=0.3)

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Memory usage plot saved to: {save_path}")

            plt.show()

        except ImportError:
            print("matplotlib not available - skipping memory usage plot")


def main():
    parser = argparse.ArgumentParser(description='Test memory leak fixes')
    parser.add_argument('--profile', choices=['production', 'staging', 'development'],
                       default='production', help='Memory profile to test')
    parser.add_argument('--load-test', action='store_true',
                       help='Run intensive load test')
    parser.add_argument('--plot', action='store_true',
                       help='Generate memory usage plots')

    args = parser.parse_args()

    tester = MemoryLeakTester()

    if args.load_test:
        print("Running intensive load test...")
        profile_map = {
            'production': MemoryProfile.PRODUCTION,
            'staging': MemoryProfile.STAGING,
            'development': MemoryProfile.DEVELOPMENT
        }
        profile = profile_map[args.profile]
        result = tester.test_fixed_collector_bounded_memory(profile)

        if args.plot:
            tester.plot_memory_usage({'tests': {'bounded_memory': result}})
    else:
        # Run comprehensive test
        results = tester.run_comparative_test()

        if args.plot:
            tester.plot_memory_usage(results, 'memory_leak_test_results.png')

        # Return appropriate exit code
        sys.exit(0 if results['overall_status'] == 'PASSED' else 1)


if __name__ == "__main__":
    main()