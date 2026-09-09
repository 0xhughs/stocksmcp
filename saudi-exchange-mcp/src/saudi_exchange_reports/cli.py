"""Command-line entry for slice-01 library usage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from saudi_exchange_reports.client import resolve_and_retrieve
from saudi_exchange_reports.errors import InvalidPdf, RetrievalError, UnsafeDestination
from saudi_exchange_reports.google_finance.service import (
    get_coverage,
    get_crosscheck,
    get_earnings,
    get_financials,
    get_inventory,
    get_news,
    get_overview,
    get_profile,
)
from saudi_exchange_reports.http import UrllibTransport
from saudi_exchange_reports.identity import resolve_company
from saudi_exchange_reports.listing import ReportType
from saudi_exchange_reports.reading import extract_report, parse_page_spec, read_pages, search_extracted
from saudi_exchange_reports.retrieval import retrieve_from_url


def google_source_from_args(_args: argparse.Namespace):
    """Hook for tests to inject ScriptedSource. Default is live client."""
    return None


def _report_type(value: str) -> ReportType:
    try:
        return ReportType(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Unknown report type {value!r}") from exc


def _reading_command(args: argparse.Namespace) -> int:
    storage = Path(args.storage)
    pdf_path = Path(args.path)
    page_spec = parse_page_spec(args.pages) if getattr(args, "pages", None) else None
    try:
        doc = extract_report(pdf_path, storage_root=storage, pages=page_spec)
    except (InvalidPdf, UnsafeDestination) as exc:
        json.dump(
            {"status": "failed", "error_type": type(exc).__name__, "reason": str(exc)},
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return 1
    if args.cmd == "extract":
        payload = {"status": "ok", **doc.to_dict()}
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    if args.cmd == "read":
        start = args.page
        end = args.page_to if args.page_to is not None else args.page
        pages = read_pages(doc, start, end)
        payload = {
            "status": "ok",
            "content_hash": doc.content_hash,
            "local_path": str(doc.local_path),
            "pages": [
                {
                    "page_number": p.page_number,
                    "method": p.method,
                    "text": p.text,
                    "unreadable_reason": p.unreadable_reason,
                    "content_hash": p.content_hash,
                }
                for p in pages
            ],
        }
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    result = search_extracted(doc, args.query)
    payload = {
        "status": result.status,
        "query": result.query,
        "reason": result.reason,
        "content_hash": doc.content_hash,
        "hits": [
            {
                "original": h.original,
                "page_number": h.page_number,
                "content_hash": h.content_hash,
                "method": h.method,
            }
            for h in result.hits
        ],
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve a Saudi Exchange pilot company and retrieve an original report PDF."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    resolve_p = sub.add_parser("resolve", help="Resolve a name/ticker in the pilot sample.")
    resolve_p.add_argument("--name")
    resolve_p.add_argument("--ticker")
    resolve_p.add_argument("--exchange")
    resolve_p.add_argument("query", nargs="?")
    resolve_p.add_argument("--format", choices=("json", "text"), default="json")

    for google_cmd, help_text in (
        ("google-overview", "Google Finance overview/quote for a pilot company."),
        ("google-news", "Google Finance security news for a pilot company."),
        ("google-profile", "Google Finance profile/about for a pilot company."),
        ("google-inventory", "Inventory of Google Finance quote-page sections."),
        ("google-earnings", "Google Finance earnings actual versus estimate."),
        ("google-coverage", "Earnings/financials coverage and gap classes."),
    ):
        gp = sub.add_parser(google_cmd, help=help_text)
        gp.add_argument("query")
        gp.add_argument("--format", choices=("json", "text"), default="json")

    gf = sub.add_parser("google-financials", help="Google Finance income statement, balance sheet, or cash flow.")
    gf.add_argument("query")
    gf.add_argument("--statement", required=True, help="income|balance|cash (or full names)")
    gf.add_argument("--frequency", required=True, choices=("annual", "quarterly"))
    gf.add_argument("--format", choices=("json", "text"), default="json")

    gx = sub.add_parser("google-crosscheck", help="Dual-provenance Google vs official PDF comparison.")
    gx.add_argument("query")
    gx.add_argument("--facts", choices=("fixture",), help="Use published FS original strings (not live Google).")
    gx.add_argument("--pdf", help="Path to stored original PDF inside --storage.")
    gx.add_argument("--storage", default="storage/reports")
    gx.add_argument("--frequency", choices=("annual", "quarterly"), default="annual")
    gx.add_argument("--format", choices=("json", "text"), default="json")

    retrieve_p = sub.add_parser("retrieve", help="List and download a report PDF.")
    retrieve_p.add_argument("--name")
    retrieve_p.add_argument("--ticker")
    retrieve_p.add_argument("--period", required=True)
    retrieve_p.add_argument("--type", dest="report_type", default="annual", type=_report_type)
    retrieve_p.add_argument("--language", default="en")
    retrieve_p.add_argument("--storage", default="storage/reports")
    retrieve_p.add_argument("--revalidate", action="store_true")
    retrieve_p.add_argument("--interval", type=float, default=1.0)
    retrieve_p.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not fall back to browser-driven Financial Statements tab listing.",
    )

    url_p = sub.add_parser(
        "retrieve-url",
        help="Download a known /Resources/fsPdf/ URL (does not invent filenames).",
    )
    url_p.add_argument("--ticker", required=True)
    url_p.add_argument("--url", required=True)
    url_p.add_argument("--period", required=True)
    url_p.add_argument("--type", dest="report_type", default="annual", type=_report_type)
    url_p.add_argument("--language", default="en")
    url_p.add_argument("--title")
    url_p.add_argument("--storage", default="storage/reports")
    url_p.add_argument("--revalidate", action="store_true")
    url_p.add_argument("--interval", type=float, default=1.0)

    extract_p = sub.add_parser("extract", help="Extract text/tables from a stored report PDF.")
    extract_p.add_argument("--path", required=True)
    extract_p.add_argument("--storage", default="storage/reports")
    extract_p.add_argument("--pages", help="1-based PDF pages, e.g. 13-18,19")

    read_p = sub.add_parser("read", help="Read extracted pages of a stored report PDF.")
    read_p.add_argument("--path", required=True)
    read_p.add_argument("--storage", default="storage/reports")
    read_p.add_argument("--page", type=int, required=True)
    read_p.add_argument("--to", dest="page_to", type=int)
    read_p.add_argument("--pages", help="Optional extract subset, e.g. 13-18,19")

    search_p = sub.add_parser("search", help="Search extracted text of a stored report PDF.")
    search_p.add_argument("--path", required=True)
    search_p.add_argument("--storage", default="storage/reports")
    search_p.add_argument("--query", required=True)
    search_p.add_argument("--pages", help="Optional extract subset, e.g. 13-18,19")

    args = parser.parse_args(argv)
    if args.cmd in {"extract", "read", "search"}:
        return _reading_command(args)

    if args.cmd.startswith("google-"):
        return _google_command(args)

    if args.cmd == "resolve":
        result = resolve_company(args.query, name=args.name, ticker=args.ticker, exchange=args.exchange)
        google = None
        if result.company is not None:
            gf = result.company.google_finance
            google = {
                "quote_symbol": gf.quote_symbol,
                "exchange": gf.exchange,
                "quote_id": gf.quote_id,
                "quote_url": gf.quote_url,
                "verified": gf.verified,
            }
        payload = {
            "status": result.status.value,
            "reason": result.reason,
            "company": None
            if result.company is None
            else {
                "company_id": result.company.company_id,
                "ticker": result.company.ticker,
                "english_name": result.company.english_name,
                "arabic_name": result.company.arabic_name,
                "exchange": result.company.exchange,
                "saudi_exchange": {
                    "company_symbol": result.company.saudi_exchange.company_symbol,
                    "profile_url": result.company.saudi_exchange.profile_url,
                    "market": result.company.saudi_exchange.market,
                    "issuer_id": result.company.saudi_exchange.issuer_id,
                },
                "google_finance": google,
            },
            "google": google,
            "candidates": [c.ticker for c in result.candidates],
        }
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0 if result.status.value == "matched" else 2

    storage = Path(args.storage)
    if args.cmd == "retrieve-url":
        resolved = resolve_company(ticker=args.ticker)
        if resolved.status.value != "matched" or resolved.company is None:
            json.dump(
                {
                    "status": resolved.status.value,
                    "reason": resolved.reason,
                    "error_type": None,
                },
                sys.stdout,
                indent=2,
            )
            sys.stdout.write("\n")
            return 2
        retrieval = retrieve_from_url(
            resolved.company,
            args.url,
            storage,
            UrllibTransport(timeout=120.0),
            period=args.period,
            report_type=args.report_type,
            language=args.language,
            title=args.title,
            revalidate=args.revalidate,
            min_interval_seconds=args.interval,
        )
        payload = {
            "status": retrieval.status,
            "error_type": retrieval.error_type,
            "reason": retrieval.reason,
            "content_hash": retrieval.record.content_hash if retrieval.record else None,
            "local_path": str(retrieval.record.local_path) if retrieval.record else None,
            "source_url": retrieval.record.source_url if retrieval.record else None,
            "final_url": retrieval.record.final_url if retrieval.record else None,
            "retrieved_at": retrieval.record.retrieved_at if retrieval.record else None,
            "inspection": None
            if retrieval.inspection is None
            else {
                "identity_confirmed": retrieval.inspection.identity_confirmed,
                "period_confirmed": retrieval.inspection.period_confirmed,
                "page_count": retrieval.inspection.page_count,
                "reason": retrieval.inspection.reason,
                "page_text_preview": retrieval.inspection.page_text[:800],
            },
        }
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0 if retrieval.status in {"downloaded", "cache_hit", "updated"} else 1

    try:
        selection, retrieval, listing, reason = resolve_and_retrieve(
            name=args.name,
            ticker=args.ticker,
            period=args.period,
            report_type=args.report_type,
            language=args.language,
            storage_root=storage,
            transport=UrllibTransport(),
            revalidate=args.revalidate,
            min_interval_seconds=args.interval,
            use_browser=not args.no_browser,
        )
    except RetrievalError as exc:
        json.dump(
            {"status": "failed", "error_type": type(exc).__name__, "reason": str(exc)},
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return 1
    payload = {
        "selection": {
            "status": selection.status,
            "reason": selection.reason,
            "report": None
            if selection.report is None
            else {
                "title": selection.report.title,
                "period": selection.report.period,
                "type": selection.report.report_type.value,
                "language": selection.report.language,
                "source_url": selection.report.source_url,
            },
        },
        "listing": None
        if listing is None
        else {
            "count": len(listing.reports),
            "from_cache": listing.from_cache,
            "unavailable": listing.unavailable,
            "reason": listing.reason,
            "source_url": listing.source_url,
        },
        "retrieval": None
        if retrieval is None
        else {
            "status": retrieval.status,
            "error_type": retrieval.error_type,
            "reason": retrieval.reason,
            "content_hash": retrieval.record.content_hash if retrieval.record else None,
            "local_path": str(retrieval.record.local_path) if retrieval.record else None,
            "source_url": retrieval.record.source_url if retrieval.record else None,
            "inspection": None
            if retrieval.inspection is None
            else {
                "identity_confirmed": retrieval.inspection.identity_confirmed,
                "period_confirmed": retrieval.inspection.period_confirmed,
                "reason": retrieval.inspection.reason,
            },
        },
        "reason": reason,
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    if retrieval and retrieval.status in {"downloaded", "cache_hit", "updated"}:
        return 0
    return 1


def _statement_name(value: str) -> str:
    folded = value.strip().lower().replace(" ", "_")
    aliases = {
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
    if folded not in aliases:
        raise ValueError(f"Unknown statement {value!r}")
    return aliases[folded]


def _google_command(args: argparse.Namespace) -> int:
    source = google_source_from_args(args)
    try:
        if args.cmd == "google-overview":
            result = get_overview(args.query, source=source)
        elif args.cmd == "google-news":
            result = get_news(args.query, source=source)
        elif args.cmd == "google-profile":
            result = get_profile(args.query, source=source)
        elif args.cmd == "google-inventory":
            result = get_inventory(args.query, source=source)
        elif args.cmd == "google-earnings":
            result = get_earnings(args.query, source=source)
        elif args.cmd == "google-financials":
            result = get_financials(
                args.query,
                statement=_statement_name(args.statement),
                frequency=args.frequency,
                source=source,
            )
        elif args.cmd == "google-coverage":
            result = get_coverage(args.query, source=source)
        elif args.cmd == "google-crosscheck":
            from saudi_exchange_reports.google_finance.compare import fixture_pdf_facts

            pdf_facts = fixture_pdf_facts() if args.facts == "fixture" else None
            pdf_path = Path(args.pdf) if getattr(args, "pdf", None) else None
            if pdf_facts is None and pdf_path is None:
                pdf_facts = fixture_pdf_facts()
            result = get_crosscheck(
                args.query,
                source=source,
                pdf_facts=pdf_facts,
                pdf_path=pdf_path,
                storage_root=Path(args.storage) if pdf_path is not None else None,
                google_frequency=args.frequency,
            )
        else:
            result = get_inventory(args.query, source=source)
    except ValueError as exc:
        json.dump({"status": "failed", "reason": str(exc)}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 2
    json.dump(result.to_dict(), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
