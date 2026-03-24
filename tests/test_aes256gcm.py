"""Tests for the AES-256-GCM cryptographic primitives (aes256gcm module).

Covers:
  - Encrypt / decrypt roundtrip
  - Authentication tag tamper detection (ciphertext, nonce, tag)
  - Nonce uniqueness across multiple encryptions
  - Ephemeral key generation properties
  - PBKDF2 key derivation determinism and salt sensitivity
  - Strict CryptoError on wrong key
"""
from __future__ import annotations

import os

import pytest

from kolay_cli.proxy.aes256gcm import (
    CryptoError,
    _KEY_BYTES,
    _NONCE_BYTES,
    _TAG_BYTES,
    decrypt,
    derive_key_pbkdf2,
    encrypt,
    generate_ephemeral_key,
)
import base64


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_key() -> bytes:
    return generate_ephemeral_key()


# ---------------------------------------------------------------------------
# encrypt / decrypt roundtrip
# ---------------------------------------------------------------------------

class TestEncryptDecryptRoundtrip:

    def test_basic_roundtrip(self) -> None:
        key = _make_key()
        plaintext = b"Hello, SOC2!"
        token = encrypt(plaintext, key)
        assert decrypt(token, key) == plaintext

    def test_empty_plaintext(self) -> None:
        key = _make_key()
        token = encrypt(b"", key)
        assert decrypt(token, key) == b""

    def test_large_payload(self) -> None:
        key = _make_key()
        plaintext = os.urandom(1_000_000)
        token = encrypt(plaintext, key)
        assert decrypt(token, key) == plaintext

    def test_binary_plaintext(self) -> None:
        key = _make_key()
        plaintext = bytes(range(256))
        assert decrypt(encrypt(plaintext, key), key) == plaintext

    def test_token_is_url_safe_base64_string(self) -> None:
        key = _make_key()
        token = encrypt(b"test", key)
        assert isinstance(token, str)
        # URL-safe base64 must not contain '+' or '/'
        assert "+" not in token
        assert "/" not in token

    def test_token_encodes_nonce_plus_ciphertext_plus_tag(self) -> None:
        key = _make_key()
        token = encrypt(b"x", key)
        raw = base64.urlsafe_b64decode(token)
        # nonce(12) + at-least-1-byte-ciphertext + tag(16)
        assert len(raw) >= _NONCE_BYTES + 1 + _TAG_BYTES


# ---------------------------------------------------------------------------
# Nonce uniqueness
# ---------------------------------------------------------------------------

class TestNonceUniqueness:

    def test_nonces_are_unique_across_calls(self) -> None:
        key = _make_key()
        nonces = set()
        for _ in range(1_000):
            token = encrypt(b"payload", key)
            raw = base64.urlsafe_b64decode(token)
            nonces.add(raw[:_NONCE_BYTES])
        assert len(nonces) == 1_000, "Nonce collision detected — CSPRNG failure"

    def test_same_plaintext_produces_different_tokens(self) -> None:
        key = _make_key()
        t1 = encrypt(b"same", key)
        t2 = encrypt(b"same", key)
        assert t1 != t2, "Identical tokens — nonce reuse detected"


# ---------------------------------------------------------------------------
# Tamper detection (authentication)
# ---------------------------------------------------------------------------

