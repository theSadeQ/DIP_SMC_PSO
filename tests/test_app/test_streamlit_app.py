#=================================================================================================\\\
#=========================== tests/test_app/test_streamlit_app.py ================================\\\
#=================================================================================================\\\
import types, sys, io
import importlib

class SessionState:
    """Mock SessionState that supports both dict-like and attribute access.
    
    Why: Streamlit's actual session_state is a special proxy object that supports
    both styles of access. This mock mimics that behavior to prevent AttributeError
    when the app code uses attribute-style assignment.
    """
    def __init__(self):
        self._data = {}
    
    def __getitem__(self, key):
        return self._data.get(key)
    
    def __setitem__(self, key, value):
        self._data[key] = value
    
    def __contains__(self, key):
        return key in self._data
    
    def __getattr__(self, key):
        # Called when attribute doesn't exist
        if key.startswith('_'):
            # Avoid infinite recursion for private attributes
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")
        return self._data.get(key)
    
    def __setattr__(self, key, value):
        # Special handling for internal attributes
        if key.startswith('_'):
            super().__setattr__(key, value)
        else:
            self._data[key] = value
    
    def get(self, key, default=None):
        """Mimic dict.get() method for compatibility."""
        return self._data.get(key, default)

class MockColumn:
    """A mock column object that supports the context manager protocol."""
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def metric(self, *args, **kwargs):
        """Mock metric method to prevent errors inside the 'with' block."""
        pass

def make_fake_streamlit():
    st = types.SimpleNamespace()
    # Use our custom SessionState instead of a plain dict
    st.session_state = SessionState()
    
    def cache_data(fn): return fn
    class Spinner:
        def __enter__(self): return None
        def __exit__(self, *a): return False
    
    # Create more flexible mocks that accept both positional and keyword arguments
    sidebar = types.SimpleNamespace(
        header=lambda *args, **kwargs: None,
        subheader=lambda *args, **kwargs: None,
        checkbox=lambda *args, **kwargs: kwargs.get('value', False),
        selectbox=lambda *args, **kwargs: (kwargs.get("options") or args[1] if len(args) > 1 else ["SMC"])[0],
        button=lambda *args, **kwargs: False,
        write=lambda *args, **kwargs: None,
        code=lambda *args, **kwargs: None,
        # Fixed: slider now accepts positional arguments
        slider=lambda *args, **kwargs: kwargs.get('value', args[3] if len(args) > 3 else 0.01),
        text_input=lambda *args, **kwargs: kwargs.get("value", "0,0,0"),
        text_area=lambda *args, **kwargs: kwargs.get("value", "0,0,0,0,0,0"),  # 6D state
    )
    st.sidebar = sidebar
    st.cache_data = cache_data
    st.set_page_config = lambda *args, **kwargs: None
    st.markdown = lambda *args, **kwargs: None
    st.title = lambda *args, **kwargs: None
    st.write = lambda *args, **kwargs: None
    st.subheader = lambda *args, **kwargs: None
    st.pyplot = lambda *args, **kwargs: None
    st.metric = lambda *args, **kwargs: None
    st.download_button = lambda *args, **kwargs: None
    st.success = lambda *args, **kwargs: None
    st.error = lambda *args, **kwargs: None
    st.warning = lambda *args, **kwargs: None
    # FIX: Return a list of MockColumn objects that support the `with` statement.
    st.columns = lambda n: [MockColumn() for _ in range(n)]
    
    class Expander:
        def __enter__(self): return None
        def __exit__(self, *a): return False
    st.expander = lambda *args, **kwargs: Expander()
    st.spinner = lambda *args, **kwargs: Spinner()
    
    return st

