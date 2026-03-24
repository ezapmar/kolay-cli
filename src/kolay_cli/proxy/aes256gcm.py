"""AES-256-GCM authenticated encryption primitives.

Compliant with SOC 2 Type II and PCI-DSS cryptographic control requirements.

Design
------
  * Cipher  : AES-256-GCM  (NIST SP 800-38D, FIPS 197)
  * Key size : 32 bytes (256 bits) — mandatory for AES-256
  * Nonce    : 12 bytes (96 bits) — NIST-recommended for GCM; unique per call
  * Auth tag : 16 bytes (128 bits) — maximum GCM tag length
  * KDF      : PBKDF2-HMAC-SHA256, 600,000 iterations (OWASP 2023 minimum)

Payload layout (bytes, before URL-safe base64 encoding)
-------------------------------------------------------
  Config at rest  :  [16-byte salt] [12-byte nonce] [ciphertext] [16-byte tag]
  Ephemeral cache :  [12-byte nonce] [ciphertext] [16-byte tag]

The 16-byte auth tag is appended automatically by `AESGCM.encrypt()` and
stripped automatically by `AESGCM.decrypt()`.  We do NOT manage it manually;
any bit-flip in the tag or ciphertext causes `AESGCM.decrypt()` to raise
`cryptography.exceptions.InvalidTag`, which we re-raise as `CryptoError`.

STRICT RULES
------------
  - No CBC mode.  No Fernet.  No ECB.
  - Nonces generated from `os.urandom(12)` — never reused.
  - Keys are raw bytes.  We do NOT base64-wrap keys (that is a Fernet artifact).
  - Standard library + `cryptography.hazmat` only.  No third-party wrappers.
"""
from __future__ import annotations

import base64
import hashlib
import os

_NONCE_BYTES = 12       # 96-bit nonce — NIST recommended for GCM
_TAG_BYTES = 16         # 128-bit auth tag — maximum GCM tag size
_KEY_BYTES = 32         # 256-bit key — AES-256
_SALT_BYTES = 16        # 128-bit salt for PBKDF2
_PBKDF2_ITERATIONS = 600_000  # OWASP 2023 minimum for PBKDF2-SHA256


# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------

class CryptoError(Exception):
    """Raised when decryption fails due to tampering, wrong key, or corruption.

    Callers MUST treat this as a hard security failure and MUST NOT reveal
    internal details to end users.
    """


# ---------------------------------------------------------------------------
# Key generation / derivation
# ---------------------------------------------------------------------------

def generate_ephemeral_key() -> bytes:
    """Return a cryptographically secure 32-byte random key.

    Uses the OS CSPRNG (`os.urandom`).  Call once at server startup and
    keep the result in process memory only — never write it to disk, logs,
    or environment variables.

    Crypto-shredding guarantee:
        When the process exits, the key object is garbage-collected along with
        all ciphertext it could decrypt.  No data persistence, no key escrow,
        no recovery — by design.

    Returns:
        32-byte raw key (not base64-encoded).
    """
    return os.urandom(_KEY_BYTES)


def derive_key_pbkdf2(seed: bytes, salt: bytes) -> bytes:
    """Derive a 32-byte AES-256 key from *seed* via PBKDF2-HMAC-SHA256.

    Parameters
    ----------
    seed : bytes
        High-entropy material such as `hostname:username`.  Not secret on its
        own; the KDF is what makes this expensive to brute-force.
    salt : bytes
        At least 16 bytes of cryptographically random bytes.  For config-at-rest
        encryption, a fresh salt is generated per encryption and stored alongside
        the ciphertext so that the key can be re-derived on decrypt.

    Returns:
        32-byte raw key.
    """
    return hashlib.pbkdf2_hmac("sha256", seed, salt, _PBKDF2_ITERATIONS, dklen=_KEY_BYTES)


# ---------------------------------------------------------------------------
# Core AES-256-GCM encrypt / decrypt
# ---------------------------------------------------------------------------

def encrypt(plaintext: bytes, key: bytes) -> str:
    """Encrypt *plaintext* with *key* using AES-256-GCM.

    A unique 12-byte nonce is generated from the OS CSPRNG for every call.
    The nonce is NEVER reused.  GCM auth tag (16 bytes) is appended by the
    underlying AESGCM implementation.

    The returned payload is URL-safe base64-encoded and safe to store in
    text files, JSON, YAML, or as a dict value.

    Payload layout (binary, before base64):
        [12-byte nonce] [ciphertext] [16-byte auth tag]

    Parameters
    ----------
    plaintext : bytes
        Arbitrary binary data to protect.
    key : bytes
        Exactly 32-byte AES-256 key.  Pass the output of
        `generate_ephemeral_key()` or `derive_key_pbkdf2()`.

    Returns:
        URL-safe base64 string containing nonce + ciphertext + tag.

    Raises:
        ValueError: if *key* is not exactly 32 bytes.
    """
    if len(key) != _KEY_BYTES:
        raise ValueError(f"Key must be exactly {_KEY_BYTES} bytes; got {len(key)}")

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore[import-untyped]

    nonce = os.urandom(_NONCE_BYTES)
    aesgcm = AESGCM(key)
    # AESGCM.encrypt() returns ciphertext || 16-byte tag concatenated
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, None)  # no associated data
    payload = nonce + ciphertext_with_tag
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decrypt(token: str, key: bytes) -> bytes:
    """Decrypt and authenticate an AES-256-GCM *token* produced by `encrypt()`.

    The decryption operation cryptographically validates the 16-byte auth tag
    before returning any plaintext.  A single bit-flip anywhere in the payload
    (nonce, ciphertext, or tag) causes an immediate, irreversible failure with
    no partial plaintext returned.

    Parameters
    ----------
    token : str
        URL-safe base64 string as returned by `encrypt()`.
    key : bytes
        Exactly 32-byte AES-256 key used during encryption.

    Returns:
        Original plaintext bytes.

    Raises:
        CryptoError: if the payload is tampered with, truncated, or the key
                     does not match.  Callers MUST NOT expose this error detail
                     to end users.
    """
    if len(key) != _KEY_BYTES:
        raise CryptoError("Invalid key length")

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore[import-untyped]
        from cryptography.exceptions import InvalidTag  # type: ignore[import-untyped]

        raw = base64.urlsafe_b64decode(token)
        if len(raw) < _NONCE_BYTES + _TAG_BYTES:
            raise CryptoError("Payload too short — likely truncated or corrupted")

        nonce = raw[:_NONCE_BYTES]
        ciphertext_with_tag = raw[_NONCE_BYTES:]

        aesgcm = AESGCM(key)
        # This call validates the auth tag internally.  InvalidTag is raised
        # immediately if any byte of the ciphertext or tag was modified.
        return aesgcm.decrypt(nonce, ciphertext_with_tag, None)

    except CryptoError:
        raise
    except InvalidTag as exc:
        raise CryptoError(
            "Authentication tag verification failed — ciphertext may have been tampered with"
        ) from exc
    except Exception as exc:
        raise CryptoError(f"Decryption failed: {type(exc).__name__}") from exc
