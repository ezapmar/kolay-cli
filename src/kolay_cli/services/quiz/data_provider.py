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

    @abstractmethod
    def get_company_start_date(self) -> str:
        """Return the earliest known date for this tenant (YYYY-MM-DD)."""
        ...



class KolayAPIProvider(DataProvider):
    """Uses KolayClient. The real deal."""

    def list_people(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return people with full profile data (including avatar).

        The list endpoint only returns id/firstName/lastName.
        We fetch full profiles for a batch to enrich with photos, department, title, etc.
        """
        from ..person import list_people, view_person
        import random

        result_stubs = []
        target = min(limit, 200)
        page = 1
        while len(result_stubs) < target:
            # Kolay API throws 400 if limit > 50
            res = list_people(status="active", limit=50, page=page)
            items = res.get("items", [])
            if not items:
                break
            result_stubs.extend(items)
            if len(items) < 50:
                break
            page += 1
            
        stubs = result_stubs[:target]  # [{id, firstName, lastName}, ...]

        if not stubs:
            return []

        # Fetch full profiles for up to 40 randomly selected people.
        # This gives us avatar, department, title, educationLevel, hireDate, etc.
        sample_size = min(40, len(stubs))
        sample = random.sample(stubs, sample_size) if len(stubs) > sample_size else stubs

        enriched: list[dict[str, Any]] = []
        for stub in sample:
            try:
                profile = view_person(stub["id"])
                # Merge stub fields so firstName/lastName are always present
                profile.setdefault("firstName", stub.get("firstName", ""))
                profile.setdefault("lastName", stub.get("lastName", ""))

                # Extract department and title from unitList
                units = profile.get("unitList") or []
                active_units = [u for u in units if u.get("active")]
                assignment = active_units[0].get("items", []) if active_units else (units[0].get("items", []) if units else [])
                
                dept_name = None
                title_name = None
                for item in assignment:
                    uname = item.get("unitName", "").lower()
                    if uname in ("department", "departman"):
                        dept_name = item.get("unitItemName")
                    elif uname in ("position", "pozisyon"):
                        title_name = item.get("unitItemName")
                
                if dept_name and not profile.get("department"):
                    profile["department"] = {"name": dept_name}
                if title_name and not profile.get("title"):
                    profile["title"] = title_name

                enriched.append(profile)
            except Exception:
                # If a profile fetch fails, use the stub (no photo, but won't crash)
                enriched.append(stub)

        # Also return the remaining stubs (without detailed data) for non-photo queries
        remaining_ids = {p["id"] for p in sample}
        for stub in stubs:
            if stub["id"] not in remaining_ids:
                enriched.append(stub)

        return enriched

    def get_unit_tree(self) -> list[dict[str, Any]]:
        from ..unit import unit_tree
        return unit_tree()

    def list_leaves(self, start: str, end: str, limit: int = 200) -> list[dict[str, Any]]:
        from ..leave import list_leaves
        return list_leaves(status="approved", start=start, end=end, limit=limit)

    def get_company_start_date(self) -> str:
        """Derive tenant start from the earliest employee hireDate."""
        from datetime import date
        people = self.list_people(limit=200)
        dates: list[str] = []
        for p in people:
            d = p.get("hireDate") or p.get("startDate") or p.get("employmentStartDate") or ""
            if d and len(d) >= 10:
                dates.append(d[:10])
        if dates:
            return min(dates)
        # Fallback: 3 years ago
        today = date.today()
        return f"{today.year - 3}-01-01"


class MockProvider(DataProvider):
    """Reads from a fixture. For tests and demos."""

    def get_company_start_date(self) -> str:
        return "2021-01-15"

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
            {"id": "mock_id_8", "firstName": "Burcu", "lastName": "Güneş",
             "department": {"name": "Finans"}, "educationLevel": "Lisans",
             "title": "Finans Analisti", "photoUrl": "https://i.pravatar.cc/150?u=8"},
            # Extras to ensure some titles belong to >1 person (multi_titles) for distractors
            {"id": "mock_id_9", "firstName": "Veli", "lastName": "Aslan",
             "title": "Kıdemli Mühendis"},
            {"id": "mock_id_10", "firstName": "Selma", "lastName": "Kısa",
             "title": "Kıdemli Mühendis"},
            {"id": "mock_id_11", "firstName": "Cem", "lastName": "Uzan",
             "title": "UX Tasarımcı"},
            {"id": "mock_id_12", "firstName": "Oktay", "lastName": "Keskin",
             "title": "Satış Temsilcisi"},
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

