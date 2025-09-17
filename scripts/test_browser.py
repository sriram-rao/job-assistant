# login_once.py
from playwright.sync_api import sync_playwright
import json
import os

OUT = os.path.expanduser("~/.wellfound_session.json")

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        "./pf",
        headless=False,
        executable_path="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
    )
    page = ctx.new_page()
    _ = page.goto("https://wellfound.com/login")
    print("Log in in the visible browser, then press Enter here…")
    _ = input()

    # optional: wait for a logged-in signal
    # page.wait_for_selector('text=/Profile|Logout|Sign out/i', timeout=15000)

    ua = page.evaluate("() => navigator.userAgent")
    cookies = ctx.cookies()  # all domains in this context

    with open(OUT, "w") as f:
        json.dump({"ua": ua, "cookies": cookies}, f, indent=2)

    print(f"Saved session -> {OUT}")
