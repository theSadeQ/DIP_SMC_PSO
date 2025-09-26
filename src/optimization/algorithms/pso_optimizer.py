#==========================================================================================\\
#============================ src/optimizer/pso_optimizer.py ============================\\
#==========================================================================================\\
"""
Particle Swarm Optimisation (PSO) tuner for sliding-mode controllers.

This module defines the high-throughput, vectorised `PSOTuner` class that wraps
a particle swarm optimisation algorithm around the vectorised simulation of a
double inverted pendulum (DIP) system.  It incorporates improvements from
design review steps, including decoupling of global state, explicit random
number generation, dynamic instability penalties and configurable cost
normalisation.  The implementation follows robust control theory practices
and is fully documented with theoretical backing.

References used throughout this module are provided in the accompanying
design-review report.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import logging
from typing import Callable, Dict, Optional, Any, Iterable, Union
from contextlib import contextmanager
import numpy as _np

from src.config import load_config, ConfigSchema
from src.utils.seed import create_rng
from ...simulation.engines.vector_sim import simulate_system_batch
from ...plant.models.dynamics import DIPParams

# ---------------------------------------------------------------------------
# Module-level configuration
#
# Module-level constants are retained for backward compatibility but are no
# longer mutated by PSOTuner instances.  Earlier versions of this module
# modified global variables (e.g., ``NORMALISATION_THRESHOLD`` and
# ``PSOTuner.COMBINE_WEIGHTS``) when loading a configuration.  Doing so
# introduced hidden coupling between independent optimisation runs and made
# concurrent tuning non-deterministic.  To eliminate cross-contamination
# PSOTuner now stores normalisation thresholds, combine weights and
# instability penalties as instance attributes.  The module constants below
# remain as sensible defaults but are no longer altered by PSOTuner.
NORMALISATION_THRESHOLD: float = 1e-12


def _normalise(val: np.ndarray, denom: float) -> np.ndarray:
    """Safely normalise an array by a scalar denominator.

    When the denominator is very small (≤ NORMALISATION_THRESHOLD) the input
    array is returned unchanged.  The division suppresses divide-by-zero
    warnings.  See tests for expected behaviour.

    Parameters
    ----------
    val : np.ndarray
        Array of values to be normalised.
    denom : float
        Scalar denominator.

    Returns
    -------
    np.ndarray
        The normalised array.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = val / denom
    return np.where(denom > NORMALISATION_THRESHOLD, ratio, val)


@contextmanager
def _seeded_global_numpy(seed: int | None):
    """Context manager to temporarily seed the global NumPy RNG.

    This is used only in the optimise method to ensure deterministic
    behaviour of the PySwarms optimiser when a fixed seed is provided.  It
    saves and restores the global RNG state.
    """
    if seed is None:
        yield
        return
    state = None
    try:
        state = _np.random.get_state()
    except Exception:
        state = None
    try:
        _np.random.seed(int(seed))
        yield
    finally:
        if state is not None:
            try:
                _np.random.set_state(state)
            except Exception:
                pass


