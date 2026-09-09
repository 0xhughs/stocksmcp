"""Command-line entry for slice-01 library usage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from saudi_exchange_reports.client import resolve_and_retrieve
from saudi_exchange_reports.errors import RetrievalError
from saudi_exchange_reports.http import UrllibTransport
from saudi_exchange_reports.identity import resolve_company
from saudi_exchange_reports.listing import ReportType
from saudi_exchange_reports.retrieval import retrieve_from_url


def _report_type(value: str) -> ReportType:
    try:
        return ReportType(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Unknown report type {value!r}") from exc


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

    retrieve_p = sub.add_parser("retrieve", help="List and download a report PDF.")
    retrieve_p.add_argument("--name")
    retrieve_p.add_argument("--ticker")
    retrieve_p.add_argument("--period", required=True)
    retrieve_p.add_argument("--type", dest="report_type", default="annual", type=_report_type)
    retrieve_p.add_argument("--language", default="en")
    retrieve_p.add_argument("--storage", default="storage/reports")
    retrieve_p.add_argument("--revalidate", action="store_true")
    retrieve_p.add_argument("--interval", type=float, default=1.0)

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

    args = parser.parse_args(argv)
    if args.cmd == "resolve":
        result = resolve_company(args.query, name=args.name, ticker=args.ticker, exchange=args.exchange)
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
                "google_finance": {
                    "quote_symbol": result.company.google_finance.quote_symbol,
                    "verified": result.company.google_finance.verified,
                },
            },
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


if __name__ == "__main__":
    raise SystemExit(main())
