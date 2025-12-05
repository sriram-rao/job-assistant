from __future__ import annotations

import logging
import threading
from typing import override

from ml.gpt import GPT
from ml.agent import Agent
from config import EXTRACTION_MODEL, EXTRACTION_MAX_TOKENS, EXTRACTION_TEMPERATURE, JOB_LISTING_CACHE_DIR

from .handler import Handler
from net.web import get_html, sanitize_filename
from util.file import html_to_text


def _thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class WebParser(Handler[str, str]):
    """Fetches and parses web pages to plaintext."""

    def __init__(self, llm: Agent | None = None):
        self.llm: Agent = llm or GPT()

    @property
    @override
    def log(self) -> logging.Logger:
        return _thread_logger()

    def extract_job_listing(self, full_text: str, model: str = EXTRACTION_MODEL) -> str:
        """Extract essential job listing from full page text using LLM."""
        if not self.llm:
            return full_text

        prompt = f"Extract only job listing text from:\n\n{full_text}"
        self.log.info(f"Extracting job listing using {model}")
        return self.llm.chat(prompt, model, EXTRACTION_MAX_TOKENS, EXTRACTION_TEMPERATURE, "low")

    def get_cached_job_listing(self, url: str) -> str | None:
        """Get cached job listing text if it exists."""
        cache_name = sanitize_filename(url)
        cache_file = JOB_LISTING_CACHE_DIR / f"{cache_name}.txt"
        self.log.info(f"Checking cache file: {cache_file}")
        if not cache_file.exists():
            self.log.info("Cache file does not exist")
            return None
        self.log.info("Cache file found")
        return cache_file.read_text(encoding="utf-8")

    def save_job_listing_to_cache(self, url: str, job_listing: str) -> None:
        """Save job listing text to cache."""
        JOB_LISTING_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_name = sanitize_filename(url)
        cache_file = JOB_LISTING_CACHE_DIR / f"{cache_name}.txt"
        cache_file.write_text(job_listing, encoding="utf-8")

    @override
    def process(self, input_data: str) -> str:
        """Fetch URL and convert HTML to plaintext."""
        self.log.info("Fetching URL: %s", input_data)

        # Check cache first
        if cached := self.get_cached_job_listing(input_data):
            self.log.info("Using cached job listing (no tokens used)")
            return cached

        html = get_html(input_data)
        full_text = html_to_text(html)
        extracted_text = self.extract_job_listing(full_text)

        # Save to cache
        self.save_job_listing_to_cache(input_data, extracted_text)

        return extracted_text
