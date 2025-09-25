#==========================================================================================\\\
#=============================== ultra_fast_controller.py ===============================\\\
#==========================================================================================\\\
"""
Ultra-Fast Controller - <0.01ms Performance Target
Extreme performance optimization for Phase 4: 20x speed improvement
"""

import numpy as np
from typing import List, Union
from numba import jit, njit
import math

# Pre-compiled ultra-fast control functions using Numba JIT

@njit(cache=True, fastmath=True)
def _ultra_fast_pid(error_pos, error_vel, integral, prev_error,
                   kp, ki, kd, max_integral, max_derivative):
    """Ultra-optimized PID control with minimal overhead."""

    # Proportional term
    p_term = kp * error_pos

    # Integral term with anti-windup
    integral += error_pos
    if integral > max_integral:
        integral = max_integral
    elif integral < -max_integral:
        integral = -max_integral

    i_term = ki * integral

    # Derivative term with limits
    derivative = error_pos - prev_error
    if derivative > max_derivative:
        derivative = max_derivative
    elif derivative < -max_derivative:
        derivative = -max_derivative

    d_term = kd * derivative

    return p_term + i_term + d_term, integral

@njit(cache=True, fastmath=True)
def _ultra_fast_control_compute(state_array,
                               pos_gains, angle1_gains, angle2_gains,
                               integral_state, prev_error_state,
                               max_force, stability_gain):
    """Ultra-optimized control computation."""

    # Extract state (no loops, direct indexing)
    x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state_array

    # Wrap angles (optimized)
    theta1 = math.atan2(math.sin(theta1), math.cos(theta1))
    theta2 = math.atan2(math.sin(theta2), math.cos(theta2))

    # Apply deadband (optimized)
    deadband = 0.05
    if abs(x) < deadband:
        x = 0.0
    if abs(theta1) < deadband:
        theta1 = 0.0
    if abs(theta2) < deadband:
        theta2 = 0.0

    # Ultra-fast PID for each subsystem
    force_pos, integral_state[0] = _ultra_fast_pid(
        x, x_dot, integral_state[0], prev_error_state[0],
        pos_gains[0], pos_gains[1], pos_gains[2], 1.0, 2.0
    )

    force_angle1, integral_state[1] = _ultra_fast_pid(
        theta1, theta1_dot, integral_state[1], prev_error_state[1],
        angle1_gains[0], angle1_gains[1], angle1_gains[2], 1.0, 2.0
    )

    force_angle2, integral_state[2] = _ultra_fast_pid(
        theta2, theta2_dot, integral_state[2], prev_error_state[2],
        angle2_gains[0], angle2_gains[1], angle2_gains[2], 1.0, 2.0
    )

    # Update previous errors
    prev_error_state[0] = x
    prev_error_state[1] = theta1
    prev_error_state[2] = theta2

    # Combine forces (optimized)
    total_force = force_pos + 0.1 * force_angle1 + 0.1 * force_angle2
    total_force *= stability_gain

    # Apply force limits (optimized)
    if total_force > max_force:
        total_force = max_force
    elif total_force < -max_force:
        total_force = -max_force

    return total_force

class UltraFastController:
    """Ultra-optimized controller for <0.01ms performance target."""

    def __init__(self):
        """Initialize with pre-allocated arrays for zero-allocation operation."""

        # Pre-compiled gains as numpy arrays (faster access)
        self.pos_gains = np.array([0.01, 0.0001, 0.005], dtype=np.float64)
        self.angle1_gains = np.array([0.5, 0.001, 0.05], dtype=np.float64)
        self.angle2_gains = np.array([0.5, 0.001, 0.05], dtype=np.float64)

        # Pre-allocated state arrays (zero allocation during control)
        self.integral_state = np.zeros(3, dtype=np.float64)
        self.prev_error_state = np.zeros(3, dtype=np.float64)
        self.state_array = np.zeros(6, dtype=np.float64)

        # Constants (pre-computed)
        self.max_force = 5.0
        self.stability_gain = 0.1

        # Performance monitoring
        self.step_count = 0

        # Warm up the JIT compiler
        self._warm_up_jit()

    def _warm_up_jit(self):
        """Warm up JIT compilation for optimal performance."""
        # Run a few dummy computations to compile the JIT functions
        dummy_state = np.array([0.1, 0.1, 0.1, 0.0, 0.0, 0.0], dtype=np.float64)
        for _ in range(10):
            _ultra_fast_control_compute(
                dummy_state, self.pos_gains, self.angle1_gains, self.angle2_gains,
                self.integral_state, self.prev_error_state,
                self.max_force, self.stability_gain
            )

    def compute_control(self, state: Union[List[float], np.ndarray]) -> List[float]:
        """Ultra-fast control computation with minimal overhead."""

        # Convert to numpy array if needed (optimized)
        if isinstance(state, list):
            # Direct assignment (faster than np.array())
            for i in range(6):
                self.state_array[i] = state[i]
        else:
            # Copy data (faster than conversion)
            np.copyto(self.state_array, state)

        # Call ultra-optimized JIT function
        control_force = _ultra_fast_control_compute(
            self.state_array,
            self.pos_gains, self.angle1_gains, self.angle2_gains,
            self.integral_state, self.prev_error_state,
            self.max_force, self.stability_gain
        )

        self.step_count += 1

        # Return as list (required interface)
        return [float(control_force)]

    def reset_controller(self):
        """Reset controller state (optimized)."""
        self.integral_state.fill(0.0)
        self.prev_error_state.fill(0.0)
        self.step_count = 0

    def get_controller_status(self) -> dict:
        """Get controller status with minimal overhead."""
        return {
            'controller_type': 'UltraFast',
            'step_count': self.step_count,
            'max_force': self.max_force,
            'performance_optimized': True
        }

    def is_stable(self, state: Union[List[float], np.ndarray]) -> bool:
        """Ultra-fast stability check."""
        if isinstance(state, list):
            return (abs(state[0]) < 1.0 and
                   abs(state[1]) < 0.3 and
                   abs(state[2]) < 0.3)
        else:
            return (abs(state[0]) < 1.0 and
                   abs(state[1]) < 0.3 and
                   abs(state[2]) < 0.3)

# Performance utilities

@njit(cache=True, fastmath=True)
def benchmark_control_loop(state_array, iterations):
    """Ultra-fast benchmark loop for performance testing."""
    pos_gains = np.array([0.01, 0.0001, 0.005])
    angle1_gains = np.array([0.5, 0.001, 0.05])
    angle2_gains = np.array([0.5, 0.001, 0.05])
    integral_state = np.zeros(3)
    prev_error_state = np.zeros(3)

    total_force = 0.0

    for i in range(iterations):
        force = _ultra_fast_control_compute(
            state_array, pos_gains, angle1_gains, angle2_gains,
            integral_state, prev_error_state, 5.0, 0.1
        )
        total_force += force

    return total_force / iterations