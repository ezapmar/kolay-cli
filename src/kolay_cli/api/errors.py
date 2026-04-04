from __future__ import annotations



HTTP_ERRORS: dict[int, tuple[str, str]] = {
    400: (
        "It looks like some of the details provided weren't quite right.",
        "Please double-check your inputs or run with [bold]--help[/bold] to see the available options.",
    ),
    401: (
        "It seems we need a fresh login to continue.",
        "Please run [bold]kolay auth login[/bold] to securely connect your session.",
    ),
    403: (
        "It seems this resource requires additional permissions.",
        "Please check with your Kolay admin to help update your access role.",
    ),
    404: (
        "We couldn't quite find the resource you're looking for.",
        "You might find it helpful to use the interactive picker to select the correct ID.",
    ),
    422: (
        "It looks like some required information is missing or formatted differently.",
        "You can find the required fields by running the command with the [bold]--help[/bold] flag.",
    ),
    429: (
        "It looks like we're sending requests a bit too fast to the API.",
        "Please wait a moment, then we can try again.",
    ),
    500: (
        "The Kolay API encountered an unexpected hiccup on their end.",
        "Please give it a minute, and we can try your request again.",
    ),
    502: (
        "We experienced a small connection interruption with the Kolay API.",
        "It might be a temporary update. Let's try again in about 30 seconds.",
    ),
    503: (
        "The Kolay API is taking a brief pause and is currently unavailable.",
        "It should be back up shortly! Let's try again in a little bit.",
    ),
    504: (
        "It took a bit too long for the API to process our request.",
        "Let's try again in a moment to see if it goes through.",
    ),
}


class APIError(Exception):
    """Base exception for Kolay API errors."""

    EXIT_CODES: dict[int, int] = {
        400: 2,
        401: 4,
        403: 4,
        404: 3,
        409: 5,
        422: 2,
        429: 1,
        500: 1,
        502: 1,
        503: 1,
        504: 1,
    }

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        hint: str | None = None,
        raw_response: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.raw_response = raw_response

        # Auto-generate hint from HTTP_ERRORS if not explicitly provided
        if hint is None:
            # Special case for Kolay's weird 400 for bad API keys
            if status_code == 400 and "API anahtarını kontrol edin" in str(message):
                self.hint = "It seems we need a fresh login to continue. Please run [bold]kolay auth login[/bold] to securely connect your session."
            elif "Deneme süreniz" in str(message):
                self.message = "It looks like your Kolay IK workspace's free trial has ended."
                self.hint = "To continue using the service, please activate a paid plan in the Kolay web app, or connect using an active API token."
                if status_code == 400:
                    self.status_code = 403  # Semantically it's a Forbidden error
            elif status_code and status_code in HTTP_ERRORS:
                self.hint = HTTP_ERRORS[status_code][1]
            else:
                self.hint = hint
        else:
            self.hint = hint

    @property
    def error_code(self) -> str:
        """Machine-readable error classification.

        Returns a stable string that callers (LLMs, scripts, UI) can
        switch on without parsing human-readable messages.
        """
        msg = str(self.message).lower()
        raw = str(self.raw_response or "").lower()
        combined = msg + raw

        # ---- Account / entitlement state ----
        if "deneme süreniz" in combined or "trial" in combined:
            return "account_expired"
        if "hesabınız" in combined and ("engellenmiş" in combined or "askıya" in combined):
            return "account_suspended"

        # ---- Credential errors ----
        if self.status_code == 401:
            return "invalid_credentials"
        if self.status_code == 400 and "api anahtar" in combined:
            return "invalid_credentials"
        if self.status_code == 400 and "geçersiz" in combined and "api" in combined:
            return "invalid_credentials"
        if "token" in combined and ("expired" in combined or "geçersiz" in combined):
            return "invalid_credentials"
        if "yetkisiz" in combined or "oturum" in combined:
            return "invalid_credentials"

        # ---- Permission / scope ----
        if self.status_code == 403:
            return "insufficient_scope"

        # ---- Client errors ----
        if self.status_code == 404:
            return "not_found"
        if self.status_code == 409:
            return "conflict"
        if self.status_code == 429:
            return "rate_limited"
        if self.status_code in (400, 422):
            return "validation_error"

        # ---- Upstream / transient ----
        if self.status_code and self.status_code >= 500:
            return "upstream_error"
        if "timeout" in combined or "timed out" in combined:
            return "upstream_timeout"
        if "connect" in combined and "could not" in combined:
            return "upstream_unreachable"

        return "unknown_error"

    @property
    def retryable(self) -> bool:
        """Whether the caller should retry this request."""
        return self.error_code in (
            "rate_limited", "upstream_error", "upstream_timeout", "upstream_unreachable",
        )

    @property
    def exit_code(self) -> int:
        """Semantic exit code from HTTP status."""
        if self.status_code is None:
            return 1

        # Override for misleading 400 auth errors from Kolay API
        if self.error_code == "invalid_credentials":
            return 4  # Auth error

        return self.EXIT_CODES.get(self.status_code, 1)

    def to_dict(self) -> dict:
        """JSON error output for CLI."""
        from kolay_cli.ui.output import strip_markup
        d: dict = {"error": True, "message": self.message}
        if self.status_code is not None:
            d["status"] = self.status_code
        if self.hint:
            d["hint"] = strip_markup(self.hint)
        d["exit_code"] = self.exit_code
        return d

    def to_mcp_dict(self) -> dict:
        """Structured error for MCP tool responses.

        Never masked by FastMCP because it is a normal return value,
        not a raised exception.
        """
        from kolay_cli.ui.output import strip_markup
        result: dict = {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.status_code is not None:
            result["http_status"] = self.status_code
        if self.hint:
            result["hint"] = strip_markup(self.hint)
        return result

