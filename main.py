from pathlib import Path
from tex import compile_to_pdf
from util.web import download_page

def generate_pdfs():
    compile_to_pdf("main", Path("resume"), "resume")
    compile_to_pdf("simplecover", Path("letter"), "letter")


def test_download_google() -> None:
    res = download_page("https://www.google.com")
    print("Saved:", res.html_path, "Encoding:", res.encoding)

if __name__ == "__main__":
    test_download_google()
