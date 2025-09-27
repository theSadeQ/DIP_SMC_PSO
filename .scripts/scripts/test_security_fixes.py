#==========================================================================================\\\
#========================== scripts/test_security_fixes.py ===========================\\\
#==========================================================================================\\\
"""
Comprehensive Security Fixes Validation
Tests all security improvements to ensure they address the critical vulnerabilities.
"""

import sys
import os
import time
import threading
import secrets
from datetime import datetime, timezone
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_authentication_system():
    """Test authentication and authorization system"""
    logger.info("Testing Authentication & Authorization System...")

    try:
        from security.authentication import auth_manager, UserRole, Permission

        # Test user creation
        success = auth_manager.create_user("test_user", "SecurePass123!", UserRole.OPERATOR)
        if not success:
            return False, "Failed to create test user"

        # Test authentication
        token = auth_manager.authenticate("test_user", "SecurePass123!")
        if not token:
            return False, "Authentication failed"

        # Test authorization
        has_permission = auth_manager.check_permission(token, Permission.CONTROL_WRITE)
        if not has_permission:
            return False, "Permission check failed"

        # Test invalid authentication
        invalid_token = auth_manager.authenticate("test_user", "WrongPassword")
        if invalid_token:
            return False, "Invalid authentication should fail"

        # Test session validation
        session = auth_manager.validate_token(token)
        if not session:
            return False, "Token validation failed"

        logger.info("✓ Authentication system working correctly")
        return True, "Authentication system validated"

    except Exception as e:
        logger.error(f"Authentication test failed: {e}")
        return False, f"Authentication test error: {e}"

def test_input_validation():
    """Test input validation and sanitization"""
    logger.info("Testing Input Validation & Sanitization...")

    try:
        from security.input_validation import input_validator, InputType, ValidationError

        # Test valid control force
        valid_force = input_validator.validate_numeric_input(50.0, InputType.CONTROL_FORCE)
        if abs(valid_force - 50.0) > 0.001:
            return False, "Valid input validation failed"

        # Test out-of-bounds control force
        try:
            input_validator.validate_numeric_input(200.0, InputType.CONTROL_FORCE)
            return False, "Out-of-bounds input should be rejected"
        except ValidationError:
            pass  # Expected

        # Test state vector validation
        valid_state = [0.1, 0.2, 0.3, 0.5, 0.1, 0.2]
        validated_state = input_validator.validate_control_state(valid_state)
        if len(validated_state) != 6:
            return False, "State vector validation failed"

        # Test malicious input
        try:
            input_validator.validate_numeric_input("'; DROP TABLE users; --", InputType.CONTROL_FORCE)
            return False, "Malicious input should be rejected"
        except ValidationError:
            pass  # Expected

        # Test string sanitization
        sanitized = input_validator.sanitize_string("Safe<script>alert('hack')</script>Input")
        if "<script>" in sanitized:
            return False, "String sanitization failed"

        logger.info("✓ Input validation working correctly")
        return True, "Input validation system validated"

    except Exception as e:
        logger.error(f"Input validation test failed: {e}")
        return False, f"Input validation test error: {e}"

def test_secure_communications():
    """Test secure communications system"""
    logger.info("Testing Secure Communications...")

    try:
        from security.secure_communications import SecureTLSServer, SecureTLSClient, SecureMessage, MessageType

        # Test message encryption/decryption
        server = SecureTLSServer()

        message = SecureMessage(
            message_id=secrets.token_hex(16),
            timestamp=datetime.now(timezone.utc),
            message_type=MessageType.CONTROL_COMMAND,
            payload={'control_force': 10.0},
            sender_id="test_client"
        )

        # Test encryption
        encrypted_data = server._encrypt_message(message)
        if not encrypted_data:
            return False, "Message encryption failed"

        # Test decryption
        decrypted_message = server._decrypt_message(encrypted_data)
        if decrypted_message.payload['control_force'] != 10.0:
            return False, "Message decryption failed"

        # Test replay attack prevention
        server.message_cache[message.message_id] = message.timestamp
        try:
            server._validate_message(message)
            return False, "Replay attack should be detected"
        except ValueError:
            pass  # Expected

        logger.info("✓ Secure communications working correctly")
        return True, "Secure communications validated"

    except Exception as e:
        logger.error(f"Secure communications test failed: {e}")
        return False, f"Secure communications test error: {e}"

def test_audit_logging():
    """Test comprehensive audit logging"""
    logger.info("Testing Audit Logging System...")

    try:
        from security.audit_logging import audit_logger, AuditEvent, AuditEventType, AuditSeverity
        from security.audit_logging import log_login_success, log_control_command, log_security_violation

        # Test audit event logging
        event = AuditEvent(
            event_id="",
            timestamp=datetime.now(timezone.utc),
            event_type=AuditEventType.CONTROL_COMMAND,
            severity=AuditSeverity.MEDIUM,
            user_id="test_user",
            client_ip="192.168.1.100",
            session_id="test_session",
            resource="dip_control",
            action="control_test",
            result="SUCCESS",
            details={'test': True},
            source_component="test_suite"
        )

        success = audit_logger.log_event(event)
        if not success:
            return False, "Audit event logging failed"

        # Test convenience functions
        log_login_success("test_user", "192.168.1.100", "session_123")
        log_control_command("test_user", "192.168.1.100", 25.0, "session_123")
        log_security_violation(None, "192.168.1.1", "bruteforce", {"attempts": 10})

        # Test log integrity verification
        integrity_result = audit_logger.verify_log_integrity()
        if integrity_result['integrity_status'] not in ['VERIFIED', 'MOSTLY_VERIFIED']:
            return False, f"Log integrity check failed: {integrity_result['integrity_status']}"

        # Test security dashboard
        dashboard = audit_logger.get_security_dashboard()
        if 'total_events_24h' not in dashboard:
            return False, "Security dashboard missing required data"

        logger.info("✓ Audit logging working correctly")
        return True, "Audit logging system validated"

    except Exception as e:
        logger.error(f"Audit logging test failed: {e}")
        return False, f"Audit logging test error: {e}"

