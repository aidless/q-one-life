from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def git_head(repository: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "baseline.json",
    )
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    life_repository = args.baseline.resolve().parent.parent

    for name in ("q-one-core", "q-one-agent"):
        expected = baseline["applications"][name]["commit"]
        actual = git_head(workspace / name)
        if actual != expected:
            raise SystemExit(
                f"source baseline mismatch for {name}: expected {expected}, got {actual}"
            )

    for integration in baseline.get("source_integrations", []):
        patch = life_repository / integration["patch"]
        digest = hashlib.sha256(patch.read_bytes()).hexdigest()
        if digest != integration["sha256"]:
            raise SystemExit(
                f"source integration hash mismatch for {integration['patch']}"
            )

    provider = (workspace / "q-one-agent" / "src" / "qone_agent" / "runtime.py").read_text(
        encoding="utf-8"
    )
    if 'provider in {"ollama", "cloud", "local"}' not in provider:
        raise SystemExit("q-one-agent local provider patch is not applied")
    print(
        "QONE_SOURCE_BASELINE_OK "
        + json.dumps(
            {
                "core": baseline["applications"]["q-one-core"]["commit"],
                "agent": baseline["applications"]["q-one-agent"]["commit"],
                "integrations": len(baseline.get("source_integrations", [])),
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
