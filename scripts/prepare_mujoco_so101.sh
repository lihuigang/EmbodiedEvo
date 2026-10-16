#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV="$ROOT/.venv-mujoco"
export MENAGERIE_CACHE_DIR="${MENAGERIE_CACHE_DIR:-$ROOT/vendor/mujoco-menagerie-cache}"

HOST_ARCH="$(uname -m)"
PYTHON_ARCH="$("$PYTHON_BIN" -c 'import platform; print(platform.machine())')"
if [[ "$(uname -s)" == "Darwin" && "$HOST_ARCH" == "arm64" && "$PYTHON_ARCH" != "arm64" ]]; then
  if [[ -x /opt/homebrew/bin/python3 ]]; then
    PYTHON_BIN=/opt/homebrew/bin/python3
    PYTHON_ARCH="$("$PYTHON_BIN" -c 'import platform; print(platform.machine())')"
  else
    echo "MuJoCo requires native arm64 Python on Apple Silicon; got $PYTHON_ARCH." >&2
    echo "Set PYTHON_BIN to an arm64 Python executable and retry." >&2
    exit 1
  fi
fi

"$PYTHON_BIN" -m venv --clear "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -e "$ROOT[mujoco]"
"$VENV/bin/python" -c \
  'import mujoco_menagerie as mm; mm.prefetch(["robotstudio_so101"]); print(mm.get("robotstudio_so101").oid)'

echo "SO-101 MuJoCo runtime ready: $VENV"
echo "Python architecture: $PYTHON_ARCH"
echo "Menagerie cache: $MENAGERIE_CACHE_DIR"
