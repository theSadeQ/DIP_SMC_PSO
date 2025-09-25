#==========================================================================================\\\
#====================== src/optimization/core/parameters.py ========================\\\
#==========================================================================================\\\

"""Parameter space definitions and management."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from .interfaces import ParameterSpace


class Parameter(ABC):
    """Abstract base class for optimization parameters."""

    def __init__(self, name: str, description: str = ""):
        """Initialize parameter.

        Parameters
        ----------
        name : str
            Parameter name
        description : str, optional
            Parameter description
        """
        self.name = name
        self.description = description

    @abstractmethod
    def sample(self, n_samples: int, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        """Sample values from parameter domain."""
        pass

    @abstractmethod
    def validate(self, value: Union[float, np.ndarray]) -> bool:
        """Validate parameter value(s)."""
        pass

    @abstractmethod
    def clip(self, value: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Clip value(s) to valid range."""
        pass

    @property
    @abstractmethod
    def bounds(self) -> Tuple[float, float]:
        """Parameter bounds (lower, upper)."""
        pass


class ContinuousParameter(Parameter):
    """Continuous real-valued parameter."""

    def __init__(self,
                 name: str,
                 lower: float,
                 upper: float,
                 description: str = "",
                 log_scale: bool = False):
        """Initialize continuous parameter.

        Parameters
        ----------
        name : str
            Parameter name
        lower : float
            Lower bound
        upper : float
            Upper bound
        description : str, optional
            Parameter description
        log_scale : bool, optional
            Whether to use log scale for sampling
        """
        super().__init__(name, description)
        self.lower = lower
        self.upper = upper
        self.log_scale = log_scale

        if lower >= upper:
            raise ValueError(f"Lower bound ({lower}) must be less than upper bound ({upper})")

        if log_scale and (lower <= 0 or upper <= 0):
            raise ValueError("Log scale requires positive bounds")

    def sample(self, n_samples: int, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        """Sample from uniform distribution."""
        if rng is None:
            rng = np.random.default_rng()

        if self.log_scale:
            log_lower = np.log(self.lower)
            log_upper = np.log(self.upper)
            log_samples = rng.uniform(log_lower, log_upper, n_samples)
            return np.exp(log_samples)
        else:
            return rng.uniform(self.lower, self.upper, n_samples)

    def validate(self, value: Union[float, np.ndarray]) -> bool:
        """Check if value is within bounds."""
        return np.all(value >= self.lower) and np.all(value <= self.upper)

    def clip(self, value: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Clip to bounds."""
        return np.clip(value, self.lower, self.upper)

    @property
    def bounds(self) -> Tuple[float, float]:
        """Parameter bounds."""
        return (self.lower, self.upper)


class DiscreteParameter(Parameter):
    """Discrete parameter with finite set of values."""

    def __init__(self,
                 name: str,
                 values: List[Union[int, float, str]],
                 description: str = ""):
        """Initialize discrete parameter.

        Parameters
        ----------
        name : str
            Parameter name
        values : List[Union[int, float, str]]
            Allowed parameter values
        description : str, optional
            Parameter description
        """
        super().__init__(name, description)
        self.values = values
        self.n_values = len(values)

        if self.n_values == 0:
            raise ValueError("At least one value must be provided")

    def sample(self, n_samples: int, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        """Sample from discrete values."""
        if rng is None:
            rng = np.random.default_rng()

        indices = rng.integers(0, self.n_values, n_samples)
        return np.array([self.values[i] for i in indices])

    def validate(self, value: Union[float, np.ndarray]) -> bool:
        """Check if value is in allowed set."""
        if isinstance(value, np.ndarray):
            return all(v in self.values for v in value)
        return value in self.values

    def clip(self, value: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Find closest valid value."""
        if isinstance(value, np.ndarray):
            return np.array([self._find_closest(v) for v in value])
        return self._find_closest(value)

    def _find_closest(self, value: Union[int, float, str]) -> Union[int, float, str]:
        """Find closest valid value."""
        if value in self.values:
            return value

        # For numeric values, find closest
        if all(isinstance(v, (int, float)) for v in self.values):
            numeric_values = np.array(self.values)
            idx = np.argmin(np.abs(numeric_values - float(value)))
            return self.values[idx]

        # For non-numeric, return first value
        return self.values[0]

    @property
    def bounds(self) -> Tuple[float, float]:
        """Bounds for discrete parameter (min and max values)."""
        if all(isinstance(v, (int, float)) for v in self.values):
            return (min(self.values), max(self.values))
        return (0, len(self.values) - 1)


class ContinuousParameterSpace(ParameterSpace):
    """Continuous parameter space with box constraints."""

    def __init__(self, lower_bounds: np.ndarray, upper_bounds: np.ndarray, names: Optional[List[str]] = None):
        """Initialize continuous parameter space.

        Parameters
        ----------
        lower_bounds : np.ndarray
            Lower bounds for each parameter
        upper_bounds : np.ndarray
            Upper bounds for each parameter
        names : List[str], optional
            Parameter names
        """
        self.lower_bounds = np.asarray(lower_bounds)
        self.upper_bounds = np.asarray(upper_bounds)

        if self.lower_bounds.shape != self.upper_bounds.shape:
            raise ValueError("Lower and upper bounds must have same shape")

        if np.any(self.lower_bounds >= self.upper_bounds):
            raise ValueError("Lower bounds must be less than upper bounds")

        self.names = names or [f"param_{i}" for i in range(len(self.lower_bounds))]
        self._dimensions = len(self.lower_bounds)

    def sample(self, n_samples: int, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        """Sample uniformly from parameter space."""
        if rng is None:
            rng = np.random.default_rng()

        return rng.uniform(
            self.lower_bounds,
            self.upper_bounds,
            size=(n_samples, self._dimensions)
        )

    def validate(self, parameters: np.ndarray) -> bool:
        """Check if parameters are within bounds."""
        parameters = np.atleast_2d(parameters)
        return (np.all(parameters >= self.lower_bounds) and
                np.all(parameters <= self.upper_bounds))

    def clip(self, parameters: np.ndarray) -> np.ndarray:
        """Clip parameters to bounds."""
        return np.clip(parameters, self.lower_bounds, self.upper_bounds)

    @property
    def dimensions(self) -> int:
        """Number of parameters."""
        return self._dimensions

    @property
    def bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Parameter bounds."""
        return (self.lower_bounds, self.upper_bounds)

    def get_parameter_info(self) -> List[Dict[str, Any]]:
        """Get information about each parameter."""
        return [
            {
                'name': name,
                'lower': float(lower),
                'upper': float(upper),
                'type': 'continuous'
            }
            for name, lower, upper in zip(self.names, self.lower_bounds, self.upper_bounds)
        ]


class MixedParameterSpace(ParameterSpace):
    """Mixed parameter space with continuous and discrete parameters."""

    def __init__(self, parameters: List[Parameter]):
        """Initialize mixed parameter space.

        Parameters
        ----------
        parameters : List[Parameter]
            List of parameter definitions
        """
        self.parameters = parameters
        self._dimensions = len(parameters)

        # Separate continuous and discrete parameters
        self.continuous_indices = []
        self.discrete_indices = []

        for i, param in enumerate(parameters):
            if isinstance(param, ContinuousParameter):
                self.continuous_indices.append(i)
            elif isinstance(param, DiscreteParameter):
                self.discrete_indices.append(i)

    def sample(self, n_samples: int, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        """Sample from mixed parameter space."""
        if rng is None:
            rng = np.random.default_rng()

        samples = np.zeros((n_samples, self._dimensions))

        for i, param in enumerate(self.parameters):
            samples[:, i] = param.sample(n_samples, rng)

        return samples

    def validate(self, parameters: np.ndarray) -> bool:
        """Validate mixed parameters."""
        parameters = np.atleast_2d(parameters)

        for i, param in enumerate(self.parameters):
            if not param.validate(parameters[:, i]):
                return False

        return True

    def clip(self, parameters: np.ndarray) -> np.ndarray:
        """Clip mixed parameters."""
        parameters = np.atleast_2d(parameters)
        clipped = parameters.copy()

        for i, param in enumerate(self.parameters):
            clipped[:, i] = param.clip(parameters[:, i])

        return clipped

    @property
    def dimensions(self) -> int:
        """Number of parameters."""
        return self._dimensions

    @property
    def bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Parameter bounds."""
        lower = np.array([param.bounds[0] for param in self.parameters])
        upper = np.array([param.bounds[1] for param in self.parameters])
        return (lower, upper)


class ParameterBounds:
    """Helper class for parameter bounds management."""

    def __init__(self, lower: np.ndarray, upper: np.ndarray, names: Optional[List[str]] = None):
        """Initialize parameter bounds."""
        self.lower = np.asarray(lower)
        self.upper = np.asarray(upper)
        self.names = names or [f"param_{i}" for i in range(len(lower))]

    def to_parameter_space(self) -> ContinuousParameterSpace:
        """Convert to continuous parameter space."""
        return ContinuousParameterSpace(self.lower, self.upper, self.names)

    def scale_to_unit(self, parameters: np.ndarray) -> np.ndarray:
        """Scale parameters to unit cube [0,1]^n."""
        return (parameters - self.lower) / (self.upper - self.lower)

    def scale_from_unit(self, unit_parameters: np.ndarray) -> np.ndarray:
        """Scale parameters from unit cube to original bounds."""
        return self.lower + unit_parameters * (self.upper - self.lower)


class ParameterMapping:
    """Maps between different parameter representations."""

    def __init__(self, parameter_space: ParameterSpace):
        """Initialize parameter mapping."""
        self.parameter_space = parameter_space

    def to_dict(self, parameters: np.ndarray) -> Dict[str, float]:
        """Convert parameter array to dictionary."""
        if hasattr(self.parameter_space, 'names'):
            names = self.parameter_space.names
        else:
            names = [f"param_{i}" for i in range(len(parameters))]

        return dict(zip(names, parameters))

    def from_dict(self, param_dict: Dict[str, float]) -> np.ndarray:
        """Convert parameter dictionary to array."""
        if hasattr(self.parameter_space, 'names'):
            names = self.parameter_space.names
            return np.array([param_dict[name] for name in names])
        else:
            # Assume ordered parameters
            return np.array(list(param_dict.values()))


class ParameterValidator:
    """Validates optimization parameters."""

    def __init__(self, parameter_space: ParameterSpace):
        """Initialize parameter validator."""
        self.parameter_space = parameter_space

    def validate_single(self, parameters: np.ndarray) -> Tuple[bool, str]:
        """Validate single parameter vector."""
        if not isinstance(parameters, np.ndarray):
            return False, "Parameters must be numpy array"

        if parameters.shape[0] != self.parameter_space.dimensions:
            return False, f"Expected {self.parameter_space.dimensions} parameters, got {parameters.shape[0]}"

        if not self.parameter_space.validate(parameters):
            return False, "Parameters outside valid bounds"

        if not np.all(np.isfinite(parameters)):
            return False, "Parameters contain non-finite values"

        return True, "Valid"

    def validate_batch(self, parameters: np.ndarray) -> Tuple[bool, str]:
        """Validate batch of parameter vectors."""
        if parameters.ndim != 2:
            return False, "Batch parameters must be 2D array"

        if parameters.shape[1] != self.parameter_space.dimensions:
            return False, f"Expected {self.parameter_space.dimensions} parameters per sample"

        for i, param_vec in enumerate(parameters):
            valid, message = self.validate_single(param_vec)
            if not valid:
                return False, f"Sample {i}: {message}"

        return True, "All samples valid"