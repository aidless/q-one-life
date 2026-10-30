#!/usr/bin/env python3
"""Build a read-only paper portfolio artifact with provenance."""

from __future__ import annotations

import argparse
import json
import platform
import shlex
from datetime import datetime, timezone
from pathlib import Path

from qone_life.research import build_portfolio, sha256_file, write_portfolio


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--artifact-dir", required=True)
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    artifact_dir = Path(args.artifact_dir).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    portfolio = build_portfolio(
        config["roots"],
        exclude_dirs=config.get("exclude_dirs", []),
        exclude_path_fragments=config.get("exclude_path_fragments", []),
        writeup_globs=config.get("writeup_globs", []),
        max_depth=config.get("max_depth", 8),
    )
    portfolio_path = artifact_dir / "paper-portfolio.json"
    markdown_path = artifact_dir / "paper-portfolio.md"
    triage_path = artifact_dir / "paper-triage.csv"
    write_portfolio(portfolio, portfolio_path, markdown_path, triage_path)

    command = shlex.join(
        [
            "python",
            "scripts/research_portfolio.py",
            "--config",
            str(config_path),
            "--artifact-dir",
            str(artifact_dir),
        ]
    )
    artifact = {
        "schema": "q-one-artifact-v1",
        "name": "research-paper-portfolio",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "command": command,
        "inputs": [{"path": str(config_path), "sha256": sha256_file(config_path)}],
        "outputs": [
            {
                "path": str(portfolio_path),
                "sha256": sha256_file(portfolio_path),
                "bytes": portfolio_path.stat().st_size,
            },
            {
                "path": str(markdown_path),
                "sha256": sha256_file(markdown_path),
                "bytes": markdown_path.stat().st_size,
            },
            {
                "path": str(triage_path),
                "sha256": sha256_file(triage_path),
                "bytes": triage_path.stat().st_size,
            },
        ],
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "notes": [
            "Read-only inventory of paper-project markers.",
            (
                "Raw roots, exact duplicates, title-version families, and supporting "
                "objects are reported separately."
            ),
            "Unknown status is not converted to a score or a guessed readiness state.",
        ],
    }
    artifact_path = artifact_dir / "artifact.json"
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    provenance = f"""# research-paper-portfolio v1 provenance

- Generated at: `{artifact['generated_at']}`
- Generator: `src/qone_life/research.py`
- Configuration: `{config_path}`
- Portfolio JSON SHA-256: `{artifact['outputs'][0]['sha256']}`
- Portfolio Markdown SHA-256: `{artifact['outputs'][1]['sha256']}`
- Triage CSV SHA-256: `{artifact['outputs'][2]['sha256']}`

## Reproduction

```bash
{command}
```

The scan is read-only. It does not modify manuscripts, run experiments, use paid
resources, authenticate to an external service, or publish anything.
"""
    (artifact_dir / "provenance.md").write_text(provenance, encoding="utf-8")
    print(json.dumps(portfolio["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
