"""Desktop sidecar process with a one-time stdin/stdout handshake."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import portalocker
import uvicorn
from qone_agent.runtime import is_loopback

from . import __version__
from .locking import exclusive_file_lock
from .web import create_app

MAX_HANDSHAKE_BYTES = 64 * 1024
INSTANCE_LOCK = ".q-one-desktop.lock"


class SidecarError(RuntimeError):
    pass


def _read_handshake(stream) -> dict[str, Any]:
    line = stream.readline(MAX_HANDSHAKE_BYTES + 1)
    if not line:
        raise SidecarError("missing desktop handshake")
    if len(line.encode("utf-8")) > MAX_HANDSHAKE_BYTES:
        raise SidecarError("desktop handshake is too large")
    try:
        value = json.loads(line)
    except json.JSONDecodeError as exc:
        raise SidecarError("desktop handshake is not valid JSON") from exc
    if not isinstance(value, dict):
        raise SidecarError("desktop handshake must be an object")
    capability = value.get("capability")
    if not isinstance(capability, str) or not 32 <= len(capability) <= 512:
        raise SidecarError("desktop capability is invalid")
    control = value.get("control")
    if not isinstance(control, str) or not 32 <= len(control) <= 512:
        raise SidecarError("desktop control token is invalid")
    cloud_key = value.get("cloud_key")
    if cloud_key is not None and (not isinstance(cloud_key, str) or len(cloud_key) > 8192):
        raise SidecarError("desktop cloud key is invalid")
    locale = value.get("locale")
    if locale is not None and (not isinstance(locale, str) or len(locale) > 32):
        raise SidecarError("desktop locale is invalid")
    local_values = (
        value.get("local_model_url"),
        value.get("local_model_name"),
        value.get("local_model_token"),
    )
    if any(item is not None for item in local_values):
        local_url, local_name, local_token = local_values
        if (
            not isinstance(local_url, str)
            or not isinstance(local_name, str)
            or not isinstance(local_token, str)
            or len(local_url) > 256
            or len(local_name) > 128
            or not 32 <= len(local_token) <= 512
        ):
            raise SidecarError("desktop local model handshake is invalid")
        parsed = urlparse(local_url)
        if (
            parsed.scheme != "http"
            or not is_loopback(local_url)
            or parsed.username is not None
            or parsed.query
            or parsed.fragment
        ):
            raise SidecarError("desktop local model endpoint must be an uncredentialed loopback URL")
    return value


def _ready_payload(port: int) -> dict[str, Any]:
    return {
        "event": "ready",
        "port": port,
        "pid": os.getpid(),
        "version": __version__,
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(prog="qone-life-sidecar")
    command.add_argument("--data-dir", required=True)
    return command


def main(argv: list[str] | None = None, *, stdin=None, stdout=None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if argv[:1] == ["restore"]:
        from .desktop_restore import main as restore_main
        return restore_main(argv[1:], stdin=stdin)
    args = parser().parse_args(argv)
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    data_dir = Path(args.data_dir).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        os.chmod(data_dir, 0o700)

    try:
        handshake = _read_handshake(stdin)
    except SidecarError as exc:
        print(
            json.dumps(
                {"event": "error", "code": "HANDSHAKE_INVALID", "message": str(exc)}
            ),
            file=stdout,
            flush=True,
        )
        return 2

    try:
        with exclusive_file_lock(data_dir / INSTANCE_LOCK, timeout=0, fail_fast=True):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 0))
            sock.listen(2048)
            port = int(sock.getsockname()[1])
            app = create_app(
                data_dir,
                capability=handshake["capability"],
                control_token=handshake["control"],
                cloud_key=handshake.get("cloud_key"),
                secret_managed=True,
                default_locale=handshake.get("locale"),
                local_model_url=handshake.get("local_model_url"),
                local_model_name=handshake.get("local_model_name"),
                local_model_token=handshake.get("local_model_token"),
            )
            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=port,
                access_log=False,
                log_level="warning",
                server_header=False,
            )
            server = uvicorn.Server(config)
            print(json.dumps(_ready_payload(port)), file=stdout, flush=True)
            server.run(sockets=[sock])
            return 0
    except (portalocker.AlreadyLocked, BlockingIOError):
        print(
            json.dumps(
                {
                    "event": "error",
                    "code": "INSTANCE_ALREADY_RUNNING",
                    "message": "another Q-One desktop sidecar is already using this data directory",
                }
            ),
            file=stdout,
            flush=True,
        )
        return 3
    except Exception as exc:  # noqa: BLE001 - CLI 顶层兜底：转成错误事件并退出
        print(
            json.dumps(
                {
                    "event": "error",
                    "code": "SIDECAR_START_FAILED",
                    "message": str(exc),
                }
            ),
            file=stdout,
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
