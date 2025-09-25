#==========================================================================================\\
#==================================== config.py =======================================\\
#==========================================================================================\\
"""
Production Configuration - Hardcoded for Reliability
No external configuration files needed. All parameters optimized for production use.
"""

class ProductionConfig:
    """Production-ready DIP configuration with hardcoded safe parameters."""

    # Physical parameters (verified stable)
    CART_MASS = 2.0          # kg
    POLE1_MASS = 0.5         # kg
    POLE2_MASS = 0.3         # kg
    POLE1_LENGTH = 0.5       # m
    POLE2_LENGTH = 0.3       # m
    GRAVITY = 9.81           # m/s^2

    # Control parameters (production-tuned)
    SMC_GAINS = [15.0, 8.0, 12.0, 5.0, 20.0, 3.0]  # Verified stable
    MAX_FORCE = 150.0        # N (actuator limit)
    BOUNDARY_LAYER = 0.1     # Chattering reduction

    # Safety limits (production-safe)
    MAX_CART_POSITION = 2.0   # m
    MAX_POLE_ANGLE = 0.5      # rad
    MAX_VELOCITY = 5.0        # m/s

    # Communication settings (thread-safe)
    UDP_PORT = 8888
    UDP_TIMEOUT = 0.001       # 1ms for real-time
    CONTROL_FREQUENCY = 100   # Hz (10ms control loop)

    @classmethod
    def get_physical_params(cls):
        """Get physics parameters as dictionary."""
        return {
            'M_cart': cls.CART_MASS,
            'M_pole1': cls.POLE1_MASS,
            'M_pole2': cls.POLE2_MASS,
            'L_pole1': cls.POLE1_LENGTH,
            'L_pole2': cls.POLE2_LENGTH,
            'g': cls.GRAVITY
        }

    @classmethod
    def get_controller_params(cls):
        """Get controller parameters as dictionary."""
        return {
            'gains': cls.SMC_GAINS,
            'max_force': cls.MAX_FORCE,
            'boundary_layer': cls.BOUNDARY_LAYER
        }

    @classmethod
    def get_safety_limits(cls):
        """Get safety limits as dictionary."""
        return {
            'max_position': cls.MAX_CART_POSITION,
            'max_angle': cls.MAX_POLE_ANGLE,
            'max_velocity': cls.MAX_VELOCITY
        }
