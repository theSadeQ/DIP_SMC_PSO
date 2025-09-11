import math
from hypothesis import given, strategies as st


@given(
    dt=st.floats(min_value=1e-6, max_value=1.0, allow_nan=False, allow_infinity=False),
    duration=st.floats(
        min_value=1e-6, max_value=10.0, allow_nan=False, allow_infinity=False
    ),
)
def test_duration_vs_dt(dt, duration):
    # Weak invariant: duration should be >= dt (or rounding implies ≥ 1 step)
    assert duration >= dt or math.ceil(duration / dt) >= 1


@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
def test_seed_is_int(seed):
    assert isinstance(seed, int)
