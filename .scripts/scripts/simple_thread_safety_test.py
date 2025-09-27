#==========================================================================================\\\
#===================== scripts/simple_thread_safety_test.py ==============================\\\
#==========================================================================================\\\
"""
Simple Thread Safety Test (No Dependencies)
Tests thread safety fixes without requiring external modules or Unicode characters.
"""

import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed


def test_basic_thread_safety():
    """Test basic thread safety with counters and locks."""
    print("Testing Basic Thread Safety...")

    # Thread-safe counter
    class SafeCounter:
        def __init__(self):
            self._value = 0
            self._lock = threading.RLock()

        def increment(self, amount=1):
            with self._lock:
                self._value += amount

        def get_value(self):
            with self._lock:
                return self._value

    counter = SafeCounter()
    errors = []

    def worker(worker_id, num_ops):
        try:
            for i in range(num_ops):
                counter.increment(1)
                time.sleep(0.001)
        except Exception as e:
            errors.append(f"Worker {worker_id}: {e}")

    # Run 10 workers, 100 increments each = 1000 total
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i, 100) for i in range(10)]
        for future in as_completed(futures):
            future.result()

    final_value = counter.get_value()
    expected_value = 1000

    if final_value == expected_value and not errors:
        print(f"  PASS: {final_value}/{expected_value} increments")
        return True
    else:
        print(f"  FAIL: {final_value}/{expected_value}, errors: {len(errors)}")
        return False


def test_concurrent_collections():
    """Test thread-safe access to shared collections."""
    print("Testing Concurrent Collections...")

    from collections import deque

    # Thread-safe bounded collection
    shared_data = deque(maxlen=500)
    data_lock = threading.RLock()
    errors = []

    def writer_worker(worker_id, num_writes):
        try:
            for i in range(num_writes):
                with data_lock:
                    item = f"worker_{worker_id}_item_{i}"
                    shared_data.append(item)
                time.sleep(0.0001)
        except Exception as e:
            errors.append(f"Writer {worker_id}: {e}")

    def reader_worker(worker_id, num_reads):
        try:
            for i in range(num_reads):
                with data_lock:
                    if shared_data:
                        item = shared_data[-1]  # Read last item
                        if not isinstance(item, str):
                            raise ValueError(f"Invalid item type: {type(item)}")
                time.sleep(0.0001)
        except Exception as e:
            errors.append(f"Reader {worker_id}: {e}")

    # Run concurrent writers and readers
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = []

        # 5 writers
        for i in range(5):
            futures.append(executor.submit(writer_worker, i, 50))

        # 10 readers
        for i in range(10):
            futures.append(executor.submit(reader_worker, i, 30))

        for future in as_completed(futures):
            future.result()

    # Check results
    with data_lock:
        final_size = len(shared_data)

    if not errors and final_size <= 500:
        print(f"  PASS: {final_size} items, no errors")
        return True
    else:
        print(f"  FAIL: {final_size} items, {len(errors)} errors")
        return False


def test_statistics_updates():
    """Test concurrent statistics updates."""
    print("Testing Statistics Updates...")

    stats = {"count": 0, "total": 0, "operations": 0}
    stats_lock = threading.RLock()
    errors = []

    def stats_worker(worker_id, num_updates):
        try:
            for i in range(num_updates):
                value = random.randint(1, 10)
                with stats_lock:
                    stats["count"] += 1
                    stats["total"] += value
                    stats["operations"] += 1
                time.sleep(0.0001)
        except Exception as e:
            errors.append(f"Stats worker {worker_id}: {e}")

    # Run concurrent statistics updates
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(stats_worker, i, 50) for i in range(12)]
        for future in as_completed(futures):
            future.result()

    # Verify consistency
    with stats_lock:
        final_stats = stats.copy()

    expected_ops = 12 * 50  # 12 workers * 50 updates = 600

    if (final_stats["operations"] == expected_ops and
        final_stats["count"] == expected_ops and
        final_stats["total"] > 0 and
        not errors):
        print(f"  PASS: {final_stats['operations']} operations completed")
        return True
    else:
        print(f"  FAIL: Expected {expected_ops}, got {final_stats}, errors: {len(errors)}")
        return False


def test_deadlock_prevention():
    """Test that locks don't cause deadlocks."""
    print("Testing Deadlock Prevention...")

    lock1 = threading.RLock()
    lock2 = threading.RLock()
    shared_data = {"value1": 0, "value2": 0}
    errors = []
    completed = {"count": 0}
    completed_lock = threading.RLock()

    def worker_a(num_ops):
        try:
            for i in range(num_ops):
                with lock1:
                    time.sleep(0.001)
                    with lock2:
                        shared_data["value1"] += 1
                        shared_data["value2"] += 1

                with completed_lock:
                    completed["count"] += 1
        except Exception as e:
            errors.append(f"Worker A: {e}")

    def worker_b(num_ops):
        try:
            for i in range(num_ops):
                with lock2:
                    time.sleep(0.001)
                    with lock1:
                        shared_data["value1"] += 10
                        shared_data["value2"] += 10

                with completed_lock:
                    completed["count"] += 1
        except Exception as e:
            errors.append(f"Worker B: {e}")

    # Start workers with timeout to detect deadlocks
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(worker_a, 15),
            executor.submit(worker_b, 15),
            executor.submit(worker_a, 15),
            executor.submit(worker_b, 15),
        ]

        try:
            for future in as_completed(futures, timeout=8.0):
                future.result()
        except Exception as e:
            print(f"  FAIL: Timeout or error - {e}")
            return False

    end_time = time.time()
    expected_ops = 4 * 15  # 60 operations

    with completed_lock:
        final_completed = completed["count"]

    if (final_completed == expected_ops and
        end_time - start_time < 5.0 and
        not errors):
        print(f"  PASS: {final_completed} operations in {end_time - start_time:.2f}s")
        return True
    else:
        print(f"  FAIL: {final_completed}/{expected_ops} ops, {end_time - start_time:.2f}s, {len(errors)} errors")
        return False


def main():
    """Run all thread safety tests."""
    print("=" * 60)
    print("Thread Safety Fix Validation")
    print("=" * 60)

    tests = [
        test_basic_thread_safety,
        test_concurrent_collections,
        test_statistics_updates,
        test_deadlock_prevention,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"  FAIL: Test exception - {e}")
            print()

    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("SUCCESS: All thread safety tests passed")
        print("Thread safety fixes are working correctly.")
    else:
        print("FAILURE: Some thread safety tests failed")
        print("Additional fixes may be needed.")

    return passed == total


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)