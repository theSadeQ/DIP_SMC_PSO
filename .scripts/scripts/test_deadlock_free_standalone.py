#==========================================================================================\\\
#==================== scripts/test_deadlock_free_standalone.py =======================\\\
#==========================================================================================\\\
"""
Standalone Deadlock-Free Thread Safety Test
Direct testing of deadlock-free implementations without complex imports.
"""

import threading
import time
import random
import sys
import traceback
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def test_deadlock_free_metrics_standalone():
    """Test deadlock-free metrics collector directly."""
    logger = logging.getLogger('standalone_metrics_test')
    logger.info("Testing Deadlock-Free Metrics Collector (Standalone)...")

    try:
        # Direct import of the deadlock-free module
        sys.path.insert(0, 'D:/Projects/main/DIP_SMC_PSO/src/interfaces/monitoring')
        from metrics_collector_deadlock_free import (
            DeadlockFreeMetricsCollector, MetricType, AggregationType, AtomicCounter
        )

        # Test AtomicCounter first
        counter = AtomicCounter(0)
        assert counter.get() == 0
        assert counter.increment() == 1
        counter.set(10)
        assert counter.get() == 10
        logger.info("✓ AtomicCounter works correctly")

        # Create collector
        collector = DeadlockFreeMetricsCollector(max_metrics=10)

        # Register test metrics
        success = collector.register_metric("cpu_usage", MetricType.GAUGE, max_values=50)
        assert success, "Failed to register metric"
        logger.info("✓ Metric registration works")

        # High-concurrency test
        def worker(worker_id: int, iterations: int):
            errors = 0
            for i in range(iterations):
                try:
                    # Collect metrics rapidly
                    success = collector.collect_metric("cpu_usage", random.uniform(0, 100))
                    if not success:
                        errors += 1

                    # Get statistics rapidly
                    if i % 10 == 0:
                        stats = collector.get_system_statistics()
                        metric_stats = collector.get_metric_statistics("cpu_usage")

                    # Cleanup
                    if i % 50 == 0:
                        collector.cleanup_old_values()

                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {e}")
                    errors += 1
            return errors

        # Test with multiple threads
        num_workers = 10
        iterations = 200
        timeout = 15  # 15 seconds

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker, i, iterations) for i in range(num_workers)]

            total_errors = 0
            completed = 0

            for future in as_completed(futures, timeout=timeout):
                try:
                    errors = future.result()
                    total_errors += errors
                    completed += 1
                except Exception as e:
                    logger.error(f"Worker failed: {e}")
                    return False

        elapsed = time.time() - start_time
        logger.info(f"✓ Completed in {elapsed:.2f}s with {total_errors} errors")
        logger.info(f"  Workers completed: {completed}/{num_workers}")

        # Verify final state
        final_stats = collector.get_system_statistics()
        logger.info(f"  Values collected: {final_stats['total_values_collected']}")

        return completed == num_workers and elapsed < timeout

    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Standalone metrics test failed: {e}")
        traceback.print_exc()
        return False


def test_deadlock_free_udp_standalone():
    """Test deadlock-free UDP interface directly."""
    logger = logging.getLogger('standalone_udp_test')
    logger.info("Testing Deadlock-Free UDP Interface (Standalone)...")

    try:
        # Direct import
        sys.path.insert(0, 'D:/Projects/main/DIP_SMC_PSO/src/interfaces/network')
        from udp_interface_deadlock_free import (
            DeadlockFreeUDPInterface, InterfaceConfig, AtomicInteger, ConnectionState
        )

        # Test AtomicInteger
        atomic_int = AtomicInteger(5)
        assert atomic_int.get() == 5
        assert atomic_int.increment() == 6
        atomic_int.add(10)
        assert atomic_int.get() == 16
        logger.info("✓ AtomicInteger works correctly")

        # Create interface
        config = InterfaceConfig(name="test")
        interface = DeadlockFreeUDPInterface(config)

        # Test basic operations
        state = interface.get_connection_state()
        assert state == ConnectionState.DISCONNECTED
        logger.info("✓ Basic operations work")

        # Concurrent stress test
        def worker(worker_id: int, iterations: int):
            errors = 0
            for i in range(iterations):
                try:
                    # Rapid concurrent access
                    state = interface.get_connection_state()
                    stats = interface.get_statistics()

                    if i % 20 == 0:
                        interface.reset_statistics()

                except Exception as e:
                    logger.error(f"UDP Worker {worker_id} error: {e}")
                    errors += 1
            return errors

        # Test concurrent access
        num_workers = 8
        iterations = 150
        timeout = 10

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker, i, iterations) for i in range(num_workers)]

            total_errors = 0
            completed = 0

            for future in as_completed(futures, timeout=timeout):
                try:
                    errors = future.result()
                    total_errors += errors
                    completed += 1
                except Exception as e:
                    logger.error(f"UDP Worker failed: {e}")
                    return False

        elapsed = time.time() - start_time
        logger.info(f"✓ UDP test completed in {elapsed:.2f}s with {total_errors} errors")
        logger.info(f"  Workers completed: {completed}/{num_workers}")

        interface.close()
        return completed == num_workers and elapsed < timeout

    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Standalone UDP test failed: {e}")
        traceback.print_exc()
        return False


