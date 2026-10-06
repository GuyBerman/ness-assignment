from __future__ import annotations

from playwright.sync_api import Locator, Page


class BaseComponent:
    """A reusable UI fragment. All locators are scoped under ``root``."""

    def __init__(self, page: Page, root: Locator | None = None) -> None:
        self.page = page
        self.root = root if root is not None else page.locator("body")

    def is_available(self) -> bool:
        return self.root.count() > 0 and self.root.first.is_visible()
