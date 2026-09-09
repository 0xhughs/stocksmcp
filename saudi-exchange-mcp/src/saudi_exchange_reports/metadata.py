"""Financial metadata only when the document states it. Missing stays unknown."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MetadataField:
    status: str
    value: str | None = None
    evidence: str | None = None
    page_number: int | None = None


@dataclass(frozen=True)
class FinancialMetadata:
    currency: MetadataField
    scale: MetadataField
    period: MetadataField
    duration: MetadataField
    quarterly_vs_cumulative: MetadataField
    scope: MetadataField
    restatement: MetadataField


def _unknown() -> MetadataField:
    return MetadataField(status="unknown", value=None, evidence=None, page_number=None)


def _stated(value: str, evidence: str, page_number: int | None = None) -> MetadataField:
    return MetadataField(status="stated", value=value, evidence=evidence, page_number=page_number)


def _page_blob(pages: list[tuple[int, str]]) -> str:
    return "\n".join(text for _n, text in pages)


def infer_financial_metadata(pages: list[tuple[int, str]]) -> FinancialMetadata:
    blob = _page_blob(pages)
    return FinancialMetadata(
        currency=_currency(pages, blob),
        scale=_scale(pages, blob),
        period=_period(pages, blob),
        duration=_duration(pages, blob),
        quarterly_vs_cumulative=_quarterly_vs_cumulative(blob),
        scope=_scope(blob),
        restatement=_restatement(blob),
    )


def _find_page(pages: list[tuple[int, str]], needle: str) -> int | None:
    low = needle.lower()
    for number, text in pages:
        if low in text.lower():
            return number
    return None


def _currency(pages: list[tuple[int, str]], blob: str) -> MetadataField:
    low = blob.lower()
    if "saudi riyals" in low or "saudi riyal" in low:
        evidence = "Saudi Riyals"
        page = _find_page(pages, "Saudi Riyals")
        value = "Saudi Riyals (SAR)" if re.search(r"\bSAR\b", blob) else "Saudi Riyals"
        return _stated(value, evidence, page)
    if re.search(r"\bSAR\b", blob):
        return _stated("SAR", "SAR", _find_page(pages, "SAR"))
    return _unknown()


def _scale(pages: list[tuple[int, str]], blob: str) -> MetadataField:
    low = blob.lower()
    if re.search(r"in thousands(?: of)?(?: saudi riyals)?", low) or "thousands of saudi" in low:
        return _stated("thousands", "in thousands", _find_page(pages, "thousands"))
    if re.search(r"in millions(?: of)?(?: saudi riyals)?", low) or "sar million" in low:
        return _stated("millions", "in millions", _find_page(pages, "millions"))
    if "unless otherwise stated" in low and ("saudi riyals" in low or "sar" in low):
        return _stated(
            "full riyals (as stated)",
            "All amounts in Saudi Riyals unless otherwise stated",
            _find_page(pages, "unless otherwise stated"),
        )
    if "saudi riyals" in low and "thousand" not in low and "million" not in low:
        return _stated(
            "full riyals (as stated)",
            "Saudi Riyals",
            _find_page(pages, "Saudi Riyals"),
        )
    return _unknown()


def _period(pages: list[tuple[int, str]], blob: str) -> MetadataField:
    match = re.search(
        r"((?:three|six|nine)[-\s]month period ended \d{1,2} \w+ \d{4}|year ended \d{1,2} \w+ \d{4}|period ended \d{1,2} \w+ \d{4})",
        blob,
        flags=re.I,
    )
    if match:
        value = re.sub(r"\s+", " ", match.group(1)).strip()
        return _stated(value, value, _find_page(pages, match.group(1)))
    return _unknown()


def _duration(pages: list[tuple[int, str]], blob: str) -> MetadataField:
    low = blob.lower()
    if "year ended" in low:
        return _stated("year", "year ended", _find_page(pages, "year ended"))
    if "nine-month" in low or "nine month" in low:
        return _stated("nine months", "nine-month", _find_page(pages, "nine"))
    if "three-month" in low or "three month" in low:
        return _stated("three months", "three-month", _find_page(pages, "three-month") or _find_page(pages, "three month"))
    if "six-month" in low or "six month" in low:
        return _stated("six months", "six-month", _find_page(pages, "six-month") or _find_page(pages, "six month"))
    return _unknown()


def _quarterly_vs_cumulative(blob: str) -> MetadataField:
    low = blob.lower()
    quarterly = "quarterly" in low or "three-month" in low or "three month" in low
    cumulative = "cumulative" in low or "nine-month" in low or "nine month" in low or "year to date" in low or "year-to-date" in low
    if quarterly and cumulative:
        return _stated(
            "quarterly (three-month) and cumulative (nine-month / YTD)",
            "quarterly vs cumulative labels",
            None,
        )
    return _unknown()


def _scope(blob: str) -> MetadataField:
    low = blob.lower()
    # Negative language that is not the statements being read.
    stripped = re.sub(r"standalone selling price", " ", low)
    stripped = re.sub(
        r"separate financial statements prepared for zakat[^\n.]*",
        " ",
        stripped,
    )
    stripped = re.sub(r"separate performance obligations", " ", stripped)
    if re.search(r"these standalone financial statements", stripped) or re.search(
        r"standalone financial statements", stripped
    ):
        if "consolidated financial statements" not in stripped:
            return _stated("standalone", "standalone financial statements", None)
    if re.search(r"separate financial statements of the parent", stripped):
        return _stated("standalone/separate", "separate financial statements of the parent", None)
    if "consolidated financial statements" in stripped or "consolidated statement of" in stripped:
        return _stated("consolidated", "consolidated financial statements", None)
    return _unknown()


def _restatement(blob: str) -> MetadataField:
    low = blob.lower()
    if "measuring unit" in low and "restated" in low:
        # IAS 29 / hyperinflation measuring-unit language is not a comparative restatement.
        comparative = re.search(
            r"comparative(?:s| figures)?(?: for 20\d{2})? (?:have been |were )?restated",
            low,
        )
        year_col = re.search(r"\b20\d{2} restated\b", low)
        if not comparative and not year_col:
            return _unknown()
    if re.search(r"comparative(?:s| figures)?(?: for 20\d{2})? (?:have been |were )?restated", low):
        return _stated("comparatives restated", "comparative figures restated", None)
    if re.search(r"restated comparatives", low):
        return _stated("comparatives restated", "restated comparatives", None)
    if re.search(r"\b20\d{2} restated\b", low):
        return _stated("comparatives restated", "year restated", None)
    return _unknown()
