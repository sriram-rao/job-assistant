from __future__ import annotations

import json
import logging
import re
import threading
from typing import override

from .handler import Handler


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class LLMResponseParser(Handler[str, dict[str, object]]):
    """Parses LLM responses to extract application JSON."""

    @property
    def log(self) -> logging.Logger:
        return thread_logger()

    @override
    def process(self, input_data: str) -> dict[str, object]:
        """Parse raw LLM response and extract application JSON."""
        self.log.info(f"Raw LLM response (first 500 chars): {input_data[:500]}")

        # Strip reasoning output (for models like GPT-OSS, DeepSeek-R1)
        input_data = re.sub(r'<think>.*?</think>', '', input_data, flags=re.DOTALL)

        # Strip markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', input_data, re.DOTALL)
        if json_match:
            input_data = json_match.group(1)
            self.log.info("Extracted JSON from markdown code block")

        input_data = input_data.strip()

        try:
            return json.loads(input_data)
        except json.JSONDecodeError as e:
            if "Extra data" not in str(e):
                raise
            last_brace = input_data.rfind('}')
            extra = input_data[last_brace+1:]
            self.log.warning(f"Truncated extra data after JSON: {extra[:200]}")
            return json.loads(input_data[:last_brace+1])

