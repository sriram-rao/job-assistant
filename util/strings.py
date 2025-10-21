from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar


def is_empty(string: str):
    return string is None or len(string) == 0


def get_default_if_blank(string: str, default: str = "result"):
    return string if not is_empty(string) else default


def pad(string: str, left_padding: str = "%%", right_padding: str = ""):
    return left_padding + string + (left_padding if is_empty(right_padding) else right_padding)


def write_to_file(path: str | Path, content: str) -> None:
    if isinstance(path, str):
        path = Path(path)
    with path.open('w') as file:
        _ = file.write(content)


def strip_inline_markdown(text: str) -> str:
    if text is None:
        return ""
    cleaned = re.sub(r"[_*]{2}([^*_`]+)[_*]{2}", r"\1", text)
    cleaned = re.sub(r"[_*]([^*_`]+)[_*]", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    return cleaned.replace("**", "").replace("__", "").strip()


T = TypeVar("T")


def dedupe_ordered(items: Iterable[T], *, key: Callable[[T], Any] | None = None) -> list[T]:
    seen: set[Any] = set()
    result: list[T] = []
    for item in items:
        marker = key(item) if key else item
        if marker in seen:
            continue
        seen.add(marker)
        result.append(item)
    return result
