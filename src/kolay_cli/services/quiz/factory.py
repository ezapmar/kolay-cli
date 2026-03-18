from __future__ import annotations
from typing import Type

from .base import BaseQuestionProvider
from .data_provider import DataProvider


class QuestionFactory:
    def __init__(self) -> None:
        self._registry: dict[str, Type[BaseQuestionProvider]] = {}

    def register(self, provider_cls: Type[BaseQuestionProvider]) -> None:
        self._registry[provider_cls.name] = provider_cls

    def get_provider(self, name: str, data_provider: DataProvider) -> BaseQuestionProvider:
        if name not in self._registry:
            raise ValueError(f"Unknown question provider: {name}")
        cls = self._registry[name]
        return cls(data_provider=data_provider)

    def available_modes(self) -> list[str]:
        return list(self._registry.keys())
