from __future__ import annotations

from playwright.sync_api import Locator, Page

from ebay_automation.components.header_search import HeaderSearch
from ebay_automation.config.settings import Settings
from ebay_automation.core.base_page import BasePage


class HomePage(BasePage):
    PATH = "/"

    def __init__(self, page: Page, settings: Settings) -> None:
        super().__init__(page, settings)
        self.header_search = HeaderSearch(page, settings.browser.min_navigation_interval_ms)

    @property
    def sign_in_link(self) -> Locator:
        # guest header shows <a href="https://signin.ebay.com/...">Sign in</a>
        return self.page.locator("header a[href*='signin']").filter(has_text="Sign in").first

    @property
    def cart_icon(self) -> Locator:
        # <a class="gh-flyout__target" aria-label="Your shopping cart contains 0 items">
        return self.page.locator("a[aria-label*='shopping cart']").first

    def is_logged_in(self) -> bool:
        return self.sign_in_link.count() == 0

    def cart_count(self) -> int | None:
        if self.cart_icon.count() == 0:
            return None
        label = self.cart_icon.get_attribute("aria-label") or ""
        digits = "".join(ch for ch in label if ch.isdigit())
        return int(digits) if digits else None
