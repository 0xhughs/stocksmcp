"""Thin MCP handlers wrapping shipped 01–04 APIs. Do not merge Google and PDF figures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from saudi_exchange_reports.client import list_reports_from_source, load_listing_cache, resolve_and_retrieve
from saudi_exchange_reports.errors import InvalidPdf, RetrievalError, UnsafeDestination
from saudi_exchange_reports.google_finance.service import (
    get_coverage,
    get_earnings,
    get_financials,
    get_news,
    get_overview,
    get_profile,
)
from saudi_exchange_reports.http import UrllibTransport
from saudi_exchange_reports.identity import resolve_company
from saudi_exchange_reports.listing import ReportType
from saudi_exchange_reports.mcp.runtime import get_runtime
from saudi_exchange_reports.mcp.serialize import (
    LISTING_FRESHNESS_NOTE,
    google_payload,
    identity_failure,
    listing_payload,
    matched,
    read_payload,
    resolve_to_dict,
    retrieval_payload,
    search_payload,
)
from saudi_exchange_reports.reading import (
    extract_report,
    find_line_item,
    parse_page_spec,
    read_pages,
    search_extracted,
)
from saudi_exchange_reports.retrieval import retrieve_from_url

STATEMENT_ALIASES = {
    "income": "income_statement",
    "income_statement": "income_statement",
    "is": "income_statement",
    "balance": "balance_sheet",
    "balance_sheet": "balance_sheet",
    "bs": "balance_sheet",
    "cash": "cash_flow",
    "cash_flow": "cash_flow",
    "cf": "cash_flow",
}

GOOGLE_SECTIONS = (
    ("income_statement", "annual", "income_statement_annual"),
    ("income_statement", "quarterly", "income_statement_quarterly"),
    ("balance_sheet", "annual", "balance_sheet_annual"),
    ("balance_sheet", "quarterly", "balance_sheet_quarterly"),
    ("cash_flow", "annual", "cash_flow_annual"),
    ("cash_flow", "quarterly", "cash_flow_quarterly"),
)


def _resolve(arguments: dict[str, Any]):
    query = arguments.get("query")
    name = arguments.get("name")
    ticker = arguments.get("ticker")
    exchange = arguments.get("exchange")
    if isinstance(query, str) and not query.strip():
        query = None
    return resolve_company(query=query, name=name, ticker=ticker, exchange=exchange)


def _transport():
    runtime = get_runtime()
    return runtime.transport if runtime.transport is not None else UrllibTransport()


def _google_source():
    return get_runtime().google_source


def _failed(source: str, exc: BaseException) -> dict[str, Any]:
    return {
        "source": source,
        "status": "unavailable",
        "error_type": type(exc).__name__,
        "reason": str(exc),
        "company": None,
        "candidates": [],
    }


def lookup_company(arguments: dict[str, Any]) -> dict[str, Any]:
    return resolve_to_dict(_resolve(arguments), source="shared_identity")


def _require_matched(arguments: dict[str, Any], *, source: str):
    resolved = _resolve(arguments)
    if not matched(resolved):
        return None, identity_failure(resolved, source=source)
    return resolved.company, None


def google_overview(arguments: dict[str, Any]) -> dict[str, Any]:
    company, failure = _require_matched(arguments, source="google_finance")
    if failure:
        return failure
    try:
        result = get_overview(company.ticker, source=_google_source())
    except Exception as exc:
        return _failed("google_finance", exc)
    return google_payload(result)


def google_news(arguments: dict[str, Any]) -> dict[str, Any]:
    company, failure = _require_matched(arguments, source="google_finance")
    if failure:
        return failure
    try:
        result = get_news(company.ticker, source=_google_source())
    except Exception as exc:
        return _failed("google_finance", exc)
    return google_payload(result)


def google_profile(arguments: dict[str, Any]) -> dict[str, Any]:
    company, failure = _require_matched(arguments, source="google_finance")
    if failure:
        return failure
    try:
        result = get_profile(company.ticker, source=_google_source())
    except Exception as exc:
        return _failed("google_finance", exc)
    return google_payload(result)


def google_earnings(arguments: dict[str, Any]) -> dict[str, Any]:
    company, failure = _require_matched(arguments, source="google_finance")
    if failure:
        return failure
    try:
        result = get_earnings(company.ticker, source=_google_source())
    except Exception as exc:
        return _failed("google_finance", exc)
    return google_payload(result)


def _statement(value: str) -> str:
    folded = value.strip().lower().replace(" ", "_")
    if folded not in STATEMENT_ALIASES:
        raise ValueError(f"Unknown statement {value!r}")
    return STATEMENT_ALIASES[folded]


def google_financials(arguments: dict[str, Any]) -> dict[str, Any]:
    company, failure = _require_matched(arguments, source="google_finance")
    if failure:
        return failure
    try:
        statement = _statement(str(arguments.get("statement", "")))
        frequency = str(arguments.get("frequency", "")).strip().lower()
        if frequency not in {"annual", "quarterly"}:
            raise ValueError(f"Unknown frequency {frequency!r}")
        result = get_financials(
            company.ticker,
            statement=statement,
            frequency=frequency,
            source=_google_source(),
        )
    except Exception as exc:
        return _failed("google_finance", exc)
    return google_payload(result)


def google_coverage(arguments: dict[str, Any]) -> dict[str, Any]:
    company, failure = _require_matched(arguments, source="google_finance")
    if failure:
        return failure
    try:
        result = get_coverage(company.ticker, source=_google_source())
    except Exception as exc:
        return _failed("google_finance", exc)
    return google_payload(result)


def research_company(arguments: dict[str, Any]) -> dict[str, Any]:
    company, failure = _require_matched(arguments, source="google_finance")
    if failure:
        return failure
    query = company.ticker
    source = _google_source()
    sections: dict[str, Any] = {}
    try:
        sections["overview"] = google_payload(get_overview(query, source=source))
    except Exception as exc:
        sections["overview"] = _failed("google_finance", exc)
    try:
        sections["news"] = google_payload(get_news(query, source=source))
    except Exception as exc:
        sections["news"] = _failed("google_finance", exc)
    try:
        sections["profile"] = google_payload(get_profile(query, source=source))
    except Exception as exc:
        sections["profile"] = _failed("google_finance", exc)
    try:
        sections["earnings"] = google_payload(get_earnings(query, source=source))
    except Exception as exc:
        sections["earnings"] = _failed("google_finance", exc)
    for statement, frequency, key in GOOGLE_SECTIONS:
        try:
            sections[key] = google_payload(
                get_financials(query, statement=statement, frequency=frequency, source=source)
            )
        except Exception as exc:
            sections[key] = _failed("google_finance", exc)
    try:
        coverage = google_payload(get_coverage(query, source=source))
    except Exception as exc:
        coverage = _failed("google_finance", exc)
    return {
        "source": "google_finance",
        "source_label": "Google Finance",
        "pulled_official_pdfs": False,
        "identity": company_to_safe(company),
        "sections": sections,
        "coverage": coverage,
        "note": (
            "Google tables are not audited filings. Missing sections are listed per payload; "
            "this compose does not retrieve Saudi Exchange PDFs."
        ),
    }


def company_to_safe(company) -> dict[str, Any]:
    from saudi_exchange_reports.mcp.serialize import company_to_dict

    return company_to_dict(company)


def list_official_reports(arguments: dict[str, Any]) -> dict[str, Any]:
    company, failure = _require_matched(arguments, source="saudi_exchange")
    if failure:
        return failure
    runtime = get_runtime()
    try:
        if arguments.get("inspect_cache"):
            listing = load_listing_cache(company, runtime.storage_root)
            if listing is None:
                return {
                    "source": "saudi_exchange",
                    "source_label": "Saudi Exchange",
                    "status": "unavailable",
                    "unavailable": True,
                    "from_cache": True,
                    "reports": [],
                    "reason": "No labelled listing cache is present.",
                    "freshness_note": LISTING_FRESHNESS_NOTE,
                }
            payload = listing_payload(listing)
            payload["status"] = "ok"
            return payload
        listing = list_reports_from_source(
            company,
            _transport(),
            storage_root=runtime.storage_root,
            min_interval_seconds=runtime.min_interval_seconds,
            use_browser=runtime.use_browser,
        )
    except RetrievalError as exc:
        return _failed("saudi_exchange", exc)
    payload = listing_payload(listing)
    payload["status"] = "unavailable" if listing.unavailable else "ok"
    return payload


def download_official_report(arguments: dict[str, Any]) -> dict[str, Any]:
    company, failure = _require_matched(arguments, source="saudi_exchange")
    if failure:
        return failure
    runtime = get_runtime()
    period = str(arguments.get("period") or "").strip()
    if not period:
        return {
            "source": "saudi_exchange",
            "status": "unavailable",
            "reason": "A reporting period is required to select an official report.",
            "record": None,
        }
    report_type_raw = str(arguments.get("report_type") or "annual").strip().lower()
    try:
        report_type = ReportType(report_type_raw)
    except ValueError:
        return {
            "source": "saudi_exchange",
            "status": "unavailable",
            "reason": f"Unknown report type {report_type_raw!r}.",
            "record": None,
        }
    language = str(arguments.get("language") or "en").strip() or "en"
    url = arguments.get("url")
    revalidate = bool(arguments.get("revalidate", False))
    try:
        if url:
            result = retrieve_from_url(
                company,
                str(url),
                runtime.storage_root,
                _transport(),
                period=period,
                report_type=report_type,
                language=language,
                revalidate=revalidate,
                min_interval_seconds=runtime.min_interval_seconds,
            )
            payload = retrieval_payload(result)
            return payload
        selection, result, listing, reason = resolve_and_retrieve(
            ticker=company.ticker,
            period=period,
            report_type=report_type,
            language=language,
            storage_root=runtime.storage_root,
            transport=_transport(),
            revalidate=revalidate,
            min_interval_seconds=runtime.min_interval_seconds,
            use_browser=runtime.use_browser,
        )
    except RetrievalError as exc:
        return {
            "source": "saudi_exchange",
            "status": "failed",
            "error_type": type(exc).__name__,
            "reason": str(exc),
            "record": None,
        }
    if result is None:
        return {
            "source": "saudi_exchange",
            "source_label": "Saudi Exchange",
            "status": selection.status,
            "reason": reason,
            "record": None,
            "listing_unavailable": listing.unavailable if listing else None,
            "listing_from_cache": listing.from_cache if listing else None,
            "freshness_note": LISTING_FRESHNESS_NOTE,
        }
    return retrieval_payload(result)


def _extract(arguments: dict[str, Any]):
    runtime = get_runtime()
    path = Path(str(arguments["path"]))
    pages = None
    if arguments.get("pages"):
        pages = parse_page_spec(str(arguments["pages"]))
    elif arguments.get("page") is not None:
        start = int(arguments["page"])
        end = int(arguments["page_to"]) if arguments.get("page_to") is not None else start
        pages = tuple(range(start, end + 1))
    return extract_report(
        path,
        storage_root=runtime.storage_root,
        extra_allowed_roots=runtime.extra_allowed_roots,
        pages=pages,
    )


def read_official_report(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        doc = _extract(arguments)
    except (UnsafeDestination, InvalidPdf) as exc:
        return {
            "source": "saudi_exchange",
            "status": "failed",
            "error_type": type(exc).__name__,
            "reason": str(exc),
        }
    if arguments.get("page") is not None:
        start = int(arguments["page"])
        end = int(arguments["page_to"]) if arguments.get("page_to") is not None else start
        pages = read_pages(doc, start, end)
    else:
        pages = doc.pages
    return read_payload(doc, pages)


def search_official_report(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        doc = _extract(arguments)
    except (UnsafeDestination, InvalidPdf) as exc:
        return {
            "source": "saudi_exchange",
            "status": "failed",
            "error_type": type(exc).__name__,
            "reason": str(exc),
        }
    query = arguments.get("query")
    if query is None:
        query = ""
    result = search_extracted(doc, str(query))
    return search_payload(doc, result)


def find_official_line_item(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        doc = _extract(arguments)
    except (UnsafeDestination, InvalidPdf) as exc:
        return {
            "source": "saudi_exchange",
            "status": "failed",
            "error_type": type(exc).__name__,
            "reason": str(exc),
        }
    result = find_line_item(doc, str(arguments.get("label") or ""))
    return {
        "source": "saudi_exchange",
        "source_label": "Saudi Exchange PDF",
        "status": result.status,
        "original": result.original,
        "parsed_number": result.parsed_number,
        "page_number": result.page_number,
        "content_hash": result.content_hash,
        "reason": result.reason,
    }


HANDLERS = {
    "lookup_company": lookup_company,
    "google_overview": google_overview,
    "google_news": google_news,
    "google_profile": google_profile,
    "google_earnings": google_earnings,
    "google_financials": google_financials,
    "google_coverage": google_coverage,
    "research_company": research_company,
    "list_official_reports": list_official_reports,
    "download_official_report": download_official_report,
    "read_official_report": read_official_report,
    "search_official_report": search_official_report,
    "find_official_line_item": find_official_line_item,
}


def dispatch(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return HANDLERS[name](arguments)
