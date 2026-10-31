from __future__ import annotations

import base64
import json
import os
import queue
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from qone_life.desktop_restore import restore_stdin
from qone_life.encrypted_backup import (
    DEFAULT_KDF,
    decode_recovery_key,
    decrypt_backup,
    encode_recovery_key,
    encrypt_backup,
)
from qone_life.repository import DatabaseVersionError
from qone_life.store import LifeStore
from qone_life.web import create_app


class DesktopBoundaryTests(unittest.TestCase):
    def test_capability_is_required_for_api_reads_and_writes(self):
        capability = "c" * 64
        with tempfile.TemporaryDirectory() as folder:
            app = create_app(folder, capability=capability)
            with TestClient(app, base_url="http://127.0.0.1") as client:
                denied = client.get("/api/health")
                self.assertEqual(denied.status_code, 403, denied.text)
                self.assertEqual(denied.json()["error"]["code"], "DESKTOP_CAPABILITY_REQUIRED")
                self.assertTrue(denied.headers["X-Request-ID"])

                allowed = client.get(
                    "/api/health",
                    headers={"X-QOne-Capability": capability},
                )
                self.assertEqual(allowed.status_code, 200, allowed.text)
                self.assertEqual(allowed.json()["status"], "ok")

                static = client.get("/")
                self.assertEqual(static.status_code, 200)
                self.assertIn("consumer.js", static.text)
                advanced = client.get("/advanced")
                self.assertEqual(advanced.status_code, 200)
                self.assertIn("app.js", advanced.text)
                self.assertEqual(
                    client.get("/static/zh-CN.json").status_code,
                    200,
                )
                missing = client.get(
                    "/api/does-not-exist",
                    headers={"X-QOne-Capability": capability},
                )
                self.assertEqual(missing.status_code, 404, missing.text)
                self.assertEqual(missing.json()["error"]["code"], "RECORD_NOT_FOUND")
                self.assertTrue(missing.json()["error"]["request_id"])

    def test_database_schema_from_newer_release_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "app.sqlite3"
            connection = sqlite3.connect(database)
            connection.execute("PRAGMA user_version=2")
            connection.commit()
            connection.close()
            with self.assertRaises(DatabaseVersionError):
                create_app(folder)

    def test_encrypted_backup_roundtrip_and_tamper_detection(self):
        recovery_key = os.urandom(32)
        data_key = os.urandom(32)
        encoded = encode_recovery_key(recovery_key)
        self.assertEqual(decode_recovery_key(encoded), recovery_key)
        raw = {"format": "q-one-backup-v3", "schema_version": 1, "created_at": "now", "events": [], "tables": {}}
        container = encrypt_backup(
            raw,
            data_key,
            recovery_key,
            kdf={"name": "argon2id", "memory_kib": 8192, "iterations": 1, "parallelism": 1},
        )
        self.assertNotIn("q-one-backup-v3", json.dumps(container))
        self.assertEqual(decrypt_backup(container, recovery_key), raw)
        with self.assertRaises(ValueError):
            decrypt_backup(container, os.urandom(32))
        tampered = json.loads(json.dumps(container))
        ciphertext = bytearray(__import__("base64").b64decode(tampered["payload"]["ciphertext"]))
        ciphertext[0] ^= 1
        tampered["payload"]["ciphertext"] = __import__("base64").b64encode(ciphertext).decode()
        with self.assertRaises(ValueError):
            decrypt_backup(tampered, recovery_key)
        tampered_header = json.loads(json.dumps(container))
        tampered_header["created_at"] = "tampered"
        with self.assertRaises(ValueError):
            decrypt_backup(tampered_header, recovery_key)
        self.assertEqual(DEFAULT_KDF["name"], "argon2id")

    def test_payload_is_encrypted_with_the_random_data_key_not_the_recovery_key(self):
        recovery_key = b"r" * 32
        raw = {
            "format": "q-one-backup-v3",
            "schema_version": 1,
            "created_at": "2026-10-27T00:00:00+00:00",
            "events": [],
            "tables": {},
        }
        kdf = {
            "name": "argon2id",
            "memory_kib": 8192,
            "iterations": 1,
            "parallelism": 1,
        }
        random_values = [
            b"s" * 16,
            b"p" * 12,
            b"w" * 12,
            b"s" * 16,
            b"p" * 12,
            b"w" * 12,
        ]
        with patch("qone_life.encrypted_backup.os.urandom", side_effect=random_values):
            first = encrypt_backup(raw, b"a" * 32, recovery_key, kdf=kdf)
            second = encrypt_backup(raw, b"b" * 32, recovery_key, kdf=kdf)
        self.assertEqual(first["payload"]["nonce"], second["payload"]["nonce"])
        self.assertNotEqual(first["payload"]["ciphertext"], second["payload"]["ciphertext"])
        self.assertNotEqual(first["wrapped_key"]["ciphertext"], second["wrapped_key"]["ciphertext"])
        self.assertEqual(decrypt_backup(first, recovery_key), raw)
        self.assertEqual(decrypt_backup(second, recovery_key), raw)

    def test_desktop_backup_control_channel_and_restore(self):
        capability = "c" * 64
        control = "x" * 64
        recovery_key = os.urandom(32)
        data_key = os.urandom(32)
        with tempfile.TemporaryDirectory() as folder:
            app = create_app(
                folder,
                capability=capability,
                control_token=control,
                cloud_key="desktop-secret",
                secret_managed=True,
            )
            with TestClient(app, base_url="http://127.0.0.1") as client:
                headers = {
                    "X-QOne-Capability": capability,
                    "X-QOne-Client": "web",
                    "Content-Type": "application/json",
                }
                self.assertEqual(
                    client.post("/api/desktop/backup/export", json={}, headers=headers).status_code,
                    403,
                )
                container = client.post(
                    "/api/desktop/backup/export",
                    headers=headers | {"X-QOne-Control": control},
                    json={
                        "data_key": base64.b64encode(data_key).decode(),
                        "recovery_key": base64.b64encode(recovery_key).decode(),
                    },
                ).json()
                inspected = client.post(
                    "/api/desktop/backup/inspect",
                    headers=headers | {"X-QOne-Control": control},
                    json=container,
                )
                self.assertEqual(inspected.status_code, 200, inspected.text)
                decoded = client.post(
                    "/api/desktop/backup/decrypt",
                    headers=headers | {"X-QOne-Control": control},
                    json={
                        "container": container,
                        "recovery_key_text": encode_recovery_key(recovery_key),
                    },
                )
                self.assertEqual(decoded.status_code, 200, decoded.text)
                self.assertEqual(decoded.json()["schema_version"], 1)
                self.assertNotIn("desktop-secret", decoded.text)
                self.assertNotIn("desktop-secret", client.get("/api/settings", headers=headers).text)

            with tempfile.TemporaryDirectory() as target:
                raw = decoded.json()
                result = restore_stdin(
                    target,
                    replace=True,
                    stream=__import__("io").BytesIO(json.dumps(raw).encode()),
                )
                self.assertTrue(result["ok"])

    def test_local_model_session_secret_is_never_public_or_backed_up(self):
        token = "local-private-" + "t" * 64
        with tempfile.TemporaryDirectory() as folder:
            app = create_app(
                folder,
                local_model_url="http://127.0.0.1:43123/v1",
                local_model_name="Qwen3-0.6B-Q8_0",
                local_model_token=token,
            )
            with TestClient(app, base_url="http://localhost") as client:
                for path in ("settings", "bootstrap", "backup", "export"):
                    response = client.get("/api/" + path)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertNotIn(token, response.text)
                    self.assertNotIn("local_token", response.text)
                settings = client.get("/api/settings").json()
                self.assertTrue(settings["local_model_available"])
                self.assertEqual(settings["local_model"], "Qwen3-0.6B-Q8_0")

    def test_interrupted_restore_rolls_back_and_keeps_a_safety_copy(self):
        with tempfile.TemporaryDirectory() as source:
            app = create_app(source)
            with TestClient(app, base_url="http://127.0.0.1") as client:
                raw = client.get("/api/backup").json()

        with tempfile.TemporaryDirectory() as parent:
            target = Path(parent) / "data"
            target.mkdir()
            marker = target / "current-record.txt"
            marker.write_text("keep-me", encoding="utf-8")

            class ReplaceFault:
                calls = 0

                def __getattr__(self, name):
                    return getattr(os, name)

                def replace(self, source, destination):
                    self.calls += 1
                    if self.calls == 2:
                        raise OSError("simulated interruption")
                    return os.replace(source, destination)

            with (
                patch("qone_life.desktop_restore.os", ReplaceFault()),
                self.assertRaises(OSError),
            ):
                restore_stdin(
                    str(target),
                    replace=True,
                    stream=__import__("io").BytesIO(json.dumps(raw).encode()),
                )

            self.assertEqual(marker.read_text(encoding="utf-8"), "keep-me")
            self.assertFalse(any(path.name.startswith(".q-one-old-") for path in Path(parent).iterdir()))
            safety = [path for path in Path(parent).iterdir() if path.name.startswith(".q-one-safety-")]
            self.assertEqual(len(safety), 1)
            self.assertEqual(
                (safety[0] / "current-record.txt").read_text(encoding="utf-8"),
                "keep-me",
            )

    def test_restore_preserves_non_secret_settings_without_cloud_key(self):
        with tempfile.TemporaryDirectory() as source:
            app = create_app(source)
            with TestClient(app, base_url="http://127.0.0.1") as client:
                raw = client.get("/api/backup").json()

        with tempfile.TemporaryDirectory() as target:
            target_path = Path(target)
            (target_path / "settings.json").write_text(
                json.dumps(
                    {
                        "language": "zh-CN",
                        "cloud_key": "must-not-survive-restore",
                        "auto_recommend_enabled": True,
                    }
                ),
                encoding="utf-8",
            )
            result = restore_stdin(
                target,
                replace=True,
                stream=__import__("io").BytesIO(json.dumps(raw).encode()),
            )
            self.assertTrue(result["ok"])
            settings = json.loads((target_path / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(settings["language"], "zh-CN")
            self.assertNotIn("cloud_key", settings)

    @unittest.skipUnless(hasattr(urllib.request, "urlopen"), "urllib unavailable")
    def test_sidecar_handshake_and_single_instance_lock(self):
        capability = "s" * 64
        with tempfile.TemporaryDirectory() as folder:
            process = subprocess.Popen(
                [sys.executable, "-m", "qone_life.sidecar", "--data-dir", folder],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertIsNotNone(process.stdin)
            self.assertIsNotNone(process.stdout)
            process.stdin.write(
                json.dumps({"capability": capability, "control": "d" * 64}) + "\n"
            )
            process.stdin.close()
            lines: queue.Queue[str] = queue.Queue()
            threading.Thread(
                target=lambda: lines.put(process.stdout.readline()),
                daemon=True,
            ).start()
            try:
                line = lines.get(timeout=15)
            except queue.Empty:
                process.kill()
                stderr = process.stderr.read() if process.stderr else ""
                self.fail(f"sidecar did not produce a handshake: {stderr}")
            ready = json.loads(line)
            self.assertEqual(ready["event"], "ready")
            self.assertGreater(ready["port"], 0)
            self.assertEqual(ready["pid"], process.pid)

            url = f"http://127.0.0.1:{ready['port']}/api/health"
            with self.assertRaises(urllib.error.HTTPError) as denied:
                urllib.request.urlopen(url, timeout=5)
            self.assertEqual(denied.exception.code, 403)
            request = urllib.request.Request(
                url,
                headers={"X-QOne-Capability": capability},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(json.load(response)["status"], "ok")

            second = subprocess.run(
                [sys.executable, "-m", "qone_life.sidecar", "--data-dir", folder],
                input=json.dumps({"capability": "t" * 64, "control": "u" * 64}) + "\n",
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(second.returncode, 3, second.stdout + second.stderr)
            self.assertEqual(json.loads(second.stdout)["code"], "INSTANCE_ALREADY_RUNNING")

            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    def test_cross_process_file_lock_preserves_every_event(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = Path(folder) / "events.jsonl"
            script = """
import sys
from pathlib import Path
from qone_life.store import LifeStore
ledger = Path(sys.argv[1])
worker = int(sys.argv[2])
store = LifeStore(ledger)
for index in range(25):
    store.append("observation_recorded", {"worker": worker, "index": index})
"""
            processes = [
                subprocess.Popen([sys.executable, "-c", script, str(ledger), str(worker)])
                for worker in range(4)
            ]
            for process in processes:
                self.assertEqual(process.wait(timeout=20), 0)
            store = LifeStore(ledger)
            self.assertEqual(store.verify(), 100)
            events = store.events()
            self.assertEqual({event["seq"] for event in events}, set(range(1, 101)))

    def test_sidecar_rejects_missing_handshake(self):
        with tempfile.TemporaryDirectory() as folder:
            process = subprocess.run(
                [sys.executable, "-m", "qone_life.sidecar", "--data-dir", folder],
                input="",
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(process.returncode, 2)
            self.assertEqual(json.loads(process.stdout)["code"], "HANDSHAKE_INVALID")

    def test_sidecar_rejects_non_loopback_local_model_handshake(self):
        with tempfile.TemporaryDirectory() as folder:
            process = subprocess.run(
                [sys.executable, "-m", "qone_life.sidecar", "--data-dir", folder],
                input=json.dumps(
                    {
                        "capability": "c" * 64,
                        "control": "d" * 64,
                        "local_model_url": "https://models.example/v1",
                        "local_model_name": "Qwen3-0.6B-Q8_0",
                        "local_model_token": "t" * 64,
                    }
                )
                + "\n",
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
            self.assertEqual(json.loads(process.stdout)["code"], "HANDSHAKE_INVALID")


if __name__ == "__main__":
    unittest.main()
