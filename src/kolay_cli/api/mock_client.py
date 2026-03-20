"""Mock API Client for local Kolay-CLI development and LLM agent testing."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from .client import KolayClient

class MockKolayClient(KolayClient):
    """
    Drop-in replacement for KolayClient that returns static fake data
    without making real HTTP requests.
    """

    def __init__(self, *args, **kwargs):
        self.base_url = "http://mock.test"
        self.session = None
        self.token = "mock-token"

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Mock GET requests."""
        if "person/list" in endpoint:
            return {"data": {"items": [{"id": "p1", "firstName": "Mock", "lastName": "User"}], "totalCount": 1}, "error": False}
        if "person/" in endpoint and "view" in endpoint:
            return {"data": {"id": "p1", "firstName": "Mock", "lastName": "User", "workEmail": "mock@kolayik.com"}, "error": False}
        if "leave/list" in endpoint:
            return {"data": {"items": [], "totalCount": 0}, "error": False}
        if "leave/balance" in endpoint:
            return {"data": [{"leaveTypeId": "type1", "leaveType": {"name": "Yıllık İzin"}, "total": 14, "used": 0, "unused": 14}], "error": False}
        if "unit/tree" in endpoint:
            return {"data": [{"id": "u1", "name": "Company", "items": [{"id": "p1", "name": "Mock User"}], "children": []}], "error": False}
        
        # Generic fallback
        return {"data": {"items": [], "totalCount": 0}, "error": False}

    def post(self, endpoint: str, data: dict[str, Any] | None = None, **kwargs) -> dict[str, Any]:
        """Mock POST requests."""
        if "person/list" in endpoint:
            # POST used for searching in Kolay API
            return {"data": {"items": [{"id": "p1", "firstName": "Mock", "lastName": "User"}], "totalCount": 1}, "error": False}
        
        return {"data": {"id": str(uuid.uuid4()), "status": "mock_created"}, "error": False}

    def put(self, endpoint: str, data: dict[str, Any] | None = None, **kwargs) -> dict[str, Any]:
        return {"data": {"id": str(uuid.uuid4()), "status": "mock_updated"}, "error": False}

    def patch(self, endpoint: str, data: dict[str, Any] | None = None, **kwargs) -> dict[str, Any]:
        return {"data": {"id": str(uuid.uuid4()), "status": "mock_patched"}, "error": False}

    def delete(self, endpoint: str, **kwargs) -> dict[str, Any]:
        return {"data": {"id": str(uuid.uuid4()), "status": "mock_deleted"}, "error": False}
