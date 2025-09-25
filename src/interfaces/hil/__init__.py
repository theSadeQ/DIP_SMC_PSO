#==========================================================================================\\\
#============================== src/interfaces/hil/__init__.py ===========================\\\
#==========================================================================================\\\
"""
Enhanced Hardware-in-the-Loop (HIL) system for control engineering.
This module provides advanced HIL capabilities including real-time simulation,
hardware integration, fault injection, and comprehensive testing frameworks
for control system validation and verification.
"""

from .enhanced_hil import EnhancedHILSystem, HILConfig, HILMode, TestScenario
from .real_time_sync import RealTimeScheduler, TimingConstraints, DeadlineMissHandler
from .fault_injection import FaultInjector, FaultType, FaultScenario
from .test_automation import HILTestFramework, TestSuite, TestCase
from .data_logging import HILDataLogger, LoggingConfig
from .simulation_bridge import SimulationBridge, ModelInterface

# Legacy compatibility
from .controller_client import HILControllerClient, run_client
from .plant_server import PlantServer

__all__ = [
    # Enhanced HIL System
    'EnhancedHILSystem', 'HILConfig', 'HILMode', 'TestScenario',

    # Real-time capabilities
    'RealTimeScheduler', 'TimingConstraints', 'DeadlineMissHandler',

    # Fault injection
    'FaultInjector', 'FaultType', 'FaultScenario',

    # Test automation
    'HILTestFramework', 'TestSuite', 'TestCase',

    # Data logging
    'HILDataLogger', 'LoggingConfig',

    # Simulation bridge
    'SimulationBridge', 'ModelInterface',

    # Legacy compatibility
    'HILControllerClient', 'run_client', 'PlantServer'
]