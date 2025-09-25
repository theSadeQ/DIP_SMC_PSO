#==========================================================================================\\\
#======================== src/interfaces/data_exchange/__init__.py =====================\\\
#==========================================================================================\\\
"""
Data exchange and serialization framework for interfaces.
This module provides efficient, type-safe serialization and deserialization
across multiple formats including JSON, MessagePack, Protocol Buffers,
and custom binary formats optimized for real-time applications.
"""

from .serializers import (
    SerializationFormat, SerializerInterface, SerializationError,
    JSONSerializer, MessagePackSerializer, PickleSerializer,
    BinarySerializer, CompressionSerializer
)
from .schemas import (
    SchemaValidator, ValidationError, DataSchema,
    JSONSchema, MessageSchema, FieldType
)
from .data_types import (
    SerializableData, DataMessage, DataPacket,
    MessageHeader, MessageMetadata
)
from .factory import SerializerFactory, create_serializer
from .performance import PerformanceSerializer, SerializationMetrics
from .streaming import StreamingSerializer, DataStream, StreamConfig

__all__ = [
    # Core serialization
    'SerializationFormat', 'SerializerInterface', 'SerializationError',
    'JSONSerializer', 'MessagePackSerializer', 'PickleSerializer',
    'BinarySerializer', 'CompressionSerializer',

    # Schema validation
    'SchemaValidator', 'ValidationError', 'DataSchema',
    'JSONSchema', 'MessageSchema', 'FieldType',

    # Data types
    'SerializableData', 'DataMessage', 'DataPacket',
    'MessageHeader', 'MessageMetadata',

    # Factory and creation
    'SerializerFactory', 'create_serializer',

    # Performance optimization
    'PerformanceSerializer', 'SerializationMetrics',

    # Streaming support
    'StreamingSerializer', 'DataStream', 'StreamConfig'
]