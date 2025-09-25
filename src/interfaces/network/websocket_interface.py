#==========================================================================================\\\
#==================== src/interfaces/network/websocket_interface.py ====================\\\
#==========================================================================================\\\
"""
WebSocket communication interface for real-time control system communication.
This module provides WebSocket-based communication with features like real-time
bidirectional messaging, connection management, and support for both client
and server modes for interactive control applications.
"""

import asyncio
import websockets
import json
import time
from typing import Optional, Dict, Any, Tuple, Callable, Set
import logging

from ..core.protocols import CommunicationProtocol, MessageMetadata, ConnectionState, MessageType, Priority
from ..core.data_types import Message, ConnectionInfo, InterfaceConfig, InterfaceType


class WebSocketInterface(CommunicationProtocol):
    """
    WebSocket communication interface for control systems.

    Features:
    - Real-time bidirectional communication
    - JSON message serialization
    - Connection management
    - Heartbeat/ping-pong support
    - Message broadcasting
    - Client and server modes
    """

    def __init__(self, config: InterfaceConfig):
        """Initialize WebSocket interface with configuration."""
        self._config = config
        self._connection_state = ConnectionState.DISCONNECTED
        self._websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._server: Optional[websockets.WebSocketServer] = None
        self._clients: Set[websockets.WebSocketServerProtocol] = set()
        self._stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'connections_established': 0,
            'connections_lost': 0,
            'heartbeats_sent': 0,
            'heartbeats_received': 0,
            'last_activity': 0.0
        }
        self._message_handlers: Dict[MessageType, Callable] = {}
        self._heartbeat_interval = config.get_setting('heartbeat_interval', 30.0)
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._logger = logging.getLogger(f"websocket_interface_{config.name}")

    async def connect(self, config: Dict[str, Any]) -> bool:
        """Establish WebSocket connection."""
        try:
            if config.get('server_mode', False):
                # Server mode - start WebSocket server
                await self._start_server(config)
            else:
                # Client mode - connect to WebSocket server
                await self._connect_client(config)

            self._connection_state = ConnectionState.CONNECTED
            self._stats['connections_established'] += 1
            self._stats['last_activity'] = time.time()

            # Start heartbeat task
            if self._heartbeat_interval > 0:
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            return True

        except Exception as e:
            self._logger.error(f"Failed to establish WebSocket connection: {e}")
            self._connection_state = ConnectionState.ERROR
            return False

    async def disconnect(self) -> bool:
        """Close WebSocket connection."""
        try:
            self._connection_state = ConnectionState.DISCONNECTED

            # Cancel tasks
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass

            if self._receive_task:
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass

            # Close client connections
            if self._clients:
                await asyncio.gather(
                    *[client.close() for client in self._clients],
                    return_exceptions=True
                )
                self._clients.clear()

            # Close server
            if self._server:
                self._server.close()
                await self._server.wait_closed()
                self._server = None

            # Close client connection
            if self._websocket:
                await self._websocket.close()
                self._websocket = None

            self._logger.info("WebSocket connection closed")
            return True

        except Exception as e:
            self._logger.error(f"Error closing WebSocket connection: {e}")
            return False

    async def send(self, data: Any, metadata: Optional[MessageMetadata] = None) -> bool:
        """Send data via WebSocket."""
        if self._connection_state != ConnectionState.CONNECTED:
            return False

        try:
            # Create message metadata if not provided
            if metadata is None:
                metadata = MessageMetadata(
                    message_id=f"ws_{int(time.time() * 1000000)}",
                    timestamp=time.time(),
                    message_type=MessageType.DATA,
                    priority=Priority.NORMAL,
                    source=self._config.name
                )

            # Create message
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

            # Serialize message
            message_json = json.dumps(message)

            # Send message
            if self._websocket:
                # Client mode - send to server
                await self._websocket.send(message_json)
            elif self._clients:
                # Server mode - broadcast to all clients
                if self._clients:
                    await asyncio.gather(
                        *[client.send(message_json) for client in self._clients.copy()],
                        return_exceptions=True
                    )
            else:
                return False

            # Update statistics
            self._stats['messages_sent'] += 1
            self._stats['bytes_sent'] += len(message_json.encode('utf-8'))
            self._stats['last_activity'] = time.time()

            return True

        except Exception as e:
            self._logger.error(f"Failed to send WebSocket message: {e}")
            return False

    async def receive(self, timeout: Optional[float] = None) -> Optional[Tuple[Any, MessageMetadata]]:
        """Receive data via WebSocket."""
        if self._connection_state != ConnectionState.CONNECTED:
            return None

        try:
            if self._websocket:
                # Client mode - receive from server
                if timeout:
                    message_json = await asyncio.wait_for(
                        self._websocket.recv(),
                        timeout=timeout
                    )
                else:
                    message_json = await self._websocket.recv()

                return self._deserialize_message(message_json)
            else:
                # Server mode - messages are handled by client handlers
                return None

        except asyncio.TimeoutError:
            return None
        except websockets.exceptions.ConnectionClosed:
            self._connection_state = ConnectionState.ERROR
            return None
        except Exception as e:
            self._logger.error(f"Error receiving WebSocket message: {e}")
            return None

    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self._connection_state

    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket communication statistics."""
        stats = self._stats.copy()
        stats['connection_state'] = self._connection_state.value
        stats['connected_clients'] = len(self._clients)
        stats['is_server'] = self._server is not None
        return stats

    def register_message_handler(self, message_type: MessageType, handler: Callable) -> None:
        """Register handler for specific message type."""
        self._message_handlers[message_type] = handler

    async def send_to_client(self, client: websockets.WebSocketServerProtocol, data: Any, metadata: Optional[MessageMetadata] = None) -> bool:
        """Send message to specific client (server mode)."""
        if client not in self._clients:
            return False

        try:
            # Create message metadata if not provided
            if metadata is None:
                metadata = MessageMetadata(
                    message_id=f"ws_{int(time.time() * 1000000)}",
                    timestamp=time.time(),
                    message_type=MessageType.DATA,
                    priority=Priority.NORMAL,
                    source=self._config.name
                )

            # Create and serialize message
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

            message_json = json.dumps(message)
            await client.send(message_json)

            # Update statistics
            self._stats['messages_sent'] += 1
            self._stats['bytes_sent'] += len(message_json.encode('utf-8'))
            self._stats['last_activity'] = time.time()

            return True

        except Exception as e:
            self._logger.error(f"Failed to send to WebSocket client: {e}")
            # Remove disconnected client
            self._clients.discard(client)
            return False

    async def _start_server(self, config: Dict[str, Any]) -> None:
        """Start WebSocket server."""
        host, port = self._parse_endpoint(config.get('endpoint', self._config.endpoint))

        self._server = await websockets.serve(
            self._handle_client_connection,
            host,
            port
        )

        self._logger.info(f"WebSocket server listening on {host}:{port}")

    async def _connect_client(self, config: Dict[str, Any]) -> None:
        """Connect WebSocket client."""
        endpoint = config.get('endpoint', self._config.endpoint)
        if not endpoint.startswith('ws://') and not endpoint.startswith('wss://'):
            endpoint = f"ws://{endpoint}"

        self._websocket = await websockets.connect(endpoint)
        self._logger.info(f"WebSocket client connected to {endpoint}")

        # Start receive task for client mode
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def _handle_client_connection(self, websocket: websockets.WebSocketServerProtocol, path: str) -> None:
        """Handle new client connection."""
        client_addr = websocket.remote_address
        self._logger.info(f"New WebSocket client connected: {client_addr}")

        self._clients.add(websocket)

        try:
            async for message_json in websocket:
                try:
                    message_data, metadata = self._deserialize_message(message_json)

                    # Update statistics
                    self._stats['messages_received'] += 1
                    self._stats['bytes_received'] += len(message_json.encode('utf-8'))
                    self._stats['last_activity'] = time.time()

                    # Call registered handlers
                    handler = self._message_handlers.get(metadata.message_type)
                    if handler:
                        asyncio.create_task(self._call_handler(handler, message_data, metadata, websocket))

                except Exception as e:
                    self._logger.error(f"Error processing WebSocket message: {e}")

        except websockets.exceptions.ConnectionClosed:
            self._logger.info(f"WebSocket client disconnected: {client_addr}")
        except Exception as e:
            self._logger.error(f"Error handling WebSocket client: {e}")
        finally:
            self._clients.discard(websocket)
            self._stats['connections_lost'] += 1

    async def _receive_loop(self) -> None:
        """Continuous receive loop for client mode."""
        try:
            while self._connection_state == ConnectionState.CONNECTED and self._websocket:
                try:
                    message_json = await self._websocket.recv()
                    message_data, metadata = self._deserialize_message(message_json)

                    # Update statistics
                    self._stats['messages_received'] += 1
                    self._stats['bytes_received'] += len(message_json.encode('utf-8'))
                    self._stats['last_activity'] = time.time()

                    # Call registered handlers
                    handler = self._message_handlers.get(metadata.message_type)
                    if handler:
                        asyncio.create_task(self._call_handler(handler, message_data, metadata))

                except websockets.exceptions.ConnectionClosed:
                    self._connection_state = ConnectionState.ERROR
                    break
                except Exception as e:
                    self._logger.error(f"Error in WebSocket receive loop: {e}")

        except Exception as e:
            self._logger.error(f"Error in WebSocket receive loop: {e}")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat messages."""
        try:
            while self._connection_state == ConnectionState.CONNECTED:
                await asyncio.sleep(self._heartbeat_interval)

                if self._connection_state != ConnectionState.CONNECTED:
                    break

                try:
                    # Send heartbeat
                    await self.send(
                        {'type': 'heartbeat', 'timestamp': time.time()},
                        MessageMetadata(
                            message_id=f"heartbeat_{int(time.time())}",
                            timestamp=time.time(),
                            message_type=MessageType.HEARTBEAT,
                            priority=Priority.LOW,
                            source=self._config.name
                        )
                    )

                    self._stats['heartbeats_sent'] += 1

                except Exception as e:
                    self._logger.warning(f"Failed to send heartbeat: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.error(f"Error in heartbeat loop: {e}")

    async def _call_handler(self, handler: Callable, data: Any, metadata: MessageMetadata, websocket: Optional[websockets.WebSocketServerProtocol] = None) -> None:
        """Call message handler safely."""
        try:
            if asyncio.iscoroutinefunction(handler):
                if websocket:
                    await handler(data, metadata, websocket)
                else:
                    await handler(data, metadata)
            else:
                if websocket:
                    handler(data, metadata, websocket)
                else:
                    handler(data, metadata)
        except Exception as e:
            self._logger.error(f"Error in WebSocket message handler: {e}")

    def _deserialize_message(self, message_json: str) -> Tuple[Any, MessageMetadata]:
        """Deserialize WebSocket message."""
        try:
            message = json.loads(message_json)

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
            self._logger.error(f"Failed to deserialize WebSocket message: {e}")
            raise

    def _parse_endpoint(self, endpoint: str) -> Tuple[str, int]:
        """Parse endpoint string into host and port."""
        # Remove protocol if present
        if '://' in endpoint:
            endpoint = endpoint.split('://', 1)[1]

        if ':' in endpoint:
            host, port_str = endpoint.rsplit(':', 1)
            return host, int(port_str)
        else:
            return endpoint, 8080


class WebSocketServer(WebSocketInterface):
    """WebSocket server for hosting real-time control services."""

    def __init__(self, config: InterfaceConfig):
        super().__init__(config)

    async def start_server(self, host: str = "0.0.0.0", port: int = 8080) -> bool:
        """Start WebSocket server."""
        return await self.connect({
            'endpoint': f"{host}:{port}",
            'server_mode': True
        })

    def get_connected_clients(self) -> Set[websockets.WebSocketServerProtocol]:
        """Get set of connected clients."""
        return self._clients.copy()

    async def broadcast(self, data: Any, metadata: Optional[MessageMetadata] = None) -> int:
        """Broadcast message to all connected clients."""
        if not self._clients:
            return 0

        success_count = 0
        for client in self._clients.copy():
            if await self.send_to_client(client, data, metadata):
                success_count += 1

        return success_count


class WebSocketClient(WebSocketInterface):
    """WebSocket client for connecting to real-time control services."""

    def __init__(self, config: InterfaceConfig):
        super().__init__(config)

    async def connect_to_server(self, url: str) -> bool:
        """Connect to WebSocket server."""
        return await self.connect({
            'endpoint': url,
            'server_mode': False
        })