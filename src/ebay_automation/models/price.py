from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class Price:
    """Amount and currency."""

    amount: Decimal
    currency: str

    def __str__(self) -> str:
        return f"{self.currency} {self.amount:,.2f}"


@dataclass(frozen=True)
class PriceRange:
    """Price range, e.g. "ILS 50.00 to ILS 80.00"."""

    low: Price
    high: Price

    @property
    def currency(self) -> str:
        return self.low.currency

    def pick(self, strategy: Literal["max", "min"]) -> Price:
        return self.high if strategy == "max" else self.low

    def __str__(self) -> str:
        return f"{self.low} to {self.high}"
