#==========================================================================================\\\
#============================= src/fault_detection/fdi.py =============================\\\
#==========================================================================================\\\
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Protocol
import numpy as np
import logging

class DynamicsProtocol(Protocol):
    """Protocol defining the expected interface for dynamics models."""
    def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        """Advance the system dynamics by one timestep."""
        ...

@dataclass
class FDIsystem:
    """
    Lightweight, modular Fault Detection and Isolation (FDI) system with
    optional adaptive thresholds and CUSUM drift detection.

    A residual is formed by comparing the one‑step state prediction from a
    dynamics model with the actual measurement.  If an extended Kalman
    filter (EKF) is available it may provide a more statistically
    informed residual (future enhancement).  The residual norm is
    monitored against a threshold; persistent violations indicate a fault.

    To improve robustness the detector can adapt its threshold based on
    recent residual statistics and can optionally employ a cumulative sum
    (CUSUM) statistic to detect slow drifts.  Adaptive thresholding has
    been shown to enhance the robustness of fault diagnosis by
    automatically adjusting to operating conditions【218697608892619†L682-L687】.  CUSUM
    methods accumulate deviations from a reference and are sensitive to
    faint changes【675426604190490†L699-L722】; however the choice of threshold and
    reference value is critical to avoid false alarms【675426604190490†L746-L752】.

    Attributes
    ----------
    residual_threshold : float
        Base threshold for the residual norm.  Used when adaptive
        thresholding is disabled or insufficient samples are available.
    persistence_counter : int
        Number of consecutive threshold violations required to declare a
        fault.  Helps filter sporadic spikes.
    use_ekf_residual : bool
        Placeholder for future EKF innovation residual.
    residual_states : list[int]
        Indices of state variables to include in the residual.
    residual_weights : list[float], optional
        Optional weights applied elementwise to the residual before
        computing the norm.
    adaptive : bool
        Enable adaptive thresholding.  When True the threshold is
        computed as ``mu + threshold_factor * sigma`` over the last
        ``window_size`` residuals.  This dynamic threshold adjusts to
        changing operating conditions【218697608892619†L682-L687】.
    window_size : int
        Number of recent residuals used to estimate the mean and
        standard deviation for adaptive thresholding.
    threshold_factor : float
        Multiplicative factor applied to the standard deviation when
        computing the adaptive threshold.  Larger values reduce
        sensitivity.
    cusum_enabled : bool
        Enable simple CUSUM drift detection.  When True the detector
        accumulates deviations of the residual norm from its running
        average and compares the sum against ``cusum_threshold`` to
        detect slow drifts【675426604190490†L699-L722】.
    cusum_threshold : float
        Threshold for the cumulative sum.  When the cumulative sum
        exceeds this value a fault is declared.

    Notes
    -----
    * Adaptive thresholding and CUSUM can be enabled independently.
    * When both methods are enabled the residual must exceed either
      the adaptive threshold persistently or the CUSUM threshold to
      trigger a fault.
    * The FDI system reports status only ("OK"/"FAULT") and does not modify
      the control command path; external supervisors decide safe-state actions.  # [CIT-064]
    """

    residual_threshold: float = 0.5  # [CIT-048]
    persistence_counter: int = 10  # [CIT-048]
    use_ekf_residual: bool = False
    residual_states: List[int] = field(default_factory=lambda: [0, 1, 2])
    residual_weights: Optional[List[float]] = None
    adaptive: bool = False
    window_size: int = 50  # [CIT-049]
    threshold_factor: float = 3.0  # [CIT-049]
    cusum_enabled: bool = False
    cusum_threshold: float = 5.0  # [CIT-049]

    # Internal state
    _counter: int = field(default=0, repr=False, init=False)
    _last_state: Optional[np.ndarray] = field(default=None, repr=False, init=False)
    tripped_at: Optional[float] = field(default=None, repr=False, init=False)
    # For adaptive thresholding and CUSUM
    _residual_window: List[float] = field(default_factory=list, repr=False, init=False)
    _cusum: float = field(default=0.0, repr=False, init=False)

    # History for plotting/analysis
    times: List[float] = field(default_factory=list, repr=False, init=False)
    residuals: List[float] = field(default_factory=list, repr=False, init=False)

    def check(
        self,
        t: float,
        meas: np.ndarray,
        u: float,
        dt: float,
        dynamics_model: DynamicsProtocol,
    ) -> Tuple[str, float]:
        """
        Check for a fault at the current time step.
        
        Args:
            t: Current simulation time
            meas: Current state measurement
            u: Control input applied
            dt: Time step
            dynamics_model: Model with step(state, u, dt) method for prediction
            
        Returns:
            Tuple of (status, residual_norm) where status is "OK" or "FAULT"
        """
        # Validate time step.  A non‑positive dt invalidates the residual
        # computation and can produce spurious faults.  Raise an error
        # rather than silently accepting a zero or negative sampling
        # interval【738473614585036†L239-L256】.
        if dt <= 0.0:
            raise ValueError("dt must be positive for FDI residual computation.")

        if self.tripped_at is not None:
            return "FAULT", np.inf

        if self._last_state is None:
            self._last_state = meas.copy()
            return "OK", 0.0

        # One-step prediction using the dynamics model
        try:
            predicted_state = dynamics_model.step(self._last_state, u, dt)
            
            # Check for numerical issues in prediction
            if not np.all(np.isfinite(predicted_state)):
                logging.warning(
                    f"FDI check at t={t:.2f}s: dynamics model returned non-finite values "
                    f"(nan or inf). Skipping residual computation."
                )
                return "OK", 0.0
                
        except Exception as e:
            # If model fails, cannot compute residual; assume OK for now but log it
            logging.warning(
                f"FDI check at t={t:.2f}s failed: dynamics model step raised "
                f"{type(e).__name__}: {str(e)}. Skipping residual computation."
            )
            return "OK", 0.0

        # Residual is the difference between prediction and measurement
        residual = meas - predicted_state

        # Compute weighted norm using specified indices and optional weights.
        # Weighted residuals allow tuning the sensitivity of the detector to
        # individual states.  When no weights are provided a standard 2‑norm is
        # used on the selected indices.  If an index error occurs fallback
        # gracefully to the full residual norm and log the error.
        try:
            sub = residual[self.residual_states]
            weights = self.residual_weights
            if weights is not None:
                # Multiply each residual component by its weight prior to
                # computing the Euclidean norm.  Weights must match
                # residual_states in length (validated in config).
                sub = sub * np.asarray(weights, dtype=float)
            residual_norm = float(np.linalg.norm(sub))
        except Exception:
            logging.error(
                f"FDI configuration error: residual_states {self.residual_states} or weights invalid "
                f"for state vector of size {len(residual)}"
            )
            residual_norm = float(np.linalg.norm(residual))

        # Store history for analysis
        self.times.append(t)
        self.residuals.append(residual_norm)

        # Append to residual window for adaptive thresholding
        self._residual_window.append(residual_norm)
        if len(self._residual_window) > self.window_size:
            self._residual_window.pop(0)

        # Compute adaptive threshold when enabled and enough samples collected
        dynamic_threshold = self.residual_threshold
        mu = None
        sigma = None
        if self.adaptive and len(self._residual_window) >= self.window_size:
            mu = float(np.mean(self._residual_window))
            sigma = float(np.std(self._residual_window))
            # Avoid zero variance; if sigma is extremely small fall back to
            # base threshold to prevent division by zero
            if sigma > 1e-12:
                dynamic_threshold = mu + self.threshold_factor * sigma
            else:
                dynamic_threshold = mu

        # CUSUM drift detection: update cumulative sum of deviations
        if self.cusum_enabled:
            # Use current mean estimate if available, otherwise base threshold
            ref = mu if (self.adaptive and mu is not None) else self.residual_threshold
            # Deviation from reference; negative deviations are clipped at zero
            self._cusum = max(0.0, self._cusum + (residual_norm - ref))
            if self._cusum > self.cusum_threshold:
                self.tripped_at = t
                logging.info(
                    f"FDI CUSUM fault detected at t={t:.2f}s (cusum={self._cusum:.4f} > threshold={self.cusum_threshold})"
                )
                return "FAULT", residual_norm

        # Update persistence counter using dynamic threshold
        if residual_norm > dynamic_threshold:
            self._counter += 1
            # Don't update _last_state when fault is detected to prevent
            # corrupted measurements from becoming the prediction base
        else:
            self._counter = 0  # Reset on any good measurement
            # Only update state when measurement appears good
            self._last_state = meas.copy()

        # Check for fault condition based on persistence count
        if self._counter >= self.persistence_counter:
            self.tripped_at = t
            threshold_used = dynamic_threshold
            logging.info(
                f"FDI fault detected at t={t:.2f}s after {self._counter} consecutive "
                f"violations (residual_norm={residual_norm:.4f} > threshold={threshold_used:.4f})"
            )
            return "FAULT", residual_norm

        return "OK", residual_norm


class FaultDetectionInterface(Protocol):
    """
    Protocol defining the interface for fault detection systems.

    This interface ensures compatibility across different fault detection
    implementations and provides a standard API for testing and usage.
    """

    def check(
        self,
        t: float,
        meas: np.ndarray,
        u: float,
        dt: float,
        dynamics_model: DynamicsProtocol,
    ) -> Tuple[str, float]:
        """
        Check for a fault at the current time step.

        Args:
            t: Current simulation time
            meas: Current state measurement
            u: Control input applied
            dt: Time step
            dynamics_model: Model with step(state, u, dt) method for prediction

        Returns:
            Tuple of (status, residual_norm) where status is "OK" or "FAULT"
        """
        ...


# Verify that FDIsystem implements the interface
def _verify_interface() -> None:
    """Verify that FDIsystem correctly implements FaultDetectionInterface."""
    # This function exists to ensure type compatibility at import time
    _: FaultDetectionInterface = FDIsystem()  # type: ignore


#===================================================================================\\\
