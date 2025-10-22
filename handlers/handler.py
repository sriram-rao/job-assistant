from __future__ import annotations

from logging import Logger
from typing import Generic, Protocol, TypeVar


T_Input = TypeVar('T_Input', contravariant=True)
T_Output = TypeVar('T_Output', covariant=True)


class Handler(Protocol, Generic[T_Input, T_Output]):
    """Generic handler interface for pipeline workers."""

    @property
    def log(self) -> Logger:
        """Logger instance for this handler."""
        ...

    def process(self, input_data: T_Input) -> T_Output:
        """Process input and return output."""
        ...
