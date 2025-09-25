#==========================================================================================\\\
#===================== src/interfaces/data_exchange/streaming.py ========================\\\
#==========================================================================================\\\
"""
Streaming serialization support for large datasets and real-time processing.
This module provides efficient streaming serialization capabilities
for processing large amounts of data, real-time data streams,
and memory-efficient handling of continuous data flows.
"""

import asyncio
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Iterator, Optional, Dict, List, Callable, Union
from enum import Enum
import logging
from collections import deque

from .serializers import SerializerInterface, SerializationError
from .data_types import DataMessage, MessageHeader, MessageType


class StreamMode(Enum):
    """Stream processing modes."""
    PUSH = "push"           # Producer pushes data
    PULL = "pull"           # Consumer pulls data
    BIDIRECTIONAL = "bidirectional"  # Both directions


class StreamState(Enum):
    """Stream state enumeration."""
    CREATED = "created"
    STARTED = "started"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class BackpressureStrategy(Enum):
    """Backpressure handling strategies."""
    BLOCK = "block"         # Block until space available
    DROP_OLDEST = "drop_oldest"  # Drop oldest items
    DROP_NEWEST = "drop_newest"  # Drop newest items
    BUFFER_EXPAND = "buffer_expand"  # Expand buffer size


@dataclass
class StreamConfig:
    """Configuration for streaming operations."""
    buffer_size: int = 10000
    batch_size: int = 100
    flush_interval: float = 1.0  # seconds
    enable_compression: bool = False
    backpressure_strategy: BackpressureStrategy = BackpressureStrategy.BLOCK
    max_memory_usage: int = 100 * 1024 * 1024  # 100MB
    enable_checkpointing: bool = False
    checkpoint_interval: int = 1000  # items
    timeout: Optional[float] = None


@dataclass
class StreamMetrics:
    """Streaming performance metrics."""
    items_processed: int = 0
    bytes_processed: int = 0
    processing_time: float = 0.0
    items_per_second: float = 0.0
    bytes_per_second: float = 0.0
    buffer_utilization: float = 0.0
    backpressure_events: int = 0
    errors: int = 0
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)

    def update(self, items: int, bytes_count: int, processing_time: float) -> None:
        """Update metrics with new data."""
        self.items_processed += items
        self.bytes_processed += bytes_count
        self.processing_time += processing_time

        # Calculate rates
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            self.items_per_second = self.items_processed / elapsed_time
            self.bytes_per_second = self.bytes_processed / elapsed_time

        self.last_update = time.time()


class StreamBuffer:
    """Thread-safe streaming buffer with backpressure handling."""

    def __init__(self, max_size: int, backpressure_strategy: BackpressureStrategy):
        self._max_size = max_size
        self._backpressure_strategy = backpressure_strategy
        self._buffer = deque()
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self._closed = False

    def put(self, item: Any, timeout: Optional[float] = None) -> bool:
        """Put item into buffer with backpressure handling."""
        with self._lock:
            if self._closed:
                return False

            # Handle backpressure
            if len(self._buffer) >= self._max_size:
                if self._backpressure_strategy == BackpressureStrategy.BLOCK:
                    return self._wait_for_space(timeout)
                elif self._backpressure_strategy == BackpressureStrategy.DROP_OLDEST:
                    self._buffer.popleft()
                elif self._backpressure_strategy == BackpressureStrategy.DROP_NEWEST:
                    return False  # Don't add new item
                elif self._backpressure_strategy == BackpressureStrategy.BUFFER_EXPAND:
                    # Allow buffer to grow (with memory limits handled elsewhere)
                    pass

            self._buffer.append(item)
            self._not_empty.notify()
            return True

    def get(self, timeout: Optional[float] = None) -> Optional[Any]:
        """Get item from buffer."""
        with self._lock:
            if not self._buffer and self._closed:
                return None

            if not self._buffer:
                if timeout is None:
                    self._not_empty.wait()
                else:
                    if not self._not_empty.wait(timeout):
                        return None

            if self._buffer:
                item = self._buffer.popleft()
                self._not_full.notify()
                return item

            return None

    def get_batch(self, batch_size: int, timeout: Optional[float] = None) -> List[Any]:
        """Get batch of items from buffer."""
        batch = []
        deadline = time.time() + timeout if timeout else None

        while len(batch) < batch_size:
            remaining_timeout = None
            if deadline:
                remaining_timeout = deadline - time.time()
                if remaining_timeout <= 0:
                    break

            item = self.get(remaining_timeout)
            if item is None:
                break
            batch.append(item)

        return batch

    def size(self) -> int:
        """Get current buffer size."""
        with self._lock:
            return len(self._buffer)

    def is_full(self) -> bool:
        """Check if buffer is full."""
        with self._lock:
            return len(self._buffer) >= self._max_size

    def close(self) -> None:
        """Close the buffer."""
        with self._lock:
            self._closed = True
            self._not_empty.notify_all()
            self._not_full.notify_all()

    def _wait_for_space(self, timeout: Optional[float]) -> bool:
        """Wait for space in buffer."""
        if timeout is None:
            while len(self._buffer) >= self._max_size and not self._closed:
                self._not_full.wait()
        else:
            deadline = time.time() + timeout
            while len(self._buffer) >= self._max_size and not self._closed:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return False
                self._not_full.wait(remaining)

        return not self._closed


