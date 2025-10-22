from __future__ import annotations

import json
import logging
import re
import threading

from .handler import Handler


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class LLMResponseParser(Handler[str, dict[str, object]]):
    """Parses LLM responses to extract application JSON."""

    @property
    def log(self) -> logging.Logger:
        return thread_logger()

    def process(self, raw_response: str) -> dict[str, object]:
        """Parse raw LLM response and extract application JSON."""
        self.log.info(f"Raw LLM response (first 500 chars): {raw_response[:500]}")

        # Strip reasoning output (for models like GPT-OSS, DeepSeek-R1)
        raw_response = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL)

        # Strip markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw_response, re.DOTALL)
        if json_match:
            raw_response = json_match.group(1)
            self.log.info("Extracted JSON from markdown code block")

        raw_response = raw_response.strip()
        return json.loads(raw_response)
