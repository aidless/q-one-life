"""本地 Q-One 文件的跨平台建议性锁。"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import portalocker


@contextmanager
def exclusive_file_lock(
    path: str | os.PathLike[str],
    *,
    timeout: float = 15,
    fail_fast: bool = False,
) -> Iterator[None]:
    """持有排他锁；在不支持锁的系统上显式失败，而不是静默降级。

    参数：
    - timeout：等待锁的最长秒数；
    - fail_fast：为 True 时锁已被占用就立即报错（非阻塞试锁）。
    离开 with 块时自动释放锁；在非 Windows 系统上还会把锁文件权限收紧为仅属主可读写。
    """
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
