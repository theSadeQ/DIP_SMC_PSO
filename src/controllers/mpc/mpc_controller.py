#==========================================================================================\\\
#========================== src/controllers/mpc/mpc_controller.py =======================\\\
#==========================================================================================\\\
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import numpy as np
# cvxpy is an optional dependency.  Attempt to import it, but allow
# the module to be imported even when cvxpy is unavailable.  When
# ``cp`` is ``None`` the controller falls back to a simple linear
# feedback law in ``compute_control``.
try:
    import cvxpy as cp  # type: ignore
except Exception:
    cp = None  # type: ignore
from scipy.linalg import expm

try:
    from src.core.dynamics import DoubleInvertedPendulum  # type: ignore
except Exception:
    try:
        from core.dynamics import DoubleInvertedPendulum  # type: ignore
    except Exception:
        DoubleInvertedPendulum = object  # type: ignore

try:
    from src.controllers.classic_smc import ClassicalSMC  # type: ignore
except Exception:
    try:
        from controllers.classic_smc import ClassicalSMC  # type: ignore
    except Exception:
        ClassicalSMC = None  # type: ignore

logger = logging.getLogger(__name__)


def _call_f(dyn: DoubleInvertedPendulum, x: np.ndarray, u: float | np.ndarray) -> np.ndarray:
    """
    Robustly call continuous‑time dynamics: xdot = f(x,u)
    Supports several common method names; last‑resort: finite‑difference via step(., dt).
    """
    u = float(np.atleast_1d(u).astype(float)[0])
    for name in ("f", "continuous_dynamics", "dynamics", "ode", "state_derivative"):
        if hasattr(dyn, name):
            fn = getattr(dyn, name)
            try:
                xdot = fn(np.asarray(x, dtype=float), float(u))
                return np.asarray(xdot, dtype=float)
            except TypeError:
                # Signature mismatch; try next option
                continue

    # Last resort: use a very small step to approximate derivative
    if hasattr(dyn, "step"):
        try:
            dt = 1e-6
            x = np.asarray(x, dtype=float)
            x2 = dyn.step(x, float(u), dt)  # type: ignore
            return (np.asarray(x2, dtype=float) - x) / dt
        except Exception:
            pass

    raise RuntimeError(
        "Cannot evaluate dynamics; expected a method like f(x,u)->xdot or step(x,u,dt)."
    )


