"""Fixtures and hooks shared by unit and e2e tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest

from ebay_automation.config.settings import Settings, get_settings
from ebay_automation.core.exceptions import BotChallengeError


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


def _skip_on_bot_challenge() -> Generator[None, object, object]:
    try:
        return (yield)
    except BotChallengeError as exc:
        if get_settings().bot_challenge_action != "fail":
            pytest.skip(f"eBay bot page: {exc}")
        raise


# A bot page isn't a product bug, so report it as skipped (bot_challenge_action=fail to fail instead).
@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item: pytest.Item) -> Generator[None, object, object]:
    return (yield from _skip_on_bot_challenge())


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, object, object]:
    return (yield from _skip_on_bot_challenge())


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> Generator[None, object, object]:
    """Expose each phase's report on the item (item.rep_setup / rep_call) for teardown fixtures."""
    report = yield
    setattr(item, f"rep_{report.when}", report)
    return report
