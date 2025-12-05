from __future__ import annotations

import json
import logging
import re
import threading
from typing import Callable, override

from .handler import Handler


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class JsonFixer(Handler[str, dict[str, object]]):
    """Fixes common JSON errors in LLM-generated responses."""

    def __init__(self) -> None:
        self.fixes: list[Callable[[str], str]] = [
            self.fix_double_closing_brackets,
            self.fix_extra_data_after_json,
        ]

    @property
    def log(self) -> logging.Logger:
        return thread_logger()

    @override
    def process(self, input_data: str) -> dict[str, object]:
        """Parse JSON string, attempting to fix common errors."""
        result = self.try_parse(input_data)
        if result is not None:
            return result

        self.log.warning("Initial JSON parse failed, attempting fixes")
        fixed_data = self.apply_all_fixes(input_data)

        result = self.try_parse(fixed_data)
        if result is not None:
            return result

        self.log.error("JSON still invalid after all fixes")
        self.log_error_context(input_data)
        raise json.JSONDecodeError("Failed to parse JSON after all fixes", input_data, 0)

    def try_parse(self, data: str) -> dict[str, object] | None:
        """Try to parse JSON, return result or None if it fails."""
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None

    def apply_all_fixes(self, data: str) -> str:
        """Apply all fixes cumulatively and return fixed data."""
        fixed_data = data
        for fix_method in self.fixes:
            fixed_data = fix_method(fixed_data)
        return fixed_data

    def fix_double_closing_brackets(self, data: str) -> str:
        """Fix double closing brackets like ]],"key" -> ],"key"."""
        fixed = re.sub(r'\]\],\s*"', r'],"', data)
        if fixed != data:
            self.log.info("Fixed double closing brackets")
        return fixed

    def fix_extra_data_after_json(self, data: str) -> str:
        """Remove extra data after final closing brace."""
        last_brace = data.rfind('}')
        if last_brace != -1 and last_brace < len(data) - 1:
            extra = data[last_brace+1:].strip()
            if extra:
                self.log.info(f"Removed extra data after JSON: {extra[:50]}")
                return data[:last_brace+1]
        return data

    def log_error_context(self, data: str) -> None:
        """Log context around JSON parse error."""
        try:
            json.loads(data)
        except json.JSONDecodeError as e:
            self.log.error(f"JSON parse error: {str(e)}")
            if hasattr(e, 'pos') and e.pos:
                start = max(0, e.pos - 100)
                end = min(len(data), e.pos + 50)
                self.log.error(f"Error context: {repr(data[start:end])}")
