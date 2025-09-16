from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import threading
from net.web import find_url_with_domain
from net.browser import Browser
from util.tex import compile_to_pdf
from net.assistant import Assistant
from ml.openai import ChatGPT


def setup_logging(dir_path: Path | None = None, level: int = logging.INFO) -> None:
    dir_path = dir_path or Path("target/logs")
    dir_path.mkdir(parents=True, exist_ok=True)
    log_file = dir_path / "app.log"
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == str(log_file) for h in root.handlers):
        root.addHandler(file_handler)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(fmt)
        root.addHandler(stream_handler)


def generate_pdfs() -> None:
    _ = compile_to_pdf("main", Path("resume"), "resume")
    _ = compile_to_pdf("simplecover", Path("letter"), "letter")


def analyze_job_posting(file_path: Path, domain: str = 'ashbyhq.com') -> None:
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    url = find_url_with_domain(html_content, domain)
    print(f"URL: {url}")


def test_browse(url: str) -> None:
    with Browser() as browser:
        browser.go_to(url)
        next_url = browser.get_link_containing("Apply")
        print("URL:", next_url)
        if not next_url:
            return
        browser.go_to(next_url)
        print("Current URL:", browser.page.url)
        apply_url = browser.get_link_containing("Apply")
        print("Apply URL:", apply_url)
        if not apply_url:
            return
        browser.go_to(apply_url)
        browser.save_html()
        print("Input areas:", browser.extract_inputs())


def test_browse_greenhouse(url: str) -> None:
    with Browser() as browser:
        browser.go_to(url)
        print("Current URL:", browser.page.url)
        browser.save_html()
        print("Input areas:", browser.extract_inputs())


def textify_file(path: str) -> None:
    html = Path(path).read_text(encoding='utf-8', errors='ignore')
    print(Assistant().to_text(html))


def demo_llm() -> None:
    # Placeholder URL and question; replace with a real job posting for actual use
    url = "https://wellfound.com/jobs/3418603-founding-engineer"
    question = "Write a cover letter showing my suitability for the role"
    print(Assistant(ChatGPT()).generate_application(url, custom_prompt=question))


if __name__ == "__main__":
    t = threading.current_thread()
    if not t.name or t.name == "MainThread":
        t.name = "main"
    setup_logging()
    demo_llm()