class PSOTuner:
    """High-throughput, vectorised tuner for sliding-mode controllers.

    The tuner wraps a particle swarm optimisation algorithm around the
    vectorised simulation.  It uses local PRNGs to avoid global side effects
    and computes instability penalties based on normalisation constants.  Cost
    aggregation between mean and worst-case performance is controlled via
    ``COMBINE_WEIGHTS``.
    """

    # Default combine weights for cost aggregation (mean vs max).  The tuple
    # (0.7, 0.3) balances average performance against worst-case performance.
    COMBINE_WEIGHTS: tuple[float, float] = (0.7, 0.3)

    # Class-level fallback penalty.  Static methods that cannot access an
    # instance use this constant to penalise invalid cost arrays.  A
    # moderate default (1e6) discourages unstable particles without risking
    # numerical overflow.  Instance-level penalties override this value.
    INSTABILITY_PENALTY: float = 1e6

    def __init__(
        self,
        controller_factory: Callable[[np.ndarray], Any],
        config: Union[ConfigSchema, str, Path],
        seed: Optional[int] = None,
        rng: Optional[np.random.Generator] = None,
        *,
        instability_penalty_factor: float = 100.0,
    ) -> None:
        """Initialise the PSOTuner.

        Parameters
        ----------
        controller_factory : Callable[[np.ndarray], Any]
            A function returning a controller instance given a gain vector.
        config : ConfigSchema or path-like
            A validated configuration object or path to the YAML file.
        seed : int or None, optional
            Seed to initialise the local RNG.  When ``None``, the seed from
            the configuration (``global_seed``) is used if present; otherwise
            the RNG is unseeded.
        rng : numpy.random.Generator or None, optional
            External PRNG.  If provided, this generator is used directly and
            ``seed`` is ignored.
        instability_penalty_factor : float, optional
            Scale factor used to compute the penalty for unstable simulations.
            The penalty is computed as
            ``instability_penalty_factor * (norm_ise + norm_u + norm_du + norm_sigma)``.
            Larger values penalise instability more heavily.  Default is 100.
        """
        # Load configuration if a path is provided
        if isinstance(config, (str, Path)):
            self.cfg: ConfigSchema = load_config(config)
        else:
            self.cfg = config

        # Store controller factory and config sections
        self.controller_factory = controller_factory
        self.physics_cfg = self.cfg.physics
        self.sim_cfg = self.cfg.simulation
        self.cost_cfg = self.cfg.cost_function
        self.uncertainty_cfg = getattr(self.cfg, "physics_uncertainty", None)

        # Local PRNG.  Use provided rng or create a new one seeded from
        # ``seed`` or ``global_seed``.  Avoid modifying global RNGs.
        default_seed = seed if seed is not None else getattr(self.cfg, "global_seed", None)
        self.seed: Optional[int] = int(default_seed) if default_seed is not None else None
        self.rng: np.random.Generator = rng or create_rng(self.seed)

        # Factor used to compute instability penalty when no explicit penalty is given
        self.instability_penalty_factor: float = float(instability_penalty_factor)

        # Deprecation warnings for unused PSOConfig parameters
        try:
            pso_cfg = self.cfg.pso
        except Exception:
            pso_cfg = None
        if pso_cfg is not None:
            # Enforce deprecation of unused PSO parameters.  Design review
            # findings recommend removing legacy parameters such as
            # ``n_processes``, ``hyper_trials``, ``hyper_search`` and
            # ``study_timeout``.  Accepting these fields silently leads to
            # misconfigured optimisations and masks typos.  Raise a
            # ValueError when a deprecated field is supplied and not set
            # to its default (None or 1 for n_processes) to force
            # callers to remove outdated keys.
            deprecated_fields = []
            n_proc = getattr(pso_cfg, "n_processes", None)
            if n_proc not in (None, 1):
                deprecated_fields.append("n_processes")
            if getattr(pso_cfg, "hyper_trials", None) is not None:
                deprecated_fields.append("hyper_trials")
            if getattr(pso_cfg, "hyper_search", None) is not None:
                deprecated_fields.append("hyper_search")
            if getattr(pso_cfg, "study_timeout", None) is not None:
                deprecated_fields.append("study_timeout")
            if deprecated_fields:
                raise ValueError(
                    f"Deprecated PSO configuration fields present: {', '.join(deprecated_fields)}. "
                    "Please remove these fields from the configuration."
                )

        # Extract cost weights
        self.weights = self.cost_cfg.weights

        # Determine instability penalty: explicit or computed
        explicit_penalty = getattr(self.cost_cfg, "instability_penalty", None)
        if explicit_penalty is not None:
            try:
                self.instability_penalty: float = float(explicit_penalty)
            except Exception:
                self.instability_penalty = float(self.instability_penalty_factor)
        else:
            self.instability_penalty = None  # to be computed from norms

        # Normalisation constants for state error, control effort, control rate and sliding variable
        norms = getattr(self.cost_cfg, "norms", None)
        if norms is not None:
            self.norm_ise = float(getattr(norms, "state_error", 1.0))
            self.norm_u = float(getattr(norms, "control_effort", 1.0))
            self.norm_du = float(getattr(norms, "control_rate", 1.0))
            self.norm_sigma = float(getattr(norms, "sliding", 1.0))
        else:
            self.norm_ise = self.norm_u = self.norm_du = self.norm_sigma = 1.0

        # Compute penalty if not explicitly provided
        if self.instability_penalty is None:
            denom_sum = (self.norm_ise + self.norm_u + self.norm_du + self.norm_sigma)
            if not np.isfinite(denom_sum) or denom_sum <= 0.0:
                denom_sum = 1.0
            self.instability_penalty = float(self.instability_penalty_factor * denom_sum)

        # Automatic baseline normalisation
        try:
            baseline = getattr(self.cost_cfg, "baseline", None)
            gains_list = None
            if baseline is not None:
                if isinstance(baseline, dict):
                    gains_list = baseline.get("gains")
                else:
                    gains_list = getattr(baseline, "gains", None)
            if gains_list is not None and isinstance(gains_list, (list, tuple)) and len(gains_list) > 0:
                # Local import to avoid circular dependency
                import numpy as _np
                baseline_particles = _np.asarray(gains_list, dtype=float).reshape(1, -1)
                try:
                    baseline_ctrl = controller_factory(baseline_particles[0])
                    u_max_val = float(getattr(baseline_ctrl, "max_force", 150.0))
                except Exception:
                    u_max_val = 150.0
                res = simulate_system_batch(
                    controller_factory=controller_factory,
                    particles=baseline_particles,
                    sim_time=self.sim_cfg.duration,
                    dt=self.sim_cfg.dt,
                    u_max=u_max_val,
                )
                if isinstance(res, list):
                    t, x_b, u_b, sigma_b = res[0]
                else:
                    t, x_b, u_b, sigma_b = res
                x_b = _np.asarray(x_b, dtype=float)
                u_b = _np.asarray(u_b, dtype=float)
                sigma_b = _np.asarray(sigma_b, dtype=float)
                dt_arr = _np.diff(t)[None, :]
                if dt_arr.size == 0:
                    dt_arr = _np.array([[self.sim_cfg.dt]])
                N = dt_arr.shape[1]
                time_mask = _np.ones((1, N), dtype=bool)
                ise_base = float(
                    _np.sum((x_b[:, :-1, :3] ** 2 * dt_arr[:, :, None]) * time_mask[:, :, None], axis=(1, 2))[0]
                )
                u_sq_base = float(_np.sum((u_b ** 2 * dt_arr) * time_mask, axis=1)[0])
                du = _np.diff(u_b, axis=1, prepend=u_b[:, 0:1])
                du_sq_base = float(_np.sum((du ** 2 * dt_arr) * time_mask, axis=1)[0])
                sigma_sq_base = float(_np.sum((sigma_b ** 2 * dt_arr) * time_mask, axis=1)[0])
                self.norm_ise = max(ise_base, 1e-12)
                self.norm_u = max(u_sq_base, 1e-12)
                self.norm_du = max(du_sq_base, 1e-12)
                self.norm_sigma = max(sigma_sq_base, 1e-12)
        except Exception:
            pass

        # Overrides for combine_weights and normalization_threshold
        # Instance-level combine weights and normalisation threshold.  Earlier
        # implementations mutated class or module variables to reflect these
        # settings.  To avoid cross-contamination between PSO runs, store
        # them per instance and avoid modifying global state.  Defaults are
        # taken from the class attributes if present.
        self.combine_weights: tuple[float, float] = (0.7, 0.3)
        # Normalisation threshold for safe division; defaults to module
        # constant.  Smaller values cause more aggressive normalisation.
        self.normalisation_threshold: float = float(NORMALISATION_THRESHOLD)
        try:
            cw = getattr(self.cost_cfg, "combine_weights", None)
            if cw is None and isinstance(self.cost_cfg, dict):
                cw = self.cost_cfg.get("combine_weights")
            if cw is not None:
                mean_w = None
                max_w = None
                if not isinstance(cw, dict):
                    mean_w = getattr(cw, "mean", None)
                    max_w = getattr(cw, "max", None)
                if isinstance(cw, dict):
                    mean_w = cw.get("mean") if mean_w is None else mean_w
                    max_w = cw.get("max") if max_w is None else max_w
                if mean_w is not None and max_w is not None:
                    mw = float(mean_w)
                    xw = float(max_w)
                    total = mw + xw
                    if total > 0:
                        self.combine_weights = (mw / total, xw / total)
        except Exception:
            pass
        try:
            nt = getattr(self.cost_cfg, "normalization_threshold", None)
            if nt is None and isinstance(self.cost_cfg, dict):
                nt = self.cost_cfg.get("normalization_threshold")
            if nt is not None:
                self.normalisation_threshold = float(nt)
        except Exception:
            pass

        # Warn about deprecated PSO fields that are ignored
        deprecated: list[str] = []
        try:
            pcfg = self.cfg.pso
            for attr in ("n_processes", "hyper_trials", "hyper_search", "study_timeout"):
                val = getattr(pcfg, attr, None)
                if val not in (None, 0, {}, []):
                    deprecated.append(attr)
            if deprecated:
                logging.warning(
                    "PSOConfig fields %s are deprecated and ignored. These parameters will be removed in a future version.",
                    deprecated,
                )
        except Exception:
            pass


    # ---------- Robust sampling ----------
    def _iter_perturbed_physics(self) -> Iterable[DIPParams]:
        """Yield perturbed physics parameters for robustness evaluation.

        The nominal model is yielded first.  Subsequent draws perturb each
        parameter within ±``percent`` of its nominal value as specified in
        ``physics_uncertainty``.  When uncertainty is disabled or ``n_evals ≤ 1``
        only the nominal model is yielded.
        """
        yield DIPParams.from_physics_config(self.physics_cfg)
        if not self.uncertainty_cfg or self.uncertainty_cfg.n_evals <= 1:
            return
        rng_local = np.random.default_rng(self.seed) if self.seed is not None else self.rng
        base_params = self.physics_cfg.model_dump()
        pu = self.uncertainty_cfg.model_dump()
        for _ in range(self.uncertainty_cfg.n_evals - 1):
            perturbed_params = base_params.copy()
            for key, pct in pu.items():
                if key == "n_evals" or pct is None or key not in perturbed_params:
                    continue
                nominal = base_params[key]
                delta = float(pct) * float(nominal)
                eps = rng_local.uniform(-delta, +delta)
                perturbed_params[key] = float(nominal) + float(eps)
            # Safety: ensure centre of mass does not exceed pendulum length
            if "pendulum1_com" in perturbed_params and "pendulum1_length" in perturbed_params:
                if perturbed_params["pendulum1_com"] >= perturbed_params["pendulum1_length"]:
                    perturbed_params["pendulum1_com"] = 0.99 * perturbed_params["pendulum1_length"]
            if "pendulum2_com" in perturbed_params and "pendulum2_length" in perturbed_params:
                if perturbed_params["pendulum2_com"] >= perturbed_params["pendulum2_length"]:
                    perturbed_params["pendulum2_com"] = 0.99 * perturbed_params["pendulum2_length"]
            # Handle field mapping for DIPParams
            dipparams_dict = perturbed_params.copy()
            if 'regularization' in dipparams_dict:
                reg = dipparams_dict.pop('regularization')
                dipparams_dict.setdefault('min_regularization', reg)
                dipparams_dict.setdefault('regularization_alpha', 1e-4)
            dipparams_dict.setdefault('max_condition_number', 1e10)
            dipparams_dict.setdefault('use_fixed_regularization', False)
            dipparams_dict.setdefault('det_threshold', 1e-12)
            dipparams_dict.setdefault('condition_tol_factor', 1e-12)
            dipparams_dict.setdefault('singularity_cond_threshold', 1e8)
            yield DIPParams(**dipparams_dict)

    # ---------- Cost computation ----------
    def _compute_cost_from_traj(
        self, t: np.ndarray, x_b: np.ndarray, u_b: np.ndarray, sigma_b: np.ndarray
    ) -> np.ndarray:
        """Compute the cost per particle from simulated trajectories.

        The cost combines state error, control effort, control slew and a
        sliding-mode stability term.  State error integrates the squared
        deviation of all state components over the horizon.  Control terms
        integrate squared commands and their rates.  A graded instability
        penalty is applied when trajectories fail early.
        """
        # Flag trajectories with any non-finite state entry
        nan_traj_mask = ~np.all(np.isfinite(x_b), axis=(1, 2)) if x_b.size else np.zeros(0, dtype=bool)
        dt = np.diff(t)
        dt_b = dt[None, :]
        dt_const = dt[0] if dt.size else self.sim_cfg.dt
        N = len(dt)
        B = x_b.shape[0]
        if N == 0:
            return np.zeros(B, dtype=float)
        # Instability detection
        fall_mask = np.abs(x_b[:, :, 1]) > (0.5 * np.pi)
        explodes_mask = np.any(np.abs(x_b) > 1e6, axis=2)
        unstable_mask = fall_mask | explodes_mask
        temp = np.full((B, N + 1), N + 1)
        temp[unstable_mask] = np.tile(np.arange(N + 1), (B, 1))[unstable_mask]
        failure_steps = np.min(temp, axis=1)
        time_mask = (np.arange(N)[None, :] < (failure_steps - 1)[:, None])
        # State error: integrate squared error across all state variables  # [CIT-068]
        ise = np.sum((x_b[:, :-1, :] ** 2 * dt_b[:, :, None]) * time_mask[:, :, None], axis=(1, 2))  # [CIT-068]
        ise_n = self._normalise(ise, self.norm_ise)
        # Control effort  # [CIT-068]
        u_sq = np.sum((u_b ** 2 * dt_b) * time_mask, axis=1)  # [CIT-068]
        u_n = self._normalise(u_sq, self.norm_u)
        # Control slew  # [CIT-068]
        du = np.diff(u_b, axis=1, prepend=u_b[:, 0:1])  # [CIT-068]
        du_sq = np.sum((du ** 2 * dt_b) * time_mask, axis=1)  # [CIT-068]
        du_n = self._normalise(du_sq, self.norm_du)
        # Sliding variable energy  # [CIT-068]
        sigma_sq = np.sum((sigma_b ** 2 * dt_b) * time_mask, axis=1)  # [CIT-068]
        sigma_n = self._normalise(sigma_sq, self.norm_sigma)
        # Graded penalty for early failure
        failure_t = np.clip((failure_steps - 1) * dt_const, 0, self.sim_cfg.duration)
        penalty = self.weights.stability * ((self.sim_cfg.duration - failure_t) / self.sim_cfg.duration) * self.instability_penalty
        J = (
            self.weights.state_error * ise_n
            + self.weights.control_effort * u_n
            + self.weights.control_rate * du_n
            + self.weights.stability * sigma_n
        ) + penalty  # [CIT-068]
        # Explicitly penalise NaN trajectories
        if nan_traj_mask.any():
            J = J.astype(float, copy=True)
            J[nan_traj_mask] = float(self.instability_penalty)
        J = J.astype(float, copy=True)
        nan_mask = ~np.isfinite(J)
        if nan_mask.any():
            J[nan_mask] = float(self.instability_penalty)
        return J

    # ---------- Normalisation and cost aggregation helpers ----------
    def _normalise(self, val: np.ndarray, denom: float) -> np.ndarray:
        """Safely normalise an array by a scalar denominator using the instance's threshold.

        When the denominator is less than or equal to ``self.normalisation_threshold`` the
        original array is returned unchanged.  This prevents amplification of
        numerical noise in near-zero denominators.

        Parameters
        ----------
        val : np.ndarray
            Array of values to be normalised.
        denom : float
            Scalar denominator.

        Returns
        -------
        np.ndarray
            The normalised array.
        """
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = val / denom
        thr = float(self.normalisation_threshold)
        return np.where(denom > thr, ratio, val)

    def _combine_costs(self, costs: np.ndarray) -> np.ndarray:
        """Aggregate costs across uncertainty draws using the instance's weights.

        For a one-dimensional array of costs, return ``w_mean*mean + w_max*max``.  For
        a two-dimensional array of shape (D, B), aggregate along the first
        dimension (draws) and return an array of shape (B,).  Non-finite inputs
        result in the instability penalty.

        Parameters
        ----------
        costs : np.ndarray
            1D or 2D array of cost values.

        Returns
        -------
        np.ndarray or float
            Aggregated costs per particle or a single scalar cost.
        """
        c = np.asarray(costs, dtype=float)
        mean_w, max_w = self.combine_weights
        if c.ndim == 1:
            if c.size == 0 or not np.all(np.isfinite(c)):
                return float(self.instability_penalty)
            return float(mean_w * c.mean() + max_w * c.max())
        if c.ndim == 2:
            if c.size == 0 or not np.all(np.isfinite(c)):
                return np.full(c.shape[1], float(self.instability_penalty), dtype=float)
            return mean_w * c.mean(axis=0) + max_w * c.max(axis=0)
        raise ValueError("costs must be 1D or 2D")

    # ---------- Fitness evaluation ----------
    def _fitness(self, particles: np.ndarray) -> np.ndarray:
        """Vectorised fitness function for a swarm of particles."""
        ref_ctrl = self.controller_factory(particles[0])
        self._u_max = getattr(ref_ctrl, "max_force", 150.0)
        self._T = self.sim_cfg.duration
        B = particles.shape[0]
        violation_mask = np.zeros(B, dtype=bool)
        valid_mask = ~violation_mask
        valid_particles = particles
        # Pre-filter particles using validate_gains if available
        if hasattr(ref_ctrl, "validate_gains") and callable(getattr(ref_ctrl, "validate_gains")):
            try:
                valid_mask_arr = ref_ctrl.validate_gains(particles)
                valid_mask_arr = valid_mask_arr.astype(bool).reshape(-1)
                if valid_mask_arr.shape[0] != particles.shape[0]:
                    raise ValueError("validate_gains returned mask with wrong length")
            except Exception:
                valid_mask_arr = None
            if valid_mask_arr is not None:
                violation_mask = ~valid_mask_arr
                if violation_mask.any():
                    if (~violation_mask).sum() == 0:
                        return np.full(B, float(self.instability_penalty), dtype=float)
                    valid_particles = particles[~violation_mask]
                    valid_mask = ~violation_mask
        # Evaluate under uncertainty draws if configured
        if self.uncertainty_cfg and self.uncertainty_cfg.n_evals > 1:
            physics_models = list(self._iter_perturbed_physics())
            try:
                results_list = simulate_system_batch(
                    controller_factory=self.controller_factory,
                    particles=valid_particles,
                    sim_time=self._T,
                    dt=self.sim_cfg.dt,
                    u_max=self._u_max,
                    params_list=physics_models,
                )
            except TypeError:
                results_list = simulate_system_batch(
                    controller_factory=self.controller_factory,
                    particles=valid_particles,
                    sim_time=self._T,
                    u_max=self._u_max,
                    params_list=physics_models,
                )
            all_costs: list[np.ndarray] = []
            for t, x_b, u_b, sigma_b in results_list:
                cost = self._compute_cost_from_traj(t, x_b, u_b, sigma_b)
                nan_mask = ~np.isfinite(cost)
                if nan_mask.any():
                    cost = cost.astype(float, copy=True)
                    cost[nan_mask] = float(self.instability_penalty)
                all_costs.append(cost)
            costs_per_draw = np.stack(all_costs, axis=0)
            J_valid = self._combine_costs(costs_per_draw)
            penalty = float(self.instability_penalty)
            unstable_mask = np.max(costs_per_draw, axis=0) >= penalty
            if np.any(unstable_mask):
                J_valid = J_valid.astype(float, copy=True)
                J_valid[unstable_mask] = penalty
        else:
            try:
                t, x_b, u_b, sigma_b = simulate_system_batch(
                    controller_factory=self.controller_factory,
                    particles=valid_particles,
                    sim_time=self._T,
                    dt=self.sim_cfg.dt,
                    u_max=self._u_max,
                )
            except TypeError:
                t, x_b, u_b, sigma_b = simulate_system_batch(
                    controller_factory=self.controller_factory,
                    particles=valid_particles,
                    sim_time=self._T,
                    u_max=self._u_max,
                )
            # Determine which particles produced non-finite trajectories.
            # Construct a mask that flags any particle whose state, control or
            # sliding variable contains NaNs or infinite values.  Parentheses
            # group the three boolean arrays to avoid inadvertent line
            # continuation issues in Python syntax.
            nan_mask = (
                (~np.all(np.isfinite(x_b), axis=(1, 2)))
                | (~np.all(np.isfinite(u_b), axis=1))
                | (~np.all(np.isfinite(sigma_b), axis=1))
            )
            J_valid = self._compute_cost_from_traj(t, x_b, u_b, sigma_b)
            if nan_mask.any():
                J_valid[nan_mask] = float(self.instability_penalty)
        if violation_mask.any():
            J_full = np.full(B, float(self.instability_penalty), dtype=float)
            J_full[valid_mask] = J_valid
            return J_full
        return J_valid

    # ---------- Optimisation ----------
    def optimise(
        self,
        *args: Any,
        iters_override: Optional[int] = None,
        n_particles_override: Optional[int] = None,
        options_override: Optional[Dict[str, float]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run particle swarm optimisation with optional overrides.

        This method constructs a `pyswarms.single.GlobalBestPSO` instance from
        the PSO configuration and executes the optimisation loop.  Two
        enhancements are supported beyond the standard PSO:

        * **Velocity clamping:** if ``pso_cfg.velocity_clamp`` is a tuple
          ``(delta_min, delta_max)``, the per-dimension particle velocities are
          constrained to lie within ``delta_min*(bmax - bmin)`` and
          ``delta_max*(bmax - bmin)``.  Clamping prevents
          particles from overshooting and encourages stability.  When unset,
          no explicit velocity limits are imposed.
        * **Inertia weight scheduling:** if ``pso_cfg.w_schedule`` is provided
          as ``(w_start, w_end)``, the inertia weight is decreased linearly
          from ``w_start`` to ``w_end`` over the iteration horizon to shift
          gradually from global exploration to local exploitation.
          When a schedule is specified, the method runs a manual stepping loop,
          updating ``optimizer.options['w']`` at each iteration and capturing
          the best cost and position history.

        Parameters
        ----------
        iters_override : int, optional
            Overrides the number of iterations specified in the configuration.
        n_particles_override : int, optional
            Overrides the swarm size specified in the configuration.
        options_override : dict, optional
            Dictionary of PSO hyperparameters (e.g., inertia and cognitive/social
            weights) that update defaults from configuration.  These values
            take precedence over the configuration defaults but are superseded
            by ``w_schedule`` for the inertia weight.

        Returns
        -------
        dict
            A dictionary containing ``best_cost``, ``best_pos`` and a history
            of costs and positions.  When a schedule is used, the history
            arrays have length ``iters``; otherwise the history is taken
            directly from the underlying PSO optimiser.
        """
        from pyswarms.single import GlobalBestPSO
        pso_cfg = self.cfg.pso
        min_list = list(pso_cfg.bounds.min)
        max_list = list(pso_cfg.bounds.max)
        if len(min_list) != len(max_list):
            raise ValueError(
                f"PSO bounds min/max lengths differ: {len(min_list)} != {len(max_list)}"
            )
        expected_dims = getattr(self.controller_factory, "n_gains", None)
        if expected_dims is None:
            raise ValueError(
                "Controller factory must define a class attribute 'n_gains' to specify the expected dimensionality of the gain vector."
            )
        if len(min_list) < expected_dims:
            raise ValueError(
                f"PSO bounds underspecified: controller expects {expected_dims} gains, but bounds provide only {len(min_list)}."
            )
        pso_options = {
            'c1': pso_cfg.c1,
            'c2': pso_cfg.c2,
            'w': pso_cfg.w,
        }
        # Warn the user if PSO hyperparameters are outside recommended ranges.
        try:
            # Recommended swarm sizes are 10–30 and balanced c1≈c2.
            if not (10 <= int(pso_cfg.n_particles) <= 50):
                logging.getLogger(__name__).warning(
                    "n_particles=%s is outside the recommended range [10,50] for PSO", pso_cfg.n_particles
                )
            if abs(float(pso_cfg.c1) - float(pso_cfg.c2)) > 0.5:
                logging.getLogger(__name__).warning(
                    "PSO acceleration coefficients are unbalanced (c1=%s, c2=%s); set c1≈c2 to avoid divergence",
                    pso_cfg.c1, pso_cfg.c2
                )
        except Exception:
            # Ignore warnings if parameters are missing or cannot be cast.
            pass
        if options_override:
            for k, v in options_override.items():
                if k in pso_options:
                    pso_options[k] = float(v)
                else:
                    pso_options[k] = v
        bmin = np.array(min_list[:expected_dims], dtype=float)
        bmax = np.array(max_list[:expected_dims], dtype=float)
        bounds = (bmin, bmax)
        n_particles = int(n_particles_override) if n_particles_override is not None else int(pso_cfg.n_particles)
        iters = int(iters_override) if iters_override is not None else int(pso_cfg.iters)
        if n_particles <= 0 or iters <= 0:
            raise ValueError("n_particles and iters must be positive")
        # Reinitialise the local RNG when a fixed seed is provided.  Using a
        # per-instance Generator avoids global side effects.
        if self.seed is not None:
            self.rng = np.random.default_rng(int(self.seed))
        # Initialise swarm positions using the local RNG to avoid
        # invoking the global NumPy RNG.  Without specifying init_pos
        # the underlying PSO implementation seeds the global RNG.
        init_pos = self.rng.uniform(low=bmin, high=bmax, size=(n_particles, expected_dims))
        # Derive a seed for the PSO library from the local RNG.  Passing a
        # deterministic seed ensures that the PSO optimiser does not rely on
        # NumPy's global RNG and produces reproducible results across runs.
        seed_int = None
        try:
            seed_int = int(self.rng.integers(0, 2**32 - 1))
        except Exception:
            seed_int = None
        # Compute optional velocity clamp.  Velocity clamping prevents particles
        # from diverging and helps ensure convergence.  The clamping limits are
        # expressed as fractions of the search range and multiplied by ``bmax - bmin``.
        v_clamp: Optional[tuple[np.ndarray, np.ndarray]] = None
        try:
            vc = getattr(pso_cfg, "velocity_clamp", None)
            if vc is not None:
                frac_min, frac_max = float(vc[0]), float(vc[1])
                # Compute per-dimension ranges
                range_vec = bmax - bmin
                v_clamp = (frac_min * range_vec, frac_max * range_vec)
        except Exception:
            v_clamp = None

        # Create optimizer - handle version compatibility for PySwarms
        try:
            # Try with newer PySwarms API that supports seed and velocity_clamp
            optimizer = GlobalBestPSO(
                n_particles=n_particles,
                dimensions=expected_dims,
                options=pso_options,
                bounds=bounds,
                init_pos=init_pos,
                seed=seed_int,
                velocity_clamp=v_clamp,
            )
        except TypeError:
            # Fallback for PySwarms 1.3.0 which doesn't support seed or velocity_clamp
            optimizer = GlobalBestPSO(
                n_particles=n_particles,
                dimensions=expected_dims,
                options=pso_options,
                bounds=bounds,
                init_pos=init_pos,
            )
        # If an inertia weight schedule is provided, perform manual stepping.  A
        # linearly decreasing inertia weight from 0.9 to 0.4 encourages early
        # exploration and late exploitation.  The
        # optimisation loop updates ``optimizer.options['w']`` at each step and
        # records cost and position history.
        if getattr(pso_cfg, "w_schedule", None):
            try:
                w_start, w_end = pso_cfg.w_schedule
                # Generate equally spaced inertia weights over the iteration horizon
                w_values = np.linspace(float(w_start), float(w_end), iters)
            except Exception:
                # Fall back to constant inertia if schedule is invalid
                w_values = np.full(iters, float(pso_cfg.w))
            cost_hist: list[float] = []
            pos_hist: list[np.ndarray] = []
            for w_val in w_values:
                # Update inertia weight for this iteration
                optimizer.options['w'] = float(w_val)
                # Execute a single PSO step; returns current best cost and position
                step_cost, step_pos = optimizer.step(self._fitness)
                cost_hist.append(float(step_cost))
                pos_hist.append(np.asarray(step_pos, dtype=float).copy())
            # Retrieve final global best values from the swarm
            try:
                final_cost = float(optimizer.swarm.best_cost)
                final_pos = np.asarray(optimizer.swarm.best_pos, dtype=float).copy()
            except Exception:
                # Fallback to the last recorded values
                final_cost = float(cost_hist[-1])
                final_pos = pos_hist[-1]
            return {
                "best_cost": final_cost,
                "best_pos": final_pos,
                "history": {
                    "cost": np.asarray(cost_hist, dtype=float),
                    "pos": np.asarray(pos_hist, dtype=float),
                },
            }
        # Otherwise run the built-in optimise method using constant inertia.  The
        # inertia weight ``w`` should typically lie in [0.4, 0.9].
        cost, pos = optimizer.optimize(self._fitness, iters=iters)
        return {
            "best_cost": float(cost),
            "best_pos": np.asarray(pos),
            "history": {
                "cost": optimizer.cost_history,
                "pos": optimizer.pos_history,
            },
        }
