"""Browser, page and flow fixtures."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

import pytest
from playwright.sync_api import BrowserContext, Page

from ebay_automation.config.settings import Settings
from ebay_automation.flows.auth_flow import AuthFlow
from ebay_automation.flows.cart_flow import CartFlow
from ebay_automation.flows.search_flow import SearchFlow
from ebay_automation.utils.randomizer import Randomizer
from ebay_automation.utils.reporter import Reporter


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """Launch options from config. CLI flags such as --headed still take priority."""
    from_config: dict[str, Any] = {"headless": settings.browser.headless, "slow_mo": settings.browser.slow_mo}
    if settings.browser.channel:
        from_config["channel"] = settings.browser.channel
    return {**from_config, **browser_type_launch_args}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any], settings: Settings) -> dict[str, Any]:
    args: dict[str, Any] = {
        **browser_context_args,
        "locale": settings.browser.locale,
        "viewport": {"width": settings.browser.viewport_width, "height": settings.browser.viewport_height},
    }
    state = settings.saved_state_file()
    if settings.auth.mode == "storage_state" and state is None:
        pytest.fail(
            "auth.mode=storage_state but no saved session - run: python scripts/save_session.py --login"
        )
    if state is not None:
        args["storage_state"] = str(state)
    return args


@pytest.fixture(autouse=True)
def _page_defaults(page: Page, settings: Settings) -> None:
    page.set_default_timeout(settings.browser.timeout_ms)
    page.set_default_navigation_timeout(settings.browser.navigation_timeout_ms)


def _artifact_name(request: pytest.FixtureRequest) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", request.node.name)


@pytest.fixture(autouse=True)
def _trace(context: BrowserContext, settings: Settings, request: pytest.FixtureRequest) -> Iterator[None]:
    """Record a Playwright trace for each test and attach it to the report.
    Skipped when pytest-playwright's own --tracing option is used.
    """
    enabled = settings.artifacts.tracing and request.config.getoption("--tracing") == "off"
    if enabled:
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
    yield
    if enabled:
        directory = settings.resolve(settings.artifacts.traces_dir)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{_artifact_name(request)}.zip"
        context.tracing.stop(path=str(path))
        Reporter.attach_file(path, "playwright trace", "zip")


@pytest.fixture(autouse=True)
def _failure_artifacts(page: Page, settings: Settings, request: pytest.FixtureRequest) -> Iterator[None]:
    yield
    report = getattr(request.node, "rep_call", None)
    if report is not None and report.failed and not page.is_closed():
        directory = settings.resolve(settings.artifacts.screenshots_dir)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"FAILED_{_artifact_name(request)}.png"
        page.screenshot(path=str(path), full_page=True)
        Reporter.attach_png(path, "failure screenshot")
        Reporter.attach_html(page.content(), "failure page html")
        Reporter.attach_text(page.url, "failure url")


@pytest.fixture
def rng(settings: Settings) -> Randomizer:
    return Randomizer(settings.random_seed)


@pytest.fixture
def auth_flow(page: Page, settings: Settings) -> AuthFlow:
    return AuthFlow(page, settings)


@pytest.fixture
def search_flow(page: Page, settings: Settings) -> SearchFlow:
    return SearchFlow(page, settings)


@pytest.fixture
def cart_flow(page: Page, settings: Settings, rng: Randomizer) -> CartFlow:
    return CartFlow(page, settings, rng)
