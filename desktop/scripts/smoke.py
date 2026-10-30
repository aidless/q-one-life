from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--electron", required=True)
    parser.add_argument("--app")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument(
        "--mode",
        choices=("launch", "crash-recovery", "model-host"),
        default="launch",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="q-one-electron-smoke-") as profile:
        environment = os.environ | {
            "QONE_SKIP_MIGRATION_PROMPT": "1",
            "ELECTRON_ENABLE_LOGGING": "1",
        }
        modes = {
            "launch": ("QONE_SMOKE_TEST", "QONE_SMOKE_OK"),
            "crash-recovery": ("QONE_CRASH_SMOKE_TEST", "QONE_CRASH_SMOKE_OK"),
            "model-host": ("QONE_MODEL_HOST_SMOKE_TEST", "QONE_MODEL_HOST_SMOKE_OK"),
        }
        environment_variable, marker = modes[args.mode]
        environment[environment_variable] = "1"
        command = [str(Path(args.electron).resolve())]
        if args.app:
            command.append(str(Path(args.app).resolve()))
        command.extend(
            [
                f"--user-data-dir={profile}",
                "--enable-logging=stderr",
                "--disable-gpu",
            ]
        )
        try:
            result = subprocess.run(
                command,
                env=environment,
                capture_output=True,
                text=True,
                timeout=args.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            print(exc.stdout or "", file=sys.stderr)
            print(exc.stderr or "", file=sys.stderr)
            print("Electron smoke test timed out", file=sys.stderr)
            return 1

    if f"{marker} " not in result.stdout or result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return 1
    report = next(
        line for line in result.stdout.splitlines() if marker in line
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
