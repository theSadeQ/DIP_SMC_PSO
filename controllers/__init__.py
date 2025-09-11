"""
Shim package forwarding `import controllers.*` to `src.controllers.*`.
"""
from importlib import import_module as _imp
_real = _imp("src.controllers")
globals().update(_real.__dict__)