def _numeric_linearize_continuous(
    dyn: DoubleInvertedPendulum,
    x_eq: np.ndarray,
    u_eq: float,
    eps: float = 1e-6,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Finite‑difference linearization around (x_eq, u_eq) using a central
    difference with adaptive perturbations.

    A continuous‑time dynamics function ``f(x,u)`` is linearised as
    ``xdot ≈ A (x - x_eq) + B (u - u_eq) + f(x_eq,u_eq)``.  Central
    differences are second‑order accurate and reduce truncation error
    relative to one‑sided (forward) differences【738473614585036†L239-L256】.
    The perturbation for each state is scaled to the magnitude of
    ``x_eq[i]`` with a floor ``eps``.  This adaptive scaling balances
    rounding and truncation errors【738473614585036†L239-L256】.

    Parameters
    ----------
    dyn : DoubleInvertedPendulum
        The continuous‑time dynamics model.
    x_eq : np.ndarray
        Equilibrium state about which to linearise.
    u_eq : float
        Equilibrium input about which to linearise.
    eps : float, optional
        Minimum perturbation used when scaling the finite difference.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        Continuous‑time state matrix A and input matrix B.
    """
    x_eq = np.asarray(x_eq, dtype=float)
    n = x_eq.size
    f0 = _call_f(dyn, x_eq, u_eq)
    A = np.zeros((n, n), dtype=float)
    # Central difference for each state dimension with adaptive step [CITE:IntroFDM §2.4]
    for i in range(n):
        # Perturbation proportional to the magnitude of x_eq[i] or unity
        delta = max(eps, 1e-4 * max(abs(x_eq[i]), 1.0))
        dx = np.zeros(n, dtype=float)
        dx[i] = delta
        f_plus = _call_f(dyn, x_eq + dx, u_eq)
        f_minus = _call_f(dyn, x_eq - dx, u_eq)
        A[:, i] = (f_plus - f_minus) / (2.0 * delta)
    # Single‑input system: adaptive perturbation for input
    du = max(eps, 1e-4 * max(abs(u_eq), 1.0))
    f_plus = _call_f(dyn, x_eq, u_eq + du)
    f_minus = _call_f(dyn, x_eq, u_eq - du)
    B = ((f_plus - f_minus) / (2.0 * du)).reshape(n, 1)
    return A, B


def _discretize_forward_euler(Ac: np.ndarray, Bc: np.ndarray, dt: float) -> Tuple[np.ndarray, np.ndarray]:
    """Simple forward‑Euler discretization (stable for small dt)."""
    n = Ac.shape[0]
    Ad = np.eye(n) + Ac * dt
    Bd = Bc * dt
    return Ad, Bd


def _discretize_exact(Ac: np.ndarray, Bc: np.ndarray, dt: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Zero‑order hold (exact) discretization using matrix exponential.
    """
    n = Ac.shape[0]
    M = np.zeros((n + 1, n + 1), dtype=float)
    M[:n, :n] = Ac
    M[:n, n:] = Bc
    Md = expm(M * dt)
    Ad = Md[:n, :n]
    Bd = Md[:n, n:].reshape(n, 1)
    return Ad, Bd


@dataclass
class MPCWeights:
    q_x: float = 1.0            # position
    q_theta: float = 10.0       # angles (each)
    q_xdot: float = 0.1         # cart velocity
    q_thetadot: float = 0.5     # angle rates (each)
    r_u: float = 1e-2           # input effort


class MPCController:
    """
    Linear MPC for the double inverted pendulum on a cart.

    State (nx=6): [x, th1, th2, xdot, th1dot, th2dot]
    Input (nu=1): u = cart force
    """

    def __init__(
        self,
        dynamics_model: DoubleInvertedPendulum,
        horizon: int = 20,
        dt: float = 0.02,
        weights: Optional[MPCWeights] = None,
        max_force: float = 20.0,
        max_cart_pos: float = 2.4,
        max_theta_dev: float = 0.5,
        use_exact_discretization: bool = True,
        *,
        fallback_smc_gains: Optional[List[float]] = None,
        fallback_pd_gains: Optional[Tuple[float, float]] = None,
        # Optional boundary layer for the fallback SMC controller.  When
        # provided this value overrides the default boundary layer used
        # by the sliding‑mode fallback.  If not supplied the layer is
        # chosen proportional to the sampling period ``dt``.  A positive
        # boundary layer mitigates chattering but introduces steady‑state
        # error【634903324123444†L631-L639】.  Scaling the layer with dt keeps
        # the controller robust across different sampling rates.
        fallback_boundary_layer: Optional[float] = None,
        # Optional output slew rate limit |du|/step for chattering/jerk reduction.
        # When provided, the returned control is rate-limited relative to the
        # previous output. Units: N per control step.
        max_du: Optional[float] = None,
    ) -> None:
        self.model = dynamics_model
        self.N = int(horizon)
        self.dt = float(dt)
        self.max_force = float(max_force)
        self.max_cart_pos = float(max_cart_pos)
        # Allow None to signal use of the default bound (0.5 radians)
        if max_theta_dev is None:
            self.max_theta_dev = 0.5
        else:
            self.max_theta_dev = float(max_theta_dev)

        self.weights = weights if weights is not None else MPCWeights()
        self._ref_fn: Optional[Callable[[float], np.ndarray]] = None

        # Warm start storage for the input sequence (size N)
        self._U_prev = np.zeros(self.N, dtype=float)
        self._last_u_out: float = 0.0
        self._max_du: Optional[float] = max_du

        # Create a safe fallback controller used if the QP fails.  Users may
        # provide custom SMC or PD gains via the ``fallback_smc_gains``
        # and ``fallback_pd_gains`` constructor arguments.  When custom
        # SMC gains are provided the controller will attempt to
        # instantiate a ClassicalSMC with those gains.  If the
        # instantiation fails or no SMC gains are provided, the
        # controller will fall back to a simple PD law using the
        # provided (kp, kd) tuple or the default values (20.0, 5.0).
        self._fallback = None
        self._fb_state = ()
        self._fb_history = {}
        # Determine PD gains early; if fallback_pd_gains is provided,
        # ensure it contains exactly two numeric values.
        self._pd_kp, self._pd_kd = (20.0, 5.0)
        if fallback_pd_gains is not None:
            try:
                kp, kd = float(fallback_pd_gains[0]), float(fallback_pd_gains[1])
                self._pd_kp, self._pd_kd = kp, kd
            except Exception:
                logger.warning(
                    "MPCController: invalid fallback_pd_gains provided; using default PD gains (20.0, 5.0)."
                )
        # Determine the boundary layer for the fallback SMC.  A user‑supplied
        # value overrides the default.  Otherwise scale a baseline layer
        # (0.05) with the sampling period to maintain chattering reduction
        # across time steps【634903324123444†L631-L639】.
        bl = None
        try:
            if fallback_boundary_layer is not None:
                bl = float(fallback_boundary_layer)
            else:
                # Base layer of 0.05 scaled by max(1, dt) to avoid vanishing
                bl = 0.05 * max(1.0, self.dt)
        except Exception:
            bl = 0.05 * max(1.0, self.dt)

        # Attempt to build the SMC fallback if gains and dependencies are available
        if fallback_smc_gains is not None and ClassicalSMC is not None:
            try:
                self._fallback = ClassicalSMC(
                    gains=[float(g) for g in fallback_smc_gains],
                    max_force=self.max_force,
                    boundary_layer=bl,
                    dynamics_model=self.model,
                )
            except Exception:
                logger.warning(
                    "MPCController: failed to instantiate fallback ClassicalSMC with provided gains; falling back to PD."
                )
                self._fallback = None
        elif ClassicalSMC is not None:
            # Use built‑in conservative gains when no custom gains are given
            try:
                self._fallback = ClassicalSMC(
                    gains=[6.0, 6.0, 12.0, 12.0, 60.0, 1.5],
                    max_force=self.max_force,
                    boundary_layer=bl,
                    dynamics_model=self.model,
                )
            except Exception:
                # If SMC cannot be constructed, leave fallback as None
                self._fallback = None

        # Choose discretization method
        self._discretize = _discretize_exact if use_exact_discretization else _discretize_forward_euler


    # -- Public API --------------------------------------------------------------------------

    def set_reference(self, ref_fn: Callable[[float], np.ndarray]) -> None:
        """
        Set a reference function ref_fn(t) -> R^6 (desired state).
        """
        self._ref_fn = ref_fn

    def __call__(self, t: float, x: np.ndarray) -> float:
        return self.compute_control(t, x)

    # -- Core --------------------------------------------------------------------------------

    def compute_control(self, t: float, x0: np.ndarray) -> float:
        """
        Build and solve a linear MPC QP around the current state x0 at time t.
        On solver failure/infeasibility, return a safe, angle-aware fallback control.
        """
        x0 = np.asarray(x0, dtype=float).reshape(-1)
        assert x0.shape[0] == 6, "Expected state dimension 6: [x, th1, th2, xdot, th1dot, th2dot]"

        # If cvxpy is unavailable, skip the optimization and compute a
        # simple linear feedback control.  Use proportional gains derived
        # from the weight object to regulate position, angles and rates
        # about the upright equilibrium.  The equilibrium is at x=0,
        # theta1=pi, theta2=pi, and zero velocities.  Clip the result
        # to respect the actuator limits.  This fallback provides a
        # deterministic control signal without depending on cvxpy.
        if cp is None:
            # Compute errors relative to the desired upright state
            x_err = float(x0[0])
            th1_err = float(x0[1] - np.pi)
            th2_err = float(x0[2] - np.pi)
            xdot = float(x0[3])
            th1dot = float(x0[4])
            th2dot = float(x0[5])
            w = self.weights if self.weights is not None else MPCWeights()
            # Simple proportional/derivative control using weights as gains
            u_fb = -(
                w.q_x * x_err
                + w.q_theta * (th1_err + th2_err)
                + w.q_xdot * xdot
                + w.q_thetadot * (th1dot + th2dot)
            )
            u_cmd = float(np.clip(u_fb, -self.max_force, self.max_force))
            # Optional slew rate limit
            if self._max_du is not None:
                du = np.clip(u_cmd - self._last_u_out, -self._max_du, self._max_du)
                u_cmd = float(self._last_u_out + du)
            self._last_u_out = u_cmd
            return u_cmd

        # Reference trajectory
        if self._ref_fn is not None:
            x_ref0 = np.asarray(self._ref_fn(t), dtype=float).reshape(-1)
            if x_ref0.size != 6:
                raise ValueError("Reference function must return a 6D state.")
            # Build a piecewise-constant ref for horizon
            Xref = np.tile(x_ref0.reshape(6, 1), (1, self.N + 1))
        else:
            # Default upright at current x target (0 pos) unless user set ref
            Xref = np.zeros((6, self.N + 1), dtype=float)
            Xref[1, :] = np.pi
            Xref[2, :] = np.pi

        # Linearize continuous dynamics around (x0, u=0), then discretize
        try:
            Ac, Bc = _numeric_linearize_continuous(self.model, x0, 0.0, eps=1e-6)
            Ad, Bd = self._discretize(Ac, Bc, self.dt)
        except Exception as e:
            logger.warning("Linearization/discretization failed (%s). Falling back.", e)
            return self._safe_fallback(x0)

        nx, nu = 6, 1
        N = self.N

        # Decision variables
        X = cp.Variable((nx, N + 1))
        U = cp.Variable((nu, N))

        # Cost weights
        w = self.weights
        Q = np.diag([w.q_x, w.q_theta, w.q_theta, w.q_xdot, w.q_thetadot, w.q_thetadot])
        R = np.array([[w.r_u]], dtype=float)

        # Objective and constraints
        obj = 0
        cons = [X[:, 0] == x0]

        for k in range(N):
            # Dynamics
            cons += [X[:, k + 1] == Ad @ X[:, k] + Bd @ U[:, k]]

            # Input constraint
            cons += [cp.abs(U[0, k]) <= self.max_force]

            # Track state to reference at each step
            e = X[:, k] - Xref[:, k]
            obj += cp.quad_form(e, Q) + cp.quad_form(U[:, k], R)

            # Cart position bounds
            cons += [cp.abs(X[0, k]) <= self.max_cart_pos]

            # Angle deviation bounds around upright (pi)
            cons += [cp.abs(X[1, k] - np.pi) <= self.max_theta_dev]
            cons += [cp.abs(X[2, k] - np.pi) <= self.max_theta_dev]

        # Terminal cost
        eN = X[:, N] - Xref[:, N]
        obj += cp.quad_form(eN, Q)

        prob = cp.Problem(cp.Minimize(obj), cons)

        # Warm start
        try:
            if self._U_prev.size == N:
                U.value = self._U_prev.reshape(1, -1)
        except Exception:
            pass

        # Solve (prefer OSQP; fall back to default if unavailable)
        try:
            prob.solve(solver=cp.OSQP, warm_start=True, verbose=False)
        except Exception:
            prob.solve(warm_start=True, verbose=False)

        if prob.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
            logger.warning("MPC solve failed with status %s; using safe fallback.", prob.status)
            return self._safe_fallback(x0)

        # Extract first control and cache warm start
        u0 = float(U.value[0, 0])
        self._U_prev = U.value.reshape(-1)
        u_cmd = float(np.clip(u0, -self.max_force, self.max_force))
        # Optional slew rate limit
        if self._max_du is not None:
            du = np.clip(u_cmd - self._last_u_out, -self._max_du, self._max_du)
            u_cmd = float(self._last_u_out + du)
        self._last_u_out = u_cmd
        return u_cmd

    # -- Fallbacks ---------------------------------------------------------------------------

    def _safe_fallback(self, x0: np.ndarray) -> float:
        """
        Angle-aware, safe fallback:
        - Prefer an instantiated ClassicalSMC controller.
        - Degrade to a conservative PD on angles if SMC is not available.
        """
        # Prefer SMC fallback if available
        if self._fallback is not None:
            try:
                u_fb, self._fb_state, self._fb_history = self._fallback.compute_control(
                    x0, self._fb_state, self._fb_history
                )
                u_cmd = float(np.clip(u_fb, -self.max_force, self.max_force))
                if self._max_du is not None:
                    du = np.clip(u_cmd - self._last_u_out, -self._max_du, self._max_du)
                    u_cmd = float(self._last_u_out + du)
                self._last_u_out = u_cmd
                return u_cmd
            except Exception as e:
                logger.debug("SMC fallback failed (%s). Degrading to PD.", e)

        # PD on angular error/rate around upright.  Use the configured
        # fallback gains if provided; otherwise fall back to the
        # conservative defaults.  These gains are determined during
        # construction and stored in ``self._pd_kp`` and ``self._pd_kd``.
        theta_err = (x0[1] - np.pi) + (x0[2] - np.pi)
        dtheta_err = x0[4] + x0[5]
        kp = getattr(self, "_pd_kp", 20.0)
        kd = getattr(self, "_pd_kd", 5.0)
        u_fb = -kp * theta_err - kd * dtheta_err
        u_cmd = float(np.clip(u_fb, -self.max_force, self.max_force))
        if self._max_du is not None:
            du = np.clip(u_cmd - self._last_u_out, -self._max_du, self._max_du)
            u_cmd = float(self._last_u_out + du)
        self._last_u_out = u_cmd
        return u_cmd


# Optional demo (kept minimal; no side-effects when imported)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        # This block is illustrative and may require your project's actual config utilities.
        model = DoubleInvertedPendulum({})  # type: ignore[arg-type]
        mpc = MPCController(model, horizon=20, dt=0.02)

        def ref_fn(t: float) -> np.ndarray:
            # Hold upright; ramp cart to +0.5 m over 5 s
            x_target = np.clip(t / 5.0, 0.0, 1.0) * 0.5
            return np.array([x_target, np.pi, np.pi, 0.0, 0.0, 0.0], dtype=float)

        mpc.set_reference(ref_fn)
        x = np.array([0.0, np.pi, np.pi, 0.0, 0.0, 0.0], dtype=float)
        u = mpc(0.0, x)
        print("u(0) =", u)
    except Exception as e:
        logger.info("Demo skipped: %s", e)


#===================================================================================\\\
