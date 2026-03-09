from __future__ import annotations



HTTP_ERRORS: dict[int, tuple[str, str]] = {
    400: (
        "Bad request — the API didn't like what you sent.",
        "Double-check your options and try again.",
    ),
    401: (
        "Your session has expired or the token is invalid.",
        "Run [bold]kolay auth login[/bold] to re-authenticate.",
    ),
    403: (
        "Permission denied — you don't have access to this resource.",
        "Ask your Kolay admin to grant the required role.",
    ),
    404: (
        "That resource wasn't found.",
        "The ID might be wrong. Use the interactive picker instead of copy-pasting.",
    ),
    422: (
        "Validation error — some fields are missing or invalid.",
        "Check the required fields with [bold]--help[/bold].",
    ),
    429: (
        "Whoa, slow down! The API rate-limited you.",
        "Wait a few seconds and try again.",
    ),
    500: (
        "The Kolay API returned an internal error.",
        "This is on their end. Try again in a minute.",
    ),
    502: (
        "Bad gateway — the Kolay API might be updating.",
        "Try again in 30 seconds.",
    ),
    503: (
        "The Kolay API is temporarily unavailable.",
        "It'll be back soon — grab a coffee.",
    ),
    504: (
        "Gateway timeout — the API took too long to respond.",
        "Try again in a moment.",
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
                self.hint = "Your API token is invalid. Run [bold]kolay auth login[/bold] to re-authenticate."
            elif status_code and status_code in HTTP_ERRORS:
                self.hint = HTTP_ERRORS[status_code][1]
            else:
                self.hint = hint
        else:
            self.hint = hint

    @property
    def exit_code(self) -> int:
        """Semantic exit code from HTTP status."""
        if self.status_code is None:
            return 1
        
        # Override for misleading 400 auth errors from Kolay API
        if self.status_code == 400 and "API anahtarını kontrol edin" in str(self.message):
            return 4  # Auth error
            
        return self.EXIT_CODES.get(self.status_code, 1)

    def to_dict(self) -> dict:
        """JSON error output."""
        from kolay_cli.ui.output import strip_markup
        d: dict = {"error": True, "message": self.message}
        if self.status_code is not None:
            d["status"] = self.status_code
        if self.hint:
            d["hint"] = strip_markup(self.hint)
        d["exit_code"] = self.exit_code
        return d

