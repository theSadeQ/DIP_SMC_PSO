# merge_config.py
# for diffrent physic pararmeters
import sys
from typing import Mapping, MutableMapping

try:
    import yaml  # PyYAML
except Exception:
    sys.stderr.write(
        "This script requires PyYAML.\n" "Install with:  pip install pyyaml\n"
    )
    raise


def deep_update(base: MutableMapping, overlay: Mapping) -> MutableMapping:
    """
    Recursively update dict `base` in-place with values from `overlay`.
    - Dicts are merged
    - Scalars/lists are replaced
    """
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_update(base[k], v)
        else:
            base[k] = v
    return base


def main():
    if len(sys.argv) != 4:
        sys.stderr.write(
            "Usage: merge_config.py BASE_CONFIG OVERLAY_CONFIG OUTPUT_CONFIG\n"
        )
        sys.exit(1)
    base_path, overlay_path, out_path = sys.argv[1:4]
    with open(base_path, "r", encoding="utf-8") as f:
        base = yaml.safe_load(f) or {}
    with open(overlay_path, "r", encoding="utf-8") as f:
        overlay = yaml.safe_load(f) or {}

    if not isinstance(base, dict) or not isinstance(overlay, dict):
        sys.stderr.write("Both files must be YAML mappings at the root.\n")
        sys.exit(2)

    merged = deep_update(base, overlay)

    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(merged, f, sort_keys=False)
    print(f"✅ Wrote merged config to {out_path}")


if __name__ == "__main__":
    main()
