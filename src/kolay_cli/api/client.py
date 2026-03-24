from __future__ import annotations
import logging
import re
import requests
from typing import Any
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

from .. import config
from .errors import APIError, HTTP_ERRORS

import os
import platform
import sys
try:
    from importlib.metadata import version, PackageNotFoundError
    __version__ = version("kolay-cli")
except (ImportError, PackageNotFoundError):
    __version__ = "unknown"

# IDs are 32-char hex. Accept hex + basic alphanum.
_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
_log = logging.getLogger("kolay.api")
_BEARER_RE = re.compile(r"(Bearer\s+)\S+", re.IGNORECASE)




def _redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Redact authorization headers for safe logging."""
    redacted = dict(headers)
    for k, v in redacted.items():
        if k.lower() == "authorization":
            redacted[k] = _BEARER_RE.sub(r"\1[REDACTED]", v)
    return redacted


def safe_id(value: str, label: str = "ID") -> str:
    """Validate a user-supplied ID before URL interpolation."""
    if not value or not value.strip():
        raise APIError(f"{label} cannot be empty.")
    value = value.strip()
    if not _SAFE_ID_RE.match(value):
        raise APIError(f"Invalid {label}: contains illegal characters.")
    return value


class KolayClient:
    """HTTP client for Kolay IK API."""

    # Class-level debug flag — set by the --debug CLI option at startup
    debug: bool = False

    def __init__(self, token: str | None = None, base_url: str | None = None) -> None:
        """Initialize the API client."""
        self._token = token or config.get_api_token()
        self.base_url = (base_url or config.get_base_url()).rstrip("/")

        if not self._token:
            # Detect first-run (no config file at all) for a friendlier onboarding hint
            from ..security import is_first_run
            if is_first_run():
                raise APIError(
                    "Kolay CLI is not set up yet.",
                    status_code=401,
                    hint="Run [bold]kolay setup[/bold] to authenticate and configure the CLI in one step.",
                )
            raise APIError(
                "No API token found.",
                status_code=401,
                hint="Run [bold]kolay auth login[/bold] or set the KOLAY_API_TOKEN env variable.",
            )

        if not self.base_url.startswith("https://"):
            raise APIError(
                "Base URL must use HTTPS.",
                hint="Check your KOLAY_BASE_URL setting in ~/.config/kolay/config.yaml",
            )

        self.session = requests.Session()

        # 3 retries with exponential backoff on transient errors.
        # respect_retry_after=True honours the Retry-After header on 429s
        # so we back off exactly as long as the API asks, not longer.
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            backoff_max=60,
            respect_retry_after_header=True,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

        user_agent = f"kolay-cli/{__version__} (Python/{sys.version.split()[0]}; {platform.system()})"
        self.session.headers.update({
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Language": "en",
            "User-Agent": user_agent,
        })

    def __repr__(self) -> str:
        """Safe repr — never exposes the bearer token."""
        return f"KolayClient(base_url={self.base_url!r})"

    def __str__(self) -> str:
        return self.__repr__()

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a GET request."""
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a POST request with JSON body."""
        return self._request("POST", endpoint, json=data)

    def put(self, endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a PUT request with JSON body."""
        return self._request("PUT", endpoint, json=data)

    def delete(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a DELETE request."""
        return self._request("DELETE", endpoint, params=params)



    def _log_audit_trail(self, method: str, endpoint: str, status: int) -> None:
        """Append write operations to local audit.log."""
        import json, datetime, os
        from pathlib import Path
        try:
            home = Path("~").expanduser() / ".config" / "kolay"
            home.mkdir(parents=True, exist_ok=True)
            try:
                home.chmod(0o700)
            except OSError:
                pass
            
            audit_file = home / "audit.log"
            entry = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()[:19] + "Z",
                "method": method,
                "endpoint": endpoint,
                "status": status,
            }
            log_line = json.dumps(entry) + "\n"
            
            from ..config_crypto import is_encryption_enabled, encrypt_bytes
            encrypt = is_encryption_enabled()
            
            # O_APPEND guarantees atomic append at the end of the file
            fd = os.open(str(audit_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            mode = "ab" if encrypt else "a"
            encoding = None if encrypt else "utf-8"
            
            with os.fdopen(fd, mode, encoding=encoding) as f:
                if encrypt:
                    f.write(encrypt_bytes(log_line.encode("utf-8")) + b"\n")
                else:
                    f.write(log_line)
        except Exception:
            pass

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Execute an API request with error handling and optional debug logging."""
        if ".." in endpoint or endpoint.startswith("/") or "://" in endpoint:
            raise APIError("Invalid API endpoint.")

        url = f"{self.base_url}/{endpoint}"

        if method.upper() == "POST":
            import hashlib, time
            window = int(time.time() // 120)  # 2-minute deduplication window
            payload = str(kwargs.get("json", {})) + str(kwargs.get("data", {}))
            idx = hashlib.md5(f"{endpoint}:{payload}:{window}".encode()).hexdigest()
            headers = kwargs.setdefault("headers", {})
            if "Idempotency-Key" not in headers:
                headers["Idempotency-Key"] = f"kolay-cli-{idx}"

        if self.debug:
            safe_hdrs = _redact_headers(dict(self.session.headers))
            _log.debug(
                "%s %s  headers=%s  params/body=%s",
                method, url, safe_hdrs,
                kwargs.get("params") or kwargs.get("json"),
            )

        try:
            response = self.session.request(method, url, timeout=30, **kwargs)

            if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
                self._log_audit_trail(method.upper(), endpoint, response.status_code)

            if self.debug:
                _log.debug("%d  %s", response.status_code, response.text[:500])

            response.raise_for_status()
            return response.json() if response.content else {}

        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0

            # Try to extract the API's specific message
            api_msg: str | None = None
            try:
                body = exc.response.json()
                api_msg = body.get("message") or body.get("error")
            except (ValueError, KeyError, AttributeError):
                pass

            if self.debug:
                _log.debug("HTTP error %d — %s", status, api_msg)

            # For 400/422 prefer the API's own validation message
            if status in (400, 422) and api_msg:
                raise APIError(api_msg, status_code=status)

            # Map to friendly message + recovery hint
            entry = HTTP_ERRORS.get(status)
            if entry:
                msg, hint = entry
                raise APIError(api_msg or msg, status_code=status, hint=hint)

            raise APIError(
                api_msg or f"Unexpected error (HTTP {status}).",
                status_code=status,
            )

        except requests.exceptions.ConnectionError:
            raise APIError(
                "Could not connect to the Kolay API.",
                hint="Check your internet connection and try again.",
            )
        except requests.exceptions.Timeout:
            raise APIError(
                "The request timed out.",
                hint="The API might be under load — try again in a moment.",
            )
        except APIError:
            raise
        except Exception as exc:
            raise APIError(f"Unexpected error: {exc}")
