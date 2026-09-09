"""Compose shared identity with Google Finance overview, news, profile, inventory."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from saudi_exchange_reports.google_finance.mapping import MappingVerdict, verify_quote_page
from saudi_exchange_reports.google_finance.parse import (
    bind_display_labels,
    dataset_is_empty,
    duration_for,
    earnings_html_is_loading,
    labelled_html_about,
    labelled_html_stats,
    parse_earnings_payload,
    parse_financials_payload,
    parse_income_statement_table,
    parse_news_rows,
    parse_profile_payload,
    parse_quote_summary,
    period_matches_header,
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
    EarningsResult,
    FinancialsResult,
    MetricPeriod,
    StatementPeriod,
    StatementRow,
    CoverageResult,
    CoverageSection,
    CrosscheckResult,
)
from saudi_exchange_reports.identity import ResolveStatus, resolve_company
from saudi_exchange_reports.models import CompanyIdentity
from saudi_exchange_reports.reading import extract_report

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
    DatasetPurpose.EARNINGS_HISTORY: "support",
    DatasetPurpose.EARNINGS_HISTORY_ALTERNATE: "support",
    DatasetPurpose.CURRENT_EARNINGS_DETAIL: "observe",
    DatasetPurpose.FINANCIALS: "support",
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


def get_earnings(query: str, *, source: GoogleFinanceSource | None = None) -> EarningsResult:
    source = _source(source)
    company = _require_company(query)
    page = _verified_page(company, source)
    retrieved_at = datetime.now(UTC)
    response = source.call_purpose(page, DatasetPurpose.EARNINGS_HISTORY)
    used_alternate = getattr(source, "last_used_purpose", None) is DatasetPurpose.EARNINGS_HISTORY_ALTERNATE
    periods = tuple(parse_earnings_payload(response.data))
    advertised = {ds.purpose for ds in page.datasets}
    both_advertised = (
        DatasetPurpose.EARNINGS_HISTORY in advertised
        and DatasetPurpose.EARNINGS_HISTORY_ALTERNATE in advertised
    )
    unavailable: list[str] = []
    if not periods:
        unavailable.append("earnings")
    loading = earnings_html_is_loading(page.html)
    if loading and not periods:
        # Loading HTML is not proof of no earnings; still record the empty dataset.
        unavailable.append("earnings_dataset")
    return EarningsResult(
        identity=AttachedIdentity.from_company(company),
        periods=periods,
        unavailable=tuple(unavailable),
        source_url=page.url,
        retrieved_at=retrieved_at,
        earnings_html_loading=loading,
        used_alternate_fallback=used_alternate,
        alternate_deduplicated=bool(both_advertised and periods and not used_alternate),
        source_dataset="earnings_history_alternate" if used_alternate else "earnings_history",
        article_summary=None,
    )


_SKIP_METRIC_INDEXES = frozenset({16, 17})


def _as_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _display_text_for(period: MetricPeriod, label: str, table) -> str | None:
    if table is None:
        return None
    for row in table.rows:
        if row.label != label:
            continue
        for cell in row.cells:
            if period_matches_header(period, cell.period_header):
                return cell.display_text
    return None


def _income_rows(period: MetricPeriod, bound: dict[int, str], table) -> tuple[StatementRow, ...]:
    rows: list[StatementRow] = []
    seen: set[str] = set()
    if table is not None:
        for display_row in table.rows:
            index = next((i for i, lab in bound.items() if lab == display_row.label), None)
            cell = next(
                (c for c in display_row.cells if period_matches_header(period, c.period_header)),
                None,
            )
            metric = period.metrics[index] if index is not None and index < len(period.metrics) else None
            if cell is not None and cell.availability == "unavailable":
                metric = None
            number = _as_number(metric)
            availability = "present" if number is not None else "unavailable"
            rows.append(
                StatementRow(
                    label=display_row.label,
                    original_label=display_row.label,
                    value=number,
                    scale="full",
                    currency=period.currency,
                    label_status="display_verified",
                    availability=availability,
                    display_text=cell.display_text if cell is not None else None,
                    slot_index=index,
                )
            )
            seen.add(display_row.label)
    for index, label in bound.items():
        if label in seen:
            continue
        number = _as_number(period.metrics[index] if index < len(period.metrics) else None)
        rows.append(
            StatementRow(
                label=label,
                original_label=label,
                value=number,
                scale="full",
                currency=period.currency,
                label_status="display_verified",
                availability="present" if number is not None else "unavailable",
                display_text=_display_text_for(period, label, table),
                slot_index=index,
            )
        )
    return tuple(rows)


def _unverified_rows(period: MetricPeriod) -> tuple[StatementRow, ...]:
    rows: list[StatementRow] = []
    for index, value in enumerate(period.metrics):
        if index in _SKIP_METRIC_INDEXES:
            continue
        number = _as_number(value)
        if number is None:
            continue
        rows.append(
            StatementRow(
                label=None,
                original_label=None,
                value=number,
                scale="full",
                currency=period.currency,
                label_status="unverified",
                availability="present",
                display_text=None,
                slot_index=index,
            )
        )
    return tuple(rows)


def _to_statement_period(
    period: MetricPeriod,
    *,
    statement: str,
    frequency: str,
    bound: dict[int, str],
    table,
) -> StatementPeriod:
    if statement == "income_statement":
        rows = _income_rows(period, bound, table)
    else:
        rows = _unverified_rows(period)
    return StatementPeriod(
        year=period.year,
        quarter=period.quarter,
        period_end=period.period_end,
        comparative_period_end=period.comparative_period_end,
        currency=period.currency,
        duration=duration_for(statement, frequency),
        rows=rows,
    )


def get_financials(
    query: str,
    *,
    statement: str,
    frequency: str,
    source: GoogleFinanceSource | None = None,
) -> FinancialsResult:
    if statement not in {"income_statement", "balance_sheet", "cash_flow"}:
        raise ValueError(f"Unknown statement {statement!r}")
    if frequency not in {"annual", "quarterly"}:
        raise ValueError(f"Unknown frequency {frequency!r}")
    source = _source(source)
    company = _require_company(query)
    page = _verified_page(company, source)
    retrieved_at = datetime.now(UTC)
    response = source.call_purpose(page, DatasetPurpose.FINANCIALS)
    parsed = parse_financials_payload(response.data)
    table = parse_income_statement_table(page.html) if statement == "income_statement" else None
    bind_periods = parsed.quarterly or parsed.annual
    bound = bind_display_labels(bind_periods, table) if statement == "income_statement" else {}
    source_periods = parsed.annual if frequency == "annual" else parsed.quarterly
    periods = tuple(
        _to_statement_period(p, statement=statement, frequency=frequency, bound=bound, table=table)
        for p in source_periods
    )
    unavailable: list[str] = []
    if dataset_is_empty(response.data) or (parsed.ticker is None and not parsed.annual and not parsed.quarterly):
        unavailable.append("financials")
        unavailable.append(statement)
    elif not source_periods:
        unavailable.append(frequency)
        unavailable.append(statement)
    display_gap = statement in {"balance_sheet", "cash_flow"}
    if statement == "income_statement" and table is None:
        display_gap = True
        unavailable.append("income_statement_display_labels")
    return FinancialsResult(
        identity=AttachedIdentity.from_company(company),
        statement=statement,
        frequency=frequency,
        periods=periods,
        unavailable=tuple(unavailable),
        source_url=page.url,
        retrieved_at=retrieved_at,
        source_dataset="financials",
        display_label_gap=display_gap,
    )


def _gap(id_: str, demonstrated: bool, evidence: str) -> dict[str, Any]:
    return {"id": id_, "demonstrated": demonstrated, "evidence": evidence}


def get_coverage(
    query: str,
    *,
    source: GoogleFinanceSource | None = None,
    peer_source: GoogleFinanceSource | None = None,
    peer_query: str | None = None,
) -> CoverageResult:
    source = _source(source)
    earnings = get_earnings(query, source=source)
    income_q = get_financials(query, statement="income_statement", frequency="quarterly", source=source)
    income_a = get_financials(query, statement="income_statement", frequency="annual", source=source)
    bs_a = get_financials(query, statement="balance_sheet", frequency="annual", source=source)
    bs_q = get_financials(query, statement="balance_sheet", frequency="quarterly", source=source)
    cf_a = get_financials(query, statement="cash_flow", frequency="annual", source=source)
    cf_q = get_financials(query, statement="cash_flow", frequency="quarterly", source=source)
    inventory = get_inventory(query, source=source)

    def section_status(result, *, earnings_result=None, display_gap=False) -> str:
        if earnings_result is not None:
            if earnings_result.periods:
                return "supported"
            return "empty/unavailable"
        if display_gap and result.periods:
            return "display-label unverified"
        if result.periods:
            return "supported"
        return "empty/unavailable"

    sections = (
        CoverageSection("earnings", "quarterly", section_status(None, earnings_result=earnings)),
        CoverageSection("earnings", "annual", "not applicable", "Google earnings history is quarterly."),
        CoverageSection("income_statement", "quarterly", section_status(income_q)),
        CoverageSection("income_statement", "annual", section_status(income_a)),
        CoverageSection("balance_sheet", "quarterly", section_status(bs_q, display_gap=True)),
        CoverageSection("balance_sheet", "annual", section_status(bs_a, display_gap=True)),
        CoverageSection("cash_flow", "quarterly", section_status(cf_q, display_gap=True)),
        CoverageSection("cash_flow", "annual", section_status(cf_a, display_gap=True)),
    )

    actual_missing = any(
        p.revenue_actual.availability == "unavailable" and p.revenue_estimate.availability == "present"
        for p in earnings.periods
    )
    estimate_missing = any(
        p.revenue_estimate.availability == "unavailable" and p.revenue_actual.availability == "present"
        for p in earnings.periods
    )
    display_blank = any(
        row.availability == "unavailable" and row.label_status == "display_verified"
        for period in income_q.periods
        for row in period.rows
    )
    comparative = any(
        p.comparative_period_end and p.period_end and p.comparative_period_end != p.period_end
        for p in income_a.periods
    )
    from google_finance_mcp.financials import enrich_financials_result

    fin_response = source.call_purpose(
        source.load_quote_page(_require_company(query)),
        DatasetPurpose.FINANCIALS,
    )
    enriched = enrich_financials_result({"id": "Pr8h2e", "data": fin_response.data}, context=None)
    avgo_unused = "labeled_data" not in enriched

    key_diff = False
    if peer_source is not None and peer_query:
        peer_inv = get_inventory(peer_query, source=peer_source)
        a_keys = {row.key for row in inventory.datasets if row.purpose == "financials"}
        b_keys = {row.key for row in peer_inv.datasets if row.purpose == "financials"}
        key_diff = bool(a_keys) and bool(b_keys) and a_keys != b_keys

    gap_classes = (
        _gap("actual_missing_estimate_present", actual_missing, "Future/unreported quarter keeps actuals unavailable."),
        _gap("estimate_missing_actual_present", estimate_missing, "Reported quarter may omit consensus estimates."),
        _gap("display_cell_blank", display_blank, "Google display '-' is unavailable, not zero."),
        _gap(
            "earnings_html_loading_dataset_populated",
            bool(earnings.earnings_html_loading and earnings.periods),
            "Loading Previous Earnings... is not treated as no earnings.",
        ),
        _gap(
            "financials_dataset_key_differs",
            key_diff,
            "Financials is selected by compiler purpose; ds:N may differ across issuers.",
        ),
        _gap(
            "unverified_metric_indices",
            bs_a.display_label_gap or cf_a.display_label_gap,
            "Balance sheet and cash flow labels stay unnamed until a displayed table is verified.",
        ),
        _gap(
            "comparative_is_prior_year",
            comparative,
            "Second metric vector is the prior-year comparative, not a second statement or company.",
        ),
        _gap(
            "google_pdf_label_mismatch",
            True,
            "Google Net income is not PDF Profit for the year; labels are kept separate.",
        ),
        _gap(
            "google_pdf_value_mismatch",
            True,
            "Cash and share-count definitions can differ; comparison records mismatch.",
        ),
        _gap(
            "no_notes_auditor_restatement_from_google",
            True,
            "Notes, auditor opinion, and restatements remain slice 02 PDF concerns.",
        ),
        _gap(
            "avgo_enricher_not_used",
            avgo_unused,
            "google_finance_mcp.financials.enrich_financials_result does not label Tadawul payloads.",
        ),
    )
    return CoverageResult(
        identity=earnings.identity,
        retrieved_at=earnings.retrieved_at,
        source_url=earnings.source_url,
        sections=sections,
        gap_classes=gap_classes,
        dated=earnings.retrieved_at.date().isoformat(),
    )


def get_crosscheck(
    query: str,
    *,
    source: GoogleFinanceSource | None = None,
    pdf_facts: Sequence | None = None,
    pdf_path: Path | None = None,
    storage_root: Path | None = None,
    google_frequency: str = "annual",
) -> CrosscheckResult:
    from saudi_exchange_reports.google_finance.compare import compare_statements, facts_from_document

    source = _source(source)
    income = get_financials(query, statement="income_statement", frequency=google_frequency, source=source)
    balance = get_financials(query, statement="balance_sheet", frequency=google_frequency, source=source)
    cash_flow = get_financials(query, statement="cash_flow", frequency=google_frequency, source=source)
    pdf_hash = None
    facts = tuple(pdf_facts) if pdf_facts is not None else ()
    if pdf_path is not None:
        if storage_root is None:
            raise ValueError("storage_root is required when pdf_path is set")
        doc = extract_report(pdf_path, storage_root=storage_root, pages=(13, 15, 17, 18, 19))
        pdf_hash = doc.content_hash
        facts = facts_from_document(doc)
    pairs = compare_statements(
        income=income,
        balance=balance,
        cash_flow=cash_flow,
        pdf_facts=facts,
        google_frequency=google_frequency,
    )
    return CrosscheckResult(
        identity=income.identity,
        pairs=pairs,
        google_is_not_audited=True,
        google_frequency=google_frequency,
        source_url=income.source_url,
        retrieved_at=income.retrieved_at,
        pdf_content_hash=pdf_hash,
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