class DataStream(ABC):
    """Abstract base class for data streams."""

    def __init__(self, config: StreamConfig):
        self._config = config
        self._state = StreamState.CREATED
        self._metrics = StreamMetrics()
        self._error_handlers: List[Callable[[Exception], None]] = []
        self._logger = logging.getLogger(f"data_stream_{id(self)}")

    @property
    def state(self) -> StreamState:
        return self._state

    @property
    def metrics(self) -> StreamMetrics:
        return self._metrics

    @abstractmethod
    async def start(self) -> bool:
        """Start the stream."""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Stop the stream."""
        pass

    @abstractmethod
    async def pause(self) -> bool:
        """Pause the stream."""
        pass

    @abstractmethod
    async def resume(self) -> bool:
        """Resume the stream."""
        pass

    def add_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Add error handler."""
        self._error_handlers.append(handler)

    def _handle_error(self, error: Exception) -> None:
        """Handle stream error."""
        self._state = StreamState.ERROR
        self._metrics.errors += 1
        self._logger.error(f"Stream error: {error}")

        for handler in self._error_handlers:
            try:
                handler(error)
            except Exception as e:
                self._logger.error(f"Error in error handler: {e}")


class StreamingSerializer:
    """Main streaming serializer for processing data streams."""

    def __init__(self, serializer: SerializerInterface, config: Optional[StreamConfig] = None):
        self._serializer = serializer
        self._config = config or StreamConfig()
        self._buffer = StreamBuffer(self._config.buffer_size, self._config.backpressure_strategy)
        self._metrics = StreamMetrics()
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        self._output_handlers: List[Callable[[bytes], None]] = []
        self._logger = logging.getLogger("streaming_serializer")

    async def start(self) -> bool:
        """Start streaming serialization."""
        if self._running:
            return False

        try:
            self._running = True
            self._processor_task = asyncio.create_task(self._process_stream())
            self._logger.info("Streaming serializer started")
            return True

        except Exception as e:
            self._logger.error(f"Failed to start streaming serializer: {e}")
            self._running = False
            return False

    async def stop(self) -> bool:
        """Stop streaming serialization."""
        if not self._running:
            return True

        try:
            self._running = False
            self._buffer.close()

            if self._processor_task:
                await self._processor_task

            self._logger.info("Streaming serializer stopped")
            return True

        except Exception as e:
            self._logger.error(f"Error stopping streaming serializer: {e}")
            return False

    def add_data(self, data: Any, timeout: Optional[float] = None) -> bool:
        """Add data to the stream for serialization."""
        if not self._running:
            return False

        return self._buffer.put(data, timeout)

    def add_output_handler(self, handler: Callable[[bytes], None]) -> None:
        """Add handler for serialized output."""
        self._output_handlers.append(handler)

    async def _process_stream(self) -> None:
        """Main stream processing loop."""
        while self._running:
            try:
                # Get batch of items
                batch = self._buffer.get_batch(
                    self._config.batch_size,
                    self._config.flush_interval
                )

                if not batch:
                    if not self._running:
                        break
                    continue

                # Process batch
                await self._process_batch(batch)

            except Exception as e:
                self._logger.error(f"Error in stream processing: {e}")
                self._metrics.errors += 1

                if not self._running:
                    break

    async def _process_batch(self, batch: List[Any]) -> None:
        """Process a batch of data items."""
        start_time = time.perf_counter()
        total_bytes = 0

        try:
            for item in batch:
                serialized = self._serializer.serialize(item)
                total_bytes += len(serialized)

                # Send to output handlers
                for handler in self._output_handlers:
                    try:
                        handler(serialized)
                    except Exception as e:
                        self._logger.error(f"Error in output handler: {e}")

            # Update metrics
            processing_time = time.perf_counter() - start_time
            self._metrics.update(len(batch), total_bytes, processing_time)

        except Exception as e:
            self._logger.error(f"Error processing batch: {e}")
            raise

    def get_metrics(self) -> StreamMetrics:
        """Get streaming metrics."""
        # Update buffer utilization
        self._metrics.buffer_utilization = self._buffer.size() / self._config.buffer_size
        return self._metrics


