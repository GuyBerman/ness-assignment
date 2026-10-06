from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Real eBay item ids are 12 digits; the "Shop on eBay" placeholder card links to /itm/123456.
_ITEM_ID_RE = re.compile(r"/itm/(?:[^/?#]+/)?(\d{9,})")


def extract_item_id(url: str) -> str | None:
    match = _ITEM_ID_RE.search(url or "")
    return match.group(1) if match else None


def normalize_item_url(url: str, base_url: str = "https://www.ebay.com") -> str | None:
    """Drop tracking params: returns https://www.ebay.com/itm/<id>."""
    item_id = extract_item_id(url)
    return f"{base_url.rstrip('/')}/itm/{item_id}" if item_id else None


def with_query_params(url: str, **params: str | int | None) -> str:
    """Return ``url`` with ``params`` set/replaced (None removes the key)."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    for key, value in params.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = str(value)
    return urlunsplit(parts._replace(query=urlencode(query)))
