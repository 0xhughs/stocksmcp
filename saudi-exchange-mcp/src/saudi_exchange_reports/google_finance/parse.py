"""Parse Google Finance quote, news, and profile payloads.

Unlabelled positional numbers are not treated as named statistics.
Headline/snippet is never promoted to an article body.
"""

from __future__ import annotations

import html as html_lib
import re
from datetime import datetime, timezone
from typing import Any

from saudi_exchange_reports.google_finance.types import (
    DisplayCell,
    DisplayRow,
    DisplayTable,
    EarningsPeriod,
    LabeledFigure,
    MetricPeriod,
    NewsItem,
    ParsedFinancials,
    present_figure,
    unavailable_figure,
)

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


def earnings_html_is_loading(html: str) -> bool:
    return "Loading Previous Earnings" in html


def _looks_like_earnings_row(row: Any) -> bool:
    if not isinstance(row, list) or len(row) < 10:
        return False
    year, quarter = row[3], row[4]
    if not isinstance(year, int) or isinstance(year, bool):
        return False
    if not isinstance(quarter, int) or isinstance(quarter, bool) or quarter not in {1, 2, 3, 4}:
        return False
    if year < 1990 or year > 2100:
        return False
    metrics = row[9]
    if not isinstance(metrics, list) or len(metrics) < 17:
        return False
    return True


def _earnings_rows(data: Any) -> list[Any]:
    if not isinstance(data, list) or not data:
        return []
    candidates: list[Any] = [data]
    if isinstance(data[0], list):
        candidates.append(data[0])
        if data[0] and isinstance(data[0][0], list):
            candidates.append(data[0][0])
    for cand in candidates:
        if isinstance(cand, list) and cand and _looks_like_earnings_row(cand[0]):
            return cand
    return []


def _numeric_figure(kind: str, value: Any) -> LabeledFigure:
    if value is None or isinstance(value, bool):
        return unavailable_figure(kind)
    if isinstance(value, (int, float)):
        return present_figure(kind, float(value))
    return unavailable_figure(kind)


def _period_end_tuple(value: Any) -> tuple[int, int, int] | None:
    if isinstance(value, list) and len(value) == 3 and all(isinstance(x, int) and not isinstance(x, bool) for x in value):
        return (value[0], value[1], value[2])
    return None


def parse_earnings_payload(data: Any) -> list[EarningsPeriod]:
    """Parse Earnings history rows. Missing actuals/estimates stay unavailable, never 0."""
    periods: list[EarningsPeriod] = []
    for row in _earnings_rows(data):
        if not _looks_like_earnings_row(row):
            continue
        metrics = row[9]
        currency = metrics[16] if isinstance(metrics[16], str) else None
        periods.append(
            EarningsPeriod(
                year=int(row[3]),
                quarter=int(row[4]),
                period_end=_period_end_tuple(metrics[17] if len(metrics) > 17 else None),
                currency=currency,
                revenue_actual=_numeric_figure("actual", metrics[0] if len(metrics) > 0 else None),
                revenue_estimate=_numeric_figure("estimate", metrics[8] if len(metrics) > 8 else None),
                eps_actual=_numeric_figure("actual", metrics[9] if len(metrics) > 9 else None),
                eps_estimate=_numeric_figure("estimate", metrics[10] if len(metrics) > 10 else None),
                surprise=unavailable_figure("surprise"),
            )
        )
    return periods


_ABBREV_RE = re.compile(r"^([+-]?\d+(?:\.\d+)?)([TBM])$", re.I)
_PERCENT_RE = re.compile(r"^([+-]?\d+(?:\.\d+)?)%$")
_PLAIN_NUM_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_HEADER_PERIOD_RE = re.compile(
    r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(20\d{2})$",
    re.I,
)
_YEAR_RE = re.compile(r"^(20\d{2})$")
_TABLE_RE = re.compile(
    r'<table[^>]*aria-label="Income statement"[^>]*>(.*?)</table>',
    re.I | re.S,
)
_HEADER_RE = re.compile(r'<div class="nQ5Kpf[^"]*">([^<]*)</div>', re.I)
_LABEL_RE = re.compile(r'<div class="sp5q4e">([^<]+)</div>', re.I)
_CELL_RE = re.compile(r'<div class="CNzF7d">([^<]*)</div>', re.I)
_TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)


