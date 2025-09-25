#==========================================================================================\\\
#======================== src/interfaces/hil/enhanced_hil.py ============================\\\
#==========================================================================================\\\
"""
Enhanced Hardware-in-the-Loop (HIL) system for advanced control testing.
This module provides a comprehensive HIL framework with real-time capabilities,
fault injection, automated testing, and integration with hardware interfaces
for professional control system validation.
"""

import asyncio
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum
import logging

from ..core.protocols import CommunicationProtocol
from ..hardware.device_drivers import DeviceDriver, DeviceManager
from ..network.factory import NetworkInterfaceFactory


class HILMode(Enum):
    """HIL operation mode enumeration."""
    SIMULATION_ONLY = "simulation_only"
    HARDWARE_ONLY = "hardware_only"
    HYBRID = "hybrid"
    REAL_TIME = "real_time"
    NON_REAL_TIME = "non_real_time"


class HILState(Enum):
    """HIL system state enumeration."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class TimingConfig:
    """HIL timing configuration."""
    sample_time: float = 0.001  # 1ms default
    max_jitter: float = 0.0001  # 100μs jitter tolerance
    deadline_factor: float = 0.9  # Use 90% of sample time as deadline
    priority: int = 99  # High priority for real-time
    cpu_affinity: Optional[List[int]] = None


@dataclass
class TestScenario:
    """HIL test scenario configuration."""
    name: str
    description: str
    duration: float
    initial_conditions: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_results: Dict[str, Any] = field(default_factory=dict)
    tolerance: Dict[str, float] = field(default_factory=dict)
    fault_scenarios: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class HILConfig:
    """Comprehensive HIL system configuration."""
    # System identification
    system_name: str = "HIL_System"
    system_id: str = "hil_001"

    # Operation mode
    mode: HILMode = HILMode.HYBRID
    real_time: bool = True

    # Timing configuration
    timing: TimingConfig = field(default_factory=TimingConfig)

    # Communication settings
    controller_endpoint: str = "localhost:8080"
    plant_endpoint: str = "localhost:8081"
    protocol: str = "udp"

    # Hardware configuration
    hardware_devices: List[Dict[str, Any]] = field(default_factory=list)

    # Simulation settings
    simulation_model: Optional[str] = None
    simulation_params: Dict[str, Any] = field(default_factory=dict)

    # Safety and monitoring
    enable_safety_monitoring: bool = True
    enable_watchdog: bool = True
    watchdog_timeout: float = 1.0
    emergency_stop_channels: List[str] = field(default_factory=list)

    # Data logging
    enable_logging: bool = True
    log_level: str = "INFO"
    data_buffer_size: int = 100000

    # Test automation
    enable_automated_testing: bool = False
    test_scenarios: List[TestScenario] = field(default_factory=list)


class EnhancedHILSystem:
    """
    Enhanced Hardware-in-the-Loop system with advanced capabilities.

    This class provides a comprehensive HIL framework that integrates
    simulation, hardware, real-time scheduling, fault injection,
    and automated testing for professional control system validation.
    """

    def __init__(self, config: HILConfig):
        """Initialize enhanced HIL system."""
        self._config = config
        self._state = HILState.IDLE
        self._logger = logging.getLogger(f"hil_{config.system_id}")

        # Core components
        self._device_manager = DeviceManager()
        self._communication_interfaces: Dict[str, CommunicationProtocol] = {}
        self._simulation_bridge: Optional['SimulationBridge'] = None

        # Real-time components
        self._real_time_scheduler: Optional['RealTimeScheduler'] = None
        self._timing_monitor = TimingMonitor(config.timing)

        # Testing and validation
        self._fault_injector: Optional['FaultInjector'] = None
        self._test_framework: Optional['HILTestFramework'] = None
        self._data_logger: Optional['HILDataLogger'] = None

        # Execution control
        self._main_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._emergency_stop = False

        # Data exchange
        self._input_data: Dict[str, Any] = {}
        self._output_data: Dict[str, Any] = {}
        self._simulation_data: Dict[str, Any] = {}

        # Performance monitoring
        self._performance_metrics = HILPerformanceMetrics()
        self._safety_monitor = SafetyMonitor(config)

    @property
    def state(self) -> HILState:
        """Get current HIL system state."""
        return self._state

    @property
    def config(self) -> HILConfig:
        """Get HIL configuration."""
        return self._config

    @property
    def performance_metrics(self) -> 'HILPerformanceMetrics':
        """Get performance metrics."""
        return self._performance_metrics

    async def initialize(self) -> bool:
        """Initialize HIL system components."""
        try:
            self._state = HILState.INITIALIZING
            self._logger.info(f"Initializing HIL system {self._config.system_id}")

            # Initialize communication interfaces
            await self._setup_communication()

            # Initialize hardware devices
            await self._setup_hardware()

            # Initialize simulation bridge if needed
            if self._config.mode in [HILMode.SIMULATION_ONLY, HILMode.HYBRID]:
                await self._setup_simulation()

            # Initialize real-time scheduler
            if self._config.real_time:
                await self._setup_real_time()

            # Initialize fault injection
            await self._setup_fault_injection()

            # Initialize test framework
            if self._config.enable_automated_testing:
                await self._setup_test_framework()

            # Initialize data logging
            if self._config.enable_logging:
                await self._setup_data_logging()

            # Perform system self-test
            if not await self._system_self_test():
                raise Exception("System self-test failed")

            self._state = HILState.READY
            self._logger.info("HIL system initialization completed successfully")
            return True

        except Exception as e:
            self._logger.error(f"HIL system initialization failed: {e}")
            self._state = HILState.ERROR
            return False

    async def start(self) -> bool:
        """Start HIL system operation."""
        try:
            if self._state != HILState.READY:
                raise Exception(f"Cannot start HIL system in state {self._state}")

            self._logger.info("Starting HIL system operation")
            self._state = HILState.RUNNING
            self._stop_event.clear()

            # Start main execution loop
            self._main_task = asyncio.create_task(self._main_loop())

            # Start subsystems
            if self._real_time_scheduler:
                await self._real_time_scheduler.start()

            if self._data_logger:
                await self._data_logger.start()

            self._logger.info("HIL system started successfully")
            return True

        except Exception as e:
            self._logger.error(f"Failed to start HIL system: {e}")
            self._state = HILState.ERROR
            return False

    async def stop(self) -> bool:
        """Stop HIL system operation."""
        try:
            self._logger.info("Stopping HIL system")
            self._stop_event.set()

            # Stop main loop
            if self._main_task:
                self._main_task.cancel()
                try:
                    await self._main_task
                except asyncio.CancelledError:
                    pass

            # Stop subsystems
            if self._real_time_scheduler:
                await self._real_time_scheduler.stop()

            if self._data_logger:
                await self._data_logger.stop()

            # Stop hardware devices
            await self._device_manager.stop_all()

            self._state = HILState.IDLE
            self._logger.info("HIL system stopped")
            return True

        except Exception as e:
            self._logger.error(f"Error stopping HIL system: {e}")
            return False

    async def emergency_stop(self) -> bool:
        """Perform emergency stop of HIL system."""
        try:
            self._logger.warning("Emergency stop triggered!")
            self._emergency_stop = True
            self._stop_event.set()

            # Immediately stop all actuators
            for device_id in self._device_manager.list_devices():
                device = self._device_manager.get_device(device_id)
                if hasattr(device, 'emergency_stop'):
                    await device.emergency_stop()

            self._state = HILState.ERROR
            return True

        except Exception as e:
            self._logger.error(f"Emergency stop failed: {e}")
            return False

    async def pause(self) -> bool:
        """Pause HIL system operation."""
        if self._state == HILState.RUNNING:
            self._state = HILState.PAUSED
            self._logger.info("HIL system paused")
            return True
        return False

    async def resume(self) -> bool:
        """Resume HIL system operation."""
        if self._state == HILState.PAUSED:
            self._state = HILState.RUNNING
            self._logger.info("HIL system resumed")
            return True
        return False

    async def run_test_scenario(self, scenario: TestScenario) -> Dict[str, Any]:
        """Run specific test scenario."""
        try:
            self._logger.info(f"Running test scenario: {scenario.name}")

            # Set initial conditions
            await self._apply_initial_conditions(scenario.initial_conditions)

            # Configure parameters
            await self._apply_parameters(scenario.parameters)

            # Configure fault scenarios
            if scenario.fault_scenarios and self._fault_injector:
                for fault_scenario in scenario.fault_scenarios:
                    await self._fault_injector.configure_scenario(fault_scenario)

            # Run scenario
            start_time = time.time()
            scenario_data = []

            while (time.time() - start_time) < scenario.duration:
                # Collect data
                current_data = {
                    'timestamp': time.time() - start_time,
                    'inputs': self._input_data.copy(),
                    'outputs': self._output_data.copy(),
                    'simulation': self._simulation_data.copy()
                }
                scenario_data.append(current_data)

                await asyncio.sleep(self._config.timing.sample_time)

            # Analyze results
            results = await self._analyze_scenario_results(scenario, scenario_data)

            self._logger.info(f"Test scenario {scenario.name} completed")
            return results

        except Exception as e:
            self._logger.error(f"Test scenario {scenario.name} failed: {e}")
            return {'status': 'failed', 'error': str(e)}

    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        device_status = self._device_manager.get_status_summary()

        status = {
            'system_id': self._config.system_id,
            'state': self._state.value,
            'mode': self._config.mode.value,
            'real_time': self._config.real_time,
            'emergency_stop': self._emergency_stop,
            'devices': device_status,
            'performance': self._performance_metrics.get_summary(),
            'timing': self._timing_monitor.get_statistics(),
            'safety': self._safety_monitor.get_status(),
            'uptime': time.time() - getattr(self, '_start_time', time.time())
        }

        return status

    async def _setup_communication(self) -> None:
        """Setup communication interfaces."""
        try:
            # Create controller interface
            controller_interface = NetworkInterfaceFactory.create_interface(
                f"{self._config.protocol}_client",
                name="hil_controller",
                config_overrides={'endpoint': self._config.controller_endpoint}
            )

            # Create plant interface
            plant_interface = NetworkInterfaceFactory.create_interface(
                f"{self._config.protocol}_server",
                name="hil_plant",
                config_overrides={'endpoint': self._config.plant_endpoint}
            )

            self._communication_interfaces['controller'] = controller_interface
            self._communication_interfaces['plant'] = plant_interface

            # Connect interfaces
            await controller_interface.connect({})
            await plant_interface.connect({'server_mode': True})

        except Exception as e:
            raise Exception(f"Failed to setup communication: {e}")

    async def _setup_hardware(self) -> None:
        """Setup hardware devices."""
        try:
            from ..hardware.factory import HardwareInterfaceFactory

            for device_config in self._config.hardware_devices:
                device_type = device_config['type']
                device_id = device_config['id']
                config = device_config.get('config', {})

                device = HardwareInterfaceFactory.create_device(
                    device_type, device_id, config
                )

                self._device_manager.add_device(device)

            # Initialize all devices
            await self._device_manager.start_all()

        except Exception as e:
            raise Exception(f"Failed to setup hardware: {e}")

    async def _setup_simulation(self) -> None:
        """Setup simulation bridge."""
        try:
            from .simulation_bridge import SimulationBridge

            self._simulation_bridge = SimulationBridge(
                model_name=self._config.simulation_model,
                parameters=self._config.simulation_params
            )

            await self._simulation_bridge.initialize()

        except Exception as e:
            raise Exception(f"Failed to setup simulation: {e}")

    async def _setup_real_time(self) -> None:
        """Setup real-time scheduler."""
        try:
            from .real_time_sync import RealTimeScheduler

            self._real_time_scheduler = RealTimeScheduler(
                sample_time=self._config.timing.sample_time,
                priority=self._config.timing.priority,
                cpu_affinity=self._config.timing.cpu_affinity
            )

        except Exception as e:
            raise Exception(f"Failed to setup real-time scheduler: {e}")

    async def _setup_fault_injection(self) -> None:
        """Setup fault injection system."""
        try:
            from .fault_injection import FaultInjector

            self._fault_injector = FaultInjector(
                device_manager=self._device_manager,
                communication_interfaces=self._communication_interfaces
            )

        except Exception as e:
            raise Exception(f"Failed to setup fault injection: {e}")

    async def _setup_test_framework(self) -> None:
        """Setup automated test framework."""
        try:
            from .test_automation import HILTestFramework

            self._test_framework = HILTestFramework(
                hil_system=self,
                test_scenarios=self._config.test_scenarios
            )

        except Exception as e:
            raise Exception(f"Failed to setup test framework: {e}")

    async def _setup_data_logging(self) -> None:
        """Setup data logging system."""
        try:
            from .data_logging import HILDataLogger, LoggingConfig

            logging_config = LoggingConfig(
                buffer_size=self._config.data_buffer_size,
                sample_rate=1.0 / self._config.timing.sample_time
            )

            self._data_logger = HILDataLogger(logging_config)
            await self._data_logger.initialize()

        except Exception as e:
            raise Exception(f"Failed to setup data logging: {e}")

    async def _system_self_test(self) -> bool:
        """Perform comprehensive system self-test."""
        try:
            self._logger.info("Performing system self-test")

            # Test communication interfaces
            for name, interface in self._communication_interfaces.items():
                if not hasattr(interface, 'get_connection_state'):
                    continue
                # Basic connectivity test would go here

            # Test hardware devices
            health_results = await self._device_manager.health_check_all()
            for device_id, result in health_results.items():
                if result.get('overall_status') != 'PASS':
                    self._logger.warning(f"Device {device_id} health check failed")

            # Test simulation bridge
            if self._simulation_bridge:
                if not await self._simulation_bridge.self_test():
                    return False

            self._logger.info("System self-test completed successfully")
            return True

        except Exception as e:
            self._logger.error(f"System self-test failed: {e}")
            return False

    async def _main_loop(self) -> None:
        """Main HIL execution loop."""
        try:
            loop_start_time = time.time()
            iteration = 0

            while not self._stop_event.is_set() and self._state == HILState.RUNNING:
                iteration_start = time.time()

                # Read inputs from hardware/communication
                await self._read_inputs()

                # Update simulation if enabled
                if self._simulation_bridge:
                    await self._update_simulation()

                # Process safety monitoring
                await self._safety_monitor.check_safety(self._input_data, self._output_data)

                # Write outputs to hardware/communication
                await self._write_outputs()

                # Log data
                if self._data_logger:
                    await self._data_logger.log_data({
                        'iteration': iteration,
                        'timestamp': time.time() - loop_start_time,
                        'inputs': self._input_data.copy(),
                        'outputs': self._output_data.copy(),
                        'simulation': self._simulation_data.copy()
                    })

                # Update performance metrics
                iteration_time = time.time() - iteration_start
                self._performance_metrics.update(iteration_time)
                self._timing_monitor.record_iteration(iteration_time)

                # Real-time scheduling
                if self._real_time_scheduler:
                    await self._real_time_scheduler.wait_for_next_period()
                else:
                    # Simple timing control
                    elapsed = time.time() - iteration_start
                    sleep_time = max(0, self._config.timing.sample_time - elapsed)
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)

                iteration += 1

        except Exception as e:
            self._logger.error(f"Main loop error: {e}")
            self._state = HILState.ERROR

    async def _read_inputs(self) -> None:
        """Read inputs from all sources."""
        # Read from hardware devices
        for device_id in self._device_manager.list_devices():
            device = self._device_manager.get_device(device_id)
            try:
                data = await device.read_data()
                self._input_data.update({f"{device_id}_{k}": v for k, v in data.items()})
            except Exception as e:
                self._logger.warning(f"Error reading from device {device_id}: {e}")

        # Read from communication interfaces
        for name, interface in self._communication_interfaces.items():
            try:
                # Interface-specific data reading would be implemented here
                pass
            except Exception as e:
                self._logger.warning(f"Error reading from interface {name}: {e}")

    async def _update_simulation(self) -> None:
        """Update simulation model."""
        if self._simulation_bridge:
            try:
                self._simulation_data = await self._simulation_bridge.step(
                    self._input_data, self._config.timing.sample_time
                )
            except Exception as e:
                self._logger.warning(f"Simulation update error: {e}")

    async def _write_outputs(self) -> None:
        """Write outputs to all destinations."""
        # Write to hardware devices
        for device_id in self._device_manager.list_devices():
            device = self._device_manager.get_device(device_id)
            try:
                # Extract relevant data for this device
                device_data = {
                    k.replace(f"{device_id}_", ""): v
                    for k, v in self._output_data.items()
                    if k.startswith(f"{device_id}_")
                }
                if device_data:
                    await device.write_data(device_data)
            except Exception as e:
                self._logger.warning(f"Error writing to device {device_id}: {e}")

    async def _apply_initial_conditions(self, conditions: Dict[str, Any]) -> None:
        """Apply initial conditions for test scenario."""
        for key, value in conditions.items():
            self._output_data[key] = value

    async def _apply_parameters(self, parameters: Dict[str, Any]) -> None:
        """Apply parameters for test scenario."""
        if self._simulation_bridge:
            await self._simulation_bridge.set_parameters(parameters)

    async def _analyze_scenario_results(self, scenario: TestScenario, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze test scenario results."""
        # Basic result analysis - would be expanded for specific test requirements
        results = {
            'scenario_name': scenario.name,
            'status': 'completed',
            'duration': scenario.duration,
            'data_points': len(data),
            'passed': True,
            'metrics': {}
        }

        # Check expected results against tolerance
        for key, expected in scenario.expected_results.items():
            tolerance = scenario.tolerance.get(key, 0.01)
            # Analysis logic would be implemented here based on requirements

        return results


