from __future__ import annotations

import logging
import threading
from typing import override

from .handler import Handler
from .llm_client import GPTClient
from ml.llm import LLM, DUMMY_LLM
from net.web import get_html
from util.file import html_to_text


def _thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class WebParser(Handler[str, str]):
    """Fetches and parses web pages to plaintext."""

    def __init__(self, llm: LLM = DUMMY_LLM):
        self.llm = llm

    @property
    def log(self) -> logging.Logger:
        return _thread_logger()

    def extract_job_description(self, full_text: str) -> str:
        """Extract essential job description from full page text using LLM."""
        if self.llm == DUMMY_LLM:
            return full_text

        prompt = f"Extract only job description text from:\n\n{full_text}"
        self.log.info("Extracting job description using gpt-4o-mini")
        gpt_client = GPTClient(self.llm, model="gpt-4o-mini", temperature=0.3, max_tokens=4000)
        return gpt_client.process(prompt)

    @override
    def process(self, input_data: str) -> str:
        """Fetch URL and convert HTML to plaintext."""
        self.log.info("Fetching URL: %s", input_data)
        html = get_html(input_data)
        full_text = html_to_text(html)
        extracted_text = self.extract_job_description(full_text)
        return extracted_text
