#!/usr/bin/env bash
set -euo pipefail
runtime_dir="${QONE_VENV:-${XDG_DATA_HOME:-$HOME/.local/share}/q-one-runtime/venv}"
if [[ ! -x "$runtime_dir/bin/qone-life" ]]; then
  echo '请先运行 bash scripts/setup.sh。' >&2
  exit 2
fi
exec "$runtime_dir/bin/qone-life" serve "$@"
