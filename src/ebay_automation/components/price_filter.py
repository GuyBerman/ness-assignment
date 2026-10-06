from __future__ import annotations

import re
from decimal import Decimal

from playwright.sync_api import Locator, Page

from ebay_automation.core.base_component import BaseComponent
from ebay_automation.utils.pacer import Pacer


def _fmt(value: Decimal | float | int) -> str:
    return format(Decimal(str(value)).normalize(), "f")


class PriceFilter(BaseComponent):
    """Price min/max filter in the left sidebar."""

    def __init__(self, page: Page, pace_ms: int = 0) -> None:
        super().__init__(page, page.locator(".su-textrange").first)
        self._pace_ms = pace_ms

    @property
    def min_input(self) -> Locator:
        return self.root.locator("input[placeholder^='Min']").first

    @property
    def max_input(self) -> Locator:
        return self.root.locator("input[placeholder^='Max']").first

    @property
    def submit_button(self) -> Locator:
        return self.root.locator("button.su-textrange__submit-button").first

    def apply(self, max_price: Decimal | float, min_price: Decimal | float | None = None) -> None:
        if min_price is not None:
            self.min_input.fill(_fmt(min_price))
        self.max_input.fill(_fmt(max_price))
        Pacer.pace(self.page, self._pace_ms)
        self.submit_button.click()
        # eBay reflects the filter in the URL as _udhi (max) / _udlo (min).
        self.page.wait_for_url(re.compile(r"[?&]_udhi="))
