"""校验桌面端依赖的源码基线是否与 baseline.json 记录一致。

检查两件事：q-one-core / q-one-agent 两个仓库的 HEAD 提交是否等于基线；
以及各个源码集成补丁文件的 sha256 是否与记录相符，最后确认本地 provider
补丁确实已应用。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def git_head(repository: Path) -> str:
    """返回指定 git 仓库当前 HEAD 的完整提交哈希。"""
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    """逐项核对基线的提交哈希、补丁哈希与 provider 补丁。"""
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

    # 逐个比对两个应用仓库的 HEAD 提交是否与基线一致。
    for name in ("q-one-core", "q-one-agent"):
        expected = baseline["applications"][name]["commit"]
        actual = git_head(workspace / name)
        if actual != expected:
            raise SystemExit(
                f"source baseline mismatch for {name}: expected {expected}, got {actual}"
            )

    # 逐个比对源码集成补丁文件的 sha256。
    for integration in baseline.get("source_integrations", []):
        patch = life_repository / integration["patch"]
        digest = hashlib.sha256(patch.read_bytes()).hexdigest()
        if digest != integration["sha256"]:
            raise SystemExit(
                f"source integration hash mismatch for {integration['patch']}"
            )

    # 确认 q-one-agent 的 runtime.py 里已带上本地 provider 补丁。
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
