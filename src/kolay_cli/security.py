"""Security and authentication for kolay-cli."""
from __future__ import annotations

import base64
import functools
import json
import logging
import os
from typing import Any, Callable, TypeVar
import contextvars

_log = logging.getLogger(__name__)

# Context variable to store request-specific token (for multi-tenant MCP)
KOLAY_TOKEN_CTX: contextvars.ContextVar[str | None] = contextvars.ContextVar("kolay_token", default=None)



_KEYRING_SERVICE = "kolay-cli"
_KEYRING_USERNAME = "api_token"



class TokenStatus:
    """Result of a token validation check."""

    def __init__(self, valid: bool, reason: str = "") -> None:
        self.valid = valid
        self.reason = reason

    def __bool__(self) -> bool:
        return self.valid

    def __repr__(self) -> str:
        return f"TokenStatus(valid={self.valid}, reason={self.reason!r})"




def _is_ci() -> bool:
    """Return True when running inside a CI environment."""
    return os.getenv("CI", "").lower() in ("true", "1", "yes")


def _try_configure_keyrings_alt() -> bool:
    """Attempt to activate keyrings.alt as a fallback backend on Linux."""
    import sys
    if sys.platform != "linux":
        return False
    try:
        import keyring
        import keyrings.alt.file  # noqa: F401
        from keyrings.alt.file import PlaintextKeyring
        keyring.set_keyring(PlaintextKeyring())
        _log.debug("keyrings.alt PlaintextKeyring activated as fallback backend")
        return True
    except ImportError:
        return False
    except Exception as exc:
        _log.debug("keyrings.alt activation failed: %s", exc)
        return False


def _keyring_backend_name() -> str:
    """Return a human-readable description of the active keyring backend."""
    try:
        import keyring
        backend = keyring.get_keyring()
        return type(backend).__name__
    except Exception:
        return "unknown"


def _keyring_available() -> bool:
    """Return True if a usable keyring backend is present.

    On Linux, if the native backend isn't available, automatically tries to
    activate ``keyrings.alt`` before giving up.
    """
    try:
        import keyring
        import keyring.errors
        backend = keyring.get_keyring()
        if "fail" not in type(backend).__name__.lower():
            return True
        # Native backend unavailable — try keyrings.alt on Linux
        return _try_configure_keyrings_alt()
    except Exception:
        return False


def store_token(token: str) -> bool:
    """Save API token to OS keychain."""
    try:
        import keyring
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, token)
        _log.debug("Token stored in OS keychain (%s)", _KEYRING_SERVICE)
        # If we successfully saved to keyring, remove it from any config file
        _remove_token_from_config_file()
        return True
    except Exception as exc:
        _log.warning("keyring unavailable — falling back to config file: %s", exc)
        return False


def get_keyring_token() -> str | None:
    """Retrieve the API token from the OS keychain.

    Returns:
        The stored token, or None if not found / keyring unavailable.
    """
    try:
        import keyring
        return keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
    except Exception:
        return None


def delete_token() -> bool:
    """Remove the API token from the OS keychain.

    Returns:
        True if deleted, False if not found or keyring unavailable.
    """
    try:
        import keyring
        import keyring.errors
        keyring.delete_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        _log.debug("Token removed from OS keychain")
        return True
    except Exception:
        return False


