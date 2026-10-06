from __future__ import annotations

import allure
import pytest

from ebay_automation.config.settings import get_settings
from ebay_automation.flows.auth_flow import AuthFlow
from ebay_automation.flows.cart_flow import CartFlow
from ebay_automation.flows.search_flow import SearchFlow
from ebay_automation.models.search_case import SearchCase
from ebay_automation.utils.data_loader import DataLoader

_settings = get_settings()
CASES = DataLoader.load(_settings.resolve(_settings.data_file), SearchCase)


@allure.epic("eBay")
@allure.feature("Shopping cart")
@pytest.mark.e2e
@pytest.mark.flaky(reruns=1, reruns_delay=5)
@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_search_add_to_cart_and_validate_total(
    case: SearchCase, auth_flow: AuthFlow, search_flow: SearchFlow, cart_flow: CartFlow
) -> None:
    allure.dynamic.title(f'"{case.query}" <= {case.max_price} x{case.limit} -> cart within budget')

    auth_flow.login()
    # A fresh guest context starts with an empty cart; a reused session may not.
    if _settings.cart.clear_before_test and _settings.saved_state_file() is not None:
        cart_flow.clear_cart()

    urls = search_flow.search_items_by_name_under_price(case.query, case.max_price, case.limit)
    assert len(urls) <= case.limit, f"Returned {len(urls)} urls, limit is {case.limit}"

    added = cart_flow.add_items_to_cart(urls)
    if urls:
        assert added, "None of the found items could be added to the cart"
        cart_flow.assert_cart_contains(added)

    # The spec passes urls.length; this passes the number actually added (the same unless one was skipped).
    cart_flow.assert_cart_total_not_exceeds(case.budget, len(added))
