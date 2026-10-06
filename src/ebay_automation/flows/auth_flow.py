from __future__ import annotations

from playwright.sync_api import Page

from ebay_automation.config.settings import Settings
from ebay_automation.core.exceptions import AutomationError
from ebay_automation.pages.home_page import HomePage
from ebay_automation.pages.login_page import LoginPage
from ebay_automation.utils.logger import get_logger
from ebay_automation.utils.reporter import Reporter

log = get_logger(__name__)


class AuthError(AutomationError):
    pass


class AuthFlow:
    """Login. auth.mode is one of:

    guest          no login (eBay allows a guest cart)
    storage_state  session saved with scripts/save_session.py --login
    credentials    EBAY_AUTH__USERNAME / EBAY_AUTH__PASSWORD
    """

    def __init__(self, page: Page, settings: Settings) -> None:
        self.page = page
        self.settings = settings

    @property
    def is_guest(self) -> bool:
        return self.settings.auth.mode == "guest"

    def login(self) -> None:
        mode = self.settings.auth.mode
        with Reporter.step(f"Authenticate (mode={mode})"):
            home = HomePage(self.page, self.settings)
            if mode == "credentials":
                self._login_with_credentials()
            home.open()
            if mode == "guest":
                log.info("Continuing as guest")
                return
            if not home.is_logged_in():
                hint = (
                    "Saved session expired - re-run scripts/save_session.py --login"
                    if mode == "storage_state"
                    else "Login did not complete"
                )
                raise AuthError(hint)
            log.info("Logged in (mode=%s)", mode)

    def _login_with_credentials(self) -> None:
        auth = self.settings.auth
        if not (auth.username and auth.password):
            raise AuthError("auth.mode=credentials requires EBAY_AUTH__USERNAME and EBAY_AUTH__PASSWORD")
        login_page = LoginPage(self.page, self.settings)
        login_page.open()
        login_page.login(auth.username.get_secret_value(), auth.password.get_secret_value())
