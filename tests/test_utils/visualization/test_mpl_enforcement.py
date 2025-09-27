import pytest

def test_backend_is_agg():
    import matplotlib
    assert matplotlib.get_backend().lower() == "agg"

def test_show_is_banned():
    import matplotlib.pyplot as plt
    with pytest.raises(AssertionError, match="banned in tests"):
        plt.show()
