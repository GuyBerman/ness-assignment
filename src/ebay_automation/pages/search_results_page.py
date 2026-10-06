from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

from ebay_automation.components.header_search import HeaderSearch
from ebay_automation.components.pagination import Pagination
from ebay_automation.components.price_filter import PriceFilter
from ebay_automation.components.result_card import CARDS_XPATH, FEWER_WORDS_DIVIDER, ResultCard
from ebay_automation.config.settings import Settings
from ebay_automation.core.base_page import BasePage
from ebay_automation.utils.url_utils import with_query_params


class SearchResultsPage(BasePage):
    PATH = "/sch/i.html"

    def __init__(self, page: Page, settings: Settings) -> None:
        super().__init__(page, settings)
        pace_ms = settings.browser.min_navigation_interval_ms
        self.header_search = HeaderSearch(page, pace_ms)
        self.price_filter = PriceFilter(page, pace_ms)
        self.pagination = Pagination(page, pace_ms)

    @property
    def results_list(self) -> Locator:
        # <ul class="srp-results srp-grid clearfix">
        return self.page.locator("ul.srp-results").first

    @property
    def no_results_banner(self) -> Locator:
        # <div class="srp-save-null-search">No exact matches found</div>
        # eBay still lists unrelated items on this page, so no cards are returned.
        return self.page.locator(".srp-save-null-search").first

    @property
    def results_heading(self) -> Locator:
        # <h1 class="srp-controls__count-heading">18 results for ...</h1>
        return self.page.locator("h1.srp-controls__count-heading").first

    @property
    def fewer_words_divider(self) -> Locator:
        return self.page.locator(f"xpath=//ul[contains(@class,'srp-results')]/{FEWER_WORDS_DIVIDER}")

    def wait_loaded(self) -> None:
        super().wait_loaded()
        self.results_list.or_(self.no_results_banner).first.wait_for()

    def has_no_exact_matches(self) -> bool:
        if self.no_results_banner.count() and self.no_results_banner.is_visible():
            return True
        heading = self.results_heading.inner_text() if self.results_heading.count() else ""
        return bool(re.match(r"\s*0 results", heading, re.I))

    def exact_matches_end_here(self) -> bool:
        """True when the remaining results are only "fewer words" matches."""
        return self.has_no_exact_matches() or self.fewer_words_divider.count() > 0

    def cards(self) -> list[ResultCard]:
        """Exact-match result cards on this page (none on a "No exact matches found" page)."""
        if self.has_no_exact_matches():
            return []
        cards = self.page.locator(f"xpath={CARDS_XPATH}")
        return [ResultCard(cards.nth(i)) for i in range(cards.count())]

    def open_search(self, query: str, **params: str | int | None) -> None:
        """Search through the URL (one page load instead of typing and submitting)."""
        self.open(with_query_params(self.url, _nkw=query, **params))

    def apply_url_params(self, **params: str | int | None) -> None:
        """Fallback/extra filters via query string (_udhi, _udlo, LH_BIN...)."""
        self.open(with_query_params(self.page.url, **params))
