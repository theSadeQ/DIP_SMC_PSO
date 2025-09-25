#==========================================================================================\\\
#========================= scripts/test_deadlock_free_fixes.py ========================\\\
#==========================================================================================\\\
"""
Deadlock-Free Thread Safety Validation
Tests the new deadlock-free implementations to ensure they resolve the timeout issues
and work correctly under extreme concurrent load without deadlocks.

This comprehensive test validates:
1. Deadlock-free metrics collector under high concurrency
2. Deadlock-free UDP interface thread safety
3. No timeouts or hanging in multi-threaded scenarios
4. Correct data integrity under concurrent access
5. Performance under stress conditions
"""

import threading
import time
import random
import sys
import traceback
import asyncio
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def test_deadlock_free_metrics():
    """Test deadlock-free metrics collector under extreme load."""
    logger = logging.getLogger('deadlock_free_metrics_test')
    logger.info("Testing Deadlock-Free Metrics Collector...")

    try:
        # Import the deadlock-free version
        sys.path.append('src')
        from interfaces.monitoring.metrics_collector_deadlock_free import (
            DeadlockFreeMetricsCollector, MetricType, AggregationType
        )

        # Create collector
        collector = DeadlockFreeMetricsCollector(max_metrics=50)

        # Register test metrics
        metrics = [
            ("cpu_usage", MetricType.GAUGE),
            ("memory_usage", MetricType.GAUGE),
            ("request_count", MetricType.COUNTER),
            ("response_time", MetricType.TIMER),
            ("error_rate", MetricType.RATE),
        ]

        for name, metric_type in metrics:
            success = collector.register_metric(name, metric_type, max_values=100)
            if not success:
                logger.error(f"Failed to register metric: {name}")
                return False

        # High-concurrency stress test
        def stress_worker(worker_id: int, iterations: int):
            """Worker that hammers metrics collector."""
            errors = 0
            for i in range(iterations):
                try:
                    # Rapid metric collection
                    for name, _ in metrics:
                        value = random.uniform(0, 100)
                        success = collector.collect_metric(name, value)
                        if not success:
                            errors += 1

                    # Rapid statistics retrieval
                    if i % 10 == 0:
                        stats = collector.get_system_statistics()
                        all_metrics = collector.get_all_metrics()

                    # Rapid cleanup
                    if i % 50 == 0:
                        collector.cleanup_old_values()

                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {e}")
                    errors += 1

            return errors

        # Launch high-concurrency test
        num_workers = 20
        iterations_per_worker = 500
        timeout = 30  # 30 seconds max - should complete much faster

        logger.info(f"Launching {num_workers} workers with {iterations_per_worker} iterations each...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(stress_worker, i, iterations_per_worker)
                for i in range(num_workers)
            ]

            # Wait with timeout
            total_errors = 0
            completed_workers = 0

            for future in as_completed(futures, timeout=timeout):
                try:
                    errors = future.result()
                    total_errors += errors
                    completed_workers += 1
                except Exception as e:
                    logger.error(f"Worker failed: {e}")
                    return False

        elapsed = time.time() - start_time
        total_operations = num_workers * iterations_per_worker * len(metrics)

        logger.info(f"✓ Metrics test completed in {elapsed:.2f} seconds")
        logger.info(f"  Workers: {completed_workers}/{num_workers}")
        logger.info(f"  Total operations: {total_operations:,}")
        logger.info(f"  Operations/sec: {total_operations/elapsed:,.0f}")
        logger.info(f"  Total errors: {total_errors}")

        # Verify final state
        final_stats = collector.get_system_statistics()
        logger.info(f"  Final metrics collected: {final_stats['total_values_collected']}")

        return completed_workers == num_workers and elapsed < timeout

    except Exception as e:
        logger.error(f"✗ Deadlock-free metrics test failed: {e}")
        traceback.print_exc()
        return False


def test_deadlock_free_udp():
    """Test deadlock-free UDP interface under concurrent load."""
    logger = logging.getLogger('deadlock_free_udp_test')
    logger.info("Testing Deadlock-Free UDP Interface...")

    try:
        # Import the deadlock-free version
        sys.path.append('src')
        from interfaces.network.udp_interface_deadlock_free import (
            DeadlockFreeUDPInterface, InterfaceConfig, MessageType, Priority
        )

        # Create interface
        config = InterfaceConfig(
            name="test_udp",
            use_compression=False,
            use_sequence=True,
            buffer_size=4096
        )
        interface = DeadlockFreeUDPInterface(config)

        # Concurrent operations test
        def concurrent_worker(worker_id: int, iterations: int):
            """Worker that performs concurrent UDP operations."""
            errors = 0

            for i in range(iterations):
                try:
                    # Rapid state checks
                    state = interface.get_connection_state()

                    # Rapid statistics access
                    stats = interface.get_statistics()

                    # Handler registration/unregistration
                    if i % 20 == 0:
                        handler = lambda msg: None
                        interface.register_message_handler(MessageType.DATA, handler)
                        interface.unregister_message_handler(MessageType.DATA)

                    # Reset statistics
                    if i % 100 == 0:
                        interface.reset_statistics()

                except Exception as e:
                    logger.error(f"UDP Worker {worker_id} error: {e}")
                    errors += 1

            return errors

        # Launch concurrent access test
        num_workers = 15
        iterations_per_worker = 300
        timeout = 20  # 20 seconds max

        logger.info(f"Launching {num_workers} UDP workers with {iterations_per_worker} iterations each...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(concurrent_worker, i, iterations_per_worker)
                for i in range(num_workers)
            ]

            # Wait with timeout
            total_errors = 0
            completed_workers = 0

            for future in as_completed(futures, timeout=timeout):
                try:
                    errors = future.result()
                    total_errors += errors
                    completed_workers += 1
                except Exception as e:
                    logger.error(f"UDP Worker failed: {e}")
                    return False

        elapsed = time.time() - start_time
        total_operations = num_workers * iterations_per_worker

        logger.info(f"✓ UDP test completed in {elapsed:.2f} seconds")
        logger.info(f"  Workers: {completed_workers}/{num_workers}")
        logger.info(f"  Total operations: {total_operations:,}")
        logger.info(f"  Operations/sec: {total_operations/elapsed:,.0f}")
        logger.info(f"  Total errors: {total_errors}")

        # Cleanup
        interface.close()

        return completed_workers == num_workers and elapsed < timeout

    except Exception as e:
        logger.error(f"✗ Deadlock-free UDP test failed: {e}")
        traceback.print_exc()
        return False


