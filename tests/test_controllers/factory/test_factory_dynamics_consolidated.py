#==========================================================================================\\
#============== tests/test_controllers/test_factory_dynamics_consolidated.py =============\\
#==========================================================================================\\
import sys, pathlib, importlib, pytest

factory = importlib.import_module("src.controllers.factory")

def test_factory_and_dynamics_core(monkeypatch):
    # a) unknown controller lists available (sorted)
    class Dyn: 
        def __init__(self, physics): pass
    monkeypatch.setattr(factory, "DoubleInvertedPendulum", Dyn, raising=False)
    class CfgA:
        class Sim: use_full_dynamics = False; dt = 0.01
        simulation = Sim(); controllers = {"zeta": {}, "alpha": {}, "beta": {}}
        controller_defaults = {}
    with pytest.raises(ValueError) as e1:
        factory.create_controller("does_not_exist", config=CfgA(), gains=None)
    assert "Available: alpha, beta, zeta" in str(e1.value)

    # b) empty controllers_map UX
    class CfgEmpty: controllers = {}
    with pytest.raises(ValueError) as e2:
        factory.create_controller("anything", config=CfgEmpty(), gains=None)
    assert "Available: none configured" in str(e2.value)

    # c) dynamics guards: DIP missing when not full
    monkeypatch.setattr(factory, "DoubleInvertedPendulum", None, raising=False)
    class CfgD:
        class Sim: use_full_dynamics = False; dt = 0.01
        simulation = Sim(); controllers = {"classical_smc": {"gains":[1,1,1], "boundary_layer": 0.05}}
    with pytest.raises(ImportError):
        factory.create_controller("classical_smc", config=CfgD(), gains=None)

    # d) dynamics guards: FullDIP missing when full
    monkeypatch.setattr(factory, "DoubleInvertedPendulum", Dyn, raising=False)
    monkeypatch.setattr(factory, "FullDIPDynamics", None, raising=False)
    class CfgF:
        class Sim: use_full_dynamics = True; dt = 0.01
        simulation = Sim(); controllers = {"classical_smc": {"gains":[1,1,1], "boundary_layer": 0.05}}
    with pytest.raises(ImportError):
        factory.create_controller("classical_smc", config=CfgF(), gains=None)

    # e) shared params validation
    monkeypatch.setattr(factory, "FullDIPDynamics", Dyn, raising=False)
    class FakeCtrl: 
        def __init__(self, **kwargs): pass
    monkeypatch.setattr(factory, "ClassicalSMC", FakeCtrl, raising=False)
    class CfgBadDt:
        class Sim: use_full_dynamics = False; dt = 0.0
        simulation = Sim(); controllers = {"classical_smc": {"gains":[1,1,1], "boundary_layer": 0.05}}
        controller_defaults = {}
    with pytest.raises(factory.ConfigValueError) as e3:
        factory.create_controller("classical_smc", config=CfgBadDt(), gains=None)
    assert "dt must be > 0" in str(e3.value)

    # f) _as_dict normalization
    class PydLike:
        def __init__(self, d): self._d = d
        def model_dump(self, exclude_unset=True): return dict(self._d)
    out = factory._as_dict(PydLike({"a":1}))
    assert out == {"a":1}
