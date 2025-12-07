from __future__ import annotations

import logging
import threading
from typing import Literal, override

from .handler import Handler
from net.browser import Browser


wait_until_literal = Literal["commit", "domcontentloaded", "load", "networkidle"]

def thread_logger() -> logging.Logger:
    name = f"{__name__}.{threading.current_thread().name}"
    return logging.getLogger(name)


class BrowserLoader(Handler[str, Browser]):
    """Open a page once and hand back the live Browser."""

    def __init__(
        self,
        *,
        headless: bool = True,
        wait_until: wait_until_literal = "domcontentloaded",
        timeout_ms: int = 30_000,
        executable_path: str | None = None,
        user_data_dir: str | Path | None = None,
    ) -> None:
        self.headless: bool = headless
        self.wait_until: wait_until_literal = wait_until
        self.timeout_ms: int = timeout_ms
        self.executable_path = executable_path
        self.user_data_dir = user_data_dir

    @property
    @override
    def log(self) -> logging.Logger:
        return thread_logger()

    @override
    def process(self, input_data: str) -> Browser:
        browser = Browser(
            headless=self.headless,
            executable_path=self.executable_path,
            user_data_dir=self.user_data_dir,
        )
        self.log.info("Opening page: %s", input_data)
        browser.go_to(input_data, wait_until=self.wait_until, timeout_ms=self.timeout_ms)
        return browser
