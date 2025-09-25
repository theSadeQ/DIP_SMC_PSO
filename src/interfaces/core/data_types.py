#==========================================================================================\\\
#====================== src/interfaces/core/data_types.py ===============================\\\
#==========================================================================================\\\

"""
Core data types for communication framework.

This module defines standardized data structures used throughout the
communication framework, providing type safety and consistent interfaces
for configuration, monitoring, and data exchange.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum
import time
import uuid
from datetime import datetime


class InterfaceType(Enum):
    """Interface type enumeration."""
    UDP = "udp"
    TCP = "tcp"
    HTTP = "http"
    WEBSOCKET = "websocket"
    SERIAL = "serial"
    MODBUS = "modbus"
    ETHERCAT = "ethercat"
    GRPC = "grpc"
    MQTT = "mqtt"
    ZEROMQ = "zeromq"
    FILE = "file"
    DATABASE = "database"


class TransportType(Enum):
    """Transport layer type."""
    RELIABLE = "reliable"      # TCP-like guarantees
    UNRELIABLE = "unreliable"  # UDP-like best effort
    STREAM = "stream"          # Continuous data flow
    DATAGRAM = "datagram"      # Discrete messages


class SecurityLevel(Enum):
    """Security level enumeration."""
    NONE = "none"
    BASIC = "basic"
    ENCRYPTED = "encrypted"
    AUTHENTICATED = "authenticated"
    MUTUAL_TLS = "mutual_tls"


@dataclass
class Message:
    """Standard message structure for all communications."""

    # Message identification
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    # Message routing
    source: str = "unknown"
    destination: Optional[str] = None
    reply_to: Optional[str] = None

    # Message content
    message_type: str = "data"
    payload: Any = None
    headers: Dict[str, Any] = field(default_factory=dict)

    # Message properties
    priority: int = 2  # 1=low, 2=normal, 3=high, 4=critical
    ttl: Optional[float] = None  # Time to live in seconds
    compression: Optional[str] = None
    encryption: Optional[str] = None

    # Delivery tracking
    retry_count: int = 0
    max_retries: int = 3
    delivery_attempts: List[float] = field(default_factory=list)

    def __post_init__(self):
        """Initialize delivery tracking."""
        if not self.delivery_attempts:
            self.delivery_attempts.append(self.timestamp)

    @property
    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.ttl is None:
            return False
        return time.time() > (self.timestamp + self.ttl)

    @property
    def age(self) -> float:
        """Get message age in seconds."""
        return time.time() - self.timestamp

    def add_header(self, key: str, value: Any) -> None:
        """Add header to message."""
        self.headers[key] = value

    def get_header(self, key: str, default: Any = None) -> Any:
        """Get header value."""
        return self.headers.get(key, default)


@dataclass
class ConnectionInfo:
    """Connection information and status."""

    # Connection identification
    connection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    endpoint: str = "unknown"
    interface_type: InterfaceType = InterfaceType.TCP

    # Connection state
    state: str = "disconnected"
    connected_at: Optional[float] = None
    disconnected_at: Optional[float] = None
    last_activity: Optional[float] = None

    # Connection properties
    local_address: Optional[Tuple[str, int]] = None
    remote_address: Optional[Tuple[str, int]] = None
    transport_type: TransportType = TransportType.RELIABLE
    security_level: SecurityLevel = SecurityLevel.NONE

    # Connection metrics
    bytes_sent: int = 0
    bytes_received: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    errors: int = 0
    reconnections: int = 0

    # Connection configuration
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self.state == "connected"

    @property
    def connection_duration(self) -> Optional[float]:
        """Get connection duration in seconds."""
        if self.connected_at is None:
            return None
        end_time = self.disconnected_at or time.time()
        return end_time - self.connected_at

    @property
    def idle_time(self) -> Optional[float]:
        """Get idle time since last activity."""
        if self.last_activity is None:
            return None
        return time.time() - self.last_activity

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()


@dataclass
class InterfaceConfig:
    """Configuration for communication interfaces."""

    # Interface identification
    name: str = "default"
    interface_type: InterfaceType = InterfaceType.TCP
    description: str = ""

    # Connection settings
    endpoint: str = "localhost:8080"
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    keep_alive: bool = True

    # Buffer settings
    send_buffer_size: int = 8192
    receive_buffer_size: int = 8192
    max_message_size: int = 1024 * 1024  # 1MB

    # Security settings
    security_level: SecurityLevel = SecurityLevel.NONE
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    auth_token: Optional[str] = None

    # Protocol settings
    serialization: str = "json"
    compression: Optional[str] = None
    encoding: str = "utf-8"

    # Quality of Service
    message_ordering: bool = False
    duplicate_detection: bool = False
    delivery_confirmation: bool = False

    # Monitoring
    enable_metrics: bool = True
    enable_logging: bool = True
    log_level: str = "INFO"

    # Custom settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get custom setting value."""
        return self.custom_settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """Set custom setting value."""
        self.custom_settings[key] = value


