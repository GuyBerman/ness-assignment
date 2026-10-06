from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Page

from ebay_automation.config.settings import Settings
from ebay_automation.core.bot_guard import BotGuard
from ebay_automation.utils.logger import get_logger
from ebay_automation.utils.pacer import Pacer
from ebay_automation.utils.reporter import Reporter

log = get_logger(__name__)


class BasePage:
    """Base class for page objects."""

    PATH: str = "/"

    def __init__(self, page: Page, settings: Settings) -> None:
        self.page = page
        self.settings = settings
        self.bot_guard = BotGuard(
            page,
            wait_for_human_ms=settings.bot_challenge_wait_ms,
            reload_retries=settings.bot_block_reload_retries,
            auto_clear_ms=settings.bot_challenge_auto_clear_s * 1000,
        )

    @property
    def url(self) -> str:
        return f"{self.settings.base_url.rstrip('/')}{self.PATH}"

    def open(self, url: str | None = None) -> BasePage:
        target = url or self.url
        log.info("Open %s", target)
        self.pace()
        self.page.goto(target, wait_until="domcontentloaded")
        # After a bot page we may be on a different page, so go back to the target.
        if self.bot_guard.check() and urlsplit(self.page.url).path != urlsplit(target).path:
            self.page.goto(target, wait_until="domcontentloaded")
        self.wait_loaded()
        return self

    def pace(self) -> None:
        Pacer.pace(self.page, self.settings.browser.min_navigation_interval_ms)

    def wait_loaded(self) -> None:
        self.page.wait_for_load_state("domcontentloaded")
        self.bot_guard.check()

    def screenshot(self, name: str, full_page: bool = False) -> Path:
        directory = self.settings.resolve(self.settings.artifacts.screenshots_dir)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{re.sub(r'[^A-Za-z0-9_.-]+', '_', name)}.png"
        self.page.screenshot(path=str(path), full_page=full_page)
        Reporter.attach_png(path, name)
        log.info("Screenshot saved: %s", path)
        return path
