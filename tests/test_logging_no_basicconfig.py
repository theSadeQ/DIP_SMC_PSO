import importlib
import logging
import pkgutil
from pathlib import Path


def test_no_basicConfig_on_import(monkeypatch):
    """Test that no library imports call logging.basicConfig."""
    called = False
    
    def fake_basicConfig(*a, **kw):
        nonlocal called
        called = True
    
    monkeypatch.setattr(logging, "basicConfig", fake_basicConfig)

    src_dir = Path("src")
    assert src_dir.exists()

    for pkg in src_dir.iterdir():
        if pkg.is_dir() and (pkg / "__init__.py").exists():
            root_name = pkg.name
            skip_suffixes = (".cli", ".app")
            for m in pkgutil.walk_packages([str(pkg)], prefix=f"{root_name}."):
                if any(m.name.endswith(s) for s in skip_suffixes):
                    continue
                importlib.import_module(m.name)

    assert not called, "library imports must not call logging.basicConfig()"