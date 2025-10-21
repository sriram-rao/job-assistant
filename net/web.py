from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from http.client import HTTPResponse
from email.message import Message
from typing import cast
from playwright.sync_api import Page, Frame, Locator


USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) Gecko/20100101 Firefox/142.0"

# Platform catalog: indicators + extraction rules
PLATFORMS: dict[str, dict[str, list[str] | dict[str, str]]] = {
    "greenhouse": {
        "url": ["greenhouse.io", "boards.greenhouse.io"],
        "text": ["grnhse"],
        "extract": {},
    },
    "lever": {
        "url": ["jobs.lever.co", "lever.co"],
        "text": ["lever"],
        "extract": {},
    },
    "workday": {
        "url": ["myworkdayjobs.com"],
        "text": ["/wday/cxs/", "workday"],
        "extract": {},
    },
    "smartrecruiters": {
        "url": ["smartrecruiters.com"],
        "text": ["smartrecruiters"],
        "extract": {},
    },
    "workable": {
        "url": ["workable.com", "apply.workable.com"],
        "text": ["workable"],
        "extract": {},
    },
    "ashbyhq": {
        "url": ["ashbyhq.com"],
        "text": ["ashbyprd.com", "recaptchapublicsitekey"],
        "extract": {
            "form_id": r'"sourceFormDefinitionId"\s*:\s*"([a-f0-9-]{10,})"',
            "recaptcha_site_key": r'"recaptchaPublicSiteKey"\s*:\s*"([^\"]+)"',
        },
    },
}

# Common API/apply path patterns
API_PATH_PATTERNS = [
    r"/api/[^\s\"']+",
    r"/graphql[/?][^\s\"']*",
    r"/wday/cxs/[^\s\"']+",
    r"/embed/job_app[^\s\"']*",
    r"/apply[^\s\"']*",
]


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    return name or "page"


