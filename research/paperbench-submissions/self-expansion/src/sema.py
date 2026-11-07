"""The SEMA continual-learning procedure (Algorithm 1 of the paper).

Rubric anchors:
- item 21-24: scan expandable layers before training task t, expand on
  triggered layers, skip the task when no layer triggers.
- item 25-27: when a module is added, its adapter / descriptor / router slice
  are trainable, all previously learned ones are frozen.
- item 28: classification head grows with the new classes.
- item 40-41: average accuracy A_N and incremental accuracy mean(A_t).
"""

from __future__ import annotations

import torch

from .descriptor import scan_for_expansion, should_skip_task, update_running_stats
from .trainer import evaluate, train_task


def prepare_task(model, n_new_classes: int) -> None:
    """Expand the classifier head for the new classes (item 28)."""
    model.add_classifier(n_new_classes)


def expand_layers(model, layers: set[int]) -> None:
    for li in sorted(layers):
        model.vit.blocks[li].add_module_pair()


def freeze_all_except_latest(model) -> None:
    for p in model.parameters():
        p.requires_grad = False
    for li in model.expandable_layers:
        model.vit.blocks[li].set_trainable("latest")
    for p in model.head.parameters():
        p.requires_grad = True


def run_sema(model, tasks, device="cpu", log=None, epochs: int = 1, scan_fraction: float = 1.0):
    """Run the task stream.

    ``tasks`` is a list of dicts with keys: ``train_loader``, ``test_loaders``
    (list of loaders for all tasks seen so far, in order), and ``n_new_classes``.
    """
    acc_matrix: list[list[float]] = []
    for ti, task in enumerate(tasks):
        if ti == 0:
            # First task has no adapters yet: expansion is unconditional so a
            # modular adapter exists in each expandable layer (Figure 1b).
            per_layer_z, to_expand = {}, set(model.expandable_layers)
        else:
            update_running_stats(model, task["train_loader"], device=device)
            per_layer_z, to_expand = scan_for_expansion(model, task["train_loader"], device=device)
        if should_skip_task(to_expand):
            if log:
                log(f"task {ti}: no expansion signal -> skipped (item 24)")
            acc_matrix.append(_eval_seen(model, tasks[: ti + 1], device, model.num_classes))
            continue
        if log:
            log(f"task {ti}: expansion in layers {sorted(to_expand)} (z={per_layer_z})")
        prepare_task(model, task["n_new_classes"])
        expand_layers(model, to_expand)
        freeze_all_except_latest(model)
        stats = train_task(model, task["train_loader"], device=device, epochs=epochs, log=log)
        if log:
            log(f"task {ti}: trained={not stats['skipped']}")
        acc_matrix.append(_eval_seen(model, tasks[: ti + 1], device, model.num_classes))
    avg_acc = _average_accuracy(acc_matrix)
    inc_acc = _incremental_accuracy(acc_matrix)
    return {"accuracy_matrix": acc_matrix, "A_N": avg_acc, "A_bar": inc_acc}


def _eval_seen(model, tasks, device, n_classes):
    """Accuracy on each task seen so far; shape grows with the stream."""
    return [evaluate(model, t["test_loader"], device=device) if t.get("test_loader") else 0.0
            for t in tasks]


def _average_accuracy(matrix):
    """item 40: A_N = (1/N) sum_i A_{i,N} over all seen tasks."""
    if not matrix:
        return 0.0
    final = matrix[-1]
    return sum(final) / len(final) if final else 0.0


def _incremental_accuracy(matrix):
    """item 41: A_bar = (1/N) sum_t A_t with A_t = mean_i A_{i,t}."""
    if not matrix:
        return 0.0
    per_task = [sum(row) / len(row) for row in matrix if row]
    return sum(per_task) / len(per_task) if per_task else 0.0
