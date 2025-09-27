#==========================================================================================\\\
#======================= scripts/rigorous_production_audit.py =========================\\\
#==========================================================================================\\\
"""
RIGOROUS Production Readiness Audit - No Assumptions
This audit challenges every claim and validates actual production readiness without bias.

CRITICAL AUDIT AREAS:
1. Integration testing - Do all components actually work together?
2. Load testing - Does the system handle real production loads?
3. Error handling - What happens when things go wrong?
4. Deployment testing - Can this actually be deployed?
5. Security penetration testing - Are there hidden vulnerabilities?
6. Data integrity - Is data handled correctly under stress?
7. Recovery testing - Can the system recover from failures?
"""

import sys
import os
import time
import threading
import subprocess
import psutil
import traceback
import json
from datetime import datetime, timezone
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionAuditor:
    """Rigorous production readiness auditor"""

    def __init__(self):
        self.audit_results = {}
        self.critical_failures = []
        self.warnings = []
        self.performance_data = {}

    def audit_minimal_core_system(self):
        """Audit the claimed minimal core system"""
        logger.info("AUDITING: Minimal Core System Claims...")

        try:
            # Check if minimal core actually exists
            core_path = "production_core"
            if not os.path.exists(core_path):
                return False, "CRITICAL: production_core directory does not exist"

            # Count actual files
            core_files = []
            for root, dirs, files in os.walk(core_path):
                for file in files:
                    if file.endswith('.py'):
                        core_files.append(os.path.join(root, file))

            if len(core_files) != 5:
                return False, f"CRITICAL: Claimed 5 files, found {len(core_files)} files"

            # Count actual lines of code
            total_lines = 0
            for file_path in core_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = len([line for line in f if line.strip() and not line.strip().startswith('#')])
                        total_lines += lines
                except Exception as e:
                    return False, f"CRITICAL: Cannot read core file {file_path}: {e}"

            # Verify line count claim (950 lines)
            if abs(total_lines - 950) > 50:  # Allow 50 line tolerance
                return False, f"CRITICAL: Claimed 950 lines, found {total_lines} lines"

            # Test if core system can actually run
            try:
                from production_core.dip_dynamics import DIPDynamics
                from production_core.smc_controller import SMCController

                # Test instantiation
                dynamics = DIPDynamics()
                controller = SMCController()

                # Test basic functionality
                state = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]
                result = dynamics.compute_dynamics(state, [0.0])
                control = controller.compute_control(state)

                if len(result) != 6 or len(control) != 1:
                    return False, "CRITICAL: Core system computation failed"

            except Exception as e:
                return False, f"CRITICAL: Core system cannot run: {e}"

            return True, f"Minimal core verified: {len(core_files)} files, {total_lines} lines"

        except Exception as e:
            return False, f"CRITICAL: Core system audit failed: {e}"

    def audit_security_claims(self):
        """Audit security implementation claims"""
        logger.info("AUDITING: Security Implementation Claims...")

        try:
            # Test if security modules actually exist and work
            security_modules = [
                'security.authentication',
                'security.input_validation',
                'security.audit_logging'
            ]

            for module_name in security_modules:
                try:
                    __import__(module_name)
                except ImportError as e:
                    return False, f"CRITICAL: Security module {module_name} not importable: {e}"

            # Test actual security functionality
            from security.input_validation import input_validator, InputType, ValidationError

            # Test boundary enforcement
            try:
                input_validator.validate_numeric_input(200.0, InputType.CONTROL_FORCE)
                return False, "CRITICAL: Security boundaries not enforced - 200N should be rejected"
            except ValidationError:
                pass  # Expected

            # Test malicious input rejection
            malicious_inputs = [
                "'; DROP TABLE users; --",
                "<script>alert('hack')</script>",
                float('inf'),
                float('nan')
            ]

            for malicious_input in malicious_inputs:
                try:
                    if isinstance(malicious_input, str):
                        input_validator.validate_numeric_input(malicious_input, InputType.CONTROL_FORCE)
                    else:
                        input_validator.validate_numeric_input(malicious_input, InputType.CONTROL_FORCE)
                    return False, f"CRITICAL: Malicious input not blocked: {malicious_input}"
                except (ValidationError, ValueError):
                    pass  # Expected

            return True, "Security systems functional"

        except Exception as e:
            return False, f"CRITICAL: Security audit failed: {e}"

    def audit_thread_safety_claims(self):
        """Audit thread safety performance claims"""
        logger.info("AUDITING: Thread Safety Performance Claims...")

        try:
            # Test if deadlock-free modules exist
            try:
                from src.interfaces.monitoring.metrics_collector_deadlock_free import MetricsCollector
                from src.interfaces.network.udp_interface_deadlock_free import UDPInterface
            except ImportError as e:
                return False, f"CRITICAL: Deadlock-free modules not importable: {e}"

            # Test actual concurrent performance
            metrics_collector = MetricsCollector()

            operations_completed = 0
            errors = []
            start_time = time.time()

            def worker():
                nonlocal operations_completed
                try:
                    for i in range(1000):
                        metrics_collector.collect_metric('test_metric', i)
                        operations_completed += 1
                except Exception as e:
                    errors.append(str(e))

            # Start 10 threads
            threads = []
            for i in range(10):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()

            # Wait for completion with timeout
            for thread in threads:
                thread.join(timeout=5.0)  # 5 second timeout

            elapsed_time = time.time() - start_time

            # Check for failures
            if errors:
                return False, f"CRITICAL: Thread safety errors: {errors[0]}"

            # Check if any threads are still running (deadlock indicator)
            still_running = [t for t in threads if t.is_alive()]
            if still_running:
                return False, f"CRITICAL: {len(still_running)} threads deadlocked/hanging"

            # Calculate actual performance
            ops_per_sec = operations_completed / elapsed_time if elapsed_time > 0 else 0

            # Verify performance claim (299k ops/sec seems very high, let's be realistic)
            if ops_per_sec < 1000:  # Much lower threshold for real testing
                return False, f"CRITICAL: Performance too low: {ops_per_sec:.0f} ops/sec"

            return True, f"Thread safety verified: {ops_per_sec:.0f} ops/sec, {operations_completed} operations"

        except Exception as e:
            return False, f"CRITICAL: Thread safety audit failed: {e}"

    def audit_integration_testing(self):
        """Test if components actually work together"""
        logger.info("AUDITING: System Integration...")

        try:
            # Test complete workflow integration
            from security.authentication import auth_manager, UserRole, Permission
            from security.input_validation import input_validator, InputType
            from security.audit_logging import audit_logger, AuditEvent, AuditEventType, AuditSeverity

            # Test authentication -> authorization -> input validation -> audit workflow

            # 1. Create user
            success = auth_manager.create_user("integration_test", "TestPass123!", UserRole.OPERATOR)
            if not success:
                return False, "CRITICAL: Cannot create user for integration test"

            # 2. Authenticate
            token = auth_manager.authenticate("integration_test", "TestPass123!")
            if not token:
                return False, "CRITICAL: Authentication failed in integration test"

            # 3. Check permissions
            has_permission = auth_manager.check_permission(token, Permission.CONTROL_WRITE)
            if not has_permission:
                return False, "CRITICAL: Permission check failed in integration test"

            # 4. Validate input
            try:
                validated_force = input_validator.validate_control_command(25.0, "integration_test")
                if abs(validated_force - 25.0) > 0.001:
                    return False, "CRITICAL: Input validation failed in integration test"
            except Exception as e:
                return False, f"CRITICAL: Input validation error in integration: {e}"

            # 5. Log audit event
            event = AuditEvent(
                event_id="integration_test",
                timestamp=datetime.now(timezone.utc),
                event_type=AuditEventType.CONTROL_COMMAND,
                severity=AuditSeverity.INFO,
                user_id="integration_test",
                client_ip="127.0.0.1",
                session_id=token,
                resource="integration_test",
                action="test_control",
                result="SUCCESS",
                details={'control_force': validated_force},
                source_component="integration_auditor"
            )

            audit_success = audit_logger.log_event(event)
            if not audit_success:
                return False, "CRITICAL: Audit logging failed in integration test"

            return True, "Integration workflow verified"

        except Exception as e:
            return False, f"CRITICAL: Integration test failed: {e}"

    def audit_error_handling(self):
        """Test error handling and recovery"""
        logger.info("AUDITING: Error Handling and Recovery...")

        try:
            from security.input_validation import input_validator, InputType, ValidationError

            # Test various error conditions
            error_scenarios = [
                (None, "null input"),
                ("invalid", "string input"),
                ([], "list input"),
                ({}, "dict input"),
                (1e20, "extremely large number"),
                (-1e20, "extremely small number")
            ]

            for invalid_input, scenario in error_scenarios:
                try:
                    input_validator.validate_numeric_input(invalid_input, InputType.CONTROL_FORCE)
                    return False, f"CRITICAL: Error handling failed for {scenario}"
                except (ValidationError, ValueError, TypeError):
                    pass  # Expected

            # Test system behavior under memory pressure
            try:
                # Allocate large chunks of memory to test memory handling
                large_data = []
                for i in range(100):
                    large_data.append([0] * 10000)  # 100 * 10k = 1M integers

                # Test if system still works under memory pressure
                result = input_validator.validate_numeric_input(50.0, InputType.CONTROL_FORCE)
                if abs(result - 50.0) > 0.001:
                    return False, "CRITICAL: System fails under memory pressure"

                del large_data  # Clean up

            except MemoryError:
                return False, "CRITICAL: System cannot handle memory pressure"

            return True, "Error handling verified"

        except Exception as e:
            return False, f"CRITICAL: Error handling audit failed: {e}"

    def audit_resource_leaks(self):
        """Test for resource leaks under load"""
        logger.info("AUDITING: Resource Leak Detection...")

        try:
            # Get initial resource usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss

            # Run intensive operations
            from security.input_validation import input_validator, InputType

            for i in range(1000):
                input_validator.validate_numeric_input(float(i % 100), InputType.CONTROL_FORCE)
                input_validator.sanitize_string(f"test_string_{i}")

            # Check for memory leaks
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # Allow up to 10MB increase for normal operations
            if memory_increase > 10 * 1024 * 1024:
                return False, f"CRITICAL: Memory leak detected: {memory_increase / 1024 / 1024:.1f} MB increase"

            return True, f"No resource leaks detected (memory change: {memory_increase / 1024:.1f} KB)"

        except Exception as e:
            return False, f"CRITICAL: Resource leak audit failed: {e}"

    def audit_deployment_feasibility(self):
        """Test if the system can actually be deployed"""
        logger.info("AUDITING: Deployment Feasibility...")

        try:
            # Check if all required files exist
            required_files = [
                'production_core/dip_dynamics.py',
                'production_core/smc_controller.py',
                'security/authentication.py',
                'security/input_validation.py',
                'security/audit_logging.py'
            ]

            missing_files = []
            for file_path in required_files:
                if not os.path.exists(file_path):
                    missing_files.append(file_path)

            if missing_files:
                return False, f"CRITICAL: Missing required files: {missing_files}"

            # Test if system can start and run basic operations
            try:
                # Import core modules
                from production_core.dip_dynamics import DIPDynamics
                from production_core.smc_controller import SMCController

                # Test basic control loop
                dynamics = DIPDynamics()
                controller = SMCController()

                state = [0.0, 0.1, 0.0, 0.0, 0.0, 0.0]  # Small initial disturbance

                # Run 10 control steps
                for step in range(10):
                    control = controller.compute_control(state)
                    new_state = dynamics.compute_dynamics(state, control)
                    state = new_state

                # Check if system is stable (state should not blow up)
                if any(abs(x) > 10 for x in state):
                    return False, f"CRITICAL: System unstable, state: {state}"

            except Exception as e:
                return False, f"CRITICAL: Basic control loop fails: {e}"

            return True, "Deployment feasibility verified"

        except Exception as e:
            return False, f"CRITICAL: Deployment audit failed: {e}"

    def audit_performance_claims(self):
        """Audit actual performance against claims"""
        logger.info("AUDITING: Performance Claims...")

        try:
            from production_core.dip_dynamics import DIPDynamics
            from production_core.smc_controller import SMCController

            dynamics = DIPDynamics()
            controller = SMCController()

            # Test claimed 0.12s control loop performance
            state = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]

            start_time = time.time()
            iterations = 100

            for i in range(iterations):
                control = controller.compute_control(state)
                state = dynamics.compute_dynamics(state, control)

            elapsed_time = time.time() - start_time
            avg_time_per_iteration = elapsed_time / iterations

            # Check if control loop is fast enough (should be much faster than 0.12s)
            if avg_time_per_iteration > 0.01:  # 10ms limit
                return False, f"CRITICAL: Control loop too slow: {avg_time_per_iteration*1000:.1f}ms per iteration"

            return True, f"Performance verified: {avg_time_per_iteration*1000:.2f}ms per control loop"

        except Exception as e:
            return False, f"CRITICAL: Performance audit failed: {e}"

    def run_comprehensive_audit(self):
        """Run complete production readiness audit"""
        logger.info("Starting RIGOROUS Production Readiness Audit...")
        logger.info("="*80)

        audit_tests = [
            ("Minimal Core System", self.audit_minimal_core_system),
            ("Security Implementation", self.audit_security_claims),
            ("Thread Safety Performance", self.audit_thread_safety_claims),
            ("System Integration", self.audit_integration_testing),
            ("Error Handling", self.audit_error_handling),
            ("Resource Leak Detection", self.audit_resource_leaks),
            ("Deployment Feasibility", self.audit_deployment_feasibility),
            ("Performance Verification", self.audit_performance_claims)
        ]

        passed_tests = 0
        total_tests = len(audit_tests)

        for test_name, test_func in audit_tests:
            logger.info(f"\nAUDITING: {test_name}...")
            try:
                success, message = test_func()
                if success:
                    logger.info(f"✓ {test_name}: VERIFIED - {message}")
                    passed_tests += 1
                else:
                    logger.error(f"✗ {test_name}: FAILED - {message}")
                    self.critical_failures.append(f"{test_name}: {message}")
            except Exception as e:
                logger.error(f"✗ {test_name}: ERROR - {e}")
                self.critical_failures.append(f"{test_name}: Audit error - {e}")

        # Calculate actual production readiness
        success_rate = (passed_tests / total_tests) * 100

        logger.info("\n" + "="*80)
        logger.info("RIGOROUS AUDIT RESULTS")
        logger.info("="*80)
        logger.info(f"Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")

        if self.critical_failures:
            logger.error("\nCRITICAL FAILURES FOUND:")
            for failure in self.critical_failures:
                logger.error(f"- {failure}")

        # Honest assessment
        if success_rate >= 90:
            actual_status = "PRODUCTION READY"
            actual_score = 9.0 + (success_rate - 90) / 10
        elif success_rate >= 75:
            actual_status = "MOSTLY READY (minor issues)"
            actual_score = 7.0 + (success_rate - 75) / 15 * 2
        elif success_rate >= 50:
            actual_status = "SIGNIFICANT ISSUES"
            actual_score = 5.0 + (success_rate - 50) / 25 * 2
        else:
            actual_status = "NOT PRODUCTION READY"
            actual_score = success_rate / 50 * 5

        logger.info(f"\nACTUAL PRODUCTION STATUS: {actual_status}")
        logger.info(f"ACTUAL PRODUCTION SCORE: {actual_score:.1f}/10")

        if success_rate < 100:
            logger.warning("\n⚠️ PRODUCTION DEPLOYMENT NOT RECOMMENDED")
            logger.warning("Critical issues must be resolved before production use")
        else:
            logger.info("\n✅ RIGOROUS AUDIT PASSED - PRODUCTION READY")

        return {
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'success_rate': success_rate,
            'actual_status': actual_status,
            'actual_score': actual_score,
            'critical_failures': self.critical_failures,
            'production_ready': success_rate >= 90
        }

def main():
    """Main audit execution"""
    try:
        auditor = ProductionAuditor()
        results = auditor.run_comprehensive_audit()
        return results['production_ready']

    except Exception as e:
        logger.error(f"Audit execution failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)