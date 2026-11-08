#!/usr/bin/env python3
"""Download and verify the public Jigsaw train.csv mirror."""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

URL = (
    "https://huggingface.co/datasets/thesofakillers/"
    "jigsaw-toxic-comment-classification-challenge/resolve/main/train.csv"
)
EXPECTED_BYTES = 68802655
EXPECTED_SHA256 = "bd4084611bd27c939ba98e5e63bc3e5a2c1a4e99477dcba46c829e4c986c429d"
OUTPUT = Path(__file__).resolve().parent / "train.csv"


def main() -> int:
    if not OUTPUT.is_file():
        urllib.request.urlretrieve(URL, OUTPUT)
    data = OUTPUT.read_bytes()
    if len(data) != EXPECTED_BYTES:
        raise ValueError(f"expected {EXPECTED_BYTES} bytes, got {len(data)}")
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f"SHA-256 mismatch: {digest}")
    print(f"OK {OUTPUT} {len(data)} bytes {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
