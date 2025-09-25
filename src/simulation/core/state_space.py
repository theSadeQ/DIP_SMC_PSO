#==========================================================================================\\\
#========================== src/simulation/core/state_space.py =========================\\\
#==========================================================================================\\\

"""State-space representation utilities for simulation framework."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


class StateSpaceUtilities:
    """Utilities for state-space system representations and manipulations."""

    @staticmethod
    def validate_state_dimensions(state: np.ndarray, expected_dim: int) -> bool:
        """Validate state vector dimensions.

        Parameters
        ----------
        state : np.ndarray
            State vector to validate
        expected_dim : int
            Expected state dimension

        Returns
        -------
        bool
            True if dimensions match
        """
        if state.ndim == 1:
            return state.shape[0] == expected_dim
        elif state.ndim == 2:
            return state.shape[-1] == expected_dim
        return False

    @staticmethod
    def normalize_state_batch(states: np.ndarray) -> np.ndarray:
        """Normalize state array to consistent batch format.

        Parameters
        ----------
        states : np.ndarray
            State array (1D, 2D, or 3D)

        Returns
        -------
        np.ndarray
            States in batch format (batch_size, time_steps, state_dim)
        """
        states = np.asarray(states)

        if states.ndim == 1:
            # Single state vector -> (1, 1, state_dim)
            return states.reshape(1, 1, -1)
        elif states.ndim == 2:
            # Could be (time_steps, state_dim) or (batch_size, state_dim)
            # Assume it's (time_steps, state_dim) -> (1, time_steps, state_dim)
            return states.reshape(1, states.shape[0], states.shape[1])
        elif states.ndim == 3:
            # Already in batch format
            return states
        else:
            raise ValueError(f"Unsupported state array dimensionality: {states.ndim}")

    @staticmethod
    def extract_state_components(state: np.ndarray,
                                indices: Dict[str, Union[int, slice, List[int]]]) -> Dict[str, np.ndarray]:
        """Extract named state components from state vector.

        Parameters
        ----------
        state : np.ndarray
            State vector or batch of states
        indices : dict
            Mapping of component names to indices/slices

        Returns
        -------
        dict
            Extracted state components
        """
        components = {}
        for name, idx in indices.items():
            if isinstance(idx, int):
                components[name] = state[..., idx]
            elif isinstance(idx, slice):
                components[name] = state[..., idx]
            elif isinstance(idx, list):
                components[name] = state[..., idx]
            else:
                raise ValueError(f"Unsupported index type for {name}: {type(idx)}")

        return components

    @staticmethod
    def compute_state_bounds(states: np.ndarray, percentile: float = 95.0) -> Tuple[np.ndarray, np.ndarray]:
        """Compute state bounds from trajectory data.

        Parameters
        ----------
        states : np.ndarray
            State trajectory data (time_steps, state_dim) or (batch, time_steps, state_dim)
        percentile : float, optional
            Percentile for bounds computation (default: 95.0)

        Returns
        -------
        tuple
            (lower_bounds, upper_bounds) arrays
        """
        # Flatten to (total_samples, state_dim)
        if states.ndim == 3:
            states_flat = states.reshape(-1, states.shape[-1])
        else:
            states_flat = states

        lower_percentile = (100 - percentile) / 2
        upper_percentile = 100 - lower_percentile

        lower_bounds = np.percentile(states_flat, lower_percentile, axis=0)
        upper_bounds = np.percentile(states_flat, upper_percentile, axis=0)

        return lower_bounds, upper_bounds

    @staticmethod
    def compute_energy(state: np.ndarray, mass_matrix: Optional[np.ndarray] = None) -> np.ndarray:
        """Compute system energy from state vector.

        Parameters
        ----------
        state : np.ndarray
            State vector with positions and velocities
        mass_matrix : np.ndarray, optional
            Mass matrix for kinetic energy computation

        Returns
        -------
        np.ndarray
            Total system energy
        """
        # Assume state is [positions, velocities]
        n_states = state.shape[-1] // 2
        velocities = state[..., n_states:]

        if mass_matrix is None:
            # Assume unit mass
            kinetic_energy = 0.5 * np.sum(velocities**2, axis=-1)
        else:
            # M * v^2 / 2
            if velocities.ndim == 1:
                kinetic_energy = 0.5 * velocities.T @ mass_matrix @ velocities
            else:
                kinetic_energy = 0.5 * np.sum(velocities * (mass_matrix @ velocities.T).T, axis=-1)

        # For pendulum systems, add gravitational potential energy
        # This would need to be customized based on specific system
        return kinetic_energy

    @staticmethod
    def linearize_about_equilibrium(dynamics_fn: callable,
                                  equilibrium_state: np.ndarray,
                                  equilibrium_control: np.ndarray,
                                  epsilon: float = 1e-6) -> Tuple[np.ndarray, np.ndarray]:
        """Linearize dynamics about an equilibrium point.

        Parameters
        ----------
        dynamics_fn : callable
            Nonlinear dynamics function f(x, u)
        equilibrium_state : np.ndarray
            Equilibrium state point
        equilibrium_control : np.ndarray
            Equilibrium control input
        epsilon : float, optional
            Finite difference step size

        Returns
        -------
        tuple
            (A_matrix, B_matrix) linear system matrices
        """
        x_eq = equilibrium_state
        u_eq = equilibrium_control

        n_states = len(x_eq)
        n_controls = len(u_eq)

        # Compute A matrix (∂f/∂x)
        A = np.zeros((n_states, n_states))
        for i in range(n_states):
            x_plus = x_eq.copy()
            x_minus = x_eq.copy()
            x_plus[i] += epsilon
            x_minus[i] -= epsilon

            f_plus = dynamics_fn(x_plus, u_eq)
            f_minus = dynamics_fn(x_minus, u_eq)

            A[:, i] = (f_plus - f_minus) / (2 * epsilon)

        # Compute B matrix (∂f/∂u)
        B = np.zeros((n_states, n_controls))
        for i in range(n_controls):
            u_plus = u_eq.copy()
            u_minus = u_eq.copy()
            u_plus[i] += epsilon
            u_minus[i] -= epsilon

            f_plus = dynamics_fn(x_eq, u_plus)
            f_minus = dynamics_fn(x_eq, u_minus)

            B[:, i] = (f_plus - f_minus) / (2 * epsilon)

        return A, B