"""Compose shared identity with Google Finance overview, news, profile, inventory."""

from __future__ import annotations

from datetime import datetime, timezone

from saudi_exchange_reports.google_finance.mapping import MappingVerdict, verify_quote_page
from saudi_exchange_reports.google_finance.parse import (
    dataset_is_empty,
    labelled_html_about,
    labelled_html_stats,
    parse_news_rows,
    parse_profile_payload,
    parse_quote_summary,
)
from saudi_exchange_reports.google_finance.source import GoogleFinanceSource, LiveGoogleSource
from saudi_exchange_reports.google_finance.types import (
    AttachedIdentity,
    DatasetPurpose,
    InventoryResult,
    InventoryRow,
    NewsResult,
    OverviewResult,
    ProfileResult,
)
from saudi_exchange_reports.identity import ResolveStatus, resolve_company
from saudi_exchange_reports.models import CompanyIdentity

UTC = timezone.utc

_PRODUCT_STATUS: dict[DatasetPurpose, str] = {
    DatasetPurpose.QUOTE_SUMMARY: "support",
    DatasetPurpose.QUOTE_SUMMARY_ALTERNATE: "support",
    DatasetPurpose.SECURITY_OVERVIEW: "support",
    DatasetPurpose.SECURITY_OVERVIEW_ALTERNATE: "support",
    DatasetPurpose.MARKET_STATISTICS: "support",
    DatasetPurpose.COMPANY_PROFILE: "support",
    DatasetPurpose.SECURITY_NEWS: "support",
    DatasetPurpose.MARKET_NEWS: "observe",
    DatasetPurpose.EARNINGS_HISTORY: "defer",
    DatasetPurpose.EARNINGS_HISTORY_ALTERNATE: "defer",
    DatasetPurpose.FINANCIALS: "defer",
    DatasetPurpose.INTRADAY_CHART: "observe",
    DatasetPurpose.RELATED_SECURITIES: "observe",
    DatasetPurpose.ANALYST_RATINGS: "observe",
    DatasetPurpose.EQUITY_SECTORS: "observe",
    DatasetPurpose.MARKET_OVERVIEW: "observe",
    DatasetPurpose.EMPTY_INIT: "non_data",
    DatasetPurpose.UNKNOWN: "observe",
}


def _require_company(query: str) -> CompanyIdentity:
    result = resolve_company(query)
    if result.status is not ResolveStatus.MATCHED or result.company is None:
        raise ValueError(result.reason)
    company = result.company
    if not company.google_finance.verified or not company.google_finance.quote_id:
        raise ValueError("No verified Google Finance mapping on this identity.")
    return company


def _source(source: GoogleFinanceSource | None) -> GoogleFinanceSource:
    return source if source is not None else LiveGoogleSource()


def _verified_page(company: CompanyIdentity, source: GoogleFinanceSource):
    page = source.load_quote_page(company)
    verdict = verify_quote_page(page.html, page.url, company)
    if verdict.status is not MappingVerdict.MATCHED:
        raise ValueError(verdict.reason)
    return page


def get_overview(query: str, *, source: GoogleFinanceSource | None = None) -> OverviewResult:
    source = _source(source)
    company = _require_company(query)
    page = _verified_page(company, source)
    retrieved_at = datetime.now(UTC)
    quote = source.call_purpose(page, DatasetPurpose.QUOTE_SUMMARY)
    parsed = parse_quote_summary(quote.data) if not dataset_is_empty(quote.data) else {}
    stats = labelled_html_stats(page.html)
    previous_close = _float_stat(stats.get("Previous close"))
    day_range = stats.get("Day range") or _range_from_high_low(stats)
    year_range = stats.get("Year range") or _year_range(stats)
    market_cap = stats.get("Market cap") or stats.get("Mkt. cap")
    pe_ratio = stats.get("P/E ratio")
    volume = stats.get("Volume")
    dividend_yield = stats.get("Dividend yield") or stats.get("Dividend")
    primary_exchange = stats.get("Primary exchange")
    unavailable: list[str] = []
    last = parsed.get("last")
    if last is None:
        unavailable.append("last")
    quoted_at = parsed.get("quoted_at")
    freshness = "quoted_at" if quoted_at is not None else "unknown"
    if quoted_at is None:
        unavailable.append("quoted_at")
    if previous_close is None:
        unavailable.append("previous_close")
    if not market_cap:
        source.call_purpose(page, DatasetPurpose.SECURITY_OVERVIEW)
    return OverviewResult(
        identity=AttachedIdentity.from_company(company),
        display_name=parsed.get("display_name"),
        last=last,
        change=parsed.get("change"),
        percent_change=parsed.get("percent_change"),
        currency=parsed.get("currency"),
        source_url=page.url,
        retrieved_at=retrieved_at,
        quoted_at=quoted_at,
        quote_timezone=parsed.get("quote_timezone"),
        session=parsed.get("session"),
        delay=None,
        previous_close=previous_close,
        day_range=day_range,
        year_range=year_range,
        market_cap=market_cap,
        pe_ratio=pe_ratio,
        volume=volume,
        dividend_yield=dividend_yield,
        primary_exchange=primary_exchange,
        freshness=freshness,
        is_realtime=False,
        unavailable=tuple(unavailable),
        source_dataset="quote_summary" if parsed else None,
        google_rpc_id=None,
    )


