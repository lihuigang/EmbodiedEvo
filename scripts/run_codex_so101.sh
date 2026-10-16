#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Host runtime missing. Follow README.md Setup to prepare .venv." >&2
  exit 1
fi
cd "$ROOT"
exec "$ROOT/.venv/bin/python" -m scripts.run_codex_so101 "$@"
