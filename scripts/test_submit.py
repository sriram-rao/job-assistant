from pathlib import Path
import sys

# Ensure project root on sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from net.browser import Browser


def main() -> None:
    src = Path("target/6564414.html").resolve()
    url = f"file://{src.as_posix()}"
    out = Path("target/submitted_6564414.html")

    with Browser(headless=True) as b:
        b.go_to(url)
        final_url = b.submit_form(timeout_ms=3000)
        # Save DOM after the submit attempt (likely shows validation)
        out.write_text(b.page.content())
        print("Final URL:", final_url)


if __name__ == "__main__":
    main()

