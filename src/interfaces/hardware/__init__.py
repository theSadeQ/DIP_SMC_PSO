#==========================================================================================\\\
#=========================== src/interfaces/hardware/__init__.py ========================\\\
#==========================================================================================\\\
"""
Hardware abstraction and device driver framework for control systems.
This module provides comprehensive hardware interface capabilities including
device drivers, sensor/actuator interfaces, data acquisition systems, and
industrial communication protocols for control engineering applications.
"""

from .device_drivers import DeviceDriver, BaseDevice, DeviceManager
from .sensors import SensorInterface, AnalogSensor, DigitalSensor, IMUSensor
from .actuators import ActuatorInterface, ServoActuator, StepperMotor, PneumaticActuator
from .daq_systems import DAQInterface, NIDAQInterface, AdcInterface
from .serial_devices import SerialDevice, ModbusDevice, CANDevice
from .factory import HardwareInterfaceFactory

__all__ = [
    # Core device framework
    'DeviceDriver', 'BaseDevice', 'DeviceManager',

    # Sensor interfaces
    'SensorInterface', 'AnalogSensor', 'DigitalSensor', 'IMUSensor',

    # Actuator interfaces
    'ActuatorInterface', 'ServoActuator', 'StepperMotor', 'PneumaticActuator',

    # Data acquisition
    'DAQInterface', 'NIDAQInterface', 'AdcInterface',

    # Serial communication devices
    'SerialDevice', 'ModbusDevice', 'CANDevice',

    # Factory
    'HardwareInterfaceFactory'
]