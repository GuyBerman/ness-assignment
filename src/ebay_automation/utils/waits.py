from __future__ import annotations

import time
from collections.abc import Callable

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

_POLL_MS = 250


def wait_until(page: Page, predicate: Callable[[], bool], timeout_ms: int, message: str) -> None:
    """Poll a condition until it is true or the timeout passes.
    Used when a single expect() can't express the condition.
    """
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except PlaywrightError:  # DOM may be mid-navigation; keep polling
            pass
        page.wait_for_timeout(_POLL_MS)
    raise TimeoutError(f"Timed out after {timeout_ms} ms waiting for: {message}")
