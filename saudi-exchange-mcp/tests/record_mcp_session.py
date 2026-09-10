"""Record MCP session field-presence (no live Google bodies)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.mcp_support import call, list_tool_names, run_session, server_params  # noqa: E402

MAADEN_HASH = "d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e"
MAADEN_FS = ROOT / "storage" / "reports" / "1211" / f"{MAADEN_HASH}.pdf"


def _keys(payload: dict[str, Any]) -> list[str]:
    return sorted(payload.keys())


def _presence(payload: dict[str, Any], fields: tuple[str, ...]) -> dict[str, bool]:
    return {field: payload.get(field) not in (None, "", [], {}) for field in fields}


def record_live(path: Path) -> dict[str, Any]:
    storage = ROOT / "storage" / "reports"
    params = server_params(storage, live=True)
    log: dict[str, Any] = {"kind": "live", "calls": []}

    async def body(session, init):
        names = await list_tool_names(session)
        log["tools"] = names
        log["instructions_present"] = bool(init.instructions)
        _ar, arabic = await call(session, "lookup_company", query="أرامكو")
        log["calls"].append(
            {
                "class": "lookup_arabic",
                "tool": "lookup_company",
                "arguments": {"query": "(Arabic Aramco)"},
                "status": arabic.get("status"),
                "company_id": (arabic.get("company") or {}).get("company_id"),
                "quote_id": ((arabic.get("company") or {}).get("google_finance") or {}).get("quote_id"),
            }
        )
        _en, english = await call(session, "lookup_company", query="Saudi Aramco")
        log["calls"].append(
            {
                "class": "lookup_english",
                "tool": "lookup_company",
                "arguments": {"query": "Saudi Aramco"},
                "status": english.get("status"),
                "company_id": (english.get("company") or {}).get("company_id"),
            }
        )
        _ov, overview = await call(session, "google_overview", query="ARAMCO")
        log["calls"].append(
            {
                "class": "broad_and_targeted",
                "tool": "google_overview",
                "arguments": {"query": "ARAMCO"},
                "source": overview.get("source"),
                "fields": _presence(
                    overview,
                    ("last", "currency", "source_url", "retrieved_at", "quoted_at", "freshness", "identity"),
                ),
                "is_realtime": overview.get("is_realtime"),
                "unavailable": overview.get("unavailable"),
            }
        )
        for tool in ("google_news", "google_profile", "google_earnings"):
            _r, payload = await call(session, tool, query="ARAMCO")
            log["calls"].append(
                {
                    "class": "broad_and_targeted",
                    "tool": tool,
                    "arguments": {"query": "ARAMCO"},
                    "source": payload.get("source"),
                    "keys": _keys(payload),
                    "unavailable": payload.get("unavailable"),
                }
            )
        for statement, frequency in (
            ("income_statement", "quarterly"),
            ("income_statement", "annual"),
            ("balance_sheet", "annual"),
            ("cash_flow", "annual"),
        ):
            _r, payload = await call(
                session, "google_financials", query="ARAMCO", statement=statement, frequency=frequency
            )
            log["calls"].append(
                {
                    "class": "targeted_financials",
                    "tool": "google_financials",
                    "arguments": {"query": "ARAMCO", "statement": statement, "frequency": frequency},
                    "source": payload.get("source"),
                    "periods": len(payload.get("periods") or []),
                    "display_label_gap": payload.get("display_label_gap"),
                    "unavailable": payload.get("unavailable"),
                }
            )
        listing_note = {"class": "official_report", "tool": "list_official_reports", "arguments": {"query": "MAADEN"}}
        try:
            _ls, listing = await call(session, "list_official_reports", query="MAADEN")
            listing_note.update(
                {
                    "source": listing.get("source"),
                    "unavailable": listing.get("unavailable"),
                    "from_cache": listing.get("from_cache"),
                    "report_count": len(listing.get("reports") or []),
                }
            )
        except Exception as exc:
            listing_note["error_type"] = type(exc).__name__
            listing_note["reason"] = "live listing failed; stored-PDF read/search still required"
        log["calls"].append(listing_note)
        if MAADEN_FS.exists():
            _rd, read = await call(session, "read_official_report", path=str(MAADEN_FS), pages="19")
            log["calls"].append(
                {
                    "class": "official_report",
                    "tool": "read_official_report",
                    "arguments": {"path": "storage/reports/1211/<hash>.pdf", "pages": "19"},
                    "source": read.get("source"),
                    "content_hash": read.get("content_hash"),
                    "page_number": (read.get("pages") or [{}])[0].get("page_number"),
                    "method": (read.get("pages") or [{}])[0].get("method"),
                    "notes_heading_present": "Notes to the consolidated financial statements"
                    in ((read.get("pages") or [{}])[0].get("text") or ""),
                }
            )
            _sr, search = await call(
                session, "search_official_report", path=str(MAADEN_FS), query="share capital", pages="19"
            )
            log["calls"].append(
                {
                    "class": "official_report",
                    "tool": "search_official_report",
                    "arguments": {"path": "storage/reports/1211/<hash>.pdf", "query": "share capital", "pages": "19"},
                    "source": search.get("source"),
                    "status": search.get("status"),
                    "hit_pages": [h.get("page_number") for h in search.get("hits") or []],
                }
            )
            _cg, g = await call(session, "google_overview", query="2222")
            _cs, s = await call(
                session, "search_official_report", path=str(MAADEN_FS), query="share capital", pages="19"
            )
            log["calls"].append(
                {
                    "class": "combined",
                    "tools": ["google_overview", "search_official_report"],
                    "sources": [g.get("source"), s.get("source")],
                    "google_quote_date_is_not_reporting_period": True,
                }
            )
        return log

    run_session(params, body)
    path.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return log


if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "evidence" / "live-payloads" / "mcp-session-live.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    record_live(dest)
    print(dest)
