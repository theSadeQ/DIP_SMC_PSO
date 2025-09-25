#!/usr/bin/env bash
set -euo pipefail
# Task 2 — Phase 1 apply wrapper

# Find the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
API_ROOT="$REPO_ROOT/dip_docs/docs/source/api"

echo "Project root: $REPO_ROOT"
echo "API root: $API_ROOT"

if [[ ! -d "$API_ROOT" ]]; then
  echo "ERROR: expected path not found: $API_ROOT" 1>&2
  exit 1
fi

python3 "$SCRIPT_DIR/task2_phase1_reorg.py" --dry-run
read -p $'\nProceed with reorganization? [y/N] ' ans
if [[ "${ans:-N}" =~ ^[Yy]$ ]]; then
  python3 "$SCRIPT_DIR/task2_phase1_reorg.py"
  echo "Done. Review changes via: git status"
else
  echo "Aborted."
fi