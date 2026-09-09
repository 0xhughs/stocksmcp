"""Shared company identity with distinct Saudi Exchange identifiers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResolveStatus(Enum):
    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"
    WRONG_EXCHANGE = "wrong_exchange"
    NOT_FOUND = "not_found"


class ReportType(Enum):
    ANNUAL = "annual"
    INTERIM = "interim"
    OTHER = "other"


@dataclass(frozen=True)
class SaudiExchangeIdentifiers:
    """Provider-specific identifiers for Saudi Exchange. Distinct from Google."""

    company_symbol: str
    profile_url: str
    market: str
    issuer_id: str | None = None


@dataclass(frozen=True)
class GoogleFinanceMapping:
    """Placeholder slot for slice 03. Not validated in slice 01."""

    quote_symbol: str | None = None
    verified: bool = False


@dataclass(frozen=True)
class CompanyIdentity:
    company_id: str
    english_name: str
    arabic_name: str
    ticker: str
    exchange: str
    aliases: tuple[str, ...]
    saudi_exchange: SaudiExchangeIdentifiers
    google_finance: GoogleFinanceMapping


@dataclass(frozen=True)
class ResolveResult:
    status: ResolveStatus
    company: CompanyIdentity | None
    candidates: tuple[CompanyIdentity, ...]
    reason: str


@dataclass(frozen=True)
class FinancialReport:
    title: str
    period: str
    report_type: ReportType
    language: str
    source_url: str
    download_url: str
    publication_date: str | None
    publication_date_unavailable: bool
    section: str | None = None
    company_ticker: str | None = None


@dataclass(frozen=True)
class ReportListing:
    reports: tuple[FinancialReport, ...]
    from_cache: bool
    retrieved_at: str | None
    unavailable: bool
    reason: str
    source_url: str | None = None


@dataclass(frozen=True)
class ReportSelection:
    status: str
    report: FinancialReport | None
    candidates: tuple[FinancialReport, ...]
    reason: str
