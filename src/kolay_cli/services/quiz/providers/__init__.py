from __future__ import annotations
from typing import Type

from ..base import BaseQuestionProvider
from .photo_match import PhotoMatchProvider
from .education_champion import EducationChampionProvider
from .unique_title import UniqueTitleProvider
from .december_exodus import DecemberExodusProvider


def get_available_providers() -> dict[str, Type[BaseQuestionProvider]]:
    return {
        PhotoMatchProvider.name: PhotoMatchProvider,
        EducationChampionProvider.name: EducationChampionProvider,
        UniqueTitleProvider.name: UniqueTitleProvider,
        DecemberExodusProvider.name: DecemberExodusProvider,
    }
