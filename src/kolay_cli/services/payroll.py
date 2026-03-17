"""Payroll services."""
from __future__ import annotations

from typing import Any

from ..api.client import KolayClient, safe_id


def view_payroll_sheet(
    payroll_id: str,
    *,
    search: str | None = None,
    status: list[str] | None = None,
    salary_period: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch the payroll sheet (Çarşaf Bordro) for a specific payroll run.

    Returns the full payroll sheet data as returned by the API.
    """
    payload: dict[str, Any] = {}

    # Build optional filter block
    filt: dict[str, Any] = {}
    if search:
        filt["search"] = search
    if status:
        filt["status"] = status
    if salary_period:
        filt["salaryPeriod"] = salary_period
    if filt:
        payload["filter"] = filt

    resp = KolayClient().post(
        f"v2/payroll-sheet/view/{safe_id(payroll_id, 'payroll_id')}",
        data=payload,
    )
    return resp.get("data", resp)
