#!/usr/bin/env bash
set -euo pipefail

# Node cannot reliably start scripts from a working directory whose first path
# component contains a colon. Copy the source into a portable path before
# installing dependencies so this check also works from the current workspace.
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target_root="${QONE_CLEANROOM_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/q-one-cleanroom/$stamp}"
with_e2e="${QONE_CLEANROOM_E2E:-0}"

if [[ "$target_root" == *:* ]]; then
  echo "QONE_CLEANROOM_DIR must not contain ':': $target_root" >&2
  exit 2
fi
if [[ -e "$target_root" ]]; then
  echo "clean-room target already exists: $target_root" >&2
  exit 2
fi
if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required" >&2
  exit 2
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required" >&2
  exit 2
fi
if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm is required" >&2
  exit 2
fi

mkdir -p "$target_root/logs"
rsync -a \
  --exclude '.git/' \
  --exclude '.pytest_cache/' \
  --exclude '.ruff_cache/' \
  --exclude '__pycache__/' \
  --exclude '*.py[cod]' \
  --exclude '.venv/' \
  --exclude 'artifacts/' \
  --exclude 'docs/' \
  --exclude 'logs/' \
  --exclude 'README.md' \
  --exclude 'CHANGELOG.md' \
  --exclude 'scripts/build_resume_evidence.py' \
  --exclude 'build/' \
  --exclude 'dist/' \
  --exclude 'desktop/node_modules/' \
  --exclude 'desktop/dist/' \
  --exclude 'desktop/release/' \
  --exclude 'desktop/playwright-report/' \
  --exclude 'desktop/test-results/' \
  "$source_root/" "$target_root/"

python3 - "$target_root" >"$target_root/logs/source-manifest.txt" <<'PY'
from __future__ import annotations

import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
excluded_roots = {
    ".venv",
    "artifacts",
    "docs",
    "logs",
    "build",
    "dist",
    "desktop/node_modules",
    "desktop/dist",
    "desktop/release",
}
excluded_files = {
    "README.md",
    "CHANGELOG.md",
    "scripts/build_resume_evidence.py",
}
rows: list[str] = []
for path in sorted(p for p in root.rglob("*") if p.is_file()):
    relative = path.relative_to(root).as_posix()
    if any(relative == item or relative.startswith(item + "/") for item in excluded_roots):
        continue
    if relative in excluded_files:
        continue
    if relative.startswith("logs/"):
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rows.append(f"{digest}  {relative}")
print("\n".join(rows))
PY
source_digest="$(sha256sum "$target_root/logs/source-manifest.txt" | cut -d' ' -f1)"

echo "QONE_CLEANROOM_ROOT=$target_root"
echo "QONE_CLEANROOM_SOURCE_SHA256=$source_digest"

started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
core_commit="b1f41dea59eb9d26b66e812f3fc167b83c23d7cf"
agent_commit="79a951ac4e4f77239a227cfe28ffdc0fb30bc19f"
core_source="${QONE_CORE_SOURCE:-$(dirname -- "$source_root")/q-one-core}"
agent_source="${QONE_AGENT_SOURCE:-$(dirname -- "$source_root")/q-one-agent}"

mkdir -p "$target_root/deps"
if git -C "$core_source" cat-file -e "$core_commit^{commit}" 2>/dev/null; then
  git clone --quiet --no-local "$core_source" "$target_root/deps/q-one-core"
  git -C "$target_root/deps/q-one-core" checkout --quiet --detach "$core_commit"
else
  git clone --quiet https://github.com/aidless/q-one-core.git \
    "$target_root/deps/q-one-core"
  git -C "$target_root/deps/q-one-core" checkout --quiet --detach "$core_commit"
fi
if git -C "$agent_source" cat-file -e "$agent_commit^{commit}" 2>/dev/null; then
  git clone --quiet --no-local "$agent_source" "$target_root/deps/q-one-agent"
  git -C "$target_root/deps/q-one-agent" checkout --quiet --detach "$agent_commit"
else
  git clone --quiet https://github.com/aidless/q-one-agent.git \
    "$target_root/deps/q-one-agent"
  git -C "$target_root/deps/q-one-agent" checkout --quiet --detach "$agent_commit"
