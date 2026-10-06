from __future__ import annotations

from decimal import Decimal

import pytest

from ebay_automation.models.price import Price, PriceRange
from ebay_automation.utils.price_parser import PriceParseError, parse_price, parse_prices, try_parse_price

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("text", "amount", "currency"),
    [
        ("ILS 45.78", "45.78", "ILS"),
        ("US $14.99", "14.99", "USD"),
        ("US $14.99or Best Offer", "14.99", "USD"),
        ("$1,234.56", "1234.56", "USD"),
        ("$20", "20", "USD"),
        ("₪45", "45", "ILS"),
        ("EUR 12,50", "12.50", "EUR"),
        ("EUR 1.234,56", "1234.56", "EUR"),
        ("£9.99", "9.99", "GBP"),
        ("C $20.00", "20.00", "CAD"),
        ("ILS 1,050.00", "1050.00", "ILS"),
        ("  ILS 305.37  ", "305.37", "ILS"),
    ],
)
def test_single_price(text: str, amount: str, currency: str) -> None:
    assert parse_price(text) == Price(Decimal(amount), currency)


@pytest.mark.parametrize(
    ("text", "low", "high"),
    [
        ("ILS 286.68 to ILS 361.06", "286.68", "361.06"),  # eBay renders 3 spans, joined by us
        ("ILS 286.68  to  ILS 361.06", "286.68", "361.06"),
        ("$20.00 to $35.00", "20.00", "35.00"),
    ],
)
def test_price_range(text: str, low: str, high: str) -> None:
    result = parse_price(text)
    assert isinstance(result, PriceRange)
    assert result.low.amount == Decimal(low)
    assert result.high.amount == Decimal(high)
    assert result.pick("max").amount == Decimal(high)
    assert result.pick("min").amount == Decimal(low)


@pytest.mark.parametrize("text", ["", "See price", "Free shipping", "Best Offer", "1234"])
def test_no_price(text: str) -> None:
    assert try_parse_price(text) is None
    with pytest.raises(PriceParseError):
        parse_price(text)


def test_parse_prices_returns_all_in_order() -> None:
    assert [p.amount for p in parse_prices("Subtotal (2 items) ILS 120.00 Shipping ILS 30.50")] == [
        Decimal("120.00"),
        Decimal("30.50"),
    ]


def test_price_str() -> None:
    assert str(Price(Decimal("1234.5"), "ILS")) == "ILS 1,234.50"
