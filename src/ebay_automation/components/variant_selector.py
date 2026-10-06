from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

from ebay_automation.core.base_component import BaseComponent
from ebay_automation.utils.logger import get_logger
from ebay_automation.utils.randomizer import Randomizer

log = get_logger(__name__)

_UNAVAILABLE_RE = re.compile(r"out of stock|unavailable|sold out", re.I)
_PLACEHOLDER_RE = re.compile(r"^\s*-?\s*select\s*-?", re.I)


class VariantSelector(BaseComponent):
    """Picks a random available option for each variation (size, color, ...).

    Handles the current listbox UI and the older <select> UI. Options are read again after
    each pick, because choosing a color can change which sizes are available.
    """

    def __init__(self, page: Page) -> None:
        super().__init__(page, page.locator(".x-msku-evo, #x-msku__container, .x-msku").first)

    @property
    def _listboxes(self) -> Locator:
        return self.page.locator(".x-msku-evo .listbox-button")

    def _pick_listbox(self, index: int, rng: Randomizer) -> str | None:
        box = self._listboxes.nth(index)
        button = box.locator("button.listbox-button__control")
        label = " ".join(button.inner_text().split())  # "Color:\nSelect" -> "Color: Select"
        button.click()
        options = box.get_by_role("option")
        candidates: list[int] = []
        for i in range(options.count()):
            option = options.nth(i)
            text = option.inner_text().strip()
            if (
                _PLACEHOLDER_RE.match(text)
                or _UNAVAILABLE_RE.search(text)
                or option.get_attribute("aria-disabled") == "true"
            ):
                continue
            candidates.append(i)
        if not candidates:
            self.page.keyboard.press("Escape")
            log.warning("No available option for variation %r", label)
            return None
        chosen = options.nth(rng.choice(candidates))
        chosen_text = chosen.inner_text().strip().split("\n")[0]  # drop hidden "selected" label
        chosen.click()
        log.info("Variation %r -> %r", label, chosen_text)
        return f"{label.split(':')[0].strip()}={chosen_text}"

    # Older <select> UI
    @property
    def _selects(self) -> Locator:
        return self.page.locator("select.x-msku__select-box")

    def _pick_select(self, index: int, rng: Randomizer) -> str | None:
        select = self._selects.nth(index)
        values: list[str] = select.locator("option").evaluate_all(
            "opts => opts.filter(o => !o.disabled && o.value && o.value !== '-1'"
            " && !/out of stock/i.test(o.textContent)).map(o => o.value)"
        )
        if not values:
            return None
        value = rng.choice(values)
        select.select_option(value=value)
        name = select.get_attribute("name") or select.get_attribute("id") or f"variation{index}"
        return f"{name}={value}"

    def has_variations(self) -> bool:
        return self._listboxes.count() > 0 or self._selects.count() > 0

    def select_random_available(self, rng: Randomizer) -> list[str]:
        """Select every variation dimension. Returns e.g. ["Color=Black", "US Shoe Size=9"]."""
        chosen: list[str] = []
        for i in range(self._listboxes.count()):
            if picked := self._pick_listbox(i, rng):
                chosen.append(picked)
        for i in range(self._selects.count()):
            if picked := self._pick_select(i, rng):
                chosen.append(picked)
        return chosen
