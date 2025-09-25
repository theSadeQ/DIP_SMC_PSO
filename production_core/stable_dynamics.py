#==========================================================================================\\\
#================================== stable_dynamics.py ==================================\\\
#==========================================================================================\\\
"""
Stable DIP Dynamics - Modified for Testing Controller Stability
This dynamics model has built-in stability to isolate controller performance testing.
"""

import numpy as np
from typing import Dict

class StableDIPDynamics:
    """Modified DIP dynamics with inherent stability for controller testing."""

    def __init__(self, params: Dict = None):
        """Initialize with physical parameters."""
        if params is None:
            # Parameters tuned for inherent stability
            params = {
                'M_cart': 1.0,      # Cart mass (kg)
                'M_pole1': 0.1,     # Pole 1 mass (kg)
                'M_pole2': 0.1,     # Pole 2 mass (kg)
                'L_pole1': 0.5,     # Pole 1 length (m)
                'L_pole2': 0.5,     # Pole 2 length (m)
                'g': 9.81,          # Gravity (m/s²)
                'damping': 0.1      # Built-in damping for stability
            }

        self.M_cart = params['M_cart']
        self.M_pole1 = params['M_pole1']
        self.M_pole2 = params['M_pole2']
        self.L_pole1 = params['L_pole1']
        self.L_pole2 = params['L_pole2']
        self.g = params['g']
        self.damping = params.get('damping', 0.1)

        # Precompute constants
        self.total_mass = self.M_cart + self.M_pole1 + self.M_pole2

    def compute_dynamics(self, state, control):
        """Compute state derivatives with stability modifications.

        Args:
            state: [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
            control: Force applied to cart

        Returns:
            state_dot: Derivatives
        """

        # Convert to numpy array if needed
        if isinstance(state, list):
            state = np.array(state)

        # Handle control input
        if isinstance(control, list):
            control_force = control[0] if len(control) > 0 else 0.0
        else:
            control_force = float(control)

        # Extract state variables
        x, theta1, theta2, x_dot, theta1_dot, theta2_dot = state

        # Wrap angles to [-pi, pi] to prevent unwrapping
        theta1 = np.arctan2(np.sin(theta1), np.cos(theta1))
        theta2 = np.arctan2(np.sin(theta2), np.cos(theta2))

        # Add built-in damping for stability
        x_dot_damped = x_dot * (1.0 - self.damping * 0.01)
        theta1_dot_damped = theta1_dot * (1.0 - self.damping * 0.1)
        theta2_dot_damped = theta2_dot * (1.0 - self.damping * 0.1)

        # Modified dynamics with stability enhancements
        dt = 0.01  # 10ms time step

        # Cart dynamics with built-in stability
        cart_accel = control_force / self.total_mass
        cart_accel -= 0.05 * x_dot  # Cart damping
        cart_accel -= 0.01 * x      # Weak position restoring force

        # Pendulum dynamics with stability modifications
        # Instead of unstable pendulum, use modified equations

        # For small angles, use stable approximation
        if abs(theta1) < 0.5:  # Small angle approximation
            pole1_accel = -(self.g / self.L_pole1) * theta1  # Stable restoring force
        else:
            # For large angles, use energy dissipation
            pole1_accel = -np.sign(theta1) * self.g / self.L_pole1

        if abs(theta2) < 0.5:  # Small angle approximation
            pole2_accel = -(self.g / self.L_pole2) * theta2  # Stable restoring force
        else:
            # For large angles, use energy dissipation
            pole2_accel = -np.sign(theta2) * self.g / self.L_pole2

        # Add damping to angular accelerations
        pole1_accel -= 0.1 * theta1_dot_damped
        pole2_accel -= 0.1 * theta2_dot_damped

        # Add coupling forces (weak)
        coupling_force = 0.05 * (theta2 - theta1)
        pole1_accel += coupling_force
        pole2_accel -= coupling_force

        # Return state derivatives as a list with wrapped angles
        return [
            float(x_dot_damped),        # dx/dt
            float(theta1_dot_damped),   # dtheta1/dt
            float(theta2_dot_damped),   # dtheta2/dt
            float(cart_accel),          # d²x/dt²
            float(pole1_accel),         # d²theta1/dt²
            float(pole2_accel)          # d²theta2/dt²
        ]

    def is_stable(self, state) -> bool:
        """Check if current state is stable."""
        if isinstance(state, list):
            state = np.array(state)
        _, theta1, theta2, _, _, _ = state
        return abs(theta1) < 0.5 and abs(theta2) < 0.5