def expand_display_abbreviation(text: str) -> tuple[float | None, str]:
    """Expand a Google UI abbreviation. The stored dataset scale remains full units."""
    raw = html_lib.unescape(text).replace(",", "").replace("\xa0", "").strip()
    if raw in {"", "-", "—", "–"}:
        return None, "unavailable"
    match = _ABBREV_RE.fullmatch(raw)
    if match:
        number = float(match.group(1))
        factor = {"T": 1e12, "B": 1e9, "M": 1e6}[match.group(2).upper()]
        return number * factor, "display_abbreviation"
    match = _PERCENT_RE.fullmatch(raw)
    if match:
        return float(match.group(1)) / 100.0, "percent"
    cleaned = raw.replace("+", "")
    if _PLAIN_NUM_RE.fullmatch(cleaned):
        return float(cleaned), "full"
    return None, "unparsed"


def parse_income_statement_table(html: str) -> DisplayTable | None:
    match = _TABLE_RE.search(html)
    if not match:
        return None
    body = match.group(1)
    rows_html = _TR_RE.findall(body)
    if not rows_html:
        return None
    header_bits = _HEADER_RE.findall(rows_html[0])
    unit_note = header_bits[0].strip() if header_bits else None
    headers = tuple(h.strip() for h in header_bits[1:])
    parsed_rows: list[DisplayRow] = []
    for tr in rows_html[1:]:
        labels = _LABEL_RE.findall(tr)
        cells_raw = _CELL_RE.findall(tr)
        if not labels:
            continue
        cells: list[DisplayCell] = []
        for i, raw in enumerate(cells_raw):
            text = html_lib.unescape(raw).strip()
            numeric, kind = expand_display_abbreviation(text)
            header = headers[i] if i < len(headers) else ""
            availability = "unavailable" if kind == "unavailable" else ("present" if numeric is not None else "unavailable")
            cells.append(
                DisplayCell(
                    display_text=text,
                    availability=availability,
                    numeric=numeric,
                    period_header=header,
                )
            )
        parsed_rows.append(DisplayRow(label=html_lib.unescape(labels[0]).strip(), cells=tuple(cells)))
    if not parsed_rows:
        return None
    return DisplayTable(
        statement="income_statement",
        unit_note=unit_note,
        headers=headers,
        rows=tuple(parsed_rows),
    )


def header_to_period(header: str) -> tuple[int, int | None] | None:
    text = header.strip()
    match = _HEADER_PERIOD_RE.fullmatch(text)
    if match:
        return int(match.group(2)), _MONTHS[match.group(1)[:3].lower()]
    match = _YEAR_RE.fullmatch(text)
    if match:
        return int(match.group(1)), None
    return None


def _unwrap_financials_company(data: Any) -> list[Any] | None:
    node = data
    for _ in range(3):
        if isinstance(node, list) and len(node) == 1:
            node = node[0]
            continue
        break
    if not isinstance(node, list) or len(node) != 8:
        return None
    if not isinstance(node[0], list) or not isinstance(node[1], list):
        return None
    ticker = node[7]
    if not (isinstance(ticker, list) and len(ticker) == 2 and all(isinstance(x, str) for x in ticker)):
        return None
    return node


def _metric_currency(metrics: Any) -> str | None:
    if isinstance(metrics, list) and len(metrics) > 16 and isinstance(metrics[16], str):
        return metrics[16]
    return None


def _looks_like_metrics(value: Any) -> bool:
    if not isinstance(value, list) or len(value) < 17:
        return False
    return isinstance(value[16], str) and _period_end_tuple(value[17] if len(value) > 17 else None) is not None


