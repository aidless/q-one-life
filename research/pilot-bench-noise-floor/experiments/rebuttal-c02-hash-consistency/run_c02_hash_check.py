"""C02 反驳实验：当前稿件是否与 native manifest 记录逐字节一致。

独立从 git 提交恢复基线文件，不依赖 evidence/source-lineage.json 的结论。
输出确定性回执：哈希、字节数、diff 统计与 diff 文件哈希。
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "q-one-rebuttal-experiment-v1"
EXPERIMENT_ID = "C02-hash-consistency"


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _portable(path: Path) -> str:
    """把 home 下的绝对路径转成 <HOME>/... 形式，避免回执泄露本机路径。"""
    try:
        relative = path.resolve().relative_to(Path.home())
    except ValueError:
        return str(path)
    return f"<HOME>/{relative.as_posix()}"


def _git_blob(repo: Path, commit: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"git show failed ({completed.returncode}): "
            f"{completed.stderr.decode('utf-8', errors='replace')[:300]}"
        )
    return completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo", required=True,
        help="git repository that holds the recorded commit",
    )
    parser.add_argument(
        "--commit", default="9eb77f1b77baaa9932d8faf18da2fc50a2077f6c"
    )
    parser.add_argument(
        "--path", default="papers/bench_noise_floor/paper/main.tex"
    )
    parser.add_argument(
        "--current",
        default=str(Path(__file__).resolve().parents[2] / "source" / "main.tex"),
    )
    parser.add_argument(
        "--manifest",
        default=str(Path(__file__).resolve().parents[2] / "evidence" / "native-manifest.json"),
    )
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent / "results"),
    )
    args = parser.parse_args()

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    repo = Path(args.repo).expanduser()
    current_path = Path(args.current).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()

    recovered = _git_blob(repo, args.commit, args.path)
    current = current_path.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    recorded = manifest["paper"]["main.tex"]

    recovered_path = out / "recovered-main.tex"
    recovered_path.write_bytes(recovered)

    recovered_lines = recovered.decode("utf-8", errors="replace").splitlines()
    current_lines = current.decode("utf-8", errors="replace").splitlines()
    diff_lines = list(difflib.unified_diff(
        recovered_lines,
        current_lines,
        fromfile=f"{args.commit}:{args.path}",
        tofile="source/main.tex",
        lineterm="",
    ))
    diff_text = "\n".join(diff_lines) + "\n"
    diff_path = out / "diff.patch"
    diff_path.write_text(diff_text, encoding="utf-8")

    added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

    checks = {
        "manifest_hash_matches_recovered": recorded["sha256"] == _sha256(recovered),
        "manifest_bytes_match_recovered": recorded["bytes"] == len(recovered),
        "current_matches_manifest": _sha256(current) == recorded["sha256"],
        "current_matches_recovered": _sha256(current) == _sha256(recovered),
    }
    verdict = "resolved" if all(checks.values()) else "stands"

    receipt = {
        "schema": SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "generated_at": _now(),
        "claim_id": "C02",
        "objection": (
            "The claim states current source/main.tex is byte-identical to the "
            "version recorded in the native manifest; boundary conditions include "
            "hash collisions and manifest/version drift."
        ),
        "inputs": {
            "repo": _portable(repo),
            "commit": args.commit,
            "path": args.path,
            "manifest": {
                "path": _portable(manifest_path),
                "sha256": _sha256(manifest_path.read_bytes()),
            },
            "current": {
                "path": _portable(current_path),
                "sha256": _sha256(current),
                "bytes": len(current),
            },
            "recovered": {
                "path": _portable(recovered_path),
                "sha256": _sha256(recovered),
                "bytes": len(recovered),
            },
            "diff": {
                "path": _portable(diff_path),
                "sha256": _sha256(diff_text.encode("utf-8")),
            },
        },
        "recorded": {"sha256": recorded["sha256"], "bytes": recorded["bytes"]},
        "diff": {"added_lines": added, "removed_lines": removed},
        "checks": checks,
        "verdict": verdict,
        "note": (
            "stands 表示异议成立：当前字节与记录不一致，C02 继续 blocked。"
            "resolved 才表示可以撤回异议。"
        ),
    }
    receipt_path = out / "receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "verdict": verdict,
        "checks": checks,
        "diff": receipt["diff"],
        "receipt": str(receipt_path),
        "receipt_sha256": _sha256(receipt_path.read_bytes()),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
