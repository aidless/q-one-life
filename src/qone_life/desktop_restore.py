"""Maintenance restore used by the desktop shell while the sidecar is stopped."""

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
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _data_has_records(directory: Path) -> bool:
    if not directory.exists():
        return False
    ignored = {".q-one-desktop.lock", "settings.json", "restore.pending.json"}
    return any(child.name not in ignored for child in directory.iterdir())


def _copy_settings(source: Path, target: Path) -> None:
    settings = source / "settings.json"
    if not settings.exists():
        return
    try:
        raw = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(raw, dict):
        raw.pop("cloud_key", None)
        target.joinpath("settings.json").write_text(
            json.dumps(raw, ensure_ascii=False),
            encoding="utf-8",
        )
        target.joinpath("settings.json").chmod(0o600)


def _build_staging(data_dir: Path, raw: dict, parent: Path) -> Path:
    staging = Path(tempfile.mkdtemp(prefix=".q-one-restore-", dir=parent))
    try:
        repository = Repository(staging)
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
        shutil.rmtree(staging, ignore_errors=True)
        raise


def restore_stdin(data_dir: str, *, replace: bool, stream) -> dict:
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
        if directory.exists() and any(directory.iterdir()):
            safety = directory.parent / (
                ".q-one-safety-" + time.strftime("%Y%m%d-%H%M%S") + "-" + str(os.getpid())
            )
            shutil.copytree(directory, safety)
            _fsync_directory(safety)
        if directory.exists():
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
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), flush=True)
        return 2
