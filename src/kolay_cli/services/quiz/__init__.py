from __future__ import annotations

from .engine import QuizEngine, SessionResult
from .factory import QuestionFactory
from .state import QuizState
from .renderer import Renderer
from .data_provider import KolayAPIProvider, MockProvider

__all__ = [
    "QuizEngine",
    "SessionResult",
    "QuestionFactory",
    "QuizState",
    "Renderer",
    "KolayAPIProvider",
    "MockProvider",
    "get_factory",
]

def get_factory() -> QuestionFactory:
    from . import providers
    factory = QuestionFactory()
    for name, cls in providers.get_available_providers().items():
        factory.register(cls)
    return factory
