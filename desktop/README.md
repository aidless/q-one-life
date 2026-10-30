# Q-One Desktop

Q-One Desktop hosts the existing Q-One local web application in Electron and
starts a Python sidecar on a random loopback port. The renderer never receives
the capability secret. Electron injects the capability into same-session
`/api/*` requests, while control operations require a second token known only
to the main process.

## Development

The sidecar build expects `q-one-core` and `q-one-agent` to be checked out next
to this repository at the reviewed commits in `baseline.json`.

```bash
# From q-one-life/desktop
pnpm install
QONE_PYTHON=/path/to/runtime/python pnpm start
```

`QONE_SIDECAR_BIN` can point to a PyInstaller build. Automated tests set
`QONE_SKIP_MIGRATION_PROMPT=1`; do not use that setting for normal runs.

The optional Qwen3 0.6B model is downloaded from the pinned Hugging Face
repository with a pinned ModelScope mirror as a fallback. Both sources must
resolve to the same fixed byte size and SHA-256 before the file is published.
Model downloads use Electron's Chromium network session so system proxy
settings apply; a standard `HTTPS_PROXY`/`ALL_PROXY` environment is also
honored through a fixed CONNECT proxy adapter for development and managed
desktops.

## Validation

```bash
# Python tests
python -m pytest -q

# TypeScript unit tests
pnpm test

# Native sidecar
python -m PyInstaller --clean --noconfirm \
  --distpath ../build/sidecar \
  --workpath ../build/pyinstaller \
  sidecar.spec

# Development Electron launch
QONE_SIDECAR_BIN=../build/sidecar/qone-life-sidecar/qone-life-sidecar \
  python scripts/smoke.py \
  --electron node_modules/electron/dist/electron \
  --app .

# Strict E2E with the pinned, hash-verified local model
node scripts/fetch-e2e-model.mjs --output /path/to/Qwen3-0.6B-Q8_0.gguf
QONE_SIDECAR_BIN=../build/sidecar/qone-life-sidecar/qone-life-sidecar \
  QONE_E2E_LOCAL_MODEL_PATH=/path/to/Qwen3-0.6B-Q8_0.gguf \
  QONE_REQUIRE_LOCAL_MODEL_E2E=1 \
  pnpm run test:e2e

# Three-crash recovery boundary
QONE_SIDECAR_BIN=../build/sidecar/qone-life-sidecar/qone-life-sidecar \
  python scripts/smoke.py \
  --mode crash-recovery \
  --electron node_modules/electron/dist/electron \
  --app .

# Unpacked application package
pnpm run dist:dir
python scripts/find_packaged.py --release-dir release

# Signed update manifest and artifact verification
node scripts/verify-release.mjs --help
```

Use a separate, pytest-free virtual environment for sidecar builds so test
dependencies cannot enter the native application.

## Resume acceptance

Run the six-task rule/local-model comparison without mixing it into the default
strict E2E:

```bash
QONE_RUN_RESUME_BENCHMARK=1 \
QONE_SIDECAR_BIN=/absolute/path/to/qone-life-sidecar \
QONE_E2E_LOCAL_MODEL_PATH=/absolute/path/to/Qwen3-0.6B-Q8_0.gguf \
node node_modules/@playwright/test/cli.js test e2e/resume-benchmark.spec.ts
```

Capture the verified consumer screenshots:

```bash
QONE_CAPTURE_DEMO=1 \
QONE_SIDECAR_BIN=/absolute/path/to/qone-life-sidecar \
QONE_E2E_LOCAL_MODEL_PATH=/absolute/path/to/Qwen3-0.6B-Q8_0.gguf \
QONE_DEMO_OUTPUT=/absolute/path/to/artifacts/resume-kit/demo \
node node_modules/@playwright/test/cli.js test e2e/capture-demo.spec.ts
```

The six-task benchmark is an engineering acceptance check, not an external
validity study or evidence of real-world benefit.

The website source lives in `../site/`. It is deployed only by manual workflow
dispatch after a signed release exists.

## Security Boundary

- Static pages may load without a capability; every `/api/*` request requires
  the Electron-generated capability.
- `contextIsolation` and sandboxing are enabled, Node integration is disabled,
  external navigation and popups are denied, and the preload API is deliberately
  small.
- Cloud API keys use Electron `safeStorage`. A Linux `basic_text` backend is
  treated as session-only and must never be presented as persistent protection.
- Portable backups are AES-256-GCM containers. A random data key encrypts the
  payload; a recovery-key-derived Argon2id key only wraps that data key.
- The working SQLite database is protected by the operating system, not by the
  backup encryption layer.

## Release Gates

The GitHub workflow builds, smoke-tests, creates evidence, and uploads
`unsigned-internal` native installers on Windows, Apple Silicon macOS, and Linux
runners. It explicitly proves those artifacts fail the public signing gate. It
does not authorize a public release.

See `RELEASE.md` for signing, update-manifest, rollback, and clean-machine
requirements. Code signing credentials, notarization, embedded update public
keys, website publication, public tags, and `1.0.0` promotion remain separate
external gates.
