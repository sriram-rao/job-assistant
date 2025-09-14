from __future__ import annotations

from typing import List, Tuple, Dict
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright
from pathlib import Path

class Browser:
    def __init__(self, *, headless: bool = True, engine: str = "chromium") -> None:
        self.playwright = sync_playwright().start()
        launcher = getattr(self.playwright, engine, self.playwright.chromium)
        try:
            self.browser = launcher.launch(headless=headless, args=["--no-sandbox", "--disable-dev-shm-usage"])  
        except Exception:
            # Fallback to WebKit in restricted environments
            self.browser = self.playwright.webkit.launch(headless=headless)
        self.page = self.browser.new_page()

    def __enter__(self) -> "Browser":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        try:
            self.browser.close()
        finally:
            self.playwright.stop()

    def go_to(self, url: str, *, wait_until: str = "domcontentloaded", timeout_ms: int = 30_000) -> None:
        self.page.goto(url, wait_until=wait_until, timeout=timeout_ms)

    def save_html(self, path: Path = Path("target")) -> None:
        ((path / (self.page.url.split("?")[0].split("#")[0].split("/")[-1] + ".html"))
            .write_text(self.page.content()))

    def list_links(self) -> List[Tuple[str, str]]:
        anchors = self.page.locator("a").all()
        results: List[Tuple[str, str]] = [(anchor.inner_text().strip(), 
                                           anchor.get_attribute("href")) for anchor in anchors]
        return [r for r in results if r[1]]

    def get_link_containing(self, link_text: str, *, exact: bool = False) -> str:
        locator = (
            self.page.get_by_role("link", name=link_text) if exact 
            else self.page.locator("a", has_text=link_text)
        )
        url = locator.first.get_attribute("href") if locator.count() > 0 else ""
        return url if url.startswith("http") else \
            (urljoin(self.page.url, url) if url.startswith("/") else "")

    def click_link_with_text(self, link_text: str, *, exact: bool = False, timeout_ms: int = 30_000) -> str:
        self.go_to(
            self.get_link_containing(link_text, exact=exact),
            wait_until="networkidle",
            timeout_ms=timeout_ms
        )
        return self.page.url

    def extract_labels(self) -> List[str]:
        return [t.strip() for t in self.page.locator("label").all_text_contents() if t.strip()]

    def extract_input_elements(self) -> List[Tuple[str, str]]:
        input_areas = self.page.locator("input, textarea, select").all()
        elements: List[Tuple[str, str]] = [(
            area.get_attribute("name") or area.get_attribute("id"),
            area.get_attribute("type") or area.evaluate("e => e.tagName.toLowerCase()" or "")
        ) for area in input_areas]
        return [e for e in elements if e[0]]

    def extract_inputs(self) -> List[Dict[str, str]]:
        # Try to wait for dynamic UI to render
        try:
            self.page.wait_for_load_state("networkidle", timeout=30_000)
            self.page.wait_for_selector(":light(input), :light(textarea), :light(select)", timeout=30_000)
        except Exception:
            pass

        def collect(scope) -> List[Dict[str, str]]:
            elems = scope.locator(":light(input), :light(textarea), :light(select)").all()
            out: List[Dict[str, str]] = []
            for element in elems:
                name = (
                    element.get_attribute("name")
                    or element.get_attribute("id")
                    or element.get_attribute("aria-label")
                    or ""
                )
                if not name:
                    continue
                typ = element.get_attribute("type") or element.evaluate("e => e.tagName.toLowerCase()")
                label = element.evaluate("el => (el.labels && el.labels[0] && el.labels[0].innerText) || ''")
                placeholder = element.get_attribute("placeholder") or ""
                required = "true" if element.get_attribute("required") else "false"
                out.append(
                    {
                        "name": name,
                        "type": (typ or ""),
                        "label": (label or ""),
                        "placeholder": placeholder,
                        "required": required,
                    }
                )
            return out

        fields: List[Dict[str, str]] = collect(self.page)
        for frame in self.page.frames:
            try:
                fields.extend(collect(frame))
            except Exception:
                continue
        return fields