@dataclass
class ErrorInfo:
    """Error information for diagnostics."""

    # Error identification
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    # Error details
    error_type: str = "unknown"
    error_code: Optional[str] = None
    message: str = ""
    details: Optional[str] = None

    # Error context
    component: str = "unknown"
    operation: Optional[str] = None
    connection_id: Optional[str] = None
    message_id: Optional[str] = None

    # Error classification
    severity: str = "error"  # debug, info, warning, error, critical
    category: str = "communication"  # communication, configuration, hardware, etc.
    recoverable: bool = True

    # Error tracking
    retry_count: int = 0
    related_errors: List[str] = field(default_factory=list)
    resolution: Optional[str] = None

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def age(self) -> float:
        """Get error age in seconds."""
        return time.time() - self.timestamp

    def add_related_error(self, error_id: str) -> None:
        """Add related error ID."""
        if error_id not in self.related_errors:
            self.related_errors.append(error_id)


@dataclass
class PerformanceMetrics:
    """Performance metrics for interfaces."""

    # Timing metrics
    latency_min: float = float('inf')
    latency_max: float = 0.0
    latency_avg: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0

    # Throughput metrics
    messages_per_second: float = 0.0
    bytes_per_second: float = 0.0
    operations_per_second: float = 0.0

    # Reliability metrics
    success_rate: float = 0.0
    error_rate: float = 0.0
    timeout_rate: float = 0.0
    retry_rate: float = 0.0

    # Resource metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    network_usage: float = 0.0
    connection_count: int = 0

    # Queue metrics
    queue_depth: int = 0
    queue_latency: float = 0.0
    dropped_messages: int = 0
    backpressure_events: int = 0

    # Time window
    measurement_start: float = field(default_factory=time.time)
    measurement_end: float = field(default_factory=time.time)
    sample_count: int = 0

    @property
    def measurement_duration(self) -> float:
        """Get measurement duration in seconds."""
        return self.measurement_end - self.measurement_start

    def update_latency(self, latency: float) -> None:
        """Update latency metrics with new sample."""
        self.latency_min = min(self.latency_min, latency)
        self.latency_max = max(self.latency_max, latency)

        # Update running average
        self.latency_avg = ((self.latency_avg * self.sample_count + latency) /
                           (self.sample_count + 1))
        self.sample_count += 1


@dataclass
class CommunicationStats:
    """Comprehensive communication statistics."""

    # Basic counters
    total_connections: int = 0
    active_connections: int = 0
    failed_connections: int = 0

    # Message counters
    messages_sent: int = 0
    messages_received: int = 0
    messages_dropped: int = 0
    messages_retried: int = 0

    # Byte counters
    bytes_sent: int = 0
    bytes_received: int = 0

    # Error counters
    connection_errors: int = 0
    timeout_errors: int = 0
    serialization_errors: int = 0
    protocol_errors: int = 0

    # Performance metrics
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)

    # Historical data
    hourly_stats: Dict[str, Any] = field(default_factory=dict)
    daily_stats: Dict[str, Any] = field(default_factory=dict)

    # Status tracking
    last_reset: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)

    def reset_counters(self) -> None:
        """Reset all counters."""
        self.total_connections = 0
        self.active_connections = 0
        self.failed_connections = 0
        self.messages_sent = 0
        self.messages_received = 0
        self.messages_dropped = 0
        self.messages_retried = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self.connection_errors = 0
        self.timeout_errors = 0
        self.serialization_errors = 0
        self.protocol_errors = 0
        self.last_reset = time.time()

    def update_timestamp(self) -> None:
        """Update last update timestamp."""
        self.last_update = time.time()

    @property
    def uptime(self) -> float:
        """Get uptime since last reset in seconds."""
        return time.time() - self.last_reset


@dataclass
class QueueConfig:
    """Configuration for message queues."""

    # Queue properties
    max_size: int = 1000
    timeout: float = 30.0
    priority_enabled: bool = False

    # Overflow behavior
    overflow_strategy: str = "drop_oldest"  # drop_oldest, drop_newest, block, reject

    # Persistence
    persistent: bool = False
    persistence_file: Optional[str] = None

    # Monitoring
    enable_metrics: bool = True
    warning_threshold: float = 0.8  # Warn when queue is 80% full

    # Serialization
    serializer: str = "pickle"

    def get_warning_size(self) -> int:
        """Get queue size that triggers warning."""
        return int(self.max_size * self.warning_threshold)


@dataclass
class DeviceInfo:
    """Device information structure."""

    # Device identification
    device_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "unknown"
    manufacturer: str = "unknown"
    model: str = "unknown"
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None

    # Device properties
    device_type: str = "generic"
    capabilities: List[str] = field(default_factory=list)
    supported_protocols: List[str] = field(default_factory=list)

    # Connection info
    interface_type: InterfaceType = InterfaceType.SERIAL
    address: Optional[str] = None
    baudrate: Optional[int] = None

    # Status
    online: bool = False
    last_seen: Optional[float] = None
    health_status: str = "unknown"

    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_online(self) -> bool:
        """Check if device is online."""
        return self.online

    @property
    def time_since_seen(self) -> Optional[float]:
        """Get time since last seen in seconds."""
        if self.last_seen is None:
            return None
        return time.time() - self.last_seen

    def update_last_seen(self) -> None:
        """Update last seen timestamp."""
        self.last_seen = time.time()
        self.online = True