class TestTamperDetection:

    def _flip_byte(self, token: str, offset: int) -> str:
        raw = bytearray(base64.urlsafe_b64decode(token))
        raw[offset % len(raw)] ^= 0xFF
        return base64.urlsafe_b64encode(bytes(raw)).decode("ascii")

    def test_flip_ciphertext_byte_raises_crypto_error(self) -> None:
        key = _make_key()
        token = encrypt(b"sensitive data", key)
        # Flip byte somewhere in the ciphertext (after the nonce)
        tampered = self._flip_byte(token, _NONCE_BYTES + 2)
        with pytest.raises(CryptoError):
            decrypt(tampered, key)

    def test_flip_nonce_byte_raises_crypto_error(self) -> None:
        key = _make_key()
        token = encrypt(b"sensitive data", key)
        tampered = self._flip_byte(token, 3)  # within nonce
        with pytest.raises(CryptoError):
            decrypt(tampered, key)

    def test_flip_auth_tag_byte_raises_crypto_error(self) -> None:
        key = _make_key()
        token = encrypt(b"sensitive data", key)
        # Flip last byte (tag)
        raw = bytearray(base64.urlsafe_b64decode(token))
        raw[-1] ^= 0x01
        tampered = base64.urlsafe_b64encode(bytes(raw)).decode("ascii")
        with pytest.raises(CryptoError):
            decrypt(tampered, key)

    def test_truncated_payload_raises_crypto_error(self) -> None:
        key = _make_key()
        token = encrypt(b"data", key)
        raw = base64.urlsafe_b64decode(token)
        truncated = base64.urlsafe_b64encode(raw[:8]).decode("ascii")
        with pytest.raises(CryptoError):
            decrypt(truncated, key)

    def test_wrong_key_raises_crypto_error(self) -> None:
        key_a = _make_key()
        key_b = _make_key()
        assert key_a != key_b
        token = encrypt(b"top secret", key_a)
        with pytest.raises(CryptoError):
            decrypt(token, key_b)

    def test_random_bytes_raises_crypto_error(self) -> None:
        key = _make_key()
        garbage = base64.urlsafe_b64encode(os.urandom(64)).decode("ascii")
        with pytest.raises(CryptoError):
            decrypt(garbage, key)


# ---------------------------------------------------------------------------
# Key validation
# ---------------------------------------------------------------------------

class TestKeyValidation:

    def test_wrong_key_size_encrypt_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="32 bytes"):
            encrypt(b"data", b"tooshort")

    def test_wrong_key_size_decrypt_raises_crypto_error(self) -> None:
        key = _make_key()
        token = encrypt(b"data", key)
        with pytest.raises(CryptoError):
            decrypt(token, b"tooshort")


# ---------------------------------------------------------------------------
# Ephemeral key generation
# ---------------------------------------------------------------------------

class TestGenerateEphemeralKey:

    def test_returns_32_bytes(self) -> None:
        k = generate_ephemeral_key()
        assert len(k) == _KEY_BYTES

    def test_multiple_calls_return_different_keys(self) -> None:
        keys = {generate_ephemeral_key() for _ in range(100)}
        assert len(keys) == 100, "Collision in ephemeral key generation"

    def test_key_is_raw_bytes_not_base64(self) -> None:
        k = generate_ephemeral_key()
        assert isinstance(k, bytes)
        # A raw 32-byte key cannot be a valid ASCII string (would include non-ASCII)
        # — we just assert it is exactly 32 bytes, no padding
        assert len(k) == 32


# ---------------------------------------------------------------------------
# PBKDF2 key derivation
# ---------------------------------------------------------------------------

class TestDeriveKeyPbkdf2:

    def test_returns_32_bytes(self) -> None:
        k = derive_key_pbkdf2(b"seed", os.urandom(16))
        assert len(k) == _KEY_BYTES

    def test_deterministic_same_inputs(self) -> None:
        salt = os.urandom(16)
        k1 = derive_key_pbkdf2(b"seed", salt)
        k2 = derive_key_pbkdf2(b"seed", salt)
        assert k1 == k2

    def test_different_salts_produce_different_keys(self) -> None:
        k1 = derive_key_pbkdf2(b"seed", b"\x00" * 16)
        k2 = derive_key_pbkdf2(b"seed", b"\xFF" * 16)
        assert k1 != k2

    def test_different_seeds_produce_different_keys(self) -> None:
        salt = os.urandom(16)
        k1 = derive_key_pbkdf2(b"seed_a", salt)
        k2 = derive_key_pbkdf2(b"seed_b", salt)
        assert k1 != k2

    def test_derived_key_is_usable_for_encryption(self) -> None:
        salt = os.urandom(16)
        key = derive_key_pbkdf2(b"hostname:user", salt)
        plaintext = b"config data"
        assert decrypt(encrypt(plaintext, key), key) == plaintext
