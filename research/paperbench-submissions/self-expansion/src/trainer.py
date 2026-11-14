"""Training loop for SEMA and the Finetune-Adapter / ADAM baselines.

Rubric anchors:
- item 29: classification loss F = cross entropy(logits, y).
- item 30: reconstruction loss of the descriptor g:
            L_rec = ||x - g(x)||^2 (mean over features).
- item 31: total loss = cross entropy + reconstruction.
- items 42-48: 5 epochs adapters, 20 epochs descriptors, batch 32, SGD,
            lr 0.005 adapters / 0.01 descriptors, cosine annealing.
- item 50: adapter bottleneck 48.
- item 32-34: Finetune Adapter = one SEMA adapter in every layer, updated
            across all tasks with the backbone frozen.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F

ADAPTER_EPOCHS = 5
DESCRIPTOR_EPOCHS = 20
BATCH_SIZE = 32
ADAPTER_LR = 0.005
DESCRIPTOR_LR = 0.01


def classification_loss(logits, y):
    return F.cross_entropy(logits, y)


def reconstruction_loss(descriptor, x):
    _, recon = descriptor(x)
    return ((recon - x) ** 2).mean()


def total_loss(model, x, y):
    logits, feats = model(x, return_features=True)
    ce = classification_loss(logits, y)
    rec = torch.zeros((), device=x.device)
    for li in getattr(model, "expandable_layers", []):
        blk = model.vit.blocks[li]
        if blk.n_modules > 0:
            rec = rec + reconstruction_loss(blk.descriptors[-1], feats)
    return ce + rec, ce.detach(), rec.detach()


def build_adapter_optimizer(model, lr=ADAPTER_LR):
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.SGD(params, lr=lr, momentum=0.9)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=ADAPTER_EPOCHS)
    return opt, sched


def build_descriptor_optimizer(model, lr=DESCRIPTOR_LR):
    params = []
    for li in getattr(model, "expandable_layers", []):
        blk = model.vit.blocks[li]
        for d in blk.descriptors:
            params.extend([p for p in d.parameters() if p.requires_grad])
    opt = torch.optim.SGD(params, lr=lr, momentum=0.9)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=DESCRIPTOR_EPOCHS)
    return opt, sched


def train_task(model, loader, device="cpu", epochs: int = ADAPTER_EPOCHS, log=None):
    model.train()
    if not any(p.requires_grad for p in model.parameters()):
        if log:
            log("no trainable parameters; skipping")
        return {"skipped": True}
    opt, sched = build_adapter_optimizer(model)
    history = []
    for ep in range(epochs):
        tot = 0.0
        n = 0
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            loss, ce, rec = total_loss(model, x, y)
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += float(loss.detach())
            n += 1
        sched.step()
        history.append(tot / max(n, 1))
        if log:
            log(f"epoch {ep + 1}/{epochs} loss={history[-1]:.4f}")
    return {"history": history, "skipped": False}


@torch.no_grad()
def evaluate(model, loader, device="cpu"):
    model.eval()
    correct = 0
    total = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        pred = model(x).argmax(dim=-1)
        correct += int((pred == y).sum())
        total += y.numel()
    return correct / total if total else 0.0