def derive_base_filename(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    tail = (
        Path(parsed.path).name or "index"
        if parsed.path and parsed.path not in ("/", "")
        else "index"
    )
    return sanitize_filename(f"{parsed.netloc}_{tail}" if parsed.netloc else tail)


def fetch(url: str, timeout: float = 20.0) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with cast(
        HTTPResponse, urllib.request.urlopen(req, timeout=timeout)
    ) as http_response:
        data: bytes = http_response.read()
        info: Message = http_response.info()
        encoding: str | None = info.get_content_charset()
        return data, (encoding or "utf-8")


@dataclass
class DownloadResult:
    url: str
    html_path: Path | None
    encoding: str | None


def ensure_dir(dir: Path | str) -> Path:
    directory = Path(dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def resolve_base(basename: str | None, url: str) -> str:
    return sanitize_filename(basename) if basename else derive_base_filename(url)


def save_html_bytes(target: Path, base: str, raw: bytes) -> Path:
    path = target / f"{base}.html"
    _ = path.write_bytes(raw)
    return path


def get_html(url: str, timeout: float = 20.0) -> str:
    """Fetch a URL or read a file path and return decoded HTML string."""
    # Check if it's an HTTP/HTTPS URL
    if url.startswith(("http://", "https://")):
        raw, encoding = fetch(url, timeout=timeout)
        try:
            return raw.decode(encoding or "utf-8", errors="replace")
        except Exception:
            return raw.decode("utf-8", errors="replace")

    # Handle file:// URLs by removing the prefix and decoding
    if url.startswith("file://"):
        url = urllib.parse.unquote(url[7:])

    # Treat as a local file path
    path = Path(url)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        # Try reading as bytes and decode
        raw = path.read_bytes()
        return raw.decode("utf-8", errors="replace")


def download_page(
    url: str,
    target_dir: Path | str | None = None,
    basename: str | None = None,
) -> Path:
    """Fetch HTML then save to file; return saved Path."""
    target = ensure_dir(target_dir or Path("target"))
    base = resolve_base(basename, url)
    try:
        html = get_html(url)
        path = target / f"{base}.html"
        _ = path.write_text(html, encoding="utf-8")
        return path
    except Exception as e:
        print(f"Failed to download or save {url}: {e}", file=sys.stderr)
        return target / f"{base}.html"


# URL: https://jobs.ashbyhq.com/snowflake/3eb872af-0ab1-4986-8f72-e7321fcd1538
def find_url_with_domain(html: str, domain: str) -> str | None:
    """Find a URL with the given domain in HTML content."""
    # Try multiple patterns to match different URL formats
    patterns = [
        rf"https?://(?:www\.)?{domain}/[\w-]+",  # Matches http(s)://domain.com/...
        rf'"(https?://[\w.-]*{domain}[\w/%-]*)',  # Matches URLs in quotes
        rf'url\(["\']?(https?://[\w.-]*{domain}[\w/%-]*)',  # Matches CSS url() patterns
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if not match:
            continue

        # Get the first group if it exists, otherwise get the full match
        url = match.group(1) if len(match.groups()) > 0 else match.group(0)
        # Clean up any trailing quotes or special characters
        url = url.split('"')[0].split("'")[0].split(")")[0]
        return url

    return None


def placeholder_for(field: dict[str, str]) -> str:
    ftype = (field.get("type") or "").lower()
    name = (field.get("name") or "").lower()
    if ftype == "email" or "email" in name:
        return "me@example.com"
    if ftype in ("tel", "phone") or "phone" in name:
        return "+1-555-123-4567"
    if "linkedin" in name:
        return "https://www.linkedin.com/in/your-handle"
    if "github" in name:
        return "https://github.com/your-handle"
    if "url" in name or "website" in name:
        return "https://example.com"
    if ftype == "file":
        return ""  # handled via files payload
    return "Lorem ipsum"


def build_payload(
    fields: list[dict[str, str]],
) -> tuple[dict[str, str], dict[str, tuple[str, bytes, str]]]:
    """
    Return (data, files) suitable for requests.post(url, data=data, files=files).
    - data: regular form fields
    - files: {name: (filename, content_bytes, content_type)}
    """
    data: dict[str, str] = {}
    files: dict[str, tuple[str, bytes, str]] = {}
    radio_groups: dict[str, list[dict[str, str]]] = defaultdict(list)

    for field in fields:
        name = field.get("name") or ""
        if not name:
            continue
        ftype = (field.get("type") or "").lower()

        if ftype == "file":
            # Placeholder 1-byte PDF; replace with real file content
            files[name] = ("resume.pdf", b"%PDF-1.4\n", "application/pdf")
        elif ftype == "checkbox":
            # Include only if you want checked; default unchecked
            # data[name] = "on"
            continue
        elif ftype == "radio":
            radio_groups[name].append(field)
        else:
            data[name] = placeholder_for(field)

    # Choose first option per radio group by default
    for name, options in radio_groups.items():
        if options:
            data[name] = "on"

    return data, files


def wait_until_ready(page: Page, *, timeout_ms: int) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        pass


def to_field(element: Locator) -> dict[str, object] | None:
    name = (
        element.get_attribute("name")
        or element.get_attribute("id")
        or element.get_attribute("aria-label")
    )

    return (
        {
            "name": name,
            "type": (
                element.get_attribute("type")
                or element.evaluate("e => e.tagName.toLowerCase()")
            ),
            "label": element.evaluate(
                "el => (el.labels && el.labels[0] && el.labels[0].innerText) || ''"
            ),
            "placeholder": element.get_attribute("placeholder"),
            "required": (
                element.evaluate("e => !!e.required")
                or ((element.get_attribute("aria-required") or "").lower() == "true")
                or element.get_attribute("required")
            ),
            "tag": element.evaluate("e => e.tagName.toLowerCase()"),
            "value": (
                element.get_attribute("value") or element.evaluate("e => e.value")
            ),
            "checked": (
                (
                    (
                        element.get_attribute("type")
                        or element.evaluate("e => e.tagName.toLowerCase()")
                    )
                    in ("checkbox", "radio")
                )
                and element.evaluate("e => !!e.checked")
            ),
            "options": element.evaluate(
                "el => el.tagName.toLowerCase()==='select' ? Array.from(el.options).map(o => ({value:o.value, label:o.label||o.textContent||'', selected:!!o.selected})) : null"
            ),
        }
        if name
        else None
    )


def collect_from_scope(
    scope: Page | Frame, *, selector: str
) -> list[dict[str, object]]:
    return list(filter(None, map(to_field, scope.locator(selector).all())))


def collect_fields_from_page(
    page: Page, *, timeout_ms: int = 60_000
) -> list[dict[str, object]]:
    wait_until_ready(page, timeout_ms=timeout_ms)
    selector = ":light(input), :light(textarea), :light(select)"
    fields: list[dict[str, object]] = []
    for scope in [page, *page.frames]:
        try:
            fields.extend(collect_from_scope(scope, selector=selector))
        except Exception:
            continue
    return fields


def parse_submit_hints_from_html(html: str, base_url: str = "") -> dict[str, object]:
    """Extract generic submit hints for SPA job pages (no <form> tags)."""

    def detect_platform(url: str, text: str) -> str | None:
        url = url.lower()
        text = text.lower()
        # Prefer URL/domain indicators over text tokens
        url_matches: list[tuple[int, str]] = []
        for platform, config in PLATFORMS.items():
            indicators: list[str] | dict[str, str] = [
                u for u in config.get("url", []) if u in url
            ]
            if indicators:
                # score by longest matching indicator to reduce false positives
                url_matches.append((max(map(len, indicators)), platform))
        if url_matches:
            url_matches.sort(reverse=True)
            return url_matches[0][1]
        # Fallback to text-based indicators
        for platform, config in PLATFORMS.items():
            if any(token in text for token in config.get("text", [])):
                return platform
        return None

    def find_paths(text: str, patterns: list[str]) -> list[str]:
        return [
            match.group(0)
            for pattern in patterns
            for match in re.finditer(pattern, text, re.I)
        ]

    platform = detect_platform(base_url, html) or "generic"

    # Initialize hints with base and platform information
    hints: dict[str, object] = {"apply_page": base_url, "platform": platform}

    # Platform-specific signals (data-driven)
    extract = cast(dict[str, str], PLATFORMS.get(platform, {}).get("extract", {}))
    hints.update(
        {
            key: match.group(1)
            for key, pattern in extract.items()  # type: ignore[union-attr]
            if (match := re.search(pattern, html, re.I))
        }
    )

    # Common API/apply paths
    hints["api_hints"] = sorted(set(find_paths(html, API_PATH_PATTERNS)))

    # Inline apply link
    if apply_match := re.search(
        r"href=[\"\']([^\"\']*apply[^\"\']*)[\"\']", html, re.I
    ):
        hints["apply_link"] = apply_match.group(1)
    return hints
