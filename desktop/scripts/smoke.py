"""Electron 桌面端冒烟测试脚本。

启动打包后的 Electron 应用，按 `--mode` 注入对应的烟雾测试环境变量，
再检查标准输出里是否出现约定的成功标记，以此判断应用能否正常启动。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    """解析参数、启动应用并校验烟雾测试标记。"""
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

    # 用临时目录充当独立的用户数据目录，避免污染真实配置。
    with tempfile.TemporaryDirectory(prefix="q-one-electron-smoke-") as profile:
        environment = os.environ | {
            "QONE_SKIP_MIGRATION_PROMPT": "1",
            "ELECTRON_ENABLE_LOGGING": "1",
        }
        # 每种模式对应一组「注入的环境变量」和「期望出现的成功标记」。
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
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            print(exc.stdout or "", file=sys.stderr)
            print(exc.stderr or "", file=sys.stderr)
            print("Electron smoke test timed out", file=sys.stderr)
            return 1

    # 标记不存在或退出码非零都算失败，回显输出便于排查。
    if f"{marker} " not in result.stdout or result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return 1

    # 在输出中找出包含该成功标记的那一行并打印出来。
    report = None
    for line in result.stdout.splitlines():
        if marker in line:
            report = line
            break
    if report is None:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return 1
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
