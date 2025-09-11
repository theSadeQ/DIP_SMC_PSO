import sys, pathlib, importlib, pytest

factory = importlib.import_module("src.controllers.factory")

def test_mpc_optional_dep_and_param_validation(monkeypatch):
    class Dyn:
        def __init__(self, physics): pass
    monkeypatch.setattr(factory, "DoubleInvertedPendulum", Dyn, raising=False)

    # a) optional dependency guard
    monkeypatch.setattr(factory, "MPCController", None, raising=False)
    class CfgA:
        class Sim: use_full_dynamics = False; dt = 0.01
        simulation = Sim(); physics = object()
        controllers = {"mpc_controller": {"horizon": 5, "q_x": 1.0, "q_theta": 1.0, "r_u": 0.1}}
        controller_defaults = {}
    with pytest.raises(ImportError) as e1:
        factory.create_controller("mpc_controller", config=CfgA(), gains=None)
    assert "missing optional dependency" in str(e1.value)

    # b) parameter validation (use stub MPC to pass construction once validated)
    class MPCStub:
        def __init__(self, **kwargs): pass
    monkeypatch.setattr(factory, "MPCController", MPCStub, raising=False)

    # - horizon type must be int
    class CfgBadHType:
        class Sim: use_full_dynamics = False; dt = 0.01
        simulation = Sim(); controllers = {"mpc_controller": {"horizon": 2.5}}
        controller_defaults = {}
    with pytest.raises(factory.ConfigValueError) as e2:
        factory.create_controller("mpc_controller", config=CfgBadHType(), gains=None)
    assert "horizon must be an integer" in str(e2.value)

    # - horizon >= 1
    class CfgBadH:
        class Sim: use_full_dynamics = False; dt = 0.01
        simulation = Sim(); controllers = {"mpc_controller": {"horizon": 0}}
        controller_defaults = {}
    with pytest.raises(factory.ConfigValueError) as e3:
        factory.create_controller("mpc_controller", config=CfgBadH(), gains=None)
    assert "horizon must be ≥ 1" in str(e3.value)

    # - geometry and weights ranges
    import math
    for mcp in [0.0, -1.0, float("inf")]:
        class CfgB:
            class Sim: use_full_dynamics = False; dt = 0.01
            simulation = Sim(); controllers = {"mpc_controller": {"max_cart_pos": mcp}}
            controller_defaults = {}
        with pytest.raises(factory.ConfigValueError) as e4:
            factory.create_controller("mpc_controller", config=CfgB(), gains=None)
        assert "max_cart_pos must be > 0" in str(e4.value)

    for wkey, val in [("q_x",-1.0), ("q_theta",-0.01), ("r_u",-1e-6)]:
        class CfgW:
            class Sim: use_full_dynamics = False; dt = 0.01
            simulation = Sim(); controllers = {"mpc_controller": {wkey: val}}
            controller_defaults = {}
        with pytest.raises(factory.ConfigValueError) as e5:
            factory.create_controller("mpc_controller", config=CfgW(), gains=None)
        assert f"{wkey} must be ≥ 0" in str(e5.value)
