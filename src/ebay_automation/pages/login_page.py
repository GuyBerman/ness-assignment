from __future__ import annotations

from playwright.sync_api import Locator, Page

from ebay_automation.config.settings import Settings
from ebay_automation.core.base_page import BasePage


class LoginPage(BasePage):
    """eBay sign-in: email, Continue, password, Sign in."""

    SIGN_IN_URL = "https://signin.ebay.com/ws/eBayISAPI.dll?SignIn"

    def __init__(self, page: Page, settings: Settings) -> None:
        super().__init__(page, settings)

    @property
    def url(self) -> str:
        return self.SIGN_IN_URL

    @property
    def username_input(self) -> Locator:
        return self.page.locator("#userid")

    @property
    def continue_button(self) -> Locator:
        return self.page.locator("#signin-continue-btn")

    @property
    def password_input(self) -> Locator:
        return self.page.locator("#pass")

    @property
    def sign_in_button(self) -> Locator:
        return self.page.locator("#sgnBt")

    def wait_loaded(self) -> None:
        super().wait_loaded()
        self.username_input.wait_for()

    def login(self, username: str, password: str) -> None:
        self.username_input.fill(username)
        self.continue_button.click()
        self.bot_guard.check()  # captcha frequently appears between the two steps
        self.password_input.fill(password)
        self.sign_in_button.click()
        self.page.wait_for_url(lambda url: "signin.ebay.com" not in url)
        self.bot_guard.check()