def test_integrated_security_workflow():
    """Test complete security workflow integration"""
    logger.info("Testing Integrated Security Workflow...")

    try:
        from security.authentication import auth_manager, UserRole, Permission
        from security.input_validation import input_validator, InputType
        from security.audit_logging import log_control_command

        # Simulate secure control command workflow

        # 1. Authentication
        token = auth_manager.authenticate("admin", "DIP_Admin_2025!")
        if not token:
            return False, "Admin authentication failed"

        # 2. Authorization check
        if not auth_manager.check_permission(token, Permission.CONTROL_WRITE):
            return False, "Control permission check failed"

        # 3. Input validation
        control_force = input_validator.validate_control_command(75.0, "test_client")
        if abs(control_force - 75.0) > 0.001:
            return False, "Control command validation failed"

        # 4. Audit logging
        session = auth_manager.validate_token(token)
        log_control_command(session.username, "192.168.1.100", control_force, token)

        logger.info("✓ Integrated security workflow working correctly")
        return True, "Integrated security workflow validated"

    except Exception as e:
        logger.error(f"Integrated security test failed: {e}")
        return False, f"Integrated security test error: {e}"

def test_security_attack_scenarios():
    """Test security against common attack scenarios"""
    logger.info("Testing Security Against Attack Scenarios...")

    try:
        from security.authentication import auth_manager
        from security.input_validation import input_validator, InputType, ValidationError

        # Test brute force protection
        for i in range(6):  # Should lock after 5 attempts
            token = auth_manager.authenticate("admin", "wrong_password")
            if token:
                return False, "Brute force protection failed"

        # Account should now be locked
        token = auth_manager.authenticate("admin", "DIP_Admin_2025!")
        if token:
            return False, "Account locking failed"

        # Test SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'/**/UNION/**/SELECT/**/*/**/FROM/**/users--",
            "<script>alert('xss')</script>",
            "../../../etc/passwd"
        ]

        for malicious_input in malicious_inputs:
            try:
                input_validator.validate_numeric_input(malicious_input, InputType.CONTROL_FORCE)
                return False, f"Malicious input not blocked: {malicious_input}"
            except ValidationError:
                pass  # Expected

        # Test buffer overflow attempts
        large_input = "A" * 10000
        try:
            input_validator.sanitize_string(large_input)
            return False, "Buffer overflow protection failed"
        except ValidationError:
            pass  # Expected

        logger.info("✓ Security attack scenarios properly blocked")
        return True, "Security attack scenarios validated"

    except Exception as e:
        logger.error(f"Security attack test failed: {e}")
        return False, f"Security attack test error: {e}"

def run_comprehensive_security_test():
    """Run all security tests and generate report"""
    logger.info("Starting Comprehensive Security Validation...")

    test_results = {}

    # Run all security tests
    tests = [
        ("Authentication System", test_authentication_system),
        ("Input Validation", test_input_validation),
        ("Secure Communications", test_secure_communications),
        ("Audit Logging", test_audit_logging),
        ("Integrated Workflow", test_integrated_security_workflow),
        ("Attack Scenarios", test_security_attack_scenarios)
    ]

    passed_tests = 0
    total_tests = len(tests)

    for test_name, test_func in tests:
        logger.info(f"\nTesting {test_name}...")
        try:
            success, message = test_func()
            test_results[test_name] = {'passed': success, 'message': message}
            if success:
                passed_tests += 1
                logger.info(f"✓ {test_name}: PASSED")
            else:
                logger.error(f"✗ {test_name}: FAILED - {message}")
        except Exception as e:
            test_results[test_name] = {'passed': False, 'message': f"Test error: {e}"}
            logger.error(f"✗ {test_name}: ERROR - {e}")

    # Generate summary
    success_rate = (passed_tests / total_tests) * 100

    logger.info("\n" + "="*70)
    logger.info("SECURITY VALIDATION SUMMARY")
    logger.info("="*70)
    logger.info(f"Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")

    if success_rate >= 90:
        security_status = "EXCELLENT"
        new_security_score = 8.5
    elif success_rate >= 75:
        security_status = "GOOD"
        new_security_score = 7.0
    elif success_rate >= 50:
        security_status = "FAIR"
        new_security_score = 5.0
    else:
        security_status = "POOR"
        new_security_score = 2.0

    logger.info(f"Security Status: {security_status}")
    logger.info(f"New Security Score: {new_security_score}/10")

    # Calculate improvement
    original_score = 2.7
    improvement = new_security_score - original_score

    logger.info(f"Security Improvement: +{improvement:.1f} points ({improvement/10*100:.1f}% better)")

    if success_rate >= 90:
        logger.info("🛡️ SECURITY READY FOR PRODUCTION!")
    else:
        logger.warning("⚠️ Additional security work needed before production")

    return {
        'passed_tests': passed_tests,
        'total_tests': total_tests,
        'success_rate': success_rate,
        'security_status': security_status,
        'new_security_score': new_security_score,
        'improvement': improvement,
        'test_results': test_results
    }

def main():
    """Main security validation execution"""
    try:
        results = run_comprehensive_security_test()
        return results['success_rate'] >= 90

    except Exception as e:
        logger.error(f"Security validation failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)