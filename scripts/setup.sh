#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_dir="${QONE_VENV:-${XDG_DATA_HOME:-$HOME/.local/share}/q-one-runtime/venv}"
if [[ "$runtime_dir" == *:* ]]; then
  echo '请把 QONE_VENV 设置到不含冒号的路径。' >&2
  exit 2
fi
python3 -m venv "$runtime_dir"
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$runtime_dir/bin/python" -r "$project_dir/requirements.txt"
  uv pip install --python "$runtime_dir/bin/python" "$project_dir"
else
  "$runtime_dir/bin/python" -m pip install -r "$project_dir/requirements.txt"
  "$runtime_dir/bin/python" -m pip install "$project_dir"
fi
echo "安装完成。运行 bash scripts/run.sh；Ctrl+C 停止。"
