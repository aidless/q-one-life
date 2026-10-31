"""面向消费级桌面应用的、经认证且由恢复密钥包裹的备份。

应用数据库本身由操作系统保护；本模块只保护可携带的备份容器：载荷密钥是随机的，
恢复密钥再用经 Argon2id 派生的 AES-GCM 密钥来包裹这个载荷密钥。
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import tempfile
import zlib
from pathlib import Path
from typing import Any

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .repository import SCHEMA_VERSION

FORMAT = "q-one-encrypted-backup-v1"
DATA_KEY_BYTES = 32
MAX_CONTAINER_BYTES = 64 * 1024 * 1024
DEFAULT_KDF = {
    "name": "argon2id",
    "memory_kib": 64 * 1024,
    "iterations": 3,
    "parallelism": 4,
}
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_CROCKFORD_REVERSE = {char: index for index, char in enumerate(_CROCKFORD)}
_AAD_PAYLOAD = b"q-one-encrypted-backup-payload-v1"
_AAD_WRAPPED_KEY = b"q-one-encrypted-backup-data-key-v1"


class BackupCryptoError(ValueError):
    """容器格式错误或恢复密钥不正确时抛出。"""


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _unb64(value: Any, field: str) -> bytes:
    """把 base64 字符串解码为字节；类型或内容不合法时抛出中文错误。"""
    if not isinstance(value, str):
        raise BackupCryptoError(f"{field} is missing")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeError) as exc:
        raise BackupCryptoError(f"{field} is not valid base64") from exc


def _canonical(value: Any) -> bytes:
    """生成确定性的 JSON 字节串（键排序、无多余空白），供加密与哈希使用。"""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _encode_crockford(raw: bytes) -> str:
    """把字节编码为 Crockford base32 文本。"""
    value = int.from_bytes(raw, "big")
    characters = []
    for shift in range((len(raw) * 8 + 4) // 5 - 1, -1, -1):
        characters.append(_CROCKFORD[(value >> (shift * 5)) & 31])
    return "".join(characters)


def _decode_crockford(text: str, expected_bytes: int) -> bytes:
    """把用户输入的恢复密钥文本解码回字节。"""
    characters = text.strip().upper()
    characters = characters.removeprefix("Q1")
    for separator in ("-", " ", "_"):
        characters = characters.replace(separator, "")
    # 把易混淆的字母统一到数字：I/L→1、O→0。
    characters = characters.replace("I", "1").replace("L", "1").replace("O", "0")

    # 逐字符校验是否属于合法字母表，遇到非法字符立即停止。
    invalid = False
    for char in characters:
        if char not in _CROCKFORD_REVERSE:
            invalid = True
            break
    if not characters or invalid:
        raise BackupCryptoError("恢复密钥包含无效字符")

    value = 0
    for char in characters:
        value = (value << 5) | _CROCKFORD_REVERSE[char]
    # 编码端输出 ceil(bytes*8/5) 个 base32 字符；这里拒绝多余的、非零的填充位，
    # 而不是默默接受一个不同的密钥。
    padding = len(characters) * 5 - expected_bytes * 8
    if padding < 0 or value >> (expected_bytes * 8):
        raise BackupCryptoError("恢复密钥长度不正确")
    return value.to_bytes(expected_bytes, "big")


def encode_recovery_key(raw: bytes) -> str:
    """把 32 字节密钥编码为带校验和的 "Q1-XXXX-…" 恢复密钥。"""
    if len(raw) != DATA_KEY_BYTES:
        raise ValueError("recovery keys must contain 256 bits")
    checksum = struct.pack(">I", zlib.crc32(raw) & 0xFFFFFFFF)
    encoded = _encode_crockford(raw + checksum)
    groups = []
    for index in range(0, len(encoded), 8):
        groups.append(encoded[index:index + 8])
    return "Q1-" + "-".join(groups)


def decode_recovery_key(value: str) -> bytes:
    """解析恢复密钥并校验校验和，返回 32 字节密钥。"""
    if not isinstance(value, str) or len(value) > 200:
        raise BackupCryptoError("恢复密钥格式不正确")
    raw = _decode_crockford(value, DATA_KEY_BYTES + 4)
    key, checksum = raw[:DATA_KEY_BYTES], raw[DATA_KEY_BYTES:]
    if struct.unpack(">I", checksum)[0] != (zlib.crc32(key) & 0xFFFFFFFF):
        raise BackupCryptoError("恢复密钥校验失败")
    return key


def _validate_kdf(raw: Any) -> dict[str, Any]:
    """校验并规范化 KDF 参数，确保落在安全边界内。"""
    if not isinstance(raw, dict) or raw.get("name") != "argon2id":
        raise BackupCryptoError("备份 KDF 参数无效")
    memory_kib = raw.get("memory_kib")
    iterations = raw.get("iterations")
    parallelism = raw.get("parallelism")
    if (
        type(memory_kib) is not int
        or not 8 * 1024 <= memory_kib <= 256 * 1024
        or type(iterations) is not int
        or not 1 <= iterations <= 10
        or type(parallelism) is not int
        or not 1 <= parallelism <= 16
    ):
        raise BackupCryptoError("备份 KDF 参数超出安全边界")
    return {
        "name": "argon2id",
        "memory_kib": memory_kib,
        "iterations": iterations,
        "parallelism": parallelism,
    }


def _derive_key(recovery_key: bytes, salt: bytes, kdf: dict[str, Any]) -> bytes:
    """用 Argon2id 从恢复密钥派生出密钥加密密钥（KEK）。"""
    return hash_secret_raw(
        secret=recovery_key,
        salt=salt,
        time_cost=kdf["iterations"],
        memory_cost=kdf["memory_kib"],
        parallelism=kdf["parallelism"],
        hash_len=32,
        type=Type.ID,
    )


def _header(created_at: Any, kdf: dict[str, Any], salt: bytes) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "kdf": kdf,
        "salt": _b64(salt),
    }


def _payload_aad(created_at: Any, kdf: dict[str, Any], salt: bytes) -> bytes:
    return _AAD_PAYLOAD + _canonical(_header(created_at, kdf, salt))


def _wrapped_key_aad(created_at: Any, kdf: dict[str, Any], salt: bytes) -> bytes:
    return _AAD_WRAPPED_KEY + _canonical(_header(created_at, kdf, salt))


def encrypt_backup(
    raw: dict[str, Any],
    data_key: bytes,
    recovery_key: bytes,
    *,
    kdf: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """加密一个明文备份对象，返回可序列化的容器字典。"""
    if len(data_key) != DATA_KEY_BYTES or len(recovery_key) != DATA_KEY_BYTES:
        raise ValueError("backup and recovery keys must contain 256 bits")
    if not isinstance(raw, dict):
        raise ValueError("backup payload must be an object")  # noqa: TRY004 - 输入校验统一用 ValueError
    params = _validate_kdf(kdf or DEFAULT_KDF)
    salt = os.urandom(16)
    payload_nonce = os.urandom(12)
    wrap_nonce = os.urandom(12)
    plaintext = _canonical(raw)
    kek = _derive_key(recovery_key, salt, params)
    created_at = raw.get("created_at")
    payload_ciphertext = AESGCM(data_key).encrypt(
        payload_nonce,
        plaintext,
        _payload_aad(created_at, params, salt),
    )
    wrapped_key = AESGCM(kek).encrypt(
        wrap_nonce,
        data_key,
        _wrapped_key_aad(created_at, params, salt),
    )
    return {
        "format": FORMAT,
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "kdf": params | {"salt": _b64(salt)},
        "payload": {
            "nonce": _b64(payload_nonce),
            "ciphertext": _b64(payload_ciphertext),
            "sha256": hashlib.sha256(plaintext).hexdigest(),
            "size": len(plaintext),
        },
        "wrapped_key": {
            "nonce": _b64(wrap_nonce),
            "ciphertext": _b64(wrapped_key),
        },
    }


def inspect_backup(container: dict[str, Any]) -> dict[str, Any]:
    """只做结构与范围校验，不接触密钥（用于展示与预检）。"""
    if not isinstance(container, dict) or container.get("format") != FORMAT:
        raise BackupCryptoError("不是受支持的 Q-One 加密备份")
    if (
        type(container.get("schema_version")) is not int
        or container.get("schema_version") != SCHEMA_VERSION
    ):
        raise BackupCryptoError("备份数据库版本与当前应用不兼容")
    kdf = _validate_kdf(container.get("kdf"))
    created_at = container.get("created_at")
    if created_at is not None and (
        not isinstance(created_at, str) or len(created_at) > 80
    ):
        raise BackupCryptoError("备份创建时间无效")
    salt = _unb64(container["kdf"].get("salt"), "salt")
    if len(salt) != 16:
        raise BackupCryptoError("备份盐值长度不正确")
    payload = container.get("payload")
    wrapped = container.get("wrapped_key")
    if (
        not isinstance(payload, dict)
        or not isinstance(wrapped, dict)
        or type(payload.get("size")) is not int
        or len(_unb64(payload.get("nonce"), "payload nonce")) != 12
        or len(_unb64(payload.get("ciphertext"), "payload")) < 16
        or len(_unb64(wrapped.get("nonce"), "wrapped key nonce")) != 12
        or len(_unb64(wrapped.get("ciphertext"), "wrapped key")) != DATA_KEY_BYTES + 16
    ):
        raise BackupCryptoError("备份载荷信息无效")
    if not 0 <= payload["size"] <= MAX_CONTAINER_BYTES:
        raise BackupCryptoError("备份过大")
    digest = payload.get("sha256")

    # 校验明文摘要必须是 64 位十六进制字符。
    digest_invalid = False
    if not isinstance(digest, str) or len(digest) != 64:
        digest_invalid = True
    else:
        for char in digest:
            if char not in "0123456789abcdef":
                digest_invalid = True
                break
    if digest_invalid:
        raise BackupCryptoError("备份明文校验信息无效")
    return {
        "format": FORMAT,
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "size": payload["size"],
        "sha256": digest,
        "kdf": kdf,
    }


def decrypt_backup(container: dict[str, Any], recovery_key: bytes) -> dict[str, Any]:
    """用恢复密钥解包数据密钥并解密载荷，返回明文对象。"""
    if len(recovery_key) != DATA_KEY_BYTES:
        raise BackupCryptoError("恢复密钥长度不正确")
    metadata = inspect_backup(container)
    kdf = metadata["kdf"]
    salt = _unb64(container["kdf"].get("salt"), "salt")
    created_at = metadata["created_at"]
    try:
        kek = _derive_key(recovery_key, salt, kdf)
        wrapped = container["wrapped_key"]
        wrap_nonce = _unb64(wrapped.get("nonce"), "wrapped key nonce")
        wrap_ciphertext = _unb64(wrapped.get("ciphertext"), "wrapped key")
        data_key = AESGCM(kek).decrypt(
            wrap_nonce,
            wrap_ciphertext,
            _wrapped_key_aad(created_at, kdf, salt),
        )
        if len(data_key) != DATA_KEY_BYTES:
            raise BackupCryptoError("备份数据密钥长度不正确")
        payload = container["payload"]
        payload_nonce = _unb64(payload.get("nonce"), "payload nonce")
        payload_ciphertext = _unb64(payload.get("ciphertext"), "payload")
        plaintext = AESGCM(data_key).decrypt(
            payload_nonce,
            payload_ciphertext,
            _payload_aad(created_at, kdf, salt),
        )
    except Exception as exc:
        # 已经是我们定义的中文错误就直接抛，其它底层异常统一归为"密钥错误或损坏"。
        if isinstance(exc, BackupCryptoError):
            raise
        raise BackupCryptoError("恢复密钥错误或备份已损坏") from exc
    if len(plaintext) != metadata["size"]:
        raise BackupCryptoError("备份明文长度与清单不一致")
    if hashlib.sha256(plaintext).hexdigest() != metadata["sha256"]:
        raise BackupCryptoError("备份明文校验失败")
    try:
        raw = json.loads(plaintext)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupCryptoError("备份明文不是有效 JSON") from exc
    if not isinstance(raw, dict):
        raise BackupCryptoError("备份明文不是对象")
    return raw


def write_container(path: str | os.PathLike[str], container: dict[str, Any]) -> None:
    """原子地写入容器文件：先写临时文件并 fsync，再替换目标文件。"""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    encoded = (_canonical(container) + b"\n")
    if len(encoded) > MAX_CONTAINER_BYTES:
        raise BackupCryptoError("加密后的备份超过大小上限")
    fd, temporary = tempfile.mkstemp(prefix=".qonebackup-", dir=destination.parent)
    try:
        if os.name != "nt":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        if os.name != "nt":
            directory_fd = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        try:
            Path(temporary).unlink()
        except FileNotFoundError:
            pass


def read_container(path: str | os.PathLike[str]) -> dict[str, Any]:
    """读取并解析容器文件，先按大小上限做保护。"""
    source = Path(path)
    if source.stat().st_size > MAX_CONTAINER_BYTES:
        raise BackupCryptoError("备份文件超过大小上限")
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupCryptoError("备份文件不是有效 JSON") from exc
    if not isinstance(raw, dict):
        raise BackupCryptoError("备份文件不是对象")
    return raw
