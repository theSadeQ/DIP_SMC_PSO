#==========================================================================================\\\
#======================= src/interfaces/core/protocols.py ===============================\\\
#==========================================================================================\\\

"""
Core protocols and interfaces for communication systems.

This module defines the fundamental protocols that all communication interfaces
must implement, providing consistent abstractions for messaging, connections,
serialization, and error handling in control systems.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable, AsyncIterator, Iterator
from dataclasses import dataclass
from enum import Enum
import time


class ConnectionState(Enum):
    """Connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    CLOSED = "closed"


class MessageType(Enum):
    """Message type enumeration."""
    COMMAND = "command"
    DATA = "data"
    STATUS = "status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    ACK = "acknowledgment"
    CONFIG = "configuration"


class Priority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class MessageMetadata:
    """Message metadata for tracking and routing."""
    message_id: str
    timestamp: float
    message_type: MessageType
    priority: Priority
    source: str
    destination: Optional[str] = None
    correlation_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    ttl: Optional[float] = None  # Time to live in seconds


class CommunicationProtocol(ABC):
    """
    Abstract base protocol for all communication interfaces.

    This protocol defines the core interface that all communication
    systems must implement, providing consistency across different
    transport mechanisms.
    """

    @abstractmethod
    async def connect(self, config: Dict[str, Any]) -> bool:
        """
        Establish connection with the remote endpoint.

        Parameters
        ----------
        config : Dict[str, Any]
            Connection configuration parameters

        Returns
        -------
        bool
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Close connection gracefully.

        Returns
        -------
        bool
            True if disconnection successful, False otherwise
        """
        pass

    @abstractmethod
    async def send(self, data: Any, metadata: Optional[MessageMetadata] = None) -> bool:
        """
        Send data to the remote endpoint.

        Parameters
        ----------
        data : Any
            Data to send
        metadata : MessageMetadata, optional
            Message metadata for tracking and routing

        Returns
        -------
        bool
            True if send successful, False otherwise
        """
        pass

    @abstractmethod
    async def receive(self, timeout: Optional[float] = None) -> Optional[Tuple[Any, MessageMetadata]]:
        """
        Receive data from the remote endpoint.

        Parameters
        ----------
        timeout : float, optional
            Timeout in seconds, None for blocking

        Returns
        -------
        Tuple[Any, MessageMetadata] or None
            Received data and metadata, or None if timeout/error
        """
        pass

    @abstractmethod
    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """Get communication statistics."""
        pass


class MessageProtocol(ABC):
    """
    Protocol for message handling and routing.

    Defines how messages are processed, routed, and handled
    within the communication system.
    """

    @abstractmethod
    async def process_message(self, data: Any, metadata: MessageMetadata) -> Optional[Any]:
        """
        Process incoming message.

        Parameters
        ----------
        data : Any
            Message data
        metadata : MessageMetadata
            Message metadata

        Returns
        -------
        Any or None
            Response data or None
        """
        pass

    @abstractmethod
    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        """
        Register message handler for specific message type.

        Parameters
        ----------
        message_type : MessageType
            Type of message to handle
        handler : Callable
            Handler function
        """
        pass

    @abstractmethod
    def unregister_handler(self, message_type: MessageType) -> None:
        """
        Unregister message handler.

        Parameters
        ----------
        message_type : MessageType
            Type of message to stop handling
        """
        pass

    @abstractmethod
    async def route_message(self, data: Any, metadata: MessageMetadata, destination: str) -> bool:
        """
        Route message to specific destination.

        Parameters
        ----------
        data : Any
            Message data
        metadata : MessageMetadata
            Message metadata
        destination : str
            Target destination

        Returns
        -------
        bool
            True if routing successful
        """
        pass


