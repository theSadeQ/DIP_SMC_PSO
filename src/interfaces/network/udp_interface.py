#==========================================================================================\\\
#======================== src/interfaces/network/udp_interface.py =======================\\\
#==========================================================================================\\\
"""
UDP communication interface for real-time control systems.
This module provides high-performance UDP communication with features like
CRC checking, sequence numbering, and connection state management for
control applications requiring low-latency communication.
"""

import asyncio
import socket
import struct
import time
import zlib
from typing import Optional, Dict, Any, Tuple, Callable
import logging

from ..core.protocols import CommunicationProtocol, MessageMetadata, ConnectionState, MessageType, Priority
from ..core.data_types import Message, ConnectionInfo, InterfaceConfig, InterfaceType, TransportType


class UDPInterface(CommunicationProtocol):
    """
    High-performance UDP communication interface for control systems.

    Features:
    - Low-latency UDP communication
    - Optional CRC integrity checking
    - Sequence number tracking
    - Connection state management
    - Statistics collection
    - Message timeout handling
    """

    def __init__(self, config: InterfaceConfig):
        """Initialize UDP interface with configuration."""
        self._config = config
        self._socket: Optional[socket.socket] = None
        self._transport: Optional[asyncio.DatagramTransport] = None
        self._protocol: Optional['UDPProtocol'] = None
        self._connection_state = ConnectionState.DISCONNECTED
        self._stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'crc_errors': 0,
            'sequence_errors': 0,
            'timeouts': 0,
            'last_activity': 0.0
        }
        self._sequence_number = 0
        self._expected_sequence = 0
        self._use_crc = config.get_setting('use_crc', True)
        self._use_sequence = config.get_setting('use_sequence', True)
        self._message_handlers: Dict[MessageType, Callable] = {}
        self._logger = logging.getLogger(f"udp_interface_{config.name}")

    async def connect(self, config: Dict[str, Any]) -> bool:
        """Establish UDP connection."""
        try:
            host, port = self._parse_endpoint(config.get('endpoint', self._config.endpoint))

            # Create asyncio UDP endpoint
            loop = asyncio.get_event_loop()

            if config.get('server_mode', False):
                # Server mode - bind and listen
                self._protocol = UDPProtocol(self)
                self._transport, _ = await loop.create_datagram_endpoint(
                    lambda: self._protocol,
                    local_addr=(host, port)
                )
                self._logger.info(f"UDP server listening on {host}:{port}")
            else:
                # Client mode - connect to remote
                self._protocol = UDPProtocol(self)
                self._transport, _ = await loop.create_datagram_endpoint(
                    lambda: self._protocol,
                    remote_addr=(host, port)
                )
                self._logger.info(f"UDP client connected to {host}:{port}")

            self._connection_state = ConnectionState.CONNECTED
            self._stats['last_activity'] = time.time()
            return True

        except Exception as e:
            self._logger.error(f"Failed to establish UDP connection: {e}")
            self._connection_state = ConnectionState.ERROR
            return False

    async def disconnect(self) -> bool:
        """Close UDP connection."""
        try:
            if self._transport:
                self._transport.close()
                self._transport = None

            self._protocol = None
            self._connection_state = ConnectionState.DISCONNECTED
            self._logger.info("UDP connection closed")
            return True

        except Exception as e:
            self._logger.error(f"Error closing UDP connection: {e}")
            return False

    async def send(self, data: Any, metadata: Optional[MessageMetadata] = None) -> bool:
        """Send data via UDP with optional CRC and sequence numbering."""
        if self._connection_state != ConnectionState.CONNECTED or not self._transport:
            return False

        try:
            # Create message metadata if not provided
            if metadata is None:
                metadata = MessageMetadata(
                    message_id=f"udp_{int(time.time() * 1000000)}",
                    timestamp=time.time(),
                    message_type=MessageType.DATA,
                    priority=Priority.NORMAL,
                    source=self._config.name
                )

            # Serialize message
            message_data = self._serialize_message(data, metadata)

            # Add sequence number if enabled
            if self._use_sequence:
                message_data = struct.pack('!I', self._sequence_number) + message_data
                self._sequence_number += 1

            # Add CRC if enabled
            if self._use_crc:
                crc = zlib.crc32(message_data) & 0xffffffff
                message_data = struct.pack('!I', crc) + message_data

            # Send via transport
            self._transport.sendto(message_data)

            # Update statistics
            self._stats['messages_sent'] += 1
            self._stats['bytes_sent'] += len(message_data)
            self._stats['last_activity'] = time.time()

            return True

        except Exception as e:
            self._logger.error(f"Failed to send UDP message: {e}")
            return False

    async def receive(self, timeout: Optional[float] = None) -> Optional[Tuple[Any, MessageMetadata]]:
        """Receive data via UDP with timeout."""
        if self._connection_state != ConnectionState.CONNECTED or not self._protocol:
            return None

        try:
            # Wait for message with timeout
            if timeout:
                message = await asyncio.wait_for(
                    self._protocol.get_next_message(),
                    timeout=timeout
                )
            else:
                message = await self._protocol.get_next_message()

            if message:
                self._stats['last_activity'] = time.time()
                return message
            else:
                self._stats['timeouts'] += 1
                return None

        except asyncio.TimeoutError:
            self._stats['timeouts'] += 1
            return None
        except Exception as e:
            self._logger.error(f"Error receiving UDP message: {e}")
            return None

    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self._connection_state

    def get_statistics(self) -> Dict[str, Any]:
        """Get UDP communication statistics."""
        stats = self._stats.copy()
        stats['connection_state'] = self._connection_state.value
        stats['sequence_number'] = self._sequence_number
        stats['expected_sequence'] = self._expected_sequence
        return stats

    def register_message_handler(self, message_type: MessageType, handler: Callable) -> None:
        """Register handler for specific message type."""
        self._message_handlers[message_type] = handler

    def _parse_endpoint(self, endpoint: str) -> Tuple[str, int]:
        """Parse endpoint string into host and port."""
        if ':' in endpoint:
            host, port_str = endpoint.rsplit(':', 1)
            return host, int(port_str)
        else:
            return endpoint, 8080

    def _serialize_message(self, data: Any, metadata: MessageMetadata) -> bytes:
        """Serialize message data and metadata."""
        import json
        import pickle

        message = {
            'metadata': {
                'message_id': metadata.message_id,
                'timestamp': metadata.timestamp,
                'message_type': metadata.message_type.value,
                'priority': metadata.priority.value,
                'source': metadata.source,
                'destination': metadata.destination,
                'correlation_id': metadata.correlation_id
            },
            'data': data
        }

        # Use JSON for simple data, pickle for complex objects
        try:
            return json.dumps(message).encode('utf-8')
        except (TypeError, ValueError):
            return pickle.dumps(message)

    def _deserialize_message(self, data: bytes) -> Tuple[Any, MessageMetadata]:
        """Deserialize message data and metadata."""
        import json
        import pickle

        try:
            # Try JSON first
            try:
                message = json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fall back to pickle
                message = pickle.loads(data)

            # Extract metadata
            meta_dict = message['metadata']
            metadata = MessageMetadata(
                message_id=meta_dict['message_id'],
                timestamp=meta_dict['timestamp'],
                message_type=MessageType(meta_dict['message_type']),
                priority=Priority(meta_dict['priority']),
                source=meta_dict['source'],
                destination=meta_dict.get('destination'),
                correlation_id=meta_dict.get('correlation_id')
            )

            return message['data'], metadata

        except Exception as e:
            self._logger.error(f"Failed to deserialize message: {e}")
            raise

    def _process_received_data(self, data: bytes, addr: Tuple[str, int]) -> Optional[Tuple[Any, MessageMetadata]]:
        """Process received UDP data packet."""
        try:
            original_data = data

            # Check and remove CRC if enabled
            if self._use_crc:
                if len(data) < 4:
                    self._logger.warning("Received packet too short for CRC")
                    return None

                received_crc = struct.unpack('!I', data[:4])[0]
                data = data[4:]
                calculated_crc = zlib.crc32(data) & 0xffffffff

                if received_crc != calculated_crc:
                    self._stats['crc_errors'] += 1
                    self._logger.warning(f"CRC mismatch: received={received_crc:08x}, calculated={calculated_crc:08x}")
                    return None

            # Check and remove sequence number if enabled
            if self._use_sequence:
                if len(data) < 4:
                    self._logger.warning("Received packet too short for sequence number")
                    return None

                sequence = struct.unpack('!I', data[:4])[0]
                data = data[4:]

                # Simple sequence checking (could be enhanced with window-based checking)
                if sequence != self._expected_sequence:
                    self._stats['sequence_errors'] += 1
                    self._logger.warning(f"Sequence error: expected={self._expected_sequence}, received={sequence}")
                    # Don't return None - still process the message but log the error

                self._expected_sequence = sequence + 1

            # Deserialize message
            message_data, metadata = self._deserialize_message(data)

            # Update statistics
            self._stats['messages_received'] += 1
            self._stats['bytes_received'] += len(original_data)

            return message_data, metadata

        except Exception as e:
            self._logger.error(f"Error processing received data: {e}")
            return None


