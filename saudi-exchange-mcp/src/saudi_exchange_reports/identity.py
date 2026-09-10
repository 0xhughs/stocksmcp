"""Resolve Arabic/English names and tickers within the documented pilot sample."""

from __future__ import annotations

from saudi_exchange_reports.catalog import (
    FOREIGN_EXCHANGES,
    PILOT_COMPANIES,
    SAUDI_EXCHANGE_NAMES,
)
from saudi_exchange_reports.models import (
    CompanyIdentity,
    ResolveResult,
    ResolveStatus,
)

__all__ = ["ResolveStatus", "resolve_company"]


def _fold(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _is_ticker_query(value: str) -> bool:
    return value.strip().isdigit() and 3 <= len(value.strip()) <= 5


def _names_of(company: CompanyIdentity) -> tuple[str, ...]:
    return (company.english_name, company.arabic_name, *company.aliases)


def _name_matches(company: CompanyIdentity, name: str) -> bool:
    q = _fold(name)
    if not q:
        return False
    for candidate in _names_of(company):
        folded = _fold(candidate)
        if q == folded or q in folded or folded in q:
            return True
    return False


def _ticker_matches(company: CompanyIdentity, ticker: str) -> bool:
    return company.ticker == ticker.strip()


def _is_foreign_exchange(exchange: str | None) -> bool:
    if not exchange:
        return False
    folded = _fold(exchange)
    if folded in FOREIGN_EXCHANGES:
        return True
    return any(token == folded for token in FOREIGN_EXCHANGES)


def _is_saudi_exchange(exchange: str | None) -> bool:
    if not exchange:
        return True
    return _fold(exchange) in SAUDI_EXCHANGE_NAMES


def resolve_company(
    query: str | None = None,
    *,
    name: str | None = None,
    ticker: str | None = None,
    exchange: str | None = None,
) -> ResolveResult:
    """Resolve a company within the pilot sample.

    Never silently picks among ambiguous or conflicting inputs.
    """
    if query is not None and name is None and ticker is None:
        if _is_ticker_query(query):
            ticker = query.strip()
        else:
            name = query

    name = name.strip() if isinstance(name, str) and name.strip() else None
    ticker = ticker.strip() if isinstance(ticker, str) and ticker.strip() else None
    exchange = exchange.strip() if isinstance(exchange, str) and exchange.strip() else None

    if not name and not ticker:
        return ResolveResult(
            status=ResolveStatus.UNKNOWN,
            company=None,
            candidates=(),
            reason="No name or ticker was provided.",
        )

    if _is_foreign_exchange(exchange):
        return ResolveResult(
            status=ResolveStatus.WRONG_EXCHANGE,
            company=None,
            candidates=(),
            reason=(
                f"Exchange {exchange!r} is not Saudi Exchange / Tadawul. "
                "Identical tickers on other venues are not treated as the same company."
            ),
        )

    if exchange is not None and not _is_saudi_exchange(exchange):
        return ResolveResult(
            status=ResolveStatus.WRONG_EXCHANGE,
            company=None,
            candidates=(),
            reason=f"Exchange {exchange!r} is not a recognised Saudi Exchange market.",
        )

    name_hits = tuple(c for c in PILOT_COMPANIES if name and _name_matches(c, name))
    ticker_hits = tuple(c for c in PILOT_COMPANIES if ticker and _ticker_matches(c, ticker))

    if name and ticker:
        name_ids = {c.company_id for c in name_hits}
        ticker_ids = {c.company_id for c in ticker_hits}
        if name_hits and ticker_hits and name_ids.isdisjoint(ticker_ids):
            # Preserve name-hit order then ticker-hit order without duplicates.
            merged: list[CompanyIdentity] = []
            seen: set[str] = set()
            for company in (*name_hits, *ticker_hits):
                if company.company_id not in seen:
                    merged.append(company)
                    seen.add(company.company_id)
            return ResolveResult(
                status=ResolveStatus.CONFLICTING,
                company=None,
                candidates=tuple(merged),
                reason=(
                    f"Name {name!r} and ticker {ticker!r} resolve to different "
                    "pilot companies; refusing to pick one."
                ),
            )
        agreed = tuple(c for c in name_hits if c.company_id in ticker_ids)
        if len(agreed) == 1:
            return ResolveResult(
                status=ResolveStatus.MATCHED,
                company=agreed[0],
                candidates=agreed,
                reason="Name and ticker agree on one pilot company.",
            )
        if not agreed:
            return ResolveResult(
                status=ResolveStatus.NOT_FOUND,
                company=None,
                candidates=(),
                reason="Name and ticker combination is not in the pilot sample.",
            )

    hits = name_hits if name and not ticker else ticker_hits if ticker and not name else name_hits
    # When only one side is provided, use that side's hits.
    if name and not ticker:
        hits = name_hits
    elif ticker and not name:
        hits = ticker_hits

    if len(hits) > 1:
        return ResolveResult(
            status=ResolveStatus.AMBIGUOUS,
            company=None,
            candidates=hits,
            reason=(
                "Multiple pilot companies match this name; refusing to pick one."
            ),
        )
    if len(hits) == 1:
        return ResolveResult(
            status=ResolveStatus.MATCHED,
            company=hits[0],
            candidates=hits,
            reason="Resolved to a single company in the documented pilot sample.",
        )
    return ResolveResult(
        status=ResolveStatus.NOT_FOUND,
        company=None,
        candidates=(),
        reason="No company in the documented pilot sample matches this query.",
    )
