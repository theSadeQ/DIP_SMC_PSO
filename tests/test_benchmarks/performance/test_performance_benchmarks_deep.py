#==========================================================================================\\\
#=================== tests/test_performance_benchmarks_deep.py ===========================\\\
#==========================================================================================\\\

"""
Deep Performance Benchmark Tests using pytest-benchmark.
COMPREHENSIVE JOB: Measure and validate computational performance of critical components.
"""

import pytest
import numpy as np
import time
import gc
from typing import List, Tuple, Dict, Any
try:
    import psutil
except ImportError:
    from psutil_fallback import *
import os


class MockControllerForBenchmark:
    """High-performance mock controller for benchmarking."""

    def __init__(self, gains):
        self.gains = np.array(gains)
        self.last_control = 0.0
        self.call_count = 0

    def compute_control(self, state):
        """Optimized control computation."""
        self.call_count += 1
        # Simulate sliding surface computation
        sigma = np.dot(self.gains, state)
        # Simulate switching function (tanh)
        control = -np.tanh(sigma * 10.0)
        self.last_control = control
        return control

    def batch_compute_control(self, states):
        """Vectorized batch control computation."""
        self.call_count += len(states)
        # Vectorized sliding surface
        sigmas = np.dot(states, self.gains)
        # Vectorized switching function
        controls = -np.tanh(sigmas * 10.0)
        return controls


class MockSimulationEngine:
    """Mock simulation engine for benchmarking."""

    def __init__(self, dt=0.01):
        self.dt = dt

    def simulate_single_step(self, state, control):
        """Single simulation step."""
        # Mock dynamics: simple double integrator-like system
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # Simple mock dynamics
        x_ddot = control
        theta1_ddot = -theta1 - 0.1 * theta1_dot
        theta2_ddot = -theta2 - 0.1 * theta2_dot

        # Integration (Euler method)
        new_state = np.array([
            x + x_dot * self.dt,
            theta1 + theta1_dot * self.dt,
            theta2 + theta2_dot * self.dt,
            x_dot + x_ddot * self.dt,
            theta1_dot + theta1_ddot * self.dt,
            theta2_dot + theta2_ddot * self.dt
        ])

        return new_state

    def simulate_batch(self, states, controls):
        """Vectorized batch simulation."""
        batch_size = len(states)
        new_states = np.zeros_like(states)

        for i in range(batch_size):
            new_states[i] = self.simulate_single_step(states[i], controls[i])

        return new_states


@pytest.mark.benchmark
class TestControllerPerformance:
    """Performance benchmarks for controller computations."""

    @pytest.fixture
    def benchmark_controller(self):
        """Create controller for benchmarking."""
        gains = [5.0, 15.0, 10.0, 2.0, 8.0, 3.0]
        return MockControllerForBenchmark(gains)

    @pytest.fixture
    def test_states_single(self):
        """Single state for benchmarking."""
        return np.array([0.1, 0.2, 0.05, 0.15, -0.03, -0.08])

    @pytest.fixture
    def test_states_batch(self):
        """Batch of states for benchmarking."""
        np.random.seed(42)
        return np.random.randn(1000, 6) * 0.5

    def test_single_control_computation_performance(self, benchmark, benchmark_controller, test_states_single):
        """Benchmark single control computation."""

        def control_computation():
            return benchmark_controller.compute_control(test_states_single)

        result = benchmark.pedantic(
            control_computation,
            rounds=1000,
            iterations=1,
            warmup_rounds=10
        )

        assert np.isfinite(result)
        # Performance assertion: should complete in < 10µs
        assert benchmark.stats['mean'] < 1e-5

    def test_batch_control_computation_performance(self, benchmark, benchmark_controller, test_states_batch):
        """Benchmark batch control computation."""

        def batch_control_computation():
            return benchmark_controller.batch_compute_control(test_states_batch)

        result = benchmark.pedantic(
            batch_control_computation,
            rounds=100,
            iterations=1,
            warmup_rounds=5
        )

        assert len(result) == 1000
        assert np.all(np.isfinite(result))

        # Performance assertion: batch should be efficient
        # Should process 1000 states in < 1ms
        assert benchmark.stats['mean'] < 1e-3

    def test_control_computation_scaling(self, benchmark, benchmark_controller):
        """Test performance scaling with different batch sizes."""
        batch_sizes = [10, 100, 1000, 5000]
        times = []

        for batch_size in batch_sizes:
            states = np.random.randn(batch_size, 6) * 0.5

            start_time = time.perf_counter()
            benchmark_controller.batch_compute_control(states)
            end_time = time.perf_counter()

            times.append(end_time - start_time)

        # Performance should scale roughly linearly
        # Time per sample should be roughly constant
        time_per_sample = [t/s for t, s in zip(times, batch_sizes)]

        # Variance in time per sample should be small (good scaling)
        assert np.std(time_per_sample) / np.mean(time_per_sample) < 0.5

    def test_memory_efficiency_batch_processing(self, benchmark_controller):
        """Test memory efficiency of batch processing."""
        process = psutil.Process(os.getpid())

        # Measure baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process large batch
        large_batch = np.random.randn(10000, 6)
        results = benchmark_controller.batch_compute_control(large_batch)

        # Measure peak memory
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - baseline_memory

        # Clean up
        del large_batch, results
        gc.collect()

        # Memory increase should be reasonable (< 100MB for 10k states)
        assert memory_increase < 100

        # Memory should be released after cleanup
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        assert final_memory - baseline_memory < 10  # Some tolerance


