"""Parses eBay price strings, e.g. "ILS 45.78", "US $14.99", "ILS 286.68 to ILS 361.06"."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from ebay_automation.models.price import Price, PriceRange

# Longest tokens first so "US $" wins over "$".
_CURRENCY_TOKENS: dict[str, str] = {
    "US $": "USD",
    "C $": "CAD",
    "AU $": "AUD",
    "ILS": "ILS",
    "USD": "USD",
    "EUR": "EUR",
    "GBP": "GBP",
    "CAD": "CAD",
    "AUD": "AUD",
    "₪": "ILS",
    "€": "EUR",
    "£": "GBP",
    "$": "USD",
}

_TOKEN_PATTERN = "|".join(re.escape(t) for t in sorted(_CURRENCY_TOKENS, key=len, reverse=True))
# currency token, optional whitespace, number with thousands separators and optional decimals
_PRICE_RE = re.compile(rf"(?P<cur>{_TOKEN_PATTERN})\s*(?P<num>\d[\d.,]*\d|\d)")


class PriceParseError(ValueError):
    pass


def _to_decimal(raw: str) -> Decimal:
    num = raw
    # Decide decimal separator: the last of "," / "." followed by exactly 1-2 digits.
    last_sep = max(num.rfind(","), num.rfind("."))
    if last_sep != -1 and 1 <= len(num) - last_sep - 1 <= 2:
        integer, fraction = num[:last_sep], num[last_sep + 1 :]
    else:
        integer, fraction = num, ""
    integer = integer.replace(",", "").replace(".", "")
    try:
        return Decimal(f"{integer}.{fraction}" if fraction else integer)
    except InvalidOperation as exc:  # pragma: no cover - regex guarantees digits
        raise PriceParseError(f"Bad number: {raw!r}") from exc


def parse_prices(text: str) -> list[Price]:
    """Return every price found in ``text`` in order of appearance."""
    return [
        Price(_to_decimal(m.group("num")), _CURRENCY_TOKENS[m.group("cur")])
        for m in _PRICE_RE.finditer(text or "")
    ]


def parse_price(text: str) -> Price | PriceRange:
    """Parse a price or a "low to high" range. Raises PriceParseError if there is no price."""
    prices = parse_prices(text)
    if not prices:
        raise PriceParseError(f"No price in {text!r}")
    if len(prices) >= 2 and re.search(r"\bto\b", text, re.IGNORECASE):
        low, high = sorted(prices[:2], key=lambda p: p.amount)
        return PriceRange(low, high)
    return prices[0]


def try_parse_price(text: str) -> Price | PriceRange | None:
    try:
        return parse_price(text)
    except PriceParseError:
        return None
