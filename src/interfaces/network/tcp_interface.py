#==========================================================================================\\\
#======================== src/interfaces/network/tcp_interface.py =======================\\\
#==========================================================================================\\\
"""
TCP communication interface for reliable control system communication.
This module provides TCP-based communication with features like connection
pooling, automatic reconnection, message framing, and flow control for
applications requiring reliable message delivery.
"""

import asyncio
import struct
import time
import json
import pickle
from typing import Optional, Dict, Any, Tuple, Callable, List
import logging

from ..core.protocols import CommunicationProtocol, MessageMetadata, ConnectionState, MessageType, Priority
from ..core.data_types import Message, ConnectionInfo, InterfaceConfig, InterfaceType


class TCPInterface(CommunicationProtocol):
    """
    Reliable TCP communication interface for control systems.

    Features:
    - Reliable TCP stream communication
    - Message framing with length prefixes
    - Connection management and pooling
    - Automatic reconnection
    - Flow control and backpressure handling
    - Statistics collection
    """

    def __init__(self, config: InterfaceConfig):
        """Initialize TCP interface with configuration."""
        self._config = config
        self._connection_state = ConnectionState.DISCONNECTED
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._server: Optional[asyncio.Server] = None
        self._clients: Dict[str, Tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}
        self._stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'connections_established': 0,
            'connections_lost': 0,
            'reconnection_attempts': 0,
            'last_activity': 0.0
        }
        self._message_handlers: Dict[MessageType, Callable] = {}
        self._auto_reconnect = config.get_setting('auto_reconnect', True)
        self._reconnect_delay = config.get_setting('reconnect_delay', 5.0)
        self._max_message_size = config.max_message_size
        self._logger = logging.getLogger(f"tcp_interface_{config.name}")
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self, config: Dict[str, Any]) -> bool:
        """Establish TCP connection."""
        try:
            host, port = self._parse_endpoint(config.get('endpoint', self._config.endpoint))

            if config.get('server_mode', False):
                # Server mode - start listening
                self._server = await asyncio.start_server(
                    self._handle_client_connection,
                    host,
                    port
                )
                self._connection_state = ConnectionState.CONNECTED
                self._logger.info(f"TCP server listening on {host}:{port}")
            else:
                # Client mode - connect to server
                self._connection_state = ConnectionState.CONNECTING
                self._reader, self._writer = await asyncio.open_connection(host, port)
                self._connection_state = ConnectionState.CONNECTED
                self._logger.info(f"TCP client connected to {host}:{port}")

                # Start receive task for client mode
                self._receive_task = asyncio.create_task(self._receive_loop())

            self._stats['connections_established'] += 1
            self._stats['last_activity'] = time.time()
            return True

        except Exception as e:
            self._logger.error(f"Failed to establish TCP connection: {e}")
            self._connection_state = ConnectionState.ERROR
            return False

    async def disconnect(self) -> bool:
        """Close TCP connection."""
        try:
            self._connection_state = ConnectionState.DISCONNECTED

            # Cancel receive task
            if self._receive_task:
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass

            # Close client connections
            for client_id, (reader, writer) in self._clients.items():
                writer.close()
                await writer.wait_closed()
            self._clients.clear()

            # Close server
            if self._server:
                self._server.close()
                await self._server.wait_closed()
                self._server = None

            # Close client connection
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
                self._writer = None
                self._reader = None

            self._logger.info("TCP connection closed")
            return True

        except Exception as e:
            self._logger.error(f"Error closing TCP connection: {e}")
            return False

    async def send(self, data: Any, metadata: Optional[MessageMetadata] = None) -> bool:
        """Send data via TCP with message framing."""
        if self._connection_state != ConnectionState.CONNECTED:
            return False

        try:
            # Create message metadata if not provided
            if metadata is None:
                metadata = MessageMetadata(
                    message_id=f"tcp_{int(time.time() * 1000000)}",
                    timestamp=time.time(),
                    message_type=MessageType.DATA,
                    priority=Priority.NORMAL,
                    source=self._config.name
                )

            # Serialize message
            message_data = self._serialize_message(data, metadata)

            # Check message size
            if len(message_data) > self._max_message_size:
                self._logger.error(f"Message too large: {len(message_data)} > {self._max_message_size}")
                return False

            # Frame message with length prefix
            framed_message = struct.pack('!I', len(message_data)) + message_data

            # Send to client or all connected clients
            if self._writer:
                # Client mode - send to server
                self._writer.write(framed_message)
                await self._writer.drain()
            else:
                # Server mode - send to all clients
                if not self._clients:
                    return False

                for client_id, (reader, writer) in list(self._clients.items()):
                    try:
                        writer.write(framed_message)
                        await writer.drain()
                    except Exception as e:
                        self._logger.warning(f"Failed to send to client {client_id}: {e}")
                        # Remove disconnected client
                        writer.close()
                        del self._clients[client_id]

            # Update statistics
            self._stats['messages_sent'] += 1
            self._stats['bytes_sent'] += len(framed_message)
            self._stats['last_activity'] = time.time()

            return True

        except Exception as e:
            self._logger.error(f"Failed to send TCP message: {e}")
            if self._auto_reconnect and not self._server:
                asyncio.create_task(self._reconnect())
            return False

    async def receive(self, timeout: Optional[float] = None) -> Optional[Tuple[Any, MessageMetadata]]:
        """Receive data via TCP with timeout."""
        if self._connection_state != ConnectionState.CONNECTED:
            return None

        try:
            # In server mode, we collect messages from all clients
            if self._server:
                # For server mode, this method would need to be modified
                # to handle multiple client messages or use a different pattern
                return None

            # Client mode - receive from server
            return await self._receive_message(self._reader, timeout)

        except Exception as e:
            self._logger.error(f"Error receiving TCP message: {e}")
            if self._auto_reconnect:
                asyncio.create_task(self._reconnect())
            return None

    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self._connection_state

    def get_statistics(self) -> Dict[str, Any]:
        """Get TCP communication statistics."""
        stats = self._stats.copy()
        stats['connection_state'] = self._connection_state.value
        stats['active_clients'] = len(self._clients)
        stats['is_server'] = self._server is not None
        return stats

    def register_message_handler(self, message_type: MessageType, handler: Callable) -> None:
        """Register handler for specific message type."""
        self._message_handlers[message_type] = handler

    async def _handle_client_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle new client connection in server mode."""
        client_addr = writer.get_extra_info('peername')
        client_id = f"{client_addr[0]}:{client_addr[1]}"

        self._logger.info(f"New client connected: {client_id}")
        self._clients[client_id] = (reader, writer)

        try:
            while True:
                message = await self._receive_message(reader)
                if message is None:
                    break

                # Call registered handlers
                message_data, metadata = message
                handler = self._message_handlers.get(metadata.message_type)
                if handler:
                    asyncio.create_task(self._call_handler(handler, message_data, metadata, client_id))

        except Exception as e:
            self._logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Clean up client connection
            writer.close()
            if client_id in self._clients:
                del self._clients[client_id]
            self._logger.info(f"Client disconnected: {client_id}")

    async def _receive_message(self, reader: asyncio.StreamReader, timeout: Optional[float] = None) -> Optional[Tuple[Any, MessageMetadata]]:
        """Receive framed message from stream."""
        try:
            # Read length prefix
            if timeout:
                length_data = await asyncio.wait_for(reader.readexactly(4), timeout=timeout)
            else:
                length_data = await reader.readexactly(4)

            if len(length_data) != 4:
                return None

            message_length = struct.unpack('!I', length_data)[0]

            # Validate message length
            if message_length > self._max_message_size:
                self._logger.error(f"Message too large: {message_length} > {self._max_message_size}")
                return None

            # Read message data
            if timeout:
                message_data = await asyncio.wait_for(reader.readexactly(message_length), timeout=timeout)
            else:
                message_data = await reader.readexactly(message_length)

            if len(message_data) != message_length:
                return None

            # Deserialize message
            data, metadata = self._deserialize_message(message_data)

            # Update statistics
            self._stats['messages_received'] += 1
            self._stats['bytes_received'] += 4 + message_length
            self._stats['last_activity'] = time.time()

            return data, metadata

        except asyncio.IncompleteReadError:
            # Connection closed
            return None
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            self._logger.error(f"Error receiving message: {e}")
            return None

    async def _receive_loop(self) -> None:
        """Continuous receive loop for client mode."""
        try:
            while self._connection_state == ConnectionState.CONNECTED and self._reader:
                message = await self._receive_message(self._reader)
                if message is None:
                    break

                # Call registered handlers
                message_data, metadata = message
                handler = self._message_handlers.get(metadata.message_type)
                if handler:
                    asyncio.create_task(self._call_handler(handler, message_data, metadata))

        except Exception as e:
            self._logger.error(f"Error in receive loop: {e}")
        finally:
            if self._connection_state == ConnectionState.CONNECTED:
                self._connection_state = ConnectionState.ERROR
                if self._auto_reconnect:
                    asyncio.create_task(self._reconnect())

    async def _call_handler(self, handler: Callable, data: Any, metadata: MessageMetadata, client_id: Optional[str] = None) -> None:
        """Call message handler safely."""
        try:
            if asyncio.iscoroutinefunction(handler):
                if client_id:
                    await handler(data, metadata, client_id)
                else:
                    await handler(data, metadata)
            else:
                if client_id:
                    handler(data, metadata, client_id)
                else:
                    handler(data, metadata)
        except Exception as e:
            self._logger.error(f"Error in message handler: {e}")

    async def _reconnect(self) -> None:
        """Attempt to reconnect to server."""
        if self._server or self._connection_state in [ConnectionState.CONNECTING, ConnectionState.RECONNECTING]:
            return

        self._connection_state = ConnectionState.RECONNECTING
        self._stats['reconnection_attempts'] += 1

        while self._connection_state == ConnectionState.RECONNECTING:
            try:
                await asyncio.sleep(self._reconnect_delay)

                host, port = self._parse_endpoint(self._config.endpoint)
                self._reader, self._writer = await asyncio.open_connection(host, port)
                self._connection_state = ConnectionState.CONNECTED

                # Restart receive task
                self._receive_task = asyncio.create_task(self._receive_loop())

                self._logger.info("TCP reconnection successful")
                break

            except Exception as e:
                self._logger.warning(f"Reconnection attempt failed: {e}")
                continue

    def _parse_endpoint(self, endpoint: str) -> Tuple[str, int]:
        """Parse endpoint string into host and port."""
        if ':' in endpoint:
            host, port_str = endpoint.rsplit(':', 1)
            return host, int(port_str)
        else:
            return endpoint, 8080

    def _serialize_message(self, data: Any, metadata: MessageMetadata) -> bytes:
        """Serialize message data and metadata."""
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


class TCPServer(TCPInterface):
    """TCP server for hosting control services."""

    def __init__(self, config: InterfaceConfig):
        super().__init__(config)

    async def start_server(self, host: str = "0.0.0.0", port: int = 8080) -> bool:
        """Start TCP server."""
        return await self.connect({
            'endpoint': f"{host}:{port}",
            'server_mode': True
        })

    def get_connected_clients(self) -> List[str]:
        """Get list of connected client IDs."""
        return list(self._clients.keys())

    async def send_to_client(self, client_id: str, data: Any, metadata: Optional[MessageMetadata] = None) -> bool:
        """Send message to specific client."""
        if client_id not in self._clients:
            return False

        try:
            # Create message metadata if not provided
            if metadata is None:
                metadata = MessageMetadata(
                    message_id=f"tcp_{int(time.time() * 1000000)}",
                    timestamp=time.time(),
                    message_type=MessageType.DATA,
                    priority=Priority.NORMAL,
                    source=self._config.name,
                    destination=client_id
                )

            # Serialize and frame message
            message_data = self._serialize_message(data, metadata)
            framed_message = struct.pack('!I', len(message_data)) + message_data

            # Send to specific client
            reader, writer = self._clients[client_id]
            writer.write(framed_message)
            await writer.drain()

            # Update statistics
            self._stats['messages_sent'] += 1
            self._stats['bytes_sent'] += len(framed_message)
            self._stats['last_activity'] = time.time()

            return True

        except Exception as e:
            self._logger.error(f"Failed to send to client {client_id}: {e}")
            # Remove disconnected client
            if client_id in self._clients:
                reader, writer = self._clients[client_id]
                writer.close()
                del self._clients[client_id]
            return False


class TCPClient(TCPInterface):
    """TCP client for connecting to control services."""

    def __init__(self, config: InterfaceConfig):
        super().__init__(config)

    async def connect_to_server(self, host: str, port: int) -> bool:
        """Connect to TCP server."""
        return await self.connect({
            'endpoint': f"{host}:{port}",
            'server_mode': False
        })