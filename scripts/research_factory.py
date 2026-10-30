#!/usr/bin/env python3
"""Build a quantified research-production queue with provenance."""

from __future__ import annotations

import argparse
import json
import platform
import shlex
from datetime import datetime, timezone
from pathlib import Path

from qone_life.research import sha256_file
from qone_life.research_factory import (
    triage_portfolio,
    write_triage,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio", required=True)
    parser.add_argument("--pilots", required=True)
    parser.add_argument("--artifact-dir", required=True)
    args = parser.parse_args()

    portfolio_path = Path(args.portfolio).resolve()
    pilot_path = Path(args.pilots).resolve()
    artifact_dir = Path(args.artifact_dir).resolve()
    portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))
    pilot_data = json.loads(pilot_path.read_text(encoding="utf-8"))
    report = triage_portfolio(portfolio, pilots=pilot_data.get("pilots", []))
    json_path = artifact_dir / "triage.json"
    markdown_path = artifact_dir / "triage.md"
    csv_path = artifact_dir / "triage.csv"
    write_triage(report, json_path, markdown=markdown_path, csv_path=csv_path)

    command = shlex.join(
        [
            "python",
            "scripts/research_factory.py",
            "--portfolio",
            str(portfolio_path),
            "--pilots",
            str(pilot_path),
            "--artifact-dir",
            str(artifact_dir),
        ]
    )
    artifact = {
        "schema": "q-one-artifact-v1",
        "name": "research-factory-triage",
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "command": command,
        "inputs": [
            {"path": str(portfolio_path), "sha256": sha256_file(portfolio_path)},
            {"path": str(pilot_path), "sha256": sha256_file(pilot_path)},
        ],
        "outputs": [
            {
                "path": str(json_path),
                "sha256": sha256_file(json_path),
                "bytes": json_path.stat().st_size,
            },
            {
                "path": str(markdown_path),
                "sha256": sha256_file(markdown_path),
                "bytes": markdown_path.stat().st_size,
            },
            {
                "path": str(csv_path),
                "sha256": sha256_file(csv_path),
                "bytes": csv_path.stat().st_size,
            },
        ],
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "notes": [
            "Production priority is an orchestration ordering, not paper quality.",
            "Suggested dispositions do not change human final dispositions.",
            "Unknown readiness is not converted to zero.",
        ],
    }
    artifact_path = artifact_dir / "artifact.json"
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    provenance = f"""# research-factory-triage v2 provenance

- Generated at: `{artifact['generated_at']}`
- Generator: `src/qone_life/research_factory.py`
- Portfolio: `{portfolio_path}`
- Pilot configuration: `{pilot_path}`
- Triage JSON SHA-256: `{artifact['outputs'][0]['sha256']}`
- Triage Markdown SHA-256: `{artifact['outputs'][1]['sha256']}`
- Triage CSV SHA-256: `{artifact['outputs'][2]['sha256']}`

## Reproduction

```bash
{command}
```

The queue is deterministic given the input portfolio and pilot configuration.
It does not modify manuscripts, run experiments, call models, or publish.
"""
    (artifact_dir / "provenance.md").write_text(provenance, encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
