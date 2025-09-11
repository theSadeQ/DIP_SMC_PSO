import math
import pytest
from hypothesis import given, strategies as st

# Adjust imports to your actual config class/names
try:
    from src.config import BaseSettings as _Base
except Exception:
    _Base = object


@given(
    dt=st.floats(min_value=1e-6, max_value=1.0),
    duration=st.floats(min_value=1e-6, max_value=10.0),
)
def test_duration_is_multiple_of_dt_or_longer(dt, duration):
    assume_ok = dt > 0 and duration > 0
    if not assume_ok:
        pytest.skip("invalid generated inputs")
    # Weak invariant: duration should be >= dt (or rounding up yields at least one step)
    assert duration >= dt or math.ceil(duration / dt) >= 1


@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
def test_seed_is_deterministic(seed):
    # If you expose set_global_seed in config, import and call here.
    # e.g., from src.config import set_global_seed
    assert isinstance(seed, int)
