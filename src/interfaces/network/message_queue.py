#==========================================================================================\\\
#====================== src/interfaces/network/message_queue.py =========================\\\
#==========================================================================================\\\
"""
Message queue communication interfaces for distributed control systems.
This module provides message queue-based communication with support for
ZeroMQ, RabbitMQ, and other queue systems for scalable, reliable
messaging in distributed control applications.
"""

import asyncio
import time
import json
import pickle
from typing import Optional, Dict, Any, Tuple, Callable, List
import logging
from abc import ABC, abstractmethod

from ..core.protocols import CommunicationProtocol, MessageMetadata, ConnectionState, MessageType, Priority
from ..core.data_types import Message, ConnectionInfo, InterfaceConfig, InterfaceType

try:
    import zmq
    import zmq.asyncio
    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False

try:
    import aio_pika
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False


class MessageQueueInterface(CommunicationProtocol, ABC):
    """
    Abstract base class for message queue interfaces.

    Features:
    - Publish/subscribe messaging patterns
    - Request/reply patterns
    - Message persistence
    - Load balancing
    - Acknowledgments and reliability
    """

    def __init__(self, config: InterfaceConfig):
        """Initialize message queue interface."""
        self._config = config
        self._connection_state = ConnectionState.DISCONNECTED
        self._stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'publish_count': 0,
            'subscribe_count': 0,
            'last_activity': 0.0
        }
        self._message_handlers: Dict[str, Callable] = {}  # topic -> handler
        self._logger = logging.getLogger(f"mq_interface_{config.name}")

    @abstractmethod
    async def publish(self, topic: str, data: Any, metadata: Optional[MessageMetadata] = None) -> bool:
        """Publish message to topic."""
        pass

    @abstractmethod
    async def subscribe(self, topic: str, handler: Callable) -> bool:
        """Subscribe to topic with message handler."""
        pass

    @abstractmethod
    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from topic."""
        pass

    @abstractmethod
    async def request(self, data: Any, timeout: Optional[float] = None) -> Optional[Any]:
        """Send request and wait for reply."""
        pass

    @abstractmethod
    async def reply(self, request_data: Any, response_data: Any) -> bool:
        """Send reply to request."""
        pass


class ZeroMQInterface(MessageQueueInterface):
    """
    ZeroMQ communication interface for high-performance messaging.

    Features:
    - Multiple socket patterns (PUB/SUB, REQ/REP, PUSH/PULL)
    - High throughput and low latency
    - Built-in load balancing
    - No broker required
    """

    def __init__(self, config: InterfaceConfig):
        """Initialize ZeroMQ interface."""
        if not ZMQ_AVAILABLE:
            raise ImportError("ZeroMQ not available. Install with: pip install pyzmq")

        super().__init__(config)
        self._context: Optional[zmq.asyncio.Context] = None
        self._sockets: Dict[str, zmq.asyncio.Socket] = {}
        self._socket_types = {
            'pub': zmq.PUB,
            'sub': zmq.SUB,
            'req': zmq.REQ,
            'rep': zmq.REP,
            'push': zmq.PUSH,
            'pull': zmq.PULL,
            'dealer': zmq.DEALER,
            'router': zmq.ROUTER
        }
        self._receive_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, config: Dict[str, Any]) -> bool:
        """Establish ZeroMQ connection."""
        try:
            self._context = zmq.asyncio.Context()

            # Create sockets based on configuration
            socket_configs = config.get('sockets', [])
            for socket_config in socket_configs:
                await self._create_socket(socket_config)

            self._connection_state = ConnectionState.CONNECTED
            self._stats['last_activity'] = time.time()
            self._logger.info("ZeroMQ interface connected")
            return True

        except Exception as e:
            self._logger.error(f"Failed to establish ZeroMQ connection: {e}")
            self._connection_state = ConnectionState.ERROR
            return False

    async def disconnect(self) -> bool:
        """Close ZeroMQ connection."""
        try:
            self._connection_state = ConnectionState.DISCONNECTED

            # Cancel receive tasks
            for task in self._receive_tasks.values():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            self._receive_tasks.clear()

            # Close sockets
            for socket in self._sockets.values():
                socket.close()
            self._sockets.clear()

            # Terminate context
            if self._context:
                self._context.term()
                self._context = None

            self._logger.info("ZeroMQ connection closed")
            return True

        except Exception as e:
            self._logger.error(f"Error closing ZeroMQ connection: {e}")
            return False

    async def send(self, data: Any, metadata: Optional[MessageMetadata] = None) -> bool:
        """Send data via ZeroMQ (using default socket)."""
        # Use publish method for default sending
        return await self.publish("default", data, metadata)

    async def receive(self, timeout: Optional[float] = None) -> Optional[Tuple[Any, MessageMetadata]]:
        """Receive data via ZeroMQ (from default socket)."""
        # ZeroMQ typically uses handlers for receiving
        # This method is provided for compatibility
        return None

    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self._connection_state

    def get_statistics(self) -> Dict[str, Any]:
        """Get ZeroMQ communication statistics."""
        stats = self._stats.copy()
        stats['connection_state'] = self._connection_state.value
        stats['active_sockets'] = len(self._sockets)
        stats['socket_names'] = list(self._sockets.keys())
        return stats

    async def publish(self, topic: str, data: Any, metadata: Optional[MessageMetadata] = None) -> bool:
        """Publish message to topic using PUB socket."""
        try:
            pub_socket = self._sockets.get('pub')
            if not pub_socket:
                self._logger.error("No PUB socket available for publishing")
                return False

            # Create message metadata if not provided
            if metadata is None:
                metadata = MessageMetadata(
                    message_id=f"zmq_{int(time.time() * 1000000)}",
                    timestamp=time.time(),
                    message_type=MessageType.DATA,
                    priority=Priority.NORMAL,
                    source=self._config.name
                )

            # Serialize message
            message_data = self._serialize_message(data, metadata)

            # Send with topic prefix
            await pub_socket.send_multipart([
                topic.encode('utf-8'),
                message_data
            ])

            # Update statistics
            self._stats['messages_sent'] += 1
            self._stats['publish_count'] += 1
            self._stats['bytes_sent'] += len(message_data)
            self._stats['last_activity'] = time.time()

            return True

        except Exception as e:
            self._logger.error(f"Failed to publish ZeroMQ message: {e}")
            return False

    async def subscribe(self, topic: str, handler: Callable) -> bool:
        """Subscribe to topic with message handler."""
        try:
            sub_socket = self._sockets.get('sub')
            if not sub_socket:
                self._logger.error("No SUB socket available for subscribing")
                return False

            # Set subscription filter
            sub_socket.setsockopt(zmq.SUBSCRIBE, topic.encode('utf-8'))

            # Register handler
            self._message_handlers[topic] = handler

            # Start receive task if not already running
            if 'sub' not in self._receive_tasks:
                self._receive_tasks['sub'] = asyncio.create_task(
                    self._subscribe_receive_loop()
                )

            self._stats['subscribe_count'] += 1
            self._logger.info(f"Subscribed to topic: {topic}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to subscribe to topic {topic}: {e}")
            return False

    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from topic."""
        try:
            sub_socket = self._sockets.get('sub')
            if not sub_socket:
                return False

            # Remove subscription filter
            sub_socket.setsockopt(zmq.UNSUBSCRIBE, topic.encode('utf-8'))

            # Remove handler
            if topic in self._message_handlers:
                del self._message_handlers[topic]

            self._logger.info(f"Unsubscribed from topic: {topic}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to unsubscribe from topic {topic}: {e}")
            return False

    async def request(self, data: Any, timeout: Optional[float] = None) -> Optional[Any]:
        """Send request and wait for reply using REQ socket."""
        try:
            req_socket = self._sockets.get('req')
            if not req_socket:
                self._logger.error("No REQ socket available for request")
                return None

            # Create metadata
            metadata = MessageMetadata(
                message_id=f"zmq_req_{int(time.time() * 1000000)}",
                timestamp=time.time(),
                message_type=MessageType.COMMAND,
                priority=Priority.NORMAL,
                source=self._config.name
            )

            # Serialize and send request
            message_data = self._serialize_message(data, metadata)
            await req_socket.send(message_data)

            # Wait for reply
            if timeout:
                reply_data = await asyncio.wait_for(
                    req_socket.recv(),
                    timeout=timeout
                )
            else:
                reply_data = await req_socket.recv()

            # Deserialize reply
            reply, reply_metadata = self._deserialize_message(reply_data)

            # Update statistics
            self._stats['messages_sent'] += 1
            self._stats['messages_received'] += 1
            self._stats['last_activity'] = time.time()

            return reply

        except asyncio.TimeoutError:
            self._logger.warning("Request timeout")
            return None
        except Exception as e:
            self._logger.error(f"Request failed: {e}")
            return None

    async def reply(self, request_data: Any, response_data: Any) -> bool:
        """Send reply to request using REP socket."""
        try:
            rep_socket = self._sockets.get('rep')
            if not rep_socket:
                self._logger.error("No REP socket available for reply")
                return False

            # Create metadata
            metadata = MessageMetadata(
                message_id=f"zmq_rep_{int(time.time() * 1000000)}",
                timestamp=time.time(),
                message_type=MessageType.RESPONSE,
                priority=Priority.NORMAL,
                source=self._config.name
            )

            # Serialize and send reply
            message_data = self._serialize_message(response_data, metadata)
            await rep_socket.send(message_data)

            # Update statistics
            self._stats['messages_sent'] += 1
            self._stats['last_activity'] = time.time()

            return True

        except Exception as e:
            self._logger.error(f"Failed to send reply: {e}")
            return False

    async def _create_socket(self, socket_config: Dict[str, Any]) -> None:
        """Create and configure ZeroMQ socket."""
        socket_name = socket_config['name']
        socket_type = socket_config['type']
        endpoint = socket_config['endpoint']
        bind = socket_config.get('bind', False)

        if socket_type not in self._socket_types:
            raise ValueError(f"Unknown socket type: {socket_type}")

        # Create socket
        socket = self._context.socket(self._socket_types[socket_type])

        # Configure socket options
        options = socket_config.get('options', {})
        for option, value in options.items():
            socket.setsockopt(getattr(zmq, option.upper()), value)

        # Bind or connect
        if bind:
            socket.bind(endpoint)
            self._logger.info(f"ZeroMQ {socket_type} socket '{socket_name}' bound to {endpoint}")
        else:
            socket.connect(endpoint)
            self._logger.info(f"ZeroMQ {socket_type} socket '{socket_name}' connected to {endpoint}")

        self._sockets[socket_name] = socket

        # Start receive task for reply sockets
        if socket_type == 'rep':
            self._receive_tasks[socket_name] = asyncio.create_task(
                self._reply_receive_loop(socket)
            )

    async def _subscribe_receive_loop(self) -> None:
        """Receive loop for SUB socket."""
        try:
            sub_socket = self._sockets['sub']

            while self._connection_state == ConnectionState.CONNECTED:
                try:
                    # Receive multipart message
                    topic_bytes, message_data = await sub_socket.recv_multipart()
                    topic = topic_bytes.decode('utf-8')

                    # Deserialize message
                    data, metadata = self._deserialize_message(message_data)

                    # Update statistics
                    self._stats['messages_received'] += 1
                    self._stats['bytes_received'] += len(message_data)
                    self._stats['last_activity'] = time.time()

                    # Call handler
                    handler = self._message_handlers.get(topic)
                    if handler:
                        asyncio.create_task(self._call_handler(handler, data, metadata, topic))

                except Exception as e:
                    self._logger.error(f"Error in subscribe receive loop: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.error(f"Subscribe receive loop error: {e}")

    async def _reply_receive_loop(self, rep_socket: zmq.asyncio.Socket) -> None:
        """Receive loop for REP socket."""
        try:
            while self._connection_state == ConnectionState.CONNECTED:
                try:
                    # Receive request
                    message_data = await rep_socket.recv()

                    # Deserialize request
                    data, metadata = self._deserialize_message(message_data)

                    # Update statistics
                    self._stats['messages_received'] += 1
                    self._stats['bytes_received'] += len(message_data)
                    self._stats['last_activity'] = time.time()

                    # Call handler (should send reply)
                    handler = self._message_handlers.get('request')
                    if handler:
                        asyncio.create_task(self._call_handler(handler, data, metadata))
                    else:
                        # Send default reply if no handler
                        await self.reply(data, {'status': 'no_handler'})

                except Exception as e:
                    self._logger.error(f"Error in reply receive loop: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.error(f"Reply receive loop error: {e}")

    async def _call_handler(self, handler: Callable, data: Any, metadata: MessageMetadata, topic: Optional[str] = None) -> None:
        """Call message handler safely."""
        try:
            if asyncio.iscoroutinefunction(handler):
                if topic:
                    await handler(data, metadata, topic)
                else:
                    await handler(data, metadata)
            else:
                if topic:
                    handler(data, metadata, topic)
                else:
                    handler(data, metadata)
        except Exception as e:
            self._logger.error(f"Error in ZeroMQ message handler: {e}")

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
            self._logger.error(f"Failed to deserialize ZeroMQ message: {e}")
            raise


class RabbitMQInterface(MessageQueueInterface):
    """
    RabbitMQ communication interface for reliable messaging.

    Features:
    - Message persistence and durability
    - Routing and exchanges
    - Acknowledgments and reliability
    - Dead letter queues
    """

    def __init__(self, config: InterfaceConfig):
        """Initialize RabbitMQ interface."""
        if not RABBITMQ_AVAILABLE:
            raise ImportError("RabbitMQ client not available. Install with: pip install aio-pika")

        super().__init__(config)
        self._connection: Optional[aio_pika.Connection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._queues: Dict[str, aio_pika.Queue] = {}
        self._exchanges: Dict[str, aio_pika.Exchange] = {}

    async def connect(self, config: Dict[str, Any]) -> bool:
        """Establish RabbitMQ connection."""
        try:
            url = config.get('url', 'amqp://guest:guest@localhost/')
            self._connection = await aio_pika.connect_robust(url)
            self._channel = await self._connection.channel()

            self._connection_state = ConnectionState.CONNECTED
            self._stats['last_activity'] = time.time()
            self._logger.info("RabbitMQ interface connected")
            return True

        except Exception as e:
            self._logger.error(f"Failed to establish RabbitMQ connection: {e}")
            self._connection_state = ConnectionState.ERROR
            return False

    async def disconnect(self) -> bool:
        """Close RabbitMQ connection."""
        try:
            self._connection_state = ConnectionState.DISCONNECTED

            if self._connection:
                await self._connection.close()
                self._connection = None
                self._channel = None

            self._queues.clear()
            self._exchanges.clear()

            self._logger.info("RabbitMQ connection closed")
            return True

        except Exception as e:
            self._logger.error(f"Error closing RabbitMQ connection: {e}")
            return False

    async def send(self, data: Any, metadata: Optional[MessageMetadata] = None) -> bool:
        """Send data via RabbitMQ (using default exchange)."""
        return await self.publish("", data, metadata)

    async def receive(self, timeout: Optional[float] = None) -> Optional[Tuple[Any, MessageMetadata]]:
        """Receive data via RabbitMQ."""
        # RabbitMQ typically uses handlers for receiving
        return None

    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self._connection_state

    def get_statistics(self) -> Dict[str, Any]:
        """Get RabbitMQ communication statistics."""
        stats = self._stats.copy()
        stats['connection_state'] = self._connection_state.value
        stats['active_queues'] = len(self._queues)
        stats['active_exchanges'] = len(self._exchanges)
        return stats

    async def publish(self, routing_key: str, data: Any, metadata: Optional[MessageMetadata] = None, exchange: str = "") -> bool:
        """Publish message to RabbitMQ exchange."""
        try:
            if not self._channel:
                return False

            # Create message metadata if not provided
            if metadata is None:
                metadata = MessageMetadata(
                    message_id=f"rmq_{int(time.time() * 1000000)}",
                    timestamp=time.time(),
                    message_type=MessageType.DATA,
                    priority=Priority.NORMAL,
                    source=self._config.name
                )

            # Serialize message
            message_data = self._serialize_message(data, metadata)

            # Create message
            message = aio_pika.Message(
                message_data,
                message_id=metadata.message_id,
                timestamp=metadata.timestamp,
                headers={
                    'source': metadata.source,
                    'message_type': metadata.message_type.value,
                    'priority': metadata.priority.value
                }
            )

            # Get exchange
            if exchange and exchange in self._exchanges:
                exchange_obj = self._exchanges[exchange]
            else:
                exchange_obj = self._channel.default_exchange

            # Publish message
            await exchange_obj.publish(message, routing_key=routing_key)

            # Update statistics
            self._stats['messages_sent'] += 1
            self._stats['publish_count'] += 1
            self._stats['bytes_sent'] += len(message_data)
            self._stats['last_activity'] = time.time()

            return True

        except Exception as e:
            self._logger.error(f"Failed to publish RabbitMQ message: {e}")
            return False

    async def subscribe(self, queue_name: str, handler: Callable) -> bool:
        """Subscribe to RabbitMQ queue with message handler."""
        try:
            if not self._channel:
                return False

            # Declare queue
            queue = await self._channel.declare_queue(queue_name, durable=True)
            self._queues[queue_name] = queue

            # Register handler
            self._message_handlers[queue_name] = handler

            # Start consuming
            await queue.consume(
                lambda message: asyncio.create_task(
                    self._handle_rabbitmq_message(message, handler)
                )
            )

            self._stats['subscribe_count'] += 1
            self._logger.info(f"Subscribed to RabbitMQ queue: {queue_name}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to subscribe to queue {queue_name}: {e}")
            return False

    async def unsubscribe(self, queue_name: str) -> bool:
        """Unsubscribe from RabbitMQ queue."""
        try:
            if queue_name in self._queues:
                queue = self._queues[queue_name]
                await queue.cancel()
                del self._queues[queue_name]

            if queue_name in self._message_handlers:
                del self._message_handlers[queue_name]

            self._logger.info(f"Unsubscribed from RabbitMQ queue: {queue_name}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to unsubscribe from queue {queue_name}: {e}")
            return False

    async def request(self, data: Any, timeout: Optional[float] = None) -> Optional[Any]:
        """Send request and wait for reply using RabbitMQ RPC pattern."""
        # Implementation would require setting up temporary reply queue
        # and correlation IDs for RPC pattern
        self._logger.warning("RabbitMQ request/reply not yet implemented")
        return None

    async def reply(self, request_data: Any, response_data: Any) -> bool:
        """Send reply to request using RabbitMQ."""
        # Implementation would require extracting reply_to and correlation_id
        # from request message and sending to reply queue
        self._logger.warning("RabbitMQ request/reply not yet implemented")
        return False

    async def _handle_rabbitmq_message(self, message: aio_pika.IncomingMessage, handler: Callable) -> None:
        """Handle incoming RabbitMQ message."""
        try:
            async with message.process():
                # Deserialize message
                data, metadata = self._deserialize_message(message.body)

                # Update statistics
                self._stats['messages_received'] += 1
                self._stats['bytes_received'] += len(message.body)
                self._stats['last_activity'] = time.time()

                # Call handler
                await self._call_handler(handler, data, metadata)

        except Exception as e:
            self._logger.error(f"Error handling RabbitMQ message: {e}")

    async def _call_handler(self, handler: Callable, data: Any, metadata: MessageMetadata) -> None:
        """Call message handler safely."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(data, metadata)
            else:
                handler(data, metadata)
        except Exception as e:
            self._logger.error(f"Error in RabbitMQ message handler: {e}")

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

        return json.dumps(message).encode('utf-8')

    def _deserialize_message(self, data: bytes) -> Tuple[Any, MessageMetadata]:
        """Deserialize message data and metadata."""
        try:
            message = json.loads(data.decode('utf-8'))

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
            self._logger.error(f"Failed to deserialize RabbitMQ message: {e}")
            raise