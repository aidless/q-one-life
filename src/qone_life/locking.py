"""Cross-platform advisory locks for local Q-One files."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import portalocker


@contextmanager
def exclusive_file_lock(
    path: str | os.PathLike[str],
    *,
    timeout: float = 15,
    fail_fast: bool = False,
) -> Iterator[None]:
    """Hold an exclusive lock without silently degrading on unsupported systems."""

    lock_path = Path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = portalocker.Lock(
        lock_path,
        mode="a+",
        timeout=timeout,
        fail_when_locked=fail_fast,
        flags=portalocker.LockFlags.EXCLUSIVE | portalocker.LockFlags.NON_BLOCKING,
        encoding="utf-8",
    )
    with lock:
        if os.name != "nt":
            os.chmod(lock_path, 0o600)
        yield
