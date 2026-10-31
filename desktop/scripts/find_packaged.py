"""在打包输出目录里定位唯一的一个可执行文件。

不同平台（Windows / macOS / Linux）的产物布局不同，这里分别按各自的目录
结构枚举候选可执行文件，并要求最终恰好命中一个，避免用错产物。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def executable_candidates(release_dir: Path) -> list[Path]:
    """按当前平台返回 release 目录下所有可能的可执行文件（已排序）。"""
    if sys.platform == "win32":
        # Windows：取 win-unpacked 下的 .exe，排除卸载程序。
        candidates = []
        for path in (release_dir / "win-unpacked").glob("*.exe"):
            if path.is_file() and "uninstall" not in path.name.lower():
                candidates.append(path)
        return sorted(candidates)

    if sys.platform == "darwin":
        # macOS：可执行文件藏在 .app 包内部的 Contents/MacOS 目录。
        candidates = []
        patterns = ("mac*/*.app/Contents/MacOS/*", "*.app/Contents/MacOS/*")
        for pattern in patterns:
            for path in release_dir.glob(pattern):
                if path.is_file() and os.access(path, os.X_OK):
                    candidates.append(path)
        return sorted(candidates)

    # Linux：取 linux-unpacked 下名称恰为 q-one 的可执行文件。
    linux_dir = release_dir / "linux-unpacked"
    if not linux_dir.is_dir():
        return []
    candidates = []
    for path in linux_dir.iterdir():
        if path.is_file() and path.name == "q-one" and os.access(path, os.X_OK):
            candidates.append(path)
    return sorted(candidates)


def main() -> int:
    """校验 release 目录存在且恰好包含一个可执行文件，然后打印其路径。"""
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
