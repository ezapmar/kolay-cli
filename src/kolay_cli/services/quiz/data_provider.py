from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class DataProvider(ABC):
    @abstractmethod
    def list_people(self, limit: int = 100) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_unit_tree(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def list_leaves(self, start: str, end: str, limit: int = 200) -> list[dict[str, Any]]:
        ...


class KolayAPIProvider(DataProvider):
    """Uses KolayClient. The real deal."""

    def list_people(self, limit: int = 100) -> list[dict[str, Any]]:
        from ..person import list_people
        result = list_people(status="active", limit=limit, page=1)
        return result.get("items", [])

    def get_unit_tree(self) -> list[dict[str, Any]]:
        from ..unit import unit_tree
        return unit_tree()

    def list_leaves(self, start: str, end: str, limit: int = 200) -> list[dict[str, Any]]:
        from ..leave import list_leaves
        return list_leaves(status="approved", start=start, end=end, limit=limit)


class MockProvider(DataProvider):
    """Reads from a fixture. For tests and demos."""

    def list_people(self, limit: int = 100) -> list[dict[str, Any]]:
        return [
            {"id": "mock_id_1", "firstName": "Ahmet", "lastName": "Yılmaz",
             "department": {"name": "Mühendislik"}, "educationLevel": "Lisans Üstü",
             "title": "Kıdemli Mühendis", "photoUrl": "https://i.pravatar.cc/150?u=1"},
            {"id": "mock_id_2", "firstName": "Ayşe", "lastName": "Kaya",
             "department": {"name": "Tasarım"}, "educationLevel": "Lisans",
             "title": "UX Tasarımcı", "photoUrl": "https://i.pravatar.cc/150?u=2"},
            {"id": "mock_id_3", "firstName": "Mehmet", "lastName": "Demir",
             "department": {"name": "Pazarlama"}, "educationLevel": "Yüksek Lisans",
             "title": "Pazarlama Direktörü", "photoUrl": "https://i.pravatar.cc/150?u=3"},
            {"id": "mock_id_4", "firstName": "Fatma", "lastName": "Şahin",
             "department": {"name": "Mühendislik"}, "educationLevel": "Doktora",
             "title": "Baş Mühendis", "photoUrl": "https://i.pravatar.cc/150?u=4"},
            {"id": "mock_id_5", "firstName": "Ali", "lastName": "Öztürk",
             "department": {"name": "Satış"}, "educationLevel": "Lisans",
             "title": "Satış Temsilcisi", "photoUrl": "https://i.pravatar.cc/150?u=5"},
            {"id": "mock_id_6", "firstName": "Zeynep", "lastName": "Arslan",
             "department": {"name": "İK"}, "educationLevel": "Yüksek Lisans",
             "title": "İK Uzmanı", "photoUrl": "https://i.pravatar.cc/150?u=6"},
            {"id": "mock_id_7", "firstName": "Emre", "lastName": "Çelik",
             "department": {"name": "Mühendislik"}, "educationLevel": "Doktora",
             "title": "Veri Bilimcisi", "photoUrl": "https://i.pravatar.cc/150?u=7"},
            {"id": "mock_id_8", "firstName": "Selin", "lastName": "Yıldız",
             "department": {"name": "Finans"}, "educationLevel": "Lisans Üstü",
             "title": "Finans Analisti", "photoUrl": "https://i.pravatar.cc/150?u=8"},
        ][:limit]

    def get_unit_tree(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "unit_1", "name": "Mühendislik",
                "items": [
                    {"id": "pos_1", "title": "Kıdemli Mühendis", "personCount": 3},
                    {"id": "pos_2", "title": "Baş Mühendis", "personCount": 1},
                    {"id": "pos_3", "title": "Veri Bilimcisi", "personCount": 1},
                ]
            },
            {
                "id": "unit_2", "name": "Pazarlama",
                "items": [
                    {"id": "pos_4", "title": "Pazarlama Direktörü", "personCount": 1},
                    {"id": "pos_5", "title": "İçerik Uzmanı", "personCount": 2},
                ]
            },
            {
                "id": "unit_3", "name": "İK",
                "items": [
                    {"id": "pos_6", "title": "İK Uzmanı", "personCount": 2},
                    {"id": "pos_7", "title": "İnsan Kaynakları Direktörü", "personCount": 1},
                ]
            },
            {
                "id": "unit_4", "name": "Finans",
                "items": [
                    {"id": "pos_8", "title": "Finans Analisti", "personCount": 2},
                    {"id": "pos_9", "title": "CFO Asistanı", "personCount": 1},
                ]
            },
            {
                "id": "unit_5", "name": "Satış",
                "items": [
                    {"id": "pos_10", "title": "Satış Temsilcisi", "personCount": 4},
                ]
            },
        ]

    def list_leaves(self, start: str, end: str, limit: int = 200) -> list[dict[str, Any]]:
        return [
            {"id": "leave_1", "leaveType": {"name": "Yıllık İzin"}, "startDate": "2024-12-02", "endDate": "2024-12-06", "dayCount": 5},
            {"id": "leave_2", "leaveType": {"name": "Uzaktan Çalışma"}, "startDate": "2024-12-09", "endDate": "2024-12-13", "dayCount": 5},
            {"id": "leave_3", "leaveType": {"name": "Yıllık İzin"}, "startDate": "2024-12-16", "endDate": "2024-12-20", "dayCount": 5},
            {"id": "leave_4", "leaveType": {"name": "Hastalık İzni"}, "startDate": "2024-12-02", "endDate": "2024-12-03", "dayCount": 2},
            {"id": "leave_5", "leaveType": {"name": "Uzaktan Çalışma"}, "startDate": "2024-12-23", "endDate": "2024-12-27", "dayCount": 5},
            {"id": "leave_6", "leaveType": {"name": "Yıllık İzin"}, "startDate": "2024-12-23", "endDate": "2024-12-27", "dayCount": 5},
            {"id": "leave_7", "leaveType": {"name": "Yıllık İzin"}, "startDate": "2024-12-09", "endDate": "2024-12-11", "dayCount": 3},
            {"id": "leave_8", "leaveType": {"name": "Uzaktan Çalışma"}, "startDate": "2024-12-16", "endDate": "2024-12-17", "dayCount": 2},
        ][:limit]

