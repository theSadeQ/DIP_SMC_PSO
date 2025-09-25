#==========================================================================================\\\
#======================== src/interfaces/hil/simulation_bridge.py =====================\\\
#==========================================================================================\\\
"""
Simulation bridge for HIL systems.
This module provides seamless integration between hardware components and
simulation models, enabling hybrid testing where some components are real
hardware and others are simulated models.
"""

import asyncio
import time
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum
import logging


class BridgeMode(Enum):
    """Bridge operation mode."""
    HARDWARE_ONLY = "hardware_only"
    SIMULATION_ONLY = "simulation_only"
    HYBRID = "hybrid"
    VALIDATION = "validation"


class ModelType(Enum):
    """Simulation model type."""
    PLANT_MODEL = "plant"
    CONTROLLER_MODEL = "controller"
    SENSOR_MODEL = "sensor"
    ACTUATOR_MODEL = "actuator"
    ENVIRONMENT_MODEL = "environment"


@dataclass
class BridgeConfig:
    """Configuration for simulation bridge."""
    mode: BridgeMode = BridgeMode.HYBRID
    sample_time: float = 0.001  # 1ms default
    real_time_factor: float = 1.0  # Real-time execution
    synchronization_tolerance: float = 0.0001  # 100μs
    enable_logging: bool = True
    log_level: str = "INFO"
    buffer_size: int = 10000
    enable_validation: bool = True
    validation_tolerance: float = 0.01


@dataclass
class ModelState:
    """State information for a simulation model."""
    model_id: str
    model_type: ModelType
    state_vector: np.ndarray
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    is_active: bool = True


class ModelInterface(ABC):
    """Abstract interface for simulation models."""

    @abstractmethod
    async def initialize(self, parameters: Dict[str, Any]) -> bool:
        """Initialize the model with given parameters."""
        pass

    @abstractmethod
    async def step(self, inputs: Dict[str, Any], dt: float) -> Dict[str, Any]:
        """Execute one simulation step."""
        pass

    @abstractmethod
    async def get_state(self) -> ModelState:
        """Get current model state."""
        pass

    @abstractmethod
    async def set_state(self, state: ModelState) -> bool:
        """Set model state."""
        pass

    @abstractmethod
    async def reset(self) -> bool:
        """Reset model to initial state."""
        pass

    @abstractmethod
    async def cleanup(self) -> bool:
        """Clean up model resources."""
        pass

    @property
    @abstractmethod
    def model_type(self) -> ModelType:
        """Get model type."""
        pass

    @property
    @abstractmethod
    def input_names(self) -> List[str]:
        """Get list of input signal names."""
        pass

    @property
    @abstractmethod
    def output_names(self) -> List[str]:
        """Get list of output signal names."""
        pass


class PlantModel(ModelInterface):
    """Base class for plant simulation models."""

    def __init__(self, model_id: str):
        self._model_id = model_id
        self._state = None
        self._parameters = {}
        self._initialized = False

    @property
    def model_type(self) -> ModelType:
        return ModelType.PLANT_MODEL

    async def initialize(self, parameters: Dict[str, Any]) -> bool:
        """Initialize plant model."""
        try:
            self._parameters = parameters.copy()

            # Initialize state vector
            state_size = parameters.get('state_size', 6)
            initial_state = parameters.get('initial_state', np.zeros(state_size))
            self._state = np.array(initial_state, dtype=float)

            self._initialized = True
            return True

        except Exception as e:
            logging.error(f"Failed to initialize plant model {self._model_id}: {e}")
            return False

    async def get_state(self) -> ModelState:
        """Get current plant state."""
        return ModelState(
            model_id=self._model_id,
            model_type=self.model_type,
            state_vector=self._state.copy() if self._state is not None else np.array([]),
            parameters=self._parameters.copy(),
            timestamp=time.time(),
            is_active=self._initialized
        )

    async def set_state(self, state: ModelState) -> bool:
        """Set plant state."""
        try:
            if state.model_id == self._model_id:
                self._state = state.state_vector.copy()
                return True
            return False
        except Exception:
            return False

    async def reset(self) -> bool:
        """Reset plant to initial state."""
        if self._initialized:
            initial_state = self._parameters.get('initial_state', np.zeros_like(self._state))
            self._state = np.array(initial_state, dtype=float)
            return True
        return False

    async def cleanup(self) -> bool:
        """Clean up plant model."""
        self._initialized = False
        return True