def get_news(query: str, *, source: GoogleFinanceSource | None = None) -> NewsResult:
    source = _source(source)
    company = _require_company(query)
    page = _verified_page(company, source)
    retrieved_at = datetime.now(UTC)
    response = source.call_purpose(page, DatasetPurpose.SECURITY_NEWS)
    items = tuple(parse_news_rows(response.data))
    unavailable: list[str] = []
    if not items:
        unavailable.append("news")
    return NewsResult(
        identity=AttachedIdentity.from_company(company),
        items=items,
        unavailable=tuple(unavailable),
        source_url=page.url,
        retrieved_at=retrieved_at,
        feed="security",
    )


def get_profile(query: str, *, source: GoogleFinanceSource | None = None) -> ProfileResult:
    source = _source(source)
    company = _require_company(query)
    page = _verified_page(company, source)
    retrieved_at = datetime.now(UTC)
    response = source.call_purpose(page, DatasetPurpose.COMPANY_PROFILE)
    parsed = parse_profile_payload(response.data) if not dataset_is_empty(response.data) else {}
    about = labelled_html_about(page.html)
    description = parsed.get("description")
    website = parsed.get("website") or _clean_dash(about.get("Website"))
    ceo = parsed.get("ceo") or _clean_dash(about.get("CEO"))
    founded = parsed.get("founded_year")
    if founded is None and about.get("Founded", "").isdigit():
        founded = int(about["Founded"])
    headquarters = _clean_dash(about.get("Headquarters"))
    employees = parsed.get("employees") or _clean_dash(about.get("Employees"))
    sector = parsed.get("sector") or _clean_dash(about.get("Sector"))
    unavailable: list[str] = []
    if not description:
        unavailable.append("description")
    if not website:
        unavailable.append("website")
    if not ceo:
        unavailable.append("ceo")
    if founded is None:
        unavailable.append("founded_year")
    if not headquarters:
        unavailable.append("headquarters")
    if not employees:
        unavailable.append("employees")
    if not sector:
        unavailable.append("sector")
    return ProfileResult(
        identity=AttachedIdentity.from_company(company),
        description=description,
        website=website,
        ceo=ceo,
        founded_year=founded,
        headquarters=headquarters,
        employees=employees,
        sector=sector,
        unavailable=tuple(unavailable),
        source_url=page.url,
        retrieved_at=retrieved_at,
    )


def get_inventory(query: str, *, source: GoogleFinanceSource | None = None) -> InventoryResult:
    source = _source(source)
    company = _require_company(query)
    page = _verified_page(company, source)
    retrieved_at = datetime.now(UTC)
    rows = tuple(
        InventoryRow(
            purpose=ds.purpose.value,
            product=_PRODUCT_STATUS.get(ds.purpose, "observe"),
            empty=ds.empty,
            key=ds.key,
            rpc_id_hidden=True,
            upstream_purpose=ds.upstream_purpose,
        )
        for ds in page.datasets
    )
    return InventoryResult(
        identity=AttachedIdentity.from_company(company),
        datasets=rows,
        source_url=page.url,
        retrieved_at=retrieved_at,
        product_api_hides_rpc_ids=True,
    )


def _clean_dash(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped == "-":
        return None
    return stripped


def _float_stat(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.replace(",", "").replace("\xa0", " ").strip()
    cleaned = cleaned.split()[-1] if cleaned[:3].isalpha() else cleaned
    try:
        return float(cleaned)
    except ValueError:
        return None


def _range_from_high_low(stats: dict[str, str]) -> str | None:
    high = stats.get("High")
    low = stats.get("Low")
    if high and low:
        return f"{low} - {high}"
    return None


def _year_range(stats: dict[str, str]) -> str | None:
    high = stats.get("52-wk high")
    low = stats.get("52-wk low")
    if high and low:
        return f"{low} - {high}"
    return None
