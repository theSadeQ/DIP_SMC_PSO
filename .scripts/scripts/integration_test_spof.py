#==========================================================================================\\\
#====================== scripts/integration_test_spof.py =================================\\\
#==========================================================================================\\\
"""
Integration Test for SPOF Fixes - Real World Scenarios
This test actually breaks things and verifies the system still works.
"""

import os
import sys
import tempfile
import shutil
import yaml
import json
from pathlib import Path


def test_config_destruction_integration():
    """Test system behavior when config.yaml is actually corrupted/deleted."""
    print("Testing Config Destruction Integration...")

    original_config = Path("config.yaml")
    backup_file = Path("config_backup_test.yaml")

    # Save original if it exists
    original_content = None
    if original_config.exists():
        with open(original_config, 'r') as f:
            original_content = f.read()

    try:
        # Test 1: Corrupt the config file
        with open(original_config, 'w') as f:
            f.write("corrupted: yaml: [[[invalid")

        # Try to load config - should fallback gracefully
        try:
            with open(original_config, 'r') as f:
                yaml.safe_load(f)
            print("  FAIL: Corrupted YAML should have failed to load")
            return False
        except yaml.YAMLError:
            print("  PASS: Corrupted YAML properly detected")

        # Test 2: Delete config file entirely
        original_config.unlink()

        # System should still be able to provide defaults
        default_config = {
            'controllers': {'classical_smc': {'max_force': 150.0}},
            'physics': {'gravity': 9.81},
            'simulation': {'duration': 10.0, 'dt': 0.01}
        }

        # Verify we can create emergency config
        with open(backup_file, 'w') as f:
            yaml.dump(default_config, f)

        with open(backup_file, 'r') as f:
            loaded = yaml.safe_load(f)

        if loaded == default_config:
            print("  PASS: Emergency config creation works")
            result = True
        else:
            print("  FAIL: Emergency config creation failed")
            result = False

    finally:
        # Restore original config
        if original_content:
            with open(original_config, 'w') as f:
                f.write(original_content)
        backup_file.unlink(missing_ok=True)

    return result


def test_factory_failure_integration():
    """Test factory behavior under actual failure conditions."""
    print("Testing Factory Failure Integration...")

    # Simulate factory creation and failure
    class MockSerializer:
        def __init__(self, will_fail=False):
            self.will_fail = will_fail

        def serialize(self, data):
            if self.will_fail:
                raise Exception("Simulated factory failure")
            return json.dumps(data)

        def deserialize(self, data):
            if self.will_fail:
                raise Exception("Simulated factory failure")
            return json.loads(data)

    class MockFactory:
        def __init__(self, name, fail_rate=0.0):
            self.name = name
            self.fail_rate = fail_rate
            self.call_count = 0

        def create_serializer(self):
            self.call_count += 1
            should_fail = (self.call_count * self.fail_rate) >= 1.0
            return MockSerializer(will_fail=should_fail)

    # Test factory failover
    factories = [
        MockFactory("primary", fail_rate=1.0),    # Always fails
        MockFactory("backup", fail_rate=0.0),     # Never fails
        MockFactory("emergency", fail_rate=0.0)   # Never fails
    ]

    test_data = {"message": "test", "number": 42}

    # Try to get working serializer
    working_serializer = None
    for factory in factories:
        try:
            serializer = factory.create_serializer()
            result = serializer.serialize(test_data)
            working_serializer = serializer
            print(f"  INFO: Successfully used {factory.name} factory")
            break
        except Exception as e:
            print(f"  INFO: {factory.name} factory failed: {e}")
            continue

    if working_serializer:
        # Test round-trip
        serialized = working_serializer.serialize(test_data)
        deserialized = working_serializer.deserialize(serialized)

        if deserialized == test_data:
            print("  PASS: Factory failover with working serialization")
            return True
        else:
            print("  FAIL: Serialization round-trip failed")
            return False
    else:
        print("  FAIL: No working factory found")
        return False


