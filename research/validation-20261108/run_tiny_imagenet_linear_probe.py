#!/usr/bin/env python3
"""Train a bounded linear probe on frozen public timm Tiny-ImageNet features.

This is a real GPU training experiment on a public alternative dataset. It is
not ImageNet-1K, not the paper's training recipe, and not a PaperBench judge.
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
    parser.add_argument("--model-name", default="resnet50.a1_in1k")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-images", type=int, default=10000)
    parser.add_argument("--val-images", type=int, default=2000)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=20261108)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    import numpy as np
    import torch
    import timm
    from PIL import Image
    from safetensors.torch import load_file
    from torchvision import transforms

    started = time.monotonic()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    cfg = timm.get_pretrained_cfg(args.model_name)
    model = timm.create_model(cfg.architecture, pretrained=False, num_classes=0,
                              pretrained_cfg=cfg)
    state = load_file(str(args.weights))
    model.load_state_dict(state, strict=False)
    model.to(args.device)
    model.eval()
    data_cfg = timm.data.resolve_model_data_config(model)
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(data_cfg["mean"], data_cfg["std"]),
    ])

    with zipfile.ZipFile(args.zip) as archive:
        wnids = archive.read("tiny-imagenet-200/wnids.txt").decode("utf-8").split()
        class_to_index = {wnid: index for index, wnid in enumerate(wnids)}
        train_names = [name for name in archive.namelist()
                       if name.startswith("tiny-imagenet-200/train/")
                       and name.lower().endswith(".jpeg")]
        random.Random(args.seed).shuffle(train_names)
        selected_train = train_names[:args.train_images]
        annotations = {}
        for line in archive.read("tiny-imagenet-200/val/val_annotations.txt").decode("utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                annotations[parts[0]] = parts[1]
        val_names = [name for name in archive.namelist()
                     if name.startswith("tiny-imagenet-200/val/images/")
                     and name.lower().endswith(".jpeg")]
        random.Random(args.seed + 1).shuffle(val_names)
        selected_val = val_names[:args.val_images]

        def extract(names: list[str], labels: list[int]) -> tuple[torch.Tensor, torch.Tensor]:
            features = []
            for start in range(0, len(names), 64):
                batch_names = names[start:start + 64]
                tensors = []
                for name in batch_names:
                    image = Image.open(io.BytesIO(archive.read(name))).convert("RGB")
                    tensors.append(transform(image))
                batch = torch.stack(tensors).to(args.device)
                with torch.no_grad():
                    features.append(model(batch).float().cpu())
                if (start // 64) % 20 == 0:
                    print(json.dumps({"extracted": min(start + 64, len(names)),
                                      "total": len(names),
                                      "elapsed_s": round(time.monotonic() - started, 1)}),
                          flush=True)
            return torch.cat(features), torch.tensor(labels, dtype=torch.long)

        train_labels = [class_to_index[name.split("/")[2]] for name in selected_train]
        val_labels = [class_to_index[annotations[Path(name).name]] for name in selected_val]
        x_train, y_train = extract(selected_train, train_labels)
        x_val, y_val = extract(selected_val, val_labels)

    torch.manual_seed(args.seed)
    probe = torch.nn.Linear(x_train.shape[1], len(wnids))
    optimizer = torch.optim.SGD(probe.parameters(), lr=args.learning_rate, momentum=0.9)
    criterion = torch.nn.CrossEntropyLoss()
    generator = torch.Generator().manual_seed(args.seed)
    history = []
    for epoch in range(args.epochs):
        order = torch.randperm(len(x_train), generator=generator)
        total_loss = 0.0
        for start in range(0, len(order), args.batch_size):
            batch = order[start:start + args.batch_size]
            loss = criterion(probe(x_train[batch]), y_train[batch])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += float(loss) * len(batch)
        with torch.no_grad():
            predictions = probe(x_val).argmax(dim=-1)
            accuracy = float((predictions == y_val).float().mean())
        row = {"epoch": epoch + 1, "train_loss": total_loss / len(x_train),
               "val_accuracy": accuracy}
        history.append(row)
        print(json.dumps(row), flush=True)

    receipt = {
        "schema": "qone-tiny-imagenet-linear-probe-v1",
        "official": False,
        "model": f"timm/{args.model_name}",
        "weights": str(args.weights),
        "weights_sha256": sha256_file(args.weights),
        "zip": str(args.zip),
        "zip_sha256": sha256_file(args.zip),
        "device": args.device,
        "seed": args.seed,
        "frozen_backbone": True,
        "feature_dim": int(x_train.shape[1]),
        "classes": len(wnids),
        "train_images": int(len(x_train)),
        "val_images": int(len(x_val)),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "history": history,
        "final_val_accuracy": history[-1]["val_accuracy"],
        "elapsed_s": round(time.monotonic() - started, 2),
        "note": ("Real frozen ResNet-50 features and trained linear probe on public "
                 "Tiny-ImageNet-200; not ImageNet-1K, not paper-level OOD results, "
                 "and not an official PaperBench judge score."),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(json.dumps(receipt, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
