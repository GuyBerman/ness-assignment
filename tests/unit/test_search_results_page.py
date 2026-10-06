"""SearchResultsPage tests against fake result pages (no network)."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, Route

from ebay_automation.config.settings import get_settings
from ebay_automation.pages.search_results_page import SearchResultsPage

pytestmark = pytest.mark.unit


def _card(item_id: str, price: str) -> str:
    return (
        f"<li class='s-card s-card--vertical'><a href='https://www.ebay.com/itm/{item_id}?_skw=x'>"
        f"<span class='s-card__title'>Item {item_id}</span></a>"
        f"<div class='s-card__attribute-row'><span class='s-card__price'>{price}</span></div></li>"
    )


def _page(heading: str, items: str, extra: str = "") -> str:
    return (
        f"<title>Results | eBay</title>{extra}"
        f"<h1 class='srp-controls__count-heading'>{heading}</h1>"
        f"<ul class='srp-results srp-grid'>{items}</ul>"
    )


def _open(page: Page, html: str) -> SearchResultsPage:
    def handler(route: Route) -> None:
        route.fulfill(status=200, content_type="text/html", body=html)

    page.route("https://www.ebay.com/**", handler)
    page.goto("https://www.ebay.com/sch/i.html?_nkw=x")
    return SearchResultsPage(page, get_settings())


def test_normal_page_returns_all_cards(page: Page) -> None:
    results = _open(
        page, _page("3 results for x", "".join(_card(f"1000000000{i}", "ILS 10.00") for i in range(3)))
    )
    assert len(results.cards()) == 3
    assert not results.exact_matches_end_here()


def test_cards_after_fewer_words_divider_are_excluded(page: Page) -> None:
    exact = "".join(_card(f"1000000000{i}", "ILS 10.00") for i in range(2))
    divider = "<li class='srp-river-answer srp-river-answer--REWRITE_START'>Results matching fewer words</li>"
    fuzzy = "".join(_card(f"2000000000{i}", "ILS 5.00") for i in range(4))
    results = _open(page, _page("2 results for x", exact + divider + fuzzy))
    ids = [c.read().href.split("/itm/")[1][:11] for c in results.cards()]
    assert ids == ["10000000000", "10000000001"]
    assert results.exact_matches_end_here()


def test_no_exact_matches_page_returns_nothing(page: Page) -> None:
    """eBay fills a 0-results page with unrelated items - none of them may be returned."""
    banner = "<div class='srp-save-null-search'>No exact matches found</div>"
    unrelated = "".join(_card(f"3000000000{i}", "ILS 1.00") for i in range(5))
    results = _open(page, _page("0 results for zzqxv9w8qpl", unrelated, extra=banner))
    assert results.has_no_exact_matches()
    assert results.cards() == []
