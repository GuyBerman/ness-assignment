from __future__ import annotations

from playwright.sync_api import Locator, Page

from ebay_automation.core.base_component import BaseComponent
from ebay_automation.utils.pacer import Pacer


class Pagination(BaseComponent):
    """Paging on the search results page."""

    def __init__(self, page: Page, pace_ms: int = 0) -> None:
        super().__init__(page, page.locator("nav.pagination, .s-pagination").first)
        self._pace_ms = pace_ms

    @property
    def next_link(self) -> Locator:
        return self.page.locator("a.pagination__next").first

    def has_next(self) -> bool:
        link = self.next_link
        if link.count() == 0 or not link.is_visible():
            return False
        return link.get_attribute("aria-disabled") != "true" and bool(link.get_attribute("href"))

    def go_next(self) -> None:
        previous_url = self.page.url
        Pacer.pace(self.page, self._pace_ms)
        self.next_link.click()
        self.page.wait_for_url(lambda url: url != previous_url)
        self.page.wait_for_load_state("domcontentloaded")
