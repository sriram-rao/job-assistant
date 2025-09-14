from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re
import sys
import urllib.parse
import urllib.request


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    return name or "page"


def derive_base_filename(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    tail = Path(parsed.path).name or "index" if parsed.path and parsed.path not in ("/", "") else "index"
    return sanitize_filename(f"{parsed.netloc}_{tail}" if parsed.netloc else tail)


def fetch(url: str, timeout: float = 20.0) -> tuple[bytes, Optional[str]]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        encoding = resp.headers.get_content_charset()  # type: ignore[attr-defined]
        return data, (encoding or "utf-8")


@dataclass
class DownloadResult:
    url: str
    html_path: Optional[Path]
    encoding: Optional[str]


def ensure_dir(dir: Path | str) -> Path:
    directory = Path(dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def resolve_base(basename: Optional[str], url: str) -> str:
    return sanitize_filename(basename) if basename else derive_base_filename(url)


def save_html_bytes(target: Path, base: str, raw: bytes) -> Path:
    path = target / f"{base}.html"
    path.write_bytes(raw)
    return path


def download_page(
    url: str,
    target_dir: Path | str = Path("target"),
    basename: Optional[str] = None,
    save_html: bool = True,
) -> DownloadResult:
    target = ensure_dir(target_dir)
    base = resolve_base(basename, url)

    try:
        raw, encoding = fetch(url)
        html_path = save_html_bytes(target, base, raw) if save_html else None
    except Exception as e:
        print(f"Failed to download or save {url}: {e}", file=sys.stderr)
        return DownloadResult(url=url, html_path=None, encoding=None)

    return DownloadResult(url=url, html_path=html_path, encoding=encoding)