@pytest.mark.benchmark
class TestSimulationPerformance:
    """Performance benchmarks for simulation computations."""

    @pytest.fixture
    def benchmark_simulator(self):
        """Create simulation engine for benchmarking."""
        return MockSimulationEngine(dt=0.01)

    @pytest.fixture
    def simulation_states_small(self):
        """Small batch of simulation states."""
        np.random.seed(42)
        return np.random.randn(100, 6) * 0.1

    @pytest.fixture
    def simulation_states_large(self):
        """Large batch of simulation states."""
        np.random.seed(42)
        return np.random.randn(5000, 6) * 0.1

    def test_single_step_simulation_performance(self, benchmark, benchmark_simulator):
        """Benchmark single simulation step."""
        state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
        control = 1.0

        def single_step():
            return benchmark_simulator.simulate_single_step(state, control)

        result = benchmark.pedantic(
            single_step,
            rounds=1000,
            iterations=1,
            warmup_rounds=10
        )

        assert len(result) == 6
        assert np.all(np.isfinite(result))

        # Should complete single step in < 5µs
        assert benchmark.stats['mean'] < 5e-6

    def test_batch_simulation_performance(self, benchmark, benchmark_simulator, simulation_states_small):
        """Benchmark batch simulation."""
        controls = np.random.randn(100)

        def batch_simulation():
            return benchmark_simulator.simulate_batch(simulation_states_small, controls)

        result = benchmark.pedantic(
            batch_simulation,
            rounds=100,
            iterations=1,
            warmup_rounds=5
        )

        assert result.shape == (100, 6)
        assert np.all(np.isfinite(result))

        # Batch of 100 should complete in < 100µs
        assert benchmark.stats['mean'] < 1e-4

    def test_large_scale_simulation_throughput(self, benchmark_simulator, simulation_states_large):
        """Test throughput for large-scale simulation."""
        controls = np.random.randn(5000)

        start_time = time.perf_counter()
        results = benchmark_simulator.simulate_batch(simulation_states_large, controls)
        end_time = time.perf_counter()

        elapsed_time = end_time - start_time
        throughput = len(simulation_states_large) / elapsed_time  # States per second

        assert np.all(np.isfinite(results))
        # Should achieve > 10,000 simulation steps per second
        assert throughput > 10000

    def test_simulation_memory_profile(self, benchmark_simulator):
        """Profile memory usage during simulation."""
        process = psutil.Process(os.getpid())

        # Baseline
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024

        # Run long simulation
        n_steps = 1000
        state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])

        states_history = []
        for i in range(n_steps):
            control = np.sin(i * 0.01)  # Time-varying control
            state = benchmark_simulator.simulate_single_step(state, control)
            if i % 100 == 0:  # Store every 100th state
                states_history.append(state.copy())

        # Check memory growth
        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = peak_memory - baseline_memory

        # Memory growth should be minimal for long simulation
        assert memory_growth < 50  # < 50MB growth

        # Verify simulation didn't blow up
        assert np.all(np.isfinite(state))
        assert np.linalg.norm(state) < 100  # Reasonable bounds


