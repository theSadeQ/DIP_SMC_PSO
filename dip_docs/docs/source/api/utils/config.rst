========================
Configuration Management
========================
.. currentmodule:: src.config

Overview
--------
Centralized configuration management system using Pydantic for validation and YAML for configuration files. Provides type-safe loading, validation, and access to simulation parameters, controller settings, and system configurations for the double-inverted pendulum project.

Examples
--------
.. doctest::

   >>> from src.config import load_config
   >>> # Load and validate project configuration
   >>> config = load_config("config.yaml")
   >>> # Access validated configuration parameters
   >>> dt = config.simulation.dt
   >>> controller_gains = config.controllers.classical_smc.gains

API Summary
-----------
.. autosummary::
   :toctree: _autosummary
   :recursive:

   src.config

Detailed API
------------
.. automodule:: src.config
   :members:
   :undoc-members:
   :show-inheritance: