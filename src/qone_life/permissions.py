"""Filesystem permission hardening for local life data (SECURITY.md OS-ACL).

The append-only JSONL stores hold private personal data. ``open(path, "a")``
creates files with ``0o666 & ~umask`` (observably ``0o664`` on a default
umask), which is group/world-readable. This module guarantees that both the
containing directory (``0o700``) and the data file (``0o600``) are owner-only,
regardless of the process umask.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO

FILE_MODE = 0o600
DIR_MODE = 0o700


def secure_dir(path: Path) -> None:
    """Create ``path`` (and parents) if needed, then tighten it to 0o700."""
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, DIR_MODE)
    except (NotImplementedError, OSError):
        # Filesystems without POSIX modes (e.g. some mounts) cannot be chmod'ed;
        # nothing more we can do here without failing the write.
        pass


@contextmanager
def secure_append(path: Path) -> Iterator[IO[str]]:
    """Open ``path`` for append, ensuring dir 0o700 and file 0o600."""
    secure_dir(path.parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, FILE_MODE)
    try:
        try:
            os.chmod(path, FILE_MODE)
        except OSError:
            pass
        handle = os.fdopen(fd, "a", encoding="utf-8")
    except Exception:
        os.close(fd)
        raise
    try:
        yield handle
    finally:
        handle.close()
