from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def executable_candidates(release_dir: Path) -> list[Path]:
    if sys.platform == "win32":
        return sorted(
            path
            for path in (release_dir / "win-unpacked").glob("*.exe")
            if path.is_file() and "uninstall" not in path.name.lower()
        )
    if sys.platform == "darwin":
        return sorted(
            path
            for pattern in ("mac*/*.app/Contents/MacOS/*", "*.app/Contents/MacOS/*")
            for path in release_dir.glob(pattern)
            if path.is_file() and os.access(path, os.X_OK)
        )
    linux_dir = release_dir / "linux-unpacked"
    if not linux_dir.is_dir():
        return []
    return sorted(
        path
        for path in linux_dir.iterdir()
        if path.is_file() and path.name == "q-one" and os.access(path, os.X_OK)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", required=True)
    args = parser.parse_args()
    release_dir = Path(args.release_dir).resolve()
    if not release_dir.is_dir():
        print(f"release directory does not exist: {release_dir}", file=sys.stderr)
        return 1
    candidates = executable_candidates(release_dir)
    if len(candidates) != 1:
        print(
            f"expected one packaged executable under {release_dir}, found {len(candidates)}",
            file=sys.stderr,
        )
        for candidate in candidates:
            print(candidate, file=sys.stderr)
        return 1
    print(candidates[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