class ConnectionProtocol(ABC):
    """
    Protocol for connection management.

    Defines connection lifecycle management, including
    establishment, maintenance, and cleanup.
    """

    @abstractmethod
    async def establish_connection(self, endpoint: str, config: Dict[str, Any]) -> str:
        """
        Establish new connection.

        Parameters
        ----------
        endpoint : str
            Remote endpoint identifier
        config : Dict[str, Any]
            Connection configuration

        Returns
        -------
        str
            Connection identifier
        """
        pass

    @abstractmethod
    async def close_connection(self, connection_id: str) -> bool:
        """
        Close specific connection.

        Parameters
        ----------
        connection_id : str
            Connection to close

        Returns
        -------
        bool
            True if successful
        """
        pass

    @abstractmethod
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get connection information.

        Parameters
        ----------
        connection_id : str
            Connection identifier

        Returns
        -------
        Dict[str, Any] or None
            Connection information or None if not found
        """
        pass

    @abstractmethod
    def list_connections(self) -> List[str]:
        """
        List all active connections.

        Returns
        -------
        List[str]
            List of connection identifiers
        """
        pass

    @abstractmethod
    async def health_check(self, connection_id: str) -> bool:
        """
        Check connection health.

        Parameters
        ----------
        connection_id : str
            Connection to check

        Returns
        -------
        bool
            True if healthy
        """
        pass


class SerializationProtocol(ABC):
    """
    Protocol for data serialization and deserialization.

    Provides consistent interface for converting between
    Python objects and wire formats.
    """

    @abstractmethod
    def serialize(self, data: Any) -> bytes:
        """
        Serialize data to bytes.

        Parameters
        ----------
        data : Any
            Data to serialize

        Returns
        -------
        bytes
            Serialized data
        """
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """
        Deserialize bytes to data.

        Parameters
        ----------
        data : bytes
            Data to deserialize

        Returns
        -------
        Any
            Deserialized data
        """
        pass

    @abstractmethod
    def get_content_type(self) -> str:
        """
        Get serialization content type.

        Returns
        -------
        str
            Content type identifier
        """
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """
        Check if serializer supports streaming.

        Returns
        -------
        bool
            True if streaming supported
        """
        pass


class ErrorHandlerProtocol(ABC):
    """
    Protocol for error handling and recovery.

    Defines how errors are handled, logged, and recovered
    from in communication systems.
    """

    @abstractmethod
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Handle communication error.

        Parameters
        ----------
        error : Exception
            Error that occurred
        context : Dict[str, Any]
            Error context information

        Returns
        -------
        bool
            True if error was handled and recovery attempted
        """
        pass

    @abstractmethod
    def should_retry(self, error: Exception, retry_count: int) -> bool:
        """
        Determine if operation should be retried.

        Parameters
        ----------
        error : Exception
            Error that occurred
        retry_count : int
            Current retry count

        Returns
        -------
        bool
            True if should retry
        """
        pass

    @abstractmethod
    def get_retry_delay(self, retry_count: int) -> float:
        """
        Get delay before retry.

        Parameters
        ----------
        retry_count : int
            Current retry count

        Returns
        -------
        float
            Delay in seconds
        """
        pass

    @abstractmethod
    def log_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """
        Log error with context.

        Parameters
        ----------
        error : Exception
            Error to log
        context : Dict[str, Any]
            Error context
        """
        pass


class StreamingProtocol(ABC):
    """
    Protocol for streaming data interfaces.

    Defines interface for continuous data streaming
    with flow control and buffering.
    """

    @abstractmethod
    async def start_stream(self, config: Dict[str, Any]) -> str:
        """
        Start data stream.

        Parameters
        ----------
        config : Dict[str, Any]
            Stream configuration

        Returns
        -------
        str
            Stream identifier
        """
        pass

    @abstractmethod
    async def stop_stream(self, stream_id: str) -> bool:
        """
        Stop data stream.

        Parameters
        ----------
        stream_id : str
            Stream to stop

        Returns
        -------
        bool
            True if successful
        """
        pass

    @abstractmethod
    async def read_stream(self, stream_id: str, count: Optional[int] = None) -> AsyncIterator[Any]:
        """
        Read from data stream.

        Parameters
        ----------
        stream_id : str
            Stream to read from
        count : int, optional
            Maximum number of items to read

        Yields
        ------
        Any
            Stream data items
        """
        pass

    @abstractmethod
    async def write_stream(self, stream_id: str, data: Any) -> bool:
        """
        Write to data stream.

        Parameters
        ----------
        stream_id : str
            Stream to write to
        data : Any
            Data to write

        Returns
        -------
        bool
            True if successful
        """
        pass

    @abstractmethod
    def get_stream_stats(self, stream_id: str) -> Dict[str, Any]:
        """
        Get stream statistics.

        Parameters
        ----------
        stream_id : str
            Stream identifier

        Returns
        -------
        Dict[str, Any]
            Stream statistics
        """
        pass


class DeviceProtocol(ABC):
    """
    Protocol for hardware device interfaces.

    Defines consistent interface for interacting with
    physical devices and hardware components.
    """

    @abstractmethod
    async def initialize_device(self, config: Dict[str, Any]) -> bool:
        """
        Initialize device with configuration.

        Parameters
        ----------
        config : Dict[str, Any]
            Device configuration

        Returns
        -------
        bool
            True if initialization successful
        """
        pass

    @abstractmethod
    async def read_from_device(self, register: str, count: int = 1) -> Any:
        """
        Read data from device.

        Parameters
        ----------
        register : str
            Device register or address
        count : int
            Number of values to read

        Returns
        -------
        Any
            Read data
        """
        pass

    @abstractmethod
    async def write_to_device(self, register: str, value: Any) -> bool:
        """
        Write data to device.

        Parameters
        ----------
        register : str
            Device register or address
        value : Any
            Value to write

        Returns
        -------
        bool
            True if successful
        """
        pass

    @abstractmethod
    def get_device_info(self) -> Dict[str, Any]:
        """
        Get device information.

        Returns
        -------
        Dict[str, Any]
            Device information
        """
        pass

    @abstractmethod
    async def device_health_check(self) -> bool:
        """
        Check device health status.

        Returns
        -------
        bool
            True if device is healthy
        """
        pass

    @abstractmethod
    async def reset_device(self) -> bool:
        """
        Reset device to initial state.

        Returns
        -------
        bool
            True if reset successful
        """
        pass