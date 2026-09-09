"""Parse Google Finance quote, news, and profile payloads.

Unlabelled positional numbers are not treated as named statistics.
Headline/snippet is never promoted to an article body.
"""

from __future__ import annotations

import html as html_lib
import re
from datetime import datetime, timezone
from typing import Any

from saudi_exchange_reports.google_finance.types import NewsItem

UTC = timezone.utc

_ABOUT_PAIR_RE = re.compile(
    r'class="OspXqd">\s*([^<]+?)\s*</span>\s*<span class="oJCxTc">(.*?)</span>',
    re.IGNORECASE | re.DOTALL,
)
_STAT_PAIR_RE = re.compile(
    r'class="SwQK7">\s*([^<]+?)\s*</div>\s*<div class="dO6ijd">([^<]*)</div>',
    re.IGNORECASE,
)
_WEBSITE_HREF_RE = re.compile(
    r'class="OspXqd">\s*Website\s*</span>\s*<span class="oJCxTc">.*?<a[^>]+href="([^"]+)"',
    re.IGNORECASE | re.DOTALL,
)
_PLAIN_STAT_RE = re.compile(
    r"(Previous close|Day range|Year range|Market cap|P/E ratio|Dividend yield|Primary exchange)\s+([^\n<]+)",
    re.IGNORECASE,
)


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace("\xa0", " ").strip()
        cleaned = re.sub(r"^[A-Z]{3}\s+", "", cleaned)
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _unwrap_quote_row(data: Any) -> list[Any] | None:
    node = data
    for _ in range(4):
        if isinstance(node, list) and len(node) == 1:
            node = node[0]
            continue
        break
    if not isinstance(node, list) or len(node) < 6:
        return None
    if node[0] is None and isinstance(node[1], list):
        return node
    if isinstance(node[1], list) and len(node[1]) == 2 and all(isinstance(x, str) for x in node[1]):
        return node
    return None


def parse_quote_summary(data: Any) -> dict[str, Any]:
    row = _unwrap_quote_row(data)
    if row is None:
        return {}
    display_name = row[2] if len(row) > 2 and isinstance(row[2], str) else None
    currency = row[4] if len(row) > 4 and isinstance(row[4], str) else None
    price_vec = row[5] if len(row) > 5 and isinstance(row[5], list) else None
    last = _as_float(price_vec[0]) if price_vec else None
    change = _as_float(price_vec[1]) if price_vec and len(price_vec) > 1 else None
    percent_change = _as_float(price_vec[2]) if price_vec and len(price_vec) > 2 else None
    unix = None
    if len(row) > 11 and isinstance(row[11], list) and row[11]:
        unix = _as_float(row[11][0])
    elif len(row) > 11:
        unix = _as_float(row[11])
    tz_name = row[12] if len(row) > 12 and isinstance(row[12], str) else None
    quoted_at = None
    if unix:
        quoted_at = datetime.fromtimestamp(int(unix), tz=UTC)
    session = _session_label(row[19] if len(row) > 19 else None, tz_name)
    quote_id = row[21] if len(row) > 21 and isinstance(row[21], str) else None
    return {
        "display_name": display_name,
        "currency": currency,
        "last": last,
        "change": change,
        "percent_change": percent_change,
        "quoted_at": quoted_at,
        "quote_timezone": tz_name,
        "session": session,
        "quote_id": quote_id,
    }


def _session_label(value: Any, tz_name: str | None) -> str | None:
    if not isinstance(value, list) or not value:
        return None
    start = end = None
    first = value[0]
    if isinstance(first, list) and first and isinstance(first[0], int) and first[0] > 1800:
        start = _clock(value[0])
        end = _clock(value[1]) if len(value) > 1 else None
    elif isinstance(first, list) and len(first) >= 3:
        start = _clock(first[1])
        end = _clock(first[2])
    if not start or not end:
        return None
    suffix = f" {tz_name}" if tz_name else ""
    return f"{start}–{end}{suffix}"


def _clock(value: Any) -> str | None:
    if not isinstance(value, list) or len(value) < 4:
        return None
    year, month, day, hour = value[0], value[1], value[2], value[3]
    if not all(isinstance(x, int) for x in (year, month, day, hour)):
        return None
    minute = value[4] if len(value) > 4 and isinstance(value[4], int) else 0
    return f"{hour:02d}:{minute:02d}"


