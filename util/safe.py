from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar("T")


def suppress_errors(fn: Callable[[], T]) -> T | None:
    """Run callable and swallow any exception."""
    try:
        return fn()
    except Exception:
        return None
