"""Tests for the tenant store — CRUD, encryption, and edge cases."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Generate a Fernet key for tests
from cryptography.fernet import Fernet

_TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    monkeypatch.setenv("TENANT_ENCRYPTION_KEY", _TEST_KEY)


@pytest.fixture
def store(tmp_path):
    from kolay_cli.slack.tenant_store import TenantStore
    return TenantStore(db_path=tmp_path / "test_tenants.db")


@pytest.fixture
def sample_tenant():
    from kolay_cli.slack.tenant_store import Tenant
    return Tenant(
        team_id="T_TEST_001",
        team_name="Acme Corp",
        kolay_api_token="kolay-secret-token-abc123",
        slack_bot_token="xoxb-test-bot-token-xyz",
        allowed_channels="C001,C002",
        allowed_users="U001,U002",
    )


# ── CRUD tests ────────────────────────────────────────────────────────────────

def test_upsert_and_find(store, sample_tenant):
    store.upsert(sample_tenant)
    found = store.find("T_TEST_001")
    assert found is not None
    assert found.team_id == "T_TEST_001"
    assert found.team_name == "Acme Corp"
    assert found.kolay_api_token == "kolay-secret-token-abc123"
    assert found.slack_bot_token == "xoxb-test-bot-token-xyz"
    assert found.allowed_channels == "C001,C002"
    assert found.allowed_users == "U001,U002"
    assert found.installed_at  # has a timestamp


def test_find_nonexistent(store):
    assert store.find("T_NONEXISTENT") is None


def test_upsert_updates_existing(store, sample_tenant):
    store.upsert(sample_tenant)

    from kolay_cli.slack.tenant_store import Tenant
    updated = Tenant(
        team_id="T_TEST_001",
        team_name="Acme Corp (Renamed)",
        kolay_api_token="new-kolay-token",
        slack_bot_token="new-bot-token",
        allowed_channels="C999",
        allowed_users="",
    )
    store.upsert(updated)

    found = store.find("T_TEST_001")
    assert found.team_name == "Acme Corp (Renamed)"
    assert found.kolay_api_token == "new-kolay-token"
    assert found.slack_bot_token == "new-bot-token"
    assert found.allowed_channels == "C999"
    assert found.allowed_users == ""
    assert store.count() == 1  # no duplicate


def test_delete(store, sample_tenant):
    store.upsert(sample_tenant)
    assert store.delete("T_TEST_001") is True
    assert store.find("T_TEST_001") is None
    assert store.count() == 0


def test_delete_nonexistent(store):
    assert store.delete("T_GHOST") is False


def test_list_all(store):
    from kolay_cli.slack.tenant_store import Tenant
    for i in range(3):
        store.upsert(Tenant(
            team_id=f"T_{i}",
            team_name=f"Company {i}",
            kolay_api_token=f"token_{i}",
            slack_bot_token=f"bot_{i}",
        ))
    tenants = store.list_all()
    assert len(tenants) == 3
    # All have decrypted tokens
    assert tenants[0].kolay_api_token.startswith("token_")


def test_count(store, sample_tenant):
    assert store.count() == 0
    store.upsert(sample_tenant)
    assert store.count() == 1


# ── Encryption tests ──────────────────────────────────────────────────────────

def test_tokens_encrypted_at_rest(store, sample_tenant, tmp_path):
    """Verify the raw SQLite DB does NOT contain plaintext tokens."""
    store.upsert(sample_tenant)

    import sqlite3
    conn = sqlite3.connect(str(tmp_path / "test_tenants.db"))
    row = conn.execute("SELECT kolay_api_token, slack_bot_token FROM tenants WHERE team_id = 'T_TEST_001'").fetchone()
    conn.close()

    raw_kolay = row[0]
    raw_bot = row[1]

    # Raw values should NOT be the plaintext tokens
    assert raw_kolay != "kolay-secret-token-abc123"
    assert raw_bot != "xoxb-test-bot-token-xyz"

    # But decrypting them should give the original
    found = store.find("T_TEST_001")
    assert found.kolay_api_token == "kolay-secret-token-abc123"
    assert found.slack_bot_token == "xoxb-test-bot-token-xyz"


def test_encryption_key_required(monkeypatch, tmp_path):
    """Without TENANT_ENCRYPTION_KEY, store operations should fail."""
    monkeypatch.delenv("TENANT_ENCRYPTION_KEY", raising=False)

    from kolay_cli.slack.tenant_store import Tenant, TenantStore
    s = TenantStore(db_path=tmp_path / "nokey.db")

    with pytest.raises(RuntimeError, match="TENANT_ENCRYPTION_KEY"):
        s.upsert(Tenant(
            team_id="T_X",
            team_name="X",
            kolay_api_token="secret",
            slack_bot_token="bot",
        ))


# ── Middleware integration test ───────────────────────────────────────────────

def test_middleware_sets_context(store, sample_tenant, monkeypatch):
    """Verify the middleware injects the correct token into KOLAY_TOKEN_CTX."""
    from kolay_cli.slack.middleware import tenant_middleware, set_store
    from kolay_cli.security import KOLAY_TOKEN_CTX

    store.upsert(sample_tenant)
    set_store(store)

    captured_token = None

    def fake_next():
        nonlocal captured_token
        captured_token = KOLAY_TOKEN_CTX.get()

    body = {"team_id": "T_TEST_001", "channel_id": "C001", "user_id": "U001"}
    tenant_middleware(payload={}, body=body, next=fake_next)

    assert captured_token == "kolay-secret-token-abc123"
    # After middleware exits, context should be reset
    assert KOLAY_TOKEN_CTX.get() is None


def test_middleware_unknown_team(store, monkeypatch):
    """Unknown team_id should NOT call next() — blocks the request."""
    from kolay_cli.slack.middleware import tenant_middleware, set_store
    from unittest.mock import MagicMock

    set_store(store)
    called = False

    def fake_next():
        nonlocal called
        called = True

    client = MagicMock()
    body = {"team_id": "T_UNKNOWN", "channel_id": "C001", "user_id": "U001"}
    tenant_middleware(payload={}, body=body, next=fake_next, client=client)

    assert not called  # next() was never invoked
    client.chat_postEphemeral.assert_called_once()
