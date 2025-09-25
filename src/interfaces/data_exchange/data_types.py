#==========================================================================================\\\
#====================== src/interfaces/data_exchange/data_types.py =====================\\\
#==========================================================================================\\\
"""
Core data types for the data exchange framework.
This module defines fundamental data structures used throughout the
serialization and communication system, including messages, packets,
headers, and metadata structures.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Union, TypeVar, Generic
from enum import Enum
import numpy as np

T = TypeVar('T')


class MessageType(Enum):
    """Message type enumeration."""
    DATA = "data"
    COMMAND = "command"
    STATUS = "status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    CONFIGURATION = "configuration"
    TELEMETRY = "telemetry"


class Priority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    REALTIME = 5


class CompressionType(Enum):
    """Compression algorithm types."""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"
    LZ4 = "lz4"
    ZSTD = "zstd"


class EncodingType(Enum):
    """Data encoding types."""
    UTF8 = "utf-8"
    ASCII = "ascii"
    BINARY = "binary"
    BASE64 = "base64"


@dataclass
class MessageHeader:
    """Message header with metadata."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.DATA
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    destination: str = "broadcast"
    priority: Priority = Priority.NORMAL
    sequence_number: int = 0
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl: Optional[float] = None  # Time to live in seconds
    version: str = "1.0"


