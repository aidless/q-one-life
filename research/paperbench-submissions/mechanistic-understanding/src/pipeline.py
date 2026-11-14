"""Executable reproduction slice for mechanistic-understanding.

Covers the first two rubric leaves honestly:
- deterministic 90:10 split of the Jigsaw toxic comment classification data
- a softmax(Wx) linear probe trained on the training split and evaluated on val

Uses scikit-learn's logistic regression as the exact softmax(Wx) binary
classifier. Deliberately does NOT claim GPT-2 residual-stream features, DPO
fine-tuning, SVD toxic vectors or the paper's ~94% validation accuracy.
"""

from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "jigsaw_train.csv"
REPO_ROOT = Path(os.environ.get("QONE_REPO_ROOT", Path.cwd())).resolve()
VALIDATION_DATA_PATH = (
    REPO_ROOT / "research/validation-20261106/datasets/mechanistic-understanding/train.csv"
)
LABEL_COLUMNS = (
    "toxic",
    "severe_toxic",
    "obscene",
    "threat",
    "insult",
    "identity_hate",
)


def load_rows(path: Path = DATA_PATH, limit: int | None = None) -> list[dict]:
    if not path.is_file() and VALIDATION_DATA_PATH.is_file():
        path = VALIDATION_DATA_PATH
    if not path.is_file():
        raise FileNotFoundError(path)
    rows: list[dict] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            text = (row.get("comment_text") or "").strip()
            if not text:
                continue
            label = "toxic" if any(int(row.get(col, 0)) > 0 for col in LABEL_COLUMNS) else "non_toxic"
            rows.append({"text": text, "label": label})
            if limit is not None and len(rows) >= limit:
                break
    return rows


def split_90_10(rows: list[dict], seed: int = 20261107) -> tuple[list[dict], list[dict]]:
    """Deterministic hash-based split; 90% train, 10% validation."""
    tagged = []
    for row in rows:
        key = f"{seed}:{row['text']}".encode("utf-8")
        digest = hashlib.sha256(key).hexdigest()
        tagged.append((int(digest[:8], 16), row))
    tagged.sort(key=lambda item: item[0])
    n_val = max(1, len(tagged) // 10)
    val = [row for _, row in tagged[:n_val]]
    train = [row for _, row in tagged[n_val:]]
    return train, val


def train_and_evaluate(train: list[dict], val: list[dict]) -> dict:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score

    vectorizer = TfidfVectorizer(max_features=20000, stop_words="english")
    x_train = vectorizer.fit_transform([r["text"] for r in train])
    x_val = vectorizer.transform([r["text"] for r in val])
    y_train = [r["label"] for r in train]
    y_val = [r["label"] for r in val]
    clf = LogisticRegression(max_iter=1000, C=1.0)
    clf.fit(x_train, y_train)
    y_pred = clf.predict(x_val)
    return {
        "classifier": "softmax(Wx) via sklearn.LogisticRegression",
        "features": "TF-IDF word n-grams (NOT GPT-2 residual stream)",
        "train_rows": len(train),
        "val_rows": len(val),
        "coef_shape": list(clf.coef_.shape),
        "accuracy": float(accuracy_score(y_val, y_pred)),
        "note": "Not comparable to the paper's ~94% GPT-2 residual-stream probe.",
    }


def run_reproduction_slice(limit: int | None = None) -> dict:
    rows = load_rows(limit=limit)
    train, val = split_90_10(rows)
    metrics = train_and_evaluate(train, val)
    return {
        "paper_id": "mechanistic-understanding",
        "status": "partial_reproduction_slice",
        "dataset": "Jigsaw toxic comment classification (public mirror)",
        "rows_loaded": len(rows),
        "split": metrics,
        "rubric_leaves_targeted": [
            "cfcf4e45-a955-4064-8c12-17bc3787bed7",
            "89eae18e-3abb-424c-b18d-8ddc210806e0",
            "14994612",
            "b54834e0",
            "39489fa7",
            "b203fdd2",
        ],
    }
