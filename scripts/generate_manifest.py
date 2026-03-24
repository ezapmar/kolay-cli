#!/usr/bin/env python3
"""Generate a Verifiable API Manifest for the Kolay IK MCP Server.

Creates an ECDSA-signed JSON Web Signature (JWS) containing our server
identity, tool catalogue, and data policies.  External autonomous
'Buyer Agents' can verify this manifest cryptographically before
connecting.

Usage:
    python -m scripts.generate_manifest

Outputs:
    mcp-manifest.json       – the unsigned manifest payload
    mcp-manifest.jws        – JWS compact serialization (signed)
    manifest-public-key.pem – ECDSA P-256 public key for verification

Dependencies:
    cryptography  (transitive dep of PyJWT, already in the project)
"""
from __future__ import annotations

import base64
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _b64url(data: bytes) -> str:
    """Base64url encode without padding (per RFC 7515)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_manifest() -> dict:
    """Build the API manifest payload."""
    return {
        "schema_version": "1.0",
        "server": {
            "name": "kolay-ik",
            "display_name": "Kolay IK MCP Server",
            "version": "0.13.0a3",
            "vendor": "Kolay IK (https://kolayik.com)",
            "description": "HR platform tools for employee, leave, payroll, and analytics management.",
        },
        "transport": {
            "protocol": "mcp",
            "endpoints": ["/mcp"],
            "auth_methods": ["bearer_token", "x-api-key"],
        },
        "tools": [
            {"name": "search_employees", "category": "read", "description": "Filtered, projected employee search with hard-limit truncation."},
            {"name": "get_employee_statistics", "category": "read", "description": "Server-side aggregations (headcount, average_age, distributions)."},
            {"name": "get_cache_status", "category": "diagnostic", "description": "TTL cache health check."},
            {"name": "person_list", "category": "read", "description": "Raw paginated employee listing."},
            {"name": "person_view", "category": "read", "description": "Full employee profile by ID."},
            {"name": "leave_list", "category": "read", "description": "Leave records with filters."},
            {"name": "team_availability_analysis", "category": "analytics", "description": "Multi-step operational risk assessment."},
            {"name": "turnover_risk_scan", "category": "analytics", "description": "Burnout and turnover signal scan."},
            {"name": "payroll_anomaly_detect", "category": "analytics", "description": "Duplicate and outlier transaction detection."},
        ],
        "data_policies": {
            "no_llm_training": True,
            "pii_masking_available": True,
            "max_response_size_bytes": 500_000,
            "rate_limiting": "sliding_window_per_token",
            "audit_logging": "structured_json_stdout",
            "data_retention": "none_stateless_proxy",
        },
        "issued_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def sign_manifest(manifest: dict) -> tuple[str, bytes, bytes]:
    """Sign the manifest with ECDSA P-256 and return (jws, private_pem, public_pem)."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
    except ImportError:
        print("ERROR: 'cryptography' package required. Install with: pip install cryptography", file=sys.stderr)
        sys.exit(1)

    # Generate ephemeral key pair
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Serialize keys
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # JWS header
    header = {"alg": "ES256", "typ": "JWT"}
    header_b64 = _b64url(json.dumps(header).encode())
    payload_b64 = _b64url(json.dumps(manifest, indent=2).encode())

    # Sign
    signing_input = f"{header_b64}.{payload_b64}".encode()
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    der_sig = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der_sig)

    # Convert to fixed-size r||s format (per RFC 7518 Section 3.4)
    sig_bytes = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    sig_b64 = _b64url(sig_bytes)

    jws = f"{header_b64}.{payload_b64}.{sig_b64}"
    return jws, private_pem, public_pem


def verify_manifest(jws: str, public_pem: bytes) -> bool:
    """Mock 'Buyer Agent' -- verify the JWS signature.

    5 lines of verification logic as specified.
    """
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

    parts = jws.split(".")
    signing_input = f"{parts[0]}.{parts[1]}".encode()
    sig_padded = parts[2] + "=" * (-len(parts[2]) % 4)
    sig_bytes = base64.urlsafe_b64decode(sig_padded)
    r, s = int.from_bytes(sig_bytes[:32], "big"), int.from_bytes(sig_bytes[32:], "big")
    der_sig = encode_dss_signature(r, s)
    pub_key = serialization.load_pem_public_key(public_pem)
    try:
        pub_key.verify(der_sig, signing_input, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


def main() -> None:
    """Generate, sign, and verify the manifest."""
    output_dir = Path(__file__).resolve().parent.parent
    scripts_dir = Path(__file__).resolve().parent

    # 1. Generate
    manifest = generate_manifest()
    manifest_path = output_dir / "mcp-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"  Manifest written to {manifest_path}")

    # 2. Sign
    jws, _priv_pem, pub_pem = sign_manifest(manifest)
    jws_path = output_dir / "mcp-manifest.jws"
    jws_path.write_text(jws + "\n")
    print(f"  JWS written to {jws_path}")

    pub_path = output_dir / "manifest-public-key.pem"
    pub_path.write_bytes(pub_pem)
    print(f"  Public key written to {pub_path}")

    # 3. Verify (mock Buyer Agent)
    verified = verify_manifest(jws, pub_pem)
    if verified:
        print("  Success: Manifest Verified")
    else:
        print("  FAILURE: Manifest signature verification failed!", file=sys.stderr)
        sys.exit(1)

    # 4. Tamper test
    tampered = jws[:10] + "TAMPERED" + jws[18:]
    tampered_ok = verify_manifest(tampered, pub_pem)
    if not tampered_ok:
        print("  Success: Tampered manifest correctly rejected")
    else:
        print("  FAILURE: Tampered manifest was incorrectly accepted!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
