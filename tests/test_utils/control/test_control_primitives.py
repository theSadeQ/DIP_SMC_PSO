# tests/test_utils/test_control_primitives.py
import numpy as np
import pytest
from src.utils import saturate

def test_saturate_tanh():
    assert saturate(10, 1) == pytest.approx(np.tanh(10))
    assert saturate(-10, 1) == pytest.approx(np.tanh(-10))
    assert saturate(0, 1) == 0.0

def test_saturate_linear():
    assert saturate(10, 1, method='linear') == 1.0
    assert saturate(-10, 1, method='linear') == -1.0
    assert saturate(0.5, 1, method='linear') == 0.5
    assert saturate(-0.5, 1, method='linear') == -0.5

def test_saturate_zero_boundary():
    with pytest.raises(ValueError, match="boundary layer epsilon must be positive"):
        saturate(10, 0)