def install_fake_modules(monkeypatch):
    # Fake streamlit
    sys.modules['streamlit'] = make_fake_streamlit()

    # Fake yaml.safe_load for translations - provide more complete translations
    import yaml
    monkeypatch.setattr(yaml, "safe_load", lambda *_: {
        "English": {
            "sidebar_header": "Controls",
            "controller_select": "Controller",
            "dynamics_header": "1. Dynamics Model",
            "use_full_label": "Use Full Nonlinear Dynamics",
            "use_full_help": "Use the complete, more accurate dynamics model.",
            "controller_label": "Controller Type",
            "pso_header": "Optimization",
            "run_button": "Run PSO",
            "spinner_msg": "Optimizing...",
            "success_msg": "Optimization succeeded.",
            "cost_metric": "Best Cost",
            "opt_fail": "Optimization failed to find a valid solution.",
            "params_header": "Controller Gains",
            "sim_settings_header": "Simulation Settings",
            "sim_duration_label": "Simulation Duration (s)",
            "sim_dt_label": "Time Step dt (s)",
            "initial_state_label": "Initial State (comma‑separated)",
            "initial_state_help": "[x, θ1, θ2, ẋ, θ̇1, θ̇2]",
            "disturbance_header": "Disturbance",
            "add_disturbance_label": "Add Disturbance",
            "dist_magnitude_label": "Magnitude (N)",
            "dist_start_label": "Start Time (s)",
            "dist_duration_label": "Duration (s)",
            "title": "Pendulum Control Dashboard",
            "intro": "Real‑time PSO‑tuned controllers for double‑inverted pendulum control.",
            "animation_header": "Simulation Animation",
            "time_series_header": "Time‑Series (x, θ1, θ2, u)",
            "cart_position_label": "Cart Position x (m)",
            "angles_label": "Angles (deg)",
            "velocities_label": "Velocities",
            "control_input_label": "Control Input u (N)",
            "time_label": "Time (s)",
            "performance_header": "Performance Analysis",
            "settling_time_label": "Settling Time",
            "rms_control_label": "RMS Control",
            "peak_x_label": "Peak |x|",
            "peak_theta1_label": "Peak |θ1|",
            "peak_theta2_label": "Peak |θ2|",
            "max_u_label": "Max |u|",
            "download_header": "Download Results",
            "download_button": "Download Results (ZIP)"
        },
        "فارسی": {}  # Empty Persian translations
    }, raising=False)

    # Fake src.* modules used by the app
    class Cfg:
        class Simulation:
            duration = 2.0
            dt = 0.01
            initial_state = [0.0, 0.1, -0.1, 0.0, 0.0, 0.0]  # 6D state vector
            use_full_dynamics = False
        class Physics:
            def model_dump(self): return {}
        simulation = Simulation()
        physics = Physics()
        controllers = {"SMC": {}}
        controller_defaults = {"SMC": {"gains": [1.0, 2.0, 3.0]}}
        global_seed = None  # Add seed attribute

    src = types.ModuleType("src")
    sys.modules["src"] = src

    cfg_mod = types.ModuleType("src.config")
    cfg_mod.load_config = lambda *args, **kwargs: Cfg()
    sys.modules["src.config"] = cfg_mod

    ctrl_mod = types.ModuleType("src.controllers.factory")
    class DummyController:
        def compute_control(self, state, sv, hist): return 0.0, sv, hist
    ctrl_mod.create_controller = lambda *args, **kwargs: DummyController()
    sys.modules["src.controllers.factory"] = ctrl_mod

    dyn_mod = types.ModuleType("src.core.dynamics")
    class DIP:
        state_dim = 6  # Changed to 6 to match actual state dimension
        l1 = 0.5  # Link 1 length
        l2 = 0.5  # Link 2 length  
        L1 = 1.0  # Distance to first pendulum
        L2 = 1.5  # Distance to second pendulum
        m0 = 1.0  # Cart mass
        m1 = 0.5  # Pendulum 1 mass
        m2 = 0.5  # Pendulum 2 mass
        
        def __init__(self, *args, **kwargs): 
            # If physics params are provided, use them
            if args and hasattr(args[0], 'model_dump'):
                params = args[0].model_dump()
                for key, value in params.items():
                    setattr(self, key, value)
        
        def step(self, s, u, dt): return s  # simple hold
        
        def default_state(self): 
            import numpy as np
            return np.zeros(6)
    dyn_mod.DIPDynamics = DIP
    sys.modules["src.core.dynamics"] = dyn_mod

    dyn_full_mod = types.ModuleType("src.core.dynamics_full")
    dyn_full_mod.FullDIPDynamics = dyn_mod.DIPDynamics
    sys.modules["src.core.dynamics_full"] = dyn_full_mod

    sim_runner = types.ModuleType("src.core.simulation_runner")
    def run_simulation(controller, dynamics_model, sim_time, dt, initial_state):
        import numpy as np
        n = int(sim_time / dt)
        t = np.linspace(0, sim_time, n+1)  # Fixed: use sim_time instead of n*dt
        x = np.tile(np.asarray(initial_state).reshape(1, -1), (n+1, 1))
        u = np.zeros(n)
        return t, x, u
    sim_runner.run_simulation = run_simulation
    sys.modules["src.core.simulation_runner"] = sim_runner

    pso_mod = types.ModuleType("src.optimizer.pso_optimizer")
    class PSOTuner:
        def __init__(self, *args, **kwargs): pass
        def optimise(self, *args, **kwargs): 
            return {"best_cost": float("inf"), "best_pos": [1.0, 2.0, 3.0]}
    pso_mod.PSOTuner = PSOTuner
    sys.modules["src.optimizer.pso_optimizer"] = pso_mod

    viz_mod = types.ModuleType("src.utils.visualization")
    class Visualizer:
        def __init__(self, model): 
            import matplotlib.pyplot as plt
            self.fig, self.ax = plt.subplots()
            # Store model reference (DisturbedDynamics will forward attribute access)
            self.model = model
        def animate(self, t, x, u, dt=0.01):
            self.ani = object()
            return self.ani
    viz_mod.Visualizer = Visualizer
    sys.modules["src.utils.visualization"] = viz_mod

    # Mock the DisturbedDynamics class since streamlit_app defines it
    class DisturbedDynamics:
        """Mock wrapper that adds disturbance to dynamics model.
        
        This mock properly forwards attribute access to the base model,
        which is critical for the Visualizer that needs to access model
        parameters like L1, l1, l2, etc.
        """
        def __init__(self, base_model, disturbance_func=None):
            self.base_model = base_model
            self.disturbance_func = disturbance_func
            self.t = 0.0
        
        def step(self, state, u, dt):
            # Add disturbance if function provided
            if self.disturbance_func:
                d = self.disturbance_func(self.t)
                u = u + d
            self.t += dt
            return self.base_model.step(state, u, dt)
        
        def __getattr__(self, name):
            # Forward attribute access to base model
            # This is crucial for Visualizer to access L1, l1, l2, etc.
            return getattr(self.base_model, name)
    
    # Inject our DisturbedDynamics mock into streamlit_app's namespace
    import streamlit_app
    streamlit_app.DisturbedDynamics = DisturbedDynamics

def test_app_import_and_main(monkeypatch):
    install_fake_modules(monkeypatch)
    # Ensure CSS loader doesn't try filesystem
    import streamlit_app
    importlib.reload(streamlit_app)
    streamlit_app.load_css = lambda *args, **kwargs: None

    # Replace file open inside load_translations
    monkeypatch.setattr(streamlit_app, "open", lambda *args, **kwargs: io.StringIO("English: {}\n"), raising=False)

    # Run
    streamlit_app.main()
#==================================================================================================================\\\