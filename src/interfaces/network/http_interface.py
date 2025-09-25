#==========================================================================================\\\
#======================= src/interfaces/network/http_interface.py =======================\\\
#==========================================================================================\\\
"""
HTTP/REST communication interface for control system web services.
This module provides HTTP-based communication with RESTful APIs, JSON
serialization, authentication, and CORS support for web-based control
applications and monitoring dashboards.
"""

import asyncio
import aiohttp
import json
import time
from typing import Optional, Dict, Any, Tuple, Callable, List
import logging
from aiohttp import web, ClientSession, ClientTimeout

from ..core.protocols import CommunicationProtocol, MessageMetadata, ConnectionState, MessageType, Priority
from ..core.data_types import Message, ConnectionInfo, InterfaceConfig, InterfaceType


class HTTPInterface(CommunicationProtocol):
    """
    HTTP/REST communication interface for control systems.

    Features:
    - RESTful HTTP communication
    - JSON serialization
    - Authentication and authorization
    - CORS support for web clients
    - Request/response pattern
    - Health monitoring endpoints
    """

    def __init__(self, config: InterfaceConfig):
        """Initialize HTTP interface with configuration."""
        self._config = config
        self._connection_state = ConnectionState.DISCONNECTED
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._session: Optional[ClientSession] = None
        self._stats = {
            'requests_sent': 0,
            'requests_received': 0,
            'responses_sent': 0,
            'responses_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'errors': 0,
            'last_activity': 0.0
        }
        self._routes: Dict[str, Dict[str, Callable]] = {}
        self._middleware: List[Callable] = []
        self._auth_handler: Optional[Callable] = None
        self._cors_enabled = config.get_setting('enable_cors', True)
        self._logger = logging.getLogger(f"http_interface_{config.name}")

    async def connect(self, config: Dict[str, Any]) -> bool:
        """Establish HTTP connection (server or client)."""
        try:
            if config.get('server_mode', False):
                # Server mode - start HTTP server
                await self._start_server(config)
            else:
                # Client mode - create session
                timeout = ClientTimeout(total=config.get('timeout', 30.0))
                self._session = ClientSession(timeout=timeout)

            self._connection_state = ConnectionState.CONNECTED
            self._stats['last_activity'] = time.time()
            return True

        except Exception as e:
            self._logger.error(f"Failed to establish HTTP connection: {e}")
            self._connection_state = ConnectionState.ERROR
            return False

    async def disconnect(self) -> bool:
        """Close HTTP connection."""
        try:
            self._connection_state = ConnectionState.DISCONNECTED

            # Close server
            if self._site:
                await self._site.stop()
                self._site = None

            if self._runner:
                await self._runner.cleanup()
                self._runner = None

            self._app = None

            # Close client session
            if self._session:
                await self._session.close()
                self._session = None

            self._logger.info("HTTP connection closed")
            return True

        except Exception as e:
            self._logger.error(f"Error closing HTTP connection: {e}")
            return False

    async def send(self, data: Any, metadata: Optional[MessageMetadata] = None) -> bool:
        """Send HTTP request (client mode)."""
        if self._connection_state != ConnectionState.CONNECTED or not self._session:
            return False

        try:
            # Create message metadata if not provided
            if metadata is None:
                metadata = MessageMetadata(
                    message_id=f"http_{int(time.time() * 1000000)}",
                    timestamp=time.time(),
                    message_type=MessageType.DATA,
                    priority=Priority.NORMAL,
                    source=self._config.name
                )

            # Extract HTTP-specific parameters from data
            if isinstance(data, dict):
                method = data.get('method', 'POST')
                url = data.get('url', self._config.endpoint)
                headers = data.get('headers', {})
                payload = data.get('payload', {})
            else:
                method = 'POST'
                url = self._config.endpoint
                headers = {}
                payload = data

            # Add standard headers
            headers['Content-Type'] = 'application/json'
            headers['X-Message-ID'] = metadata.message_id
            headers['X-Timestamp'] = str(metadata.timestamp)

            # Send HTTP request
            async with self._session.request(
                method=method,
                url=url,
                json=payload,
                headers=headers
            ) as response:
                response_data = await response.text()

                # Update statistics
                self._stats['requests_sent'] += 1
                self._stats['responses_received'] += 1
                self._stats['bytes_sent'] += len(json.dumps(payload).encode('utf-8'))
                self._stats['bytes_received'] += len(response_data.encode('utf-8'))
                self._stats['last_activity'] = time.time()

                return response.status < 400

        except Exception as e:
            self._logger.error(f"Failed to send HTTP request: {e}")
            self._stats['errors'] += 1
            return False

    async def receive(self, timeout: Optional[float] = None) -> Optional[Tuple[Any, MessageMetadata]]:
        """Receive HTTP request/response (not applicable for HTTP)."""
        # HTTP is request/response based, not streaming
        # This method would be used differently in HTTP context
        return None

    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self._connection_state

    def get_statistics(self) -> Dict[str, Any]:
        """Get HTTP communication statistics."""
        stats = self._stats.copy()
        stats['connection_state'] = self._connection_state.value
        stats['is_server'] = self._app is not None
        stats['registered_routes'] = len(self._routes)
        return stats

    def add_route(self, method: str, path: str, handler: Callable) -> None:
        """Add HTTP route handler."""
        if path not in self._routes:
            self._routes[path] = {}
        self._routes[path][method.upper()] = handler

    def add_middleware(self, middleware: Callable) -> None:
        """Add HTTP middleware."""
        self._middleware.append(middleware)

    def set_auth_handler(self, handler: Callable) -> None:
        """Set authentication handler."""
        self._auth_handler = handler

    async def _start_server(self, config: Dict[str, Any]) -> None:
        """Start HTTP server."""
        # Create aiohttp application
        self._app = web.Application()

        # Add CORS middleware if enabled
        if self._cors_enabled:
            self._app.middlewares.append(self._cors_middleware)

        # Add authentication middleware if configured
        if self._auth_handler:
            self._app.middlewares.append(self._auth_middleware)

        # Add custom middleware
        for middleware in self._middleware:
            self._app.middlewares.append(middleware)

        # Add logging middleware
        self._app.middlewares.append(self._logging_middleware)

        # Register routes
        self._register_routes()

        # Add default health check endpoint
        self._app.router.add_get('/health', self._health_check_handler)
        self._app.router.add_get('/stats', self._stats_handler)

        # Start server
        host, port = self._parse_endpoint(config.get('endpoint', self._config.endpoint))
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, host, port)
        await self._site.start()

        self._logger.info(f"HTTP server listening on {host}:{port}")

    def _register_routes(self) -> None:
        """Register all configured routes."""
        for path, methods in self._routes.items():
            for method, handler in methods.items():
                if method == 'GET':
                    self._app.router.add_get(path, self._wrap_handler(handler))
                elif method == 'POST':
                    self._app.router.add_post(path, self._wrap_handler(handler))
                elif method == 'PUT':
                    self._app.router.add_put(path, self._wrap_handler(handler))
                elif method == 'DELETE':
                    self._app.router.add_delete(path, self._wrap_handler(handler))
                elif method == 'PATCH':
                    self._app.router.add_patch(path, self._wrap_handler(handler))

    def _wrap_handler(self, handler: Callable) -> Callable:
        """Wrap user handler with standard processing."""
        async def wrapped_handler(request: web.Request) -> web.Response:
            try:
                # Extract metadata from headers
                metadata = MessageMetadata(
                    message_id=request.headers.get('X-Message-ID', f"http_{int(time.time() * 1000000)}"),
                    timestamp=float(request.headers.get('X-Timestamp', time.time())),
                    message_type=MessageType.DATA,
                    priority=Priority.NORMAL,
                    source=request.headers.get('X-Source', 'unknown')
                )

                # Get request data
                if request.content_type == 'application/json':
                    data = await request.json()
                else:
                    data = await request.text()

                # Call user handler
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(data, metadata, request)
                else:
                    result = handler(data, metadata, request)

                # Update statistics
                self._stats['requests_received'] += 1
                self._stats['last_activity'] = time.time()

                # Create response
                if isinstance(result, web.Response):
                    response = result
                elif isinstance(result, dict):
                    response = web.json_response(result)
                else:
                    response = web.Response(text=str(result))

                # Update response statistics
                self._stats['responses_sent'] += 1
                return response

            except Exception as e:
                self._logger.error(f"Error in HTTP handler: {e}")
                self._stats['errors'] += 1
                return web.json_response(
                    {'error': str(e)},
                    status=500
                )

        return wrapped_handler

    @web.middleware
    async def _cors_middleware(self, request: web.Request, handler: Callable) -> web.Response:
        """CORS middleware."""
        if request.method == 'OPTIONS':
            response = web.Response()
        else:
            response = await handler(request)

        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Message-ID, X-Timestamp, X-Source'

        return response

    @web.middleware
    async def _auth_middleware(self, request: web.Request, handler: Callable) -> web.Response:
        """Authentication middleware."""
        # Skip auth for health check and CORS preflight
        if request.path in ['/health', '/stats'] or request.method == 'OPTIONS':
            return await handler(request)

        try:
            # Call authentication handler
            if asyncio.iscoroutinefunction(self._auth_handler):
                is_authenticated = await self._auth_handler(request)
            else:
                is_authenticated = self._auth_handler(request)

            if not is_authenticated:
                return web.json_response(
                    {'error': 'Authentication required'},
                    status=401
                )

            return await handler(request)

        except Exception as e:
            self._logger.error(f"Authentication error: {e}")
            return web.json_response(
                {'error': 'Authentication failed'},
                status=401
            )

    @web.middleware
    async def _logging_middleware(self, request: web.Request, handler: Callable) -> web.Response:
        """Logging middleware."""
        start_time = time.time()

        try:
            response = await handler(request)
            duration = time.time() - start_time

            self._logger.info(
                f"{request.method} {request.path} -> {response.status} "
                f"({duration:.3f}s)"
            )

            return response

        except Exception as e:
            duration = time.time() - start_time
            self._logger.error(
                f"{request.method} {request.path} -> ERROR {str(e)} "
                f"({duration:.3f}s)"
            )
            raise

    async def _health_check_handler(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        health_data = {
            'status': 'healthy',
            'timestamp': time.time(),
            'connection_state': self._connection_state.value,
            'uptime': time.time() - self._stats['last_activity']
        }
        return web.json_response(health_data)

    async def _stats_handler(self, request: web.Request) -> web.Response:
        """Statistics endpoint."""
        return web.json_response(self.get_statistics())

    def _parse_endpoint(self, endpoint: str) -> Tuple[str, int]:
        """Parse endpoint string into host and port."""
        if '://' in endpoint:
            # Remove protocol if present
            endpoint = endpoint.split('://', 1)[1]

        if ':' in endpoint:
            host, port_str = endpoint.rsplit(':', 1)
            return host, int(port_str)
        else:
            return endpoint, 8080


class HTTPServer(HTTPInterface):
    """HTTP server for hosting RESTful control services."""

    def __init__(self, config: InterfaceConfig):
        super().__init__(config)

    async def start_server(self, host: str = "0.0.0.0", port: int = 8080) -> bool:
        """Start HTTP server."""
        return await self.connect({
            'endpoint': f"{host}:{port}",
            'server_mode': True
        })

    def add_get_route(self, path: str, handler: Callable) -> None:
        """Add GET route."""
        self.add_route('GET', path, handler)

    def add_post_route(self, path: str, handler: Callable) -> None:
        """Add POST route."""
        self.add_route('POST', path, handler)

    def add_put_route(self, path: str, handler: Callable) -> None:
        """Add PUT route."""
        self.add_route('PUT', path, handler)

    def add_delete_route(self, path: str, handler: Callable) -> None:
        """Add DELETE route."""
        self.add_route('DELETE', path, handler)


class HTTPClient(HTTPInterface):
    """HTTP client for calling RESTful control services."""

    def __init__(self, config: InterfaceConfig):
        super().__init__(config)

    async def connect_to_server(self, base_url: str) -> bool:
        """Connect to HTTP server."""
        self._config.endpoint = base_url
        return await self.connect({
            'endpoint': base_url,
            'server_mode': False
        })

    async def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Send GET request."""
        try:
            url = f"{self._config.endpoint.rstrip('/')}/{path.lstrip('/')}"

            async with self._session.get(url, headers=headers) as response:
                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    return {'text': await response.text()}

        except Exception as e:
            self._logger.error(f"GET request failed: {e}")
            return None

    async def post(self, path: str, data: Any, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Send POST request."""
        try:
            url = f"{self._config.endpoint.rstrip('/')}/{path.lstrip('/')}"

            async with self._session.post(url, json=data, headers=headers) as response:
                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    return {'text': await response.text()}

        except Exception as e:
            self._logger.error(f"POST request failed: {e}")
            return None

    async def put(self, path: str, data: Any, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Send PUT request."""
        try:
            url = f"{self._config.endpoint.rstrip('/')}/{path.lstrip('/')}"

            async with self._session.put(url, json=data, headers=headers) as response:
                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    return {'text': await response.text()}

        except Exception as e:
            self._logger.error(f"PUT request failed: {e}")
            return None

    async def delete(self, path: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Send DELETE request."""
        try:
            url = f"{self._config.endpoint.rstrip('/')}/{path.lstrip('/')}"

            async with self._session.delete(url, headers=headers) as response:
                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    return {'text': await response.text()}

        except Exception as e:
            self._logger.error(f"DELETE request failed: {e}")
            return None