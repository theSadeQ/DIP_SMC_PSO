#==========================================================================================\\\
#========================== src/interfaces/network/factory.py ===========================\\\
#==========================================================================================\\\
"""
Network interface factory for creating communication interfaces.
This module provides factory methods and utilities for creating and
configuring various types of network communication interfaces for
control systems applications.
"""

from typing import Dict, Any, Type, Optional, Union
import logging

from ..core.protocols import CommunicationProtocol
from ..core.data_types import InterfaceConfig, InterfaceType

from .udp_interface import UDPInterface, UDPServer, UDPClient
from .tcp_interface import TCPInterface, TCPServer, TCPClient
from .http_interface import HTTPInterface, HTTPServer, HTTPClient
from .websocket_interface import WebSocketInterface, WebSocketServer, WebSocketClient
from .message_queue import MessageQueueInterface, ZeroMQInterface, RabbitMQInterface


class NetworkInterfaceFactory:
    """
    Factory for creating network communication interfaces.

    This factory provides centralized creation and configuration of
    various network interface types with consistent configuration
    patterns and error handling.
    """

    # Registry of available interface types
    _interface_registry: Dict[str, Type[CommunicationProtocol]] = {
        # UDP interfaces
        'udp': UDPInterface,
        'udp_server': UDPServer,
        'udp_client': UDPClient,

        # TCP interfaces
        'tcp': TCPInterface,
        'tcp_server': TCPServer,
        'tcp_client': TCPClient,

        # HTTP interfaces
        'http': HTTPInterface,
        'http_server': HTTPServer,
        'http_client': HTTPClient,

        # WebSocket interfaces
        'websocket': WebSocketInterface,
        'ws_server': WebSocketServer,
        'ws_client': WebSocketClient,

        # Message queue interfaces
        'zeromq': ZeroMQInterface,
        'rabbitmq': RabbitMQInterface,
    }

    # Default configurations for interface types
    _default_configs: Dict[str, Dict[str, Any]] = {
        'udp': {
            'endpoint': 'localhost:8080',
            'use_crc': True,
            'use_sequence': True,
            'buffer_size': 4096,
        },
        'tcp': {
            'endpoint': 'localhost:8080',
            'auto_reconnect': True,
            'reconnect_delay': 5.0,
            'max_message_size': 1024 * 1024,
        },
        'http': {
            'endpoint': 'localhost:8080',
            'enable_cors': True,
            'timeout': 30.0,
        },
        'websocket': {
            'endpoint': 'localhost:8080',
            'heartbeat_interval': 30.0,
        },
        'zeromq': {
            'sockets': [
                {
                    'name': 'pub',
                    'type': 'pub',
                    'endpoint': 'tcp://localhost:5555',
                    'bind': True
                }
            ]
        },
        'rabbitmq': {
            'url': 'amqp://guest:guest@localhost/',
        }
    }

    @classmethod
    def create_interface(
        cls,
        interface_type: str,
        name: str = "default",
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> CommunicationProtocol:
        """
        Create network interface of specified type.

        Parameters
        ----------
        interface_type : str
            Type of interface to create (e.g., 'udp', 'tcp_server', 'websocket')
        name : str
            Name for the interface instance
        config_overrides : Dict[str, Any], optional
            Configuration overrides for the interface

        Returns
        -------
        CommunicationProtocol
            Configured network interface instance

        Raises
        ------
        ValueError
            If interface type is not supported
        """
        if interface_type not in cls._interface_registry:
            available_types = list(cls._interface_registry.keys())
            raise ValueError(
                f"Unsupported interface type: {interface_type}. "
                f"Available types: {available_types}"
            )

        # Get interface class
        interface_class = cls._interface_registry[interface_type]

        # Build configuration
        config = cls._build_interface_config(
            interface_type, name, config_overrides
        )

        # Create and return interface instance
        try:
            return interface_class(config)
        except Exception as e:
            logging.error(f"Failed to create {interface_type} interface: {e}")
            raise

    @classmethod
    def create_udp_interface(
        cls,
        host: str = "localhost",
        port: int = 8080,
        server_mode: bool = False,
        **kwargs
    ) -> Union[UDPInterface, UDPServer, UDPClient]:
        """
        Create UDP interface with simplified configuration.

        Parameters
        ----------
        host : str
            Host address
        port : int
            Port number
        server_mode : bool
            Whether to create server or client interface
        **kwargs
            Additional configuration options

        Returns
        -------
        UDPInterface
            Configured UDP interface
        """
        interface_type = 'udp_server' if server_mode else 'udp_client'
        config_overrides = {
            'endpoint': f"{host}:{port}",
            **kwargs
        }
        return cls.create_interface(interface_type, config_overrides=config_overrides)

    @classmethod
    def create_tcp_interface(
        cls,
        host: str = "localhost",
        port: int = 8080,
        server_mode: bool = False,
        **kwargs
    ) -> Union[TCPInterface, TCPServer, TCPClient]:
        """
        Create TCP interface with simplified configuration.

        Parameters
        ----------
        host : str
            Host address
        port : int
            Port number
        server_mode : bool
            Whether to create server or client interface
        **kwargs
            Additional configuration options

        Returns
        -------
        TCPInterface
            Configured TCP interface
        """
        interface_type = 'tcp_server' if server_mode else 'tcp_client'
        config_overrides = {
            'endpoint': f"{host}:{port}",
            **kwargs
        }
        return cls.create_interface(interface_type, config_overrides=config_overrides)

    @classmethod
    def create_http_interface(
        cls,
        host: str = "localhost",
        port: int = 8080,
        server_mode: bool = False,
        **kwargs
    ) -> Union[HTTPInterface, HTTPServer, HTTPClient]:
        """
        Create HTTP interface with simplified configuration.

        Parameters
        ----------
        host : str
            Host address
        port : int
            Port number
        server_mode : bool
            Whether to create server or client interface
        **kwargs
            Additional configuration options

        Returns
        -------
        HTTPInterface
            Configured HTTP interface
        """
        interface_type = 'http_server' if server_mode else 'http_client'
        config_overrides = {
            'endpoint': f"http://{host}:{port}",
            **kwargs
        }
        return cls.create_interface(interface_type, config_overrides=config_overrides)

    @classmethod
    def create_websocket_interface(
        cls,
        host: str = "localhost",
        port: int = 8080,
        server_mode: bool = False,
        **kwargs
    ) -> Union[WebSocketInterface, WebSocketServer, WebSocketClient]:
        """
        Create WebSocket interface with simplified configuration.

        Parameters
        ----------
        host : str
            Host address
        port : int
            Port number
        server_mode : bool
            Whether to create server or client interface
        **kwargs
            Additional configuration options

        Returns
        -------
        WebSocketInterface
            Configured WebSocket interface
        """
        interface_type = 'ws_server' if server_mode else 'ws_client'
        config_overrides = {
            'endpoint': f"ws://{host}:{port}",
            **kwargs
        }
        return cls.create_interface(interface_type, config_overrides=config_overrides)

    @classmethod
    def create_zeromq_interface(
        cls,
        socket_configs: Optional[list] = None,
        **kwargs
    ) -> ZeroMQInterface:
        """
        Create ZeroMQ interface with socket configuration.

        Parameters
        ----------
        socket_configs : list, optional
            List of socket configurations
        **kwargs
            Additional configuration options

        Returns
        -------
        ZeroMQInterface
            Configured ZeroMQ interface
        """
        config_overrides = kwargs.copy()
        if socket_configs:
            config_overrides['sockets'] = socket_configs

        return cls.create_interface('zeromq', config_overrides=config_overrides)

    @classmethod
    def create_rabbitmq_interface(
        cls,
        url: str = "amqp://guest:guest@localhost/",
        **kwargs
    ) -> RabbitMQInterface:
        """
        Create RabbitMQ interface with connection URL.

        Parameters
        ----------
        url : str
            RabbitMQ connection URL
        **kwargs
            Additional configuration options

        Returns
        -------
        RabbitMQInterface
            Configured RabbitMQ interface
        """
        config_overrides = {
            'url': url,
            **kwargs
        }
        return cls.create_interface('rabbitmq', config_overrides=config_overrides)

    @classmethod
    def create_hil_interface(
        cls,
        controller_endpoint: str = "localhost:8080",
        plant_endpoint: str = "localhost:8081",
        protocol: str = "udp"
    ) -> Dict[str, CommunicationProtocol]:
        """
        Create Hardware-in-the-Loop interface pair.

        Parameters
        ----------
        controller_endpoint : str
            Controller interface endpoint
        plant_endpoint : str
            Plant interface endpoint
        protocol : str
            Communication protocol ('udp', 'tcp')

        Returns
        -------
        Dict[str, CommunicationProtocol]
            Dictionary with 'controller' and 'plant' interfaces
        """
        if protocol not in ['udp', 'tcp']:
            raise ValueError(f"Unsupported HIL protocol: {protocol}")

        # Create controller interface (client)
        controller_config = {
            'endpoint': controller_endpoint,
        }
        controller = cls.create_interface(
            f"{protocol}_client",
            name="hil_controller",
            config_overrides=controller_config
        )

        # Create plant interface (server)
        plant_config = {
            'endpoint': plant_endpoint,
        }
        plant = cls.create_interface(
            f"{protocol}_server",
            name="hil_plant",
            config_overrides=plant_config
        )

        return {
            'controller': controller,
            'plant': plant
        }

    @classmethod
    def register_interface_type(
        cls,
        name: str,
        interface_class: Type[CommunicationProtocol],
        default_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register new interface type with factory.

        Parameters
        ----------
        name : str
            Name for the interface type
        interface_class : Type[CommunicationProtocol]
            Interface class to register
        default_config : Dict[str, Any], optional
            Default configuration for the interface type
        """
        cls._interface_registry[name] = interface_class
        if default_config:
            cls._default_configs[name] = default_config

    @classmethod
    def get_available_types(cls) -> list:
        """
        Get list of available interface types.

        Returns
        -------
        list
            List of registered interface type names
        """
        return list(cls._interface_registry.keys())

    @classmethod
    def get_default_config(cls, interface_type: str) -> Dict[str, Any]:
        """
        Get default configuration for interface type.

        Parameters
        ----------
        interface_type : str
            Interface type name

        Returns
        -------
        Dict[str, Any]
            Default configuration dictionary
        """
        return cls._default_configs.get(interface_type, {}).copy()

    @classmethod
    def _build_interface_config(
        cls,
        interface_type: str,
        name: str,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> InterfaceConfig:
        """
        Build interface configuration from type and overrides.

        Parameters
        ----------
        interface_type : str
            Type of interface
        name : str
            Interface name
        config_overrides : Dict[str, Any], optional
            Configuration overrides

        Returns
        -------
        InterfaceConfig
            Built interface configuration
        """
        # Start with default configuration
        base_config = cls.get_default_config(interface_type)

        # Apply overrides
        if config_overrides:
            base_config.update(config_overrides)

        # Map interface type to InterfaceType enum
        interface_type_mapping = {
            'udp': InterfaceType.UDP,
            'udp_server': InterfaceType.UDP,
            'udp_client': InterfaceType.UDP,
            'tcp': InterfaceType.TCP,
            'tcp_server': InterfaceType.TCP,
            'tcp_client': InterfaceType.TCP,
            'http': InterfaceType.HTTP,
            'http_server': InterfaceType.HTTP,
            'http_client': InterfaceType.HTTP,
            'websocket': InterfaceType.WEBSOCKET,
            'ws_server': InterfaceType.WEBSOCKET,
            'ws_client': InterfaceType.WEBSOCKET,
            'zeromq': InterfaceType.ZEROMQ,
            'rabbitmq': InterfaceType.MQTT,  # Close enough for enum
        }

        # Create InterfaceConfig
        config = InterfaceConfig(
            name=name,
            interface_type=interface_type_mapping.get(interface_type, InterfaceType.TCP),
            description=f"{interface_type} interface",
            endpoint=base_config.get('endpoint', 'localhost:8080'),
            timeout=base_config.get('timeout', 30.0),
            retry_attempts=base_config.get('retry_attempts', 3),
            retry_delay=base_config.get('retry_delay', 1.0),
            keep_alive=base_config.get('keep_alive', True),
            send_buffer_size=base_config.get('send_buffer_size', 8192),
            receive_buffer_size=base_config.get('receive_buffer_size', 8192),
            max_message_size=base_config.get('max_message_size', 1024 * 1024),
            serialization=base_config.get('serialization', 'json'),
            compression=base_config.get('compression'),
            encoding=base_config.get('encoding', 'utf-8'),
            message_ordering=base_config.get('message_ordering', False),
            duplicate_detection=base_config.get('duplicate_detection', False),
            delivery_confirmation=base_config.get('delivery_confirmation', False),
            enable_metrics=base_config.get('enable_metrics', True),
            enable_logging=base_config.get('enable_logging', True),
            log_level=base_config.get('log_level', 'INFO')
        )

        # Set custom settings
        for key, value in base_config.items():
            if key not in [
                'endpoint', 'timeout', 'retry_attempts', 'retry_delay',
                'keep_alive', 'send_buffer_size', 'receive_buffer_size',
                'max_message_size', 'serialization', 'compression',
                'encoding', 'message_ordering', 'duplicate_detection',
                'delivery_confirmation', 'enable_metrics', 'enable_logging',
                'log_level'
            ]:
                config.set_setting(key, value)

        return config


# Convenience functions for common interface creation patterns
def create_control_communication_pair(
    protocol: str = "udp",
    controller_port: int = 8080,
    plant_port: int = 8081,
    host: str = "localhost"
) -> Dict[str, CommunicationProtocol]:
    """
    Create communication interface pair for control applications.

    Parameters
    ----------
    protocol : str
        Communication protocol ('udp', 'tcp', 'websocket')
    controller_port : int
        Port for controller interface
    plant_port : int
        Port for plant interface
    host : str
        Host address

    Returns
    -------
    Dict[str, CommunicationProtocol]
        Dictionary with 'controller' and 'plant' interfaces
    """
    return NetworkInterfaceFactory.create_hil_interface(
        controller_endpoint=f"{host}:{controller_port}",
        plant_endpoint=f"{host}:{plant_port}",
        protocol=protocol
    )


def create_monitoring_interface(
    port: int = 8080,
    host: str = "localhost",
    interface_type: str = "http"
) -> CommunicationProtocol:
    """
    Create monitoring interface for control system observation.

    Parameters
    ----------
    port : int
        Port number
    host : str
        Host address
    interface_type : str
        Type of interface ('http', 'websocket')

    Returns
    -------
    CommunicationProtocol
        Configured monitoring interface
    """
    if interface_type == "http":
        return NetworkInterfaceFactory.create_http_interface(
            host=host, port=port, server_mode=True
        )
    elif interface_type == "websocket":
        return NetworkInterfaceFactory.create_websocket_interface(
            host=host, port=port, server_mode=True
        )
    else:
        raise ValueError(f"Unsupported monitoring interface type: {interface_type}")


def create_distributed_control_mesh(
    nodes: list,
    protocol: str = "zeromq"
) -> Dict[str, CommunicationProtocol]:
    """
    Create mesh of communication interfaces for distributed control.

    Parameters
    ----------
    nodes : list
        List of node configurations
    protocol : str
        Communication protocol ('zeromq', 'rabbitmq')

    Returns
    -------
    Dict[str, CommunicationProtocol]
        Dictionary of node interfaces
    """
    interfaces = {}

    for node_config in nodes:
        node_name = node_config['name']
        if protocol == "zeromq":
            interfaces[node_name] = NetworkInterfaceFactory.create_zeromq_interface(
                socket_configs=node_config.get('sockets', [])
            )
        elif protocol == "rabbitmq":
            interfaces[node_name] = NetworkInterfaceFactory.create_rabbitmq_interface(
                url=node_config.get('url', 'amqp://guest:guest@localhost/')
            )
        else:
            raise ValueError(f"Unsupported distributed protocol: {protocol}")

    return interfaces