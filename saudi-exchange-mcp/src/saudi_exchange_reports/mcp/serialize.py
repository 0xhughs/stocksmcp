"""JSON boundary for MCP tool results. Adds explicit source; does not merge numbers."""

from __future__ import annotations

from typing import Any

from saudi_exchange_reports.identity import ResolveStatus
from saudi_exchange_reports.models import CompanyIdentity, FinancialReport, ResolveResult
from saudi_exchange_reports.reading import ExtractedDocument, SearchResult
from saudi_exchange_reports.retrieval import RetrievalResult


def company_to_dict(company: CompanyIdentity) -> dict[str, Any]:
    return {
        "company_id": company.company_id,
        "english_name": company.english_name,
        "arabic_name": company.arabic_name,
        "ticker": company.ticker,
        "exchange": company.exchange,
        "saudi_exchange": {
            "company_symbol": company.saudi_exchange.company_symbol,
            "profile_url": company.saudi_exchange.profile_url,
            "market": company.saudi_exchange.market,
            "issuer_id": company.saudi_exchange.issuer_id,
        },
        "google_finance": {
            "quote_symbol": company.google_finance.quote_symbol,
            "exchange": company.google_finance.exchange,
            "quote_id": company.google_finance.quote_id,
            "quote_url": company.google_finance.quote_url,
            "verified": company.google_finance.verified,
        },
    }


def resolve_to_dict(result: ResolveResult, *, source: str = "shared_identity") -> dict[str, Any]:
    return {
        "source": source,
        "status": result.status.value,
        "reason": result.reason,
        "company": None if result.company is None else company_to_dict(result.company),
        "candidates": [company_to_dict(c) for c in result.candidates],
    }


def identity_failure(result: ResolveResult, *, source: str) -> dict[str, Any]:
    payload = resolve_to_dict(result, source=source)
    payload["company"] = None
    return payload


def google_payload(result: Any) -> dict[str, Any]:
    payload = result.to_dict()
    payload["source"] = "google_finance"
    payload["source_label"] = "Google Finance"
    return payload


def report_to_dict(report: FinancialReport) -> dict[str, Any]:
    return {
        "title": report.title,
        "period": report.period,
        "report_type": report.report_type.value,
        "language": report.language,
        "publication_date": report.publication_date,
        "publication_date_unavailable": report.publication_date_unavailable,
        "source_url": report.source_url,
        "download_url": report.download_url,
        "section": report.section,
        "company_ticker": report.company_ticker,
    }


LISTING_FRESHNESS_NOTE = (
    "A cached listing is not proof that no newer report exists. "
    "Re-fetch from source before concluding coverage."
)


def listing_payload(listing: Any) -> dict[str, Any]:
    return {
        "source": "saudi_exchange",
        "source_label": "Saudi Exchange",
        "reports": [report_to_dict(r) for r in listing.reports],
        "from_cache": listing.from_cache,
        "retrieved_at": listing.retrieved_at,
        "unavailable": listing.unavailable,
        "reason": listing.reason,
        "source_url": listing.source_url,
        "freshness_note": LISTING_FRESHNESS_NOTE,
    }


def retrieval_payload(result: RetrievalResult) -> dict[str, Any]:
    record = result.record
    inspection = result.inspection
    return {
        "source": "saudi_exchange",
        "source_label": "Saudi Exchange",
        "status": result.status,
        "error_type": result.error_type,
        "reason": result.reason,
        "content_hash": record.content_hash if record else None,
        "local_path": str(record.local_path) if record else None,
        "source_url": record.source_url if record else None,
        "final_url": record.final_url if record else None,
        "retrieved_at": record.retrieved_at if record else None,
        "from_cache": record.from_cache if record else None,
        "record": None
        if record is None
        else {
            "company_id": record.company_id,
            "ticker": record.ticker,
            "title": record.title,
            "period": record.period,
            "report_type": record.report_type,
            "language": record.language,
            "source_url": record.source_url,
            "final_url": record.final_url,
            "retrieved_at": record.retrieved_at,
            "content_hash": record.content_hash,
            "local_path": str(record.local_path),
            "from_cache": record.from_cache,
        },
        "inspection": None
        if inspection is None
        else {
            "identity_confirmed": inspection.identity_confirmed,
            "period_confirmed": inspection.period_confirmed,
            "page_count": inspection.page_count,
            "reason": inspection.reason,
        },
    }


def read_payload(doc: ExtractedDocument, pages: tuple) -> dict[str, Any]:
    return {
        "source": "saudi_exchange",
        "source_label": "Saudi Exchange PDF",
        "status": "ok",
        "content_hash": doc.content_hash,
        "local_path": str(doc.local_path),
        "pages": [
            {
                "page_number": page.page_number,
                "method": page.method,
                "text": page.text,
                "unreadable_reason": page.unreadable_reason,
                "content_hash": page.content_hash,
            }
            for page in pages
        ],
    }


def search_payload(doc: ExtractedDocument, result: SearchResult) -> dict[str, Any]:
    return {
        "source": "saudi_exchange",
        "source_label": "Saudi Exchange PDF",
        "status": result.status,
        "query": result.query,
        "reason": result.reason,
        "content_hash": doc.content_hash,
        "hits": [
            {
                "original": hit.original,
                "page_number": hit.page_number,
                "content_hash": hit.content_hash,
                "method": hit.method,
            }
            for hit in result.hits
        ],
    }


def matched(result: ResolveResult) -> bool:
    return result.status is ResolveStatus.MATCHED and result.company is not None
