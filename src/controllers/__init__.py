#==========================================================================================\\\
#============================= src/controllers/__init__.py =============================\\\
#==========================================================================================\\\

"""
Clean SMC Controllers Package

Provides unified access to 4 core SMC controllers optimized for research and PSO tuning:
- Classical SMC
- Adaptive SMC
- Super-Twisting SMC
- Hybrid Adaptive-STA SMC

Usage Examples:
    # PSO-optimized controller creation
    from controllers import create_smc_for_pso, SMCType
    controller = create_smc_for_pso(SMCType.CLASSICAL, gains=[10, 8, 15, 12, 50, 5])

    # Direct controller instantiation
    from controllers import ClassicalSMC
    controller = ClassicalSMC(gains=[10, 8, 15, 12, 50, 5], max_force=100.0)

    # Clean factory usage
    from controllers import SMCFactory, SMCConfig
    config = SMCConfig(gains=[10, 8, 15, 12, 50, 5], max_force=100.0)
    controller = SMCFactory.create_controller(SMCType.CLASSICAL, config)
"""

# ============================================================================
# CLEAN SMC API - PRIMARY INTERFACE
# ============================================================================

# Import the clean SMC factory from factory package
from .factory import (
    # Core types
    SMCType,
    SMCConfig,
    SMCFactory,

    # PSO-optimized functions
    create_smc_for_pso,
    get_gain_bounds_for_pso,
    validate_smc_gains,

    # Specifications
    SMC_GAIN_SPECS
)

# Import individual SMC controllers for direct access
try:
    from .smc.classic_smc import ClassicalSMC
    from .smc.adaptive_smc import AdaptiveSMC
    from .smc.sta_smc import SuperTwistingSMC
    from .smc.hybrid_adaptive_sta_smc import HybridAdaptiveSTASMC
except ImportError:
    # Import fallback - controllers may not be available in all contexts
    ClassicalSMC = None
    AdaptiveSMC = None
    SuperTwistingSMC = None
    HybridAdaptiveSTASMC = None

# ============================================================================
# OPTIONAL CONTROLLERS (for comparison/specialized use)
# ============================================================================

# Only import if you need them for comparison studies
try:
    from .mpc.mpc_controller import MPCController, MPCWeights
    _HAS_MPC = True
except ImportError:
    _HAS_MPC = False

try:
    from .specialized.swing_up_smc import SwingUpSMC
    _HAS_SWING_UP = True
except ImportError:
    _HAS_SWING_UP = False

# Legacy factory for backward compatibility
from .factory import create_controller_legacy

# ============================================================================
# CLEAN PUBLIC API
# ============================================================================

__all__ = [
    # ========================================
    # PRIMARY SMC API (USE THESE)
    # ========================================

    # SMC Controller Types
    "SMCType",
    "ClassicalSMC",
    "AdaptiveSMC",
    "SuperTwistingSMC",
    "HybridAdaptiveSTASMC",

    # Clean Factory Interface
    "SMCFactory",
    "SMCConfig",

    # PSO Integration (OPTIMIZED FOR YOUR RESEARCH)
    "create_smc_for_pso",
    "get_gain_bounds_for_pso",
    "validate_smc_gains",

    # Gain Specifications
    "SMC_GAIN_SPECS",

    # ========================================
    # SECONDARY API (optional)
    # ========================================

    # Legacy compatibility
    "create_controller_legacy",
]

# Add optional controllers to __all__ if available
if _HAS_MPC:
    __all__.extend(["MPCController", "MPCWeights"])

if _HAS_SWING_UP:
    __all__.append("SwingUpSMC")

# ============================================================================
# CONVENIENCE FUNCTIONS FOR COMMON RESEARCH PATTERNS
# ============================================================================

def create_all_smc_controllers(
    gains_dict: dict[str, list[float]],
    max_force: float = 100.0,
    dt: float = 0.01
) -> dict[str, any]:
    """
    Create all 4 SMC controllers at once for comparison studies.

    Args:
        gains_dict: Dictionary mapping controller names to their gains
                   e.g., {"classical": [10,8,15,12,50,5], "adaptive": [10,8,15,12,0.5]}
        max_force: Maximum control force
        dt: Control timestep

    Returns:
        Dictionary of initialized SMC controllers

    Example:
        gains = {
            "classical": [10, 8, 15, 12, 50, 5],
            "adaptive": [10, 8, 15, 12, 0.5],
            "sta": [25, 10, 15, 12, 20, 15],
            "hybrid": [15, 12, 18, 15]
        }
        controllers = create_all_smc_controllers(gains)
    """
    controllers = {}

    type_mapping = {
        "classical": SMCType.CLASSICAL,
        "adaptive": SMCType.ADAPTIVE,
        "sta": SMCType.SUPER_TWISTING,
        "super_twisting": SMCType.SUPER_TWISTING,
        "hybrid": SMCType.HYBRID
    }

    for name, gains in gains_dict.items():
        if name.lower() in type_mapping:
            smc_type = type_mapping[name.lower()]
            controllers[name] = create_smc_for_pso(
                smc_type=smc_type,
                gains=gains,
                max_force=max_force,
                dt=dt
            )
        else:
            raise ValueError(f"Unknown SMC controller type: {name}")

    return controllers

def get_all_gain_bounds() -> dict[str, list[tuple[float, float]]]:
    """Get PSO gain bounds for all SMC controller types."""
    return {
        "classical": get_gain_bounds_for_pso(SMCType.CLASSICAL),
        "adaptive": get_gain_bounds_for_pso(SMCType.ADAPTIVE),
        "sta": get_gain_bounds_for_pso(SMCType.SUPER_TWISTING),
        "hybrid": get_gain_bounds_for_pso(SMCType.HYBRID)
    }

# Add convenience functions to exports
__all__.extend(["create_all_smc_controllers", "get_all_gain_bounds"])

