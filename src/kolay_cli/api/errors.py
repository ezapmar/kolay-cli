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

