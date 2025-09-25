#==========================================================================================\\\
#====================== src/simulation/core/simulation_context.py ======================\\\
#==========================================================================================\\\

"""Enhanced simulation context management with framework integration."""

from __future__ import annotations

import logging
from typing import Optional, List, Any, Dict, Union

# Import the necessary components
from src.config import load_config, ConfigSchema
from .interfaces import SimulationEngine
from src.utils.config_compatibility import wrap_physics_config

try:
    # Optional: FDI system may not be present in some builds
    from ...analysis.fault_detection.fdi import FaultDetectionInterface as FDIsystem  # type: ignore
except Exception:
    FDIsystem = None  # type: ignore


class SimulationContext:
    """Enhanced simulation context with framework integration.

    Centralizes simulation setup including configuration loading,
    dynamics model selection, and framework component initialization.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the simulation context.

        Parameters
        ----------
        config_path : str, optional
            Path to configuration file
        """
        self.config: ConfigSchema = load_config(config_path, allow_unknown=True)
        self.dynamics_model = self._initialize_dynamics_model()
        self._components: Dict[str, Any] = {}

    def _initialize_dynamics_model(self) -> Any:
        """Initialize the dynamics model based on configuration.

        Returns
        -------
        Any
            Initialized dynamics model
        """
        # Import dynamics lazily to avoid circular imports
        try:
            from ...plant.models.dynamics import DoubleInvertedPendulum as DIPDynamics
        except (ModuleNotFoundError, ImportError) as exc:
            raise RuntimeError("Double inverted pendulum dynamics model not found (light)") from exc

        full_model_cls = None
        full_import_error = None
        try:
            from ...plant.models.full.dynamics import FullDIPDynamics as _FullDIPDynamics
        except (ModuleNotFoundError, ImportError) as exc:
            full_import_error = exc
        else:
            full_model_cls = _FullDIPDynamics

        use_full = self.config.simulation.use_full_dynamics
        physics_cfg = wrap_physics_config(self.config.physics)

        if use_full:
            logging.info("Initializing Full Nonlinear Dynamics Model.")
            if full_model_cls is None:
                raise RuntimeError("Double inverted pendulum dynamics model not found (full)") from full_import_error
            return full_model_cls(physics_cfg)

        logging.info("Initializing Simplified Dynamics Model.")
        return DIPDynamics(physics_cfg)

    def get_dynamics_model(self) -> Any:
        """Return the initialized dynamics model."""
        return self.dynamics_model

    def get_config(self) -> ConfigSchema:
        """Return the validated configuration."""
        return self.config

    def create_controller(self, name: Optional[str] = None, gains: Optional[List[float]] = None) -> Any:
        """Create a controller using the configuration.

        Parameters
        ----------
        name : str, optional
            Controller name (default: 'classical_smc')
        gains : list, optional
            Controller gains (uses config defaults if None)

        Returns
        -------
        Any
            Configured controller instance
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
        """Create FDI system if enabled in configuration.

        Returns
        -------
        Optional[Any]
            FDI system instance or None if disabled/unavailable
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
            logging.warning("Failed to instantiate FDIsystem (%s); continuing without FDI.", e, exc_info=True)
            return None

    def register_component(self, name: str, component: Any) -> None:
        """Register a simulation framework component.

        Parameters
        ----------
        name : str
            Component name
        component : Any
            Component instance
        """
        self._components[name] = component

    def get_component(self, name: str) -> Optional[Any]:
        """Get a registered component.

        Parameters
        ----------
        name : str
            Component name

        Returns
        -------
        Optional[Any]
            Component instance or None if not found
        """
        return self._components.get(name)

    def create_simulation_engine(self, engine_type: str = "sequential") -> SimulationEngine:
        """Create a simulation engine of specified type.

        Parameters
        ----------
        engine_type : str, optional
            Engine type ('sequential', 'batch', 'parallel', 'real_time')

        Returns
        -------
        SimulationEngine
            Configured simulation engine
        """
        if engine_type == "sequential":
            from ..orchestrators.sequential import SequentialOrchestrator
            return SequentialOrchestrator(self)
        elif engine_type == "batch":
            from ..orchestrators.batch import BatchOrchestrator
            return BatchOrchestrator(self)
        elif engine_type == "parallel":
            from ..orchestrators.parallel import ParallelOrchestrator
            return ParallelOrchestrator(self)
        elif engine_type == "real_time":
            from ..orchestrators.real_time import RealTimeOrchestrator
            return RealTimeOrchestrator(self)
        else:
            raise ValueError(f"Unknown engine type: {engine_type}")

    def get_simulation_parameters(self) -> Dict[str, Any]:
        """Get simulation parameters from configuration.

        Returns
        -------
        dict
            Simulation parameters
        """
        sim_config = self.config.simulation
        return {
            "dt": getattr(sim_config, "dt", 0.01),
            "use_full_dynamics": getattr(sim_config, "use_full_dynamics", False),
            "safety": getattr(sim_config, "safety", None),
            "integration_method": getattr(sim_config, "integration_method", "rk4"),
            "real_time": getattr(sim_config, "real_time", False)
        }