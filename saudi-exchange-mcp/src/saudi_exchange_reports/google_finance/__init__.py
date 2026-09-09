"""Google Finance research branch (slice 03). Separate from Saudi PDF/OCR."""

from __future__ import annotations

from saudi_exchange_reports.google_finance.mapping import MappingVerdict, verify_quote_page
from saudi_exchange_reports.google_finance.service import get_inventory, get_news, get_overview, get_profile
from saudi_exchange_reports.google_finance.source import LiveGoogleSource, ScriptedSource

PINNED_REVISION = "319760998e60d4b060fb993b3dc8db94364b019c"

__all__ = [
    "PINNED_REVISION",
    "MappingVerdict",
    "LiveGoogleSource",
    "ScriptedSource",
    "get_inventory",
    "get_news",
    "get_overview",
    "get_profile",
    "verify_quote_page",
]
