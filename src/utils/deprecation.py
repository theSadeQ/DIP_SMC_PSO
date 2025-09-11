from __future__ import annotations
import warnings


def warn_deprecated(
    old_key: str, new_key: str | None = None, *, stacklevel: int = 3
) -> None:
    msg = f"'{old_key}' is deprecated"
    if new_key:
        msg += f"; use '{new_key}' instead"
    warnings.warn(msg, DeprecationWarning, stacklevel=stacklevel)