class StreamingDeserializer:
    """Streaming deserializer for processing serialized data streams."""

    def __init__(self, serializer: SerializerInterface, config: Optional[StreamConfig] = None):
        self._serializer = serializer
        self._config = config or StreamConfig()
        self._buffer = StreamBuffer(self._config.buffer_size, self._config.backpressure_strategy)
        self._metrics = StreamMetrics()
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        self._output_handlers: List[Callable[[Any], None]] = []
        self._logger = logging.getLogger("streaming_deserializer")

    async def start(self) -> bool:
        """Start streaming deserialization."""
        if self._running:
            return False

        try:
            self._running = True
            self._processor_task = asyncio.create_task(self._process_stream())
            self._logger.info("Streaming deserializer started")
            return True

        except Exception as e:
            self._logger.error(f"Failed to start streaming deserializer: {e}")
            self._running = False
            return False

    async def stop(self) -> bool:
        """Stop streaming deserialization."""
        if not self._running:
            return True

        try:
            self._running = False
            self._buffer.close()

            if self._processor_task:
                await self._processor_task

            self._logger.info("Streaming deserializer stopped")
            return True

        except Exception as e:
            self._logger.error(f"Error stopping streaming deserializer: {e}")
            return False

    def add_serialized_data(self, data: bytes, timeout: Optional[float] = None) -> bool:
        """Add serialized data to the stream for deserialization."""
        if not self._running:
            return False

        return self._buffer.put(data, timeout)

    def add_output_handler(self, handler: Callable[[Any], None]) -> None:
        """Add handler for deserialized output."""
        self._output_handlers.append(handler)

    async def _process_stream(self) -> None:
        """Main stream processing loop."""
        while self._running:
            try:
                # Get batch of items
                batch = self._buffer.get_batch(
                    self._config.batch_size,
                    self._config.flush_interval
                )

                if not batch:
                    if not self._running:
                        break
                    continue

                # Process batch
                await self._process_batch(batch)

            except Exception as e:
                self._logger.error(f"Error in stream processing: {e}")
                self._metrics.errors += 1

                if not self._running:
                    break

    async def _process_batch(self, batch: List[bytes]) -> None:
        """Process a batch of serialized data."""
        start_time = time.perf_counter()
        total_bytes = sum(len(item) for item in batch)

        try:
            for item in batch:
                deserialized = self._serializer.deserialize(item)

                # Send to output handlers
                for handler in self._output_handlers:
                    try:
                        handler(deserialized)
                    except Exception as e:
                        self._logger.error(f"Error in output handler: {e}")

            # Update metrics
            processing_time = time.perf_counter() - start_time
            self._metrics.update(len(batch), total_bytes, processing_time)

        except Exception as e:
            self._logger.error(f"Error processing batch: {e}")
            raise

    def get_metrics(self) -> StreamMetrics:
        """Get streaming metrics."""
        # Update buffer utilization
        self._metrics.buffer_utilization = self._buffer.size() / self._config.buffer_size
        return self._metrics


