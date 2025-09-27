#==========================================================================================\\\
#=================================== smc_controller.py ==================================\\\
#==========================================================================================\\\
"""
Production-Ready SMC Controller - Minimal Implementation
Sliding Mode Controller optimized for DIP stabilization in production environments.
"""

import numpy as np
from typing import List, Union
from .bulletproof_controller import BulletproofController

class SMCController:
    """Production-ready Sliding Mode Controller for DIP system."""

    def __init__(self, gains: List[float] = None):
        """Initialize bulletproof SMC controller."""
        # Use bulletproof controller as the core implementation
        self.controller = BulletproofController()

        # Legacy compatibility
        self.max_force = 30.0   # Conservative force limit

    def compute_control(self, state: Union[List[float], np.ndarray]) -> List[float]:
        """Compute bulletproof control force.

        Args:
            state: [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]

        Returns:
            [control_force]: Control force applied to cart
        """
        # Delegate to bulletproof controller
        return self.controller.compute_control(state)

    def is_stable(self, state: Union[List[float], np.ndarray]) -> bool:
        """Check if the system is in a stable configuration."""
        return self.controller.is_stable(state)

    def get_controller_info(self) -> dict:
        """Get controller configuration information."""
        status = self.controller.get_controller_status()
        return {
            'controller_type': 'Bulletproof SMC',
            'mode': status['mode'],
            'max_force_limit': self.max_force,
            'step_count': status['step_count'],
            'fault_count': status['fault_count'],
            'stability_status': {
                'max_state_magnitude': status['max_state_magnitude'],
                'oscillation_detected': status['oscillation_detected']
            }
        }