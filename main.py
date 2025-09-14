from pathlib import Path
from typing import Optional
import re
import sys

from util.tex import compile_to_pdf
from util.web import find_url_with_domain
from util.browser import Browser

def generate_pdfs():
    compile_to_pdf("main", Path("resume"), "resume")
    compile_to_pdf("simplecover", Path("letter"), "letter")


def analyze_job_posting(file_path: Path, domain: str = 'ashbyhq.com') -> None:
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()           
    url = find_url_with_domain(html_content, domain)
    print(f"URL: {url}")


def test_browse(url: str) -> None:
    with Browser() as browser:
        browser.go_to(url)
        url = browser.get_link_containing("Apply")
        print("URL:", url)
        browser.go_to(url)
        print("Current URL:", browser.page.url)
        apply_url = browser.get_link_containing("Apply")
        print("Apply URL:", apply_url)
        browser.save_html()
        print("Input areas:", browser.extract_inputs())


if __name__ == "__main__":
    test_browse("https://careers.snowflake.com/us/en/job/SNCOUSDD524B932E4E4E3B84B44684A46E9148EXTERNALENUS3EB872AF0AB149868F72E7321FCD1538/Software-Engineer-Backend")
