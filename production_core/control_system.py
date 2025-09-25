#==========================================================================================\\
#================================ control_system.py ====================================\\
#==========================================================================================\\
"""
Production Control System - Integrated DIP Control Loop
Combines all essential components into a single production-ready control system.
"""

import numpy as np
import time
import logging
from typing import Tuple, Optional

from dip_dynamics import SimplifiedDIPDynamics
from smc_controller import ClassicalSMC
from safe_interface import SafeUDPInterface
from config import ProductionConfig

class ProductionControlSystem:
    """Production-ready DIP control system with integrated safety and monitoring."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.config = ProductionConfig()
        self.dynamics = SimplifiedDIPDynamics(self.config.get_physical_params())
        self.controller = ClassicalSMC(self.config.get_controller_params())
        self.interface = SafeUDPInterface(self.config.UDP_PORT)

        # Control state
        self.state = np.zeros(6)  # [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
        self.last_control = 0.0
        self.control_dt = 1.0 / self.config.CONTROL_FREQUENCY

        # Safety monitoring
        self.safety_violations = 0
        self.control_iterations = 0
        self.start_time = time.time()

        self.logger.info("Production Control System initialized")

    def check_safety_limits(self, state: np.ndarray) -> bool:
        """Check if state violates safety limits."""
        limits = self.config.get_safety_limits()

        # Position limits
        if abs(state[0]) > limits['max_position']:
            self.logger.warning(f"Position limit violated: {state[0]:.3f} > {limits['max_position']}")
            return False

        # Angle limits
        if abs(state[1]) > limits['max_angle'] or abs(state[2]) > limits['max_angle']:
            self.logger.warning(f"Angle limits violated: {state[1]:.3f}, {state[2]:.3f}")
            return False

        # Velocity limits
        if abs(state[3]) > limits['max_velocity']:
            self.logger.warning(f"Velocity limit violated: {state[3]:.3f} > {limits['max_velocity']}")
            return False

        return True

    def emergency_stop(self) -> float:
        """Emergency stop - return zero control."""
        self.safety_violations += 1
        self.logger.error("EMERGENCY STOP ACTIVATED - Safety violation detected")
        return 0.0

    def control_step(self, state: np.ndarray) -> Tuple[float, bool]:
        """Execute single control step with safety checks."""

        # Safety check
        if not self.check_safety_limits(state):
            return self.emergency_stop(), False

        # Compute control
        try:
            control = self.controller.compute_control(state, self.last_control)

            # Clamp to actuator limits
            control = np.clip(control, -self.config.MAX_FORCE, self.config.MAX_FORCE)

            self.last_control = control
            self.control_iterations += 1

            return control, True

        except Exception as e:
            self.logger.error(f"Control computation failed: {e}")
            return self.emergency_stop(), False

    def run_control_loop(self, duration_seconds: float = 10.0):
        """Run production control loop for specified duration."""

        self.logger.info(f"Starting control loop for {duration_seconds} seconds")

        start_time = time.time()
        next_control_time = start_time

        try:
            while (time.time() - start_time) < duration_seconds:

                # Timing control
                current_time = time.time()
                if current_time < next_control_time:
                    time.sleep(next_control_time - current_time)

                # Get state (in production, this would come from sensors)
                # For now, integrate dynamics forward
                state = self.state

                # Control step
                control, success = self.control_step(state)

                # Send control (in production, this would go to actuators)
                self.interface.send_control(control)

                # Integrate dynamics forward (simulation only)
                if success:
                    state_dot = self.dynamics.compute_dynamics(state, control)
                    self.state = state + state_dot * self.control_dt

                # Schedule next control iteration
                next_control_time += self.control_dt

        except KeyboardInterrupt:
            self.logger.info("Control loop interrupted by user")
        except Exception as e:
            self.logger.error(f"Control loop failed: {e}")
        finally:
            self.shutdown()

    def get_performance_stats(self) -> dict:
        """Get control system performance statistics."""
        runtime = time.time() - self.start_time
        return {
            'runtime_seconds': runtime,
            'control_iterations': self.control_iterations,
            'control_frequency_actual': self.control_iterations / runtime if runtime > 0 else 0,
            'control_frequency_target': self.config.CONTROL_FREQUENCY,
            'safety_violations': self.safety_violations,
            'success_rate': 1.0 - (self.safety_violations / max(self.control_iterations, 1))
        }

    def shutdown(self):
        """Shutdown control system safely."""
        self.interface.shutdown()
        stats = self.get_performance_stats()

        self.logger.info("Control System Performance:")
        self.logger.info(f"  Runtime: {stats['runtime_seconds']:.2f} seconds")
        self.logger.info(f"  Control iterations: {stats['control_iterations']}")
        self.logger.info(f"  Actual frequency: {stats['control_frequency_actual']:.1f} Hz")
        self.logger.info(f"  Safety violations: {stats['safety_violations']}")
        self.logger.info(f"  Success rate: {stats['success_rate']:.3f}")

def main():
    """Production control system entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and run control system
    control_system = ProductionControlSystem()

    # Run for 30 seconds as demonstration
    control_system.run_control_loop(duration_seconds=30.0)

if __name__ == "__main__":
    main()
