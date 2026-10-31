"""桌面外壳用于维护恢复的入口（此时后台 sidecar 已停止）。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from .backup import apply_pending, validate_backup
from .repository import Repository


def _fsync_directory(directory: Path) -> None:
    """把目录元数据刷到磁盘（Windows 上跳过），保证 rename 结果真正落盘。"""
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _data_has_records(directory: Path) -> bool:
    """判断数据目录里除锁/设置/待恢复标记外，是否已有实际记录。"""
    if not directory.exists():
        return False
    ignored = {".q-one-desktop.lock", "settings.json", "restore.pending.json"}
    # 刻意用显式 for 循环表达（比 any 推导式更直白），此处忽略 lint 的合并建议。
    for child in directory.iterdir():  # noqa: SIM110
        if child.name not in ignored:
            return True
    return False


def _copy_settings(source: Path, target: Path) -> None:
    """把旧目录的 settings.json 复制到新目录（去掉云密钥，权限收紧）。"""
    settings = source / "settings.json"
    if not settings.exists():
        return
    try:
        raw = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(raw, dict):
        return
    raw.pop("cloud_key", None)
    target_settings = target.joinpath("settings.json")
    target_settings.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    target_settings.chmod(0o600)


def _build_staging(data_dir: Path, raw: dict, parent: Path) -> Path:
    """在数据目录同级的临时目录里重建恢复结果，成功后再整体替换。"""
    staging = Path(tempfile.mkdtemp(prefix=".q-one-restore-", dir=parent))
    try:
        repository = Repository(staging)

        # 先把待恢复内容写成待处理标记，再让 apply_pending 落库。
        marker = staging / "restore.pending.json"
        marker.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        marker.chmod(0o600)

        with repository.connect() as db:
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        from qone_core.ledger import Ledger

        ledger = Ledger(staging / "decisions.jsonl")
        apply_pending(staging, repository, ledger)
        _copy_settings(data_dir, staging)
        return staging
    except Exception:
        # 任何失败都要清理临时目录，避免留下半成品。
        shutil.rmtree(staging, ignore_errors=True)
        raise


def restore_stdin(data_dir: str, *, replace: bool, stream) -> dict:
    """从标准输入读取备份并恢复到 data_dir。

    流程：读入并校验备份 → 在临时目录重建 → 备份旧目录 → 原子替换。
    当目标目录已有数据且未显式允许替换时拒绝执行。
    """
    directory = Path(data_dir).expanduser().resolve()
    payload = stream.read()
    if not payload:
        raise ValueError("恢复数据为空")
    if len(payload) > 64 * 1024 * 1024:
        raise ValueError("恢复数据超过大小上限")

    raw = json.loads(payload)
    validate_backup(raw)
    directory.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    if _data_has_records(directory) and not replace:
        raise ValueError("当前数据目录非空；必须显式允许替换")

    staging = _build_staging(directory, raw, directory.parent)
    safety: Path | None = None
    try:
        # 目录已有内容时，先整份复制出一份安全副本。
        if directory.exists() and any(directory.iterdir()):
            safety = directory.parent / (
                ".q-one-safety-" + time.strftime("%Y%m%d-%H%M%S") + "-" + str(os.getpid())
            )
            shutil.copytree(directory, safety)
            _fsync_directory(safety)

        if directory.exists():
            # 先改名旧目录为 backup_old，再把 staging 换上来；失败时回滚。
            backup_old = directory.parent / (
                ".q-one-old-" + time.strftime("%Y%m%d-%H%M%S") + "-" + str(os.getpid())
            )
            os.replace(directory, backup_old)
            try:
                os.replace(staging, directory)
            except Exception:
                os.replace(backup_old, directory)
                raise
            shutil.rmtree(backup_old, ignore_errors=True)
        else:
            os.replace(staging, directory)

        _fsync_directory(directory.parent)
        return {
            "ok": True,
            "data_dir": str(directory),
            "safety": str(safety) if safety else None,
            "digest": hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest(),
        }
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def main(argv: list[str] | None = None, *, stdin=None) -> int:
    """命令行入口：读取备份并恢复，结果以 JSON 打印。"""
    parser = argparse.ArgumentParser(prog="qone-life restore")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--backup-stdin", action="store_true", required=True)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = restore_stdin(
            args.data_dir,
            replace=args.replace,
            stream=stdin or sys.stdin.buffer,
        )
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI 顶层兜底：任何异常须转成 JSON 错误并返回非零
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), flush=True)
        return 2