def parse_news_rows(data: Any) -> list[NewsItem]:
    if not data:
        return []
    rows = data[0] if isinstance(data, list) and data and isinstance(data[0], list) else data
    if not isinstance(rows, list):
        return []
    items: list[NewsItem] = []
    for row in rows:
        if not isinstance(row, list) or not row:
            continue
        url = row[0] if isinstance(row[0], str) and row[0].startswith("http") else None
        if url is None and not (isinstance(row[0], str) and row[0]):
            continue
        if not isinstance(row[0], str):
            continue
        if not url and not (len(row) > 1 and isinstance(row[1], str)):
            continue
        headline = row[1] if len(row) > 1 and isinstance(row[1], str) else None
        publisher = row[2] if len(row) > 2 and isinstance(row[2], str) and row[2].strip() else None
        unix = _as_float(row[4]) if len(row) > 4 else None
        snippet = row[16] if len(row) > 16 and isinstance(row[16], str) else None
        published_at = datetime.fromtimestamp(int(unix), tz=UTC) if unix else None
        missing: list[str] = []
        if not publisher:
            missing.append("publisher")
        if published_at is None:
            missing.append("published_at")
        if not url:
            missing.append("url")
        items.append(
            NewsItem(
                url=url,
                headline=headline,
                publisher=publisher,
                published_at=published_at,
                snippet=snippet,
                article_body=None,
                read_status="not_read",
                unavailable=tuple(missing),
            )
        )
    return items


def parse_profile_payload(data: Any) -> dict[str, Any]:
    row = _unwrap_profile_row(data)
    if row is None:
        return {}
    description = row[2] if len(row) > 2 and isinstance(row[2], str) and row[2].strip() else None
    founded = None
    if len(row) > 4:
        if isinstance(row[4], list) and row[4] and isinstance(row[4][0], int):
            founded = row[4][0]
        else:
            maybe = _as_float(row[4])
            if maybe is not None and 1800 < maybe < 2100:
                founded = int(maybe)
    ceo = row[5] if len(row) > 5 and isinstance(row[5], str) and row[5].strip() else None
    employees = None
    if len(row) > 6 and isinstance(row[6], (int, float)) and not isinstance(row[6], bool):
        employees = str(int(row[6]))
    website = None
    if len(row) > 22 and isinstance(row[22], str) and row[22].startswith("http"):
        website = row[22]
    sector = None
    if row and isinstance(row[-1], str) and row[-1] and " " not in row[-1] and len(row[-1]) < 40:
        # Only accept a trailing sector-like token when it is a short label, not a URL.
        if not row[-1].startswith("http") and row[-1][0].isalpha():
            sector = row[-1]
    return {
        "description": description,
        "website": website,
        "ceo": ceo,
        "founded_year": founded,
        "employees": employees,
        "sector": sector,
    }


def _unwrap_profile_row(data: Any) -> list[Any] | None:
    node = data
    for _ in range(4):
        if isinstance(node, list) and len(node) == 1:
            node = node[0]
            continue
        break
    if not isinstance(node, list) or len(node) < 3:
        return None
    if node[0] is None and (len(node) < 2 or node[1] is None or isinstance(node[1], str)):
        return node
    if isinstance(node[2], str):
        return node
    return None


def labelled_html_about(html: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for label, raw in _ABOUT_PAIR_RE.findall(html):
        value = html_lib.unescape(re.sub(r"<[^>]+>", "", raw)).strip()
        pairs[label.strip()] = value
    href = _WEBSITE_HREF_RE.search(html)
    if href and "Website" not in pairs:
        pairs["Website"] = href.group(1)
    elif "Website" in pairs and "http" not in pairs["Website"]:
        if href:
            pairs["Website"] = href.group(1)
    return pairs


def labelled_html_stats(html: str) -> dict[str, str]:
    stats: dict[str, str] = {}
    for label, raw in _PLAIN_STAT_RE.findall(html):
        stats[label.strip()] = html_lib.unescape(raw).strip()
    for label, raw in _STAT_PAIR_RE.findall(html):
        stats[label.strip()] = html_lib.unescape(raw).replace("\xa0", " ").strip()
    return stats


def dataset_is_empty(data: Any) -> bool:
    if data is None:
        return True
    if data == []:
        return True
    if data == [None] or data == [[None]] or data == [[[None]]]:
        return True
    return False