class LinearPlantModel(PlantModel):
    """Linear plant model implementation."""

    def __init__(self, model_id: str):
        super().__init__(model_id)
        self._A = None
        self._B = None
        self._C = None
        self._D = None

    @property
    def input_names(self) -> List[str]:
        return ['control_input']

    @property
    def output_names(self) -> List[str]:
        return ['plant_output', 'state_vector']

    async def initialize(self, parameters: Dict[str, Any]) -> bool:
        """Initialize linear plant model."""
        success = await super().initialize(parameters)
        if not success:
            return False

        try:
            # Extract state-space matrices
            self._A = np.array(parameters['A'], dtype=float)
            self._B = np.array(parameters['B'], dtype=float)
            self._C = np.array(parameters.get('C', np.eye(self._A.shape[0])), dtype=float)
            self._D = np.array(parameters.get('D', np.zeros((self._C.shape[0], self._B.shape[1]))), dtype=float)

            return True

        except Exception as e:
            logging.error(f"Failed to initialize linear plant matrices: {e}")
            return False

    async def step(self, inputs: Dict[str, Any], dt: float) -> Dict[str, Any]:
        """Execute linear plant simulation step."""
        if not self._initialized or self._state is None:
            return {}

        try:
            # Get control input
            u = np.array(inputs.get('control_input', 0.0))
            u = np.atleast_1d(u)

            # Discrete-time integration (zero-order hold)
            # x[k+1] = Ad * x[k] + Bd * u[k]
            # y[k] = C * x[k] + D * u[k]

            # Compute discrete-time matrices if continuous
            if 'discrete' not in self._parameters or not self._parameters['discrete']:
                # Zero-order hold discretization
                n = self._A.shape[0]
                m = self._B.shape[1]

                # Exponential matrix computation
                import scipy.linalg
                F = np.block([[self._A, self._B], [np.zeros((m, n + m))]])
                expF = scipy.linalg.expm(F * dt)

                Ad = expF[:n, :n]
                Bd = expF[:n, n:]
            else:
                Ad = self._A
                Bd = self._B

            # State update
            self._state = Ad @ self._state + Bd @ u

            # Output computation
            y = self._C @ self._state + self._D @ u

            return {
                'plant_output': y,
                'state_vector': self._state.copy(),
                'timestamp': time.time()
            }

        except Exception as e:
            logging.error(f"Error in linear plant simulation step: {e}")
            return {}


class SignalMapper:
    """Maps signals between hardware and simulation components."""

    def __init__(self):
        self._mappings: Dict[str, Dict[str, Any]] = {}
        self._transformations: Dict[str, Callable] = {}

    def add_mapping(self, source: str, destination: str,
                   transformation: Optional[Callable[[Any], Any]] = None,
                   scaling: Optional[float] = None,
                   offset: Optional[float] = None) -> None:
        """Add signal mapping."""
        mapping = {
            'destination': destination,
            'transformation': transformation,
            'scaling': scaling or 1.0,
            'offset': offset or 0.0
        }
        self._mappings[source] = mapping

    def map_signal(self, source: str, value: Any) -> Dict[str, Any]:
        """Map signal from source to destination."""
        if source not in self._mappings:
            return {}

        mapping = self._mappings[source]
        mapped_value = value

        try:
            # Apply scaling and offset
            if isinstance(value, (int, float, np.ndarray)):
                mapped_value = value * mapping['scaling'] + mapping['offset']

            # Apply custom transformation
            if mapping['transformation']:
                mapped_value = mapping['transformation'](mapped_value)

            return {mapping['destination']: mapped_value}

        except Exception as e:
            logging.error(f"Error mapping signal {source}: {e}")
            return {}

    def get_mappings(self) -> Dict[str, str]:
        """Get all signal mappings."""
        return {src: mapping['destination'] for src, mapping in self._mappings.items()}