@pytest.mark.benchmark
class TestNumericalPerformance:
    """Performance benchmarks for numerical computations."""

    def test_matrix_operations_performance(self, benchmark):
        """Benchmark critical matrix operations."""
        np.random.seed(42)

        # Test matrices similar to those in control systems
        A = np.random.randn(6, 6)  # System matrix
        B = np.random.randn(6, 1)  # Control matrix
        states = np.random.randn(1000, 6)  # Batch of states

        def matrix_computation():
            # Typical operations in control systems
            state_derivatives = states @ A.T  # Batch matrix multiplication
            norms = np.linalg.norm(state_derivatives, axis=1)  # Norms
            return norms.sum()

        result = benchmark.pedantic(
            matrix_computation,
            rounds=1000,
            iterations=1,
            warmup_rounds=10
        )

        assert np.isfinite(result)
        # Should complete in < 100µs
        assert benchmark.stats['mean'] < 1e-4

    def test_trigonometric_functions_performance(self, benchmark):
        """Benchmark trigonometric function performance."""
        np.random.seed(42)
        angles = np.random.uniform(-np.pi, np.pi, 10000)

        def trig_computation():
            # Common in robotics and control
            cos_vals = np.cos(angles)
            sin_vals = np.sin(angles)
            tan_vals = np.tanh(angles)  # Used in switching functions
            return cos_vals.sum() + sin_vals.sum() + tan_vals.sum()

        result = benchmark.pedantic(
            trig_computation,
            rounds=100,
            iterations=1,
            warmup_rounds=5
        )

        assert np.isfinite(result)
        # Should handle 10k trig operations quickly
        assert benchmark.stats['mean'] < 1e-3

    def test_optimization_performance(self, benchmark):
        """Benchmark simple optimization operations."""
        np.random.seed(42)

        def optimization_step():
            # Simulate PSO-like operations
            particles = np.random.randn(50, 6)  # 50 particles, 6 dimensions
            velocities = np.random.randn(50, 6)

            # Typical PSO updates
            inertia = 0.7
            c1, c2 = 1.5, 1.5
            r1, r2 = np.random.rand(50, 6), np.random.rand(50, 6)

            # Global best (simulation)
            global_best = np.random.randn(6)
            personal_best = np.random.randn(50, 6)

            # Velocity update
            new_velocities = (inertia * velocities +
                             c1 * r1 * (personal_best - particles) +
                             c2 * r2 * (global_best - particles))

            # Position update
            new_particles = particles + new_velocities

            return np.sum(new_particles**2)  # Simple objective

        result = benchmark.pedantic(
            optimization_step,
            rounds=1000,
            iterations=1,
            warmup_rounds=10
        )

        assert np.isfinite(result)
        # PSO step should be fast
        assert benchmark.stats['mean'] < 1e-4


