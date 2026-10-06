from __future__ import annotations

import time

from playwright.sync_api import Page

from ebay_automation.utils.logger import get_logger

log = get_logger(__name__)


class Pacer:
    """Keeps a minimum gap between page loads. eBay starts returning error pages when
    pages load too quickly.
    """

    _last_navigation: float = 0.0

    @classmethod
    def pace(cls, page: Page, interval_ms: int) -> None:
        elapsed_ms = (time.monotonic() - cls._last_navigation) * 1000
        if cls._last_navigation and elapsed_ms < interval_ms:
            page.wait_for_timeout(interval_ms - elapsed_ms)
        cls._last_navigation = time.monotonic()
