#==========================================================================================\\\
#====================== src/interfaces/hardware/factory.py ==============================\\\
#==========================================================================================\\\
"""
Hardware interface factory for creating device drivers.
This module provides factory methods and utilities for creating and
configuring various types of hardware interfaces for control systems,
including sensors, actuators, DAQ systems, and communication devices.
"""

from typing import Dict, Any, Type, Optional, Union, List
import logging

from .device_drivers import DeviceDriver, DeviceConfig, DeviceManager
from .sensors import SensorInterface, AnalogSensor, DigitalSensor, IMUSensor, SensorType
from .actuators import ActuatorInterface, ServoActuator, StepperMotor, PneumaticActuator, ActuatorType
from .daq_systems import DAQInterface, NIDAQInterface, AdcInterface, ChannelConfig, ChannelType
from .serial_devices import SerialDevice, ModbusDevice, CANDevice, SerialProtocol, ModbusRegister, DataType


class HardwareInterfaceFactory:
    """
    Factory for creating hardware device interfaces.

    This factory provides centralized creation and configuration of
    various hardware interface types with consistent configuration
    patterns and error handling.
    """

    # Registry of available device types
    _device_registry: Dict[str, Type[DeviceDriver]] = {
        # Sensors
        'analog_sensor': AnalogSensor,
        'digital_sensor': DigitalSensor,
        'imu_sensor': IMUSensor,

        # Actuators
        'servo_actuator': ServoActuator,
        'stepper_motor': StepperMotor,
        'pneumatic_actuator': PneumaticActuator,

        # DAQ Systems
        'nidaq': NIDAQInterface,
        'adc': AdcInterface,

        # Serial Devices
        'modbus_device': ModbusDevice,
        'can_device': CANDevice,
    }

    # Default configurations for device types
    _default_configs: Dict[str, Dict[str, Any]] = {
        'analog_sensor': {
            'connection_params': {},
            'operational_params': {
                'adc_resolution': 12,
                'reference_voltage': 5.0,
                'measurement_range': (0.0, 5.0),
                'channel_count': 4,
                'noise_filter_enabled': True,
                'filter_window_size': 5
            },
            'calibration_params': {},
            'safety_limits': {},
            'update_rate': 100.0,
            'timeout': 1.0
        },
        'digital_sensor': {
            'connection_params': {},
            'operational_params': {
                'pin_count': 8,
                'debounce_time': 0.05
            },
            'calibration_params': {},
            'safety_limits': {},
            'update_rate': 100.0,
            'timeout': 1.0
        },
        'imu_sensor': {
            'connection_params': {},
            'operational_params': {
                'accelerometer_range': 16,
                'gyroscope_range': 2000,
                'magnetometer_enabled': True,
                'sensor_fusion_enabled': True
            },
            'calibration_params': {},
            'safety_limits': {},
            'update_rate': 100.0,
            'timeout': 1.0
        },
        'servo_actuator': {
            'connection_params': {},
            'operational_params': {
                'encoder_resolution': 4096,
                'gear_ratio': 1.0,
                'max_rpm': 3000,
                'pid_gains': {'kp': 1.0, 'ki': 0.1, 'kd': 0.01},
                'limits': {
                    'min_position': -360.0,
                    'max_position': 360.0,
                    'max_velocity': 1800.0,
                    'max_force': 10.0
                },
                'position_tolerance': 0.1,
                'safety_enabled': True
            },
            'calibration_params': {},
            'safety_limits': {},
            'update_rate': 100.0,
            'timeout': 1.0
        },
        'stepper_motor': {
            'connection_params': {},
            'operational_params': {
                'steps_per_revolution': 200,
                'microstep_resolution': 16
            },
            'calibration_params': {},
            'safety_limits': {},
            'update_rate': 50.0,
            'timeout': 1.0
        },
        'pneumatic_actuator': {
            'connection_params': {},
            'operational_params': {
                'max_pressure': 6.0,
                'cylinder_diameter': 50.0,
                'stroke_length': 100.0
            },
            'calibration_params': {},
            'safety_limits': {},
            'update_rate': 10.0,
            'timeout': 1.0
        },
        'nidaq': {
            'connection_params': {
                'device_name': 'Dev1'
            },
            'operational_params': {
                'sample_rate': 1000.0,
                'buffer_size': 10000
            },
            'calibration_params': {},
            'safety_limits': {},
            'update_rate': 0.0,  # Continuous acquisition
            'timeout': 1.0
        },
        'adc': {
            'connection_params': {},
            'operational_params': {
                'resolution': 12,
                'reference_voltage': 3.3,
                'channel_count': 8,
                'sample_rate': 1000.0,
                'buffer_size': 10000
            },
            'calibration_params': {},
            'safety_limits': {},
            'update_rate': 0.0,
            'timeout': 1.0
        },
        'modbus_device': {
            'connection_params': {
                'port': '/dev/ttyUSB0',
                'baudrate': 9600,
                'bytesize': 8,
                'parity': 'N',
                'stopbits': 1,
                'timeout': 1.0,
                'protocol': 'modbus_rtu'
            },
            'operational_params': {
                'unit_id': 1
            },
            'calibration_params': {},
            'safety_limits': {},
            'update_rate': 10.0,
            'timeout': 1.0
        },
        'can_device': {
            'connection_params': {
                'interface': 'socketcan',
                'channel': 'can0',
                'bitrate': 500000
            },
            'operational_params': {},
            'calibration_params': {},
            'safety_limits': {},
            'update_rate': 0.0,
            'timeout': 1.0
        }
    }

    @classmethod
    def create_device(
        cls,
        device_type: str,
        device_id: str,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> DeviceDriver:
        """
        Create hardware device of specified type.

        Parameters
        ----------
        device_type : str
            Type of device to create
        device_id : str
            Unique identifier for the device
        config_overrides : Dict[str, Any], optional
            Configuration overrides

        Returns
        -------
        DeviceDriver
            Configured device instance

        Raises
        ------
        ValueError
            If device type is not supported
        """
        if device_type not in cls._device_registry:
            available_types = list(cls._device_registry.keys())
            raise ValueError(
                f"Unsupported device type: {device_type}. "
                f"Available types: {available_types}"
            )

        # Get device class
        device_class = cls._device_registry[device_type]

        # Build configuration
        config = cls._build_device_config(device_type, device_id, config_overrides)

        # Create and return device instance
        try:
            return device_class(config)
        except Exception as e:
            logging.error(f"Failed to create {device_type} device: {e}")
            raise

    @classmethod
    def create_sensor(
        cls,
        sensor_type: str,
        device_id: str,
        **kwargs
    ) -> SensorInterface:
        """
        Create sensor with simplified configuration.

        Parameters
        ----------
        sensor_type : str
            Type of sensor ('analog', 'digital', 'imu')
        device_id : str
            Device identifier
        **kwargs
            Additional configuration options

        Returns
        -------
        SensorInterface
            Configured sensor instance
        """
        device_type = f"{sensor_type}_sensor"
        return cls.create_device(device_type, device_id, kwargs)

    @classmethod
    def create_actuator(
        cls,
        actuator_type: str,
        device_id: str,
        **kwargs
    ) -> ActuatorInterface:
        """
        Create actuator with simplified configuration.

        Parameters
        ----------
        actuator_type : str
            Type of actuator ('servo', 'stepper', 'pneumatic')
        device_id : str
            Device identifier
        **kwargs
            Additional configuration options

        Returns
        -------
        ActuatorInterface
            Configured actuator instance
        """
        if actuator_type == "servo":
            device_type = "servo_actuator"
        elif actuator_type == "stepper":
            device_type = "stepper_motor"
        elif actuator_type == "pneumatic":
            device_type = "pneumatic_actuator"
        else:
            raise ValueError(f"Unknown actuator type: {actuator_type}")

        return cls.create_device(device_type, device_id, kwargs)

    @classmethod
    def create_daq_system(
        cls,
        daq_type: str,
        device_id: str,
        channels: Optional[List[ChannelConfig]] = None,
        **kwargs
    ) -> DAQInterface:
        """
        Create DAQ system with channel configuration.

        Parameters
        ----------
        daq_type : str
            Type of DAQ system ('nidaq', 'adc')
        device_id : str
            Device identifier
        channels : List[ChannelConfig], optional
            Channel configurations
        **kwargs
            Additional configuration options

        Returns
        -------
        DAQInterface
            Configured DAQ system
        """
        daq = cls.create_device(daq_type, device_id, kwargs)

        # Add channels if provided
        if channels:
            for channel_config in channels:
                asyncio.create_task(daq.add_channel(channel_config))

        return daq

    @classmethod
    def create_modbus_device(
        cls,
        device_id: str,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
        registers: Optional[List[ModbusRegister]] = None,
        **kwargs
    ) -> ModbusDevice:
        """
        Create Modbus device with register configuration.

        Parameters
        ----------
        device_id : str
            Device identifier
        port : str
            Serial port
        baudrate : int
            Baud rate
        registers : List[ModbusRegister], optional
            Modbus register configurations
        **kwargs
            Additional configuration options

        Returns
        -------
        ModbusDevice
            Configured Modbus device
        """
        config_overrides = {
            'connection_params': {
                'port': port,
                'baudrate': baudrate,
                **kwargs.get('connection_params', {})
            },
            **{k: v for k, v in kwargs.items() if k != 'connection_params'}
        }

        device = cls.create_device('modbus_device', device_id, config_overrides)

        # Add registers if provided
        if registers:
            for register in registers:
                asyncio.create_task(device.add_register(register))

        return device

    @classmethod
    def create_can_device(
        cls,
        device_id: str,
        channel: str = "can0",
        bitrate: int = 500000,
        interface: str = "socketcan",
        **kwargs
    ) -> CANDevice:
        """
        Create CAN device with simplified configuration.

        Parameters
        ----------
        device_id : str
            Device identifier
        channel : str
            CAN channel
        bitrate : int
            CAN bitrate
        interface : str
            CAN interface type
        **kwargs
            Additional configuration options

        Returns
        -------
        CANDevice
            Configured CAN device
        """
        config_overrides = {
            'connection_params': {
                'channel': channel,
                'bitrate': bitrate,
                'interface': interface,
                **kwargs.get('connection_params', {})
            },
            **{k: v for k, v in kwargs.items() if k != 'connection_params'}
        }

        return cls.create_device('can_device', device_id, config_overrides)

    @classmethod
    def create_device_manager(cls, devices: Optional[List[DeviceDriver]] = None) -> DeviceManager:
        """
        Create device manager with optional initial devices.

        Parameters
        ----------
        devices : List[DeviceDriver], optional
            Initial devices to add to manager

        Returns
        -------
        DeviceManager
            Configured device manager
        """
        manager = DeviceManager()

        if devices:
            for device in devices:
                manager.add_device(device)

        return manager

    @classmethod
    def create_control_system(
        cls,
        sensors: List[Dict[str, Any]],
        actuators: List[Dict[str, Any]],
        daq_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, DeviceDriver]:
        """
        Create complete control system with sensors, actuators, and DAQ.

        Parameters
        ----------
        sensors : List[Dict[str, Any]]
            Sensor configurations
        actuators : List[Dict[str, Any]]
            Actuator configurations
        daq_config : Dict[str, Any], optional
            DAQ system configuration

        Returns
        -------
        Dict[str, DeviceDriver]
            Dictionary of created devices
        """
        devices = {}

        # Create sensors
        for sensor_config in sensors:
            device_id = sensor_config['device_id']
            sensor_type = sensor_config['type']
            config = sensor_config.get('config', {})
            devices[device_id] = cls.create_sensor(sensor_type, device_id, **config)

        # Create actuators
        for actuator_config in actuators:
            device_id = actuator_config['device_id']
            actuator_type = actuator_config['type']
            config = actuator_config.get('config', {})
            devices[device_id] = cls.create_actuator(actuator_type, device_id, **config)

        # Create DAQ system if configured
        if daq_config:
            device_id = daq_config['device_id']
            daq_type = daq_config['type']
            channels = daq_config.get('channels', [])
            config = daq_config.get('config', {})
            devices[device_id] = cls.create_daq_system(daq_type, device_id, channels, **config)

        return devices

    @classmethod
    def register_device_type(
        cls,
        name: str,
        device_class: Type[DeviceDriver],
        default_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register new device type with factory.

        Parameters
        ----------
        name : str
            Name for the device type
        device_class : Type[DeviceDriver]
            Device class to register
        default_config : Dict[str, Any], optional
            Default configuration for the device type
        """
        cls._device_registry[name] = device_class
        if default_config:
            cls._default_configs[name] = default_config

    @classmethod
    def get_available_types(cls) -> List[str]:
        """
        Get list of available device types.

        Returns
        -------
        List[str]
            List of registered device type names
        """
        return list(cls._device_registry.keys())

    @classmethod
    def get_default_config(cls, device_type: str) -> Dict[str, Any]:
        """
        Get default configuration for device type.

        Parameters
        ----------
        device_type : str
            Device type name

        Returns
        -------
        Dict[str, Any]
            Default configuration dictionary
        """
        return cls._default_configs.get(device_type, {}).copy()

    @classmethod
    def _build_device_config(
        cls,
        device_type: str,
        device_id: str,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> DeviceConfig:
        """
        Build device configuration from type and overrides.

        Parameters
        ----------
        device_type : str
            Type of device
        device_id : str
            Device identifier
        config_overrides : Dict[str, Any], optional
            Configuration overrides

        Returns
        -------
        DeviceConfig
            Built device configuration
        """
        # Start with default configuration
        base_config = cls.get_default_config(device_type)

        # Apply overrides
        if config_overrides:
            # Deep merge configuration sections
            for section in ['connection_params', 'operational_params', 'calibration_params', 'safety_limits']:
                if section in config_overrides:
                    if section not in base_config:
                        base_config[section] = {}
                    base_config[section].update(config_overrides[section])

            # Update top-level parameters
            for key, value in config_overrides.items():
                if key not in ['connection_params', 'operational_params', 'calibration_params', 'safety_limits']:
                    base_config[key] = value

        # Create DeviceConfig
        config = DeviceConfig(
            device_id=device_id,
            device_type=device_type,
            connection_params=base_config.get('connection_params', {}),
            operational_params=base_config.get('operational_params', {}),
            calibration_params=base_config.get('calibration_params', {}),
            safety_limits=base_config.get('safety_limits', {}),
            update_rate=base_config.get('update_rate', 10.0),
            timeout=base_config.get('timeout', 1.0),
            retry_attempts=base_config.get('retry_attempts', 3),
            enable_logging=base_config.get('enable_logging', True)
        )

        return config


# Convenience functions for common device creation patterns
def create_sensor_array(
    sensor_type: str,
    count: int,
    base_id: str = "sensor",
    **kwargs
) -> List[SensorInterface]:
    """
    Create array of sensors of the same type.

    Parameters
    ----------
    sensor_type : str
        Type of sensor
    count : int
        Number of sensors to create
    base_id : str
        Base identifier for sensors
    **kwargs
        Configuration for all sensors

    Returns
    -------
    List[SensorInterface]
        List of created sensors
    """
    sensors = []
    for i in range(count):
        device_id = f"{base_id}_{i}"
        sensor = HardwareInterfaceFactory.create_sensor(sensor_type, device_id, **kwargs)
        sensors.append(sensor)
    return sensors


def create_actuator_array(
    actuator_type: str,
    count: int,
    base_id: str = "actuator",
    **kwargs
) -> List[ActuatorInterface]:
    """
    Create array of actuators of the same type.

    Parameters
    ----------
    actuator_type : str
        Type of actuator
    count : int
        Number of actuators to create
    base_id : str
        Base identifier for actuators
    **kwargs
        Configuration for all actuators

    Returns
    -------
    List[ActuatorInterface]
        List of created actuators
    """
    actuators = []
    for i in range(count):
        device_id = f"{base_id}_{i}"
        actuator = HardwareInterfaceFactory.create_actuator(actuator_type, device_id, **kwargs)
        actuators.append(actuator)
    return actuators


def create_multi_axis_system(
    axes: List[Dict[str, Any]],
    sensors_per_axis: int = 1,
    actuators_per_axis: int = 1
) -> Dict[str, List[DeviceDriver]]:
    """
    Create multi-axis control system.

    Parameters
    ----------
    axes : List[Dict[str, Any]]
        Axis configurations
    sensors_per_axis : int
        Number of sensors per axis
    actuators_per_axis : int
        Number of actuators per axis

    Returns
    -------
    Dict[str, List[DeviceDriver]]
        Dictionary of axis devices
    """
    system = {}

    for axis_config in axes:
        axis_name = axis_config['name']
        sensor_type = axis_config.get('sensor_type', 'analog')
        actuator_type = axis_config.get('actuator_type', 'servo')

        # Create sensors for axis
        sensors = create_sensor_array(
            sensor_type,
            sensors_per_axis,
            f"{axis_name}_sensor",
            **axis_config.get('sensor_config', {})
        )

        # Create actuators for axis
        actuators = create_actuator_array(
            actuator_type,
            actuators_per_axis,
            f"{axis_name}_actuator",
            **axis_config.get('actuator_config', {})
        )

        system[axis_name] = {
            'sensors': sensors,
            'actuators': actuators
        }

    return system


def create_distributed_io_system(
    modbus_devices: List[Dict[str, Any]],
    can_devices: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, DeviceDriver]:
    """
    Create distributed I/O system with Modbus and CAN devices.

    Parameters
    ----------
    modbus_devices : List[Dict[str, Any]]
        Modbus device configurations
    can_devices : List[Dict[str, Any]], optional
        CAN device configurations

    Returns
    -------
    Dict[str, DeviceDriver]
        Dictionary of communication devices
    """
    devices = {}

    # Create Modbus devices
    for device_config in modbus_devices:
        device_id = device_config['device_id']
        port = device_config.get('port', '/dev/ttyUSB0')
        baudrate = device_config.get('baudrate', 9600)
        registers = device_config.get('registers', [])
        config = device_config.get('config', {})

        devices[device_id] = HardwareInterfaceFactory.create_modbus_device(
            device_id, port, baudrate, registers, **config
        )

    # Create CAN devices
    if can_devices:
        for device_config in can_devices:
            device_id = device_config['device_id']
            channel = device_config.get('channel', 'can0')
            bitrate = device_config.get('bitrate', 500000)
            config = device_config.get('config', {})

            devices[device_id] = HardwareInterfaceFactory.create_can_device(
                device_id, channel, bitrate, **config
            )

    return devices