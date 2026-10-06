from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class SearchCase(BaseModel):
    """One row of data/search_cases.yaml."""

    id: str
    query: str = Field(min_length=1)
    max_price: Decimal = Field(gt=0)
    limit: int = Field(default=5, ge=1)
    # Defaults to max_price.
    budget_per_item: Decimal | None = None

    @property
    def budget(self) -> Decimal:
        return self.budget_per_item if self.budget_per_item is not None else self.max_price
