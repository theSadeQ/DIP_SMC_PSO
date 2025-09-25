#==========================================================================================\\\
#==================== src/interfaces/hardware/serial_devices.py =======================\\\
#==========================================================================================\\\
"""
Serial communication device interfaces for control systems.
This module provides standardized interfaces for serial communication
protocols including RS232/485, Modbus RTU/TCP, CAN bus, and other
industrial communication standards commonly used in control systems.
"""

import asyncio
import serial
import struct
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple, Union
from enum import Enum
import logging

from .device_drivers import DeviceDriver, DeviceConfig, DeviceCapability, DeviceState

try:
    import serial_asyncio
    SERIAL_ASYNCIO_AVAILABLE = True
except ImportError:
    SERIAL_ASYNCIO_AVAILABLE = False

try:
    from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient
    from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
    from pymodbus.constants import Endian
    PYMODBUS_AVAILABLE = True
except ImportError:
    PYMODBUS_AVAILABLE = False

try:
    import can
    CAN_AVAILABLE = True
except ImportError:
    CAN_AVAILABLE = False


class SerialProtocol(Enum):
    """Serial communication protocol enumeration."""
    RS232 = "rs232"
    RS485 = "rs485"
    MODBUS_RTU = "modbus_rtu"
    MODBUS_TCP = "modbus_tcp"
    CAN = "can"
    PROFIBUS = "profibus"
    DEVICENET = "devicenet"


class DataType(Enum):
    """Data type enumeration for serial communication."""
    UINT16 = "uint16"
    INT16 = "int16"
    UINT32 = "uint32"
    INT32 = "int32"
    FLOAT32 = "float32"
    BOOL = "bool"
    STRING = "string"


@dataclass
class SerialConfig:
    """Serial communication configuration."""
    port: str
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = 'N'  # N, E, O
    stopbits: int = 1
    timeout: float = 1.0
    protocol: SerialProtocol = SerialProtocol.RS232


@dataclass
class ModbusRegister:
    """Modbus register configuration."""
    name: str
    address: int
    data_type: DataType
    function_code: int  # 1, 2, 3, 4
    unit_id: int = 1
    count: int = 1
    scaling: float = 1.0
    offset: float = 0.0
    unit: str = ""
    read_only: bool = True


@dataclass
class CANMessage:
    """CAN message structure."""
    timestamp: float
    arbitration_id: int
    data: bytes
    is_extended: bool = False
    is_remote: bool = False
    channel: Optional[str] = None


