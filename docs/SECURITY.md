# Security, Privacy, and Encryption

Kolay CLI and MCP Server are built with a **defense-in-depth** security architecture. We implement multiple independent layers of protection to ensure your HR data remains private, secure, and under your control.

---

## Security Architecture Overview

The system operates on a zero-trust model where data is sanitized, masked, and encrypted at every stage of its lifecycle.

```
                        AI Client (ChatGPT, Claude, Gemini, etc.)
                                        |
                                     HTTPS
                                        |
                    [Layer 1]  TLS / mTLS Transport Encryption
                                        |
                    [Layer 2]  Authentication (keychain / JWT)
                                        |
                    [Layer 3]  AI Circuit Breaker (loop detection)
                                        |
                    [Layer 4]  Rate Limiting (sliding window)
                                        |
                   =================== Core Logic ===================
                   |                                                |
            [Layer 5] Field Sanitizer         [Layer 6] Encrypted Cache
            (drop banned PII fields)          (AES-128-CBC + HMAC-SHA256)
                   |                                                |
            [Layer 7] PII Masking             [Layer 8] Tenant Isolation
            (pseudonymization)                (HMAC-SHA256 cache keys)
                   |                                                |
                   =================== Data Output ==================
                                        |
                    [Layer 9]  Egress DLP Scanner (last-mile redaction)
                                        |
                    [Layer 10] Payload Padding (anti-traffic analysis)
                                        |
                    [Layer 11] Activity Logging (audit trail)
                    [Layer 12] HMAC Execution Receipts
                                        |
                                  AI Client receives
                                  sanitized response
```

---

## 1. Local Data Security (CLI)

### Token Management
The CLI never stores tokens in plaintext if a secure vault is available.
- **macOS/Windows/Linux:** Tokens are stored in the system's native keychain (macOS Keychain, Windows Credential Vault, or GNOME Keyring).
- **Headless Fallback:** On servers without a GUI/keyring, `keyrings.alt` provides a file-backed fallback with restricted `0o600` permissions.

### Config Encryption at Rest
**Variable:** `KOLAY_ENCRYPT_CONFIG=true`
The configuration file can be encrypted using Fernet (AES-128-CBC + HMAC-SHA256). The key is derived on-the-fly from machine identity (hostname + username) using PBKDF2 with 600,000 iterations. It is never stored on disk.

---

## 2. Transport Security

### TLS 1.2+ (Standard)
All communication with the Kolay API and between MCP clients/servers is encrypted using TLS 1.2 or higher.

### Mutual TLS (mTLS)
For networked deployments, you can enforce Mutual TLS using an NGINX sidecar. This requires clients to present a valid X.509 certificate signed by your private Certificate Authority before a connection is established.

---

## 3. Data Privacy and Masking

### Field Sanitizer (Whitelist Only)
A strict whitelist filter drops all non-essential fields before data hits the cache or the LLM. Fields like salary, IBAN, SSN, and home addresses are ruthlessly removed at the entry point.

### PII Masking and Pseudonymization
**Variable:** `MCP_PII_MASKING_ENABLED=true`
Names and emails are replaced with deterministic pseudonyms (e.g., `EMP-8F92`). This allows LLMs to correlate identities within a session without seeing real personal data. Masking is salted with a session-specific random 32-byte key.

### Egress DLP Scanner
**Variable:** `MCP_DLP_ENABLED=true`
A last-mile safety layer scans the final JSON payload for sensitive patterns (TC Kimlik, IBAN, Credit Cards) and redacts them if they escaped previous filters.

---

## 4. Infrastructure Protection

### AI Circuit Breaker
**Variable:** `MCP_CIRCUIT_BREAKER_ENABLED=true`
Protects against infinite tool-calling loops. If an autonomous agent calls the same tool too many times in a short window, the circuit breaks and forces the agent to yield to a human.

### Rate Limiting
**Variable:** `MCP_RATE_LIMIT_ENABLED=true`
A sliding-window rate limiter prevents API abuse, keyed by a privacy-safe hash of the user's token.

### Encrypted In-Memory Cache
Data cached in memory is stored as ciphertext using an ephemeral AES key that exists only in RAM. If the process crashes or exits, the key is lost and the cached data becomes permanently unreadable (crypto-shredding).

---

## 5. Audit and Verifiability

### Structured Activity Logging
The server logs tool invocations as JSON objects to stdout. To protect privacy:
- Full tokens are never logged (only 8-character suffixes).
- Response payloads are never logged.
- Arguments are truncated and redacted if they exceed 64 characters.

### HMAC Execution Receipts
**Variable:** `MCP_RECEIPT_SECRET=<secret>`
Every tool execution can generate a tamper-proof receipt signed with HMAC-SHA256, allowing for verifiable audit trails.

### API Manifest Verification
The server provides a JWS-signed `mcp-manifest.json` allowing independent agents to verify server identity and security capabilities.

---

## Security Environment Variable Reference

| Variable | Default | Description |
|---|---|---|
| `KOLAY_ENCRYPT_CONFIG` | `false` | Enable encryption for local config files |
| `MCP_PII_MASKING_ENABLED` | `false` | Enable PII pseudonymization |
| `MCP_DLP_ENABLED` | `true` | Enable last-mile DLP redaction |
| `MCP_PAYLOAD_PADDING` | `false` | Enable padding against traffic analysis |
| `MCP_RATE_LIMIT_ENABLED` | `false` | Enable per-token rate limiting |
| `MCP_CIRCUIT_BREAKER_ENABLED` | `true` | Enable AI loop protection |
| `MCP_JWT_SECRET` | -- | Secret for cryptographic JWT verification |
| `MCP_RECEIPT_SECRET` | -- | Secret for HMAC execution receipts |
