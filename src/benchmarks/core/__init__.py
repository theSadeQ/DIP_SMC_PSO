#==========================================================================================\\\
#====================== src/benchmarks/core/__init__.py ==================================\\\
#==========================================================================================\\\
"""
Core benchmarking infrastructure for control system evaluation.

This package provides the fundamental trial execution and orchestration
capabilities for statistical benchmarking of control systems.

Key Components:
- **Trial Runner**: Execute multiple independent simulation trials
- **Configuration Validation**: Ensure valid experimental setup
- **Error Handling**: Robust simulation execution with fallbacks
"""

from __future__ import annotations

from .trial_runner import (
    execute_single_trial,
    run_multiple_trials,
    validate_trial_configuration
)

__all__ = [
    'execute_single_trial',
    'run_multiple_trials',
    'validate_trial_configuration'
]