#!/usr/bin/env python3
"""Run frozen-feature linear probes for four public timm checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

MODELS = {
    "resnet50.a1_in1k": "vision/resnet50.a1_in1k.safetensors",
    "vit_base_patch16_224.augreg_in21k_ft_in1k":
        "vision/vit_base_patch16_224.augreg_in21k_ft_in1k.safetensors",
    "convnext_tiny.fb_in22k_ft_in1k": "vision/convnext_tiny.safetensors",
    "convnext_small.fb_in22k_ft_in1k":
        "vision/convnext_small.fb_in22k_ft_in1k.safetensors",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/root/qone-paperbench-full10"))
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-images", type=int, default=5000)
    parser.add_argument("--val-images", type=int, default=1000)
    parser.add_argument("--epochs", type=int, default=2)
    args = parser.parse_args()

    zip_path = args.root / "vision" / "tiny-imagenet-200.zip"
    run_root = args.root / "runs" / "linear-probe-matrix"
    run_root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    rows = []
    for model_name, weights_relative in MODELS.items():
        weights = args.root / weights_relative
        output = run_root / f"{model_name}.json"
        log = run_root / f"{model_name}.log"
        command = [sys.executable, str(args.script), "--zip", str(zip_path),
                   "--weights", str(weights), "--model-name", model_name,
                   "--output", str(output), "--train-images", str(args.train_images),
                   "--val-images", str(args.val_images), "--epochs", str(args.epochs),
                   "--device", "cuda"]
        row = {"model": f"timm/{model_name}", "weights": str(weights),
               "command": command, "output": str(output), "log": str(log)}
        if not weights.is_file():
            row.update({"status": "blocked", "reason": "weights_missing"})
            rows.append(row)
            continue
        row["weights_sha256"] = sha256_file(weights)
        model_started = time.monotonic()
        with log.open("w", encoding="utf-8") as handle:
            process = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT,
                                     text=True, check=False)
        row["returncode"] = process.returncode
        row["elapsed_s"] = round(time.monotonic() - model_started, 2)
        if process.returncode == 0 and output.is_file():
            receipt = json.loads(output.read_text(encoding="utf-8"))
            row["status"] = "completed"
            row["feature_dim"] = receipt["feature_dim"]
            row["train_images"] = receipt["train_images"]
            row["val_images"] = receipt["val_images"]
            row["final_val_accuracy"] = receipt["final_val_accuracy"]
            row["history"] = receipt["history"]
            row["receipt_sha256"] = sha256_file(output)
        else:
            row["status"] = "blocked"
            row["reason"] = f"subprocess_exit_{process.returncode}"
        rows.append(row)
        print(json.dumps({"done": model_name, "status": row["status"],
                          "final_val_accuracy": row.get("final_val_accuracy")}), flush=True)

    report = {
        "schema": "qone-tiny-imagenet-linear-probe-matrix-v1",
        "official": False,
        "zip": str(zip_path),
        "zip_sha256": sha256_file(zip_path),
        "train_images_per_model": args.train_images,
        "val_images_per_model": args.val_images,
        "epochs": args.epochs,
        "models": rows,
        "completed": sum(row["status"] == "completed" for row in rows),
        "blocked": sum(row["status"] == "blocked" for row in rows),
        "elapsed_s": round(time.monotonic() - started, 2),
        "note": ("Real frozen public timm features with trained linear probes on "
                 "Tiny-ImageNet-200; not ImageNet-1K, paper-level OOD or official judge."),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps(report, indent=1), flush=True)
    return 0 if report["blocked"] == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