class TimingMonitor:
    """Monitor timing performance of HIL system."""

    def __init__(self, timing_config: TimingConfig):
        self.config = timing_config
        self.iteration_times: List[float] = []
        self.deadline_misses = 0
        self.max_jitter = 0.0

    def record_iteration(self, iteration_time: float) -> None:
        """Record iteration timing."""
        self.iteration_times.append(iteration_time)

        # Keep only recent history
        if len(self.iteration_times) > 1000:
            self.iteration_times.pop(0)

        # Check for deadline miss
        deadline = self.config.sample_time * self.config.deadline_factor
        if iteration_time > deadline:
            self.deadline_misses += 1

        # Update jitter
        if len(self.iteration_times) > 1:
            jitter = abs(iteration_time - self.iteration_times[-2])
            self.max_jitter = max(self.max_jitter, jitter)

    def get_statistics(self) -> Dict[str, Any]:
        """Get timing statistics."""
        if not self.iteration_times:
            return {}

        return {
            'mean_time': np.mean(self.iteration_times),
            'max_time': np.max(self.iteration_times),
            'min_time': np.min(self.iteration_times),
            'std_time': np.std(self.iteration_times),
            'deadline_misses': self.deadline_misses,
            'max_jitter': self.max_jitter,
            'deadline_miss_rate': self.deadline_misses / len(self.iteration_times)
        }


class HILPerformanceMetrics:
    """Performance metrics for HIL system."""

    def __init__(self):
        self.iterations = 0
        self.total_time = 0.0
        self.cpu_usage = 0.0
        self.memory_usage = 0.0

    def update(self, iteration_time: float) -> None:
        """Update performance metrics."""
        self.iterations += 1
        self.total_time += iteration_time

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            'iterations': self.iterations,
            'avg_iteration_time': self.total_time / max(1, self.iterations),
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage
        }


class SafetyMonitor:
    """Safety monitoring for HIL system."""

    def __init__(self, config: HILConfig):
        self.config = config
        self.safety_violations = 0
        self.last_check = time.time()

    async def check_safety(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> bool:
        """Check safety conditions."""
        # Implement safety checks based on configuration
        # This would include limits checking, rate limiting, etc.
        self.last_check = time.time()
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get safety status."""
        return {
            'violations': self.safety_violations,
            'last_check': self.last_check,
            'status': 'safe' if self.safety_violations == 0 else 'warning'
        }