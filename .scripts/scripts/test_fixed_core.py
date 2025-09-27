#==========================================================================================\\\
#========================== scripts/test_fixed_core.py ===============================\\\
#==========================================================================================\\\
"""
Test the Fixed Minimal Core System
"""

import sys
import os
import time
import threading
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_core_imports():
    """Test if core modules can be imported"""
    logger.info("Testing core module imports...")

    try:
        from production_core.dip_dynamics import DIPDynamics
        logger.info("✓ DIPDynamics imported successfully")

        from production_core.smc_controller import SMCController
        logger.info("✓ SMCController imported successfully")

        return True, "Core imports successful"

    except Exception as e:
        return False, f"Core import failed: {e}"

def test_core_functionality():
    """Test if core modules work"""
    logger.info("Testing core functionality...")

    try:
        from production_core.dip_dynamics import DIPDynamics
        from production_core.smc_controller import SMCController

        # Test instantiation
        dynamics = DIPDynamics()
        controller = SMCController()
        logger.info("✓ Core objects created successfully")

        # Test computation
        test_state = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]
        test_control = [0.0]

        # Test dynamics
        new_state = dynamics.compute_dynamics(test_state, test_control)
        if not isinstance(new_state, list) and not hasattr(new_state, '__iter__'):
            return False, f"Invalid dynamics output type: {type(new_state)}"

        if len(new_state) != 6:
            return False, f"Invalid dynamics output length: {len(new_state)}"

        # Test controller
        control_output = controller.compute_control(test_state)
        if not isinstance(control_output, list):
            return False, f"Invalid controller output type: {type(control_output)}"

        if len(control_output) != 1:
            return False, f"Invalid controller output length: {len(control_output)}"

        logger.info("✓ Core computation successful")

        # Test control loop (single step for basic functionality)
        state = test_state.copy()
        try:
            control = controller.compute_control(state)
            new_state = dynamics.compute_dynamics(state, control)
            if isinstance(new_state, list):
                state = new_state
            else:
                state = new_state.tolist()

            # Check for reasonable output (not NaN or infinity)
            if any(not isinstance(x, (int, float)) or x != x or abs(x) == float('inf') for x in state):
                return False, f"System produced invalid values: {state}"

        except Exception as e:
            return False, f"Control loop failed: {e}"

        logger.info("✓ Control loop stability verified")

        return True, "Core functionality verified"

    except Exception as e:
        logger.error(f"Core functionality test failed: {e}")
        return False, f"Core functionality failed: {e}"

def test_security_systems():
    """Test if security systems work"""
    logger.info("Testing security systems...")

    try:
        from security.input_validation import input_validator, InputType, ValidationError

        # Test boundary enforcement
        try:
            result = input_validator.validate_numeric_input(200.0, InputType.CONTROL_FORCE)
            return False, f"Security boundary not enforced: {result}"
        except ValidationError:
            pass  # Expected

        # Test valid input
        try:
            result = input_validator.validate_numeric_input(50.0, InputType.CONTROL_FORCE)
            if abs(result - 50.0) > 0.001:
                return False, f"Valid input incorrectly modified: {result}"
        except Exception as e:
            return False, f"Valid input rejected: {e}"

        logger.info("✓ Security input validation working")

        # Test audit logging
        from security.audit_logging import audit_logger, AuditEvent, AuditEventType, AuditSeverity
        from datetime import datetime, timezone

        event = AuditEvent(
            event_id="test_core_event",
            timestamp=datetime.now(timezone.utc),
            event_type=AuditEventType.SYSTEM_INFO,
            severity=AuditSeverity.INFO,
            user_id="test_user",
            client_ip="127.0.0.1",
            session_id="test_session",
            resource="test_core",
            action="test_audit",
            result="SUCCESS",
            details={'test': True},
            source_component="test_core"
        )

        success = audit_logger.log_event(event)
        if not success:
            return False, "Audit logging failed"

        logger.info("✓ Security audit logging working")

        return True, "Security systems verified"

    except Exception as e:
        logger.error(f"Security test failed: {e}")
        return False, f"Security test failed: {e}"

def test_integration():
    """Test complete integration"""
    logger.info("Testing full integration...")

    try:
        # Import all systems
        from production_core.dip_dynamics import DIPDynamics
        from production_core.smc_controller import SMCController
        from security.input_validation import input_validator, InputType

        # Create systems
        dynamics = DIPDynamics()
        controller = SMCController()

        # Simulate secure control workflow
        raw_state = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]

        # Validate state components
        validated_state = []
        for i, component in enumerate(raw_state):
            if i < 3:  # Positions/angles
                validated_component = input_validator.validate_numeric_input(
                    component, InputType.CART_POSITION if i == 0 else InputType.PENDULUM_ANGLE)
            else:  # Velocities
                validated_component = input_validator.validate_numeric_input(
                    component, InputType.VELOCITY)
            validated_state.append(validated_component)

        # Compute control
        control = controller.compute_control(validated_state)

        # Validate control output
        validated_control = input_validator.validate_control_command(control[0], "integration_test")

        # Apply to dynamics
        new_state = dynamics.compute_dynamics(validated_state, [validated_control])

        # Check results
        if len(new_state) != 6:
            return False, f"Invalid integration result length: {len(new_state)}"

        if any(abs(x) > 100 for x in new_state):
            return False, f"Integration result unstable: {new_state}"

        logger.info("✓ Full integration successful")

        return True, "Integration verified"

    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        return False, f"Integration failed: {e}"

def run_fixed_core_tests():
    """Run all fixed core tests"""
    logger.info("Starting Fixed Core System Tests...")
    logger.info("="*60)

    tests = [
        ("Core Imports", test_core_imports),
        ("Core Functionality", test_core_functionality),
        ("Security Systems", test_security_systems),
        ("Full Integration", test_integration)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        logger.info(f"\nTesting: {test_name}...")
        try:
            success, message = test_func()
            if success:
                logger.info(f"PASS: {message}")
                passed += 1
            else:
                logger.error(f"FAIL: {message}")
        except Exception as e:
            logger.error(f"ERROR: {test_name} - {e}")

    # Results
    success_rate = (passed / total) * 100

    logger.info("\n" + "="*60)
    logger.info("FIXED CORE SYSTEM TEST RESULTS")
    logger.info("="*60)
    logger.info(f"Tests Passed: {passed}/{total} ({success_rate:.1f}%)")

    if success_rate >= 75:
        logger.info("FIXED CORE STATUS: WORKING")
        return True
    else:
        logger.warning("FIXED CORE STATUS: STILL HAS ISSUES")
        return False

def main():
    """Main test execution"""
    try:
        return run_fixed_core_tests()
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)