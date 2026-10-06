from __future__ import annotations

import re
import sys
from typing import Literal

from playwright.sync_api import Locator, Page

from ebay_automation.core.exceptions import BotChallengeError
from ebay_automation.utils.logger import get_logger
from ebay_automation.utils.waits import wait_until

log = get_logger(__name__)

BlockKind = Literal["challenge", "blocked"]

# eBay bot pages:
#   challenge - /splashui/challenge, title "Pardon Our Interruption..."
#   blocked   - title "Error Page | eBay" ("SORRY - Something went wrong on our end")
_CHALLENGE_TITLE_RE = re.compile(r"pardon our interruption|security measure|verify yourself", re.I)
_BLOCKED_TITLE_RE = re.compile(r"^error page", re.I)
_CHALLENGE_URL_RE = re.compile(r"/splashui/(challenge|captcha)|/captcha", re.I)
# No check for a captcha iframe: normal result pages also contain a hidden reCAPTCHA iframe.

_HINTS: dict[BlockKind, str] = {
    "challenge": "Solve it in the browser window, or save a session with scripts/save_session.py.",
    "blocked": (
        "eBay blocked the browser. Try again later or from another network, "
        "or save a session with scripts/save_session.py."
    ),
}


def _notify(message: str) -> None:
    """Print to the terminal even when pytest captures output."""
    print(f"\a\n>>> {message}\n", file=sys.__stderr__, flush=True)


class BotGuard:
    """Detects eBay's bot pages.

    On the error page it clicks "Go to homepage" and retries. On a challenge it waits for the
    page to clear, or for a person to solve it. Raises BotChallengeError if it doesn't clear.
    """

    def __init__(
        self,
        page: Page,
        wait_for_human_ms: int = 0,
        reload_retries: int = 2,
        backoff_ms: int = 5_000,
        auto_clear_ms: int = 20_000,
    ) -> None:
        self._page = page
        self._wait_ms = wait_for_human_ms
        self._reload_retries = reload_retries
        self._backoff_ms = backoff_ms
        self._auto_clear_ms = auto_clear_ms

    def detect(self) -> BlockKind | None:
        if _CHALLENGE_URL_RE.search(self._page.url):
            return "challenge"
        try:
            title = self._page.title()
        except Exception:  # page mid-navigation
            return None
        if _BLOCKED_TITLE_RE.search(title):
            return "blocked"
        if _CHALLENGE_TITLE_RE.search(title):
            return "challenge"
        return None

    def is_challenged(self) -> bool:
        return self.detect() is not None

    def check(self) -> bool:
        """Return True if a bot page was shown and then cleared."""
        kind = self.detect()
        if kind is None:
            return False
        if kind == "blocked":
            kind = self._recover_from_error_page()
        if kind == "challenge":
            kind = self._let_challenge_finish()
        if kind and self._wait_ms > 0:
            kind = self._wait_for_human(kind)
        if kind:
            raise BotChallengeError(f"eBay {kind} page at {self._page.url}. {_HINTS[kind]}")
        return True

    @property
    def _go_home_link(self) -> Locator:
        # <a class="fake-btn" href="https://www.ebay.com">Go to homepage</a>
        return self._page.get_by_role("link", name="Go to homepage")

    def _recover_from_error_page(self) -> BlockKind | None:
        """Click "Go to homepage", then go back to the original URL. Reload if there is no button."""
        target = self._page.url
        for attempt in range(1, self._reload_retries + 1):
            delay_ms = self._backoff_ms * attempt
            if self._go_home_link.count():
                log.warning(
                    "eBay 'Error Page' - clicking 'Go to homepage' (%d/%d)", attempt, self._reload_retries
                )
                self._go_home_link.click()
                self._page.wait_for_load_state("domcontentloaded")
                if self.detect() is None:
                    self._page.wait_for_timeout(delay_ms)  # pause before asking for the page again
                    self._page.goto(target, wait_until="domcontentloaded")
            else:
                log.warning(
                    "eBay 'Error Page' - reload %d/%d in %ss", attempt, self._reload_retries, delay_ms // 1000
                )
                self._page.wait_for_timeout(delay_ms)
                self._page.reload(wait_until="domcontentloaded")
            if (kind := self.detect()) != "blocked":
                return kind
        return "blocked"

    def _let_challenge_finish(self) -> BlockKind | None:
        """The challenge page usually redirects back by itself after a few seconds."""
        log.warning("eBay challenge page - waiting up to %ss for it to clear", self._auto_clear_ms // 1000)
        try:
            wait_until(self._page, lambda: self.detect() is None, self._auto_clear_ms, "challenge to clear")
        except TimeoutError:
            return self.detect()
        self._page.wait_for_load_state("domcontentloaded")
        log.info("Challenge cleared by itself - continuing")
        return None

    def _wait_for_human(self, kind: BlockKind) -> BlockKind | None:
        seconds = self._wait_ms // 1000
        _notify(
            f"eBay {kind} page in the browser window. Solve it within {seconds}s and the test will continue."
        )
        try:
            wait_until(self._page, lambda: self.detect() is None, self._wait_ms, "bot page to clear")
        except TimeoutError:
            return self.detect()
        self._page.wait_for_load_state("domcontentloaded")
        log.info("Bot page cleared - continuing")
        return None
