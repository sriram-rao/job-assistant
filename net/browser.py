from __future__ import annotations

from typing import List, Tuple, Dict
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright
from pathlib import Path
from .web import collect_fields_from_page, build_payload, parse_submit_hints_from_html
from .form import values_from_defaults

# Common selectors (DRY)
SUBMIT_SELECTOR = "input[type=submit], button[type=submit]"
APPLY_SELECTOR = (
    "button:has-text('Submit'), button:has-text('Apply'), "
    "a:has-text('Submit'), a:has-text('Apply'), "
    f"{SUBMIT_SELECTOR}"
)
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
        results: List[Tuple[str, str]] = []
        for anchor in anchors:
            text = (anchor.inner_text() or "").strip()
            url = anchor.get_attribute("href") or ""
            if url:
                results.append((text, url))
        return results

    def find_link_by_text(self, link_text: str, *, exact: bool = False):
        return (
            self.page.get_by_role("link", name=link_text)
            if exact
            else self.page.locator("a", has_text=link_text)
        )

    def get_link_containing(self, link_text: str, *, exact: bool = False) -> str | None:
        locator = self.find_link_by_text(link_text, exact=exact)
        if locator.count() == 0:
            return None
        url = locator.first.get_attribute("href") or ""
        return urljoin(self.page.url, url) if url else None

    def click_link_with_text(self, link_text: str, *, exact: bool = False, timeout_ms: int = 30_000) -> str:
        url = self.get_link_containing(link_text, exact=exact)
        if not url:
            return ""
        self.go_to(url, wait_until="networkidle", timeout_ms=timeout_ms)
        return self.page.url

    # Backward-compatible alias
    def click_link_containing(self, link_text: str, *, exact: bool = False, timeout_ms: int = 30_000) -> str:
        return self.click_link_with_text(link_text, exact=exact, timeout_ms=timeout_ms)

    def extract_labels(self) -> List[str]:
        return [t.strip() for t in self.page.locator("label").all_text_contents() if t.strip()]

    def extract_inputs(self, *, timeout_ms: int = 30_000) -> List[Dict[str, str]]:
        """Thin wrapper delegating to net.web.collect_fields_from_page."""
        return collect_fields_from_page(self.page, timeout_ms=timeout_ms)

    def fill_fields(self, values: Dict[str, object]) -> None:
        for key, val in values.items():
            sel = (
                f":is(input:not([type=hidden]), textarea, select)[name='{key}'],"
                f":is(input:not([type=hidden]), textarea, select)[id='{key}'],"
                f":is(input:not([type=hidden]), textarea, select)[aria-label='{key}']"
            )
            locator = self.page.locator(sel)
            if locator.count() == 0:
                continue
            loc = locator.first
            tag = (loc.evaluate("e => e.tagName.toLowerCase()") or "").lower()
            typ = (loc.get_attribute("type") or "").lower()

            if typ == "file":
                paths = [str(v) for v in val] if isinstance(val, (list, tuple)) else ([str(val)] if val else [])
                if paths:
                    loc.set_input_files(paths)
                continue

            if typ in ("checkbox", "radio"):
                if isinstance(val, bool):
                    suppress_errors(lambda: (loc.check if val else loc.uncheck)())
                continue

            (val is not None) and ((loc.select_option if tag == "select" else loc.fill)(str(val)))

    
    def fill_with_defaults(self, *, timeout_ms: int = 60_000) -> Dict[str, object]:
        fields = self.extract_inputs(timeout_ms=timeout_ms)
        values = values_from_defaults(fields)
        if values:
            self.fill_fields(values)
        return values
    
    def __submit_form__(self, *, wait_until: str, timeout_ms: int) -> str:
        # 1) Click an obvious submit/apply control
        submit = self.page.locator(SUBMIT_SELECTOR)
        if submit.count() == 0:
            submit = self.page.locator(APPLY_SELECTOR)
        if submit.count() > 0:
            with self.page.expect_navigation(wait_until=wait_until, timeout=timeout_ms):
                submit.first.click()
            return self.page.url

        # 2) Programmatic submit on first form
        forms = self.page.locator("form")
        if forms.count() == 0:
            return self.page.url
        forms.first.evaluate("el => el.submit()")
        return self.page.wait_for_load_state(wait_until, timeout=timeout_ms)


    def submit_form(self, *, wait_until: str = "networkidle", timeout_ms: int = 60_000) -> str:
        return suppress_errors(lambda: self.__submit_form__(wait_until=wait_until, timeout_ms=timeout_ms))

    def extract_form_submit_info(self) -> Dict[str, object]:
        forms = self.page.locator("form")
        if forms.count() == 0:
            return {
                "action": self.page.url,
                "method": "GET",
                "enctype": "application/x-www-form-urlencoded",
                "submit_buttons": [],
            }
        form = forms.first
        action = form.get_attribute("action") or ""
        method = (form.get_attribute("method") or "GET").upper()
        enctype = form.get_attribute("enctype") or "application/x-www-form-urlencoded"
        submits = []
        for el in form.locator(SUBMIT_SELECTOR).all():
            name = el.get_attribute("name") or ""
            value = el.get_attribute("value") or (el.inner_text() or "").strip()
            submits.append({"name": name, "value": value})
        return {
            "action": urljoin(self.page.url, action) if action else self.page.url,
            "method": method,
            "enctype": enctype,
            "submit_buttons": submits,
        }

    def build_payload_from_url(
        self,
        url: str,
        *,
        wait_until: str = "networkidle",
        timeout_ms: int = 60_000,
        headless: bool = True,
        engine: str = "chromium",
    ) -> Tuple[Dict[str, str], Dict[str, Tuple[str, bytes, str]], List[Dict], Dict[str, object]]:
        """
        Navigate to the form URL with a headless browser, extract inputs,
        and return (data, files, raw_fields).
        """
        self.go_to(url, wait_until=wait_until, timeout_ms=timeout_ms)
        fields = collect_fields_from_page(self.page, timeout_ms=timeout_ms)
        # Try to find a form; if none, follow an Apply link, else fallback to SPA hints
        submit = self.extract_form_submit_info()
        if not submit["submit_buttons"] and self.get_link_containing("Apply"):
            self.go_to(self.get_link_containing("Apply") or url, wait_until=wait_until, timeout_ms=timeout_ms)
            fields = collect_fields_from_page(self.page, timeout_ms=timeout_ms)
            submit = self.extract_form_submit_info()
        if not submit["submit_buttons"]:
            html = self.page.content()
            submit = {**parse_submit_hints_from_html(html, base_url=self.page.url), **{"submit_buttons": []}}
        data, files = build_payload(fields)
        return data, files, fields, submit


def suppress_errors(func):
    try: 
        return func()
    except Exception:
        pass
