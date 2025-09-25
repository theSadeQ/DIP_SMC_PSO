#==========================================================================================\\\
#============================= src/interfaces/core/__init__.py =============================\\\
#==========================================================================================\\\
"""
Core interfaces and protocols for the interfaces framework.
This module provides basic data types and communication protocols
for the interface system.
"""

# Import only what actually exists
from .protocols import (
    CommunicationProtocol, MessageProtocol, ConnectionProtocol,
    SerializationProtocol, ErrorHandlerProtocol, DeviceProtocol
)

from .data_types import (
    Message, ConnectionInfo, InterfaceConfig, ErrorInfo,
    PerformanceMetrics, CommunicationStats, QueueConfig, DeviceInfo,
    InterfaceType, TransportType, SecurityLevel
)

__all__ = [
    # Protocols that actually exist
    'CommunicationProtocol', 'MessageProtocol', 'ConnectionProtocol',
    'SerializationProtocol', 'ErrorHandlerProtocol', 'DeviceProtocol',

    # Data types that actually exist
    'Message', 'ConnectionInfo', 'InterfaceConfig', 'ErrorInfo',
    'PerformanceMetrics', 'CommunicationStats', 'QueueConfig', 'DeviceInfo',
    'InterfaceType', 'TransportType', 'SecurityLevel'
]