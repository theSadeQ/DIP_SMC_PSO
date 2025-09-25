import sys, pathlib, numpy as np, pytest

from src.utils import saturate

def test_control_primitives_core_behaviors():
    # scalar tanh + linear basic
    assert np.isclose(saturate(0.0, 0.1), 0.0)
    assert saturate(100.0, 0.1) > 0.999
    assert saturate(-100.0, 0.1) < -0.999
    assert saturate(0.0, 1.0, method="linear") == 0.0
    assert saturate(10.0, 1.0, method="linear") == 1.0
    assert saturate(-10.0, 1.0, method="linear") == -1.0

    # epsilon must be positive
    with pytest.raises(ValueError):
        saturate(1.0, 0.0)
    with pytest.raises(ValueError):
        saturate(1.0, -1.0)

    # vector shape + bounds (linear clips to [-1,1])
    x = np.array([-10., -1., 0., 0.5, 2.0])
    y = saturate(x, 1.0, method="linear")
    assert y.shape == x.shape
    assert np.all(y >= -1.0) and np.all(y <= 1.0)

    # property-ish: random vectors
    rng = np.random.default_rng(123)
    x = rng.normal(size=200)
    eps = float(rng.uniform(0.01, 1.0))
    y = saturate(x, eps, method="linear")
    assert np.all(y >= -1.0) and np.all(y <= 1.0)
    y2 = saturate(x, eps, method="tanh")
    assert np.all(np.abs(y2) < 1.0)
