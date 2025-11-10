"""Utility functions for converting between JSON and TOON format."""

import json
from typing import Any
import toon_format


def json_to_toon(data: dict[str, Any] | list[Any] | str) -> str:
    """Convert JSON data to TOON format string.

    Args:
        data: Python dict/list or JSON string

    Returns:
        TOON formatted string
    """
    if isinstance(data, str):
        data = json.loads(data)
    return toon_format.encode(data)


def toon_to_json(toon_str: str) -> dict[str, Any] | list[Any]:
    """Convert TOON format string to Python dict/list.

    Args:
        toon_str: TOON formatted string

    Returns:
        Python dict or list
    """
    return toon_format.decode(toon_str)


def toon_to_json_str(toon_str: str) -> str:
    """Convert TOON format string to JSON string.

    Args:
        toon_str: TOON formatted string

    Returns:
        JSON string
    """
    data = toon_format.decode(toon_str)
    return json.dumps(data)
