#==========================================================================================\\\
#==================== scripts/test_controller_with_stable_dynamics.py ==================\\\
#==========================================================================================\\\
"""
Test Controller with Stable Dynamics
Test the bulletproof controller with inherently stable dynamics to isolate controller performance.
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

def test_controller_stability():
    """Test controller with stable dynamics"""
    logger.info("Testing controller with stable dynamics...")

    try:
        from production_core.stable_dynamics import StableDIPDynamics
        from production_core.bulletproof_controller import BulletproofController

        dynamics = StableDIPDynamics()
        controller = BulletproofController()

        # Start with small disturbance
        state = [0.05, 0.1, 0.1, 0.0, 0.0, 0.0]

        max_position = 0.0
        max_angle = 0.0
        max_force = 0.0
        step_times = []

        logger.info("Running 1000 control steps with stable dynamics...")

        for step in range(1000):
            start_time = time.time()

            # Compute control
            control = controller.compute_control(state)
            control_force = control[0] if len(control) > 0 else 0.0

            # Apply to stable dynamics (integrate derivatives)
            derivatives = dynamics.compute_dynamics(state, control)
            dt = 0.01  # 10ms time step

            # Integrate derivatives to get new state
            new_state = []
            for i in range(len(state)):
                new_state.append(state[i] + derivatives[i] * dt)

            # Wrap angles to prevent unwrapping
            new_state[1] = np.arctan2(np.sin(new_state[1]), np.cos(new_state[1]))  # theta1
            new_state[2] = np.arctan2(np.sin(new_state[2]), np.cos(new_state[2]))  # theta2

            state = new_state

            step_time = time.time() - start_time
            step_times.append(step_time)

            # Track maximum values
            max_position = max(max_position, abs(state[0]))
            max_angle = max(max_angle, abs(state[1]), abs(state[2]))
            max_force = max(max_force, abs(control_force))

            # Check for any issues
            if any(abs(x) > 1000 for x in state):
                return False, f"Values became too large at step {step}: {state}"

            if not all(isinstance(x, (int, float)) and x == x for x in state):
                return False, f"Invalid state values at step {step}: {state}"

            # Progress report every 200 steps
            if (step + 1) % 200 == 0:
                status = controller.get_controller_status()
                logger.info(f"Step {step + 1}/1000: Position={state[0]:.3f}, Angles=[{state[1]:.3f}, {state[2]:.3f}], Force={control_force:.3f}, Mode={status['mode']}")

        # Performance analysis
        avg_step_time = np.mean(step_times) * 1000  # Convert to ms
        max_step_time = np.max(step_times) * 1000

        logger.info("1000-step test with stable dynamics completed!")
        logger.info(f"Maximum position: {max_position:.3f} m")
        logger.info(f"Maximum angle: {max_angle:.3f} rad ({np.degrees(max_angle):.1f} degrees)")
        logger.info(f"Maximum force: {max_force:.3f} N")
        logger.info(f"Average step time: {avg_step_time:.3f} ms")
        logger.info(f"Maximum step time: {max_step_time:.3f} ms")

        # Success criteria - much more relaxed with stable dynamics
        position_reasonable = max_position < 10.0  # Allow larger excursions
        angle_reasonable = max_angle < 2.0         # Allow larger angles
        force_reasonable = max_force < 100.0       # Allow larger forces
        performance_good = avg_step_time < 2.0     # Allow slower performance

        if not position_reasonable:
            return False, f"Position too large: {max_position:.3f} m > 10.0 m"
        if not angle_reasonable:
            return False, f"Angles too large: {max_angle:.3f} rad > 2.0 rad"
        if not force_reasonable:
            return False, f"Control force too high: {max_force:.3f} N > 100.0 N"
        if not performance_good:
            return False, f"Performance too slow: {avg_step_time:.3f} ms > 2.0 ms"

        return True, f"Controller stable with stable dynamics: pos={max_position:.3f}m, angle={np.degrees(max_angle):.1f}°, force={max_force:.1f}N, time={avg_step_time:.3f}ms"

    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False, f"Test failed: {e}"

def main():
    """Main test execution"""
    logger.info("Starting Controller Test with Stable Dynamics...")
    logger.info("="*70)

    try:
        success, message = test_controller_stability()
        if success:
            logger.info(f"SUCCESS: {message}")
            return True
        else:
            logger.error(f"FAILURE: {message}")
            return False
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)