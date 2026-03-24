"""Config encryption at rest using AES-256-GCM (AEAD).

The encryption key is derived from machine identity via PBKDF2-HMAC-SHA256
(600,000 iterations, 32-byte output) with a cryptographically random 16-byte
salt that is generated fresh on every write and embedded in the ciphertext
payload.  The key is NEVER stored on disk.

Payload format (stored on disk, base64-encoded)
-----------------------------------------------
  [16-byte salt] [12-byte nonce] [ciphertext] [16-byte auth tag]
  -- all URL-safe base64 encoded --

The stored blob starts with prefix ``KCFG1:`` to distinguish it from plaintext
and from legacy Fernet payloads (``gAAAAA``).

Backward compatibility
----------------------
  Files with the Fernet prefix (``gAAAAA``) are attempted with the legacy
  Fernet key so that users can seamlessly migrate without re-typing credentials.
  New writes ALWAYS use AES-256-GCM.

Opt-in: set KOLAY_ENCRYPT_CONFIG=true to enable.
"""
from __future__ import annotations

import base64
import getpass
import json
import logging
import os
import platform
from pathlib import Path
from typing import Any

from .aes256gcm import (
    CryptoError,
    _SALT_BYTES,  # noqa: PLC2701  (internal constant reuse is intentional)
    derive_key_pbkdf2,
    encrypt as _gcm_encrypt,
    decrypt as _gcm_decrypt,
)

_log = logging.getLogger(__name__)

# Header prefix written before the base64 blob — machine-readable version tag
_GCM_PREFIX = b"KCFG1:"
# Legacy Fernet prefix — detect old-format files for graceful migration
_FERNET_PREFIX = b"gAAAAA"


def is_encryption_enabled() -> bool:
    """Return True if config encryption is enabled via env var."""
    return os.environ.get("KOLAY_ENCRYPT_CONFIG", "").lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Internal key derivation
# ---------------------------------------------------------------------------

def _machine_seed() -> bytes:
    """Return a stable machine-identity seed (hostname + OS username)."""
    return f"{platform.node()}:{getpass.getuser()}".encode("utf-8")


def _derive_key(salt: bytes) -> bytes:
    """Derive a 32-byte AES-256 key from machine identity + *salt*."""
    return derive_key_pbkdf2(_machine_seed(), salt)


# ---------------------------------------------------------------------------
# Public encrypt / decrypt bytes API
# ---------------------------------------------------------------------------

def encrypt_bytes(plaintext: bytes) -> bytes:
    """Encrypt plaintext bytes and return an AES-256-GCM ciphertext blob.

    A fresh 16-byte cryptographic salt is generated on every call.  The salt
    is embedded in the returned blob so that decryption can re-derive the key.

    Returns:
        ``KCFG1:<url-safe-base64(salt + nonce + ciphertext + tag)>`` as bytes.
    """
    salt = os.urandom(_SALT_BYTES)
    key = _derive_key(salt)
    # _gcm_encrypt returns base64(nonce + ciphertext + tag)
    gcm_token = _gcm_encrypt(plaintext, key)
    # Prepend salt to the decoded token so we can re-derive the key on decrypt
    gcm_raw = base64.urlsafe_b64decode(gcm_token)
    combined = base64.urlsafe_b64encode(salt + gcm_raw)
    return _GCM_PREFIX + combined


def decrypt_bytes(ciphertext: bytes) -> bytes:
    """Decrypt an AES-256-GCM ciphertext blob produced by `encrypt_bytes()`.

    Raises:
        CryptoError: if the payload is malformed, tampered, or the machine key
                     has changed.
    """
    stripped = ciphertext.strip()

    if stripped.startswith(_GCM_PREFIX):
        return _decrypt_gcm(stripped[len(_GCM_PREFIX):])

    if stripped.startswith(_FERNET_PREFIX):
        return _decrypt_legacy_fernet(stripped)

    raise CryptoError("Unrecognised ciphertext format")


def _decrypt_gcm(combined_b64: bytes) -> bytes:
    """Decrypt a GCM payload: base64(salt + nonce + ciphertext + tag)."""
    try:
        combined = base64.urlsafe_b64decode(combined_b64)
    except Exception as exc:
        raise CryptoError("Base64 decode failed") from exc

    if len(combined) < _SALT_BYTES:
        raise CryptoError("Payload too short — salt missing")

    salt = combined[:_SALT_BYTES]
    gcm_raw = combined[_SALT_BYTES:]
    gcm_token = base64.urlsafe_b64encode(gcm_raw).decode("ascii")

    key = _derive_key(salt)
    return _gcm_decrypt(gcm_token, key)


def _decrypt_legacy_fernet(ciphertext: bytes) -> bytes:
    """Attempt decryption with the legacy Fernet key (migration path only)."""
    try:
        import hashlib as _hashlib
        import base64 as _b64

        old_salt = b"kolay-cli-config-encryption-v1"
        seed = _machine_seed()
        dk = _hashlib.pbkdf2_hmac("sha256", seed, old_salt, 600_000, dklen=32)
        fernet_key = _b64.urlsafe_b64encode(dk)

        from cryptography.fernet import Fernet  # type: ignore[import-untyped]
        return Fernet(fernet_key).decrypt(ciphertext)
    except Exception as exc:
        raise CryptoError("Legacy Fernet decryption failed") from exc


def is_encrypted(raw: bytes) -> bool:
    """Return True if *raw* bytes look like an AES-256-GCM or legacy Fernet payload."""
    stripped = raw.lstrip()
    return stripped.startswith(_GCM_PREFIX) or stripped.startswith(_FERNET_PREFIX)


# ---------------------------------------------------------------------------
# File-level helpers (public API consumed by config.py)
# ---------------------------------------------------------------------------

def decrypt_config_file(path: Path) -> str | None:
    """Read a config file, decrypting transparently if necessary.

    Returns the plaintext string content, or None if the file does not exist,
    is empty, or decryption fails.
    """
    if not path.exists():
        return None

    raw = path.read_bytes()
    if not raw.strip():
        return None

    if is_encrypted(raw):
        try:
            return decrypt_bytes(raw.strip()).decode("utf-8")
        except (CryptoError, Exception):
            _log.warning(
                "Could not decrypt %s — machine key may have changed. "
                "Re-authenticate with 'kolay auth login'.",
                path,
            )
            return None
    else:
        return raw.decode("utf-8")


def encrypt_and_write(path: Path, data: dict[str, Any], use_yaml: bool = False) -> None:
    """Serialize *data* and write to *path*, encrypting if enabled.

    Args:
        path: Target file path.
        data: Config dict to serialize.
        use_yaml: If True, serialize as YAML; otherwise JSON.
    """
    if use_yaml:
        import yaml  # type: ignore[import-untyped]
        plaintext = yaml.dump(data, default_flow_style=False)
    else:
        plaintext = json.dumps(data, indent=2)

    content: bytes = plaintext.encode("utf-8")
    if is_encryption_enabled():
        content = encrypt_bytes(content)

    # Write with restricted permissions (owner-only)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(content)
