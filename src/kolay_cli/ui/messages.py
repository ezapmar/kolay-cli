"""
ui/messages.py — Witty, empathetic error messages for the Kolay IK CLI.

Keep the funny strings here so engineers can tweak the vibe without
touching any logic. Each scenario returns a (headline, body, hint) tuple.
"""
from __future__ import annotations
import random

# ── 401 Unauthorised ──────────────────────────────────────────────────────────
# Vibe: "I have no idea who you are, but you seem nice."

_401_SCENARIOS = [
    (
        "🕵️  Couldn't verify your identity",
        "You tried to enter the building with a library card.\n"
        "Our bouncer (the API) was not impressed.",
        "Run [bold]kolay auth login[/bold] and try again.",
    ),
    (
        "🎟️  Nice try, but this isn't a valid ticket",
        "Your token is either expired, revoked, or you copy-pasted\n"
        "it from a Post-it note three months ago.",
        "Run [bold]kolay auth login[/bold] to set a fresh token.",
    ),
    (
        "🔑  The door didn't open",
        "Either the key is wrong or the lock was changed while\n"
        "you were on holiday. Either way — not your day.",
        "Run [bold]kolay auth login[/bold] or set [bold]KOLAY_API_TOKEN[/bold] in your env.",
    ),
]

# ── 403 Forbidden ─────────────────────────────────────────────────────────────
# Vibe: "You're logged in, but you're not *that* important."

_403_SCENARIOS = [
    (
        "🚫  You don't have clearance for this",
        "Think of it as the VIP section of the API.\n"
        "Your token is totally valid — it just can't open this door.",
        "Ask your Kolay IK Admin to grant the required scopes.",
    ),
    (
        "📁  Those aren't your files to shred",
        "You're authenticated, but not authorised.\n"
        "Management has opinions about who touches what.",
        "Contact your Kolay IK Admin — they control API permissions.",
    ),
    (
        "👔  Nice badge, wrong floor",
        "Your token works, but this endpoint requires\n"
        "elevated access that your current role doesn't have.",
        "Your Kolay IK Admin can promote your token's scopes.",
    ),
]

# ── 429 Rate Limited ──────────────────────────────────────────────────────────
_429_SCENARIOS = [
    (
        "☕  Whoa, slow down there",
        "You've been hammering the API like it owes you money.\n"
        "It needs a moment to breathe.",
        "Wait a few seconds and try again.",
    ),
]

# ── 500 Server Error ─────────────────────────────────────────────────────────
_500_SCENARIOS = [
    (
        "💥  The server sneezed",
        "Something went wrong on Kolay IK's end — not your fault.\n"
        "The hamsters powering the server took a break.",
        "Try again in a moment. If it persists, check status.kolayik.com",
    ),
]

# ── Dispatch ──────────────────────────────────────────────────────────────────

_SCENARIO_MAP: dict[int, list[tuple[str, str, str]]] = {
    401: _401_SCENARIOS,
    403: _403_SCENARIOS,
    429: _429_SCENARIOS,
    500: _500_SCENARIOS,
    502: _500_SCENARIOS,
    503: _500_SCENARIOS,
}


def get_scenario(status_code: int) -> tuple[str, str, str] | None:
    """Return a random (headline, body, hint) for the given HTTP status code.

    Returns None if no witty scenario is defined for that code.
    """
    pool = _SCENARIO_MAP.get(status_code)
    if not pool:
        return None
    return random.choice(pool)  # nosec B311 — cosmetic UI quip, not crypto
