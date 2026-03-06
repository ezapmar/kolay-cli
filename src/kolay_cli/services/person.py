"""Person / employee services."""
from __future__ import annotations

from typing import Any

from ..api.client import KolayClient, safe_id


REASON_CODES = {
    "01": "Resignation (deneme süreli fesh - işverence)",
    "03": "Voluntary resignation (istifa)",
    "04": "Termination without notice (haklı nedenle)",
    "10": "End of fixed-term contract",
    "11": "Retirement",
    "22": "Termination by employer (geçerli neden)",
    "23": "Death",
    "30": "Other",
}


def list_people(
    *,
    page: int = 1,
    status: str = "active",
    search: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Return ``{items, totalCount, page}``."""
    payload: dict[str, Any] = {"page": page, "status": status, "limit": limit}
    if search:
        payload["search"] = search
    resp = KolayClient().post("v2/person/list", data=payload)
    data = resp.get("data", {})
    items = data.get("items", [])
    total = data.get("totalCount") or data.get("total") or data.get("count") or data.get("size") or len(items)
    return {"items": items, "totalCount": total, "page": page}


def view_person(person_id: str) -> dict[str, Any]:
    """Full profile dict."""
    resp = KolayClient().get(f"v2/person/view/{safe_id(person_id)}")
    outer = resp.get("data", {})
    return outer.get("person", outer)


def summary(person_id: str) -> dict[str, Any]:
    return KolayClient().get(f"v2/person/summary/{safe_id(person_id)}").get("data", {})


def leave_status(person_id: str) -> list[dict[str, Any]]:
    return KolayClient().get(f"v2/person/leave-status/{safe_id(person_id)}").get("data", [])


def create_person(
    *,
    first_name: str,
    last_name: str,
    email: str,
    employment_start: str,
    mobile_phone: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "person": {
            "firstName": first_name,
            "lastName": last_name,
            "workEmail": email,
            "employmentStartDate": employment_start,
        }
    }
    if mobile_phone:
        payload["person"]["mobilePhone"] = mobile_phone
    return KolayClient().post("v2/person/create", data=payload).get("data", {})


def update_person(
    person_id: str,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    mobile_phone: str | None = None,
    custom_fields: dict[str, str] | None = None,
) -> dict[str, Any]:
    p: dict[str, Any] = {"id": safe_id(person_id)}
    if first_name:
        p["firstName"] = first_name
    if last_name:
        p["lastName"] = last_name
    if email:
        p["workEmail"] = email
    if mobile_phone:
        p["mobilePhone"] = mobile_phone
    if custom_fields:
        p["dataList"] = [{"fieldToken": k, "value": v} for k, v in custom_fields.items()]
    KolayClient().put("v2/person/update", data={"person": p})
    return {"status": "updated", "person_id": person_id}


def terminate_person(
    person_id: str,
    *,
    termination_date: str,
    reason_code: str,
) -> dict[str, Any]:
    KolayClient().post("v2/person/terminate", data={
        "personId": safe_id(person_id),
        "date": termination_date,
        "reasonCode": reason_code,
        "details": REASON_CODES.get(reason_code, "Termination"),
    })
    return {"status": "terminated", "person_id": person_id, "date": termination_date}


def rehire_person(person_id: str, *, start_date: str) -> dict[str, Any]:
    KolayClient().post(f"v2/person/rehire/{safe_id(person_id)}", data={"employmentStartDate": start_date})
    return {"status": "rehired", "person_id": person_id, "start_date": start_date}


def list_files(person_id: str) -> list[dict[str, Any]]:
    return KolayClient().get(f"v2/person/list-files/{safe_id(person_id)}").get("data", [])


def delete_file(file_id: str) -> dict[str, Any]:
    KolayClient().delete(f"v2/person/delete-file/{safe_id(file_id)}")
    return {"status": "deleted", "id": file_id}


def delete_folder(folder_id: str) -> dict[str, Any]:
    KolayClient().delete(f"v2/person/delete-folder/{safe_id(folder_id)}")
    return {"status": "deleted", "id": folder_id}


def available_fields() -> list[dict[str, Any]]:
    return KolayClient().get("v2/person/show-available-data-fields").get("data", [])


def list_trainings(person_id: str) -> list[dict[str, Any]]:
    return KolayClient().get(f"v2/person/list-trainings/{safe_id(person_id)}").get("data", [])


def assign_training(
    *,
    person_id: str,
    training_id: str,
    status: str = "waiting",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "personId": safe_id(person_id),
        "trainingId": safe_id(training_id),
        "status": status,
    }
    if start_date:
        payload["startDate"] = start_date
    if end_date:
        payload["endDate"] = end_date
    KolayClient().post("v2/person/assign-training", data=payload)
    return {"status": "assigned", "person_id": person_id, "training_id": training_id}


def update_training(
    person_training_id: str,
    *,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if status:
        payload["status"] = status
    if start_date:
        payload["startDate"] = start_date
    if end_date:
        payload["endDate"] = end_date
    KolayClient().put(f"v2/person/update-training/{safe_id(person_training_id)}", data=payload)
    return {"status": "updated", "id": person_training_id}


def delete_training(person_training_id: str) -> dict[str, Any]:
    KolayClient().delete(f"v2/person/delete-training/{safe_id(person_training_id)}")
    return {"status": "deleted", "id": person_training_id}
