from pathlib import Path

path = Path("benchmarks/integration/numerical_methods.py")
text = path.read_text()

# Restore imports to only DIPDynamics (remove compute_simplified_dynamics_numba)
text = text.replace('from src.core.dynamics import DIPDynamics, compute_simplified_dynamics_numba\n', 'from src.core.dynamics import DIPDynamics\n')

# Remove helper function _build_numba_params
import re
text = re.sub(r"\n\ndef _build_numba_params\(config\).*?\n\nclass EulerIntegrator:", "\n\nclass EulerIntegrator:\n", text, flags=re.S)

# Update Euler integrate to use compute_dynamics
text = re.sub(
    r"        start_time = time.time\(\)\n        params = _build_numba_params\(self\.dynamics\.config\)\n\n        # Main integration loop\n        for i in range\(n_steps - 1\):\n            if controller is not None:\n                u, last_u, history = controller.compute_control\(states\[i\], last_u, history\)\n            else:\n                u = 0\.0\n\n            controls\[i\] = u\n            state_dot = compute_simplified_dynamics_numba\(states\[i\], u, \*params\)\n            states\[i \+ 1\] = states\[i\] \+ dt \* state_dot\n\n        elapsed = time.time\(\) - start_time",
    "        start_time = time.time()\n\n        # Main integration loop\n        for i in range(n_steps - 1):\n            if controller is not None:\n                u, last_u, history = controller.compute_control(states[i], last_u, history)\n            else:\n                u = 0.0\n\n            controls[i] = u\n            dyn_result = self.dynamics.compute_dynamics(states[i], np.array([u], dtype=float))\n            if not getattr(dyn_result, 'success', True):\n                raise RuntimeError(f'Euler integration failed at step {i}: {dyn_result.info if hasattr(dyn_result, "info") else "unknown error"}')\n            state_dot = dyn_result.state_derivative\n            states[i + 1] = states[i] + dt * state_dot\n\n        elapsed = time.time() - start_time",
    text
)

# Update RK4 integrate to use compute_dynamics
text = re.sub(
    r"        start_time = time.time\(\)\n        params = _build_numba_params\(self\.dynamics\.config\)\n\n        # Main integration loop\n        for i in range\(n_steps - 1\):\n            if controller is not None:\n                u, last_u, history = controller.compute_control\(states\[i\], last_u, history\)\n            else:\n                u = 0\.0\n\n            controls\[i\] = u\n            k1 = compute_simplified_dynamics_numba\(states\[i\], u, \*params\)\n            k2 = compute_simplified_dynamics_numba\(states\[i\] \+ 0\.5 \* dt \* k1, u, \*params\)\n            k3 = compute_simplified_dynamics_numba\(states\[i\] \+ 0\.5 \* dt \* k2, u, \*params\)\n            k4 = compute_simplified_dynamics_numba\(states\[i\] \+ dt \* k3, u, \*params\)\n            states\[i \+ 1\] = states\[i\] \+ (dt / 6\.0) \* (k1 \+ 2\.0 \* k2 \+ 2\.0 \* k3 \+ k4)\n\n        elapsed = time.time\(\) - start_time",
    "        start_time = time.time()\n\n        # Main integration loop\n        for i in range(n_steps - 1):\n            if controller is not None:\n                u, last_u, history = controller.compute_control(states[i], last_u, history)\n            else:\n                u = 0.0\n\n            controls[i] = u\n            control_vec = np.array([u], dtype=float)\n            k1 = self._compute_derivative(states[i], control_vec)\n            k2 = self._compute_derivative(states[i] + 0.5 * dt * k1, control_vec)\n            k3 = self._compute_derivative(states[i] + 0.5 * dt * k2, control_vec)\n            k4 = self._compute_derivative(states[i] + dt * k3, control_vec)\n            states[i + 1] = states[i] + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)\n\n        elapsed = time.time() - start_time",
    text
)

# Add helper method _compute_derivative to both integrators
text = text.replace(
    "        return IntegrationResult(\n            t=t, states=states, controls=controls,\n            elapsed_time=elapsed, method='Euler',\n            dt=dt, n_steps=n_steps\n        )\n\n\nclass RK4Integrator:",
    "        return IntegrationResult(\n            t=t, states=states, controls=controls,\n            elapsed_time=elapsed, method='Euler',\n            dt=dt, n_steps=n_steps\n        )\n\n    def _compute_derivative(self, state: np.ndarray, control_vec: np.ndarray) -> np.ndarray:\n        dyn_result = self.dynamics.compute_dynamics(state, control_vec)\n        if not getattr(dyn_result, 'success', True):\n            raise RuntimeError(dyn_result.info if hasattr(dyn_result, 'info') else 'Dynamics computation failed')\n        return dyn_result.state_derivative\n\n\nclass RK4Integrator:",
)

text = text.replace(
    "        return IntegrationResult(\n            t=t, states=states, controls=controls,\n            elapsed_time=elapsed, method='RK4',\n            dt=dt, n_steps=n_steps\n        )\n\n\n\nclass AdaptiveRK45Integrator:",
    "        return IntegrationResult(\n            t=t, states=states, controls=controls,\n            elapsed_time=elapsed, method='RK4',\n            dt=dt, n_steps=n_steps\n        )\n\n    def _compute_derivative(self, state: np.ndarray, control_vec: np.ndarray) -> np.ndarray:\n        dyn_result = self.dynamics.compute_dynamics(state, control_vec)\n        if not getattr(dyn_result, 'success', True):\n            raise RuntimeError(dyn_result.info if hasattr(dyn_result, 'info') else 'Dynamics computation failed')\n        return dyn_result.state_derivative\n\n\nclass AdaptiveRK45Integrator:",
)

path.write_text(text)
