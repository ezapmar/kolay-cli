"""Tests for config encryption at rest (AES-256-GCM migration)."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from kolay_cli.config_crypto import (
    encrypt_bytes,
    decrypt_bytes,
    is_encrypted,
    is_encryption_enabled,
    decrypt_config_file,
    encrypt_and_write,
)
from kolay_cli.proxy.aes256gcm import CryptoError


def test_encrypt_decrypt_roundtrip() -> None:
    """Encrypted data can be decrypted back to original."""
    plaintext = b'{"base_url": "https://api.kolayik.com"}'
    ciphertext = encrypt_bytes(plaintext)
    assert ciphertext != plaintext
    assert decrypt_bytes(ciphertext) == plaintext


def test_encrypted_output_starts_with_gcm_prefix() -> None:
    """AES-256-GCM ciphertext starts with 'KCFG1:'."""
    ciphertext = encrypt_bytes(b"test")
    assert ciphertext.startswith(b"KCFG1:")


def test_is_encrypted_detects_gcm_payload() -> None:
    """AES-256-GCM ciphertext is detected by is_encrypted()."""
    ciphertext = encrypt_bytes(b"test")
    assert is_encrypted(ciphertext)


def test_is_encrypted_detects_legacy_fernet() -> None:
    """Legacy Fernet prefix gAAAAA is still detected as encrypted."""
    assert is_encrypted(b"gAAAAAbXljcHl0aG9u")


def test_is_encrypted_rejects_plaintext() -> None:
    """Plain JSON/YAML is not detected as encrypted."""
    assert not is_encrypted(b'{"key": "value"}')
    assert not is_encrypted(b"base_url: https://api.kolayik.com\n")


def test_each_encryption_produces_different_ciphertext() -> None:
    """Fresh salt + nonce on each call — same input produces different output."""
    ct1 = encrypt_bytes(b"same plaintext")
    ct2 = encrypt_bytes(b"same plaintext")
    assert ct1 != ct2


def test_tampered_ciphertext_raises_crypto_error() -> None:
    """Bit-flip in ciphertext must raise CryptoError."""
    ct = bytearray(encrypt_bytes(b"secret config"))
    # Flip a byte well inside the GCM payload (after prefix + some base64)
    ct[20] ^= 0xFF
    with pytest.raises((CryptoError, Exception)):
        decrypt_bytes(bytes(ct))


def test_is_encryption_enabled_default_false() -> None:
    """Encryption is disabled by default."""
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("KOLAY_ENCRYPT_CONFIG", None)
        assert not is_encryption_enabled()


def test_is_encryption_enabled_true() -> None:
    """Encryption is enabled when env var is set."""
    with patch.dict(os.environ, {"KOLAY_ENCRYPT_CONFIG": "true"}):
        assert is_encryption_enabled()


def test_decrypt_config_file_plaintext() -> None:
    """Plaintext config files are returned as-is."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"base_url": "https://api.kolayik.com"}, f)
        f.flush()
        path = Path(f.name)

    try:
        result = decrypt_config_file(path)
        assert result is not None
        data = json.loads(result)
        assert data["base_url"] == "https://api.kolayik.com"
    finally:
        path.unlink()


def test_decrypt_config_file_encrypted() -> None:
    """AES-256-GCM encrypted config files are decrypted transparently."""
    plaintext = json.dumps({"base_url": "https://api.kolayik.com"})
    ciphertext = encrypt_bytes(plaintext.encode("utf-8"))

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".json", delete=False) as f:
        f.write(ciphertext)
        path = Path(f.name)

    try:
        result = decrypt_config_file(path)
        assert result is not None
        data = json.loads(result)
        assert data["base_url"] == "https://api.kolayik.com"
    finally:
        path.unlink()


def test_decrypt_config_file_missing() -> None:
    """Non-existent files return None."""
    assert decrypt_config_file(Path("/tmp/nonexistent_kolay_config_gcm.json")) is None


def test_encrypt_and_write_plaintext() -> None:
    """When encryption is disabled, files are written as plaintext."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)

    try:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KOLAY_ENCRYPT_CONFIG", None)
            encrypt_and_write(path, {"key": "value"})

        raw = path.read_bytes()
        assert not is_encrypted(raw)
        data = json.loads(raw)
        assert data["key"] == "value"
    finally:
        path.unlink()


def test_encrypt_and_write_encrypted() -> None:
    """When encryption is enabled, files are written as AES-256-GCM ciphertext."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)

    try:
        with patch.dict(os.environ, {"KOLAY_ENCRYPT_CONFIG": "true"}):
            encrypt_and_write(path, {"key": "value"})

        raw = path.read_bytes()
        assert is_encrypted(raw)
        assert raw.startswith(b"KCFG1:")  # confirm AES-256-GCM, not legacy Fernet

        # Roundtrip: must decrypt back cleanly
        result = decrypt_config_file(path)
        data = json.loads(result)  # type: ignore[arg-type]
        assert data["key"] == "value"
    finally:
        path.unlink()
