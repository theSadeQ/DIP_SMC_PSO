#============================================================================================\\\
#=========================== tests/test_controllers/test_sta_smc.py =========================\\\
#============================================================================================\\\
import numpy as np
import pytest
from src.controllers.sta_smc import SuperTwistingSMC
from src.core.dynamics import DoubleInvertedPendulum
from src.core.vector_sim import simulate_system_batch


class IllConditionedDynamics:
    """Mock dynamics model returning an inertia matrix with a large condition number."""

    def _compute_physics_matrices(self, state: np.ndarray):
        # Construct a diagonal inertia matrix with one very large element
        # to produce an ill‑conditioned matrix (cond ~1e8).
        M = np.diag([1.1e8, 1.0, 1.0])
        C = np.zeros((3, 3), dtype=float)
        G = np.zeros(3, dtype=float)
        return M, C, G


@pytest.fixture
def dynamics(physics_params):
    return DoubleInvertedPendulum(physics_params)

def test_finite_time_convergence(dynamics, timeout=2.0):
    """STA sliding surface σ should converge below 1e-4 in ≤ 2 s."""
    np.random.seed(42)  # For reproducibility

    dt = 0.001
    gains = [1.18495, 47.7040, 1.0807, 7.4019, 46.9200, 0.6699]
    batch_size = 20
    std_angle = 0.05

    # Define the controller factory
    def controller_factory(particle_gains):
        return SuperTwistingSMC(gains=particle_gains, dt=dt, dynamics_model=dynamics)

    # All particles use the same gains
    particle_gains = np.tile(np.asarray(gains), (batch_size, 1))

    # Create a batch of initial states with noise on angles
    central_state = np.array([0.0, 0.1, 0.1, 0.0, 0.0, 0.0])
    initial_states_batch = np.tile(central_state, (batch_size, 1))
    initial_states_batch[:, 1:3] += np.random.normal(0, std_angle, (batch_size, 2))

    # Run the batch simulation
    t, _, _, sigma_b = simulate_system_batch(
        controller_factory=controller_factory,
        particles=particle_gains,
        sim_time=timeout,
        dt=dt,
        initial_state=initial_states_batch,
    )

    # Analyze convergence across the batch
    grace_period_steps = int(0.1 / dt)
    max_sigma_per_step = np.max(np.abs(sigma_b), axis=0)
    converged_indices = np.where(max_sigma_per_step[grace_period_steps:] < 1e-4)[0]

    if len(converged_indices) > 0:
        first_convergence_index = converged_indices[0] + grace_period_steps
        convergence_time = t[first_convergence_index]
        assert convergence_time < timeout
    else:
        final_max_sigma = np.max(np.abs(sigma_b[:, -1]))
        pytest.fail(f"STA did not converge within {timeout}s. Final max σ={final_max_sigma:.2e}")

def test_initialize_and_compute_control(dynamics):
    """Smoke test for API contract of STA."""
    # ✅ Using the same PSO-optimized gains for consistency
    ctrl = SuperTwistingSMC(
        gains=[1.1850,47.7040,1.0807,7.4019,46.9200,0.6699],
        dt=0.001,
        dynamics_model=dynamics,
    )
    state = np.zeros(6, dtype=float)

    sv = ctrl.initialize_state()
    hist = ctrl.initialize_history()

    u, sv2, hist2 = ctrl.compute_control(state, sv, hist)
    assert isinstance(u, float)
    assert isinstance(sv2, tuple)
    assert isinstance(hist2, dict)

def test_sta_smc_equivalent_control_singular():
    """When the inertia matrix is ill‑conditioned, SuperTwistingSMC should return u_eq=0.0."""
    dyn = IllConditionedDynamics()
    ctrl = SuperTwistingSMC(
        gains=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        dt=0.01,
        max_force=10.0,
        damping_gain=0.0,
        boundary_layer=0.1,
        dynamics_model=dyn,
    )
    state = np.zeros(6, dtype=float)
    u_eq = ctrl._compute_equivalent_control(state)
    assert u_eq == 0.0

class DummyDyn:
    def __init__(self, M, C=None, G=None):
        self._M = M
        self._C = C if C is not None else np.zeros((3, 3))
        self._G = G if G is not None else np.zeros(3)
    def _compute_physics_matrices(self, state): return self._M, self._C, self._G

def test_equivalent_control_handles_singularity(caplog):
    M = np.eye(3); M[0,0] = 1e-12  # ill-conditioned → cond ≫ 1e9
    ctrl = SuperTwistingSMC(gains=[2.0,3.0], dt=0.01, max_force=100.0, damping_gain=0.0, boundary_layer=1e-3, dynamics_model=DummyDyn(M))
    state = np.zeros(6)
    u_eq = ctrl._compute_equivalent_control(state)
    assert u_eq == 0.0

def test_equivalent_control_clamps_large_value(caplog):
    M = np.eye(3)
    # Make G huge to drive u_eq large; controllability scalar is  L @ I @ B = Lx = 0.0 -> use small off-diagonal to avoid zero
    dyn = DummyDyn(M, C=np.zeros((3,3)), G=np.array([0.0, 0.0, 1e6]))
    ctrl = SuperTwistingSMC(gains=[2.0,3.0,5.0,3.0,2.0,1.0], dt=0.01, max_force=10.0, damping_gain=0.0, boundary_layer=1e-3, dynamics_model=dyn)
    state = np.array([0,0.1,0.1,0,0,0], dtype=float)
    u_eq = ctrl._compute_equivalent_control(state)
    assert abs(u_eq) <= 20.0  # clamped to ±2*max_force
#==============================================================================================================================================\\\
