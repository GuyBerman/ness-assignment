"""BotGuard tests against fake eBay pages (no network)."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, Route

from ebay_automation.core.bot_guard import BotGuard
from ebay_automation.core.exceptions import BotChallengeError

pytestmark = pytest.mark.unit

NORMAL = "<title>Electronics, Cars, Fashion, Collectibles &amp; More | eBay</title><h1>home</h1>"
BLOCKED = "<title>Error Page | eBay</title><h1>SORRY</h1>"
CHALLENGE = "<title>Pardon Our Interruption...</title>"


def _serve(page: Page, *bodies: str) -> None:
    """Fulfil successive requests with ``bodies`` (last one repeats)."""
    queue = list(bodies)

    def handler(route: Route) -> None:
        body = queue.pop(0) if len(queue) > 1 else queue[0]
        route.fulfill(status=200, content_type="text/html", body=body)

    page.route("https://www.ebay.com/**", handler)


@pytest.mark.parametrize(
    ("url", "body", "expected"),
    [
        ("https://www.ebay.com/", NORMAL, None),
        ("https://www.ebay.com/", BLOCKED, "blocked"),
        ("https://www.ebay.com/", CHALLENGE, "challenge"),
        ("https://www.ebay.com/splashui/challenge?ap=1", NORMAL, "challenge"),
    ],
)
def test_detect(page: Page, url: str, body: str, expected: str | None) -> None:
    _serve(page, body)
    page.goto(url)
    assert BotGuard(page).detect() == expected


def test_normal_page_passes(page: Page) -> None:
    _serve(page, NORMAL)
    page.goto("https://www.ebay.com/")
    assert BotGuard(page).check() is False


def test_transient_error_page_recovers_after_reload(page: Page) -> None:
    _serve(page, BLOCKED, NORMAL)
    page.goto("https://www.ebay.com/")
    assert BotGuard(page, reload_retries=2, backoff_ms=10).check() is True


def test_persistent_block_raises_with_hint(page: Page) -> None:
    _serve(page, BLOCKED)
    page.goto("https://www.ebay.com/")
    with pytest.raises(BotChallengeError, match="blocked the browser"):
        BotGuard(page, reload_retries=1, backoff_ms=10).check()


def test_waits_for_human_then_continues(page: Page) -> None:
    _serve(page, CHALLENGE, NORMAL)
    page.goto("https://www.ebay.com/")
    # Simulate the human solving it: the page navigates away from the challenge shortly after.
    page.evaluate("setTimeout(() => location.reload(), 300)")
    assert BotGuard(page, wait_for_human_ms=5_000).check() is True


def test_invisible_recaptcha_on_normal_page_is_not_a_challenge(page: Page) -> None:
    """Normal result pages contain a hidden reCAPTCHA iframe."""
    _serve(page, "<title>Shoes for sale | eBay</title><iframe src='about:blank#recaptcha' hidden></iframe>")
    page.goto("https://www.ebay.com/sch/i.html?_nkw=shoes&_udhi=220")
    assert BotGuard(page).detect() is None


ERROR_PAGE_WITH_HOME_LINK = (
    "<title>Error Page | eBay</title><div class='error-header'><h1>SORRY</h1>"
    "<a class='fake-btn' href='https://www.ebay.com/'>Go to homepage</a></div>"
)


def test_error_page_goes_home_then_back_to_target(page: Page) -> None:
    visited: list[str] = []

    def handler(route: Route) -> None:
        visited.append(route.request.url)
        # first hit on the search page is blocked; home and the retried search are fine
        blocked = (
            route.request.url.endswith("/sch/i.html?_nkw=shoes") and visited.count(route.request.url) == 1
        )
        body = ERROR_PAGE_WITH_HOME_LINK if blocked else NORMAL
        route.fulfill(status=200, content_type="text/html", body=body)

    page.route("https://www.ebay.com/**", handler)
    page.goto("https://www.ebay.com/sch/i.html?_nkw=shoes")
    assert BotGuard(page, reload_retries=2, backoff_ms=10).check() is True
    assert visited == [
        "https://www.ebay.com/sch/i.html?_nkw=shoes",  # blocked
        "https://www.ebay.com/",  # clicked "Go to homepage"
        "https://www.ebay.com/sch/i.html?_nkw=shoes",  # back to the page we needed
    ]
    assert page.url == "https://www.ebay.com/sch/i.html?_nkw=shoes"