class UDPProtocol(asyncio.DatagramProtocol):
    """Asyncio UDP protocol handler."""

    def __init__(self, interface: UDPInterface):
        self._interface = interface
        self._message_queue = asyncio.Queue()
        self._transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        """Called when connection is established."""
        self._transport = transport

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Called when datagram is received."""
        try:
            message = self._interface._process_received_data(data, addr)
            if message:
                # Put message in queue for retrieval
                asyncio.create_task(self._message_queue.put(message))

                # Call registered handlers
                message_data, metadata = message
                handler = self._interface._message_handlers.get(metadata.message_type)
                if handler:
                    asyncio.create_task(self._call_handler(handler, message_data, metadata))

        except Exception as e:
            logging.error(f"Error processing received datagram: {e}")

    async def _call_handler(self, handler: Callable, data: Any, metadata: MessageMetadata) -> None:
        """Call message handler safely."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(data, metadata)
            else:
                handler(data, metadata)
        except Exception as e:
            logging.error(f"Error in message handler: {e}")

    async def get_next_message(self) -> Optional[Tuple[Any, MessageMetadata]]:
        """Get next message from queue."""
        try:
            return await self._message_queue.get()
        except Exception:
            return None

    def error_received(self, exc: Exception) -> None:
        """Called when error is received."""
        logging.error(f"UDP protocol error: {exc}")


class UDPServer(UDPInterface):
    """UDP server for hosting control services."""

    def __init__(self, config: InterfaceConfig):
        super().__init__(config)
        self._clients: Dict[Tuple[str, int], Dict[str, Any]] = {}

    async def start_server(self, host: str = "0.0.0.0", port: int = 8080) -> bool:
        """Start UDP server."""
        return await self.connect({
            'endpoint': f"{host}:{port}",
            'server_mode': True
        })

    def get_connected_clients(self) -> Dict[Tuple[str, int], Dict[str, Any]]:
        """Get list of connected clients."""
        return self._clients.copy()


class UDPClient(UDPInterface):
    """UDP client for connecting to control services."""

    def __init__(self, config: InterfaceConfig):
        super().__init__(config)

    async def connect_to_server(self, host: str, port: int) -> bool:
        """Connect to UDP server."""
        return await self.connect({
            'endpoint': f"{host}:{port}",
            'server_mode': False
        })