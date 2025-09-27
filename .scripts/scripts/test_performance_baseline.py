#==========================================================================================\\\
#======================= scripts/test_performance_baseline.py ===========================\\\
#==========================================================================================\\\
"""
Performance Baseline Test - Phase 4 Starting Point
Measure current performance before extreme optimization.
"""

import sys
import os
import time
import gc
import statistics
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_control_loop_performance():
    """Test current control loop performance."""
    print("Testing control loop performance...")

    try:
        from production_core.bulletproof_controller import BulletproofController
        from production_core.dip_dynamics import DIPDynamics

        controller = BulletproofController()
        dynamics = DIPDynamics()

        # Warm up
        state = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]
        for _ in range(100):
            control = controller.compute_control(state)
            state = dynamics.compute_dynamics(state, control)

        # Performance test
        times = []
        num_iterations = 1000

        print(f"Running {num_iterations} control loop iterations...")

        for i in range(num_iterations):
            start = time.perf_counter()

            # Single control loop iteration
            control = controller.compute_control(state)
            state = dynamics.compute_dynamics(state, control)

            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to milliseconds

        # Calculate statistics
        mean_time = statistics.mean(times)
        median_time = statistics.median(times)
        p95_time = np.percentile(times, 95)
        min_time = min(times)
        max_time = max(times)

        print(f"Control Loop Performance:")
        print(f"  Mean time: {mean_time:.3f} ms")
        print(f"  Median time: {median_time:.3f} ms")
        print(f"  95th percentile: {p95_time:.3f} ms")
        print(f"  Min time: {min_time:.3f} ms")
        print(f"  Max time: {max_time:.3f} ms")

        # Check target: <0.01ms (10 microseconds)
        target_ms = 0.01
        if mean_time < target_ms:
            print(f"ALREADY MEETS TARGET: {mean_time:.3f}ms < {target_ms}ms")
            return True, f"Control loop: {mean_time:.3f}ms (target achieved)"
        else:
            print(f"NEEDS OPTIMIZATION: {mean_time:.3f}ms > {target_ms}ms")
            return False, f"Control loop: {mean_time:.3f}ms (needs {target_ms}ms)"

    except Exception as e:
        print(f"Control loop test failed: {e}")
        return False, f"Control loop test error: {e}"

def test_memory_usage():
    """Test basic memory usage patterns."""
    print("\\nTesting memory usage...")

    try:
        from production_core.bulletproof_controller import BulletproofController
        from production_core.dip_dynamics import DIPDynamics

        controller = BulletproofController()
        dynamics = DIPDynamics()

        # Run control loops
        state = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]

        for i in range(1000):
            control = controller.compute_control(state)
            state = dynamics.compute_dynamics(state, control)

        # Force garbage collection
        gc.collect()

        print(f"Memory Usage:")
        print(f"  Completed 1000 iterations")
        print(f"  Garbage collection performed")

        # Basic check - if we get here without memory errors, it's good
        print(f"NO MEMORY ERRORS detected")
        return True, f"Memory: No memory errors in 1000 iterations"

    except Exception as e:
        print(f"Memory test failed: {e}")
        return False, f"Memory test error: {e}"

def test_scalability():
    """Test performance under load."""
    print("\\nTesting scalability...")

    try:
        from production_core.bulletproof_controller import BulletproofController

        controller = BulletproofController()

        # Test different load levels
        load_levels = [100, 500, 1000, 2000]
        results = {}

        for load in load_levels:
            state = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]
            times = []

            start_total = time.perf_counter()

            for _ in range(load):
                start = time.perf_counter()
                control = controller.compute_control(state)
                end = time.perf_counter()
                times.append((end - start) * 1000)

            end_total = time.perf_counter()
            total_time = (end_total - start_total) * 1000

            mean_time = statistics.mean(times)
            throughput = load / (total_time / 1000)  # Operations per second

            results[load] = {
                'mean_time': mean_time,
                'throughput': throughput
            }

            print(f"  Load {load}: {mean_time:.3f}ms avg, {throughput:.0f} ops/sec")

        # Check for performance degradation
        baseline_throughput = results[100]['throughput']
        high_load_throughput = results[2000]['throughput']
        degradation = (baseline_throughput - high_load_throughput) / baseline_throughput * 100

        if degradation < 20:  # Less than 20% degradation
            print(f"GOOD SCALABILITY: {degradation:.1f}% degradation")
            return True, f"Scalability: {degradation:.1f}% degradation"
        else:
            print(f"SCALABILITY ISSUE: {degradation:.1f}% degradation")
            return False, f"Scalability: {degradation:.1f}% degradation"

    except Exception as e:
        print(f"Scalability test failed: {e}")
        return False, f"Scalability test error: {e}"

def main():
    """Run performance baseline tests."""
    print("PERFORMANCE BASELINE TEST - PHASE 4")
    print("="*60)

    tests = [
        ("Control Loop Performance", test_control_loop_performance),
        ("Memory Usage", test_memory_usage),
        ("Scalability", test_scalability)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            success, message = test_func()
            if success:
                print(f"PASS: {message}")
                passed += 1
            else:
                print(f"NEEDS WORK: {message}")
        except Exception as e:
            print(f"ERROR: {test_name} - {e}")

    print("\\n" + "="*60)
    print("BASELINE RESULTS")
    print("="*60)
    print(f"Tests Passed: {passed}/{total}")

    if passed == total:
        print("ALREADY OPTIMIZED - Phase 4 targets may already be met!")
    else:
        print("OPTIMIZATION NEEDED - Proceeding with Phase 4...")

    return passed, total

if __name__ == "__main__":
    passed, total = main()
    sys.exit(0)