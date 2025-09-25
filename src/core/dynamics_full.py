#==========================================================================================\\\
#================================== src/core/dynamics_full.py ==============================\\\
#==========================================================================================\\\
"""
Full dynamics compatibility layer.
This module re-exports the full dynamics class from its new modular location
for backward compatibility with legacy import paths.
"""

# Re-export full dynamics class from new location
from ..plant.models.full.dynamics import FullDIPDynamics

# Re-export integration functions for test compatibility
from .dynamics import step_rk4_numba, step_euler_numba

# For backward compatibility, also create FullDIPParams alias
# Tests expect this to exist
class FullDIPParams:
    """Compatibility class for full DIP parameters."""
    def __init__(self, config=None):
        if config is None:
            # Create default parameters - will be extracted by the numba functions
            self.masses = type('masses', (), {
                'cart': 0.5, 'pendulum1': 0.2, 'pendulum2': 0.2
            })()
            self.lengths = type('lengths', (), {
                'pendulum1': 0.3, 'pendulum2': 0.3,
                'pendulum1_com': 0.15, 'pendulum2_com': 0.15
            })()
            self.inertias = type('inertias', (), {
                'pendulum1': 0.006, 'pendulum2': 0.006
            })()
            self.physics = type('physics', (), {'gravity': 9.81})()
            self.damping = type('damping', (), {
                'cart': 0.1, 'pendulum1': 0.00, 'pendulum2': 0.00
            })()
        else:
            # Use provided config
            self.masses = config.masses
            self.lengths = config.lengths
            self.inertias = config.inertias
            self.physics = config.physics
            self.damping = config.damping

__all__ = ['FullDIPDynamics', 'step_rk4_numba', 'step_euler_numba', 'FullDIPParams']