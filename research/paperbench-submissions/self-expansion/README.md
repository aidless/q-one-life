# SEMA (Self-Expansion of Pre-trained Models) — Reproduction Submission

Paper: "Self-Expansion of Pre-trained Models with Mixture of Adapters for Continual Learning" (Wang, Lu, Yao, Gong 2024).

## Scope

- `SEMA` method (modular adapters + representation descriptors + expanding router).
- `Finetune Adapter` baseline (unconditional adapters).
- `ADAM` baseline (AdaptFormer adapters).
- `LoRA` adapter.
- `ViT-B/16` backbone (image classification).

## Architecture

- Functional adapter: linear 768→48, ReLU, linear 48→768.
- Representation descriptor: linear 768→128, LeakyReLU(alpha=0.01), linear 128→768.
- Router: learnable matrix weighting adapter outputs (softmax over module slots).
- Adapters are inserted after LayerNorm in each transformer block's residual path.
- Expansion scope: last three transformer layers only.
- New modules when expansion triggered by distribution-shift result of descriptor z-scores.
- Loss: reconstruction term + classification cross-entropy.

## Data

- CIFAR-100 test-splice 10 classes.
- ImageNet-R organized into 10-class tasks (manifest only here).
- VTAB ADAM subset 5-domain split (manifest placeholder).

## Requirements

- `torch>=2.3`, `timm`, `numpy`, `torchvision` (optional), `datasets` (optional).

## Usage

```bash
pip install -r requirements.txt
python run_smoke.py --datasets cifar100,imagenet-r,vtab --epochs 1 --device cpu
```
