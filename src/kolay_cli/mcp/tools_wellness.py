from .adapter import Tool
from typing import Any
from ..security import require_auth
from ..services import wellness as wellness_svc
from ..proxy.semantic_cache import semantic_cached


@require_auth
@semantic_cached(ttl=900)
def analyze_employee_wellbeing(person_id: str) -> dict[str, Any]:
    """[READ] Unified burnout + smart leave analysis for a single employee.

    Crosses leave history, annual balance, and Turkish public holidays to:
      - Score burnout signals (balance thresholds + leave recency gaps)
      - Identify bridge-day opportunities in the next 90 days
      - Generate a concrete wellbeing recommendation

    Returns: burnout_status (red_zone [RED] / orange [ORANGE] / yellow [YELLOW] / healthy [GREEN]),
    burnout_score, signals[], bridge_day_opportunities[], and a recommendation string.

    person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved)."""
    return wellness_svc.analyze_employee_wellbeing(person_id)


@require_auth
@semantic_cached(ttl=900)
def get_smart_rest_plan(
    person_id: str,
    horizon_days: int = 90,
) -> dict[str, Any]:
    """[READ] Generate the top-3 rest opportunities ranked by leave efficiency.

    Leave efficiency = total rest days gained / leave credits spent.
    Budget tier is auto-determined from remaining balance:
      <5 days  → conservative (long weekends only)
      5-15     → balanced (long weekends + bridge days)
      15+      → generous (full weeks considered)

    person_id: Employee ID (UUID from person_list, or a name that will be auto-resolved).
    horizon_days: How many days ahead to scan (default 90)."""
    return wellness_svc.get_smart_rest_plan(person_id, horizon_days=horizon_days)


def register(mcp):
    # analyze_employee_wellbeing cross-references leave + timelogs — allow 60s
    mcp.add_tool(Tool.from_function(analyze_employee_wellbeing,
        annotations={"readOnlyHint": True, "openWorldHint": False},
        timeout=60.0,
        tags={"read", "wellness"},
    ))
    # get_smart_rest_plan fanout across leave periods — allow 60s
    mcp.add_tool(Tool.from_function(get_smart_rest_plan,
        annotations={"readOnlyHint": True, "openWorldHint": False},
        timeout=60.0,
        tags={"read", "wellness"},
    ))
