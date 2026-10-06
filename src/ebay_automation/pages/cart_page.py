from __future__ import annotations

import re
from typing import Literal

from playwright.sync_api import Locator, Page, expect

from ebay_automation.config.settings import Settings
from ebay_automation.core.base_page import BasePage
from ebay_automation.models.price import Price
from ebay_automation.utils.price_parser import parse_prices
from ebay_automation.utils.url_utils import extract_item_id

CartAmount = Literal["items", "subtotal"]

# Order summary on cart.ebay.com:
#   Items (N)  [data-test-id=ITEM_TOTAL]  item prices only
#   Shipping   [data-test-id=SHIPPING]
#   Subtotal   [data-test-id=SUBTOTAL]    items + shipping
SUMMARY_SELECTOR = "[data-test-id='cart-summary']"
AMOUNT_SELECTORS: dict[CartAmount, str] = {
    "items": "[data-test-id='ITEM_TOTAL']",
    "subtotal": "[data-test-id='SUBTOTAL']",
}
# Line items: one <div data-test-id="cart-bucket"> per seller, item links + remove buttons inside.
ITEM_LINK_SELECTOR = "a[data-test-id='cart-item-link']"
REMOVE_BUTTON_SELECTOR = "button[data-test-id='cart-remove-item']"
EMPTY_CART_SELECTOR = ".empty-cart"  # "You don't have any items in your cart."

# Used if the data-test-id selectors stop matching: find the label, then the row with the amount.
_AMOUNT_ANCESTOR = (
    "/ancestor::*[.//*[contains(text(),'$') or contains(text(),'ILS') or contains(text(),'€')"
    " or contains(text(),'£') or contains(text(),'₪')]][1]"
)
AMOUNT_FALLBACK_XPATHS: dict[CartAmount, str] = {
    "items": "//*[starts-with(normalize-space(text()),'Items (')]" + _AMOUNT_ANCESTOR,
    "subtotal": "//*[normalize-space(text())='Subtotal']" + _AMOUNT_ANCESTOR,
}
_EMPTY_TEXT_RE = re.compile(r"don't have any items in your cart|your cart is empty", re.I)


class CartPage(BasePage):
    def __init__(self, page: Page, settings: Settings) -> None:
        super().__init__(page, settings)

    @property
    def url(self) -> str:
        return self.settings.cart_url

    @property
    def summary(self) -> Locator:
        return self.page.locator(SUMMARY_SELECTOR).first

    def _amount(self, field: CartAmount) -> Locator:
        # Not .or_(): with a union, .first could pick the wrong row.
        primary = self.page.locator(AMOUNT_SELECTORS[field])
        if primary.count():
            return primary.first
        return self.page.locator(f"xpath={AMOUNT_FALLBACK_XPATHS[field]}").first

    @property
    def item_links(self) -> Locator:
        return self.page.locator(ITEM_LINK_SELECTOR)

    @property
    def remove_buttons(self) -> Locator:
        return self.page.locator(REMOVE_BUTTON_SELECTOR)

    @property
    def empty_cart(self) -> Locator:
        return self.page.locator(EMPTY_CART_SELECTOR).or_(self.page.get_by_text(_EMPTY_TEXT_RE)).first

    def wait_loaded(self) -> None:
        super().wait_loaded()
        self.summary.or_(self.empty_cart).first.wait_for()

    def is_empty(self) -> bool:
        return self.empty_cart.count() > 0 and self.empty_cart.is_visible()

    def read_amount(self, field: CartAmount) -> Price:
        text = self._amount(field).inner_text()
        prices = parse_prices(text)
        if not prices:
            raise AssertionError(f"Could not read cart {field!r} amount from: {text!r}")
        return prices[-1]  # fallback rows contain label + value; the value comes last

    def item_ids(self) -> list[str]:
        """Distinct item ids in the cart."""
        links = self.item_links if self.item_links.count() else self.page.locator("main a[href*='/itm/']")
        hrefs = links.evaluate_all("els => els.map(e => e.href)")
        return list(dict.fromkeys(i for h in hrefs if (i := extract_item_id(h))))

    def remove_all(self) -> None:
        while self.remove_buttons.count():
            before = self.remove_buttons.count()
            self.remove_buttons.first.click()
            expect(self.remove_buttons).to_have_count(before - 1)
