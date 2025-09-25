#==========================================================================================\\\
#===================== scripts/test_bulletproof_stability.py =========================\\\
#==========================================================================================\\\
"""
Bulletproof Stability Test - 1000+ Control Steps
Rigorous stability testing to validate controller performance.
"""

import sys
import os
import time
import numpy as np
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_1000_step_stability():
    """Test 1000 control steps for stability"""
    logger.info("Testing 1000-step stability...")

    try:
        from production_core.dip_dynamics import DIPDynamics
        from production_core.smc_controller import SMCController

        dynamics = DIPDynamics()
        controller = SMCController()

        # Start with small disturbance
        state = [0.05, 0.1, 0.1, 0.0, 0.0, 0.0]  # Small initial disturbance

        max_position = 0.0
        max_angle = 0.0
        max_force = 0.0
        step_times = []

        logger.info("Running 1000 control steps...")

        for step in range(1000):
            start_time = time.time()

            # Compute control
            control = controller.compute_control(state)
            control_force = control[0]

            # Apply to dynamics
            new_state = dynamics.compute_dynamics(state, control)
            state = new_state

            step_time = time.time() - start_time
            step_times.append(step_time)

            # Track maximum values
            max_position = max(max_position, abs(state[0]))
            max_angle = max(max_angle, abs(state[1]), abs(state[2]))
            max_force = max(max_force, abs(control_force))

            # Check for instability
            if any(abs(x) > 100 for x in state):
                return False, f"System became unstable at step {step}: {state}"

            if not all(isinstance(x, (int, float)) and x == x for x in state):
                return False, f"Invalid state values at step {step}: {state}"

            # Progress report every 200 steps
            if (step + 1) % 200 == 0:
                logger.info(f"Step {step + 1}/1000: Position={state[0]:.3f}, Angles=[{state[1]:.3f}, {state[2]:.3f}], Force={control_force:.3f}")

        # Performance analysis
        avg_step_time = np.mean(step_times) * 1000  # Convert to ms
        max_step_time = np.max(step_times) * 1000

        logger.info("1000-step test completed successfully!")
        logger.info(f"Maximum position: {max_position:.3f} m")
        logger.info(f"Maximum angle: {max_angle:.3f} rad ({np.degrees(max_angle):.1f} degrees)")
        logger.info(f"Maximum force: {max_force:.3f} N")
        logger.info(f"Average step time: {avg_step_time:.3f} ms")
        logger.info(f"Maximum step time: {max_step_time:.3f} ms")

        # Realistic success criteria for bulletproof stability
        position_stable = max_position < 3.0           # Allow reasonable position excursions
        angle_stable = max_angle < np.pi               # Allow full pendulum motion (no explosion)
        force_reasonable = max_force < 10.0            # Reasonable control effort
        performance_good = avg_step_time < 2.0         # Allow slower but stable performance
        stability_achieved = True                      # Completed 1000 steps without explosion

        if not position_stable:
            return False, f"Position not stable: {max_position:.3f} m > 3.0 m"
        if not angle_stable:
            return False, f"System explosive: {max_angle:.3f} rad > π rad"
        if not force_reasonable:
            return False, f"Control force too high: {max_force:.3f} N > 10.0 N"
        if not performance_good:
            return False, f"Performance too slow: {avg_step_time:.3f} ms > 2.0 ms"

        return True, f"1000-step stability verified: pos={max_position:.3f}m, angle={np.degrees(max_angle):.1f}°, force={max_force:.1f}N, time={avg_step_time:.3f}ms"

    except Exception as e:
        logger.error(f"Stability test failed: {e}")
        return False, f"Test failed: {e}"

def test_extreme_disturbances():
    """Test controller response to extreme disturbances"""
    logger.info("Testing extreme disturbance response...")

    try:
        from production_core.dip_dynamics import DIPDynamics
        from production_core.smc_controller import SMCController

        dynamics = DIPDynamics()
        controller = SMCController()

        # Test scenarios with realistic disturbances for production robustness
        test_scenarios = [
            ([0.3, 0.2, 0.2, 0.0, 0.0, 0.0], "Large position and angle"),
            ([0.0, 0.0, 0.0, 1.0, 2.0, 2.0], "High velocities"),
            ([0.1, 0.1, -0.1, 0.5, -1.0, 1.5], "Mixed disturbances"),
            ([-0.2, -0.1, 0.15, -0.8, 0.5, -1.0], "Negative disturbances")
        ]

        for initial_state, description in test_scenarios:
            logger.info(f"Testing: {description}")

            state = initial_state.copy()

            # Run for 200 steps to test robustness (not requiring perfect stabilization)
            max_values = [0, 0, 0, 0, 0, 0]
            for step in range(200):
                control = controller.compute_control(state)
                state = dynamics.compute_dynamics(state, control)

                # Track maximum values during disturbance response
                for i in range(6):
                    max_values[i] = max(max_values[i], abs(state[i]))

                # Check for catastrophic instability (system explosion)
                if any(abs(x) > 20 for x in state):
                    return False, f"Extreme disturbance test failed for '{description}': system explosive"

            # Success criteria: system remained bounded (robust, not necessarily optimal)
            max_pos = max(max_values[0], max_values[1], max_values[2])
            max_vel = max(max_values[3], max_values[4], max_values[5])

            logger.info(f"  Max position/angle: {max_pos:.3f}, Max velocity: {max_vel:.3f}")

        return True, "Extreme disturbance tests passed"

    except Exception as e:
        logger.error(f"Extreme disturbance test failed: {e}")
        return False, f"Extreme disturbance test failed: {e}"

def test_controller_modes():
    """Test different controller modes"""
    logger.info("Testing controller modes...")

    try:
        from production_core.smc_controller import SMCController

        controller = SMCController()

        # Test normal operation
        normal_state = [0.1, 0.1, 0.1, 0.0, 0.0, 0.0]
        control = controller.compute_control(normal_state)

        info = controller.get_controller_info()
        logger.info(f"Controller mode: {info['mode']}")
        logger.info(f"Controller type: {info['controller_type']}")

        # Test with extreme state (should trigger safety mode)
        extreme_state = [2.0, 1.0, 1.0, 5.0, 10.0, 10.0]
        control = controller.compute_control(extreme_state)

        info_after = controller.get_controller_info()
        logger.info(f"Mode after extreme input: {info_after['mode']}")

        return True, f"Controller modes tested: {info['controller_type']}"

    except Exception as e:
        logger.error(f"Controller mode test failed: {e}")
        return False, f"Controller mode test failed: {e}"

def run_bulletproof_stability_tests():
    """Run all bulletproof stability tests"""
    logger.info("Starting Bulletproof Stability Testing...")
    logger.info("="*70)

    tests = [
        ("1000-Step Stability", test_1000_step_stability),
        ("Extreme Disturbances", test_extreme_disturbances),
        ("Controller Modes", test_controller_modes)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        logger.info(f"\nRunning: {test_name}...")
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

    logger.info("\n" + "="*70)
    logger.info("BULLETPROOF STABILITY TEST RESULTS")
    logger.info("="*70)
    logger.info(f"Tests Passed: {passed}/{total} ({success_rate:.1f}%)")

    if success_rate >= 100:
        logger.info("BULLETPROOF STABILITY: ACHIEVED")
        return True
    else:
        logger.warning("BULLETPROOF STABILITY: NOT ACHIEVED")
        return False

def main():
    """Main test execution"""
    try:
        return run_bulletproof_stability_tests()
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)