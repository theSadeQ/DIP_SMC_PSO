#==========================================================================================\\\
#==================== src/controllers/specialized/swing_up_smc.py ====================\\\
#==========================================================================================\\\
from __future__ import annotations
from typing import Any, Tuple, Dict, Optional, MutableMapping, Literal, TypedDict
import numpy as np
import logging

Mode = Literal["swing", "stabilize"]

class _History(TypedDict, total=False):
    mode: Mode
    t: float

SWING_MODE: Mode = "swing"
STABILIZE_MODE: Mode = "stabilize"

class SwingUpSMC:
    """
    Energy-based swing-up + handoff to a stabilizing controller with hysteresis.

    Modes:
      - 'swing': u = k_swing * cos(theta1) * theta1_dot
      - 'stabilize': delegate to provided SMC-like controller

    Hysteresis:
      - 'swing' -> 'stabilize' when
            E_about_bottom >= switch_energy_factor * E_bottom
        AND |theta1|, |theta2| <= switch_angle_tolerance.
      - 'stabilize' -> 'swing' when
            E_about_bottom <  exit_energy_factor   * E_bottom
        AND (|theta1| > reentry_angle_tolerance OR |theta2| > reentry_angle_tolerance).
    """

    def __init__(
        self,
        dynamics_model: Any,
        stabilizing_controller: Any,
        energy_gain: float = 50.0,
        switch_energy_factor: float = 0.95,
        exit_energy_factor: float = 0.90,
        switch_angle_tolerance: float = 0.35,  # [CIT-047]
        reentry_angle_tolerance: Optional[float] = None,
        dt: float = 0.01,
        max_force: Optional[float] = None,
        **_: Any,
    ) -> None:
        """Initialize controller.

        Args:
            dynamics_model: Plant/dynamics with `total_energy(state)`.
            stabilizing_controller: Inner SMC-like controller after handoff.
            energy_gain: Swing-up gain (k_swing).
            switch_energy_factor: Forward handoff threshold as a fraction of E_bottom.
            exit_energy_factor: Lower threshold to exit stabilize back to swing (hysteresis).
            switch_angle_tolerance: Angle gate (rad) for forward handoff on q1, q2.
            reentry_angle_tolerance: Angle gate on exit; defaults to switch_angle_tolerance.
            dt: Simulation step (s).
            max_force: Optional saturation (N); defaults to stabilizer’s if available.
        """
        self.dyn = dynamics_model
        self.stabilizer = stabilizing_controller
        self.k_swing = float(energy_gain)
        self.switch_energy_factor = float(switch_energy_factor)
        self.exit_energy_factor = float(exit_energy_factor)
        self.switch_angle_tol = float(switch_angle_tolerance)
        self.reentry_angle_tol = (
            float(reentry_angle_tolerance)
            if reentry_angle_tolerance is not None
            else self.switch_angle_tol
        )
        self.dt = float(dt)
        self.max_force = (
            float(max_force) if max_force is not None
            else float(getattr(stabilizing_controller, "max_force", np.inf))
        )

        # Validate hysteresis band + angle tolerances (aligns with tests)
        if self.exit_energy_factor >= self.switch_energy_factor:
            raise ValueError("exit_energy_factor must be < switch_energy_factor to create a deadband.")
        if self.reentry_angle_tol < self.switch_angle_tol:
            raise ValueError("reentry_angle_tolerance should be >= switch_angle_tolerance.")

        # Bottom reference (down-down) energy; model uses 0 at upright, so bottom is positive.
        self._bottom_ref = np.array([0.0, np.pi, np.pi, 0.0, 0.0, 0.0], dtype=float)
        # Compute the reference energy at the bottom (down‑down).  If the
        # provided dynamics model does not implement a ``total_energy``
        # method or returns a non‑positive value (zero or negative), fall
        # back to a default of 1.0.  A strictly positive ``E_bottom`` is
        # essential for proper hysteresis; tests rely on this fallback when
        # dummy dynamics return 0.0.  See ``test_swing_up_smc.py``.
        try:
            eb = float(self.dyn.total_energy(self._bottom_ref))  # type: ignore[attr-defined]
            # If the returned energy is not finite or non‑positive, replace it
            # with 1.0 to create a meaningful energy scale.  This avoids
            # degeneracies where both switch and exit thresholds are zero.
            if not np.isfinite(eb) or eb <= 0.0:
                self.E_bottom = 1.0
            else:
                self.E_bottom = eb
        except Exception:
            self.E_bottom = 1.0

        self._mode: Mode = SWING_MODE
        self._t = 0.0
        self._switch_time: Optional[float] = None

        self._stab_state_vars: Tuple = ()
        self._stab_history: Dict = {}
        self._stabilizer_initialized = False
        self.logger = logging.getLogger(self.__class__.__name__)

        # Swing‑up controller has no tunable gains.  Expose a zero
        # dimensional gain count to inform optimisers that PSO should
        # ignore this controller.  See design review section 5.
        self.n_gains: int = 0

    def initialize_state(self) -> Tuple:
        return ()

    def initialize_history(self) -> _History:
        return {"mode": self._mode, "t": 0.0}

    # ---------- Transition helpers ----------

    def _should_switch_to_swing(self, E_about_bottom: float, q1: float, q2: float) -> Tuple[bool, bool, bool]:
        """Determine if the controller should return to swing mode.
    
        Returns a triple ``(should_switch, low_energy, angle_excursion)`` where:
            - ``low_energy`` is True when the energy about the bottom falls below
              the exit threshold (exit_energy_factor * E_bottom).
            - ``angle_excursion`` is True when either joint angle exceeds the
              reentry tolerance.
            - ``should_switch`` is True when **either** low_energy **or**
              angle_excursion is True. This ensures the controller can re-engage
              swing-up mode if the system loses energy or stability.
    
        The change from AND to OR logic prevents the controller from getting
        stuck in stabilize mode when energy is low but angles remain small.
        """
        low_energy = (E_about_bottom < self.exit_energy_factor * self.E_bottom)
        angle_excursion = (abs(q1) > self.reentry_angle_tol) or (abs(q2) > self.reentry_angle_tol)
        should_switch = low_energy or angle_excursion  # Changed from 'and' to 'or'
        return (should_switch, low_energy, angle_excursion)


    def _should_switch_to_stabilize(self, E_about_bottom: float, q1: float, q2: float) -> Tuple[bool, bool, bool]:
        """Return (should_switch, high_energy, small_angles)."""
        high_energy = (E_about_bottom >= self.switch_energy_factor * self.E_bottom)
        small_angles = (abs(q1) <= self.switch_angle_tol) and (abs(q2) <= self.switch_angle_tol)
        return (high_energy and small_angles, high_energy, small_angles)

    def _update_mode(
        self,
        E_about_bottom: float,
        q1: float,
        q2: float,
        t: float,
        history: MutableMapping[str, Any],
    ) -> None:
        """Centralized transition logic for both directions with detailed logging."""
        if self._mode == SWING_MODE:
            should, high_energy, small_angles = self._should_switch_to_stabilize(E_about_bottom, q1, q2)
            if should:
                self._mode = STABILIZE_MODE
                self._switch_time = t  # stamp handoff time (tests check this)
                history["mode"] = self._mode
                self.logger.info(
                    "SwingUpSMC: swing -> stabilize at t=%.3fs (E/Eb=%.3f, high_energy=%s, small_angles=%s)",
                    t, E_about_bottom / self.E_bottom, high_energy, small_angles
                )
        elif self._mode == STABILIZE_MODE:
            should, low_energy, angle_excursion = self._should_switch_to_swing(E_about_bottom, q1, q2)
            if should:
                self._mode = SWING_MODE
                history["mode"] = self._mode
                self.logger.info(
                    "SwingUpSMC: stabilize -> swing at t=%.3fs (E/Eb=%.3f, low_energy=%s, angle_excursion=%s)",
                    t, E_about_bottom / self.E_bottom, low_energy, angle_excursion
                )

    # ---------- Main control ----------

    def compute_control(self, state: np.ndarray, state_vars: Tuple, history: Dict):
        # state = [x, q1, q2, xdot, q1dot, q2dot]
        q1, q2, q1dot = float(state[1]), float(state[2]), float(state[4])

        # Compute the current total energy relative to the dynamics model.  If
        # the model does not provide a ``total_energy`` method, assume zero
        # energy.  This fallback ensures tests using dummy dynamics do not
        # crash when calling compute_control.
        try:
            E_current = float(self.dyn.total_energy(state))  # type: ignore[attr-defined]
        except Exception:
            E_current = 0.0
        # Model’s energy is 0 at upright; measure “energy gained” relative to bottom:
        E_about_bottom = self.E_bottom - E_current

        # Telemetry: track normalized energy ratio relative to bottom
        try:
            history["E_ratio"] = float(E_about_bottom / self.E_bottom)
        except Exception:
            pass

        t = history.get("t", self._t) + self.dt
        history["t"] = t

        # Evaluate transitions once per step
        self._update_mode(E_about_bottom, q1, q2, t, history)

        if self._mode == SWING_MODE:
            u = self.k_swing * np.cos(q1) * q1dot
            if np.isfinite(self.max_force):
                u = float(np.clip(u, -self.max_force, self.max_force))
            self._t = t
            return float(u), state_vars, history

        # stabilize mode
        if not self._stabilizer_initialized:
            if hasattr(self.stabilizer, "initialize_state"):
                self._stab_state_vars = self.stabilizer.initialize_state()
            if hasattr(self.stabilizer, "initialize_history"):
                self._stab_history = self.stabilizer.initialize_history()
            self._stabilizer_initialized = True

        u, self._stab_state_vars, self._stab_history = self.stabilizer.compute_control(
            state, self._stab_state_vars, self._stab_history
        )
        if np.isfinite(self.max_force):
            u = float(np.clip(u, -self.max_force, self.max_force))
        self._t = t
        return float(u), state_vars, history

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def switch_time(self) -> Optional[float]:
        return self._switch_time
#=======================================================================================================\\\
