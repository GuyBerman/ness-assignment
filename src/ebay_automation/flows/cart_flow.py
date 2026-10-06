from __future__ import annotations

from decimal import Decimal

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ebay_automation.config.settings import Settings
from ebay_automation.core.exceptions import ItemNotAddableError
from ebay_automation.pages.cart_page import CartPage
from ebay_automation.pages.item_page import ItemPage
from ebay_automation.utils.logger import get_logger
from ebay_automation.utils.randomizer import Randomizer
from ebay_automation.utils.reporter import Reporter
from ebay_automation.utils.url_utils import extract_item_id

log = get_logger(__name__)


class CartFlow:
    def __init__(self, page: Page, settings: Settings, rng: Randomizer) -> None:
        self.page = page  # the "search" tab - items are opened in their own tabs
        self.settings = settings
        self.rng = rng

    def add_items_to_cart(self, urls: list[str]) -> list[str]:
        """Open each item in a new tab, pick random variants, add it to the cart and take a
        screenshot. Returns the URLs that were added.
        """
        Reporter.attach_text(str(self.rng.seed), "random seed (variants)")
        added: list[str] = []
        for index, url in enumerate(urls, start=1):
            item_id = extract_item_id(url) or str(index)
            with Reporter.step(f"[{index}/{len(urls)}] Add item {item_id} to cart"):
                tab = self.page.context.new_page()
                item = ItemPage(tab, self.settings)
                try:
                    item.open(url)
                    variants = (
                        item.variants.select_random_available(self.rng)
                        if item.variants.has_variations()
                        else []
                    )
                    Reporter.attach_json(
                        {
                            "url": url,
                            "title": item.title.inner_text(),
                            "price": str(item.read_price()),
                            "variants": variants,
                        },
                        f"item {item_id}",
                    )
                    item.add_to_cart()
                    item.screenshot(f"{index:02d}_added_{item_id}")  # shows the "Added to cart" dialog
                    added.append(url)
                except (ItemNotAddableError, TimeoutError, PlaywrightTimeoutError) as exc:
                    log.warning("Skipping %s: %s", url, exc)
                    item.screenshot(f"{index:02d}_skipped_{item_id}")
                    Reporter.attach_text(f"{url}\n{exc}", f"skipped {item_id}")
                finally:
                    tab.close()
                    self.page.bring_to_front()
        log.info("Added %d/%d items", len(added), len(urls))
        return added

    def assert_cart_total_not_exceeds(self, budget_per_item: Decimal | float, items_count: int) -> None:
        """Assert the cart amount (cart.compare_field) <= budget_per_item * items_count."""
        budget = Decimal(str(budget_per_item))
        threshold = budget * items_count
        field = self.settings.cart.compare_field
        with Reporter.step(f"Assert cart {field} <= {budget} x {items_count} = {threshold}"):
            cart = CartPage(self.page, self.settings)
            cart.open()
            try:
                if items_count == 0:
                    assert cart.is_empty(), "Expected an empty cart when no items were added"
                    return
                amount = cart.read_amount(field)
                Reporter.attach_json(
                    {
                        "field": field,
                        "amount": str(amount),
                        "threshold": str(threshold),
                        "items": items_count,
                    },
                    "cart check",
                )
                assert amount.currency == self.settings.currency, (
                    f"Cart currency {amount.currency} != expected {self.settings.currency}; "
                    "cannot compare across currencies"
                )
                assert amount.amount <= threshold, (
                    f"Cart {field} {amount} exceeds {amount.currency} {threshold} "
                    f"({budget} x {items_count} items)"
                )
                log.info("Cart %s %s <= %s", field, amount, threshold)
            finally:
                cart.screenshot(f"cart_page_{budget}x{items_count}", full_page=True)  # one per scenario
                Reporter.attach_html(self.page.content(), "cart page html")

    def assert_cart_contains(self, urls: list[str]) -> None:
        expected = {i for u in urls if (i := extract_item_id(u))}
        with Reporter.step(f"Assert cart contains the {len(expected)} added items"):
            cart = CartPage(self.page, self.settings)
            cart.open()
            missing = expected - set(cart.item_ids())
            assert not missing, f"Items missing from cart: {sorted(missing)}"

    def clear_cart(self) -> None:
        with Reporter.step("Empty cart before test"):
            cart = CartPage(self.page, self.settings)
            cart.open()
            if not cart.is_empty():
                cart.remove_all()
