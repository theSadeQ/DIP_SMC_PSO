#==========================================================================================\\\
#==================== src/interfaces/data_exchange/serializers.py =====================\\\
#==========================================================================================\\\
"""
Core serialization framework with multiple format support.
This module provides efficient serializers for various data formats
including JSON, MessagePack, Pickle, and custom binary formats
with compression and performance optimization capabilities.
"""

import json
import pickle
import gzip
import zlib
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union, Type, TypeVar
from enum import Enum
import logging
import time

try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False

try:
    import lz4.frame
    LZ4_AVAILABLE = True
except ImportError:
    LZ4_AVAILABLE = False

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

from .data_types import SerializableData, DataMessage, CompressionType

T = TypeVar('T')


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    MSGPACK = "msgpack"
    PICKLE = "pickle"
    BINARY = "binary"
    JSON_COMPRESSED = "json_compressed"
    MSGPACK_COMPRESSED = "msgpack_compressed"


class SerializationError(Exception):
    """Exception raised during serialization/deserialization."""

    def __init__(self, message: str, format_type: SerializationFormat,
                 original_error: Optional[Exception] = None):
        super().__init__(message)
        self.format_type = format_type
        self.original_error = original_error


class SerializerInterface(ABC):
    """Abstract interface for serializers."""

    @abstractmethod
    def serialize(self, data: Any) -> bytes:
        """Serialize data to bytes."""
        pass

    @abstractmethod
    def deserialize(self, data: bytes, target_type: Optional[Type[T]] = None) -> T:
        """Deserialize bytes to data."""
        pass

    @property
    @abstractmethod
    def format_type(self) -> SerializationFormat:
        """Get serialization format type."""
        pass

    @property
    @abstractmethod
    def content_type(self) -> str:
        """Get MIME content type."""
        pass

    def get_compression_ratio(self, original_data: Any) -> float:
        """Calculate compression ratio."""
        try:
            original_size = len(pickle.dumps(original_data))
            compressed_size = len(self.serialize(original_data))
            return original_size / compressed_size if compressed_size > 0 else 1.0
        except Exception:
            return 1.0


class JSONSerializer(SerializerInterface):
    """JSON serialization with custom encoder support."""

    def __init__(self, ensure_ascii: bool = False, sort_keys: bool = False,
                 indent: Optional[int] = None, compact: bool = True):
        self._ensure_ascii = ensure_ascii
        self._sort_keys = sort_keys
        self._indent = None if compact else (indent or 2)
        self._separators = (',', ':') if compact else None

    @property
    def format_type(self) -> SerializationFormat:
        return SerializationFormat.JSON

    @property
    def content_type(self) -> str:
        return "application/json"

    def serialize(self, data: Any) -> bytes:
        """Serialize data to JSON bytes."""
        try:
            # Convert SerializableData to dict
            if isinstance(data, SerializableData):
                json_data = data.to_dict()
            elif isinstance(data, DataMessage):
                json_data = data.to_dict()
            elif hasattr(data, 'to_dict'):
                json_data = data.to_dict()
            else:
                json_data = self._prepare_for_json(data)

            json_str = json.dumps(
                json_data,
                ensure_ascii=self._ensure_ascii,
                sort_keys=self._sort_keys,
                indent=self._indent,
                separators=self._separators,
                default=self._json_default
            )
            return json_str.encode('utf-8')

        except Exception as e:
            raise SerializationError(
                f"JSON serialization failed: {e}",
                SerializationFormat.JSON,
                e
            )

    def deserialize(self, data: bytes, target_type: Optional[Type[T]] = None) -> T:
        """Deserialize JSON bytes to data."""
        try:
            json_str = data.decode('utf-8')
            json_data = json.loads(json_str)

            # Convert back to target type if specified
            if target_type:
                if issubclass(target_type, SerializableData):
                    return target_type.from_dict(json_data)
                elif issubclass(target_type, DataMessage):
                    return target_type.from_dict(json_data)

            return self._restore_from_json(json_data)

        except Exception as e:
            raise SerializationError(
                f"JSON deserialization failed: {e}",
                SerializationFormat.JSON,
                e
            )

    def _json_default(self, obj: Any) -> Any:
        """Default JSON encoder for non-serializable objects."""
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)

    def _prepare_for_json(self, data: Any) -> Any:
        """Prepare data for JSON serialization."""
        return SerializableData._serialize_data(data)

    def _restore_from_json(self, data: Any) -> Any:
        """Restore data from JSON representation."""
        return SerializableData._deserialize_data(data)


