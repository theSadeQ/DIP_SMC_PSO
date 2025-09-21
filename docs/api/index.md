# API Reference Documentation

This section provides comprehensive API documentation for all modules in the DIP_SMC_PSO project.

## Modules

```{toctree}
:maxdepth: 2

core
controllers
optimizer
hil
config
```

## Auto-Generated Documentation

```{eval-rst}
.. automodule:: src.core.dynamics
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.controllers.factory
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: src.optimizer.pso_optimizer
   :members:
   :undoc-members:
   :show-inheritance:
```

## Overview

The API documentation is automatically generated from Python docstrings using Sphinx autodoc. This ensures the documentation stays synchronized with the codebase.

Key modules include:
- **Core**: Simulation engine and dynamics
- **Controllers**: All sliding mode control implementations
- **Optimizer**: PSO tuning algorithms
- **HIL**: Hardware-in-the-loop interfaces
- **Config**: Configuration management