from __future__ import annotations

import logging
import threading
from typing import override

from ml.gpt import GPT
from ml.agent import Agent

from .handler import Handler
from .llm_client import Agent
from net.web import get_html
from util.file import html_to_text


def _thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class WebParser(Handler[str, str]):
    """Fetches and parses web pages to plaintext."""

    def __init__(self, llm: Agent = GPT()):
        self.llm = llm

    @property
    def log(self) -> logging.Logger:
        return _thread_logger()

    def extract_job_description(self, full_text: str) -> str:
        """Extract essential job description from full page text using LLM."""
        if not self.llm:
            return full_text

        prompt = f"Extract only job description text from:\n\n{full_text}"
        self.log.info("Extracting job description using gpt-4o-mini")
        return self.llm.chat(prompt, "gpt-4o-mini", 1024 * 4, 0.3, "low")

    @override
    def process(self, input_data: str) -> str:
        """Fetch URL and convert HTML to plaintext."""
        self.log.info("Fetching URL: %s", input_data)
        html = get_html(input_data)
        full_text = html_to_text(html)
        extracted_text = self.extract_job_description(full_text)
        return extracted_text