@pytest.mark.benchmark
class TestRealTimePerformance:
    """Performance benchmarks for real-time control requirements."""

    def test_control_loop_timing(self):
        """Test complete control loop timing for real-time requirements."""
        controller = MockControllerForBenchmark([5.0, 15.0, 10.0, 2.0, 8.0, 3.0])
        simulator = MockSimulationEngine(dt=0.01)

        # Real-time control loop simulation
        state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])
        loop_times = []

        n_loops = 1000
        for i in range(n_loops):
            start_time = time.perf_counter()

            # Complete control loop
            control = controller.compute_control(state)
            state = simulator.simulate_single_step(state, control)

            end_time = time.perf_counter()
            loop_times.append(end_time - start_time)

        loop_times = np.array(loop_times)

        # Real-time requirements analysis
        mean_time = np.mean(loop_times)
        max_time = np.max(loop_times)
        percentile_95 = np.percentile(loop_times, 95)

        # Assertions for real-time performance
        # For 100Hz control (10ms period), need much faster computation
        assert mean_time < 1e-4  # Mean < 100µs
        assert percentile_95 < 5e-4  # 95th percentile < 500µs
        assert max_time < 1e-3  # Maximum < 1ms

        # Jitter analysis (consistency)
        jitter = np.std(loop_times)
        assert jitter < mean_time * 0.5  # Jitter < 50% of mean

    def test_deadline_miss_rate(self):
        """Test deadline miss rate for hard real-time requirements."""
        controller = MockControllerForBenchmark([5.0, 15.0, 10.0, 2.0, 8.0, 3.0])
        simulator = MockSimulationEngine(dt=0.01)

        # Simulate control with hard deadline
        deadline = 1e-3  # 1ms hard deadline
        state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0])

        deadline_misses = 0
        total_loops = 1000

        for i in range(total_loops):
            start_time = time.perf_counter()

            # Control computation
            control = controller.compute_control(state)
            state = simulator.simulate_single_step(state, control)

            end_time = time.perf_counter()
            computation_time = end_time - start_time

            if computation_time > deadline:
                deadline_misses += 1

        miss_rate = deadline_misses / total_loops

        # Hard real-time requirement: < 0.1% deadline misses
        assert miss_rate < 0.001

        # Additional check: verify system remains stable
        assert np.all(np.isfinite(state))
        assert np.linalg.norm(state) < 10  # Bounded


@pytest.mark.benchmark
class TestScalabilityPerformance:
    """Performance benchmarks for scalability testing."""

    def test_state_dimension_scalability(self, benchmark):
        """Test performance scaling with state dimension."""
        dimensions = [6, 12, 24, 48]  # Different system complexities

        for dim in dimensions:
            gains = np.ones(dim)
            controller = MockControllerForBenchmark(gains)
            test_state = np.random.randn(dim) * 0.1

            def control_computation():
                return controller.compute_control(test_state)

            result = benchmark.pedantic(
                control_computation,
                rounds=100,
                iterations=1
            )

            # Performance should scale reasonably
            # For twice the dimensions, time should be < 3x worse
            expected_time = (dim / 6) * 1e-5  # Linear scaling baseline
            assert benchmark.stats['mean'] < expected_time * 3

    def test_batch_size_scalability(self):
        """Test performance scaling with batch size."""
        controller = MockControllerForBenchmark([1, 1, 1, 1, 1, 1])
        batch_sizes = [100, 500, 1000, 2000, 5000]

        times_per_sample = []

        for batch_size in batch_sizes:
            states = np.random.randn(batch_size, 6) * 0.1

            start_time = time.perf_counter()
            results = controller.batch_compute_control(states)
            end_time = time.perf_counter()

            time_per_sample = (end_time - start_time) / batch_size
            times_per_sample.append(time_per_sample)

            assert len(results) == batch_size

        # Time per sample should remain roughly constant (good vectorization)
        time_variation = np.std(times_per_sample) / np.mean(times_per_sample)
        assert time_variation < 0.3  # < 30% variation

    def test_concurrent_performance_baseline(self):
        """Baseline test for concurrent performance (single-threaded)."""
        controller = MockControllerForBenchmark([5.0, 15.0, 10.0, 2.0, 8.0, 3.0])

        # Simulate multiple controllers working
        n_controllers = 4
        n_steps = 1000

        states = [np.random.randn(6) * 0.1 for _ in range(n_controllers)]

        start_time = time.perf_counter()

        # Sequential processing
        for step in range(n_steps):
            for i in range(n_controllers):
                control = controller.compute_control(states[i])
                # Simple state update simulation
                states[i] = states[i] * 0.99 + np.random.randn(6) * 0.01

        end_time = time.perf_counter()

        total_computations = n_controllers * n_steps
        time_per_computation = (end_time - start_time) / total_computations

        # Baseline performance measurement
        assert time_per_computation < 1e-5  # < 10µs per computation

        # All states should remain bounded
        for state in states:
            assert np.all(np.isfinite(state))
            assert np.linalg.norm(state) < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "--benchmark-only", "--benchmark-autosave", "-v"])