#==========================================================================================\\\
#============== tests/test_concurrent_thread_safety_deep.py ===============================\\\
#==========================================================================================\\\

"""
Deep Concurrent and Thread Safety Tests.
COMPREHENSIVE JOB: Test thread safety, concurrent operations, and parallel execution.
"""

import pytest
import numpy as np
import threading
import time
import queue
import concurrent.futures
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import warnings
import multiprocessing as mp
from contextlib import contextmanager
import gc


@dataclass
class ConcurrencyTestResult:
    """Results from concurrency testing."""
    thread_id: int
    success: bool
    execution_time: float
    operations_completed: int
    errors: List[str]
    final_state: Optional[Any]


@dataclass
class ThreadSafetyResult:
    """Results from thread safety analysis."""
    data_races_detected: int
    inconsistent_states: int
    successful_threads: int
    total_threads: int
    max_execution_time: float
    data_integrity_score: float


class ThreadSafeController:
    """Thread-safe mock controller for testing."""

    def __init__(self, gains):
        self.gains = np.array(gains)
        self._lock = threading.RLock()  # Reentrant lock
        self._state_history = []
        self._control_history = []
        self._operation_count = 0
        self._shared_data = {'value': 0.0, 'timestamp': time.time()}

    def compute_control_thread_safe(self, state, reference=None):
        """Thread-safe control computation."""
        with self._lock:
            # Simulate some computation time
            time.sleep(0.001)  # 1ms computation

            # Thread-safe operations
            self._operation_count += 1
            error = state if reference is None else state - reference
            control = -np.dot(self.gains, error)

            # Update shared data atomically
            self._shared_data['value'] += control * 0.1
            self._shared_data['timestamp'] = time.time()

            # Store history
            self._state_history.append(state.copy())
            self._control_history.append(control)

            return control

    def get_statistics(self):
        """Get thread-safe statistics."""
        with self._lock:
            return {
                'operation_count': self._operation_count,
                'history_length': len(self._state_history),
                'shared_value': self._shared_data['value'],
                'last_timestamp': self._shared_data['timestamp']
            }

    def reset(self):
        """Thread-safe reset."""
        with self._lock:
            self._state_history.clear()
            self._control_history.clear()
            self._operation_count = 0
            self._shared_data = {'value': 0.0, 'timestamp': time.time()}


class ConcurrentSimulator:
    """Simulator for concurrent operations testing."""

    def __init__(self, num_controllers=4):
        self.controllers = [
            ThreadSafeController([1+i, 2+i, 1.5+i, 0.5+i, 1+i, 0.5+i])
            for i in range(num_controllers)
        ]
        self.results_queue = queue.Queue()
        self.error_count = 0
        self.lock = threading.Lock()

    def worker_function(self, worker_id, num_operations, operation_delay=0.001):
        """Worker function for concurrent testing."""
        try:
            controller = self.controllers[worker_id % len(self.controllers)]
            errors = []
            start_time = time.time()
            operations_completed = 0

            for i in range(num_operations):
                try:
                    # Random state
                    state = np.random.normal(0, 0.1, 6)

                    # Control computation
                    control = controller.compute_control_thread_safe(state)

                    # Verify result is reasonable
                    if not np.isfinite(control):
                        errors.append(f"Non-finite control at operation {i}")

                    operations_completed += 1

                    # Optional delay
                    if operation_delay > 0:
                        time.sleep(operation_delay)

                except Exception as e:
                    errors.append(f"Operation {i}: {str(e)}")
                    with self.lock:
                        self.error_count += 1

            end_time = time.time()

            # Get final controller state
            final_stats = controller.get_statistics()

            result = ConcurrencyTestResult(
                thread_id=worker_id,
                success=len(errors) == 0,
                execution_time=end_time - start_time,
                operations_completed=operations_completed,
                errors=errors,
                final_state=final_stats
            )

            self.results_queue.put(result)

        except Exception as e:
            # Catch any unexpected errors
            result = ConcurrencyTestResult(
                thread_id=worker_id,
                success=False,
                execution_time=0.0,
                operations_completed=0,
                errors=[f"Worker exception: {str(e)}"],
                final_state=None
            )
            self.results_queue.put(result)

    def analyze_thread_safety(self, results: List[ConcurrencyTestResult]) -> ThreadSafetyResult:
        """Analyze thread safety from results."""

        successful_threads = sum(1 for r in results if r.success)
        total_threads = len(results)

        # Check for data consistency
        controller_stats = []
        for controller in self.controllers:
            stats = controller.get_statistics()
            controller_stats.append(stats)

        # Simple data race detection: check if operation counts make sense
        total_expected_operations = sum(r.operations_completed for r in results)
        total_actual_operations = sum(stats['operation_count'] for stats in controller_stats)

        # Account for shared controllers
        expected_per_controller = {}
        for r in results:
            controller_idx = r.thread_id % len(self.controllers)
            if controller_idx not in expected_per_controller:
                expected_per_controller[controller_idx] = 0
            expected_per_controller[controller_idx] += r.operations_completed

        # Check consistency
        data_races_detected = 0
        inconsistent_states = 0

        for i, stats in enumerate(controller_stats):
            expected = expected_per_controller.get(i, 0)
            actual = stats['operation_count']

            if abs(expected - actual) > 0:
                data_races_detected += 1

            # Check history consistency
            if stats['operation_count'] != stats['history_length']:
                inconsistent_states += 1

        # Calculate data integrity score
        if total_threads > 0:
            integrity_score = successful_threads / total_threads
        else:
            integrity_score = 0.0

        max_execution_time = max((r.execution_time for r in results), default=0.0)

        return ThreadSafetyResult(
            data_races_detected=data_races_detected,
            inconsistent_states=inconsistent_states,
            successful_threads=successful_threads,
            total_threads=total_threads,
            max_execution_time=max_execution_time,
            data_integrity_score=integrity_score
        )


