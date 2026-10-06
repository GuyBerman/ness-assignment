from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from ebay_automation.config.settings import _deep_merge
from ebay_automation.models.search_case import SearchCase
from ebay_automation.utils.data_loader import DataLoader
from ebay_automation.utils.randomizer import Randomizer
from ebay_automation.utils.url_utils import extract_item_id, normalize_item_url, with_query_params

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("url", "item_id"),
    [
        ("https://www.ebay.com/itm/178275474822?_skw=shoes&itmmeta=01M", "178275474822"),
        ("https://www.ebay.com/itm/Nike-Air-Max/307206808085?hash=x", "307206808085"),
        ("https://ebay.com/itm/123456", None),  # "Shop on eBay" placeholder card
        ("https://www.ebay.com/sch/i.html?_nkw=shoes", None),
        ("", None),
    ],
)
def test_extract_item_id(url: str, item_id: str | None) -> None:
    assert extract_item_id(url) == item_id


def test_normalize_item_url_strips_tracking() -> None:
    assert (
        normalize_item_url("https://www.ebay.com/itm/178275474822?_skw=shoes&itmmeta=01M&hash=abc")
        == "https://www.ebay.com/itm/178275474822"
    )


def test_with_query_params_sets_replaces_and_removes() -> None:
    url = "https://www.ebay.com/sch/i.html?_nkw=shoes&_udhi=100"
    result = with_query_params(url, _udhi=220, LH_BIN=1, _nkw=None)
    assert "_udhi=220" in result and "LH_BIN=1" in result and "_nkw" not in result


def test_randomizer_is_reproducible() -> None:
    items = list(range(100))
    assert [Randomizer(7).choice(items) for _ in range(5)] == [Randomizer(7).choice(items) for _ in range(5)]


def test_deep_merge_profile_over_default() -> None:
    base = {"browser": {"headless": True, "slow_mo": 0}, "currency": "ILS"}
    merged = _deep_merge(base, {"browser": {"headless": False}})
    assert merged == {"browser": {"headless": False, "slow_mo": 0}, "currency": "ILS"}


@pytest.mark.parametrize("ext", ["yaml", "json", "csv"])
def test_data_loader_formats(tmp_path: Path, ext: str) -> None:
    content = {
        "yaml": "- id: a\n  query: shoes\n  max_price: 220\n",
        "json": '[{"id": "a", "query": "shoes", "max_price": 220}]',
        "csv": "id,query,max_price\na,shoes,220\n",
    }[ext]
    path = tmp_path / f"cases.{ext}"
    path.write_text(content, encoding="utf-8")
    [case] = DataLoader.load(path, SearchCase)
    assert case.query == "shoes" and case.max_price == Decimal("220") and case.limit == 5
    assert case.budget == Decimal("220")


def test_project_data_file_is_valid() -> None:
    from ebay_automation.config.settings import get_settings

    settings = get_settings()
    cases = DataLoader.load(settings.resolve(settings.data_file), SearchCase)
    assert cases and len({c.id for c in cases}) == len(cases)
