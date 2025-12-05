from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import override

from ml.gpt import GPT
from ml.agent import Agent


from .handler import Handler
from config import APPLICATION_MODEL, HANDLER_MAX_TOKENS, HANDLER_TEMPERATURE


LLM_LOG_DIR = Path("target/logs")
LLM_CACHE_FILE = LLM_LOG_DIR / "last_llm_response.txt"
LLM_DEBUG_FILE = LLM_LOG_DIR / "llm_response_debug.txt"


def thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class LLMHandler(Handler[str, str]):
    def __init__(
        self,
        llm: Agent | None = None,
        model: str = APPLICATION_MODEL,
        max_tokens: int = HANDLER_MAX_TOKENS,
        temperature: float = HANDLER_TEMPERATURE,
        reasoning_effort: str = "low",
        system_prompt: str = ""
    ) -> None:
        self.model: str = model
        self.max_tokens: int = max_tokens
        self.temperature: float = temperature
        self.reasoning_effort: str = reasoning_effort
        self.llm: Agent = llm or GPT(model, system_prompt)

    @property
    @override
    def log(self) -> logging.Logger:
        return thread_logger()

    def read_cached_llm_output(self) -> str | None:
        if not LLM_CACHE_FILE.exists():
            return None
        return LLM_CACHE_FILE.read_text(encoding="utf-8")

    def write_cached_llm_output(self, raw_output: str) -> None:
        LLM_LOG_DIR.mkdir(parents=True, exist_ok=True)
        _ = LLM_CACHE_FILE.write_text(raw_output, encoding="utf-8")

    @override
    def process(self, input_data: str) -> str:
        """Send prompt to LLM and return response."""
        self.log.info("Calling LLM.chat_full, model=%s", self.model or APPLICATION_MODEL)
        prompt = input_data
        res = self.llm.chat_full([{"role": "user", "content": prompt}], self.model, self.max_tokens, self.temperature, self.reasoning_effort)
        self.write_cached_llm_output(res[0])
        return res[0]


