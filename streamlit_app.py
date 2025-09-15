#==========================================================================================\\\
#==================================== streamlit_app.py ====================================\\\
#==========================================================================================\\\

"""
Interactive Streamlit dashboard for PSO‑tuned SMC-controllers of a double‑inverted pendulum.

"""
from __future__ import annotations

import io
import json
import numpy as np
import matplotlib.pyplot as plt
# The Streamlit module is optional.  Wrap the import in a try/except so that
# this file can be imported when Streamlit is not installed (e.g., during
# automated tests).  When the import fails, fall back to a minimal stub
# object that exposes ``warning`` and ``markdown`` as no‑ops.  Any other
# attribute access on the stub returns a no‑op function.  Tests monkey‑patch
# ``streamlit_app.st`` directly, so the presence of this stub ensures that
# module import succeeds and that ``_parse_initial_state`` can still call
# ``st.warning`` without raising AttributeError.
try:
    import streamlit as st  # type: ignore
except Exception:
    class _StreamlitStub:
        def warning(self, *args, **kwargs) -> None:
            return None
        def markdown(self, *args, **kwargs) -> None:
            return None
        def __getattr__(self, name: str):
            # Return a no‑op function for any other attribute.  Using a
            # lambda ensures that calls return None regardless of arguments.
            return lambda *args, **kwargs: None
    st = _StreamlitStub()  # type: ignore
import yaml
import zipfile
from pathlib import Path
from typing import Callable, Optional

from src.config import load_config
from src.controllers.factory import create_controller
from src.core.dynamics import DIPDynamics
from src.core.dynamics_full import FullDIPDynamics
from src.core.simulation_runner import run_simulation
from src.optimizer.pso_optimizer import PSOTuner

# Visualizer import (support both in‑repo path and local file during CI/examples)
try:
    from src.utils.visualization import Visualizer  # project structure
except ModuleNotFoundError:
    try:
        from visualization import Visualizer  # fallback for isolated runs
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Critical: Visualizer module not found in either src/utils/ or local path. "
            "Cannot proceed without visualization capability."
        ) from e

# ────────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────────

