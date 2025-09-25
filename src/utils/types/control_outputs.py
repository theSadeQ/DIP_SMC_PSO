#==========================================================================================\\
#============================ src/utils/control_outputs.py ============================\\
#==========================================================================================\\
"""
Structured return types for controllers.

This module defines a collection of `NamedTuple` classes that formalise the
output contract of the various controller classes in this project.  Each
controller returns an instance of a corresponding named tuple rather than
a bare tuple.  Returning a named tuple preserves backward compatibility
with existing code that expects a tuple (because a named tuple inherits
from ``tuple``) while also exposing descriptive attribute names to clarify
the meaning of each element.  Explicit interfaces act as contracts
between caller and callee: the client must satisfy preconditions and
may rely on the supplier to guarantee postconditions.  As noted in
interface‑based programming literature, the tighter the contract (for
example through explicit return types), the less freedom the
implementation has to deviate from expectations【738473614585036†L239-L256】.  By
codifying controller outputs in named tuples, we communicate the
structure of the returned data unambiguously and reduce the risk of
misinterpretation by downstream components.

References
----------
- F. Steimann and P. Mayer, “Patterns of interface‑based programming,” *Journal
  of Object Technology*, vol. 4, no. 7, pp. 75–94, 2005.  The authors view
  interfaces as contracts between a client and a supplier, emphasising that
  clear preconditions and postconditions constrain the behaviour of
  implementations【738473614585036†L239-L256】.  Encoding controller outputs as named
  tuples tightens the return contract and prevents ambiguous slicing or
  misuse.
"""

from __future__ import annotations

from typing import NamedTuple, Tuple, Dict, Any


class ClassicalSMCOutput(NamedTuple):
    """Return type for :class:`classical_smc.ClassicalSMC.compute_control`.

    Parameters
    ----------
    u : float
        The saturated control input applied to the actuator (N).
    state : Tuple[(), ...]
        Tuple representing internal controller state.  Classical SMC has
        no internal state, so this is always an empty tuple.
    history : Dict[str, Any]
        A history dictionary used to record intermediate variables for
        debugging or plotting.  May be empty.
    """

    u: float
    state: Tuple[Any, ...]
    history: Dict[str, Any]


class AdaptiveSMCOutput(NamedTuple):
    """Return type for :class:`adaptive_smc.AdaptiveSMC.compute_control`.

    Parameters
    ----------
    u : float
        The saturated control input (N).
    state : Tuple[float, ...]
        A tuple containing the updated integrator or adaptation states
        returned by the controller.  The length of this tuple depends on
        the controller implementation (e.g., leak integrator value).
    history : Dict[str, Any]
        Dictionary capturing intermediate variables and trajectories.
    sigma : float
        Current sliding surface value.  Exposing sigma allows the caller
        to monitor the switching surface and verify sliding mode
        convergence.  Providing it here rather than re‑computing avoids
        redundant calculations.
    """

    u: float
    state: Tuple[float, ...]
    history: Dict[str, Any]
    sigma: float


class STAOutput(NamedTuple):
    """Return type for super‑twisting controllers.

    Parameters
    ----------
    u : float
        The bounded control input (N).
    state : Tuple[float, float]
        A tuple containing the auxiliary integrator states (e.g., ``z`` and
        ``sigma``).  These states evolve according to the super‑twisting
        algorithm and are needed to resume control in the next time step.
    history : Dict[str, Any]
        History information for diagnostics and plotting.
    """

    u: float
    state: Tuple[float, ...]
    history: Dict[str, Any]


class HybridSTAOutput(NamedTuple):
    """Return type for :class:`hybrid_adaptive_sta_smc.HybridAdaptiveSTASMC.compute_control`.

    Parameters
    ----------
    u : float
        The saturated control input.
    state : Tuple[float, float, float]
        Tuple containing the adaptive gains and integral state, e.g.,
        ``(k1, k2, u_int)``.
    history : Dict[str, Any]
        Dictionary capturing trajectories of gains, the integral term
        and the sliding surface.
    sigma : float
        Current sliding surface value.
    """

    u: float
    state: Tuple[float, ...]
    history: Dict[str, Any]
    sigma: float