fi
git -C "$target_root/deps/q-one-agent" apply \
  "$target_root/desktop/patches/q-one-agent-local-provider.patch"
test "$(git -C "$target_root/deps/q-one-core" rev-parse HEAD)" = "$core_commit"
test "$(git -C "$target_root/deps/q-one-agent" rev-parse HEAD)" = "$agent_commit"

uv venv --python python3 "$target_root/.venv" >/dev/null
grep -vE '^q-one-(core|agent)(\[[^]]+\])? @ ' \
  "$target_root/requirements.txt" >"$target_root/logs/base-requirements.txt"
uv pip install --python "$target_root/.venv/bin/python" \
  -r "$target_root/logs/base-requirements.txt" \
  'numpy>=1.26,<3' \
  'scipy>=1.11,<2' \
  pytest==9.1.1 >"$target_root/logs/python-install.log" 2>&1
uv pip install --python "$target_root/.venv/bin/python" --no-deps \
  -e "$target_root/deps/q-one-core" \
  -e "$target_root/deps/q-one-agent" \
  -e "$target_root" >>"$target_root/logs/python-install.log" 2>&1

(
  cd "$target_root"
  PYTHONPATH=src .venv/bin/python -m pytest -q | tee logs/pytest.log
  PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v \
    >logs/unittest.log 2>&1
  node --check <src/qone_life/static/app.js
  node --input-type=module - <tests/test_app_render.mjs
  node tests/test_site.mjs
)

(
  cd "$target_root/desktop"
  pnpm install --frozen-lockfile | tee ../logs/pnpm-install.log
  node node_modules/electron/install.js
  pnpm test | tee ../logs/desktop-unit.log
)

if [[ "$with_e2e" == "1" ]]; then
  sidecar="${QONE_SIDECAR_BIN:-}"
  model="${QONE_E2E_LOCAL_MODEL_PATH:-}"
  if [[ -z "$sidecar" || -z "$model" ]]; then
    echo "QONE_CLEANROOM_E2E=1 requires QONE_SIDECAR_BIN and QONE_E2E_LOCAL_MODEL_PATH" >&2
    exit 2
  fi
  (
    cd "$target_root/desktop"
    ELECTRON_OZONE_PLATFORM_HINT=headless \
      QONE_SIDECAR_BIN="$sidecar" \
      QONE_E2E_LOCAL_MODEL_PATH="$model" \
      QONE_REQUIRE_LOCAL_MODEL_E2E=1 \
      pnpm run test:e2e | tee ../logs/electron-e2e.log
  )
fi

finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 - "$target_root" "$started_at" "$finished_at" "$source_digest" "$with_e2e" <<'PY'
from __future__ import annotations

import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
receipt = {
    "schema": "q-one-cleanroom-check-v1",
    "started_at": sys.argv[2],
    "finished_at": sys.argv[3],
    "result": "passed",
    "source_manifest_sha256": sys.argv[4],
    "scope": "fresh dependency install and tests from a copied runtime source tree",
    "source_manifest_scope": (
        "runtime source, tests, build/release inputs, and this clean-room harness; "
        "documentation and generated evidence are hash-bound separately"
    ),
    "pinned_sources": {
        "q-one-core": "b1f41dea59eb9d26b66e812f3fc167b83c23d7cf",
        "q-one-agent": "79a951ac4e4f77239a227cfe28ffdc0fb30bc19f",
        "q-one-agent_patch": "desktop/patches/q-one-agent-local-provider.patch"
    },
    "python_tests": ["pytest", "unittest", "render", "site"],
    "desktop_tests": ["typescript-unit"],
    "strict_electron_e2e": sys.argv[5] == "1",
    "generated_artifacts_excluded": [
        ".venv",
        "artifacts",
        "logs",
        "build",
        "desktop/node_modules",
        "desktop/release",
    ],
    "documentation_and_evidence_excluded": [
        "README.md",
        "CHANGELOG.md",
        "docs/",
        "artifacts/",
        "logs/",
        "scripts/build_resume_evidence.py",
    ],
    "logs": sorted(
        path.relative_to(root).as_posix()
        for path in (root / "logs").iterdir()
        if path.is_file()
    ),
}
(root / "cleanroom-receipt.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(f"QONE_CLEANROOM_RECEIPT={root / 'cleanroom-receipt.json'}")
PY
