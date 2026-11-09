#!/usr/bin/env python3
"""Download public full10 experiment assets to cloud-only directories.

This uses only public URLs and records byte counts plus SHA-256 values. No
credentials or private account data are read, stored, or printed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

HF_MIRROR = "https://hf-mirror.com"
D4RL_BASE = "https://rail.eecs.berkeley.edu/datasets/offline_rl"
TIMM_MODELS = {
    "resnet50.a1_in1k": "timm/resnet50.a1_in1k",
    "vit_base_patch16_224.augreg_in21k_ft_in1k":
        "timm/vit_base_patch16_224.augreg_in21k_ft_in1k",
    "convnext_small.fb_in22k_ft_in1k": "timm/convnext_small.fb_in22k_ft_in1k",
}
TOXIC_FILES = (
    "config.json", "pytorch_model.bin", "vocab.json", "merges.txt",
    "special_tokens_map.json", "tokenizer_config.json",
)
D4RL_FILES = {
    "kitchen/kitchen_microwave_kettle_light_slider-v0.hdf5":
        "d4rl/kitchen_microwave_kettle_light_slider-v0.hdf5",
    "kitchen/mini_kitchen_microwave_kettle_light_slider-v0.hdf5":
        "d4rl/mini_kitchen_microwave_kettle_light_slider-v0.hdf5",
    "gym_mujoco_v2/hopper_medium-v2.hdf5": "d4rl/hopper_medium-v2.hdf5",
    "gym_mujoco_v2/hopper_medium_replay-v2.hdf5":
        "d4rl/hopper_medium_replay-v2.hdf5",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, path: Path, timeout_s: float) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    if path.is_file():
        return {"url": url, "path": str(path), "state": "present",
                "bytes": path.stat().st_size, "sha256": sha256_file(path)}
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": "qone-full10-public-assets/1"})
    with urllib.request.urlopen(request, timeout=timeout_s) as response, temporary.open("wb") as handle:
        shutil.copyfileobj(response, handle, length=1024 * 1024)
    temporary.replace(path)
    return {"url": url, "path": str(path), "state": "downloaded",
            "bytes": path.stat().st_size, "sha256": sha256_file(path),
            "elapsed_s": round(time.monotonic() - started, 2)}


def hf_download(repo: str, filename: str, path: Path, timeout_s: float) -> dict:
    url = f"{HF_MIRROR}/{repo}/resolve/main/{filename}"
    return download(url, path, timeout_s)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/root/qone-paperbench-full10"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--include-large-d4rl", action="store_true")
    args = parser.parse_args()

    report = {"schema": "qone-full10-public-assets-v1", "root": str(args.root),
              "official": False, "hf_mirror": HF_MIRROR, "d4rl_base": D4RL_BASE,
              "timm": {}, "toxicity_classifier": {}, "d4rl": {}}
    vision_root = args.root / "vision"
    for model_name, repo in TIMM_MODELS.items():
        target = vision_root / f"{model_name}.safetensors"
        try:
            report["timm"][model_name] = hf_download(repo, "model.safetensors", target,
                                                      args.timeout_s)
        except Exception as exc:
            report["timm"][model_name] = {"url": f"{HF_MIRROR}/{repo}/resolve/main/model.safetensors",
                                           "path": str(target), "state": "blocked",
                                           "error": f"{type(exc).__name__}: {exc}"[:300]}

    toxic_root = args.root / "public-models" / "unbiased-toxic-roberta"
    for filename in TOXIC_FILES:
        target = toxic_root / filename
        try:
            report["toxicity_classifier"][filename] = hf_download(
                "unitary/unbiased-toxic-roberta", filename, target, args.timeout_s)
        except Exception as exc:
            report["toxicity_classifier"][filename] = {
                "url": f"{HF_MIRROR}/unitary/unbiased-toxic-roberta/resolve/main/{filename}",
                "path": str(target), "state": "blocked",
                "error": f"{type(exc).__name__}: {exc}"[:300]}

    for remote, local in D4RL_FILES.items():
        if "hopper" in local and not args.include_large_d4rl:
            report["d4rl"][local] = {"url": f"{D4RL_BASE}/{remote}",
                                      "path": str(args.root / local),
                                      "state": "skipped_large"}
            continue
        target = args.root / local
        try:
            report["d4rl"][local] = download(f"{D4RL_BASE}/{remote}", target,
                                              args.timeout_s)
        except Exception as exc:
            report["d4rl"][local] = {"url": f"{D4RL_BASE}/{remote}",
                                      "path": str(target), "state": "blocked",
                                      "error": f"{type(exc).__name__}: {exc}"[:300]}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    states = {section: {name: row["state"] for name, row in rows.items()}
              for section, rows in report.items() if isinstance(rows, dict)}
    print(json.dumps(states, indent=2), flush=True)
    return 0 if all(row.get("state") in {"present", "downloaded", "skipped_large"}
                    for rows in report.values() if isinstance(rows, dict)
                    for row in rows.values()) else 3


if __name__ == "__main__":
    raise SystemExit(main())
