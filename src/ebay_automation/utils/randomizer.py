from __future__ import annotations

import random
from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


class Randomizer:
    """Seeded random, so variant choices can be reproduced."""

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else random.randrange(1_000_000)
        self._rng = random.Random(self.seed)

    def choice(self, items: Sequence[T]) -> T:
        if not items:
            raise ValueError("Cannot choose from an empty sequence")
        return self._rng.choice(items)
