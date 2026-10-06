"""Open Chrome so you can pass eBay's check (or sign in) by hand, then save the session
for the tests to reuse.

    python scripts/save_session.py           # saves auth/session.json
    python scripts/save_session.py --login   # saves auth/storage_state.json
"""

from __future__ import annotations

import argparse

from playwright.sync_api import sync_playwright

from ebay_automation.config.settings import get_settings
from ebay_automation.core.bot_guard import BotGuard


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--login", action="store_true", help="sign in manually and save a logged-in session")
    args = parser.parse_args()

    settings = get_settings()
    target = settings.resolve(
        settings.auth.storage_state_path if args.login else settings.auth.session_state_path
    )
    target.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel=settings.browser.channel)
        context = browser.new_context(
            locale=settings.browser.locale,
            viewport={"width": settings.browser.viewport_width, "height": settings.browser.viewport_height},
        )
        page = context.new_page()
        page.goto("https://signin.ebay.com/" if args.login else settings.base_url)
        action = "sign in" if args.login else "make sure the eBay home page is shown (solve any challenge)"
        if BotGuard(page).detect() == "blocked":
            print("\neBay shows its error page. Try again later or from another network.")
        input(f"\nIn the browser window: {action}. Then press Enter here to save the session... ")
        if BotGuard(page).detect():
            print("eBay still shows a bot page, so this session won't help.")
        context.storage_state(path=str(target))
        browser.close()
    print(f"Saved session to {target}")


if __name__ == "__main__":
    main()
