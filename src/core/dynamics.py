#==========================================================================================\\\
#==================================== src/core/dynamics.py ================================\\\
#==========================================================================================\\\
"""
Dynamics compatibility layer.
This module re-exports the main dynamics class from its new modular location
for backward compatibility with legacy import paths.
"""

# Re-export main dynamics class from new location
from ..plant.models.simplified.dynamics import SimplifiedDIPDynamics as DIPDynamics
from ..plant.models.simplified.physics import compute_simplified_dynamics_numba

# Legacy alias
DoubleInvertedPendulum = DIPDynamics

# Import numba for optimization
try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

import numpy as np


@njit
def rhs_numba(state: np.ndarray, u: float, params) -> np.ndarray:
    """
    Numba-optimized right-hand side function for DIP dynamics.
    This is the same as compute_simplified_dynamics_numba but with parameter unpacking.

    Args:
        state: Current state vector [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
        u: Control input (force)
        params: Dynamics parameters object

    Returns:
        State derivative vector
    """
    # Extract parameters from the config object
    m0 = params.masses.cart
    m1 = params.masses.pendulum1
    m2 = params.masses.pendulum2
    L1 = params.lengths.pendulum1
    L2 = params.lengths.pendulum2
    Lc1 = params.lengths.pendulum1_com
    Lc2 = params.lengths.pendulum2_com
    I1 = params.inertias.pendulum1
    I2 = params.inertias.pendulum2
    g = params.physics.gravity
    c0 = params.damping.cart
    c1 = params.damping.pendulum1
    c2 = params.damping.pendulum2

    # Use adaptive regularization parameters
    reg_alpha = 1e-6  # Default regularization
    min_reg = 1e-8    # Minimum regularization

    # Compute and return state derivative
    return compute_simplified_dynamics_numba(
        state, u, m0, m1, m2, L1, L2, Lc1, Lc2, I1, I2, g, c0, c1, c2, reg_alpha, min_reg
    )


@njit
def step_euler_numba(state: np.ndarray, u: float, dt: float, params) -> np.ndarray:
    """
    Numba-optimized Euler integration step for DIP dynamics.

    Args:
        state: Current state vector [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
        u: Control input (force)
        dt: Time step
        params: Dynamics parameters object

    Returns:
        Next state vector after one Euler step
    """
    # Extract parameters from the config object
    m0 = params.masses.cart
    m1 = params.masses.pendulum1
    m2 = params.masses.pendulum2
    L1 = params.lengths.pendulum1
    L2 = params.lengths.pendulum2
    Lc1 = params.lengths.pendulum1_com
    Lc2 = params.lengths.pendulum2_com
    I1 = params.inertias.pendulum1
    I2 = params.inertias.pendulum2
    g = params.physics.gravity
    c0 = params.damping.cart
    c1 = params.damping.pendulum1
    c2 = params.damping.pendulum2

    # Use adaptive regularization parameters
    reg_alpha = 1e-6  # Default regularization
    min_reg = 1e-8    # Minimum regularization

    # Compute state derivative
    state_dot = compute_simplified_dynamics_numba(
        state, u, m0, m1, m2, L1, L2, Lc1, Lc2, I1, I2, g, c0, c1, c2, reg_alpha, min_reg
    )

    # Euler step: x_{k+1} = x_k + dt * f(x_k, u_k)
    return state + dt * state_dot


@njit
def step_rk4_numba(state: np.ndarray, u: float, dt: float, params) -> np.ndarray:
    """
    Numba-optimized 4th-order Runge-Kutta integration step for DIP dynamics.

    Args:
        state: Current state vector [x, theta1, theta2, x_dot, theta1_dot, theta2_dot]
        u: Control input (force)
        dt: Time step
        params: Dynamics parameters object

    Returns:
        Next state vector after one RK4 step
    """
    # Extract parameters from the config object
    m0 = params.masses.cart
    m1 = params.masses.pendulum1
    m2 = params.masses.pendulum2
    L1 = params.lengths.pendulum1
    L2 = params.lengths.pendulum2
    Lc1 = params.lengths.pendulum1_com
    Lc2 = params.lengths.pendulum2_com
    I1 = params.inertias.pendulum1
    I2 = params.inertias.pendulum2
    g = params.physics.gravity
    c0 = params.damping.cart
    c1 = params.damping.pendulum1
    c2 = params.damping.pendulum2

    # Use adaptive regularization parameters
    reg_alpha = 1e-6  # Default regularization
    min_reg = 1e-8    # Minimum regularization

    # RK4 method
    # k1 = f(x_k, u_k)
    k1 = compute_simplified_dynamics_numba(
        state, u, m0, m1, m2, L1, L2, Lc1, Lc2, I1, I2, g, c0, c1, c2, reg_alpha, min_reg
    )

    # k2 = f(x_k + dt/2 * k1, u_k)
    k2 = compute_simplified_dynamics_numba(
        state + 0.5 * dt * k1, u, m0, m1, m2, L1, L2, Lc1, Lc2, I1, I2, g, c0, c1, c2, reg_alpha, min_reg
    )

    # k3 = f(x_k + dt/2 * k2, u_k)
    k3 = compute_simplified_dynamics_numba(
        state + 0.5 * dt * k2, u, m0, m1, m2, L1, L2, Lc1, Lc2, I1, I2, g, c0, c1, c2, reg_alpha, min_reg
    )

    # k4 = f(x_k + dt * k3, u_k)
    k4 = compute_simplified_dynamics_numba(
        state + dt * k3, u, m0, m1, m2, L1, L2, Lc1, Lc2, I1, I2, g, c0, c1, c2, reg_alpha, min_reg
    )

    # x_{k+1} = x_k + dt/6 * (k1 + 2*k2 + 2*k3 + k4)
    return state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


