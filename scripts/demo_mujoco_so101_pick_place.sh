#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "$(uname -s)" == "Darwin" ]]; then
  RUNTIME="$ROOT/.venv-mujoco/bin/mjpython"
else
  RUNTIME="$ROOT/.venv-mujoco/bin/python"
fi

if [[ ! -x "$RUNTIME" ]]; then
  echo "SO-101 MuJoCo runtime is missing. Run: bash scripts/prepare_mujoco_so101.sh" >&2
  exit 1
fi

exec "$RUNTIME" "$ROOT/scripts/demo_mujoco_so101_pick_place.py" "$@"
