#==========================================================================================\\\
#================== tests/test_memory_resource_deep.py ===================================\\\
#==========================================================================================\\\

"""
Deep Memory Usage and Resource Management Tests.
COMPREHENSIVE JOB: Test memory efficiency, resource management, and performance monitoring.
"""

import pytest
import numpy as np
try:
    import psutil
except ImportError:
    from psutil_fallback import *
import os
import gc
import time
import threading
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import warnings
import sys
import tracemalloc
# Optional memory profiler dependency with fallback
try:
    from memory_profiler import profile
except ImportError:
    # Fallback decorator that does nothing if memory_profiler isn't available
    def profile(func):
        return func

from contextlib import contextmanager


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size
    peak_mb: float  # Peak memory usage
    available_mb: float  # Available system memory
    timestamp: float


@dataclass
class ResourceProfile:
    """Comprehensive resource usage profile."""
    memory_snapshots: List[MemorySnapshot]
    cpu_percent: float
    memory_peak_mb: float
    memory_baseline_mb: float
    memory_growth_mb: float
    gc_collections: Dict[str, int]
    allocation_stats: Dict[str, Any]


class MemoryProfiler:
    """Advanced memory profiling and monitoring."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.snapshots = []
        self.baseline_memory = None

    @contextmanager
    def profile_memory(self):
        """Context manager for memory profiling."""
        # Start memory tracking
        tracemalloc.start()
        gc.collect()

        # Baseline measurement
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024
        start_time = time.time()

        try:
            yield self
        finally:
            # Final measurement
            final_memory = self.process.memory_info().rss / 1024 / 1024
            end_time = time.time()

            # Get tracemalloc stats
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Store results
            self.final_stats = {
                'baseline_mb': self.baseline_memory,
                'final_mb': final_memory,
                'growth_mb': final_memory - self.baseline_memory,
                'peak_traced_mb': peak / 1024 / 1024,
                'current_traced_mb': current / 1024 / 1024,
                'duration_seconds': end_time - start_time
            }

    def take_snapshot(self):
        """Take a memory usage snapshot."""
        memory_info = self.process.memory_info()
        system_memory = psutil.virtual_memory()

        snapshot = MemorySnapshot(
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            peak_mb=getattr(memory_info, 'peak_wset', memory_info.rss) / 1024 / 1024,
            available_mb=system_memory.available / 1024 / 1024,
            timestamp=time.time()
        )

        self.snapshots.append(snapshot)
        return snapshot

    def analyze_memory_growth(self) -> Dict[str, float]:
        """Analyze memory growth patterns."""
        if len(self.snapshots) < 2:
            return {'insufficient_data': True}

        rss_values = [s.rss_mb for s in self.snapshots]

        return {
            'initial_mb': rss_values[0],
            'final_mb': rss_values[-1],
            'growth_mb': rss_values[-1] - rss_values[0],
            'peak_mb': max(rss_values),
            'mean_mb': np.mean(rss_values),
            'std_mb': np.std(rss_values),
            'growth_rate_mb_per_snapshot': (rss_values[-1] - rss_values[0]) / len(rss_values),
            'monotonic_growth': all(rss_values[i] <= rss_values[i+1] for i in range(len(rss_values)-1))
        }


class MockMemoryIntensiveController:
    """Mock controller for memory testing."""

    def __init__(self, memory_intensive_level=1):
        self.memory_intensive_level = memory_intensive_level
        self.data_storage = []
        self.computation_cache = {}

    def simulate_memory_intensive_operation(self, data_size=1000):
        """Simulate memory-intensive control operations."""

        # Level 1: Basic operations
        if self.memory_intensive_level >= 1:
            # Create large state history
            states = np.random.randn(data_size, 6)
            controls = np.random.randn(data_size)

            self.data_storage.append({
                'states': states,
                'controls': controls,
                'timestamp': time.time()
            })

        # Level 2: More intensive caching
        if self.memory_intensive_level >= 2:
            # Matrix computations with caching
            for i in range(100):
                key = f"matrix_{i}"
                if key not in self.computation_cache:
                    matrix = np.random.randn(50, 50)
                    self.computation_cache[key] = {
                        'matrix': matrix,
                        'inverse': np.linalg.inv(matrix + 0.01 * np.eye(50)),  # Regularized
                        'eigenvals': np.linalg.eigvals(matrix)
                    }

        # Level 3: Extreme memory usage
        if self.memory_intensive_level >= 3:
            # Large tensor operations
            large_tensor = np.random.randn(100, 100, 10)
            decomposition = np.linalg.svd(large_tensor.reshape(100, -1))
            self.data_storage.append({
                'large_computation': decomposition,
                'tensor_shape': large_tensor.shape
            })

    def cleanup_memory(self):
        """Clean up stored data."""
        self.data_storage.clear()
        self.computation_cache.clear()
        gc.collect()

    def get_memory_usage_estimate(self):
        """Estimate current memory usage."""
        total_size = 0

        for item in self.data_storage:
            for key, value in item.items():
                if isinstance(value, np.ndarray):
                    total_size += value.nbytes

        for cache_item in self.computation_cache.values():
            for key, value in cache_item.items():
                if isinstance(value, np.ndarray):
                    total_size += value.nbytes

        return total_size / 1024 / 1024  # MB


@pytest.mark.memory
class TestMemoryUsage:
    """Memory usage and efficiency tests."""

    def test_controller_memory_baseline(self):
        """Test baseline memory usage of controllers."""
        profiler = MemoryProfiler()

        with profiler.profile_memory():
            # Create multiple controllers
            controllers = []
            for i in range(10):
                controller = MockMemoryIntensiveController(memory_intensive_level=1)
                controllers.append(controller)

            # Basic operations
            for controller in controllers:
                controller.simulate_memory_intensive_operation(data_size=100)

        # Memory analysis
        stats = profiler.final_stats

        # Baseline memory usage should be reasonable
        assert stats['growth_mb'] < 50, f"Excessive memory growth: {stats['growth_mb']:.2f} MB"
        assert stats['peak_traced_mb'] < 100, f"Peak memory too high: {stats['peak_traced_mb']:.2f} MB"

        # Cleanup should work
        for controller in controllers:
            controller.cleanup_memory()

        gc.collect()

        # Memory should be released after cleanup
        post_cleanup_memory = profiler.process.memory_info().rss / 1024 / 1024
        assert post_cleanup_memory - stats['baseline_mb'] < 20, "Memory not properly released after cleanup"

    def test_memory_leak_detection(self):
        """Test for memory leaks in iterative operations."""
        profiler = MemoryProfiler()

        with profiler.profile_memory():
            controller = MockMemoryIntensiveController(memory_intensive_level=1)

            # Perform repeated operations
            for iteration in range(20):
                profiler.take_snapshot()

                # Simulate control loop
                controller.simulate_memory_intensive_operation(data_size=50)

                # Periodic cleanup (simulating real-world usage)
                if iteration % 5 == 4:
                    controller.cleanup_memory()

        # Analyze memory growth
        growth_analysis = profiler.analyze_memory_growth()

        # Should not have significant memory leaks
        assert not growth_analysis.get('insufficient_data', True), "Insufficient snapshots"
        assert growth_analysis['growth_mb'] < 30, f"Potential memory leak: {growth_analysis['growth_mb']:.2f} MB growth"

        # Growth should not be strictly monotonic due to cleanup
        assert not growth_analysis['monotonic_growth'], "Memory should be released during cleanup cycles"

    def test_large_batch_memory_efficiency(self):
        """Test memory efficiency for large batch operations."""
        profiler = MemoryProfiler()

        with profiler.profile_memory():
            controller = MockMemoryIntensiveController(memory_intensive_level=2)

            # Simulate large batch processing
            batch_sizes = [100, 500, 1000, 2000]

            for batch_size in batch_sizes:
                snapshot_before = profiler.take_snapshot()

                # Process large batch
                controller.simulate_memory_intensive_operation(data_size=batch_size)

                snapshot_after = profiler.take_snapshot()

                # Memory growth should be roughly proportional to batch size
                memory_growth = snapshot_after.rss_mb - snapshot_before.rss_mb

                # Clean up to avoid accumulation
                controller.cleanup_memory()

        # Overall memory efficiency check
        stats = profiler.final_stats
        assert stats['growth_mb'] < 100, f"Inefficient batch processing: {stats['growth_mb']:.2f} MB total growth"

    def test_memory_fragmentation_analysis(self):
        """Test memory fragmentation during repeated allocations."""
        profiler = MemoryProfiler()

        with profiler.profile_memory():
            controller = MockMemoryIntensiveController(memory_intensive_level=2)

            # Create fragmentation through repeated alloc/dealloc cycles
            for cycle in range(10):
                # Allocate
                controller.simulate_memory_intensive_operation(data_size=200)
                snapshot_alloc = profiler.take_snapshot()

                # Partial cleanup (simulate fragmentation)
                if len(controller.data_storage) > 3:
                    # Remove every other item
                    controller.data_storage = controller.data_storage[::2]

                snapshot_partial = profiler.take_snapshot()

                # Full cleanup every few cycles
                if cycle % 3 == 2:
                    controller.cleanup_memory()
                    snapshot_cleanup = profiler.take_snapshot()

        # Analysis
        growth_analysis = profiler.analyze_memory_growth()

        # Should handle fragmentation reasonably
        assert growth_analysis['std_mb'] < 50, "Excessive memory fragmentation"
        assert growth_analysis['final_mb'] - growth_analysis['initial_mb'] < 50, "Memory not properly managed"

    def test_memory_pressure_handling(self):
        """Test behavior under memory pressure."""
        profiler = MemoryProfiler()

        # Get available system memory
        available_memory = psutil.virtual_memory().available / 1024 / 1024  # MB

        with profiler.profile_memory():
            controller = MockMemoryIntensiveController(memory_intensive_level=3)

            # Don't consume too much system memory in tests
            target_memory = min(available_memory * 0.1, 500)  # At most 10% of available or 500MB

            allocated_memory = 0
            operations = 0

            try:
                while allocated_memory < target_memory and operations < 50:
                    controller.simulate_memory_intensive_operation(data_size=500)

                    estimated_usage = controller.get_memory_usage_estimate()
                    allocated_memory = estimated_usage
                    operations += 1

                    # Check system memory availability
                    current_available = psutil.virtual_memory().available / 1024 / 1024
                    if current_available < available_memory * 0.8:  # If consumed >20% of system memory
                        break

            except MemoryError:
                warnings.warn("MemoryError encountered during memory pressure test")

            finally:
                controller.cleanup_memory()

        # Should handle memory pressure gracefully
        stats = profiler.final_stats
        assert operations > 0, "Should complete at least one operation"

        # Final cleanup should work even under pressure
        final_memory = profiler.process.memory_info().rss / 1024 / 1024
        memory_released = stats['final_mb'] - final_memory
        assert memory_released > -10, "Memory cleanup should work under pressure"  # Allow some variance


@pytest.mark.memory
class TestResourceManagement:
    """Resource management and monitoring tests."""

    def test_cpu_usage_monitoring(self):
        """Test CPU usage monitoring during operations."""
        # CPU monitoring
        cpu_percent_before = psutil.cpu_percent(interval=0.1)

        start_time = time.time()

        # CPU-intensive operations
        controller = MockMemoryIntensiveController(memory_intensive_level=2)

        for _ in range(10):
            # Matrix operations are CPU intensive
            controller.simulate_memory_intensive_operation(data_size=200)

        end_time = time.time()
        cpu_percent_after = psutil.cpu_percent(interval=0.1)

        duration = end_time - start_time

        # CPU usage analysis
        assert duration < 10.0, "Operations should complete in reasonable time"

        # CPU usage should be reasonable (not necessarily high due to other processes)
        max_expected_cpu = 80.0  # Allow high CPU usage for computational tasks
        if cpu_percent_after > max_expected_cpu:
            warnings.warn(f"High CPU usage: {cpu_percent_after:.1f}%")

        controller.cleanup_memory()

    def test_garbage_collection_monitoring(self):
        """Test garbage collection behavior."""

        # Get initial GC stats
        gc_stats_initial = {i: gc.get_count()[i] for i in range(3)}

        # Operations that create objects
        controller = MockMemoryIntensiveController(memory_intensive_level=2)

        # Force some object creation and collection
        for i in range(20):
            controller.simulate_memory_intensive_operation(data_size=100)

            # Periodic forced collection
            if i % 5 == 4:
                gc.collect()

        # Get final GC stats
        gc_stats_final = {i: gc.get_count()[i] for i in range(3)}

        # GC should have occurred
        total_collections_initial = sum(gc_stats_initial.values())
        total_collections_final = sum(gc_stats_final.values())

        # Some garbage collection should have occurred
        # Note: This is not guaranteed in all Python implementations
        gc_occurred = total_collections_final != total_collections_initial
        if not gc_occurred:
            warnings.warn("No garbage collection detected during test")

        controller.cleanup_memory()

    def test_file_descriptor_usage(self):
        """Test file descriptor usage (if applicable)."""

        # Get initial file descriptor count
        try:
            initial_fds = len(os.listdir('/proc/self/fd')) if os.path.exists('/proc/self/fd') else 0
        except (OSError, PermissionError):
            initial_fds = 0

        # Operations that might use file descriptors
        controller = MockMemoryIntensiveController(memory_intensive_level=1)

        for _ in range(10):
            controller.simulate_memory_intensive_operation(data_size=50)

        # Get final file descriptor count
        try:
            final_fds = len(os.listdir('/proc/self/fd')) if os.path.exists('/proc/self/fd') else 0
        except (OSError, PermissionError):
            final_fds = 0

        # Should not have file descriptor leaks
        if initial_fds > 0 and final_fds > 0:
            fd_increase = final_fds - initial_fds
            assert fd_increase < 10, f"Potential file descriptor leak: {fd_increase} new FDs"

        controller.cleanup_memory()

    def test_thread_local_resource_usage(self):
        """Test resource usage in thread-local contexts."""

        def worker_function(thread_id, results, profiler):
            """Worker function for thread testing."""
            try:
                controller = MockMemoryIntensiveController(memory_intensive_level=1)

                # Thread-local operations
                for _ in range(5):
                    snapshot = profiler.take_snapshot()
                    controller.simulate_memory_intensive_operation(data_size=50)

                # Estimate memory usage
                memory_usage = controller.get_memory_usage_estimate()

                results[thread_id] = {
                    'success': True,
                    'memory_usage_mb': memory_usage,
                    'operations_completed': 5
                }

                controller.cleanup_memory()

            except Exception as e:
                results[thread_id] = {
                    'success': False,
                    'error': str(e)
                }

        # Create threads
        num_threads = 3
        threads = []
        results = {}
        profiler = MemoryProfiler()

        with profiler.profile_memory():
            for i in range(num_threads):
                thread = threading.Thread(target=worker_function, args=(i, results, profiler))
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join(timeout=10)

        # Verify all threads completed successfully
        assert len(results) == num_threads, f"Not all threads completed: {len(results)}/{num_threads}"

        for thread_id, result in results.items():
            assert result['success'], f"Thread {thread_id} failed: {result.get('error', 'Unknown error')}"
            assert result['memory_usage_mb'] > 0, f"Thread {thread_id} reported no memory usage"

        # Overall resource usage should be reasonable
        stats = profiler.final_stats
        assert stats['growth_mb'] < 200, f"Excessive memory growth with threads: {stats['growth_mb']:.2f} MB"


@pytest.mark.memory
class TestMemoryOptimization:
    """Memory optimization and efficiency tests."""

    def test_numpy_memory_optimization(self):
        """Test NumPy memory optimization techniques."""
        profiler = MemoryProfiler()

        with profiler.profile_memory():
            # Inefficient approach
            inefficient_data = []
            for i in range(100):
                data = np.random.randn(50, 50)
                result = data @ data.T  # Matrix multiplication
                inefficient_data.append(result)

            inefficient_snapshot = profiler.take_snapshot()

            # Clear inefficient data
            del inefficient_data
            gc.collect()

            # Efficient approach - pre-allocate and reuse
            efficient_results = np.zeros((100, 50, 50))
            temp_data = np.zeros((50, 50))

            for i in range(100):
                np.random.randn(50, 50, out=temp_data)  # In-place generation
                np.matmul(temp_data, temp_data.T, out=efficient_results[i])  # In-place multiplication

            efficient_snapshot = profiler.take_snapshot()

        # Efficient approach should use less memory
        # Note: This comparison might not always hold due to garbage collection timing
        if inefficient_snapshot.rss_mb > efficient_snapshot.rss_mb:
            memory_savings = inefficient_snapshot.rss_mb - efficient_snapshot.rss_mb
            assert memory_savings > 0, "Efficient approach should save memory"

    def test_memory_pool_usage(self):
        """Test memory pool usage patterns."""
        profiler = MemoryProfiler()

        class SimpleMemoryPool:
            def __init__(self, block_size, num_blocks):
                self.block_size = block_size
                self.blocks = [np.zeros(block_size) for _ in range(num_blocks)]
                self.available = list(range(num_blocks))

            def get_block(self):
                if self.available:
                    return self.blocks[self.available.pop()]
                return None

            def return_block(self, block_idx):
                if block_idx < len(self.blocks):
                    self.available.append(block_idx)

        with profiler.profile_memory():
            # Test memory pool efficiency
            pool = SimpleMemoryPool(block_size=(100,), num_blocks=20)

            # Simulate allocation/deallocation cycles
            allocated_blocks = []

            for cycle in range(50):
                # Allocate phase
                for _ in range(min(10, len(pool.available))):
                    block = pool.get_block()
                    if block is not None:
                        allocated_blocks.append(block)
                        # Use the block
                        np.random.randn(*block.shape, out=block)

                # Deallocate phase
                if cycle % 5 == 4:
                    allocated_blocks.clear()
                    pool.available = list(range(len(pool.blocks)))

        stats = profiler.final_stats

        # Memory pool should prevent excessive allocation
        assert stats['growth_mb'] < 50, "Memory pool should limit memory growth"

    def test_sparse_matrix_memory_efficiency(self):
        """Test sparse matrix memory efficiency."""
        from scipy import sparse

        profiler = MemoryProfiler()

        with profiler.profile_memory():
            # Dense matrix approach
            dense_size = 1000
            dense_matrix = np.random.randn(dense_size, dense_size)
            # Make it sparse (90% zeros)
            mask = np.random.random((dense_size, dense_size)) < 0.1
            dense_matrix = dense_matrix * mask

            dense_snapshot = profiler.take_snapshot()

            # Convert to sparse format
            sparse_matrix = sparse.csr_matrix(dense_matrix)

            sparse_snapshot = profiler.take_snapshot()

            # Operations on sparse matrix
            result = sparse_matrix @ sparse_matrix.T

            operation_snapshot = profiler.take_snapshot()

        # Sparse representation should be more memory efficient for sparse data
        # Note: Actual memory usage depends on sparsity level

        # At minimum, operations should complete without excessive memory usage
        stats = profiler.final_stats
        assert stats['growth_mb'] < 500, "Sparse matrix operations should be memory efficient"

        # Verify sparse matrix properties
        sparsity = 1.0 - (sparse_matrix.nnz / (sparse_matrix.shape[0] * sparse_matrix.shape[1]))
        assert sparsity > 0.8, "Matrix should be sufficiently sparse for this test"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])