class SerialDevice(DeviceDriver, ABC):
    """
    Abstract base class for serial communication devices.

    This class provides common functionality for serial communication
    including connection management, message framing, and error handling.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize serial device."""
        super().__init__(config)
        self._serial_config = SerialConfig(**config.connection_params)
        self._serial_port: Optional[serial.Serial] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._message_handlers: List[callable] = []

    @property
    def is_connected(self) -> bool:
        """Check if serial device is connected."""
        return self._serial_port is not None and self._serial_port.is_open

    @abstractmethod
    async def send_message(self, data: bytes) -> bool:
        """
        Send message over serial interface.

        Parameters
        ----------
        data : bytes
            Message data to send

        Returns
        -------
        bool
            True if send successful
        """
        pass

    @abstractmethod
    async def receive_message(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """
        Receive message from serial interface.

        Parameters
        ----------
        timeout : float, optional
            Receive timeout

        Returns
        -------
        bytes or None
            Received message data
        """
        pass

    async def connect_serial(self) -> bool:
        """Connect to serial device."""
        try:
            if SERIAL_ASYNCIO_AVAILABLE:
                # Use asyncio serial for better performance
                reader, writer = await serial_asyncio.open_serial_connection(
                    url=self._serial_config.port,
                    baudrate=self._serial_config.baudrate,
                    bytesize=self._serial_config.bytesize,
                    parity=self._serial_config.parity,
                    stopbits=self._serial_config.stopbits,
                    timeout=self._serial_config.timeout
                )
                self._reader = reader
                self._writer = writer
            else:
                # Fallback to synchronous serial
                self._serial_port = serial.Serial(
                    port=self._serial_config.port,
                    baudrate=self._serial_config.baudrate,
                    bytesize=self._serial_config.bytesize,
                    parity=self._serial_config.parity,
                    stopbits=self._serial_config.stopbits,
                    timeout=self._serial_config.timeout
                )

            self._logger.info(f"Connected to serial device on {self._serial_config.port}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to connect to serial device: {e}")
            return False

    async def disconnect_serial(self) -> bool:
        """Disconnect from serial device."""
        try:
            if self._receive_task:
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass

            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
                self._writer = None
                self._reader = None

            if self._serial_port and self._serial_port.is_open:
                self._serial_port.close()
                self._serial_port = None

            self._logger.info("Disconnected from serial device")
            return True

        except Exception as e:
            self._logger.error(f"Error disconnecting from serial device: {e}")
            return False

    def add_message_handler(self, handler: callable) -> None:
        """Add message handler for received data."""
        self._message_handlers.append(handler)

    async def _receive_loop(self) -> None:
        """Continuous receive loop."""
        try:
            while self.is_connected:
                try:
                    message = await self.receive_message(timeout=1.0)
                    if message:
                        # Call message handlers
                        for handler in self._message_handlers:
                            try:
                                if asyncio.iscoroutinefunction(handler):
                                    await handler(message)
                                else:
                                    handler(message)
                            except Exception as e:
                                self._logger.error(f"Error in message handler: {e}")

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    self._logger.error(f"Error in receive loop: {e}")
                    break

        except asyncio.CancelledError:
            pass


class ModbusDevice(SerialDevice):
    """
    Modbus RTU/TCP device implementation.

    Provides Modbus communication for reading and writing
    holding registers, input registers, coils, and discrete inputs.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize Modbus device."""
        if not PYMODBUS_AVAILABLE:
            raise ImportError("pymodbus not available. Install with: pip install pymodbus")

        super().__init__(config)
        self._modbus_client: Optional[Union[ModbusSerialClient, ModbusTcpClient]] = None
        self._registers: Dict[str, ModbusRegister] = {}
        self._default_unit_id = config.operational_params.get('unit_id', 1)
        self._tcp_host = config.connection_params.get('tcp_host', 'localhost')
        self._tcp_port = config.connection_params.get('tcp_port', 502)

    async def initialize(self) -> bool:
        """Initialize Modbus device."""
        self._logger.info(f"Initializing Modbus device {self.device_id}")

        try:
            if self._serial_config.protocol == SerialProtocol.MODBUS_RTU:
                self._modbus_client = ModbusSerialClient(
                    method='rtu',
                    port=self._serial_config.port,
                    baudrate=self._serial_config.baudrate,
                    bytesize=self._serial_config.bytesize,
                    parity=self._serial_config.parity,
                    stopbits=self._serial_config.stopbits,
                    timeout=self._serial_config.timeout
                )
            elif self._serial_config.protocol == SerialProtocol.MODBUS_TCP:
                self._modbus_client = ModbusTcpClient(
                    host=self._tcp_host,
                    port=self._tcp_port,
                    timeout=self._serial_config.timeout
                )
            else:
                raise ValueError(f"Unsupported protocol: {self._serial_config.protocol}")

            # Connect to Modbus device
            if self._modbus_client.connect():
                self._logger.info("Connected to Modbus device")
                return True
            else:
                self._logger.error("Failed to connect to Modbus device")
                return False

        except Exception as e:
            self._logger.error(f"Failed to initialize Modbus device: {e}")
            return False

    async def shutdown(self) -> bool:
        """Shutdown Modbus device."""
        try:
            if self._modbus_client:
                self._modbus_client.close()
                self._modbus_client = None
            return True
        except Exception as e:
            self._logger.error(f"Error shutting down Modbus device: {e}")
            return False

    async def read_data(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """Read data from Modbus device."""
        if channel:
            if channel in self._registers:
                value = await self.read_register(channel)
                return {channel: value}
            return {}
        else:
            # Read all registers
            data = {}
            for reg_name in self._registers:
                try:
                    value = await self.read_register(reg_name)
                    data[reg_name] = value
                except Exception as e:
                    self._logger.warning(f"Failed to read register {reg_name}: {e}")
            return data

    async def write_data(self, data: Dict[str, Any]) -> bool:
        """Write data to Modbus device."""
        try:
            for reg_name, value in data.items():
                if reg_name in self._registers:
                    await self.write_register(reg_name, value)
            return True
        except Exception as e:
            self._logger.error(f"Failed to write Modbus data: {e}")
            return False

    async def self_test(self) -> Dict[str, Any]:
        """Perform Modbus device self-test."""
        test_results = await super().self_test()

        try:
            # Test connection
            if self._modbus_client and self._modbus_client.socket:
                test_results['connection_active'] = True

                # Test read capability
                if self._registers:
                    test_reg = list(self._registers.keys())[0]
                    value = await self.read_register(test_reg)
                    test_results['read_functional'] = value is not None
                else:
                    test_results['read_functional'] = True

            else:
                test_results['connection_active'] = False
                test_results['overall_status'] = 'FAIL'

        except Exception as e:
            test_results['modbus_error'] = str(e)
            test_results['overall_status'] = 'FAIL'

        return test_results

    async def send_message(self, data: bytes) -> bool:
        """Send raw Modbus message."""
        # For Modbus, typically use higher-level read/write methods
        self._logger.warning("Use read_register/write_register for Modbus communication")
        return False

    async def receive_message(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """Receive raw Modbus message."""
        # For Modbus, typically use higher-level read/write methods
        return None

    async def add_register(self, register: ModbusRegister) -> bool:
        """Add Modbus register configuration."""
        try:
            self._registers[register.name] = register

            # Add capability
            capability = DeviceCapability(
                name=register.name,
                description=f"Modbus register at address {register.address}",
                data_type=register.data_type.value,
                unit=register.unit,
                read_only=register.read_only
            )
            self.add_capability(capability)

            self._logger.info(f"Added Modbus register {register.name}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to add register {register.name}: {e}")
            return False

    async def read_register(self, register_name: str) -> Optional[Union[float, int, bool]]:
        """Read value from Modbus register."""
        try:
            if register_name not in self._registers:
                raise ValueError(f"Register {register_name} not configured")

            register = self._registers[register_name]

            # Read based on function code
            if register.function_code == 1:  # Read Coils
                result = self._modbus_client.read_coils(
                    register.address, register.count, unit=register.unit_id
                )
                if result.isError():
                    raise Exception(f"Modbus error: {result}")
                return result.bits[0] if register.count == 1 else result.bits

            elif register.function_code == 2:  # Read Discrete Inputs
                result = self._modbus_client.read_discrete_inputs(
                    register.address, register.count, unit=register.unit_id
                )
                if result.isError():
                    raise Exception(f"Modbus error: {result}")
                return result.bits[0] if register.count == 1 else result.bits

            elif register.function_code == 3:  # Read Holding Registers
                result = self._modbus_client.read_holding_registers(
                    register.address, register.count, unit=register.unit_id
                )
                if result.isError():
                    raise Exception(f"Modbus error: {result}")

                # Decode based on data type
                decoder = BinaryPayloadDecoder.fromRegisters(
                    result.registers, byteorder=Endian.Big
                )
                return self._decode_value(decoder, register.data_type, register.scaling, register.offset)

            elif register.function_code == 4:  # Read Input Registers
                result = self._modbus_client.read_input_registers(
                    register.address, register.count, unit=register.unit_id
                )
                if result.isError():
                    raise Exception(f"Modbus error: {result}")

                decoder = BinaryPayloadDecoder.fromRegisters(
                    result.registers, byteorder=Endian.Big
                )
                return self._decode_value(decoder, register.data_type, register.scaling, register.offset)

            else:
                raise ValueError(f"Unsupported function code: {register.function_code}")

        except Exception as e:
            self._logger.error(f"Failed to read register {register_name}: {e}")
            return None

    async def write_register(self, register_name: str, value: Union[float, int, bool]) -> bool:
        """Write value to Modbus register."""
        try:
            if register_name not in self._registers:
                raise ValueError(f"Register {register_name} not configured")

            register = self._registers[register_name]

            if register.read_only:
                raise ValueError(f"Register {register_name} is read-only")

            # Apply inverse scaling
            scaled_value = (value - register.offset) / register.scaling

            # Write based on function code
            if register.function_code == 1:  # Write Coil
                result = self._modbus_client.write_coil(
                    register.address, bool(value), unit=register.unit_id
                )
                return not result.isError()

            elif register.function_code == 3:  # Write Holding Register
                # Encode based on data type
                builder = BinaryPayloadBuilder(byteorder=Endian.Big)
                self._encode_value(builder, register.data_type, scaled_value)

                result = self._modbus_client.write_registers(
                    register.address, builder.to_registers(), unit=register.unit_id
                )
                return not result.isError()

            else:
                raise ValueError(f"Cannot write to function code {register.function_code}")

        except Exception as e:
            self._logger.error(f"Failed to write register {register_name}: {e}")
            return False

    def _decode_value(self, decoder: BinaryPayloadDecoder, data_type: DataType, scaling: float, offset: float) -> Union[float, int, bool]:
        """Decode value from Modbus registers."""
        if data_type == DataType.UINT16:
            raw_value = decoder.decode_16bit_uint()
        elif data_type == DataType.INT16:
            raw_value = decoder.decode_16bit_int()
        elif data_type == DataType.UINT32:
            raw_value = decoder.decode_32bit_uint()
        elif data_type == DataType.INT32:
            raw_value = decoder.decode_32bit_int()
        elif data_type == DataType.FLOAT32:
            raw_value = decoder.decode_32bit_float()
        elif data_type == DataType.BOOL:
            raw_value = bool(decoder.decode_16bit_uint())
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

        return raw_value * scaling + offset

    def _encode_value(self, builder: BinaryPayloadBuilder, data_type: DataType, value: Union[float, int, bool]) -> None:
        """Encode value to Modbus registers."""
        if data_type == DataType.UINT16:
            builder.add_16bit_uint(int(value))
        elif data_type == DataType.INT16:
            builder.add_16bit_int(int(value))
        elif data_type == DataType.UINT32:
            builder.add_32bit_uint(int(value))
        elif data_type == DataType.INT32:
            builder.add_32bit_int(int(value))
        elif data_type == DataType.FLOAT32:
            builder.add_32bit_float(float(value))
        elif data_type == DataType.BOOL:
            builder.add_16bit_uint(1 if value else 0)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")


class CANDevice(SerialDevice):
    """
    CAN bus device implementation.

    Provides CAN bus communication for sending and receiving
    CAN messages with configurable filters and arbitration IDs.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize CAN device."""
        if not CAN_AVAILABLE:
            raise ImportError("python-can not available. Install with: pip install python-can")

        super().__init__(config)
        self._can_bus: Optional[can.BusABC] = None
        self._interface = config.connection_params.get('interface', 'socketcan')
        self._channel = config.connection_params.get('channel', 'can0')
        self._bitrate = config.connection_params.get('bitrate', 500000)
        self._message_filters: List[Dict[str, Any]] = []
        self._notifier: Optional[can.Notifier] = None

    async def initialize(self) -> bool:
        """Initialize CAN device."""
        self._logger.info(f"Initializing CAN device {self.device_id}")

        try:
            # Create CAN bus
            self._can_bus = can.interface.Bus(
                channel=self._channel,
                interface=self._interface,
                bitrate=self._bitrate
            )

            # Set up message notifier
            self._notifier = can.Notifier(self._can_bus, [self._can_message_handler])

            self._logger.info(f"CAN device initialized on {self._channel}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to initialize CAN device: {e}")
            return False

    async def shutdown(self) -> bool:
        """Shutdown CAN device."""
        try:
            if self._notifier:
                self._notifier.stop()
                self._notifier = None

            if self._can_bus:
                self._can_bus.shutdown()
                self._can_bus = None

            return True

        except Exception as e:
            self._logger.error(f"Error shutting down CAN device: {e}")
            return False

    async def read_data(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """Read data from CAN device."""
        # CAN is message-based, use message handlers instead
        return {"status": "use_message_handlers"}

    async def write_data(self, data: Dict[str, Any]) -> bool:
        """Write data to CAN device."""
        try:
            if "message" in data:
                message_data = data["message"]
                arbitration_id = message_data.get("id", 0x123)
                payload = message_data.get("data", b"")
                is_extended = message_data.get("extended", False)

                return await self.send_can_message(arbitration_id, payload, is_extended)

            return True

        except Exception as e:
            self._logger.error(f"Failed to write CAN data: {e}")
            return False

    async def self_test(self) -> Dict[str, Any]:
        """Perform CAN device self-test."""
        test_results = await super().self_test()

        try:
            # Test CAN bus connectivity
            if self._can_bus:
                test_results['can_bus_active'] = True

                # Send test message
                test_message = can.Message(
                    arbitration_id=0x123,
                    data=[0x01, 0x02, 0x03, 0x04],
                    is_extended_id=False
                )

                try:
                    self._can_bus.send(test_message)
                    test_results['can_send_functional'] = True
                except Exception:
                    test_results['can_send_functional'] = False

            else:
                test_results['can_bus_active'] = False
                test_results['overall_status'] = 'FAIL'

        except Exception as e:
            test_results['can_error'] = str(e)
            test_results['overall_status'] = 'FAIL'

        return test_results

    async def send_message(self, data: bytes) -> bool:
        """Send raw CAN message."""
        # Use send_can_message for proper CAN communication
        return await self.send_can_message(0x123, data)

    async def receive_message(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """Receive raw CAN message."""
        try:
            if self._can_bus:
                message = self._can_bus.recv(timeout=timeout)
                if message:
                    return message.data
            return None
        except Exception as e:
            self._logger.error(f"Error receiving CAN message: {e}")
            return None

    async def send_can_message(self, arbitration_id: int, data: bytes, is_extended: bool = False) -> bool:
        """Send CAN message with specific arbitration ID."""
        try:
            if not self._can_bus:
                raise Exception("CAN bus not initialized")

            message = can.Message(
                arbitration_id=arbitration_id,
                data=data,
                is_extended_id=is_extended
            )

            self._can_bus.send(message)
            self._logger.debug(f"Sent CAN message ID=0x{arbitration_id:X}, data={data.hex()}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to send CAN message: {e}")
            return False

    def add_message_filter(self, arbitration_id: int, mask: int = 0x7FF) -> None:
        """Add CAN message filter."""
        self._message_filters.append({
            'can_id': arbitration_id,
            'can_mask': mask
        })

    def _can_message_handler(self, message: can.Message) -> None:
        """Handle received CAN messages."""
        try:
            can_message = CANMessage(
                timestamp=message.timestamp,
                arbitration_id=message.arbitration_id,
                data=message.data,
                is_extended=message.is_extended_id,
                is_remote=message.is_remote_frame,
                channel=self._channel
            )

            # Call registered message handlers
            for handler in self._message_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(can_message))
                    else:
                        handler(can_message)
                except Exception as e:
                    self._logger.error(f"Error in CAN message handler: {e}")

        except Exception as e:
            self._logger.error(f"Error processing CAN message: {e}")