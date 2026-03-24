"""Config encryption at rest using Fernet (AES-128-CBC + HMAC-SHA256).

The encryption key is derived from machine identity via PBKDF2 and is
never stored on disk. If the config file starts with the Fernet prefix
('gAAAAA'), it is treated as encrypted; otherwise it is read as plaintext
(backward-compatible).

Opt-in: set KOLAY_ENCRYPT_CONFIG=true to enable.
"""
from __future__ import annotations

import base64
import getpass
import hashlib
import json
import os
import platform
from pathlib import Path
from typing import Any

_PBKDF2_ITERATIONS = 600_000
_SALT = b"kolay-cli-config-encryption-v1"


def is_encryption_enabled() -> bool:
    """Return True if config encryption is enabled via env var."""
    return os.environ.get("KOLAY_ENCRYPT_CONFIG", "").lower() in ("1", "true", "yes")


def _derive_key() -> bytes:
    """Derive a 32-byte Fernet key from machine identity.

    Uses platform.node() (hostname) + getpass.getuser() (OS username)
    as the seed material, run through PBKDF2-HMAC-SHA256 with 600k rounds.
    """
    seed = f"{platform.node()}:{getpass.getuser()}".encode("utf-8")
    dk = hashlib.pbkdf2_hmac("sha256", seed, _SALT, _PBKDF2_ITERATIONS, dklen=32)
    return base64.urlsafe_b64encode(dk)


def _get_fernet():
    """Return a Fernet instance keyed to this machine."""
    from cryptography.fernet import Fernet
    return Fernet(_derive_key())


def encrypt_bytes(plaintext: bytes) -> bytes:
    """Encrypt plaintext bytes and return Fernet ciphertext."""
    return _get_fernet().encrypt(plaintext)


def decrypt_bytes(ciphertext: bytes) -> bytes:
    """Decrypt Fernet ciphertext and return plaintext bytes."""
    return _get_fernet().decrypt(ciphertext)


def is_encrypted(raw: bytes) -> bool:
    """Return True if raw bytes look like Fernet ciphertext."""
    return raw.lstrip().startswith(b"gAAAAA")


def decrypt_config_file(path: Path) -> str | None:
    """Read a config file, decrypting if necessary.

    Returns the plaintext string content, or None if the file
    does not exist or decryption fails.
    """
    if not path.exists():
        return None

    raw = path.read_bytes()
    if not raw.strip():
        return None

    if is_encrypted(raw):
        try:
            return decrypt_bytes(raw.strip()).decode("utf-8")
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                "Could not decrypt %s — machine key may have changed. "
                "Re-authenticate with 'kolay auth login'.",
                path,
            )
            return None
    else:
        return raw.decode("utf-8")


def encrypt_and_write(path: Path, data: dict[str, Any], use_yaml: bool = False) -> None:
    """Serialize data and write to path, encrypting if enabled.

    Args:
        path: Target file path.
        data: Config dict to serialize.
        use_yaml: If True, serialize as YAML; otherwise JSON.
    """
    if use_yaml:
        import yaml
        plaintext = yaml.dump(data, default_flow_style=False)
    else:
        plaintext = json.dumps(data, indent=2)

    content = plaintext.encode("utf-8")
    if is_encryption_enabled():
        content = encrypt_bytes(content)

    # Write with restricted permissions (owner-only)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(content)