@pytest.mark.concurrent
class TestBasicConcurrency:
    """Basic concurrency and thread safety tests."""

    def test_thread_safe_controller_basic(self):
        """Test basic thread safety of controller."""
        controller = ThreadSafeController([2, 4, 3, 1, 2, 1])

        def worker(worker_id, results, num_ops=50):
            """Worker function."""
            errors = []
            for i in range(num_ops):
                try:
                    state = np.random.normal(0, 0.05, 6)
                    control = controller.compute_control_thread_safe(state)
                    if not np.isfinite(control):
                        errors.append(f"Non-finite control in worker {worker_id}")
                except Exception as e:
                    errors.append(f"Worker {worker_id}: {str(e)}")

            results[worker_id] = errors

        # Run multiple threads
        num_threads = 4
        threads = []
        results = {}

        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i, results))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)

        # Check results
        all_errors = []
        for worker_errors in results.values():
            all_errors.extend(worker_errors)

        assert len(all_errors) == 0, f"Thread safety errors: {all_errors}"

        # Check final state consistency
        final_stats = controller.get_statistics()
        assert final_stats['operation_count'] == num_threads * 50, "Operation count inconsistency"
        assert final_stats['history_length'] == num_threads * 50, "History length inconsistency"

    def test_concurrent_simulation_stress(self):
        """Stress test concurrent simulation."""
        simulator = ConcurrentSimulator(num_controllers=3)

        # Launch multiple workers
        num_workers = 6
        operations_per_worker = 100
        threads = []

        start_time = time.time()

        for worker_id in range(num_workers):
            thread = threading.Thread(
                target=simulator.worker_function,
                args=(worker_id, operations_per_worker, 0.0005)  # Small delay
            )
            threads.append(thread)
            thread.start()

        # Wait for all workers
        for thread in threads:
            thread.join(timeout=30)  # Generous timeout

        end_time = time.time()
        total_time = end_time - start_time

        # Collect results
        results = []
        while not simulator.results_queue.empty():
            results.append(simulator.results_queue.get())

        assert len(results) == num_workers, f"Expected {num_workers} results, got {len(results)}"

        # Analyze thread safety
        safety_analysis = simulator.analyze_thread_safety(results)

        # Validation
        assert safety_analysis.successful_threads >= num_workers * 0.8, "Too many thread failures"
        assert safety_analysis.data_races_detected == 0, f"Data races detected: {safety_analysis.data_races_detected}"
        assert safety_analysis.inconsistent_states == 0, f"Inconsistent states: {safety_analysis.inconsistent_states}"
        assert safety_analysis.data_integrity_score >= 0.8, f"Poor data integrity: {safety_analysis.data_integrity_score}"

        # Performance check
        assert total_time < 20.0, f"Stress test took too long: {total_time:.2f}s"

    def test_producer_consumer_pattern(self):
        """Test producer-consumer pattern for control systems."""
        state_queue = queue.Queue(maxsize=20)
        control_queue = queue.Queue(maxsize=20)
        controller = ThreadSafeController([3, 6, 4, 1.5, 3, 1.5])

        # Producer: generates states
        def producer(num_states):
            for i in range(num_states):
                state = np.random.normal(0, 0.1, 6)
                state_queue.put((i, state))
                time.sleep(0.001)  # Simulate sensor sampling rate

        # Consumer: processes states
        def consumer(results, num_states):
            processed = 0
            errors = []

            while processed < num_states:
                try:
                    state_id, state = state_queue.get(timeout=1.0)
                    control = controller.compute_control_thread_safe(state)

                    control_queue.put((state_id, control))
                    processed += 1

                except queue.Empty:
                    errors.append("Queue timeout")
                    break
                except Exception as e:
                    errors.append(f"Processing error: {str(e)}")

            results['processed'] = processed
            results['errors'] = errors

        # Monitor: checks outputs
        def monitor(results, expected_count):
            received = 0
            errors = []

            while received < expected_count:
                try:
                    state_id, control = control_queue.get(timeout=2.0)

                    if not np.isfinite(control):
                        errors.append(f"Non-finite control for state {state_id}")

                    received += 1

                except queue.Empty:
                    errors.append("Monitor timeout")
                    break
                except Exception as e:
                    errors.append(f"Monitor error: {str(e)}")

            results['received'] = received
            results['errors'] = errors

        # Run producer-consumer test
        num_items = 100
        consumer_results = {}
        monitor_results = {}

        producer_thread = threading.Thread(target=producer, args=(num_items,))
        consumer_thread = threading.Thread(target=consumer, args=(consumer_results, num_items))
        monitor_thread = threading.Thread(target=monitor, args=(monitor_results, num_items))

        # Start all threads
        producer_thread.start()
        consumer_thread.start()
        monitor_thread.start()

        # Wait for completion
        producer_thread.join(timeout=5)
        consumer_thread.join(timeout=5)
        monitor_thread.join(timeout=10)

        # Verify results
        assert consumer_results.get('processed', 0) == num_items, f"Consumer processed {consumer_results.get('processed', 0)}/{num_items}"
        assert len(consumer_results.get('errors', [])) == 0, f"Consumer errors: {consumer_results.get('errors', [])}"

        assert monitor_results.get('received', 0) == num_items, f"Monitor received {monitor_results.get('received', 0)}/{num_items}"
        assert len(monitor_results.get('errors', [])) == 0, f"Monitor errors: {monitor_results.get('errors', [])}"


