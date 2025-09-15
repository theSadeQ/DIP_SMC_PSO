#==========================================================================================\\\
#====================================== src/__init__.py ====================================\\\
#==========================================================================================\\\
"""
Expose the top‑level ``src`` package and provide convenient access
to its submodules.

This module exists to ensure that the ``src`` directory is treated as
a proper Python package during test collection.  Without an
``__init__.py`` file, pytest may fail to locate attributes such as
``src.config`` when performing monkeypatching.

In addition to making the package importable, we deliberately expose
the ``config`` submodule as an attribute on the package.  Some tests
refer to ``src.config`` directly when patching configuration loaders
via ``monkeypatch.setattr``.  Importing the submodule here ensures
that ``src.config`` resolves to the actual configuration module,
rather than raising ``AttributeError: module 'src' has no attribute
'config'`` during test execution.

We avoid importing any other submodules by default to prevent
side effects or unnecessary dependencies from being loaded at
package import time.  Users should import submodules explicitly as
needed.
"""

from importlib import import_module
# -----------------------------------------------------------------------------
# Warning filters
#
# Some third‑party dependencies emit noisy warnings during normal operation.
# Suppress specific warnings here to keep test output clean while preserving
# other warnings.  See pytest warnings summary for details.
import warnings

# Suppress matplotlib animation warning when an animation object is garbage
# collected before being rendered.  The Visualizer stores the animation on
# itself, but if the calling code does not retain a reference, matplotlib
# emits a UserWarning.  This filter silences that warning globally.
warnings.filterwarnings(
    "ignore",
    message="Animation was deleted without rendering anything",
    category=UserWarning,
    module="matplotlib.animation",
)

# Suppress a PendingDeprecationWarning from the osqp solver interface.  The
# default value of ``raise_error`` will change in a future release; our
# MPCController explicitly handles solver failure by falling back, so we
# choose to silence this noisy warning.
warnings.filterwarnings(
    "ignore",
    category=PendingDeprecationWarning,
    module="osqp.interface",
)

# Expose the configuration module as an attribute.  Importing
# ``src.config`` here ensures that monkeypatching via ``src.config``
# operates on the correct module.  See tests that call
# ``monkeypatch.setattr('src.config.load_config', ...)``.
try:
    config = import_module('.config', __package__)
except Exception:
    # If the configuration module fails to import (e.g., due to
    # intentionally missing dependencies in a test environment), define a
    # placeholder object so that ``src.config`` always exists.  The
    # placeholder allows attribute assignment via monkeypatching but will
    # otherwise raise the original import exception when attributes are
    # accessed.  This avoids AttributeError: module 'src' has no
    # attribute 'config' while preserving the original failure mode.
    import types

    class _ConfigPlaceholder(types.SimpleNamespace):
        # Capture the exception to raise when an undefined attribute is
        # accessed.  ``exc`` is closed over from the except block.
        def __init__(self, exc: Exception):
            super().__init__()
            self.__exc = exc

        def __getattr__(self, item):
            # When any attribute other than those explicitly set via
            # monkeypatching is accessed, re-raise the original import
            # exception to signal that the real config could not be
            # imported.  This mirrors the behavior one would see if
            # ``src.config`` failed to import normally.
            raise self.__exc

    # Use the caught exception from the outer scope to initialize the
    # placeholder.  ``exc_info()`` is not available here so reuse
    # Exception from except.
    import sys
    # Capture the current exception info.  sys.exc_info()[1] holds the
    # exception instance that was raised when attempting to import
    # src.config.  If no exception is available (should not happen
    # because we are in an except block), default to a generic
    # ImportError.
    exc = sys.exc_info()[1] or ImportError("src.config could not be imported")
    config = _ConfigPlaceholder(exc)

# Export only the explicitly exposed names from this package.  Keeping
# ``__all__`` small avoids accidentally re‑exporting every submodule.
__all__ = ['config']