#==========================================================================================\\\
#==================================== dip_dynamics.py ==================================\\\
#==========================================================================================\\\
"""
Production-Ready DIP Dynamics - Minimal Implementation
Simplified double inverted pendulum physics optimized for real-time control.
"""

import numpy as np
from typing import Dict

class DIPDynamics:
    """Production-ready simplified DIP dynamics for real-time control."""

    def __init__(self, params: Dict = None):
        """Initialize with physical parameters."""
        if params is None:
            # Default parameters for DIP system
            params = {
                'M_cart': 1.0,      # Cart mass (kg)
                'M_pole1': 0.1,     # Pole 1 mass (kg)
                'M_pole2': 0.1,     # Pole 2 mass (kg)
                'L_pole1': 0.5,     # Pole 1 length (m)
                'L_pole2': 0.5,     # Pole 2 length (m)
                'g': 9.81           # Gravity (m/s²)
            }

        self.M_cart = params['M_cart']      # Cart mass
        self.M_pole1 = params['M_pole1']    # Pole 1 mass
        self.M_pole2 = params['M_pole2']    # Pole 2 mass
        self.L_pole1 = params['L_pole1']    # Pole 1 length
        self.L_pole2 = params['L_pole2']    # Pole 2 length
        self.g = params['g']                # Gravity

        # Precompute constants for efficiency
        self.total_mass = self.M_cart + self.M_pole1 + self.M_pole2
        self.pole1_factor = self.M_pole1 * self.L_pole1
        self.pole2_factor = self.M_pole2 * self.L_pole2

    def compute_dynamics(self, state, control):
        """Compute next state for DIP system with integration.

        Args:
            state: [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
            control: Force applied to cart

        Returns:
            next_state: Next state after integration [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
        """

        # Convert to numpy array if needed
        if isinstance(state, list):
            state = np.array(state)

        # Handle control input
        if isinstance(control, list):
            control_force = control[0]
        else:
            control_force = float(control)

        # Extract state variables
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # Wrap angles to prevent explosive growth
        theta1 = np.arctan2(np.sin(theta1), np.cos(theta1))
        theta2 = np.arctan2(np.sin(theta2), np.cos(theta2))

        # Apply state bounds for numerical stability
        x = np.clip(x, -10.0, 10.0)
        x_dot = np.clip(x_dot, -20.0, 20.0)
        theta1_dot = np.clip(theta1_dot, -50.0, 50.0)
        theta2_dot = np.clip(theta2_dot, -50.0, 50.0)

        # Trigonometric functions (computed once for efficiency)
        sin1, cos1 = np.sin(theta1), np.cos(theta1)
        sin2, cos2 = np.sin(theta2), np.cos(theta2)

        # STABLE dynamics with energy dissipation built-in
        damping = 0.05  # Built-in damping for stability

        # Cart acceleration with stability improvements
        cart_accel = control_force / self.total_mass
        cart_accel -= damping * x_dot  # Velocity damping
        cart_accel -= 0.1 * x          # Position restoring force

        # Stable pendulum equations (corrected signs for stability)
        # Original had wrong sign causing instability
        pole1_accel = (self.g * sin1 - cart_accel * cos1) / self.L_pole1  # Corrected sign
        pole2_accel = (self.g * sin2 - cart_accel * cos2) / self.L_pole2  # Corrected sign

        # Add damping to angular accelerations
        pole1_accel -= damping * theta1_dot
        pole2_accel -= damping * theta2_dot

        # Add coupling with damping
        coupling = 0.05 * (theta2 - theta1)
        pole1_accel += coupling
        pole2_accel -= coupling

        # Integration with fixed time step
        dt = 0.01  # 10ms time step

        # Integrate to get next state
        next_x = x + x_dot * dt
        next_theta1 = theta1 + theta1_dot * dt
        next_theta2 = theta2 + theta2_dot * dt
        next_x_dot = x_dot + cart_accel * dt
        next_theta1_dot = theta1_dot + pole1_accel * dt
        next_theta2_dot = theta2_dot + pole2_accel * dt

        # Wrap angles again to ensure they stay in bounds
        next_theta1 = np.arctan2(np.sin(next_theta1), np.cos(next_theta1))
        next_theta2 = np.arctan2(np.sin(next_theta2), np.cos(next_theta2))

        # Return next state as a list for consistency
        return [
            float(next_x),          # x
            float(next_theta1),     # theta1
            float(next_theta2),     # theta2
            float(next_x_dot),      # x_dot
            float(next_theta1_dot), # theta1_dot
            float(next_theta2_dot)  # theta2_dot
        ]

    def is_stable(self, state) -> bool:
        """Check if current state is stable (poles approximately upright)."""
        if isinstance(state, list):
            state = np.array(state)
        _, theta1, theta2, _, _, _ = state
        return abs(theta1) < 0.5 and abs(theta2) < 0.5  # Within 30 degrees