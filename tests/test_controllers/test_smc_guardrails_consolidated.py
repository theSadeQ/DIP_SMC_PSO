import sys, pathlib, importlib, numpy as np, pytest

factory = importlib.import_module("src.controllers.factory")

def test_smc_guardrails_and_smokes(monkeypatch):
    class Dyn:
        def __init__(self, physics): pass

    # a) classical: boundary_layer <= 0 -> factory-time error
    monkeypatch.setattr(factory, "DoubleInvertedPendulum", Dyn, raising=False)
    class FakeClassical:
        def __init__(self, **kwargs): pass
    monkeypatch.setattr(factory, "ClassicalSMC", FakeClassical, raising=False)

    class CfgBadBL:
        class Sim: use_full_dynamics = False; dt = 0.01
        simulation = Sim(); controllers = {"classical_smc": {"gains":[1,1,1], "boundary_layer": 0.0}}
        controller_defaults = {}
    with pytest.raises(factory.ConfigValueError):
        factory.create_controller("classical_smc", config=CfgBadBL(), gains=None)

    # b) classical smoke: default boundary layer = 0.01 and compute finite
    class RealisticClassical:
        def __init__(self, **kwargs): self.boundary_layer = kwargs.get("boundary_layer", 0.0)
        def compute_control(self, sigma=0.1):
            from src.utils.control_primitives import saturate
            return float(saturate(sigma, self.boundary_layer, method="linear"))
    monkeypatch.setattr(factory, "ClassicalSMC", RealisticClassical, raising=False)
    class CfgOk:
        class Sim: use_full_dynamics = False; dt = 0.01
        simulation = Sim(); physics = object()
        controllers = {"classical_smc": {"gains":[1,1,1]}}  # no boundary_layer -> default 0.01
        controller_defaults = {}
    ctrl = factory.create_controller("classical_smc", config=CfgOk(), gains=None)
    assert getattr(ctrl, "boundary_layer", None) == 0.01
    assert np.isfinite(ctrl.compute_control(0.1))

    # c) STA smoke with supplied boundary layer
    class FakeSTA:
        def __init__(self, **kwargs): self.boundary_layer = kwargs.get("boundary_layer", 0.0)
        def compute_control(self, sigma=0.1):
            from src.utils.control_primitives import saturate
            return float(saturate(sigma, self.boundary_layer, method="linear"))
    monkeypatch.setattr(factory, "SuperTwistingSMC", FakeSTA, raising=False)
    class CfgSTA:
        class Sim: use_full_dynamics = False; dt = 0.01
        simulation = Sim(); physics = object()
        controllers = {"sta_smc": {"gains":[1,1,1], "boundary_layer": 0.05}}
        controller_defaults = {}
    ctrl2 = factory.create_controller("sta_smc", config=CfgSTA(), gains=None)
    assert getattr(ctrl2, "boundary_layer", None) == 0.05
    assert np.isfinite(ctrl2.compute_control(0.1))

    # d) swing-up self recursion guard
    class StubSwing: 
        def __init__(self, **kwargs): pass
    monkeypatch.setattr(factory, "SwingUpSMC", StubSwing, raising=False)
    class CfgSelf:
        class Sim: use_full_dynamics = False; dt = 0.01
        simulation = Sim(); controllers = {"swing_up_smc": {"stabilizing_controller": "swing_up_smc"}}
    with pytest.raises(factory.ConfigValueError):
        factory.create_controller("swing_up_smc", config=CfgSelf(), gains=None)

    # e) swing-up inherits dt from simulation
    class StubSwing2:
        def __init__(self, **kwargs): self.dt_received = kwargs.get("dt")
    monkeypatch.setattr(factory, "SwingUpSMC", StubSwing2, raising=False)
    class FakeClassical2:
        max_force = 123.0
        def __init__(self, **kwargs): pass
    monkeypatch.setattr(factory, "ClassicalSMC", FakeClassical2, raising=False)
    class CfgDt:
        class Sim: use_full_dynamics = False; dt = 0.02
        simulation = Sim(); physics = object()
        controllers = {"swing_up_smc": {"stabilizing_controller": "classical_smc"},
                       "classical_smc": {"gains":[1,1,1], "boundary_layer": 0.05}}
        controller_defaults = {}
    ctrl3 = factory.create_controller("swing_up_smc", config=CfgDt(), gains=None)
    assert getattr(ctrl3, "dt_received", None) == 0.02
