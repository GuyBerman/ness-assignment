from __future__ import annotations

import re

from playwright.sync_api import Locator, Page, expect

from ebay_automation.core.base_component import BaseComponent
from ebay_automation.utils.logger import get_logger
from ebay_automation.utils.pacer import Pacer

log = get_logger(__name__)

_RESULTS_URL_RE = re.compile(r"/sch/.*[?&]_nkw=")


class HeaderSearch(BaseComponent):
    """Search box in the eBay header."""

    def __init__(self, page: Page, pace_ms: int = 0) -> None:
        super().__init__(page, page.locator("header, #gh").first)
        self._pace_ms = pace_ms

    @property
    def input(self) -> Locator:
        # <input id="gh-ac" name="_nkw" role="combobox" aria-label="Search for anything">
        return (
            self.page.get_by_role("combobox", name="Search for anything")
            .or_(self.page.locator("input[name='_nkw']"))
            .first
        )

    @property
    def submit_button(self) -> Locator:
        # <button id="gh-search-btn">Search</button>
        return (
            self.page.locator("#gh-search-btn")
            .or_(self.page.get_by_role("button", name="Search", exact=True))
            .first
        )

    def is_available(self) -> bool:
        return self.input.count() > 0 and self.input.is_visible()

    def search(self, query: str, attempts: int = 2) -> None:
        """Type the query and submit. eBay sometimes clears the box while the page is still loading,
        so the value and the result URL are checked, and the search is retried once.
        """
        for attempt in range(1, attempts + 1):
            self.page.wait_for_load_state("load")
            self.input.fill(query)
            expect(self.input).to_have_value(query)
            Pacer.pace(self.page, self._pace_ms)
            self.submit_button.click()
            self.page.wait_for_load_state("domcontentloaded")
            if _RESULTS_URL_RE.search(self.page.url):
                return
            log.warning("Search attempt %d landed on %s (query lost) - retrying", attempt, self.page.url)
        raise AssertionError(f"Search for {query!r} did not reach a results page (at {self.page.url})")
