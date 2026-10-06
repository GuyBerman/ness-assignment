from __future__ import annotations

from decimal import Decimal

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from ebay_automation.config.settings import Settings
from ebay_automation.models.price import PriceRange
from ebay_automation.pages.home_page import HomePage
from ebay_automation.pages.search_results_page import SearchResultsPage
from ebay_automation.utils.logger import get_logger
from ebay_automation.utils.reporter import Reporter
from ebay_automation.utils.url_utils import extract_item_id, normalize_item_url

log = get_logger(__name__)


class SearchFlow:
    def __init__(self, page: Page, settings: Settings) -> None:
        self.page = page
        self.settings = settings

    def search_items_by_name_under_price(
        self, query: str, max_price: Decimal | float, limit: int = 5
    ) -> list[str]:
        """Return up to `limit` item URLs priced <= max_price.

        Uses the page's price filter and moves to the next page until there are enough items
        or no more pages. Returning fewer items (or none) is fine.
        """
        max_price = Decimal(str(max_price))
        currency = self.settings.currency
        with Reporter.step(f'Search "{query}" with price <= {currency} {max_price} (limit {limit})'):
            results = SearchResultsPage(self.page, self.settings)
            bin_param = 1 if self.settings.search.buy_it_now_only else None
            if self.settings.search.use_header_search:
                home = HomePage(self.page, self.settings)
                if not home.header_search.is_available():  # header search exists on every eBay page
                    home.open()
                home.header_search.search(query)
                results.wait_loaded()
                if bin_param:
                    with Reporter.step("Filter: Buy It Now only (LH_BIN=1)"):
                        results.apply_url_params(LH_BIN=bin_param)
            else:
                with Reporter.step(f"Open search results (LH_BIN={bin_param})"):
                    results.open_search(query, LH_BIN=bin_param)
            self._apply_price_filter(results, max_price)

            found: dict[str, str] = {}  # item id -> url
            page_no = 1
            while True:
                with Reporter.step(f"Scan results page {page_no}"):
                    self._collect(results, max_price, limit, found)
                if len(found) >= limit:
                    break
                if results.exact_matches_end_here():
                    log.info("No more exact matches after page %s", page_no)
                    break
                if page_no >= self.settings.search.max_pages:
                    log.info("Reached max_pages=%s", page_no)
                    break
                if not results.pagination.has_next():
                    log.info("No more pages after page %s", page_no)
                    break
                results.pagination.go_next()
                results.wait_loaded()
                page_no += 1

            urls = list(found.values())[:limit]
            Reporter.attach_json(
                {
                    "query": query,
                    "max_price": max_price,
                    "currency": currency,
                    "pages": page_no,
                    "urls": urls,
                },
                "search result",
            )
            log.info("Found %d/%d items under %s %s", len(urls), limit, currency, max_price)
            return urls

    def _apply_price_filter(self, results: SearchResultsPage, max_price: Decimal) -> None:
        cfg = self.settings.search
        if cfg.use_ui_price_filter and results.price_filter.is_available():
            try:
                with Reporter.step(f"Filter: UI price max={max_price}"):
                    results.price_filter.apply(max_price)
                    results.wait_loaded()
                return
            except PlaywrightError as exc:
                log.warning("UI price filter failed (%s) - falling back to URL params", exc)
        with Reporter.step(f"Filter: URL price _udhi={max_price}"):
            results.apply_url_params(_udhi=format(max_price, "f"))

    def _collect(
        self, results: SearchResultsPage, max_price: Decimal, limit: int, found: dict[str, str]
    ) -> None:
        cfg, currency = self.settings.search, self.settings.currency
        cards = results.cards()
        matched = 0
        for card in cards:
            if len(found) >= limit:
                break
            data = card.read()
            item_id = extract_item_id(data.href)
            if not item_id:  # "Shop on eBay" placeholder (/itm/123456) or ad tile
                continue
            if item_id in found or data.price is None:
                continue
            if data.price.currency != currency:
                log.debug("Skip %s: currency %s != %s", item_id, data.price.currency, currency)
                continue
            price = (
                data.price.pick(cfg.range_price_strategy)
                if isinstance(data.price, PriceRange)
                else data.price
            )
            if price.amount <= max_price:
                found[item_id] = normalize_item_url(data.href, self.settings.base_url) or data.href
                matched += 1
                log.info("Match %s | %s | %s", item_id, data.price, data.title[:60])
        log.info("Page scanned: %d cards, %d matched, %d total", len(cards), matched, len(found))
