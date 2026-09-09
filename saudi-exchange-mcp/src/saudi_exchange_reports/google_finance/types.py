"""Product types for the Google Finance research branch.

Dataset keys (`ds:N`) and RPC ids are kept on internal objects for selection
and tests. Public JSON omits RPC ids. Overview/news/profile results expose
stable purpose names, not live hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from saudi_exchange_reports.models import CompanyIdentity, GoogleFinanceMapping


class DatasetPurpose(str, Enum):
    QUOTE_SUMMARY = "quote_summary"
    QUOTE_SUMMARY_ALTERNATE = "quote_summary_alternate"
    COMPANY_PROFILE = "company_profile"
    MARKET_STATISTICS = "market_statistics"
    SECURITY_OVERVIEW = "security_overview"
    SECURITY_OVERVIEW_ALTERNATE = "security_overview_alternate"
    SECURITY_NEWS = "security_news"
    MARKET_NEWS = "market_news"
    EARNINGS_HISTORY = "earnings_history"
    EARNINGS_HISTORY_ALTERNATE = "earnings_history_alternate"
    FINANCIALS = "financials"
    INTRADAY_CHART = "intraday_chart"
    RELATED_SECURITIES = "related_securities"
    ANALYST_RATINGS = "analyst_ratings"
    EQUITY_SECTORS = "equity_sectors"
    MARKET_OVERVIEW = "market_overview"
    EMPTY_INIT = "empty_init"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DatasetMetadata:
    key: str
    hash_id: str
    rpc_id: str
    purpose: DatasetPurpose
    empty: bool = False
    upstream_purpose: str = ""


@dataclass(frozen=True)
class QuotePage:
    url: str
    html: str
    datasets: tuple[DatasetMetadata, ...]
    source_path: str = ""
    batchexecute_url: str = ""


@dataclass(frozen=True)
class DatasetResponse:
    id: str
    rpc_id: str
    data: Any
    error: str | None = None


@dataclass(frozen=True)
class FetchResult:
    html: str
    final_url: str


@dataclass(frozen=True)
class AttachedIdentity:
    company_id: str
    ticker: str
    english_name: str
    google: GoogleFinanceMapping

    @classmethod
    def from_company(cls, company: CompanyIdentity) -> AttachedIdentity:
        return cls(
            company_id=company.company_id,
            ticker=company.ticker,
            english_name=company.english_name,
            google=company.google_finance,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "ticker": self.ticker,
            "english_name": self.english_name,
            "google": {
                "quote_symbol": self.google.quote_symbol,
                "exchange": self.google.exchange,
                "quote_id": self.google.quote_id,
                "quote_url": self.google.quote_url,
                "verified": self.google.verified,
            },
        }


@dataclass(frozen=True)
class OverviewResult:
    identity: AttachedIdentity
    display_name: str | None
    last: float | None
    change: float | None
    percent_change: float | None
    currency: str | None
    source_url: str
    retrieved_at: datetime
    quoted_at: datetime | None
    quote_timezone: str | None
    session: str | None
    delay: str | None
    previous_close: float | None
    day_range: str | None
    year_range: str | None
    market_cap: str | None
    pe_ratio: str | None
    volume: str | None
    dividend_yield: str | None
    primary_exchange: str | None
    freshness: str
    is_realtime: bool
    unavailable: tuple[str, ...]
    source_dataset: str | None
    google_rpc_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "display_name": self.display_name,
            "last": self.last,
            "change": self.change,
            "percent_change": self.percent_change,
            "currency": self.currency,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at.isoformat(),
            "quoted_at": self.quoted_at.isoformat() if self.quoted_at else None,
            "quote_timezone": self.quote_timezone,
            "session": self.session,
            "delay": self.delay,
            "previous_close": self.previous_close,
            "day_range": self.day_range,
            "year_range": self.year_range,
            "market_cap": self.market_cap,
            "pe_ratio": self.pe_ratio,
            "volume": self.volume,
            "dividend_yield": self.dividend_yield,
            "primary_exchange": self.primary_exchange,
            "freshness": self.freshness,
            "is_realtime": self.is_realtime,
            "unavailable": list(self.unavailable),
            "source_dataset": self.source_dataset,
        }


@dataclass(frozen=True)
class NewsItem:
    url: str | None
    headline: str | None
    publisher: str | None
    published_at: datetime | None
    snippet: str | None
    article_body: None
    read_status: str
    unavailable: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "headline": self.headline,
            "publisher": self.publisher,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "snippet": self.snippet,
            "article_body": self.article_body,
            "read_status": self.read_status,
            "unavailable": list(self.unavailable),
        }


@dataclass(frozen=True)
class NewsResult:
    identity: AttachedIdentity
    items: tuple[NewsItem, ...]
    unavailable: tuple[str, ...]
    source_url: str
    retrieved_at: datetime
    feed: str = "security"

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "feed": self.feed,
            "items": [item.to_dict() for item in self.items],
            "unavailable": list(self.unavailable),
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at.isoformat(),
        }


@dataclass(frozen=True)
class ProfileResult:
    identity: AttachedIdentity
    description: str | None
    website: str | None
    ceo: str | None
    founded_year: int | None
    headquarters: str | None
    employees: str | None
    sector: str | None
    unavailable: tuple[str, ...]
    source_url: str
    retrieved_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "description": self.description,
            "website": self.website,
            "ceo": self.ceo,
            "founded_year": self.founded_year,
            "headquarters": self.headquarters,
            "employees": self.employees,
            "sector": self.sector,
            "unavailable": list(self.unavailable),
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at.isoformat(),
        }


@dataclass(frozen=True)
class InventoryRow:
    purpose: str
    product: str
    empty: bool
    key: str
    rpc_id_hidden: bool = True
    upstream_purpose: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "purpose": self.purpose,
            "product": self.product,
            "empty": self.empty,
            "rpc_id_hidden": self.rpc_id_hidden,
            "upstream_purpose": self.upstream_purpose,
        }


@dataclass(frozen=True)
class InventoryResult:
    identity: AttachedIdentity
    datasets: tuple[InventoryRow, ...]
    source_url: str
    retrieved_at: datetime
    product_api_hides_rpc_ids: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "datasets": [row.to_dict() for row in self.datasets],
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at.isoformat(),
            "product_api_hides_rpc_ids": self.product_api_hides_rpc_ids,
        }
