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


class LLMResponseParser(Handler[str, dict[str, object]]):
    """Parses LLM responses to extract application JSON."""

    def __init__(self) -> None:
        self.fixes: list[Callable[[str], str]] = [
            self.fix_reasoning_tags,
            self.fix_markdown_code_blocks,
            self.fix_double_quotes,
            self.fix_double_closing_brackets,
        ]

    @property
    def log(self) -> logging.Logger:
        return thread_logger()

    @override
    def process(self, input_data: str) -> dict[str, object]:
        """Parse raw LLM response and extract application JSON."""
        self.log.info(f"Raw LLM response (first 500 chars): {input_data[:500]}")

        input_data = self.apply_all_fixes(input_data.strip())

        result = self.try_parse(input_data)
        if result is not None:
            return result

        raise json.JSONDecodeError("Failed to parse JSON after all fixes", input_data, 0)

    def try_parse(self, data: str) -> dict[str, object]:
        """Try to parse JSON, return result or None if it fails."""
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            if not hasattr(e, 'pos') or not e.pos:
                return dict()
            if "Extra data" in str(e):
                self.log.warning(f"Ignoring extra data after position {e.pos}")
                # return self.try_parse(data[:e.pos])
                try:
                    return json.loads(data[:e.pos])
                except json.JSONDecodeError:
                    pass

            self.log.error(f"JSON parse error: {str(e)}")
            start = max(0, e.pos - 100)
            end = min(len(data), e.pos + 50)
            self.log.error(f"Error context: {repr(data[start:end])}")
        return dict()

    def apply_all_fixes(self, data: str) -> str:
        """Apply all fixes cumulatively and return fixed data."""
        fixed_data = data
        for fix_method in self.fixes:
            fixed_data = fix_method(fixed_data)
        return fixed_data

    def fix_reasoning_tags(self, data: str) -> str:
        """Strip reasoning output tags like <think>...</think>."""
        fixed = re.sub(r'<think>.*?</think>', '', data, flags=re.DOTALL)
        if fixed != data:
            self.log.info("Removed reasoning tags")
        return fixed

    def fix_markdown_code_blocks(self, data: str) -> str:
        """Extract JSON from markdown code blocks."""
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', data, re.DOTALL)
        if json_match:
            self.log.info("Extracted JSON from markdown code block")
            return json_match.group(1)
        return data

    def fix_double_quotes(self, data: str) -> str:
        """Fix double quotes like {""key" -> {"key"."""
        fixed = re.sub(r'\{""', r'{"', data)
        if fixed != data:
            self.log.info("Fixed double quotes")
        return fixed

    def fix_double_closing_brackets(self, data: str) -> str:
        """Fix double closing brackets like ]],"key" -> ],"key"."""
        fixed = re.sub(r'\]\],\s*"', r'],"', data)
        if fixed != data:
            self.log.info("Fixed double closing brackets")
        return fixed

    def fix_extra_data_after_json(self, data: str) -> str:
        """Remove extra data after first complete JSON object."""
        depth = 0
        for i, char in enumerate(data):
            depth += 1 if char == '{' else (-1 if char == '}' else 0)

            if depth != 0:
                continue

            remaining = data[i+1:].strip()
            if not remaining:
                return data

            self.log.info(f"Removed extra data after JSON: {remaining[:50]}")
            return data[:i+1]

        return data

