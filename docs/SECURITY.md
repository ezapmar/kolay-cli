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
The configuration file can be encrypted using AES-256-GCM (Galois/Counter Mode). The 32-byte key is derived on-the-fly from machine identity (hostname + username) using PBKDF2 with 600,000 iterations and a cryptographically secure random salt generated per write. It ensures both confidentiality and cryptographic integrity mathematically, without needing a separate HMAC layer. The key is never stored on disk.

---

## 2. Transport Security

### TLS 1.2+ (Standard)
All communication with the Kolay API and between MCP clients/servers is encrypted using TLS 1.2 or higher.

### Mutual TLS (mTLS)
For networked deployments, you can enforce Mutual TLS using an NGINX sidecar. This requires clients to present a valid X.509 certificate signed by your private Certificate Authority before a connection is established.

### Payload Padding (Anti-Traffic Analysis)
**Variable:** `MCP_PAYLOAD_PADDING=false`
To protect against side-channel network attacks where eavesdroppers might deduce the nature of HR responses based solely on encrypted packet sizes (e.g., guessing an action was "denied" because the packet is only 100 bytes), the server can inject randomized, cryptographically secure decoy bytes (padding) into the JSON payload before TLS encryption. This homogenizes response sizes across different endpoints.

---

## 3. Data Privacy and Masking

### Field Sanitizer (Whitelist Only)
A strict whitelist filter drops all non-essential fields before data hits the cache or the LLM. Fields like salary, IBAN, SSN, and home addresses are ruthlessly removed at the entry point.

### PII Masking and Pseudonymization
**Variable:** `MCP_PII_MASKING_ENABLED=true`
Names and emails are replaced with deterministic pseudonyms (e.g., `EMP-8F92`). This allows LLMs to correlate identities within a session without seeing real personal data. Masking is salted with a session-specific random 32-byte key.

### Layer 15: Egress DLP Scanner
Standalone `DLPScannerMiddleware` scans the final tool response strings for Turkish TC Kimlik numbers and sensitive IBAN patterns. Hits are replaced with redacted labels (e.g., `[REDACTED_TC]`). This prevents data exfiltration even if an upstream API or LLM attempt to leak internal IDs.

### K-Anonymity (Anti-Inference Protection)
To prevent targeted inference attacks—where an AI agent queries aggregated HR data for a highly specific demographic that resolves to a single individual (e.g., "average salary of 34-year-old female developers")—all statistical tools enforce a strict K-Anonymity policy. Any AI query resulting in a cohort of fewer than the defined threshold (e.g., `< 3 employees`) is automatically rejected with an `HTTP 451 Privacy Violation` error. This mathematically guarantees that an LLM cannot reverse-engineer a specific employee's private data.

### Just-In-Time (JIT) Tool Provisioning (RBAC)
The Kolay MCP Server adheres to the Principle of Least Privilege for tool visibility. Instead of declaring all available tools to every connected LLM, the server dynamically filters the tool schemas based on the verified user's RBAC profile (JWT/Keychain claims). Standard employees are never made aware of administrative tools (e.g., `update_salary`), physically eliminating the attack surface for prompt injection aimed at privilege escalation and significantly reducing token context bloat.

### Layer 17: Semantic Result Cache
Lightweight in-memory cache for computed analytical aggregates. Keyed by `HMAC-SHA256(tenant_id:tool_name:args)`. Returns pre-calculated results in O(1) for redundant queries, significantly reducing CPU usage for expensive metrics like turnover risk or burnout scores.

### Layer 18: Webhook-Driven Invalidation
Event-driven cache management. An HMAC-SHA256 signed endpoint at `/webhooks/cache-invalidate` allow the core Kolay IK API to trigger immediate purges of cached data upon mutation. This eliminates "stale data" windows and unnecessary periodic polling.
- Signature: `x-kolayik-signature` checked against `WEBHOOK_SECRET`.
- Scope: Per-tenant invalidation of both raw and semantic caches.

---

## 4. Infrastructure Protection

### AI Circuit Breaker
**Variable:** `MCP_CIRCUIT_BREAKER_ENABLED=true`
Protects against infinite tool-calling loops. If an autonomous agent calls the same tool too many times in a short window, the circuit breaks and forces the agent to yield to a human.

### Rate Limiting
**Variable:** `MCP_RATE_LIMIT_ENABLED=true`
A sliding-window rate limiter prevents API abuse, keyed by a privacy-safe hash of the user's token.

### Encrypted In-Memory Cache
Data cached in memory is stored as ciphertext using AES-256-GCM. A completely random 32-byte (256-bit) ephemeral key is generated on server startup using the OS's cryptographically secure pseudo-random number generator (CSPRNG). A unique 12-byte nonce is generated for every operation, and a 16-byte Auth Tag strictly validates cryptographic integrity on decryption. If the process crashes or exits, the key is lost and the cached data becomes permanently unreadable (crypto-shredding).

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