def _remove_token_from_config_file() -> None:
    """Remove the api_token key from the config file after migrating to keyring."""
    try:
        from .config import CONFIG_FILE_JSON, CONFIG_FILE_YAML, CONFIG_DIR
        import json as _json

        # Remove from YAML config if present
        try:
            import yaml
            if CONFIG_FILE_YAML.exists():
                with open(CONFIG_FILE_YAML, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if "api_token" in data:
                    del data["api_token"]
                    import os as _os
                    fd = _os.open(str(CONFIG_FILE_YAML), _os.O_WRONLY | _os.O_CREAT | _os.O_TRUNC, 0o600)
                    with _os.fdopen(fd, "w", encoding="utf-8") as f:
                        yaml.dump(data, f, default_flow_style=False)
                    _log.debug("Removed api_token from config YAML (migrated to keychain)")
        except ImportError:
            pass

        # Remove from JSON config if present
        if CONFIG_FILE_JSON.exists():
            with open(CONFIG_FILE_JSON, "r", encoding="utf-8") as f:
                data = _json.load(f)
            if "api_token" in data:
                del data["api_token"]
                import os as _os
                fd = _os.open(str(CONFIG_FILE_JSON), _os.O_WRONLY | _os.O_CREAT | _os.O_TRUNC, 0o600)
                with _os.fdopen(fd, "w", encoding="utf-8") as f:
                    _json.dump(data, f, indent=2)
                _log.debug("Removed api_token from config JSON (migrated to keychain)")
    except Exception as exc:
        _log.debug("Could not remove token from config file: %s", exc)




def is_first_run() -> bool:
    """Return True if CLI is not configured."""
    try:
        from .config import CONFIG_FILE_JSON, CONFIG_FILE_YAML
        if CONFIG_FILE_JSON.exists() or CONFIG_FILE_YAML.exists():
            return False
    except (OSError, ValueError) as exc:
        _log.warning("Could not verify run status due to file error: %s", exc)
    return resolve_token() is None


def resolve_token() -> str | None:
    """Resolve API token.

    Priority:
      0. Per-request ContextVar (multi-tenant MCP host)
      1. Environment variable KOLAY_API_TOKEN
      2. OS Keychain
      3. Legacy config file
    """
    # 0. Request context (multi-tenant MCP host)
    ctx_token = KOLAY_TOKEN_CTX.get()
    if ctx_token:
        _log.debug("Token resolved from request context header")
        return ctx_token

    # 1. Environment variable
    env_token = os.getenv("KOLAY_API_TOKEN")
    if env_token:
        _log.debug("Token resolved from environment variable")
        return env_token

    # 2. Keychain
    keyring_token = get_keyring_token()
    if keyring_token:
        _log.debug("Token resolved from OS keychain")
        return keyring_token

    # 3. Legacy config file — auto-migrate to keychain
    file_token = _get_token_from_config_file()
    if file_token:
        _log.debug("Token resolved from config file — migrating to OS keychain")
        migrated = store_token(file_token)
        if migrated:
            _migration_notice()
        return file_token

    return None


def resolve_token_with_source() -> tuple[str | None, str]:
    """Resolve token and identify its source."""
    if os.getenv("KOLAY_API_TOKEN"):
        return resolve_token(), "environment variable"
    keyring_token = get_keyring_token()
    if keyring_token:
        return keyring_token, "OS Keychain "
    file_token = _get_token_from_config_file()
    if file_token:
        return file_token, "config file"
    return None, "not configured"



def _get_token_from_config_file() -> str | None:
    """Read api_token directly from the config file (bypasses `Config` class)."""
    try:
        from .config import CONFIG_FILE_JSON, CONFIG_FILE_YAML
        import json as _json

        try:
            import yaml
            if CONFIG_FILE_YAML.exists():
                with open(CONFIG_FILE_YAML, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    return data.get("api_token")
        except (OSError, yaml.YAMLError) as exc:
            _log.warning("Failed reading YAML config file for token: %s", exc)

        if CONFIG_FILE_JSON.exists():
            with open(CONFIG_FILE_JSON, "r", encoding="utf-8") as f:
                return _json.load(f).get("api_token")
    except (OSError, _json.JSONDecodeError) as exc:
        _log.warning("Failed reading JSON config file for token: %s", exc)
    return None


_migration_noticed = False

def _migration_notice() -> None:
    """Print a one-time notice that the token was migrated."""
    global _migration_noticed
    if not _migration_noticed:
        _migration_noticed = True
        try:
            from rich.console import Console
            Console(highlight=False).print(
                " [grey62]Token migrated from config file to OS Keychain  "
                "(plaintext copy removed)[/grey62]"
            )
        except ImportError:
            pass
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("Failed to print migration notice: %s", exc)




# Seconds of leeway for clock skew.
_JWT_CLOCK_SKEW_SECONDS = 5


def _is_jwt(token: str) -> bool:
    """Return True if token is a structurally valid JWT."""
    parts = token.split(".")
    if len(parts) != 3:
        return False
    try:
        # Pad to a multiple of 4 for standard base64 decoding
        header_b64 = parts[0] + "=" * (-len(parts[0]) % 4)
        header_bytes = base64.urlsafe_b64decode(header_b64)
        # A real JWT header is always a JSON object
        return header_bytes.lstrip().startswith(b"{")
    except Exception:
        return False


def _decode_jwt_claims(token: str) -> dict[str, Any] | None:
    """Decode JWT claims without signature verification.

    Returns the payload dict, or None if decoding fails.
    """
    try:
        parts = token.split(".")
        # Pad base64 to a multiple-of-4 length
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return None


def validate_token(token: str) -> TokenStatus:
    """Validate token locally (JWT expiry or opaque acceptance)."""
    if not token or not token.strip():
        return TokenStatus(False, "Token is empty.")

    if not _is_jwt(token):
        # Opaque bearer token — trust it; API validates on each call
        return TokenStatus(True, "Opaque token (not a JWT) — accepted as-is.")

    # JWT path — decode without verifying signature
    claims = _decode_jwt_claims(token)
    if claims is None:
        return TokenStatus(False, "JWT payload could not be decoded.")

    # Check expiration (with clock-skew leeway)
    import time
    exp = claims.get("exp")
    if exp is not None:
        now = int(time.time())
        if now > exp + _JWT_CLOCK_SKEW_SECONDS:
            import datetime
            expired_at = datetime.datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M")
            return TokenStatus(False, f"JWT expired at {expired_at}. Run 'kolay auth login' to refresh.")
        # Warn if expiring in less than 5 minutes
        if exp - now < 300:
            _log.warning("Token expires in less than 5 minutes.")

    return TokenStatus(True, "JWT is valid.")




F = TypeVar("F", bound=Callable[..., Any])

_AUTH_ERROR_TEMPLATE = {
    "error": True,
    "code": 401,
}


def _auth_error(message: str, hint: str | None = None) -> dict[str, Any]:
    """Build a structured auth error response for MCP tool callers."""
    result: dict[str, Any] = {**_AUTH_ERROR_TEMPLATE, "message": message}
    if hint:
        result["hint"] = hint
    return result


def require_auth(fn: F) -> F:
    """Decorator that guards an MCP tool function with token authentication
    and activity logging. Rate limiting is handled by FastMCP middleware."""
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        import time as _time
        from .rate_limiter import token_key as rl_token_key
        from .activity_log import log_tool_call

        token = resolve_token()

        if not token:
            return _auth_error(
                "It seems we need a valid API token to proceed.",
                hint="Please run 'kolay auth login' or set the KOLAY_API_TOKEN environment variable to get started.",
            )

        status = validate_token(token)
        if not status:
            return _auth_error(
                f"We couldn't verify the current session: {status.reason}",
                hint="Please run 'kolay auth login' to refresh your connection.",
            )

        key = rl_token_key(token)

        # ── Execute tool with timing + activity logging ──
        t0 = _time.monotonic()
        try:
            result = fn(*args, **kwargs)
            log_tool_call(key, fn.__name__, kwargs, _time.monotonic() - t0, success=True)
            return result
        except Exception as exc:
            log_tool_call(key, fn.__name__, kwargs, _time.monotonic() - t0, success=False, error=str(exc))
            from .api.errors import APIError
            if isinstance(exc, APIError) and exc.status_code == 401:
                return _auth_error(
                    "It seems the API session has expired.",
                    hint="Please run 'kolay auth login' to update your connection.",
                )
            raise

    return wrapper  # type: ignore[return-value]

