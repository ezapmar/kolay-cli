"""Error messages for Kolay IK CLI."""
from __future__ import annotations
import random



_401_SCENARIOS = [
    (
        "Authentication failed",
        "Your API token was rejected by the Kolay IK API.\n"
        "It may be expired, revoked, or entered incorrectly.",
        "Run [bold]kolay auth login[/bold] to set a valid token.",
    ),
    (
        "Invalid API token",
        "The API token stored on this machine is no longer accepted.\n"
        "This usually means it was revoked or has expired.",
        "Run [bold]kolay auth login[/bold] with a fresh token from the Kolay IK web app.",
    ),
    (
        "Session expired",
        "Your API session is no longer valid.\n"
        "You need to authenticate again before making API calls.",
        "Run [bold]kolay auth login[/bold] or set [bold]KOLAY_API_TOKEN[/bold] in your environment.",
    ),
]



_403_SCENARIOS = [
    (
        "Permission denied",
        "Your token is valid, but it does not have permission\n"
        "to access this endpoint.",
        "Ask your Kolay IK Admin to grant the required API scopes for your token.",
    ),
    (
        "Insufficient permissions",
        "You are authenticated, but your token's access level\n"
        "does not allow this operation.",
        "Contact your Kolay IK Admin to update the permissions for this API token.",
    ),
    (
        "Access denied (403)",
        "This endpoint requires a higher permission level\n"
        "than your current API token has.",
        "Your Kolay IK Admin can add the required scope to your API token.",
    ),
]


_429_SCENARIOS = [
    (
        "Rate limit reached",
        "Too many requests were sent in a short period.\n"
        "The Kolay IK API has temporarily blocked further requests.",
        "Wait a few seconds and try again.",
    ),
]


_500_SCENARIOS = [
    (
        "Kolay IK API error",
        "The Kolay IK API returned an internal server error.\n"
        "This is not caused by your request.",
        "Try again in a moment. If it persists, check status.kolayik.com",
    ),
]



_SCENARIO_MAP: dict[int, list[tuple[str, str, str]]] = {
    401: _401_SCENARIOS,
    403: _403_SCENARIOS,
    429: _429_SCENARIOS,
    500: _500_SCENARIOS,
    502: _500_SCENARIOS,
    503: _500_SCENARIOS,
}


def get_scenario(status_code: int) -> tuple[str, str, str] | None:
    """Return a scenario message for the given HTTP status code."""
    pool = _SCENARIO_MAP.get(status_code)
    if not pool:
        return None
    return random.choice(pool)  # nosec B311 — cosmetic UI only, not crypto