@dataclass
class MessageMetadata:
    """Extended message metadata."""
    content_type: str = "application/json"
    content_length: int = 0
    encoding: EncodingType = EncodingType.UTF8
    compression: CompressionType = CompressionType.NONE
    checksum: Optional[str] = None
    encryption: Optional[str] = None
    routing_key: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    custom_headers: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SerializableData:
    """Base class for serializable data structures."""
    data: Any
    schema_version: str = "1.0"
    data_type: str = "generic"
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validate data structure."""
        return self.data is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'data': self._serialize_data(self.data),
            'schema_version': self.schema_version,
            'data_type': self.data_type,
            'created_at': self.created_at,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SerializableData':
        """Create from dictionary representation."""
        return cls(
            data=cls._deserialize_data(data.get('data')),
            schema_version=data.get('schema_version', '1.0'),
            data_type=data.get('data_type', 'generic'),
            created_at=data.get('created_at', time.time()),
            metadata=data.get('metadata', {})
        )

    @staticmethod
    def _serialize_data(data: Any) -> Any:
        """Serialize data for JSON compatibility."""
        if isinstance(data, np.ndarray):
            return {
                '__type__': 'numpy.ndarray',
                'data': data.tolist(),
                'dtype': str(data.dtype),
                'shape': data.shape
            }
        elif isinstance(data, (np.integer, np.floating)):
            return {
                '__type__': 'numpy.scalar',
                'data': data.item(),
                'dtype': str(data.dtype)
            }
        elif hasattr(data, 'to_dict'):
            return data.to_dict()
        else:
            return data

    @staticmethod
    def _deserialize_data(data: Any) -> Any:
        """Deserialize data from JSON representation."""
        if isinstance(data, dict) and '__type__' in data:
            if data['__type__'] == 'numpy.ndarray':
                return np.array(data['data'], dtype=data['dtype']).reshape(data['shape'])
            elif data['__type__'] == 'numpy.scalar':
                return np.dtype(data['dtype']).type(data['data'])
        return data


@dataclass
class DataMessage(Generic[T]):
    """Typed data message structure."""
    header: MessageHeader
    payload: T
    metadata: MessageMetadata = field(default_factory=MessageMetadata)

    def validate(self) -> bool:
        """Validate message structure."""
        return (
            self.header is not None and
            self.payload is not None and
            self.metadata is not None
        )

    def is_expired(self) -> bool:
        """Check if message has expired based on TTL."""
        if self.header.ttl is None:
            return False
        return (time.time() - self.header.timestamp) > self.header.ttl

    def get_age(self) -> float:
        """Get message age in seconds."""
        return time.time() - self.header.timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'header': {
                'message_id': self.header.message_id,
                'message_type': self.header.message_type.value,
                'timestamp': self.header.timestamp,
                'source': self.header.source,
                'destination': self.header.destination,
                'priority': self.header.priority.value,
                'sequence_number': self.header.sequence_number,
                'correlation_id': self.header.correlation_id,
                'reply_to': self.header.reply_to,
                'ttl': self.header.ttl,
                'version': self.header.version
            },
            'payload': self._serialize_payload(self.payload),
            'metadata': {
                'content_type': self.metadata.content_type,
                'content_length': self.metadata.content_length,
                'encoding': self.metadata.encoding.value,
                'compression': self.metadata.compression.value,
                'checksum': self.metadata.checksum,
                'encryption': self.metadata.encryption,
                'routing_key': self.metadata.routing_key,
                'tags': self.metadata.tags,
                'custom_headers': self.metadata.custom_headers
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataMessage':
        """Create message from dictionary."""
        header_data = data.get('header', {})
        metadata_data = data.get('metadata', {})

        header = MessageHeader(
            message_id=header_data.get('message_id', str(uuid.uuid4())),
            message_type=MessageType(header_data.get('message_type', 'data')),
            timestamp=header_data.get('timestamp', time.time()),
            source=header_data.get('source', 'unknown'),
            destination=header_data.get('destination', 'broadcast'),
            priority=Priority(header_data.get('priority', 2)),
            sequence_number=header_data.get('sequence_number', 0),
            correlation_id=header_data.get('correlation_id'),
            reply_to=header_data.get('reply_to'),
            ttl=header_data.get('ttl'),
            version=header_data.get('version', '1.0')
        )

        metadata = MessageMetadata(
            content_type=metadata_data.get('content_type', 'application/json'),
            content_length=metadata_data.get('content_length', 0),
            encoding=EncodingType(metadata_data.get('encoding', 'utf-8')),
            compression=CompressionType(metadata_data.get('compression', 'none')),
            checksum=metadata_data.get('checksum'),
            encryption=metadata_data.get('encryption'),
            routing_key=metadata_data.get('routing_key'),
            tags=metadata_data.get('tags', {}),
            custom_headers=metadata_data.get('custom_headers', {})
        )

        payload = cls._deserialize_payload(data.get('payload'))

        return cls(header=header, payload=payload, metadata=metadata)

    @staticmethod
    def _serialize_payload(payload: T) -> Any:
        """Serialize payload for transmission."""
        if hasattr(payload, 'to_dict'):
            return payload.to_dict()
        elif isinstance(payload, SerializableData):
            return payload.to_dict()
        else:
            return SerializableData._serialize_data(payload)

    @staticmethod
    def _deserialize_payload(payload_data: Any) -> T:
        """Deserialize payload from transmission format."""
        return SerializableData._deserialize_data(payload_data)


@dataclass
class DataPacket:
    """Low-level data packet for binary transmission."""
    version: int = 1
    packet_type: int = 0
    flags: int = 0
    sequence_number: int = 0
    payload_length: int = 0
    payload: bytes = field(default_factory=bytes)
    checksum: int = 0

    def pack(self) -> bytes:
        """Pack packet into binary format."""
        import struct

        # Update payload length
        self.payload_length = len(self.payload)

        # Calculate checksum
        self.checksum = self._calculate_checksum()

        # Pack header (24 bytes)
        header = struct.pack(
            '>BBHIII',  # Big-endian format
            self.version,
            self.packet_type,
            self.flags,
            self.sequence_number,
            self.payload_length,
            self.checksum
        )

        return header + self.payload

    @classmethod
    def unpack(cls, data: bytes) -> 'DataPacket':
        """Unpack packet from binary format."""
        import struct

        if len(data) < 12:  # Minimum header size
            raise ValueError("Insufficient data for packet header")

        # Unpack header
        header_data = struct.unpack('>BBHIII', data[:12])
        version, packet_type, flags, sequence_number, payload_length, checksum = header_data

        # Extract payload
        if len(data) < 12 + payload_length:
            raise ValueError("Insufficient data for payload")

        payload = data[12:12 + payload_length]

        packet = cls(
            version=version,
            packet_type=packet_type,
            flags=flags,
            sequence_number=sequence_number,
            payload_length=payload_length,
            payload=payload,
            checksum=checksum
        )

        # Verify checksum
        if packet._calculate_checksum() != checksum:
            raise ValueError("Checksum mismatch")

        return packet

    def _calculate_checksum(self) -> int:
        """Calculate simple checksum for packet integrity."""
        checksum = 0
        checksum ^= self.version
        checksum ^= self.packet_type
        checksum ^= self.flags
        checksum ^= self.sequence_number
        checksum ^= self.payload_length

        for byte in self.payload:
            checksum ^= byte

        return checksum & 0xFFFFFFFF

    def is_valid(self) -> bool:
        """Check if packet is valid."""
        return (
            self.version > 0 and
            self.payload_length == len(self.payload) and
            self._calculate_checksum() == self.checksum
        )


@dataclass
class ControlMessage(SerializableData):
    """Control message for system commands."""
    command: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    target: str = "system"
    timeout: Optional[float] = None

    def __post_init__(self):
        super().__init__()
        self.data_type = "control_message"


@dataclass
class StatusMessage(SerializableData):
    """Status message for system state reporting."""
    status: str
    details: Dict[str, Any] = field(default_factory=dict)
    error_code: Optional[int] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        super().__init__()
        self.data_type = "status_message"

    def is_error(self) -> bool:
        """Check if this is an error status."""
        return self.error_code is not None or self.status.lower() in ['error', 'failed', 'failure']


@dataclass
class TelemetryMessage(SerializableData):
    """Telemetry message for sensor data and measurements."""
    sensor_id: str
    measurements: Dict[str, Union[float, int, str]] = field(default_factory=dict)
    units: Dict[str, str] = field(default_factory=dict)
    quality: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        super().__init__()
        self.data_type = "telemetry_message"

    def add_measurement(self, name: str, value: Union[float, int, str],
                       unit: str = "", quality: float = 1.0) -> None:
        """Add a measurement to the telemetry."""
        self.measurements[name] = value
        if unit:
            self.units[name] = unit
        self.quality[name] = quality


@dataclass
class ConfigurationMessage(SerializableData):
    """Configuration message for system settings."""
    config_section: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    operation: str = "update"  # update, get, delete

    def __post_init__(self):
        super().__init__()
        self.data_type = "configuration_message"


# Type aliases for common message types
ControlDataMessage = DataMessage[ControlMessage]
StatusDataMessage = DataMessage[StatusMessage]
TelemetryDataMessage = DataMessage[TelemetryMessage]
ConfigurationDataMessage = DataMessage[ConfigurationMessage]