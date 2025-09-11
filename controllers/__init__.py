"""
Compat shim: expose `src.controllers` as `controllers`.
This makes `import controllers.*` behave exactly like `import src.controllers.*`.
"""
import importlib, sys
_real = importlib.import_module("src.controllers")

# Mirror package identity so relative imports work correctly
globals().update(_real.__dict__)
try:
    __path__ = _real.__path__
    __spec__ = _real.__spec__
except Exception:
    pass

# Make Python treat this module as the same package object
sys.modules[__name__] = _real
