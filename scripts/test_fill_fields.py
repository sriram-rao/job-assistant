from pathlib import Path
import sys

# Ensure project root on sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from net.browser import Browser


def main() -> None:
    src = Path("target/6564414.html").resolve()
    url = f"file://{src.as_posix()}"
    out = Path("target/filled_6564414.html")
    out_submitted = Path("target/submitted_6564414.html")

    values = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "Email": "ada@example.com",
        "Phone": "+1-555-123-4567",
    }

    with Browser(headless=True) as b:
        b.go_to(url)
        b.fill_fields(values)
        # Snapshot current form values into attributes so they appear in saved HTML
        b.page.evaluate(
            "() => {"
            "document.querySelectorAll('input, textarea').forEach(el => el.setAttribute('value', el.value || ''));"
            "document.querySelectorAll('select').forEach(sel => {"
            "  const v = sel.value; Array.from(sel.options).forEach(o => o.selected = (o.value === v));"
            "});"
            "document.querySelectorAll('input[type=checkbox], input[type=radio]').forEach(el => el.checked ? el.setAttribute('checked','') : el.removeAttribute('checked'));"
            "}"
        )
        out.write_text(b.page.content())

    # Submit without filling (to capture validation state)
    with Browser(headless=True) as b:
        b.go_to(url)
        b.submit_form(timeout_ms=3000)
        out_submitted.write_text(b.page.content())


if __name__ == "__main__":
    main()
