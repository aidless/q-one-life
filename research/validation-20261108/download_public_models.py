#!/usr/bin/env python3
"""Download small public model files to a cloud-only directory and record hashes.

No gated model, no credentials, no authentication headers. This script is safe
to run on the authorized AMD host; large assets never enter git.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path("/root/qone-paperbench-full10/public-models")
MODELS = {
    "pythia-70m": {
        "repo": "EleutherAI/pythia-70m",
        "files": ["config.json", "model.safetensors", "tokenizer.json",
                  "tokenizer_config.json", "special_tokens_map.json"],
    },
    "gpt2-medium": {
        "repo": "openai-community/gpt2-medium",
        "files": ["config.json", "model.safetensors", "vocab.json",
                  "merges.txt", "tokenizer_config.json"],
    },
}


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    report = {"schema": "qone-public-model-download-v1", "root": str(ROOT), "models": {}}
    for name, spec in MODELS.items():
        target = ROOT / name
        target.mkdir(parents=True, exist_ok=True)
        rows = []
        for filename in spec["files"]:
            url = f"https://huggingface.co/{spec['repo']}/resolve/main/{filename}"
            path = target / filename
            if not path.is_file():
                try:
                    urllib.request.urlretrieve(url, path)
                    state = "downloaded"
                except Exception as exc:
                    rows.append({"file": filename, "state": "blocked",
                                 "error": f"{type(exc).__name__}: {exc}"[:200]})
                    continue
            else:
                state = "present"
            data = path.read_bytes()
            rows.append({"file": filename, "state": state, "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest()})
        report["models"][name] = {"repo": spec["repo"], "files": rows}
    (ROOT / "ASSET_RECEIPT.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"root": str(ROOT),
                      "states": {name: [row["state"] for row in spec["files"]]
                                 for name, spec in report["models"].items()}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
