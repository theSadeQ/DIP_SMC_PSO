#==========================================================================================\\\
#====================== src/simulation/integrators/factory.py ===========================\\\
#==========================================================================================\\\

"""
Integrator Factory for creating numerical integration instances.

This module provides a factory pattern for instantiating different types
of numerical integrators with proper configuration and parameter management.
"""

from typing import Dict, Type, Any, Optional, Union
import logging

from .base import BaseIntegrator
from .fixed_step.euler import ForwardEuler, BackwardEuler
from .fixed_step.runge_kutta import RungeKutta4, RungeKutta2
from .adaptive.runge_kutta import AdaptiveRungeKutta, DormandPrince45
from .discrete.zero_order_hold import ZeroOrderHold


class IntegratorFactory:
    """
    Factory for creating numerical integrator instances.

    Provides centralized creation and management of integrators
    with validation and consistency checking.
    """

    # Registry of available integrator classes
    _integrator_registry: Dict[str, Type[BaseIntegrator]] = {
        'euler': ForwardEuler,
        'forward_euler': ForwardEuler,
        'backward_euler': BackwardEuler,
        'rk2': RungeKutta2,
        'rk4': RungeKutta4,
        'runge_kutta_4': RungeKutta4,
        'adaptive_rk': AdaptiveRungeKutta,
        'dormand_prince': DormandPrince45,
        'dp45': DormandPrince45,
        'zoh': ZeroOrderHold,
        'zero_order_hold': ZeroOrderHold
    }

    @classmethod
    def create_integrator(
        cls,
        integrator_type: str,
        dt: float = 0.01,
        **kwargs: Any
    ) -> BaseIntegrator:
        """
        Create an integrator instance of the specified type.

        Args:
            integrator_type: Type of integrator ('euler', 'rk4', 'adaptive_rk', etc.)
            dt: Integration time step (stored as attribute, not passed to constructor)
            **kwargs: Additional integrator-specific parameters

        Returns:
            Configured integrator instance

        Raises:
            ValueError: If integrator_type is not recognized
        """
        logger = logging.getLogger(__name__)

        # Normalize integrator type name
        integrator_type = integrator_type.lower().replace('-', '_').replace(' ', '_')

        if integrator_type not in cls._integrator_registry:
            available = list(cls._integrator_registry.keys())
            raise ValueError(f"Unknown integrator type '{integrator_type}'. Available: {available}")

        integrator_class = cls._integrator_registry[integrator_type]

        try:
            # Create integrator without dt parameter (dt is used per-integration call)
            integrator = integrator_class(**kwargs)

            # Store dt as an attribute for convenience
            integrator.default_dt = dt

            logger.debug(f"Created {integrator_type} integrator with default dt={dt}")
            return integrator

        except Exception as e:
            logger.error(f"Failed to create {integrator_type} integrator: {e}")
            raise

    @classmethod
    def list_available_integrators(cls) -> list[str]:
        """
        Get list of available integrator types.

        Returns:
            List of integrator type names
        """
        return list(cls._integrator_registry.keys())

    @classmethod
    def get_integrator_info(cls, integrator_type: str) -> Dict[str, Any]:
        """
        Get information about an integrator type.

        Args:
            integrator_type: Type of integrator

        Returns:
            Dictionary with integrator information
        """
        integrator_type = integrator_type.lower().replace('-', '_').replace(' ', '_')

        if integrator_type not in cls._integrator_registry:
            raise ValueError(f"Unknown integrator type '{integrator_type}'")

        integrator_class = cls._integrator_registry[integrator_type]

        return {
            'class_name': integrator_class.__name__,
            'module': integrator_class.__module__,
            'order': getattr(integrator_class, 'ORDER', None),
            'adaptive': 'adaptive' in integrator_type,
            'description': integrator_class.__doc__.split('\n')[0] if integrator_class.__doc__ else "No description"
        }

    @classmethod
    def register_integrator(cls, name: str, integrator_class: Type[BaseIntegrator]) -> None:
        """
        Register a custom integrator class.

        Args:
            name: Name to register the integrator under
            integrator_class: Integrator class to register
        """
        if not issubclass(integrator_class, BaseIntegrator):
            raise ValueError("Integrator class must inherit from BaseIntegrator")

        cls._integrator_registry[name.lower()] = integrator_class

    @classmethod
    def create_default_integrator(cls, dt: float = 0.01) -> BaseIntegrator:
        """
        Create a default integrator instance.

        Args:
            dt: Integration time step

        Returns:
            Default integrator (RK4)
        """
        return cls.create_integrator('rk4', dt=dt)


# Convenience functions for backwards compatibility
def create_integrator(integrator_type: str, dt: float = 0.01, **kwargs) -> BaseIntegrator:
    """Create integrator instance (convenience function)."""
    return IntegratorFactory.create_integrator(integrator_type, dt, **kwargs)


def get_available_integrators() -> list[str]:
    """Get available integrator types (convenience function)."""
    return IntegratorFactory.list_available_integrators()