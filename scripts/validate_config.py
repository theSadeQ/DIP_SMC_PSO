#==========================================================================================\\\
#================================ scripts/validate_config.py ============================\\\
#==========================================================================================\\\
#!/usr/bin/env python3
"""
Configuration validation script for CI and local development.
Validates that config.yaml is syntactically correct and loads properly.
"""
import sys
from pathlib import Path

def main():
    """
    Validate config.yaml and exit with appropriate return codes.
    Returns 0 on success, non-zero on failure.
    """
    config_path = Path("config.yaml")

    if not config_path.exists():
        print(f"ERROR: Configuration file {config_path} not found", file=sys.stderr)
        return 1

    # Test YAML syntax
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        print("YAML syntax validation passed")
    except Exception as e:
        print(f"ERROR: YAML syntax validation failed: {e}", file=sys.stderr)
        return 1

    # Test config loading
    try:
        from src.config import load_config
        cfg = load_config(str(config_path), allow_unknown=True)
        print("Configuration validation passed")
        print(f"Loaded config with {len(cfg.controller_defaults.__class__.model_fields)} controller types")
    except Exception as e:
        print(f"ERROR: Configuration validation failed: {e}", file=sys.stderr)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())