@pytest.mark.concurrent
class TestAdvancedConcurrency:
    """Advanced concurrency patterns and edge cases."""

    def test_deadlock_prevention(self):
        """Test deadlock prevention mechanisms."""

        class DeadlockTestController:
            def __init__(self):
                self.lock1 = threading.Lock()
                self.lock2 = threading.Lock()
                self.counter = 0

            def method_a(self):
                """Method that acquires locks in order A -> B."""
                with self.lock1:
                    time.sleep(0.001)  # Small delay to increase deadlock chance
                    with self.lock2:
                        self.counter += 1
                        return self.counter

            def method_b(self):
                """Method that acquires locks in order B -> A (potential deadlock)."""
                # Fixed: Use consistent lock ordering to prevent deadlock
                with self.lock1:  # Same order as method_a
                    time.sleep(0.001)
                    with self.lock2:
                        self.counter += 10
                        return self.counter

        controller = DeadlockTestController()

        def worker_a(results, num_ops):
            """Worker that calls method_a."""
            errors = []
            for i in range(num_ops):
                try:
                    result = controller.method_a()
                    if result <= 0:
                        errors.append(f"Invalid result from method_a: {result}")
                except Exception as e:
                    errors.append(f"method_a error: {str(e)}")

            results['a_errors'] = errors

        def worker_b(results, num_ops):
            """Worker that calls method_b."""
            errors = []
            for i in range(num_ops):
                try:
                    result = controller.method_b()
                    if result <= 0:
                        errors.append(f"Invalid result from method_b: {result}")
                except Exception as e:
                    errors.append(f"method_b error: {str(e)}")

            results['b_errors'] = errors

        # Test with multiple threads to check for deadlocks
        results = {}
        threads = []

        # Create alternating worker types
        for i in range(6):
            if i % 2 == 0:
                thread = threading.Thread(target=worker_a, args=(results, 50))
            else:
                thread = threading.Thread(target=worker_b, args=(results, 50))
            threads.append(thread)

        start_time = time.time()

        for thread in threads:
            thread.start()

        # Wait with timeout to detect potential deadlocks
        for thread in threads:
            thread.join(timeout=5)  # 5 second timeout

        end_time = time.time()

        # Check if any threads are still alive (deadlock indicator)
        alive_threads = [t for t in threads if t.is_alive()]
        assert len(alive_threads) == 0, f"Potential deadlock: {len(alive_threads)} threads still alive"

        # Should complete quickly without deadlocks
        assert end_time - start_time < 3.0, f"Test took too long: {end_time - start_time:.2f}s (possible deadlock)"

        # Check that both methods executed successfully
        assert 'a_errors' in results and 'b_errors' in results, "Not all workers completed"
        assert len(results.get('a_errors', [])) == 0, f"Method A errors: {results.get('a_errors', [])}"
        assert len(results.get('b_errors', [])) == 0, f"Method B errors: {results.get('b_errors', [])}"

    def test_race_condition_detection(self):
        """Test race condition detection and prevention."""

        class RaceConditionController:
            def __init__(self):
                self.shared_counter = 0
                self.operations_log = []
                self.lock = threading.Lock()

            def unsafe_increment(self):
                """Unsafe increment (potential race condition)."""
                # Read-modify-write without proper synchronization
                temp = self.shared_counter
                time.sleep(0.0001)  # Simulate processing delay
                self.shared_counter = temp + 1

            def safe_increment(self):
                """Safe increment with proper synchronization."""
                with self.lock:
                    temp = self.shared_counter
                    time.sleep(0.0001)  # Same processing delay
                    self.shared_counter = temp + 1
                    self.operations_log.append(self.shared_counter)

        # Test unsafe operations (should detect race conditions)
        unsafe_controller = RaceConditionController()

        def unsafe_worker(num_ops):
            for _ in range(num_ops):
                unsafe_controller.unsafe_increment()

        unsafe_threads = []
        for _ in range(5):
            thread = threading.Thread(target=unsafe_worker, args=(20,))
            unsafe_threads.append(thread)
            thread.start()

        for thread in unsafe_threads:
            thread.join()

        # Expected value: 5 threads * 20 operations = 100
        # Actual value will likely be less due to race conditions
        unsafe_final_value = unsafe_controller.shared_counter
        expected_value = 100

        # Race condition indicator: final value less than expected
        race_condition_detected = unsafe_final_value < expected_value
        if not race_condition_detected:
            warnings.warn(f"Race condition not detected in unsafe test (got {unsafe_final_value}/{expected_value})")

        # Test safe operations (should not have race conditions)
        safe_controller = RaceConditionController()

        def safe_worker(num_ops):
            for _ in range(num_ops):
                safe_controller.safe_increment()

        safe_threads = []
        for _ in range(5):
            thread = threading.Thread(target=safe_worker, args=(20,))
            safe_threads.append(thread)
            thread.start()

        for thread in safe_threads:
            thread.join()

        safe_final_value = safe_controller.shared_counter

        # Safe version should achieve expected value
        assert safe_final_value == expected_value, f"Safe operations failed: {safe_final_value}/{expected_value}"

        # Verify operation log consistency
        assert len(safe_controller.operations_log) == expected_value, "Operations log inconsistent"

    def test_thread_pool_executor(self):
        """Test thread pool executor for concurrent operations."""
        controller = ThreadSafeController([2, 4, 3, 1, 2, 1])

        def control_task(task_id):
            """Task for thread pool execution."""
            try:
                state = np.random.normal(0, 0.1, 6)
                control = controller.compute_control_thread_safe(state)

                return {
                    'task_id': task_id,
                    'success': True,
                    'control': control,
                    'error': None
                }
            except Exception as e:
                return {
                    'task_id': task_id,
                    'success': False,
                    'control': None,
                    'error': str(e)
                }

        # Use ThreadPoolExecutor
        num_tasks = 100
        max_workers = 8

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_task = {executor.submit(control_task, i): i for i in range(num_tasks)}

            # Collect results
            results = []
            for future in concurrent.futures.as_completed(future_to_task, timeout=10):
                result = future.result()
                results.append(result)

        end_time = time.time()

        # Verify results
        assert len(results) == num_tasks, f"Expected {num_tasks} results, got {len(results)}"

        successful_tasks = [r for r in results if r['success']]
        failed_tasks = [r for r in results if not r['success']]

        assert len(successful_tasks) >= num_tasks * 0.95, f"Too many failed tasks: {len(failed_tasks)}"

        # Check controller consistency
        final_stats = controller.get_statistics()
        assert final_stats['operation_count'] == len(successful_tasks), "Operation count mismatch"

        # Performance check
        assert end_time - start_time < 5.0, f"Thread pool execution took too long: {end_time - start_time:.2f}s"

        # Check for any errors
        if failed_tasks:
            error_messages = [task['error'] for task in failed_tasks]
            warnings.warn(f"Some tasks failed: {error_messages}")