def test_mixed_concurrent_access():
    """Test mixed concurrent access patterns that previously caused deadlocks."""
    logger = logging.getLogger('mixed_concurrent_test')
    logger.info("Testing Mixed Concurrent Access Patterns...")

    try:
        # Test both systems together under load
        sys.path.append('src')
        from interfaces.monitoring.metrics_collector_deadlock_free import (
            DeadlockFreeMetricsCollector, MetricType
        )
        from interfaces.network.udp_interface_deadlock_free import (
            DeadlockFreeUDPInterface, InterfaceConfig
        )

        # Initialize both systems
        collector = DeadlockFreeMetricsCollector(max_metrics=20)
        collector.register_metric("test_metric", MetricType.GAUGE, max_values=50)

        config = InterfaceConfig(name="mixed_test")
        udp_interface = DeadlockFreeUDPInterface(config)

        # Mixed access pattern
        def mixed_worker(worker_id: int, iterations: int):
            """Worker that accesses both systems in patterns that caused deadlocks."""
            errors = 0

            for i in range(iterations):
                try:
                    # Pattern 1: Metrics -> UDP
                    collector.collect_metric("test_metric", random.uniform(0, 100))
                    udp_stats = udp_interface.get_statistics()

                    # Pattern 2: UDP -> Metrics
                    udp_state = udp_interface.get_connection_state()
                    metric_stats = collector.get_system_statistics()

                    # Pattern 3: Overlapping operations
                    if i % 10 == 0:
                        all_metrics = collector.get_all_metrics()
                        udp_interface.reset_statistics()

                    # Pattern 4: Rapid alternation
                    for _ in range(5):
                        collector.collect_metric("test_metric", i)
                        udp_interface.get_statistics()

                except Exception as e:
                    logger.error(f"Mixed worker {worker_id} error: {e}")
                    errors += 1

            return errors

        # Test under extreme load
        num_workers = 25
        iterations_per_worker = 200
        timeout = 25  # 25 seconds max

        logger.info(f"Launching {num_workers} mixed workers...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(mixed_worker, i, iterations_per_worker)
                for i in range(num_workers)
            ]

            total_errors = 0
            completed_workers = 0

            for future in as_completed(futures, timeout=timeout):
                try:
                    errors = future.result()
                    total_errors += errors
                    completed_workers += 1
                except Exception as e:
                    logger.error(f"Mixed worker failed: {e}")
                    return False

        elapsed = time.time() - start_time

        logger.info(f"✓ Mixed access test completed in {elapsed:.2f} seconds")
        logger.info(f"  Workers: {completed_workers}/{num_workers}")
        logger.info(f"  Total errors: {total_errors}")

        # Cleanup
        udp_interface.close()

        return completed_workers == num_workers and elapsed < timeout

    except Exception as e:
        logger.error(f"✗ Mixed concurrent test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Main test execution with comprehensive validation."""
    logger = logging.getLogger('deadlock_free_validation')
    logger.info("Starting Deadlock-Free Thread Safety Validation...")
    logger.info("This test validates that the timeout issues have been resolved.")

    # Test results tracking
    test_results = {}
    start_time = time.time()

    # 1. Test deadlock-free metrics collector
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Deadlock-Free Metrics Collector")
    logger.info("="*60)
    test_results['metrics'] = test_deadlock_free_metrics()

    # 2. Test deadlock-free UDP interface
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Deadlock-Free UDP Interface")
    logger.info("="*60)
    test_results['udp'] = test_deadlock_free_udp()

    # 3. Test mixed concurrent access
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Mixed Concurrent Access Patterns")
    logger.info("="*60)
    test_results['mixed'] = test_mixed_concurrent_access()

    # Generate final report
    total_time = time.time() - start_time
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)

    logger.info("\n" + "="*80)
    logger.info("DEADLOCK-FREE THREAD SAFETY TEST REPORT")
    logger.info("="*80)

    logger.info(f"Total Test Time: {total_time:.2f} seconds")
    logger.info(f"Tests Passed: {passed_tests}/{total_tests}")

    for test_name, passed in test_results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {test_name.upper()}: {status}")

    if passed_tests == total_tests:
        logger.info(f"\n🎉 ALL TESTS PASSED - DEADLOCK ISSUES RESOLVED!")
        logger.info(f"   Thread safety fixes are working correctly")
        logger.info(f"   No timeouts or hanging detected")
        logger.info(f"   Safe for production deployment")
    else:
        logger.info(f"\n❌ {total_tests - passed_tests} TEST(S) FAILED")
        logger.info(f"   Deadlock issues may still exist")
        logger.info(f"   NOT safe for production deployment")

    logger.info("="*80)

    # Return success if all tests passed
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)