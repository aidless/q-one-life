"""本地生活数据的文件权限加固（对应 SECURITY.md 的 OS-ACL 约定）。

追加写入的 JSONL 存储保存的是私密个人数据。直接用 ``open(path, "a")`` 创建文件时，
权限是 ``0o666 & ~umask``（在默认 umask 下通常是 ``0o664``），同组和其他用户都可读。
本模块保证“所在目录为 0o700、数据文件为 0o600”，无论进程 umask 是什么。
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
    """确保目录存在（含父目录），并把权限收紧为 0o700。"""
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, DIR_MODE)
    except (NotImplementedError, OSError):
        # 有些挂载点没有 POSIX 权限位、无法 chmod；这种情况只能跳过，
        # 而不是因为改不了权限就让写入失败。
        pass


@contextmanager
def secure_append(path: Path) -> Iterator[IO[str]]:
    """以追加方式打开文件，并保证目录 0o700、文件 0o600。"""
    secure_dir(path.parent)

    # 用 os.open 直接指定创建权限 0o600，绕开 umask 的影响。
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, FILE_MODE)
    try:
        try:
            # 对“文件已存在”的情况，os.open 不会改权限，这里显式收紧一次。
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
