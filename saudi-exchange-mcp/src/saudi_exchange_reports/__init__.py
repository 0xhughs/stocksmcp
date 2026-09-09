"""Saudi Exchange report discovery, original-PDF retrieval, and page-level reading (slices 01–02)."""

from saudi_exchange_reports.client import list_reports_from_source, resolve_and_retrieve
from saudi_exchange_reports.identity import ResolveStatus, resolve_company
from saudi_exchange_reports.listing import ReportType, list_reports, select_report
from saudi_exchange_reports.models import (
    CompanyIdentity,
    FinancialReport,
    GoogleFinanceMapping,
    ReportListing,
    ReportSelection,
    ResolveResult,
    SaudiExchangeIdentifiers,
)
from saudi_exchange_reports.reading import extract_report, find_line_item, read_pages, search_extracted
from saudi_exchange_reports.retrieval import inspect_pdf_identity, retrieve_from_url, retrieve_report

__all__ = [
    "CompanyIdentity",
    "FinancialReport",
    "GoogleFinanceMapping",
    "ReportListing",
    "ReportSelection",
    "ReportType",
    "ResolveResult",
    "ResolveStatus",
    "SaudiExchangeIdentifiers",
    "extract_report",
    "find_line_item",
    "inspect_pdf_identity",
    "list_reports",
    "list_reports_from_source",
    "read_pages",
    "resolve_and_retrieve",
    "resolve_company",
    "retrieve_from_url",
    "retrieve_report",
    "search_extracted",
    "select_report",
]
