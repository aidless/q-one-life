#!/usr/bin/env python3
"""Tiny-ImageNet TTA/LCA-style small matrix with a public timm checkpoint.

This is a real vision-model matrix on 200 public images. It is not the paper's
ImageNet-1K / ImageNet-OOD model zoo and does not claim paper-level results.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import time
import zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--model-name", default="convnext_tiny.fb_in22k_ft_in1k")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--images", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20261108)
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--checkpoint-every", type=int, default=200)
    args = parser.parse_args()

    import numpy as np
    import torch
    import timm
    from PIL import Image
    from safetensors.torch import load_file
    from torchvision import transforms

    started = time.monotonic()
    if args.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    cfg = timm.get_pretrained_cfg(args.model_name)
    model = timm.create_model(cfg.architecture, pretrained=False,
                              num_classes=cfg.num_classes, pretrained_cfg=cfg)
    state = load_file(str(args.weights))
    model.load_state_dict(state, strict=False)
    model.to(device)
    model.eval()

    data_cfg = timm.data.resolve_model_data_config(model)
    base_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(data_cfg["mean"], data_cfg["std"]),
    ])
    transforms_by_corruption = {
        "clean": lambda image: base_transform(image),
        "hflip": lambda image: base_transform(image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)),
        "brightness": lambda image: base_transform(
            transforms.functional.adjust_brightness(image, 1.25)),
        "center_crop": lambda image: base_transform(
            transforms.functional.center_crop(image, (48, 48))),
        "grayscale": lambda image: base_transform(
            transforms.functional.rgb_to_grayscale(image, num_output_channels=3)),
        "contrast": lambda image: base_transform(
            transforms.functional.adjust_contrast(image, 1.5)),
    }

    with zipfile.ZipFile(args.zip) as archive:
        names = [name for name in archive.namelist()
                 if name.startswith("tiny-imagenet-200/train/")
                 and name.lower().endswith(".jpeg")]
        random.Random(args.seed).shuffle(names)
        selected = names[:args.images]
        rows = []
        for index, name in enumerate(selected):
            raw = archive.read(name)
            image = Image.open(io.BytesIO(raw)).convert("RGB")
            row = {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}
            tensors = []
            for corruption, transform in transforms_by_corruption.items():
                tensors.append(transform(image))
            batch = torch.stack(tensors, dim=0).to(device)
            with torch.no_grad():
                logits = model(batch)
                probabilities = torch.softmax(logits, dim=-1)
                confidence, prediction = probabilities.max(dim=-1)
            for corruption_index, corruption in enumerate(transforms_by_corruption):
                row[corruption] = {
                    "prediction": int(prediction[corruption_index]),
                    "confidence": round(float(confidence[corruption_index]), 6),
                }
            rows.append(row)
            if (index + 1) % args.checkpoint_every == 0:
                print(json.dumps({"done": index + 1, "total": len(selected),
                                  "elapsed_s": round(time.monotonic() - started, 1)}), flush=True)

    clean_hits = {
        corruption: sum(row[corruption]["prediction"] == row["clean"]["prediction"] for row in rows)
        for corruption in transforms_by_corruption
    }
    mean_confidence = {
        corruption: round(float(np.mean([row[corruption]["confidence"] for row in rows])), 6)
        for corruption in transforms_by_corruption
    }
    # Toy taxonomy: 200 WordNet-like labels grouped into 20 parents. LCA error is
    # 0 when same parent, 1 otherwise; this is a hierarchy-consistency probe only.
    lca_errors = {
        corruption: round(
            sum((row[corruption]["prediction"] % 20) != (row["clean"]["prediction"] % 20)
                for row in rows) / len(rows), 6)
        for corruption in transforms_by_corruption
    }
    receipt = {
        "schema": "qone-tiny-imagenet-tta-lca-matrix-v1",
        "model": f"timm/{args.model_name}",
        "weights": str(args.weights),
        "weights_sha256": sha256_file(args.weights),
        "zip": str(args.zip),
        "zip_sha256": sha256_file(args.zip),
        "official": False,
        "images": len(rows),
        "device": device,
        "batch_size_per_image": len(transforms_by_corruption),
        "corruptions": list(transforms_by_corruption),
        "clean_prediction_agreement": clean_hits,
        "mean_confidence": mean_confidence,
        "toy_lca_error": lca_errors,
        "elapsed_s": round(time.monotonic() - started, 2),
        "note": (
            f"Real public timm/{args.model_name} on Tiny-ImageNet images; toy "
            "20-parent hierarchy only, no ImageNet-1K/OOD or paper-level results."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