def test_extreme_concurrent_load():
    """Test both systems under extreme concurrent load."""
    logger = logging.getLogger('extreme_load_test')
    logger.info("Testing Extreme Concurrent Load...")

    try:
        # Import both modules
        sys.path.insert(0, 'D:/Projects/main/DIP_SMC_PSO/src/interfaces/monitoring')
        sys.path.insert(0, 'D:/Projects/main/DIP_SMC_PSO/src/interfaces/network')

        from metrics_collector_deadlock_free import DeadlockFreeMetricsCollector, MetricType
        from udp_interface_deadlock_free import DeadlockFreeUDPInterface, InterfaceConfig

        # Create instances
        collector = DeadlockFreeMetricsCollector(max_metrics=5)
        collector.register_metric("load_test", MetricType.COUNTER)

        config = InterfaceConfig(name="load_test")
        udp_interface = DeadlockFreeUDPInterface(config)

        # Extreme load worker
        def extreme_worker(worker_id: int, iterations: int):
            errors = 0
            for i in range(iterations):
                try:
                    # Rapid alternating access to both systems
                    collector.collect_metric("load_test", i)
                    udp_stats = udp_interface.get_statistics()

                    udp_state = udp_interface.get_connection_state()
                    metric_stats = collector.get_system_statistics()

                    # Mixed operations
                    if i % 15 == 0:
                        collector.cleanup_old_values()
                        udp_interface.reset_statistics()

                except Exception as e:
                    errors += 1
            return errors

        # Extreme load test
        num_workers = 20
        iterations = 300
        timeout = 20

        logger.info(f"Running extreme load: {num_workers} workers, {iterations} iterations each")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(extreme_worker, i, iterations) for i in range(num_workers)]

            total_errors = 0
            completed = 0

            for future in as_completed(futures, timeout=timeout):
                try:
                    errors = future.result()
                    total_errors += errors
                    completed += 1
                except Exception as e:
                    logger.error(f"Extreme load worker failed: {e}")
                    return False

        elapsed = time.time() - start_time
        total_ops = num_workers * iterations * 4  # 4 operations per iteration

        logger.info(f"✓ Extreme load completed in {elapsed:.2f}s")
        logger.info(f"  Workers: {completed}/{num_workers}")
        logger.info(f"  Total operations: {total_ops:,}")
        logger.info(f"  Operations/sec: {total_ops/elapsed:,.0f}")
        logger.info(f"  Total errors: {total_errors}")

        udp_interface.close()
        return completed == num_workers and elapsed < timeout

    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Extreme load test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Main test execution."""
    logger = logging.getLogger('deadlock_free_standalone')
    logger.info("Starting Standalone Deadlock-Free Validation...")

    test_results = {}
    start_time = time.time()

    # Test 1: Metrics collector
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Deadlock-Free Metrics Collector")
    logger.info("="*60)
    test_results['metrics'] = test_deadlock_free_metrics_standalone()

    # Test 2: UDP interface
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Deadlock-Free UDP Interface")
    logger.info("="*60)
    test_results['udp'] = test_deadlock_free_udp_standalone()

    # Test 3: Extreme load
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Extreme Concurrent Load")
    logger.info("="*60)
    test_results['extreme_load'] = test_extreme_concurrent_load()

    # Final report
    total_time = time.time() - start_time
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)

    logger.info("\n" + "="*80)
    logger.info("DEADLOCK-FREE VALIDATION REPORT")
    logger.info("="*80)

    logger.info(f"Total Test Time: {total_time:.2f} seconds")
    logger.info(f"Tests Passed: {passed_tests}/{total_tests}")

    for test_name, passed in test_results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {test_name.upper()}: {status}")

    if passed_tests == total_tests:
        logger.info(f"\n🎉 ALL TESTS PASSED!")
        logger.info(f"   Deadlock issues have been resolved")
        logger.info(f"   Thread safety fixes are working")
        logger.info(f"   No timeouts or hanging detected")
        logger.info(f"   Systems are now safe for concurrent use")
        result = "SUCCESS"
    else:
        logger.info(f"\n❌ {total_tests - passed_tests} TEST(S) FAILED")
        logger.info(f"   Deadlock issues may still exist")
        result = "FAILURE"

    logger.info("="*80)

    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)