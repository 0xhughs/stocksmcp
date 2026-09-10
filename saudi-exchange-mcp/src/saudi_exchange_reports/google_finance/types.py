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
    CURRENT_EARNINGS_DETAIL = "current_earnings_detail"
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


@dataclass(frozen=True)
class LabeledFigure:
    """A Google figure that is either present or explicitly unavailable (never coerced to 0)."""

    value: float | None
    kind: str
    availability: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "kind": self.kind,
            "availability": self.availability,
        }


def unavailable_figure(kind: str) -> LabeledFigure:
    return LabeledFigure(value=None, kind=kind, availability="unavailable")


def present_figure(kind: str, value: float) -> LabeledFigure:
    return LabeledFigure(value=value, kind=kind, availability="present")


@dataclass(frozen=True)
class EarningsPeriod:
    year: int
    quarter: int
    period_end: tuple[int, int, int] | None
    currency: str | None
    revenue_actual: LabeledFigure
    revenue_estimate: LabeledFigure
    eps_actual: LabeledFigure
    eps_estimate: LabeledFigure
    surprise: LabeledFigure

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "quarter": self.quarter,
            "period_end": list(self.period_end) if self.period_end else None,
            "currency": self.currency,
            "revenue_actual": self.revenue_actual.to_dict(),
            "revenue_estimate": self.revenue_estimate.to_dict(),
            "eps_actual": self.eps_actual.to_dict(),
            "eps_estimate": self.eps_estimate.to_dict(),
            "surprise": self.surprise.to_dict(),
        }


@dataclass(frozen=True)
class EarningsResult:
    identity: AttachedIdentity
    periods: tuple[EarningsPeriod, ...]
    unavailable: tuple[str, ...]
    source_url: str
    retrieved_at: datetime
    earnings_html_loading: bool = False
    used_alternate_fallback: bool = False
    alternate_deduplicated: bool = False
    source_dataset: str | None = "earnings_history"
    article_summary: None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "periods": [p.to_dict() for p in self.periods],
            "unavailable": list(self.unavailable),
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at.isoformat(),
            "earnings_html_loading": self.earnings_html_loading,
            "used_alternate_fallback": self.used_alternate_fallback,
            "alternate_deduplicated": self.alternate_deduplicated,
            "source_dataset": self.source_dataset,
            "article_summary": self.article_summary,
        }


@dataclass(frozen=True)
class DisplayCell:
    display_text: str
    availability: str
    numeric: float | None
    period_header: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "display_text": self.display_text,
            "availability": self.availability,
            "numeric": self.numeric,
            "period_header": self.period_header,
        }


@dataclass(frozen=True)
class DisplayRow:
    label: str
    cells: tuple[DisplayCell, ...]


@dataclass(frozen=True)
class DisplayTable:
    statement: str
    unit_note: str | None
    headers: tuple[str, ...]
    rows: tuple[DisplayRow, ...]


@dataclass(frozen=True)
class MetricPeriod:
    year: int
    quarter: int | None
    currency: str | None
    period_end: tuple[int, int, int] | None
    comparative_period_end: tuple[int, int, int] | None
    metrics: tuple[Any, ...]
    comparative_metrics: tuple[Any, ...] | None


@dataclass(frozen=True)
class ParsedFinancials:
    ticker: tuple[str, str] | None
    name: str | None
    quarterly: tuple[MetricPeriod, ...]
    annual: tuple[MetricPeriod, ...]


@dataclass(frozen=True)
class StatementRow:
    label: str | None
    original_label: str | None
    value: float | None
    scale: str
    currency: str | None
    label_status: str
    availability: str
    display_text: str | None = None
    slot_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "original_label": self.original_label,
            "value": self.value,
            "scale": self.scale,
            "currency": self.currency,
            "label_status": self.label_status,
            "availability": self.availability,
            "display_text": self.display_text,
        }


@dataclass(frozen=True)
class StatementPeriod:
    year: int
    quarter: int | None
    period_end: tuple[int, int, int] | None
    comparative_period_end: tuple[int, int, int] | None
    currency: str | None
    duration: str
    rows: tuple[StatementRow, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "quarter": self.quarter,
            "period_end": list(self.period_end) if self.period_end else None,
            "comparative_period_end": list(self.comparative_period_end) if self.comparative_period_end else None,
            "currency": self.currency,
            "duration": self.duration,
            "rows": [row.to_dict() for row in self.rows],
        }


@dataclass(frozen=True)
class FinancialsResult:
    identity: AttachedIdentity
    statement: str
    frequency: str
    periods: tuple[StatementPeriod, ...]
    unavailable: tuple[str, ...]
    source_url: str
    retrieved_at: datetime
    source_dataset: str | None = "financials"
    display_label_gap: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "statement": self.statement,
            "frequency": self.frequency,
            "periods": [p.to_dict() for p in self.periods],
            "unavailable": list(self.unavailable),
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at.isoformat(),
            "source_dataset": self.source_dataset,
            "display_label_gap": self.display_label_gap,
        }


@dataclass(frozen=True)
class CoverageSection:
    section: str
    frequency: str
    status: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "section": self.section,
            "frequency": self.frequency,
            "status": self.status,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CoverageResult:
    identity: AttachedIdentity
    retrieved_at: datetime
    source_url: str
    sections: tuple[CoverageSection, ...]
    gap_classes: tuple[dict[str, Any], ...]
    dated: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "retrieved_at": self.retrieved_at.isoformat(),
            "source_url": self.source_url,
            "dated": self.dated or self.retrieved_at.date().isoformat(),
            "sections": [s.to_dict() for s in self.sections],
            "gap_classes": list(self.gap_classes),
        }


@dataclass(frozen=True)
class CrosscheckResult:
    identity: AttachedIdentity
    pairs: tuple[Any, ...]
    google_is_not_audited: bool
    google_frequency: str
    source_url: str
    retrieved_at: datetime
    pdf_content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "google_is_not_audited": self.google_is_not_audited,
            "google_frequency": self.google_frequency,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at.isoformat(),
            "pdf_content_hash": self.pdf_content_hash,
            "pairs": [p.to_dict() if hasattr(p, "to_dict") else p for p in self.pairs],
        }
