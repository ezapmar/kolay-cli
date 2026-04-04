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
    """[READ] Check if the current Kolay IK token is valid and the API is reachable.
    Returns account info on success, or an error message on failure."""
    from ..api.client import KolayClient
    from ..api.errors import APIError
    try:
        data = KolayClient().get("v2/person/list", params={"limit": 1})
        return {"connected": True, "message": "Connection successful.", "sample": data}
    except APIError as e:
        return {"connected": False, "message": str(e)}


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