class MessagePackSerializer(SerializerInterface):
    """MessagePack serialization for efficient binary encoding."""

    def __init__(self, use_bin_type: bool = True, strict_map_key: bool = False):
        if not MSGPACK_AVAILABLE:
            raise ImportError("msgpack library not available")

        self._use_bin_type = use_bin_type
        self._strict_map_key = strict_map_key

    @property
    def format_type(self) -> SerializationFormat:
        return SerializationFormat.MSGPACK

    @property
    def content_type(self) -> str:
        return "application/msgpack"

    def serialize(self, data: Any) -> bytes:
        """Serialize data to MessagePack bytes."""
        try:
            # Convert to serializable format
            if isinstance(data, (SerializableData, DataMessage)):
                pack_data = data.to_dict()
            elif hasattr(data, 'to_dict'):
                pack_data = data.to_dict()
            else:
                pack_data = SerializableData._serialize_data(data)

            return msgpack.packb(
                pack_data,
                use_bin_type=self._use_bin_type,
                strict_map_key=self._strict_map_key
            )

        except Exception as e:
            raise SerializationError(
                f"MessagePack serialization failed: {e}",
                SerializationFormat.MSGPACK,
                e
            )

    def deserialize(self, data: bytes, target_type: Optional[Type[T]] = None) -> T:
        """Deserialize MessagePack bytes to data."""
        try:
            unpacked_data = msgpack.unpackb(data, raw=False, strict_map_key=False)

            # Convert back to target type if specified
            if target_type:
                if issubclass(target_type, SerializableData):
                    return target_type.from_dict(unpacked_data)
                elif issubclass(target_type, DataMessage):
                    return target_type.from_dict(unpacked_data)

            return SerializableData._deserialize_data(unpacked_data)

        except Exception as e:
            raise SerializationError(
                f"MessagePack deserialization failed: {e}",
                SerializationFormat.MSGPACK,
                e
            )


class PickleSerializer(SerializerInterface):
    """Pickle serialization for Python object preservation."""

    def __init__(self, protocol: int = pickle.HIGHEST_PROTOCOL):
        self._protocol = protocol

    @property
    def format_type(self) -> SerializationFormat:
        return SerializationFormat.PICKLE

    @property
    def content_type(self) -> str:
        return "application/python-pickle"

    def serialize(self, data: Any) -> bytes:
        """Serialize data to pickle bytes."""
        try:
            return pickle.dumps(data, protocol=self._protocol)
        except Exception as e:
            raise SerializationError(
                f"Pickle serialization failed: {e}",
                SerializationFormat.PICKLE,
                e
            )

    def deserialize(self, data: bytes, target_type: Optional[Type[T]] = None) -> T:
        """Deserialize pickle bytes to data."""
        try:
            return pickle.loads(data)
        except Exception as e:
            raise SerializationError(
                f"Pickle deserialization failed: {e}",
                SerializationFormat.PICKLE,
                e
            )


