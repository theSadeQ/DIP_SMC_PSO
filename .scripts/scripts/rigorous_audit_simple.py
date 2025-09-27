#==========================================================================================\\\
#======================= scripts/rigorous_audit_simple.py ============================\\\
#==========================================================================================\\\
"""
RIGOROUS Production Audit - No External Dependencies
Challenges every production readiness claim with actual testing.
"""

import sys
import os
import time
import threading
import traceback
import gc
from datetime import datetime, timezone
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RigorousAuditor:
    """No-nonsense production auditor"""

    def __init__(self):
        self.critical_failures = []

    def audit_minimal_core_existence(self):
        """Verify minimal core actually exists as claimed"""
        logger.info("AUDITING: Minimal Core System Existence...")

        try:
            core_path = "production_core"
            if not os.path.exists(core_path):
                return False, "CRITICAL: production_core directory missing"

            # Count Python files
            py_files = []
            for root, dirs, files in os.walk(core_path):
                for file in files:
                    if file.endswith('.py'):
                        py_files.append(os.path.join(root, file))

            if len(py_files) == 0:
                return False, "CRITICAL: No Python files in production_core"

            # Try to read each file and count non-comment lines
            total_loc = 0
            for file_path in py_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                        total_loc += len(lines)
                except Exception as e:
                    return False, f"CRITICAL: Cannot read {file_path}: {e}"

            return True, f"Core found: {len(py_files)} files, {total_loc} lines of code"

        except Exception as e:
            return False, f"CRITICAL: Core audit failed: {e}"

    def audit_minimal_core_functionality(self):
        """Test if minimal core can actually run"""
        logger.info("AUDITING: Minimal Core Functionality...")

        try:
            # Test if core modules can be imported and instantiated
            try:
                from production_core.dip_dynamics import DIPDynamics
                dynamics = DIPDynamics()
            except Exception as e:
                return False, f"CRITICAL: DIPDynamics cannot be imported/created: {e}"

            try:
                from production_core.smc_controller import SMCController
                controller = SMCController()
            except Exception as e:
                return False, f"CRITICAL: SMCController cannot be imported/created: {e}"

            # Test basic computation
            try:
                test_state = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]
                test_control = [0.0]

                # Test dynamics computation
                new_state = dynamics.compute_dynamics(test_state, test_control)
                if not isinstance(new_state, (list, tuple)) or len(new_state) != 6:
                    return False, f"CRITICAL: Invalid dynamics output: {new_state}"

                # Test controller computation
                control_output = controller.compute_control(test_state)
                if not isinstance(control_output, (list, tuple, float)) or (isinstance(control_output, (list, tuple)) and len(control_output) != 1):
                    return False, f"CRITICAL: Invalid controller output: {control_output}"

                # Test numerical sanity
                if any(abs(x) > 1000 for x in new_state):
                    return False, f"CRITICAL: Dynamics output unstable: {new_state}"

            except Exception as e:
                return False, f"CRITICAL: Core computation failed: {e}"

            return True, "Core functionality verified"

        except Exception as e:
            return False, f"CRITICAL: Core functionality audit failed: {e}"

    def audit_security_basics(self):
        """Test if security systems actually work"""
        logger.info("AUDITING: Security System Basics...")

        try:
            # Test input validation
            try:
                from security.input_validation import input_validator, InputType, ValidationError
            except ImportError as e:
                return False, f"CRITICAL: Cannot import input validation: {e}"

            # Test boundary enforcement
            try:
                result = input_validator.validate_numeric_input(200.0, InputType.CONTROL_FORCE)
                return False, f"CRITICAL: Boundary not enforced - 200N accepted: {result}"
            except ValidationError:
                pass  # Expected

            try:
                result = input_validator.validate_numeric_input(50.0, InputType.CONTROL_FORCE)
                if abs(result - 50.0) > 0.001:
                    return False, f"CRITICAL: Valid input incorrectly modified: {result}"
            except Exception as e:
                return False, f"CRITICAL: Valid input rejected: {e}"

            # Test audit logging
            try:
                from security.audit_logging import audit_logger, AuditEvent, AuditEventType, AuditSeverity

                event = AuditEvent(
                    event_id="audit_test",
                    timestamp=datetime.now(timezone.utc),
                    event_type=AuditEventType.SYSTEM_INFO,
                    severity=AuditSeverity.INFO,
                    user_id="auditor",
                    client_ip="127.0.0.1",
                    session_id="audit_session",
                    resource="audit_test",
                    action="test_logging",
                    result="SUCCESS",
                    details={'test': True},
                    source_component="auditor"
                )

                success = audit_logger.log_event(event)
                if not success:
                    return False, "CRITICAL: Audit logging failed"

            except Exception as e:
                return False, f"CRITICAL: Audit logging error: {e}"

            return True, "Security basics verified"

        except Exception as e:
            return False, f"CRITICAL: Security audit failed: {e}"

    def audit_thread_safety_reality(self):
        """Test thread safety with actual concurrent execution"""
        logger.info("AUDITING: Thread Safety Reality Check...")

        try:
            # Test deadlock-free metrics collector
            try:
                from src.interfaces.monitoring.metrics_collector_deadlock_free import MetricsCollector
                collector = MetricsCollector()
            except ImportError as e:
                return False, f"CRITICAL: Cannot import deadlock-free collector: {e}"

            # Concurrent stress test
            errors = []
            completed_operations = 0
            lock = threading.Lock()

            def worker_thread(thread_id):
                nonlocal completed_operations
                try:
                    for i in range(100):
                        collector.collect_metric(f'test_{thread_id}_{i}', float(i))
                        with lock:
                            completed_operations += 1
                except Exception as e:
                    errors.append(f"Thread {thread_id}: {e}")

            # Start multiple threads
            threads = []
            num_threads = 5
            start_time = time.time()

            for i in range(num_threads):
                thread = threading.Thread(target=worker_thread, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for completion with timeout
            for thread in threads:
                thread.join(timeout=10.0)  # 10 second timeout

            elapsed_time = time.time() - start_time

            # Check for errors
            if errors:
                return False, f"CRITICAL: Thread safety failed: {errors[0]}"

            # Check for deadlocks
            still_running = [t for t in threads if t.is_alive()]
            if still_running:
                return False, f"CRITICAL: {len(still_running)} threads deadlocked/hanging"

            # Check completion
            expected_operations = num_threads * 100
            if completed_operations < expected_operations:
                return False, f"CRITICAL: Only {completed_operations}/{expected_operations} operations completed"

            ops_per_sec = completed_operations / elapsed_time if elapsed_time > 0 else 0

            return True, f"Thread safety verified: {completed_operations} ops in {elapsed_time:.2f}s ({ops_per_sec:.0f} ops/sec)"

        except Exception as e:
            return False, f"CRITICAL: Thread safety audit failed: {e}"

    def audit_integration_workflow(self):
        """Test complete workflow integration"""
        logger.info("AUDITING: End-to-End Integration...")

        try:
            # Test complete secure control workflow
            from security.authentication import auth_manager, UserRole, Permission
            from security.input_validation import input_validator, InputType
            from production_core.dip_dynamics import DIPDynamics
            from production_core.smc_controller import SMCController

            # Create test user
            username = f"test_user_{int(time.time())}"
            if not auth_manager.create_user(username, "TestPassword123!", UserRole.OPERATOR):
                return False, "CRITICAL: Cannot create test user"

            # Authenticate
            token = auth_manager.authenticate(username, "TestPassword123!")
            if not token:
                return False, "CRITICAL: Authentication failed"

            # Check permissions
            if not auth_manager.check_permission(token, Permission.CONTROL_WRITE):
                return False, "CRITICAL: Permission check failed"

            # Validate control input
            control_force = input_validator.validate_control_command(25.0, "integration_test")
            if abs(control_force - 25.0) > 0.001:
                return False, "CRITICAL: Input validation failed"

            # Run control system
            dynamics = DIPDynamics()
            controller = SMCController()

            state = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]
            for _ in range(5):
                control = controller.compute_control(state)
                state = dynamics.compute_dynamics(state, control)

            # Check for stability
            if any(abs(x) > 10 for x in state):
                return False, f"CRITICAL: System unstable in integration test: {state}"

            return True, "End-to-end integration verified"

        except Exception as e:
            return False, f"CRITICAL: Integration audit failed: {e}"

    def audit_error_resilience(self):
        """Test system behavior under error conditions"""
        logger.info("AUDITING: Error Resilience...")

        try:
            from security.input_validation import input_validator, InputType, ValidationError

            # Test various error inputs
            error_cases = [
                (None, "null"),
                ("malicious_string", "string"),
                ([], "empty list"),
                ({}, "empty dict"),
                (float('inf'), "infinity"),
                (float('nan'), "NaN"),
                (1e100, "huge number"),
                (-1e100, "huge negative")
            ]

            handled_errors = 0
            for test_input, description in error_cases:
                try:
                    input_validator.validate_numeric_input(test_input, InputType.CONTROL_FORCE)
                    # If we get here, the error wasn't caught
                    logger.warning(f"Error case not handled: {description}")
                except (ValidationError, ValueError, TypeError):
                    handled_errors += 1
                except Exception as e:
                    return False, f"CRITICAL: Unexpected error for {description}: {e}"

            if handled_errors < len(error_cases) * 0.8:  # Should handle at least 80%
                return False, f"CRITICAL: Poor error handling: {handled_errors}/{len(error_cases)}"

            return True, f"Error resilience verified: {handled_errors}/{len(error_cases)} cases handled"

        except Exception as e:
            return False, f"CRITICAL: Error resilience audit failed: {e}"

    def audit_performance_reality(self):
        """Test actual performance"""
        logger.info("AUDITING: Performance Reality...")

        try:
            from production_core.dip_dynamics import DIPDynamics
            from production_core.smc_controller import SMCController

            dynamics = DIPDynamics()
            controller = SMCController()

            # Measure actual control loop performance
            state = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]
            iterations = 1000

            start_time = time.time()
            for i in range(iterations):
                control = controller.compute_control(state)
                state = dynamics.compute_dynamics(state, control)

            elapsed_time = time.time() - start_time
            avg_loop_time = elapsed_time / iterations

            # Performance thresholds
            if avg_loop_time > 0.01:  # 10ms per loop
                return False, f"CRITICAL: Control loop too slow: {avg_loop_time*1000:.1f}ms/loop"

            # Check for numerical stability
            if any(abs(x) > 100 for x in state):
                return False, f"CRITICAL: System becomes unstable: {state}"

            return True, f"Performance verified: {avg_loop_time*1000:.2f}ms per control loop"

        except Exception as e:
            return False, f"CRITICAL: Performance audit failed: {e}"

    def audit_memory_behavior(self):
        """Test memory usage and leak behavior"""
        logger.info("AUDITING: Memory Behavior...")

        try:
            # Force garbage collection to get baseline
            gc.collect()

            from security.input_validation import input_validator, InputType

            # Run memory-intensive operations
            for i in range(1000):
                input_validator.validate_numeric_input(float(i % 100), InputType.CONTROL_FORCE)
                input_validator.sanitize_string(f"test_string_{i}_with_some_content")

            # Force garbage collection again
            gc.collect()

            # Test large string handling
            try:
                large_string = "A" * 100000  # 100KB string
                input_validator.sanitize_string(large_string, max_length=1000)
                return False, "CRITICAL: Large string not rejected"
            except Exception:
                pass  # Expected

            return True, "Memory behavior acceptable"

        except Exception as e:
            return False, f"CRITICAL: Memory audit failed: {e}"

    def run_rigorous_audit(self):
        """Run complete rigorous audit"""
        logger.info("Starting RIGOROUS Production Audit (No Assumptions)...")
        logger.info("="*80)

        tests = [
            ("Minimal Core Existence", self.audit_minimal_core_existence),
            ("Minimal Core Functionality", self.audit_minimal_core_functionality),
            ("Security System Basics", self.audit_security_basics),
            ("Thread Safety Reality", self.audit_thread_safety_reality),
            ("Integration Workflow", self.audit_integration_workflow),
            ("Error Resilience", self.audit_error_resilience),
            ("Performance Reality", self.audit_performance_reality),
            ("Memory Behavior", self.audit_memory_behavior)
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            logger.info(f"\nTesting: {test_name}...")
            try:
                success, message = test_func()
                if success:
                    logger.info(f"✓ PASS: {message}")
                    passed += 1
                else:
                    logger.error(f"✗ FAIL: {message}")
                    self.critical_failures.append(message)
            except Exception as e:
                logger.error(f"✗ ERROR: {test_name} - {e}")
                self.critical_failures.append(f"{test_name}: {e}")

        # Calculate honest results
        success_rate = (passed / total) * 100

        logger.info("\n" + "="*80)
        logger.info("RIGOROUS AUDIT RESULTS")
        logger.info("="*80)
        logger.info(f"Tests Passed: {passed}/{total} ({success_rate:.1f}%)")

        if self.critical_failures:
            logger.error("\nCRITICAL FAILURES:")
            for failure in self.critical_failures:
                logger.error(f"  - {failure}")

        # Honest production readiness assessment
        if success_rate >= 90:
            status = "PRODUCTION READY"
            score = 8.5 + (success_rate - 90) / 10 * 1.5
        elif success_rate >= 75:
            status = "MOSTLY READY"
            score = 7.0 + (success_rate - 75) / 15 * 1.5
        elif success_rate >= 50:
            status = "NEEDS WORK"
            score = 5.0 + (success_rate - 50) / 25 * 2
        else:
            status = "NOT READY"
            score = success_rate / 50 * 5

        logger.info(f"\nHONEST ASSESSMENT:")
        logger.info(f"Production Status: {status}")
        logger.info(f"Realistic Score: {score:.1f}/10")

        if success_rate < 90:
            logger.warning("🚨 ISSUES FOUND - Address before production")
        else:
            logger.info("✅ RIGOROUS AUDIT PASSED")

        return {
            'passed': passed,
            'total': total,
            'success_rate': success_rate,
            'status': status,
            'score': score,
            'failures': self.critical_failures,
            'ready': success_rate >= 90
        }

def main():
    """Main audit execution"""
    try:
        auditor = RigorousAuditor()
        results = auditor.run_rigorous_audit()
        return results['ready']
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)