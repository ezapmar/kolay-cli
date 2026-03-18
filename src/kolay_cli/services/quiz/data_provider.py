from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class DataProvider(ABC):
    @abstractmethod
    def list_people(self, limit: int = 100) -> list[dict[str, Any]]:
        ...


class KolayAPIProvider(DataProvider):
    """Uses KolayClient. The real deal."""

    def list_people(self, limit: int = 100) -> list[dict[str, Any]]:
        from ..person import list_people

        # Try to fetch up to limit active people
        result = list_people(status="active", limit=limit, page=1)
        return result.get("items", [])


class MockProvider(DataProvider):
    """Reads from a fixture. For tests and demos."""

    def list_people(self, limit: int = 100) -> list[dict[str, Any]]:
        return [
            {
                "id": "mock_id_1",
                "firstName": "Ahmet",
                "lastName": "Yılmaz",
                "department": {"name": "Engineering"},
                "photoUrl": "https://i.pravatar.cc/150?u=1",
            },
            {
                "id": "mock_id_2",
                "firstName": "Ayşe",
                "lastName": "Kaya",
                "department": {"name": "Design"},
                "photoUrl": "https://i.pravatar.cc/150?u=2",
            },
            {
                "id": "mock_id_3",
                "firstName": "Mehmet",
                "lastName": "Demir",
                "department": {"name": "Marketing"},
                "photoUrl": "https://i.pravatar.cc/150?u=3",
            },
            {
                "id": "mock_id_4",
                "firstName": "Fatma",
                "lastName": "Şahin",
                "department": {"name": "Engineering"},
                "photoUrl": "https://i.pravatar.cc/150?u=4",
            },
            {
                "id": "mock_id_5",
                "firstName": "Ali",
                "lastName": "Öztürk",
                "department": {"name": "Sales"},
                "photoUrl": "https://i.pravatar.cc/150?u=5",
            },
        ][:limit]
