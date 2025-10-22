from __future__ import annotations

import logging
import threading
from pathlib import Path

from .handler import Handler
from ml.llm import DUMMY_LLM, LLM, to_request
from settings import OPENAI_MODEL, REASONING_EFFORT


LLM_LOG_DIR = Path("target/logs")
LLM_CACHE_FILE = LLM_LOG_DIR / "last_llm_response.txt"


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class LLMClient(Handler[str, str]):
    """Handles LLM communication and caching."""

    def __init__(
        self,
        llm: LLM = DUMMY_LLM,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self.llm = llm
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort

    @property
    def log(self) -> logging.Logger:
        return thread_logger()

    def read_cached_llm_output(self) -> str | None:
        if not LLM_CACHE_FILE.exists():
            return None
        return LLM_CACHE_FILE.read_text(encoding="utf-8")

    def write_cached_llm_output(self, raw_output: str) -> None:
        LLM_LOG_DIR.mkdir(parents=True, exist_ok=True)
        LLM_CACHE_FILE.write_text(raw_output, encoding="utf-8")

    def process(self, prompt: str) -> str:
        """Send prompt to LLM and return response."""
        req = to_request(
            prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            reasoning_effort=self.reasoning_effort or REASONING_EFFORT,
        )
        self.log.info("Calling LLM.chat, model=%s", self.model or OPENAI_MODEL)
        res = self.llm.chat(req)
        if not res.choices:
            self.log.error("LLM returned no content, see logs for provider call details")
            raise RuntimeError("LLM returned no choices/content")
        return res.choices[0].content