# Compatibility parameter class for optimization code
class DIPParams:
    """
    Compatibility parameter class for DIP dynamics.
    This class provides the interface expected by the optimization modules
    while working with the new config-based system.
    """

    def __init__(self, **kwargs):
        """Initialize DIP parameters from keyword arguments."""
        # Set default values
        defaults = {
            'cart_mass': 0.5,
            'pendulum1_mass': 0.2,
            'pendulum2_mass': 0.2,
            'pendulum1_length': 0.3,
            'pendulum2_length': 0.3,
            'pendulum1_com': 0.15,
            'pendulum2_com': 0.15,
            'pendulum1_inertia': 0.006,
            'pendulum2_inertia': 0.006,
            'gravity': 9.81,
            'cart_damping': 0.1,
            'pendulum1_damping': 0.0,
            'pendulum2_damping': 0.0,
            'regularization': 1e-6,
            'singularity_cond_threshold': 1e8
        }

        # Update with provided kwargs
        defaults.update(kwargs)

        # Set attributes for compatibility
        for key, value in defaults.items():
            setattr(self, key, value)

        # Create compatibility structure similar to config objects
        self.masses = type('masses', (), {
            'cart': defaults['cart_mass'],
            'pendulum1': defaults['pendulum1_mass'],
            'pendulum2': defaults['pendulum2_mass']
        })()

        self.lengths = type('lengths', (), {
            'pendulum1': defaults['pendulum1_length'],
            'pendulum2': defaults['pendulum2_length'],
            'pendulum1_com': defaults['pendulum1_com'],
            'pendulum2_com': defaults['pendulum2_com']
        })()

        self.inertias = type('inertias', (), {
            'pendulum1': defaults['pendulum1_inertia'],
            'pendulum2': defaults['pendulum2_inertia']
        })()

        self.physics = type('physics', (), {
            'gravity': defaults['gravity']
        })()

        self.damping = type('damping', (), {
            'cart': defaults['cart_damping'],
            'pendulum1': defaults['pendulum1_damping'],
            'pendulum2': defaults['pendulum2_damping']
        })()

    @classmethod
    def from_physics_config(cls, physics_config):
        """Create DIPParams from a physics configuration object."""
        # Extract parameters from config object
        try:
            # Try nested structure first (for backward compatibility)
            kwargs = {
                'cart_mass': physics_config.masses.cart,
                'pendulum1_mass': physics_config.masses.pendulum1,
                'pendulum2_mass': physics_config.masses.pendulum2,
                'pendulum1_length': physics_config.lengths.pendulum1,
                'pendulum2_length': physics_config.lengths.pendulum2,
                'pendulum1_com': physics_config.lengths.pendulum1_com,
                'pendulum2_com': physics_config.lengths.pendulum2_com,
                'pendulum1_inertia': physics_config.inertias.pendulum1,
                'pendulum2_inertia': physics_config.inertias.pendulum2,
                'gravity': physics_config.physics.gravity,
                'cart_damping': physics_config.damping.cart,
                'pendulum1_damping': physics_config.damping.pendulum1,
                'pendulum2_damping': physics_config.damping.pendulum2,
            }
        except AttributeError:
            # Try flat structure (SimplifiedDIPConfig)
            try:
                kwargs = {
                    'cart_mass': physics_config.cart_mass,
                    'pendulum1_mass': physics_config.pendulum1_mass,
                    'pendulum2_mass': physics_config.pendulum2_mass,
                    'pendulum1_length': physics_config.pendulum1_length,
                    'pendulum2_length': physics_config.pendulum2_length,
                    'pendulum1_com': physics_config.pendulum1_com,
                    'pendulum2_com': physics_config.pendulum2_com,
                    'pendulum1_inertia': physics_config.pendulum1_inertia,
                    'pendulum2_inertia': physics_config.pendulum2_inertia,
                    'gravity': physics_config.gravity,
                    'cart_damping': physics_config.cart_friction,
                    'pendulum1_damping': physics_config.joint1_friction,
                    'pendulum2_damping': physics_config.joint2_friction,
                }
            except AttributeError:
                # Final fallback - use defaults
                kwargs = {}

        return cls(**kwargs)


__all__ = ['DIPDynamics', 'DoubleInvertedPendulum', 'step_euler_numba', 'step_rk4_numba', 'rhs_numba', 'DIPParams']