"""Verify Google Finance quote pages against an existing shared identity."""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlsplit

from saudi_exchange_reports.models import CompanyIdentity

REJECTED_EXCHANGES = frozenset({"SAU"})
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_QUOTE_PATH_RE = re.compile(
    r"/finance/(?:beta/)?quote/([^/?#]+)",
    re.IGNORECASE,
)


class MappingVerdict(Enum):
    MATCHED = "matched"
    REJECTED = "rejected"
    MISMATCH = "mismatch"


@dataclass(frozen=True)
class QuotePageVerdict:
    status: MappingVerdict
    quote_id: str | None
    company_id: str | None
    reason: str


def quote_id_from_url(url: str) -> str | None:
    path = urlsplit(url).path
    match = _QUOTE_PATH_RE.search(path)
    if not match:
        return None
    token = match.group(1).strip()
    if ":" not in token:
        return None
    symbol, exchange = token.split(":", 1)
    if not symbol or not exchange:
        return None
    return f"{symbol}:{exchange.upper()}"


def _page_title(html: str) -> str:
    match = _TITLE_RE.search(html)
    if not match:
        return ""
    return html_lib.unescape(re.sub(r"\s+", " ", match.group(1))).strip()


def _name_tokens(company: CompanyIdentity) -> tuple[str, ...]:
    names = (company.english_name, company.arabic_name, *company.aliases)
    tokens: list[str] = []
    for name in names:
        folded = name.strip()
        if folded:
            tokens.append(folded.casefold())
    return tuple(tokens)


def _title_mentions_company(title: str, company: CompanyIdentity) -> bool:
    folded = title.casefold()
    if not folded or folded == "google finance":
        return False
    if company.ticker not in title:
        return False
    return any(token in folded for token in _name_tokens(company) if len(token) >= 4)


def verify_quote_page(html: str, final_url: str, identity: CompanyIdentity) -> QuotePageVerdict:
    """Confirm a Google quote page belongs to the given shared identity.

    A related-security mention of another ticker on the page does not attach or
    swap identity. `2222:SAU` / `1211:SAU` are rejected (not Tadawul listings).
    """
    quote_id = quote_id_from_url(final_url)
    title = _page_title(html)
    if quote_id is None:
        return QuotePageVerdict(
            status=MappingVerdict.REJECTED,
            quote_id=None,
            company_id=identity.company_id,
            reason="Quote URL did not contain a SYMBOL:EXCHANGE path.",
        )
    symbol, exchange = quote_id.split(":", 1)
    if exchange in REJECTED_EXCHANGES:
        return QuotePageVerdict(
            status=MappingVerdict.REJECTED,
            quote_id=quote_id,
            company_id=identity.company_id,
            reason=(
                f"{quote_id} is not a verified Tadawul mapping; "
                "identical numeric tickers on other venues are not the same company."
            ),
        )
    if not _title_mentions_company(title, identity):
        if title.casefold() in {"", "google finance"}:
            return QuotePageVerdict(
                status=MappingVerdict.REJECTED,
                quote_id=quote_id,
                company_id=identity.company_id,
                reason=(
                    f"Page title {title!r} does not identify the company; "
                    "refusing to treat this listing as verified."
                ),
            )
        return QuotePageVerdict(
            status=MappingVerdict.MISMATCH,
            quote_id=quote_id,
            company_id=identity.company_id,
            reason=(
                f"Google page title {title!r} does not agree with identity "
                f"{identity.company_id} ticker {identity.ticker}."
            ),
        )
    if symbol != identity.ticker:
        return QuotePageVerdict(
            status=MappingVerdict.MISMATCH,
            quote_id=quote_id,
            company_id=identity.company_id,
            reason=(
                f"Quote {quote_id} does not match identity ticker {identity.ticker}; "
                "refusing to swap or create a second company."
            ),
        )
    if identity.google_finance.quote_id and identity.google_finance.quote_id != quote_id:
        return QuotePageVerdict(
            status=MappingVerdict.MISMATCH,
            quote_id=quote_id,
            company_id=identity.company_id,
            reason=(
                f"Page quote {quote_id} disagrees with stored mapping "
                f"{identity.google_finance.quote_id}."
            ),
        )
    return QuotePageVerdict(
        status=MappingVerdict.MATCHED,
        quote_id=quote_id,
        company_id=identity.company_id,
        reason="Google page company/ticker agrees with the shared identity.",
    )
