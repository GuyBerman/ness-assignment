from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Locator

from ebay_automation.models.price import Price, PriceRange
from ebay_automation.utils.price_parser import try_parse_price

# Result cards (XPath). Matches li.s-card and the older li.s-item layout.
# Cards after the "Results matching fewer words" divider don't match the query, so they're skipped.
FEWER_WORDS_DIVIDER = "li[contains(@class,'srp-river-answer--REWRITE_START')]"
CARDS_XPATH = (
    "//ul[contains(@class,'srp-results')]"
    "/li[contains(@class,'s-card') or contains(@class,'s-item')]"
    "[.//a[contains(@href,'/itm/')]]"
    f"[not(preceding-sibling::{FEWER_WORDS_DIVIDER})]"
)
LINK_XPATH = ".//a[contains(@href,'/itm/')]"
# A price range is split into three spans: "ILS 286.68", " to ", "ILS 361.06".
# The crossed-out old price has a different class, so it isn't included.
PRICE_XPATH = ".//span[contains(@class,'s-card__price') or contains(@class,'s-item__price')]"
TITLE_XPATH = ".//*[contains(@class,'s-card__title') or contains(@class,'s-item__title')]"


@dataclass(frozen=True)
class ResultCardData:
    href: str
    price_text: str
    price: Price | PriceRange | None
    title: str


class ResultCard:
    """Wraps one search result <li>."""

    def __init__(self, root: Locator) -> None:
        self.root = root

    def read(self) -> ResultCardData:
        href = self.root.locator(f"xpath={LINK_XPATH}").first.get_attribute("href") or ""
        price_text = " ".join(t.strip() for t in self.root.locator(f"xpath={PRICE_XPATH}").all_inner_texts())
        title_loc = self.root.locator(f"xpath={TITLE_XPATH}")
        title = title_loc.first.inner_text().split("\n")[0].strip() if title_loc.count() else ""
        return ResultCardData(
            href=href, price_text=price_text, price=try_parse_price(price_text), title=title
        )
