from pathlib import Path
import sys

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from application_pipeline import autofill_form, open_browser_for


def main() -> None:
    url = "https://www.google.com"
    browser = open_browser_for(url, False, "load", 15000)

    autofill_form(
        browser,
        values={"q": "job assistant autofill test"},
        snapshot=Path("target/google_autofill_snapshot.html"),
        wait_until="load",
        timeout_ms=15000,
    )

    input("Filled search box. Review in the browser, then press Enter to exit...")
    browser.close()


if __name__ == "__main__":
    main()
