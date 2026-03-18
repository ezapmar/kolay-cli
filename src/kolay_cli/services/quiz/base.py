from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .data_provider import DataProvider


class MediaType(Enum):
    PHOTO_URL = "photo_url"
    ASCII = "ascii"
    TEXT = "text"


@dataclass
class QuestionMedia:
    type: MediaType
    content: str


@dataclass
class QuestionResult:
    is_correct: bool
    correct_answer: str
    explanation: str


class BaseQuestion(ABC):
    """One question. One answer. One truth."""

    @property
    @abstractmethod
    def id(self) -> str:
        ...
    
    @abstractmethod
    def prompt_text(self) -> str:
        ...

    @abstractmethod
    def choices(self) -> list[str]:
        ...
        
    @property
    @abstractmethod
    def correct_answer(self) -> str:
        ...

    @abstractmethod
    def check_answer(self, answer: str) -> QuestionResult:
        ...

    @abstractmethod
    def media(self) -> QuestionMedia | None:
        ...


class BaseQuestionProvider(ABC):
    """Produces questions. That's it. That's the interface."""
    name: str
    # Override in subclasses with context-appropriate "scanning..." lines.
    analyzing_hints: list[str] = [
        "Scanning records...",
        "Cross-referencing data...",
        "Loading case file...",
    ]

    def __init__(self, data_provider: DataProvider):
        self.data_provider = data_provider

    @abstractmethod
    def generate(self, count: int, seen_ids: set[str]) -> list[BaseQuestion]:
        ...

