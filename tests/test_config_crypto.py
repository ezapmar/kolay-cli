"""Tests for config encryption at rest."""
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


def test_encrypt_decrypt_roundtrip():
    """Encrypted data can be decrypted back to original."""
    plaintext = b'{"base_url": "https://api.kolayik.com"}'
    ciphertext = encrypt_bytes(plaintext)
    assert ciphertext != plaintext
    assert decrypt_bytes(ciphertext) == plaintext


def test_is_encrypted_detects_fernet():
    """Fernet ciphertext starts with 'gAAAAA'."""
    ciphertext = encrypt_bytes(b"test")
    assert is_encrypted(ciphertext)


def test_is_encrypted_rejects_plaintext():
    """Plain JSON is not detected as encrypted."""
    assert not is_encrypted(b'{"key": "value"}')
    assert not is_encrypted(b"base_url: https://api.kolayik.com\n")


def test_is_encryption_enabled_default_false():
    """Encryption is disabled by default."""
    with patch.dict(os.environ, {}, clear=True):
        # Remove var if it exists
        os.environ.pop("KOLAY_ENCRYPT_CONFIG", None)
        assert not is_encryption_enabled()


def test_is_encryption_enabled_true():
    """Encryption is enabled when env var is set."""
    with patch.dict(os.environ, {"KOLAY_ENCRYPT_CONFIG": "true"}):
        assert is_encryption_enabled()


def test_decrypt_config_file_plaintext():
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


def test_decrypt_config_file_encrypted():
    """Encrypted config files are decrypted transparently."""
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


def test_decrypt_config_file_missing():
    """Non-existent files return None."""
    assert decrypt_config_file(Path("/tmp/nonexistent_kolay_config.json")) is None


def test_encrypt_and_write_plaintext():
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


def test_encrypt_and_write_encrypted():
    """When encryption is enabled, files are written as Fernet ciphertext."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)

    try:
        with patch.dict(os.environ, {"KOLAY_ENCRYPT_CONFIG": "true"}):
            encrypt_and_write(path, {"key": "value"})
        
        raw = path.read_bytes()
        assert is_encrypted(raw)

        # Can be read back
        result = decrypt_config_file(path)
        data = json.loads(result)
        assert data["key"] == "value"
    finally:
        path.unlink()