class BinarySerializer(SerializerInterface):
    """High-performance binary serializer for structured data."""

    def __init__(self):
        self._struct_cache: Dict[str, Any] = {}

    @property
    def format_type(self) -> SerializationFormat:
        return SerializationFormat.BINARY

    @property
    def content_type(self) -> str:
        return "application/octet-stream"

    def serialize(self, data: Any) -> bytes:
        """Serialize data to custom binary format."""
        try:
            import struct

            if isinstance(data, (int, float)):
                # Simple numeric types
                if isinstance(data, int):
                    return b'i' + struct.pack('>q', data)  # 8-byte signed int
                else:
                    return b'f' + struct.pack('>d', data)  # 8-byte double

            elif isinstance(data, str):
                # String data
                str_bytes = data.encode('utf-8')
                return b's' + struct.pack('>I', len(str_bytes)) + str_bytes

            elif isinstance(data, bytes):
                # Raw bytes
                return b'b' + struct.pack('>I', len(data)) + data

            elif isinstance(data, (list, tuple)):
                # Sequence data
                result = b'l' + struct.pack('>I', len(data))
                for item in data:
                    item_bytes = self.serialize(item)
                    result += struct.pack('>I', len(item_bytes)) + item_bytes
                return result

            elif isinstance(data, dict):
                # Dictionary data
                result = b'd' + struct.pack('>I', len(data))
                for key, value in data.items():
                    key_bytes = self.serialize(key)
                    value_bytes = self.serialize(value)
                    result += struct.pack('>II', len(key_bytes), len(value_bytes))
                    result += key_bytes + value_bytes
                return result

            else:
                # Fall back to pickle for complex objects
                pickled = pickle.dumps(data)
                return b'p' + struct.pack('>I', len(pickled)) + pickled

        except Exception as e:
            raise SerializationError(
                f"Binary serialization failed: {e}",
                SerializationFormat.BINARY,
                e
            )

    def deserialize(self, data: bytes, target_type: Optional[Type[T]] = None) -> T:
        """Deserialize binary data."""
        try:
            import struct

            if len(data) < 1:
                raise ValueError("Empty data")

            type_marker = data[0:1]
            payload = data[1:]

            if type_marker == b'i':
                return struct.unpack('>q', payload)[0]
            elif type_marker == b'f':
                return struct.unpack('>d', payload)[0]
            elif type_marker == b's':
                length = struct.unpack('>I', payload[:4])[0]
                return payload[4:4+length].decode('utf-8')
            elif type_marker == b'b':
                length = struct.unpack('>I', payload[:4])[0]
                return payload[4:4+length]
            elif type_marker == b'l':
                length = struct.unpack('>I', payload[:4])[0]
                result = []
                offset = 4
                for _ in range(length):
                    item_length = struct.unpack('>I', payload[offset:offset+4])[0]
                    offset += 4
                    item_data = payload[offset:offset+item_length]
                    offset += item_length
                    result.append(self.deserialize(item_data))
                return result
            elif type_marker == b'd':
                length = struct.unpack('>I', payload[:4])[0]
                result = {}
                offset = 4
                for _ in range(length):
                    key_length, value_length = struct.unpack('>II', payload[offset:offset+8])
                    offset += 8
                    key_data = payload[offset:offset+key_length]
                    offset += key_length
                    value_data = payload[offset:offset+value_length]
                    offset += value_length
                    key = self.deserialize(key_data)
                    value = self.deserialize(value_data)
                    result[key] = value
                return result
            elif type_marker == b'p':
                length = struct.unpack('>I', payload[:4])[0]
                return pickle.loads(payload[4:4+length])
            else:
                raise ValueError(f"Unknown type marker: {type_marker}")

        except Exception as e:
            raise SerializationError(
                f"Binary deserialization failed: {e}",
                SerializationFormat.BINARY,
                e
            )