class SimulationBridge:
    """
    Main simulation bridge for HIL systems.

    Coordinates execution between hardware components and simulation models,
    ensuring proper timing, data flow, and synchronization.
    """

    def __init__(self, config: Optional[BridgeConfig] = None):
        """Initialize simulation bridge."""
        self._config = config or BridgeConfig()
        self._models: Dict[str, ModelInterface] = {}
        self._signal_mapper = SignalMapper()

        # Execution control
        self._running = False
        self._paused = False
        self._step_count = 0
        self._start_time = 0.0
        self._simulation_time = 0.0

        # Data buffers
        self._input_buffer: Dict[str, List[Any]] = {}
        self._output_buffer: Dict[str, List[Any]] = {}
        self._state_history: List[Dict[str, ModelState]] = []

        # Performance monitoring
        self._step_times: List[float] = []
        self._sync_errors: List[float] = []

        # Hardware interface callbacks
        self._hardware_read_callback: Optional[Callable] = None
        self._hardware_write_callback: Optional[Callable] = None

        self._logger = logging.getLogger("simulation_bridge")

    async def initialize(self) -> bool:
        """Initialize simulation bridge."""
        try:
            self._logger.info("Initializing simulation bridge")

            # Initialize all models
            for model_id, model in self._models.items():
                if not await model.initialize({}):
                    self._logger.error(f"Failed to initialize model {model_id}")
                    return False

            # Initialize buffers
            self._input_buffer.clear()
            self._output_buffer.clear()
            self._state_history.clear()

            self._logger.info(f"Simulation bridge initialized with {len(self._models)} models")
            return True

        except Exception as e:
            self._logger.error(f"Failed to initialize simulation bridge: {e}")
            return False

    async def start(self) -> bool:
        """Start simulation bridge execution."""
        if not await self.initialize():
            return False

        try:
            self._running = True
            self._paused = False
            self._step_count = 0
            self._start_time = time.time()
            self._simulation_time = 0.0

            self._logger.info("Simulation bridge started")
            return True

        except Exception as e:
            self._logger.error(f"Failed to start simulation bridge: {e}")
            return False

    async def stop(self) -> bool:
        """Stop simulation bridge execution."""
        try:
            self._running = False

            # Cleanup all models
            for model in self._models.values():
                await model.cleanup()

            self._logger.info("Simulation bridge stopped")
            return True

        except Exception as e:
            self._logger.error(f"Error stopping simulation bridge: {e}")
            return False

    def add_model(self, model_id: str, model: ModelInterface) -> bool:
        """Add simulation model to bridge."""
        if model_id in self._models:
            self._logger.warning(f"Model {model_id} already exists, replacing")

        self._models[model_id] = model
        self._logger.info(f"Added {model.model_type.value} model: {model_id}")
        return True

    def remove_model(self, model_id: str) -> bool:
        """Remove simulation model from bridge."""
        if model_id in self._models:
            del self._models[model_id]
            self._logger.info(f"Removed model: {model_id}")
            return True
        return False

    def add_signal_mapping(self, source: str, destination: str,
                          transformation: Optional[Callable] = None) -> None:
        """Add signal mapping between components."""
        self._signal_mapper.add_mapping(source, destination, transformation)

    def set_hardware_interface(self, read_callback: Callable, write_callback: Callable) -> None:
        """Set hardware interface callbacks."""
        self._hardware_read_callback = read_callback
        self._hardware_write_callback = write_callback

    async def execute_step(self) -> bool:
        """Execute one simulation/HIL step."""
        if not self._running or self._paused:
            return False

        step_start = time.time()

        try:
            # Read from hardware if available
            hardware_inputs = {}
            if self._hardware_read_callback:
                hardware_inputs = await self._hardware_read_callback()

            # Collect model states
            model_states = {}
            for model_id, model in self._models.items():
                model_states[model_id] = await model.get_state()

            # Execute simulation models
            model_outputs = {}
            for model_id, model in self._models.items():
                # Map inputs for this model
                model_inputs = self._map_inputs_for_model(model, hardware_inputs, model_outputs)

                # Execute model step
                outputs = await model.step(model_inputs, self._config.sample_time)
                model_outputs[model_id] = outputs

            # Map outputs to hardware
            hardware_outputs = self._map_outputs_to_hardware(model_outputs)

            # Write to hardware if available
            if self._hardware_write_callback and hardware_outputs:
                await self._hardware_write_callback(hardware_outputs)

            # Update buffers and history
            self._update_buffers(hardware_inputs, model_outputs)
            self._state_history.append(model_states)

            # Maintain buffer size
            if len(self._state_history) > self._config.buffer_size:
                self._state_history.pop(0)

            # Update timing
            self._step_count += 1
            self._simulation_time += self._config.sample_time

            step_time = time.time() - step_start
            self._step_times.append(step_time)

            # Check timing constraints
            expected_time = self._config.sample_time / self._config.real_time_factor
            sync_error = abs(step_time - expected_time)
            self._sync_errors.append(sync_error)

            if sync_error > self._config.synchronization_tolerance:
                self._logger.warning(f"Synchronization error: {sync_error*1000:.2f}ms")

            return True

        except Exception as e:
            self._logger.error(f"Error in simulation step: {e}")
            return False

    async def run_continuous(self, duration: Optional[float] = None) -> bool:
        """Run simulation bridge continuously."""
        if not self._running:
            if not await self.start():
                return False

        try:
            end_time = time.time() + duration if duration else float('inf')

            while self._running and time.time() < end_time:
                if not await self.execute_step():
                    break

                # Real-time synchronization
                await self._synchronize_real_time()

            return True

        except Exception as e:
            self._logger.error(f"Error in continuous execution: {e}")
            return False

    def pause(self) -> None:
        """Pause simulation bridge execution."""
        self._paused = True

    def resume(self) -> None:
        """Resume simulation bridge execution."""
        self._paused = False

    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self._step_times:
            return {}

        return {
            'total_steps': self._step_count,
            'simulation_time': self._simulation_time,
            'wall_clock_time': time.time() - self._start_time if self._running else 0.0,
            'average_step_time': np.mean(self._step_times),
            'max_step_time': np.max(self._step_times),
            'average_sync_error': np.mean(self._sync_errors) if self._sync_errors else 0.0,
            'max_sync_error': np.max(self._sync_errors) if self._sync_errors else 0.0,
            'real_time_factor_achieved': self._simulation_time / (time.time() - self._start_time) if self._running and time.time() > self._start_time else 0.0
        }

    def _map_inputs_for_model(self, model: ModelInterface,
                             hardware_inputs: Dict[str, Any],
                             model_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Map inputs for a specific model."""
        inputs = {}

        # Map from hardware
        for hw_signal, value in hardware_inputs.items():
            mapped = self._signal_mapper.map_signal(hw_signal, value)
            for signal_name in model.input_names:
                if signal_name in mapped:
                    inputs[signal_name] = mapped[signal_name]

        # Map from other models
        for other_model_id, outputs in model_outputs.items():
            for output_signal, value in outputs.items():
                mapped = self._signal_mapper.map_signal(f"{other_model_id}.{output_signal}", value)
                for signal_name in model.input_names:
                    if signal_name in mapped:
                        inputs[signal_name] = mapped[signal_name]

        return inputs

    def _map_outputs_to_hardware(self, model_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Map model outputs to hardware signals."""
        hardware_outputs = {}

        for model_id, outputs in model_outputs.items():
            for output_signal, value in outputs.items():
                mapped = self._signal_mapper.map_signal(f"{model_id}.{output_signal}", value)
                hardware_outputs.update(mapped)

        return hardware_outputs

    def _update_buffers(self, inputs: Dict[str, Any], outputs: Dict[str, Dict[str, Any]]) -> None:
        """Update data buffers."""
        # Update input buffer
        for signal, value in inputs.items():
            if signal not in self._input_buffer:
                self._input_buffer[signal] = []
            self._input_buffer[signal].append(value)

            # Maintain buffer size
            if len(self._input_buffer[signal]) > self._config.buffer_size:
                self._input_buffer[signal].pop(0)

        # Update output buffer
        for model_id, model_outputs in outputs.items():
            for signal, value in model_outputs.items():
                full_signal = f"{model_id}.{signal}"
                if full_signal not in self._output_buffer:
                    self._output_buffer[full_signal] = []
                self._output_buffer[full_signal].append(value)

                # Maintain buffer size
                if len(self._output_buffer[full_signal]) > self._config.buffer_size:
                    self._output_buffer[full_signal].pop(0)

    async def _synchronize_real_time(self) -> None:
        """Synchronize with real-time execution."""
        if self._config.real_time_factor <= 0:
            return

        expected_wall_time = self._simulation_time / self._config.real_time_factor
        actual_wall_time = time.time() - self._start_time
        sleep_time = expected_wall_time - actual_wall_time

        if sleep_time > 0:
            await asyncio.sleep(sleep_time)


# Factory functions for common models
def create_linear_plant_model(model_id: str, A: np.ndarray, B: np.ndarray,
                             C: Optional[np.ndarray] = None,
                             D: Optional[np.ndarray] = None) -> LinearPlantModel:
    """Create linear plant model with state-space matrices."""
    model = LinearPlantModel(model_id)
    return model


def create_simulation_bridge(sample_time: float = 0.001,
                           real_time_factor: float = 1.0) -> SimulationBridge:
    """Create simulation bridge with default configuration."""
    config = BridgeConfig(
        sample_time=sample_time,
        real_time_factor=real_time_factor
    )
    return SimulationBridge(config)