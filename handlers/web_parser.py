from __future__ import annotations

import logging
import threading

from .handler import Handler
from net.web import get_html
from util.file import html_to_text


def _thread_logger() -> logging.Logger:
    name: str = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class WebParser(Handler[str, str]):
    """Fetches and parses web pages to plaintext."""

    @property
    def log(self) -> logging.Logger:
        return _thread_logger()

    def process(self, url: str) -> str:
        """Fetch URL and convert HTML to plaintext."""
        self.log.info("Fetching URL: %s", url)
        html = get_html(url)
        return html_to_text(html)
