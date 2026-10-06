from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

from ebay_automation.components.variant_selector import VariantSelector
from ebay_automation.config.settings import Settings
from ebay_automation.core.base_page import BasePage
from ebay_automation.core.exceptions import ItemNotAddableError
from ebay_automation.models.price import Price, PriceRange
from ebay_automation.pages.home_page import HomePage
from ebay_automation.utils.price_parser import try_parse_price
from ebay_automation.utils.waits import wait_until

_ADDED_RE = re.compile(r"^\s*added to (your )?cart\s*$", re.I)


class ItemPage(BasePage):
    def __init__(self, page: Page, settings: Settings) -> None:
        super().__init__(page, settings)
        self.variants = VariantSelector(page)
        self._header = HomePage(page, settings)  # header (cart badge) is shared

    @property
    def title(self) -> Locator:
        return self.page.locator("h1").first

    @property
    def price(self) -> Locator:
        # <div class="x-price-primary">US $14.99</div>
        return self.page.locator(".x-price-primary").first

    @property
    def add_to_cart_button(self) -> Locator:
        # <a id="atcBtn_btn_1" data-testid="ux-call-to-action" ...>Add to cart</a>
        return (
            self.page.locator("#atcBtn_btn_1")
            .or_(self.page.get_by_role("link", name=re.compile(r"^add to cart$", re.I)))
            .or_(self.page.get_by_role("button", name=re.compile(r"^add to cart$", re.I)))
            .first
        )

    @property
    def added_dialog(self) -> Locator:
        # <div data-testid="ux-overlay" role="dialog"> with an "Added to cart" heading.
        # The dialog shows "Adding to your cart" first, so wait for the heading.
        return self.page.locator("[data-testid='ux-overlay'][role='dialog']").filter(
            has=self.page.get_by_role("heading", name=_ADDED_RE)
        )

    @property
    def variation_error(self) -> Locator:
        # Shown when a variation isn't selected:
        # <div class="x-sku has-error"> ... <div class="error-text">Please select a Color</div>
        return self.page.locator(".x-msku-evo .has-error .error-text")

    def wait_loaded(self) -> None:
        super().wait_loaded()
        self.title.wait_for()

    def read_price(self) -> Price | PriceRange | None:
        return try_parse_price(self.price.inner_text()) if self.price.count() else None

    def can_add_to_cart(self) -> bool:
        return self.add_to_cart_button.count() > 0 and self.add_to_cart_button.is_visible()

    def add_to_cart(self) -> None:
        if not self.can_add_to_cart():
            raise ItemNotAddableError(f"No 'Add to cart' on {self.page.url} (auction / ended / sold out)")
        before = self._header.cart_count()
        start_url = self.page.url
        self.add_to_cart_button.click()

        def confirmed() -> bool:
            if self.variation_error.count() and self.variation_error.first.is_visible():
                raise ItemNotAddableError(f"Variation not accepted on {start_url}")
            if "cart.ebay.com" in self.page.url:
                return True
            return self.added_dialog.count() > 0 and self.added_dialog.first.is_visible()

        try:
            wait_until(self.page, confirmed, self.settings.browser.timeout_ms, "'Added to cart' confirmation")
        except TimeoutError:
            # Fallback: check whether the cart count in the header went up.
            after = self._header.cart_count()
            if before is None or after is None or after <= before:
                raise
