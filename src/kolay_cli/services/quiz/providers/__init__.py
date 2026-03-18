from __future__ import annotations
from typing import Type

from ..base import BaseQuestionProvider
from .photo_match import PhotoMatchProvider

def get_available_providers() -> dict[str, Type[BaseQuestionProvider]]:
    return {
        PhotoMatchProvider.name: PhotoMatchProvider,
    }
