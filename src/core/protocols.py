#==========================================================================================\\
#================================ src/core/protocols.py ===============================\\
#==========================================================================================\\
from typing import Protocol, Tuple, Dict, Any, Optional, Union
import numpy as np

class ControllerProtocol(Protocol):
    def validate_gains(self, gains_b: 'np.ndarray') -> 'np.ndarray':
        """
        Optional fast, vectorized validity check for controller gain sets.
        Returns a boolean mask of shape (B,) where True means the corresponding
        particle's gains are valid and should be simulated.
        Implementations should be pure and inexpensive (no simulation).
        """
        ...

    """Protocol defining the interface for controllers."""
    
    def compute_control(
        self, 
        state: np.ndarray, 
        state_vars: Optional[Any] = None, 
        history: Optional[Dict[str, Any]] = None
    ) -> Union[float, Tuple[float, Any, Dict[str, Any]], Tuple[float, Any, Dict[str, Any], Any]]:
        """Compute control action given current state."""
        ...
    
    def initialize_state(self) -> Any:
        """Initialize internal state variables."""
        ...
    
    def initialize_history(self) -> Dict[str, Any]:
        """Initialize history tracking."""
        ...

class DynamicsProtocol(Protocol):
    """Protocol defining the interface for dynamics models."""
    
    state_dim: int
    
    def step(self, state: np.ndarray, control: float, dt: float) -> np.ndarray:
        """Step the dynamics forward by dt."""
        ...