@pytest.mark.concurrent
class TestParallelProcessing:
    """Test parallel processing with multiprocessing."""

    def test_multiprocessing_controller_isolation(self):
        """Test controller isolation in multiprocessing."""

        def worker_process(worker_id, num_operations, result_queue):
            """Worker process function."""
            try:
                # Each process gets its own controller instance
                from tests.test_concurrent_thread_safety_deep import ThreadSafeController
                controller = ThreadSafeController([1+worker_id, 2+worker_id, 1.5, 0.5, 1, 0.5])

                results = []
                for i in range(num_operations):
                    state = np.random.normal(0, 0.1, 6)
                    control = controller.compute_control_thread_safe(state)
                    results.append(control)

                # Return statistics
                stats = controller.get_statistics()
                result_queue.put({
                    'worker_id': worker_id,
                    'success': True,
                    'operations_completed': len(results),
                    'final_stats': stats,
                    'sample_controls': results[:5]  # First 5 controls as sample
                })

            except Exception as e:
                result_queue.put({
                    'worker_id': worker_id,
                    'success': False,
                    'error': str(e),
                    'operations_completed': 0
                })

        # Create multiprocessing context
        if hasattr(mp, 'get_context'):
            ctx = mp.get_context('spawn')  # Use spawn to avoid issues
        else:
            ctx = mp

        # Create processes
        num_processes = 3
        operations_per_process = 50
        result_queue = ctx.Queue()

        processes = []
        for i in range(num_processes):
            process = ctx.Process(
                target=worker_process,
                args=(i, operations_per_process, result_queue)
            )
            processes.append(process)
            process.start()

        # Wait for completion
        start_time = time.time()
        for process in processes:
            process.join(timeout=10)

        end_time = time.time()

        # Collect results
        results = []
        while not result_queue.empty():
            try:
                result = result_queue.get_nowait()
                results.append(result)
            except:
                break

        # Clean up
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join()

        # Verify results
        assert len(results) == num_processes, f"Expected {num_processes} results, got {len(results)}"

        successful_processes = [r for r in results if r['success']]
        assert len(successful_processes) == num_processes, f"Some processes failed"

        # Check isolation - each process should have completed its operations
        for result in successful_processes:
            assert result['operations_completed'] == operations_per_process
            assert result['final_stats']['operation_count'] == operations_per_process

        # Performance check
        assert end_time - start_time < 8.0, f"Multiprocessing took too long: {end_time - start_time:.2f}s"

    def test_shared_memory_safety(self):
        """Test shared memory safety between processes."""
        # This test would typically use multiprocessing.shared_memory
        # For simplicity, we'll use a basic shared value test

        if hasattr(mp, 'get_context'):
            ctx = mp.get_context('spawn')
        else:
            ctx = mp

        # Shared counter
        shared_counter = ctx.Value('i', 0)
        shared_lock = ctx.Lock()

        def increment_worker(worker_id, num_increments, counter, lock, result_queue):
            """Worker that increments shared counter."""
            try:
                local_increments = 0

                for i in range(num_increments):
                    with lock:
                        counter.value += 1
                        local_increments += 1

                result_queue.put({
                    'worker_id': worker_id,
                    'success': True,
                    'increments': local_increments
                })

            except Exception as e:
                result_queue.put({
                    'worker_id': worker_id,
                    'success': False,
                    'error': str(e)
                })

        # Test shared memory operations
        num_processes = 4
        increments_per_process = 25
        result_queue = ctx.Queue()

        processes = []
        for i in range(num_processes):
            process = ctx.Process(
                target=increment_worker,
                args=(i, increments_per_process, shared_counter, shared_lock, result_queue)
            )
            processes.append(process)
            process.start()

        # Wait for completion
        for process in processes:
            process.join(timeout=5)

        # Collect results
        results = []
        while not result_queue.empty():
            try:
                result = result_queue.get_nowait()
                results.append(result)
            except:
                break

        # Clean up
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join()

        # Verify shared memory consistency
        expected_final_value = num_processes * increments_per_process
        actual_final_value = shared_counter.value

        assert actual_final_value == expected_final_value, f"Shared counter inconsistent: {actual_final_value}/{expected_final_value}"

        # Verify all processes completed successfully
        successful_processes = [r for r in results if r['success']]
        assert len(successful_processes) == num_processes, "Some processes failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])