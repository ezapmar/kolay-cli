from .adapter import Tool
from typing import Any
from .adapter import Context
from .adapter import CurrentContext
from ..security import require_auth
from ..services import person as person_svc
from ..services import leave as leave_svc
from ..services import timelog as timelog_svc
from ..services import training as training_svc
from ..services import transaction as transaction_svc
from ..services import calendar as calendar_svc
from ..services import unit as unit_svc
from ..services import approval as approval_svc
from ..services import hr_analytics as hr_analytics_svc
from ..services import payroll as payroll_svc
from ..services import wellness as wellness_svc
from ..ui.search import filter_items_silent
from ..mcp_progress import sync_progress_bridge
import json


@require_auth
def validate_connection() -> dict[str, Any]:
    """[READ] Comprehensive health check for the Kolay IK API connection.

    Probes the API with a lightweight request and returns structured
    diagnostic information:
      - connected: bool
      - account_status: active | trial_expired | suspended | unknown
      - error_code: machine-readable error classification (if failed)
      - latency_ms: round-trip time to the API
      - api_version: detected API version
      - hint: remediation guidance (if failed)

    Use this FIRST when any other tool returns an error to diagnose
    whether it is a credentials, account, or connectivity issue."""
    import time
    from ..api.client import KolayClient
    from ..api.errors import APIError

    t0 = time.monotonic()
    try:
        client = KolayClient()
        data = client.get("v2/person/list", params={"limit": 1})
        latency = round((time.monotonic() - t0) * 1000, 1)

        return {
            "connected": True,
            "account_status": "active",
            "latency_ms": latency,
            "api_version": "v2",
            "message": "Connection successful. API is reachable and token is valid.",
            "sample_record_count": len(data) if isinstance(data, list) else 1,
        }

    except APIError as e:
        latency = round((time.monotonic() - t0) * 1000, 1)

        # Map error_code to account_status
        code = e.error_code
        if code == "account_expired":
            account_status = "trial_expired"
        elif code == "account_suspended":
            account_status = "suspended"
        elif code in ("invalid_credentials",):
            account_status = "credentials_invalid"
        else:
            account_status = "unknown"

        return {
            "connected": False,
            "account_status": account_status,
            "error_code": code,
            "http_status": e.status_code,
            "message": str(e),
            "hint": e.hint or "Check your API token and account status.",
            "retryable": e.retryable,
            "latency_ms": latency,
        }

    except Exception as e:
        latency = round((time.monotonic() - t0) * 1000, 1)
        return {
            "connected": False,
            "account_status": "unknown",
            "error_code": "connector_error",
            "message": str(e),
            "hint": "An unexpected error occurred in the connector layer. Check server logs.",
            "retryable": False,
            "latency_ms": latency,
        }


@require_auth
def quiz_challenge(
    mode: str = "photo_match",
    count: int = 5,
) -> dict[str, Any]:
    """[READ] Generate a Kolay Quiz challenge.
    Use this when the user says 'give me a quiz' or 'test my knowledge'.
    Returns a list of questions with their choices, correct answers, and media.
    You, the AI, should act as the game host: present the questions one by one, wait for the user's answer, and then reveal if they were right.
    Do NOT reveal the correct answers immediately."""
    from ..services.quiz import get_factory, KolayAPIProvider
    factory = get_factory()
    try:
        provider = factory.get_provider(mode, KolayAPIProvider())
    except ValueError as e:
        return {"error": True, "message": str(e)}
        
    questions = provider.generate(count, set())
    
    payload = []
    for q in questions:
        media = q.media()
        payload.append({
            "prompt": q.prompt_text(),
            "choices": q.choices(),
            "correct_answer": q.correct_answer,
            "media": {
                "type": media.type.value,
                "content": media.content
            } if media else None
        })
        
    return {
        "mode": mode,
        "total_questions": len(payload),
        "questions": payload
    }


def register(mcp):
    mcp.add_tool(Tool.from_function(validate_connection, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
    mcp.add_tool(Tool.from_function(quiz_challenge, annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"read"},
    ))