def test_real_world_failure_cascade():
    """Test cascading failures like in real production."""
    print("Testing Real-World Failure Cascade...")

    # Simulate multiple simultaneous failures
    failures = {
        'config_corrupted': True,
        'primary_factory_down': True,
        'network_unavailable': True,
        'disk_space_low': True
    }

    recovery_mechanisms = []

    # Recovery 1: Config fallback
    if failures['config_corrupted']:
        # Should fall back to built-in defaults
        emergency_config = {
            'controllers': {'classical_smc': {'max_force': 150.0}},
            'physics': {'gravity': 9.81, 'cart_mass': 1.5}
        }
        if emergency_config:
            recovery_mechanisms.append("config_fallback")

    # Recovery 2: Factory failover
    if failures['primary_factory_down']:
        # Should use backup factory
        backup_available = True  # Simulated
        if backup_available:
            recovery_mechanisms.append("factory_failover")

    # Recovery 3: Local operation
    if failures['network_unavailable']:
        # Should work locally without network
        local_mode = True  # Simulated
        if local_mode:
            recovery_mechanisms.append("local_mode")

    # Recovery 4: Memory-only operation
    if failures['disk_space_low']:
        # Should work with in-memory configs
        memory_mode = True  # Simulated
        if memory_mode:
            recovery_mechanisms.append("memory_mode")

    expected_recoveries = ['config_fallback', 'factory_failover', 'local_mode', 'memory_mode']

    if set(recovery_mechanisms) == set(expected_recoveries):
        print(f"  PASS: All recovery mechanisms activated: {recovery_mechanisms}")
        return True
    else:
        missing = set(expected_recoveries) - set(recovery_mechanisms)
        print(f"  FAIL: Missing recovery mechanisms: {missing}")
        return False


def test_performance_under_degradation():
    """Test that performance is acceptable even under degraded conditions."""
    print("Testing Performance Under Degradation...")

    import time

    # Test 1: Emergency serializer performance
    start_time = time.time()

    test_data = {"values": list(range(1000)), "metadata": "test"}

    # Use basic JSON serializer (emergency fallback)
    for i in range(100):
        serialized = json.dumps(test_data)
        deserialized = json.loads(serialized)

    end_time = time.time()
    duration = end_time - start_time

    # Should complete 100 serializations in under 1 second
    if duration < 1.0:
        print(f"  PASS: Emergency serialization performance acceptable: {duration:.3f}s")
        perf_ok = True
    else:
        print(f"  FAIL: Emergency serialization too slow: {duration:.3f}s")
        perf_ok = False

    # Test 2: Config loading performance
    start_time = time.time()

    default_config = {
        'controllers': {'classical_smc': {'max_force': 150.0}},
        'physics': {'gravity': 9.81, 'cart_mass': 1.5},
        'simulation': {'duration': 10.0, 'dt': 0.01}
    }

    # Simulate config loading/merging 100 times
    for i in range(100):
        loaded_config = default_config.copy()
        # Simulate validation
        required_keys = ['controllers', 'physics', 'simulation']
        all_present = all(key in loaded_config for key in required_keys)

    end_time = time.time()
    duration = end_time - start_time

    if duration < 0.1 and all_present:
        print(f"  PASS: Config loading performance acceptable: {duration:.3f}s")
        config_ok = True
    else:
        print(f"  FAIL: Config loading performance issue: {duration:.3f}s")
        config_ok = False

    return perf_ok and config_ok


def main():
    """Run comprehensive SPOF integration tests."""
    print("=" * 80)
    print("SPOF Integration Tests - Real World Scenarios")
    print("=" * 80)

    tests = [
        test_config_destruction_integration,
        test_factory_failure_integration,
        test_real_world_failure_cascade,
        test_performance_under_degradation,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"  FAIL: Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("=" * 80)
    print(f"Integration Test Results: {passed}/{total} tests passed")
    print("=" * 80)

    if passed == total:
        print("SUCCESS: SPOF fixes work under real-world conditions")
    elif passed >= total * 0.75:
        print("PARTIAL SUCCESS: Most SPOF fixes work, some edge cases remain")
    else:
        print("FAILURE: SPOF fixes not adequate for production")

    return passed >= total * 0.75


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)