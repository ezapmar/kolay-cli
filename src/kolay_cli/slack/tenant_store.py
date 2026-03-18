"""SQLite-backed tenant registry with Fernet encryption for stored tokens."""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Encryption helpers ────────────────────────────────────────────────────────

def _get_fernet():  # type: ignore[no-untyped-def]
    """Return a Fernet instance using TENANT_ENCRYPTION_KEY env var."""
    from cryptography.fernet import Fernet

    key = os.environ.get("TENANT_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "TENANT_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def _encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def _decrypt(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


# ── Tenant dataclass ──────────────────────────────────────────────────────────

@dataclass
class Tenant:
    team_id: str              # Slack workspace ID (e.g. T0123ABC)
    team_name: str            # Slack workspace name
    kolay_api_token: str      # Company's Kolay API token (stored encrypted)
    slack_bot_token: str      # Workspace-specific bot token (stored encrypted)
    allowed_channels: str = ""    # comma-separated channel IDs, empty = all
    allowed_users: str = ""       # comma-separated user IDs, empty = all
    installed_at: str = ""        # ISO 8601 timestamp


# ── Store ─────────────────────────────────────────────────────────────────────

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tenants (
    team_id          TEXT PRIMARY KEY,
    team_name        TEXT NOT NULL,
    kolay_api_token  TEXT NOT NULL,
    slack_bot_token  TEXT NOT NULL,
    allowed_channels TEXT DEFAULT '',
    allowed_users    TEXT DEFAULT '',
    installed_at     TEXT NOT NULL
);
"""

_COLUMNS = (
    "team_id", "team_name", "kolay_api_token", "slack_bot_token",
    "allowed_channels", "allowed_users", "installed_at",
)


class TenantStore:
    """Thread-safe SQLite tenant registry.

    Tokens are encrypted at rest using Fernet (AES-128-CBC).
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = str(db_path or os.environ.get("TENANT_DB_PATH", "tenants.db"))
        self._ensure_table()

    # ── internal ──────────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_table(self) -> None:
        with self._conn() as conn:
            conn.execute(_CREATE_TABLE)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def upsert(self, tenant: Tenant) -> None:
        """Insert or replace a tenant. Encrypts tokens before storage."""
        now = tenant.installed_at or datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO tenants (team_id, team_name, kolay_api_token, slack_bot_token,
                                     allowed_channels, allowed_users, installed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(team_id) DO UPDATE SET
                    team_name = excluded.team_name,
                    kolay_api_token = excluded.kolay_api_token,
                    slack_bot_token = excluded.slack_bot_token,
                    allowed_channels = excluded.allowed_channels,
                    allowed_users = excluded.allowed_users
                """,
                (
                    tenant.team_id,
                    tenant.team_name,
                    _encrypt(tenant.kolay_api_token),
                    _encrypt(tenant.slack_bot_token),
                    tenant.allowed_channels,
                    tenant.allowed_users,
                    now,
                ),
            )

    def find(self, team_id: str) -> Tenant | None:
        """Look up a tenant by Slack team ID. Decrypts tokens on read."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM tenants WHERE team_id = ?", (team_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_tenant(row)

    def delete(self, team_id: str) -> bool:
        """Remove a tenant. Returns True if a row was deleted."""
        with self._conn() as conn:
            cursor = conn.execute("DELETE FROM tenants WHERE team_id = ?", (team_id,))
            return cursor.rowcount > 0

    def list_all(self) -> list[Tenant]:
        """Return all tenants (tokens decrypted)."""
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM tenants ORDER BY installed_at DESC").fetchall()
        return [self._row_to_tenant(r) for r in rows]

    def count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_tenant(row: tuple) -> Tenant:
        return Tenant(
            team_id=row[0],
            team_name=row[1],
            kolay_api_token=_decrypt(row[2]),
            slack_bot_token=_decrypt(row[3]),
            allowed_channels=row[4],
            allowed_users=row[5],
            installed_at=row[6],
        )