class CompressionSerializer(SerializerInterface):
    """Wrapper serializer that adds compression to any base serializer."""

    def __init__(self, base_serializer: SerializerInterface,
                 compression_type: CompressionType = CompressionType.GZIP,
                 compression_level: int = 6):
        self._base_serializer = base_serializer
        self._compression_type = compression_type
        self._compression_level = compression_level

        # Validate compression availability
        if compression_type == CompressionType.LZ4 and not LZ4_AVAILABLE:
            raise ImportError("lz4 library not available")
        if compression_type == CompressionType.ZSTD and not ZSTD_AVAILABLE:
            raise ImportError("zstandard library not available")

    @property
    def format_type(self) -> SerializationFormat:
        base_format = self._base_serializer.format_type
        if base_format == SerializationFormat.JSON:
            return SerializationFormat.JSON_COMPRESSED
        elif base_format == SerializationFormat.MSGPACK:
            return SerializationFormat.MSGPACK_COMPRESSED
        else:
            return base_format

    @property
    def content_type(self) -> str:
        return f"{self._base_serializer.content_type}+{self._compression_type.value}"

    def serialize(self, data: Any) -> bytes:
        """Serialize and compress data."""
        try:
            # First serialize with base serializer
            serialized_data = self._base_serializer.serialize(data)

            # Then compress
            if self._compression_type == CompressionType.GZIP:
                return gzip.compress(serialized_data, compresslevel=self._compression_level)
            elif self._compression_type == CompressionType.ZLIB:
                return zlib.compress(serialized_data, level=self._compression_level)
            elif self._compression_type == CompressionType.LZ4:
                return lz4.frame.compress(serialized_data, compression_level=self._compression_level)
            elif self._compression_type == CompressionType.ZSTD:
                compressor = zstd.ZstdCompressor(level=self._compression_level)
                return compressor.compress(serialized_data)
            else:
                return serialized_data

        except Exception as e:
            raise SerializationError(
                f"Compression serialization failed: {e}",
                self.format_type,
                e
            )

    def deserialize(self, data: bytes, target_type: Optional[Type[T]] = None) -> T:
        """Decompress and deserialize data."""
        try:
            # First decompress
            if self._compression_type == CompressionType.GZIP:
                decompressed_data = gzip.decompress(data)
            elif self._compression_type == CompressionType.ZLIB:
                decompressed_data = zlib.decompress(data)
            elif self._compression_type == CompressionType.LZ4:
                decompressed_data = lz4.frame.decompress(data)
            elif self._compression_type == CompressionType.ZSTD:
                decompressor = zstd.ZstdDecompressor()
                decompressed_data = decompressor.decompress(data)
            else:
                decompressed_data = data

            # Then deserialize with base serializer
            return self._base_serializer.deserialize(decompressed_data, target_type)

        except Exception as e:
            raise SerializationError(
                f"Compression deserialization failed: {e}",
                self.format_type,
                e
            )

    def get_compression_stats(self, data: Any) -> Dict[str, Any]:
        """Get compression statistics."""
        try:
            original_data = self._base_serializer.serialize(data)
            compressed_data = self.serialize(data)

            return {
                'original_size': len(original_data),
                'compressed_size': len(compressed_data),
                'compression_ratio': len(original_data) / len(compressed_data),
                'space_savings': (len(original_data) - len(compressed_data)) / len(original_data),
                'compression_type': self._compression_type.value
            }
        except Exception:
            return {}


# Convenience functions for quick serializer creation
def create_json_serializer(compact: bool = True, ensure_ascii: bool = False) -> JSONSerializer:
    """Create JSON serializer with common settings."""
    return JSONSerializer(ensure_ascii=ensure_ascii, compact=compact)


def create_msgpack_serializer() -> MessagePackSerializer:
    """Create MessagePack serializer."""
    if not MSGPACK_AVAILABLE:
        raise ImportError("msgpack library not available")
    return MessagePackSerializer()


def create_compressed_serializer(base_format: SerializationFormat = SerializationFormat.JSON,
                                compression_type: CompressionType = CompressionType.GZIP,
                                compression_level: int = 6) -> CompressionSerializer:
    """Create compressed serializer."""
    if base_format == SerializationFormat.JSON:
        base_serializer = create_json_serializer()
    elif base_format == SerializationFormat.MSGPACK:
        base_serializer = create_msgpack_serializer()
    elif base_format == SerializationFormat.PICKLE:
        base_serializer = PickleSerializer()
    else:
        base_serializer = BinarySerializer()

    return CompressionSerializer(base_serializer, compression_type, compression_level)