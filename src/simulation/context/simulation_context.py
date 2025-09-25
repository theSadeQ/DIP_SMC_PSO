#==========================================================================================\\\
#=================== src/simulation/context/simulation_context.py ==================\\\
#==========================================================================================\\\
"""
Manages the simulation setup, including configuration loading and
dynamic selection of the physics model.

"""
from __future__ import annotations

import logging
from typing import Optional, List, Any

# Import the necessary components
from src.config import load_config, ConfigSchema
# Import dynamics lazily to avoid circular imports
# from ...plant.models.dynamics import DoubleInvertedPendulum as DIPDynamics
# from ...plant.models.dip_full import FullDIPDynamics
# Import factory lazily to avoid circular imports
# from src.controllers.factory import create_controller as _create_controller

try:
    # Optional: FDI system may not be present in some builds
    from ...analysis.fault_detection.fdi import FaultDetectionInterface as FDIsystem  # type: ignore
except Exception:
    FDIsystem = None  # type: ignore


class SimulationContext:
    """
    Initializes and holds the context for a simulation run.

    This class centralizes the setup logic by loading the configuration
    and selecting the appropriate dynamics model based on that config.
    """
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the simulation context by loading the configuration.
        """
        self.config: ConfigSchema = load_config(config_path, allow_unknown=True)
        self.dynamics_model = self._initialize_dynamics_model()

    def _initialize_dynamics_model(self) -> Any:
        """
        Initialize the correct dynamics model based on the configuration.

        This is the central point for model selection logic.
        """
        # Import dynamics lazily to avoid circular imports
        from ...plant.models.dynamics import DoubleInvertedPendulum as DIPDynamics
        from ...plant.models.dip_full import FullDIPDynamics

        # The use_full_dynamics flag in config.yaml controls this selection
        use_full = self.config.simulation.use_full_dynamics

        # Always pass the validated PhysicsConfig object directly to the dynamics
        # constructors.  Passing a raw dict causes attribute errors inside the
        # dynamics classes when they attempt to call `model_dump()` again.  The
        # dynamics classes expect a PhysicsConfig instance and handle any
        # required conversion internally.
        if use_full:
            logging.info("Initializing Full Nonlinear Dynamics Model.")
            return FullDIPDynamics(self.config.physics)
        else:
            logging.info("Initializing Simplified Dynamics Model.")
            return DIPDynamics(self.config.physics)

    def get_dynamics_model(self) -> Any:
        """
        Return the initialized dynamics model.
        """
        return self.dynamics_model

    def get_config(self) -> ConfigSchema:
        """
        Return the validated configuration model for reuse by callers.
        """
        return self.config

    def create_controller(self, name: Optional[str] = None, gains: Optional[List[float]] = None) -> Any:
        """
        Create a controller using the shared, validated config and the project factory.
        If no name is provided, default to 'classical_smc'.
        If no gains are provided, use defaults from config.
        """
        ctrl_name = name or "classical_smc"

        # Use default gains from config if none provided
        if gains is None:
            ctrl_defaults = getattr(self.config.controller_defaults, ctrl_name, None)
            if ctrl_defaults and hasattr(ctrl_defaults, 'gains'):
                gains = ctrl_defaults.gains

        # Import factory lazily to avoid circular imports
        from src.controllers.factory import create_controller as _create_controller
        return _create_controller(ctrl_name, config=self.config, gains=gains)

    def create_fdi(self) -> Optional[Any]:
        """
        Create the FDI system if enabled in config; otherwise return None.
        Mirrors the previous app-level behavior (non-fatal if missing).
        """
        fdi_cfg = getattr(self.config, "fdi", None)
        if not fdi_cfg or not getattr(fdi_cfg, "enabled", False):
            return None
        if FDIsystem is None:
            logging.warning("FDIsystem is enabled but not importable; continuing without FDI.")
            return None
        kwargs = fdi_cfg.model_dump(exclude={"enabled"}, exclude_unset=True)
        try:
            return FDIsystem(**kwargs)
        except Exception as e:
            # Keep parity with prior behavior: warn and continue without FDI
            logging.warning("Failed to instantiate FDIsystem (%s); continuing without FDI.", e, exc_info=True)
            return None
#=================================================================================\\\