def load_css(path: str):
    try:
        with open(path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:  # Expected - CSS is optional
        pass

def _parse_initial_state(text: str, default: np.ndarray, state_dim: int) -> np.ndarray:
    """Parse comma‑separated floats; pad/truncate to `state_dim`.
    Falls back to `default` on parse error.

    Why: We only catch ValueError and TypeError because these are the expected
    exceptions from user input parsing. Any other exception (like MemoryError,
    AttributeError) indicates a critical backend issue that should propagate.
    """
    try:
        arr = np.array([float(s) for s in text.replace("\n", ",").split(",") if s.strip() != ""], dtype=float)
        if arr.size == 0:
            st.warning("Empty initial state; using defaults from config.")
            return np.array(default, dtype=float)
    except ValueError:
        # These are expected from bad user input
        st.warning("Could not parse initial state; using defaults from config.")
        return np.array(default, dtype=float)
    except TypeError:
        # Also expected from certain malformed inputs
        st.warning("Invalid input type for initial state; using defaults from config.")
        return np.array(default, dtype=float)
    # Any other exception (like AttributeError, MemoryError) should propagate
    # as it indicates a serious backend issue, not a user input problem
    
    if arr.size < state_dim:
        arr = np.pad(arr, (0, state_dim - arr.size))
    elif arr.size > state_dim:
        st.warning(f"Input has {arr.size} values, but {state_dim} are required. Truncating excess values.")
        arr = arr[:state_dim]
    return arr

def _compute_metrics(t: np.ndarray, x: np.ndarray, u: np.ndarray,
                     tol_x: float = 0.02, tol_th: float = 0.05) -> dict:
    """Compute simple performance metrics.
    - Settling time: first time after which |x|<tol_x & |θ1|,|θ2|<tol_th until end
    - RMS control effort
    - Peak magnitudes
    """
    # tolerances against equilibrium 0
    within = (np.abs(x[:, 0]) < tol_x)
    if x.shape[1] >= 3:
        within = within & (np.abs(x[:, 1]) < tol_th) & (np.abs(x[:, 2]) < tol_th)

    settle_idx = len(t) - 1
    for i in range(len(t)):
        if np.all(within[i:]):
            settle_idx = i
            break

    metrics = {
        "settling_time_s": float(t[settle_idx]),
        "rms_control_N": float(np.sqrt(np.mean(u**2))) if u.size else 0.0,
        "peak_abs_x_m": float(np.max(np.abs(x[:, 0]))),
        "peak_abs_th1_deg": float(np.rad2deg(np.max(np.abs(x[:, 1])))) if x.shape[1] > 1 else 0.0,
        "peak_abs_th2_deg": float(np.rad2deg(np.max(np.abs(x[:, 2])))) if x.shape[1] > 2 else 0.0,
        "max_abs_u_N": float(np.max(np.abs(u))) if u.size else 0.0,
    }
    return metrics

class DisturbedDynamics:
    """Wrap a dynamics model and inject an external disturbance d(t) to the input.

    The wrapped `step` passes (u + d(t)) to the underlying model. Time is
    advanced internally using the provided `dt` at each call.
    """
    def __init__(self, base, d_fn: Optional[Callable[[float], float]]):
        self._base = base
        self._d_fn = d_fn
        self._time = 0.0
        self.state_dim = int(getattr(base, "state_dim", 6))

    def default_state(self):
        if hasattr(self._base, "default_state"):
            return self._base.default_state()
        return np.zeros(self.state_dim)

    def step(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        d = float(self._d_fn(self._time)) if self._d_fn is not None else 0.0
        self._time += float(dt)
        return self._base.step(state, u + d, dt)

    def __getattr__(self, name):  # allow Visualizer to read geometry (l1/l2/etc.)
        return getattr(self._base, name)

# ────────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────────

def main():
    # ───────── Translations
    @st.cache_data
    def load_translations(path: str = "translations.yaml") -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Translations are optional - return empty dict
            return {}

    cfg = load_config("config.yaml")
    translations = load_translations()

    st.set_page_config(page_title="Pendulum Control Simulator", layout="wide")
    load_css("src/assets/style.css")

    # Workaround for older/newer Streamlit versions: ``st.session_state`` may
    # behave like a dictionary without a ``get`` method.  Define a helper
    # function to retrieve keys safely.  When ``st.session_state.get``
    # exists, use it; otherwise fall back to dict-style indexing.
    def _session_state_get(key: str, default: Optional[str] = None) -> Optional[str]:
        ss = st.session_state  # type: ignore[attr-defined]
        if hasattr(ss, "get"):
            try:
                return ss.get(key, default)  # type: ignore[call-arg]
            except Exception:
                pass
        try:
            return ss[key]  # type: ignore[index]
        except Exception:
            return default
    # Language selector
    lang_default = _session_state_get("lang", "English")
    # Use keyword arguments for selectbox to accommodate fake streamlit stubs in
    # tests.  Passing arguments positionally causes a ``TypeError`` when
    # ``st.sidebar.selectbox`` is a simple function accepting only keyword
    # arguments (see tests/test_app/test_streamlit_app.py).  Provide a label
    # and options explicitly to avoid positional parameters.
    st.session_state.lang = st.sidebar.selectbox(
        label="Language / زبان",
        options=("English", "فارسی"),
        index=("English", "فارسی").index(lang_default),
    )
    t = translations.get(st.session_state.lang, translations.get("English", {}))

    # ───────── Sidebar
    st.sidebar.header(t.get("sidebar_header", "Controls"))

    # 1) Dynamics selection
    st.sidebar.subheader(t.get("dynamics_header", "1. Dynamics Model"))
    use_full_dynamics = st.sidebar.checkbox(
        t.get("use_full_label", "Use Full Nonlinear Dynamics"),
        value=bool(getattr(cfg.simulation, "use_full_dynamics", False)),
        help=t.get("use_full_help", "Use the complete, more accurate dynamics model."),
    )
    cfg.simulation.use_full_dynamics = use_full_dynamics

    # 2) Controller
    st.sidebar.subheader(t.get("controller_select", "2. Controller"))
    controller_options = list(cfg.controllers.keys())
    controller_sel = st.sidebar.selectbox(
        label=t.get("controller_label", "Controller Type"),
        options=controller_options,
    )

    # 3) PSO (optional)
    st.sidebar.subheader(t.get("pso_header", "Optimization"))
    best_params = np.array(cfg.controller_defaults[controller_sel]["gains"], dtype=float)
    if st.sidebar.button(t.get("run_button", "Run PSO")):
        with st.spinner(t.get("spinner_msg", "Optimizing...")):
            controller_factory = lambda gains: create_controller(controller_sel, config=cfg, gains=gains)
            tuner = PSOTuner(controller_factory, config=cfg, seed=getattr(cfg, "global_seed", None))
            res = tuner.optimise(x0=np.asarray(best_params, dtype=float))
            if np.isfinite(res.get("best_cost", np.inf)):
                best_params = np.array(res["best_pos"], dtype=float)
                st.success(t.get("success_msg", "Optimization succeeded."))
                st.metric(label=t.get("cost_metric", "Best Cost"), value=f"{res['best_cost']:.4f}")
            else:
                st.error(t.get("opt_fail", "Optimization failed to find a valid solution."))
    st.sidebar.write(f"**{t.get('params_header', 'Controller Gains')}**")
    st.sidebar.code(np.array2string(best_params, precision=3))

    # 4) Simulation settings (NEW)
    st.sidebar.subheader(t.get("sim_settings_header", "Simulation Settings"))
    sim_cfg = cfg.simulation
    sim_duration = st.sidebar.slider(
        t.get("sim_duration_label", "Simulation Duration (s)"),
        min_value=1.0,
        max_value=60.0,
        value=float(sim_cfg.duration),
        step=0.5,
    )
    sim_dt = st.sidebar.slider(
        t.get("sim_dt_label", "Time Step dt (s)"),
        min_value=0.001,
        max_value=0.1,
        value=float(sim_cfg.dt),
        step=0.001,
    )

    # Initial state input
    default_state = np.array(sim_cfg.initial_state, dtype=float)
    state_str = st.sidebar.text_area(
        t.get("initial_state_label", "Initial State (comma‑separated)"),
        value=", ".join([f"{v:.3f}" for v in default_state]),
        help=t.get("initial_state_help", "[x, θ1, θ2, ẋ, θ̇1, θ̇2]"),
    )
    state_dim = 6
    initial_state = _parse_initial_state(state_str, default_state, state_dim)

    # 5) Disturbance (NEW)
    st.sidebar.subheader(t.get("disturbance_header", "Disturbance"))
    add_disturbance = st.sidebar.checkbox(t.get("add_disturbance_label", "Add Disturbance"), value=False)
    disturbance_function = None
    if add_disturbance:
        dist_mag = st.sidebar.slider(
            t.get("dist_magnitude_label", "Magnitude (N)"),
            min_value=0.0,
            max_value=10.0,
            value=2.0,
            step=0.1,
        )
        dist_start = st.sidebar.slider(
            t.get("dist_start_label", "Start Time (s)"),
            min_value=0.0,
            max_value=sim_duration - 0.1,
            value=1.0,
            step=0.1,
        )
        dist_duration = st.sidebar.slider(
            t.get("dist_duration_label", "Duration (s)"),
            min_value=0.1,
            max_value=sim_duration - dist_start,
            value=0.5,
            step=0.1,
        )
        # Rectangular pulse
        def disturbance_function(t: float) -> float:
            return dist_mag if dist_start <= t < dist_start + dist_duration else 0.0

    # ───────── Main area
    st.title(t.get("title", "Pendulum Control Dashboard"))
    st.write(t.get("intro", "Real‑time PSO‑tuned controllers for double‑inverted pendulum control."))

    # ───────── Dynamics
    physics_params = cfg.physics
    if use_full_dynamics:
        base_model = FullDIPDynamics(physics_params)
    else:
        base_model = DIPDynamics(physics_params)

    dynamics_model = DisturbedDynamics(base_model, disturbance_function)

    # ───────── Controller
    controller = create_controller(controller_sel, config=cfg, gains=best_params)

    # ───────── Run
    t_sim, x_sim, u_sim = run_simulation(
        controller=controller,
        dynamics_model=dynamics_model,
        sim_time=sim_duration,
        dt=sim_dt,
        initial_state=initial_state,
    )

    # ───────── Visualization (NEW)
    st.subheader(t.get("animation_header", "Simulation Animation"))
    
    # Create visualizer
    visualizer = Visualizer(dynamics_model)
    visualizer.animate(t_sim, x_sim, u_sim, dt=sim_dt)
    
    # Display animation
    # Animation objects don't render reliably in Streamlit; show the figure.
    st.pyplot(visualizer.fig)

    # ───────── Time‑series
    with st.expander(t.get("time_series_header", "Time‑Series (x, θ1, θ2, u)")):
        fig, axes = plt.subplots(4, 1, figsize=(8, 8), sharex=True)
        
        # Cart position
        axes[0].plot(t_sim, x_sim[:, 0], 'b-')
        axes[0].set_ylabel(t.get("cart_position_label", "Cart Position x (m)"))
        axes[0].grid(True, alpha=0.3)
        
        # Pendulum angles
        axes[1].plot(t_sim, np.rad2deg(x_sim[:, 1]), 'r-', label='θ1')
        axes[1].plot(t_sim, np.rad2deg(x_sim[:, 2]), 'g-', label='θ2')
        axes[1].set_ylabel(t.get("angles_label", "Angles (deg)"))
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # Velocities
        axes[2].plot(t_sim, x_sim[:, 3], 'b--', label='ẋ')
        axes[2].plot(t_sim, x_sim[:, 4], 'r--', label='θ̇1')
        axes[2].plot(t_sim, x_sim[:, 5], 'g--', label='θ̇2')
        axes[2].set_ylabel(t.get("velocities_label", "Velocities"))
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        # Control input
        axes[3].plot(t_sim[:-1], u_sim, 'k-')
        axes[3].set_ylabel(t.get("control_input_label", "Control Input u (N)"))
        axes[3].set_xlabel(t.get("time_label", "Time (s)"))
        axes[3].grid(True, alpha=0.3)
        
        # Add disturbance visualization if active
        if disturbance_function is not None:
            d_values = [disturbance_function(t) for t in t_sim[:-1]]
            axes[3].plot(t_sim[:-1], d_values, 'orange', linestyle='--', label='Disturbance')
            axes[3].legend()
        
        fig.tight_layout()
        st.pyplot(fig)

    # ───────── Performance analysis (NEW)
    st.subheader(t.get("performance_header", "Performance Analysis"))
    metrics = _compute_metrics(t_sim, x_sim, u_sim)
    
    cols = st.columns(3)
    with cols[0]:
        st.metric(t.get("settling_time_label", "Settling Time"), f"{metrics['settling_time_s']:.2f} s")
        st.metric(t.get("rms_control_label", "RMS Control"), f"{metrics['rms_control_N']:.2f} N")
    with cols[1]:
        st.metric(t.get("peak_x_label", "Peak |x|"), f"{metrics['peak_abs_x_m']:.3f} m")
        st.metric(t.get("peak_theta1_label", "Peak |θ1|"), f"{metrics['peak_abs_th1_deg']:.1f}°")
    with cols[2]:
        st.metric(t.get("peak_theta2_label", "Peak |θ2|"), f"{metrics['peak_abs_th2_deg']:.1f}°")
        st.metric(t.get("max_u_label", "Max |u|"), f"{metrics['max_abs_u_N']:.1f} N")

    # ───────── Downloads (NEW)
    st.subheader(t.get("download_header", "Download Results"))
    
    # Save time-series figure
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    
    # Create zip file with results
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add the plot
        zf.writestr("time_series.png", buf.getvalue())
        
        # Add metadata
        meta = {
            "controller": controller_sel,
            "parameters": best_params.tolist(),
            "simulation": {
                "duration": sim_duration,
                "dt": sim_dt,
                "initial_state": initial_state.tolist(),
            },
            "disturbance": {
                "enabled": add_disturbance,
                "magnitude": dist_mag if add_disturbance else 0,
                "start_time": dist_start if add_disturbance else 0,
                "duration": dist_duration if add_disturbance else 0,
            } if add_disturbance else None,
            "metrics": metrics,
        }
        zf.writestr("metadata.json", json.dumps(meta, indent=2))
        
        # Add raw data as CSV
        import csv
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["time", "x", "theta1", "theta2", "x_dot", "theta1_dot", "theta2_dot", "u"])
        # Write all steps with control input (N rows)
        for i in range(len(u_sim)):
            writer.writerow([
                t_sim[i], x_sim[i, 0], x_sim[i, 1], x_sim[i, 2],
                x_sim[i, 3], x_sim[i, 4], x_sim[i, 5], u_sim[i]
            ])
        # Append final state vector without a corresponding control value
        writer.writerow([
            t_sim[-1], x_sim[-1, 0], x_sim[-1, 1], x_sim[-1, 2],
            x_sim[-1, 3], x_sim[-1, 4], x_sim[-1, 5], ''
        ])
        zf.writestr("simulation_data.csv", csv_buf.getvalue())
    
    zip_buf.seek(0)
    st.download_button(
        label=t.get("download_button", "Download Results (ZIP)"),
        data=zip_buf,
        file_name="pendulum_simulation_results.zip",
        mime="application/zip",
    )

    # ───────── RTL fix
    if st.session_state.lang == "فارسی":
        st.markdown("<style>div[data-testid='stSidebar'] > div {direction: rtl;}</style>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
#======================================================================================================================\\\