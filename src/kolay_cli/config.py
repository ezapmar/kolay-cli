from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

# Token resolution is delegated to security.py which holds the keyring logic.
# We import lazily to avoid circular imports at module load time.

CONFIG_DIR = Path.home() / ".config" / "kolay"
CONFIG_FILE_JSON = CONFIG_DIR / "config.json"
CONFIG_FILE_YAML = CONFIG_DIR / "config.yaml"


class Config:
    """Centralized configuration manager for kolay-cli.

    Handles values from environment variables, YAML config, or JSON config.
    Falls back to JSON-only when PyYAML is not installed.
    """

    def __init__(self) -> None:
        """Initialize and load current configuration."""
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        """Load configuration from files, preferring YAML over JSON.

        Transparently decrypts files that were encrypted at rest
        by :mod:`config_crypto` (detected by Fernet prefix).
        """
        from .config_crypto import decrypt_config_file
        data: dict[str, Any] = {}

        # 1. Load JSON if it exists
        if CONFIG_FILE_JSON.exists():
            try:
                raw = decrypt_config_file(CONFIG_FILE_JSON)
                if raw:
                    data.update(json.loads(raw))
            except (json.JSONDecodeError, OSError):
                pass

        # 2. Load YAML if it exists and PyYAML is available (takes precedence)
        if _HAS_YAML and CONFIG_FILE_YAML.exists():
            try:
                raw = decrypt_config_file(CONFIG_FILE_YAML)
                if raw:
                    yaml_data = yaml.safe_load(raw)
                    if isinstance(yaml_data, dict):
                        data.update(yaml_data)
            except (yaml.YAMLError, OSError):
                pass

        return data

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with environment variable precedence.

        For ``api_token`` specifically, the full resolution chain (env 
        keyring config file) is handled by :func:`get_api_token` below.
        All other keys use env config file.

        Args:
            key: The configuration key (e.g., 'api_token').
            default: Value to return if key is not found anywhere.

        Returns:
            The configuration value.
        """
        # Environment variables take highest precedence (KOLAY_API_TOKEN etc.)
        env_val = os.getenv(f"KOLAY_{key.upper()}")
        if env_val is not None:
            return env_val

        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and persist to disk.

        For ``api_token``: saves to the OS keychain via :mod:`security`
        (the plaintext copy is removed from the config file).  Falls back to
        the config file when keyring is unavailable.

        For all other keys: saves to YAML / JSON config file as before.

        Args:
            key: The configuration key.
            value: The value to set.
        """
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        if key == "api_token":
            # Prefer keyring; fall back to file only when keyring unavailable
            from .security import store_token
            if store_token(str(value)):
                # Keyring accepted it — no need to write to file
                # (store_token already stripped it from the config file)
                return
            # Keyring unavailable — fall through to file storage below

        self._data[key] = value

        from .config_crypto import encrypt_and_write
        if _HAS_YAML:
            encrypt_and_write(CONFIG_FILE_YAML, self._data, use_yaml=True)
        else:
            encrypt_and_write(CONFIG_FILE_JSON, self._data, use_yaml=False)

    @property
    def api_token(self) -> str | None:
        """The API token — resolved via env keyring config file."""
        from .security import resolve_token
        return resolve_token()

    @property
    def base_url(self) -> str:
        """The Kolay API base URL."""
        url = self.get("base_url") or "https://api.kolayik.com"
        # Basic validation
        if not url.startswith("https://"):
            # We don't raise here to allow the client to catch it or the user to fix it
            pass
        return str(url)


# Global instance for easy access
_config_instance = Config()


def get_api_token() -> str | None:
    """Resolve the API token via env keyring config file."""
    from .security import resolve_token
    return resolve_token()


def get_base_url() -> str:
    """Shortcut to get the base URL."""
    return _config_instance.base_url


def set_config_value(key: str, value: Any) -> None:
    """Shortcut to set a configuration value."""
    _config_instance.set(key, value)


def get_config_value(key: str, default: Any = None) -> Any:
    """Shortcut to get any configuration value."""
    return _config_instance.get(key, default)