class MessageStream(DataStream):
    """Message-oriented data stream with protocol support."""

    def __init__(self, serializer: SerializerInterface, config: Optional[StreamConfig] = None):
        super().__init__(config or StreamConfig())
        self._serializer = serializer
        self._message_handlers: Dict[MessageType, List[Callable[[DataMessage], None]]] = {}
        self._streaming_serializer = StreamingSerializer(serializer, self._config)
        self._streaming_deserializer = StreamingDeserializer(serializer, self._config)

    async def start(self) -> bool:
        """Start message stream."""
        if self._state != StreamState.CREATED:
            return False

        try:
            self._state = StreamState.STARTED

            # Start streaming components
            if not await self._streaming_serializer.start():
                return False

            if not await self._streaming_deserializer.start():
                await self._streaming_serializer.stop()
                return False

            # Set up message routing
            self._streaming_deserializer.add_output_handler(self._route_message)

            self._state = StreamState.RUNNING
            self._logger.info("Message stream started")
            return True

        except Exception as e:
            self._handle_error(e)
            return False

    async def stop(self) -> bool:
        """Stop message stream."""
        if self._state in [StreamState.STOPPED, StreamState.ERROR]:
            return True

        try:
            await self._streaming_serializer.stop()
            await self._streaming_deserializer.stop()

            self._state = StreamState.STOPPED
            self._logger.info("Message stream stopped")
            return True

        except Exception as e:
            self._handle_error(e)
            return False

    async def pause(self) -> bool:
        """Pause message stream."""
        if self._state == StreamState.RUNNING:
            self._state = StreamState.PAUSED
            return True
        return False

    async def resume(self) -> bool:
        """Resume message stream."""
        if self._state == StreamState.PAUSED:
            self._state = StreamState.RUNNING
            return True
        return False

    def send_message(self, message: DataMessage, timeout: Optional[float] = None) -> bool:
        """Send message through the stream."""
        if self._state != StreamState.RUNNING:
            return False

        return self._streaming_serializer.add_data(message, timeout)

    def add_message_handler(self, message_type: MessageType,
                           handler: Callable[[DataMessage], None]) -> None:
        """Add handler for specific message type."""
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)

    def _route_message(self, message_data: Any) -> None:
        """Route message to appropriate handlers."""
        try:
            if isinstance(message_data, DataMessage):
                message_type = message_data.header.message_type
                if message_type in self._message_handlers:
                    for handler in self._message_handlers[message_type]:
                        try:
                            handler(message_data)
                        except Exception as e:
                            self._logger.error(f"Error in message handler: {e}")

        except Exception as e:
            self._logger.error(f"Error routing message: {e}")

    def get_stream_metrics(self) -> Dict[str, StreamMetrics]:
        """Get metrics for all stream components."""
        return {
            'serializer': self._streaming_serializer.get_metrics(),
            'deserializer': self._streaming_deserializer.get_metrics()
        }


class FileStreamProcessor:
    """Stream processor for file-based data processing."""

    def __init__(self, serializer: SerializerInterface, config: Optional[StreamConfig] = None):
        self._serializer = serializer
        self._config = config or StreamConfig()
        self._logger = logging.getLogger("file_stream_processor")

    async def process_file_stream(self, input_file: str, output_file: str,
                                 transform_func: Optional[Callable[[Any], Any]] = None) -> StreamMetrics:
        """Process file stream with optional transformation."""
        metrics = StreamMetrics()

        try:
            with open(input_file, 'rb') as infile, open(output_file, 'wb') as outfile:
                while True:
                    # Read chunk
                    chunk = infile.read(self._config.batch_size * 1024)  # KB chunks
                    if not chunk:
                        break

                    start_time = time.perf_counter()

                    try:
                        # Deserialize chunk
                        data = self._serializer.deserialize(chunk)

                        # Apply transformation if provided
                        if transform_func:
                            data = transform_func(data)

                        # Serialize transformed data
                        output_chunk = self._serializer.serialize(data)

                        # Write to output
                        outfile.write(output_chunk)

                        # Update metrics
                        processing_time = time.perf_counter() - start_time
                        metrics.update(1, len(output_chunk), processing_time)

                    except Exception as e:
                        self._logger.error(f"Error processing chunk: {e}")
                        metrics.errors += 1

        except Exception as e:
            self._logger.error(f"Error in file stream processing: {e}")
            metrics.errors += 1

        return metrics


# Factory functions
def create_streaming_serializer(serializer: SerializerInterface,
                               config: Optional[StreamConfig] = None) -> StreamingSerializer:
    """Create streaming serializer."""
    return StreamingSerializer(serializer, config)


def create_streaming_deserializer(serializer: SerializerInterface,
                                 config: Optional[StreamConfig] = None) -> StreamingDeserializer:
    """Create streaming deserializer."""
    return StreamingDeserializer(serializer, config)


def create_message_stream(serializer: SerializerInterface,
                         config: Optional[StreamConfig] = None) -> MessageStream:
    """Create message stream."""
    return MessageStream(serializer, config)


def create_stream_config(buffer_size: int = 10000,
                        batch_size: int = 100,
                        flush_interval: float = 1.0,
                        backpressure_strategy: BackpressureStrategy = BackpressureStrategy.BLOCK) -> StreamConfig:
    """Create stream configuration."""
    return StreamConfig(
        buffer_size=buffer_size,
        batch_size=batch_size,
        flush_interval=flush_interval,
        backpressure_strategy=backpressure_strategy
    )