def parse_financials_payload(data: Any) -> ParsedFinancials:
    """Walk Financials nested shape. Slot names are not taken from the AVGO enricher."""
    company = _unwrap_financials_company(data)
    if company is None:
        return ParsedFinancials(ticker=None, name=None, quarterly=(), annual=())
    quarterly_rows, annual_rows = company[0], company[1]
    name = company[6] if isinstance(company[6], str) else None
    ticker = (company[7][0], company[7][1])
    quarterly: list[MetricPeriod] = []
    for row in quarterly_rows:
        if not isinstance(row, list) or len(row) < 3:
            continue
        year, quarter, metrics = row[0], row[1], row[2]
        if not isinstance(year, int) or not isinstance(quarter, int) or quarter not in {1, 2, 3, 4}:
            continue
        if not _looks_like_metrics(metrics):
            continue
        comp = row[3] if len(row) > 3 else None
        quarterly.append(
            MetricPeriod(
                year=year,
                quarter=quarter,
                currency=_metric_currency(metrics),
                period_end=_period_end_tuple(metrics[17]),
                comparative_period_end=_period_end_tuple(comp[17]) if _looks_like_metrics(comp) else None,
                metrics=tuple(metrics),
                comparative_metrics=tuple(comp) if isinstance(comp, list) else None,
            )
        )
    annual: list[MetricPeriod] = []
    for row in annual_rows:
        if not isinstance(row, list) or len(row) < 2:
            continue
        year, metrics = row[0], row[1]
        if not isinstance(year, int) or isinstance(year, bool):
            continue
        if not _looks_like_metrics(metrics):
            continue
        comp = row[2] if len(row) > 2 else None
        annual.append(
            MetricPeriod(
                year=year,
                quarter=None,
                currency=_metric_currency(metrics),
                period_end=_period_end_tuple(metrics[17]),
                comparative_period_end=_period_end_tuple(comp[17]) if _looks_like_metrics(comp) else None,
                metrics=tuple(metrics),
                comparative_metrics=tuple(comp) if isinstance(comp, list) else None,
            )
        )
    return ParsedFinancials(ticker=ticker, name=name, quarterly=tuple(quarterly), annual=tuple(annual))


def _display_matches(metric: Any, cell: DisplayCell) -> bool:
    if cell.availability == "unavailable":
        return metric is None
    if metric is None or isinstance(metric, bool) or isinstance(metric, str):
        return False
    if not isinstance(metric, (int, float)):
        return False
    text = cell.display_text.strip()
    expanded, kind = expand_display_abbreviation(text)
    if kind == "unavailable":
        return False
    if kind == "display_abbreviation":
        suffix = text[-1].upper()
        factor = {"T": 1e12, "B": 1e9, "M": 1e6}[suffix]
        return round(float(metric) / factor, 2) == round(expanded / factor, 2)
    if kind == "percent":
        as_ratio = round(float(metric) * 100.0, 2)
        as_already_pct = round(float(metric), 2)
        shown = round(expanded * 100.0, 2)
        return as_ratio == shown or as_already_pct == shown
    if kind == "full":
        return round(float(metric), 2) == round(expanded, 2)
    return False


def period_matches_header(period: MetricPeriod, header: str) -> bool:
    parsed = header_to_period(header)
    if parsed is None or period.period_end is None:
        return False
    year, month = parsed
    if period.period_end[0] != year:
        return False
    if period.quarter is None:
        return month is None
    if month is None:
        return False
    return period.period_end[1] == month


def bind_display_labels(
    periods: tuple[MetricPeriod, ...],
    table: DisplayTable | None,
) -> dict[int, str]:
    """Bind Google original labels to metric indices only after display agreement."""
    if table is None or not periods:
        return {}
    bound: dict[int, str] = {}
    max_len = max((len(p.metrics) for p in periods), default=0)
    for display_row in table.rows:
        matching_indices: list[int] = []
        for index in range(max_len):
            if index in {16, 17}:
                continue
            ok = True
            saw = False
            for cell in display_row.cells:
                period = next((p for p in periods if period_matches_header(p, cell.period_header)), None)
                if period is None or index >= len(period.metrics):
                    continue
                saw = True
                if not _display_matches(period.metrics[index], cell):
                    ok = False
                    break
            if ok and saw:
                matching_indices.append(index)
        if len(matching_indices) == 1:
            bound[matching_indices[0]] = display_row.label
    return bound


def duration_for(statement: str, frequency: str) -> str:
    if statement == "balance_sheet":
        return "point_in_time"
    if statement == "cash_flow":
        return "period"
    return frequency
