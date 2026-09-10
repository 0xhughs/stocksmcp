"""Child-process MCP injection. Imported only when SAUDI_MCP_HOOK is set."""

from __future__ import annotations

import os
from pathlib import Path

from helpers import FakeResponse, FakeTransport, synthetic_pdf_bytes
from saudi_exchange_reports.catalog import profile_url
from saudi_exchange_reports.google_finance.source import ScriptedSource
from saudi_exchange_reports.google_finance.types import DatasetResponse
from tests.google_fixtures import (
    dataset_response,
    earnings_payload,
    financials_payload,
    fixture_quote_page,
    news_payload,
    overview_card_payload,
    profile_payload,
    quote_summary_payload,
)
from tests.test_google_mapping import ARAMCO_HTML, MAADEN_HTML

PDF_URL = "https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf"
PAGE_TEXT = (
    "Saudi Arabian Mining Co. Annual Report for the year 2025\n"
    "Notes to the consolidated financial statements share capital 38,887,634,180"
)

LISTING_HTML = f"""
<table>
  <tr>
    <td>2025</td><td>Annual</td>
    <td><a href="{PDF_URL}">English</a></td>
  </tr>
</table>
"""

EMPTY_PROFILE = "<html><body>Financial Statements section without PDF links.</body></html>"


def full_scripted_source() -> ScriptedSource:
    return ScriptedSource(
        quote_page=fixture_quote_page(),
        quote_summary=dataset_response(quote_summary_payload()),
        overview_card=dataset_response(overview_card_payload()),
        news=dataset_response(news_payload()),
        profile=dataset_response(profile_payload()),
        earnings=dataset_response(earnings_payload()),
        financials=dataset_response(financials_payload()),
        mapping_html={("2222", "TADAWUL"): ARAMCO_HTML, ("1211", "TADAWUL"): MAADEN_HTML},
    )


def _storage() -> Path:
    return Path(os.environ["SAUDI_REPORTS_STORAGE"])


def _pdf_body() -> bytes:
    return synthetic_pdf_bytes(PAGE_TEXT)


def _listing_transport(*, pdf_body: bytes | None = None, empty: bool = False) -> FakeTransport:
    html = EMPTY_PROFILE if empty else LISTING_HTML
    body = html.encode("utf-8")
    routes: dict[str, FakeResponse] = {
        profile_url("1211"): FakeResponse(status=200, body=body, headers={"Content-Type": "text/html"}),
        profile_url("2222"): FakeResponse(status=200, body=body, headers={"Content-Type": "text/html"}),
    }
    if not empty:
        pdf = _pdf_body() if pdf_body is None else pdf_body
        routes[PDF_URL] = FakeResponse(
            status=200,
            body=pdf,
            headers={"Content-Type": "application/pdf"},
        )
    return FakeTransport(routes)


def _install(*, google, transport) -> None:
    from saudi_exchange_reports.mcp.runtime import Runtime, set_runtime

    extra: tuple[Path, ...] = ()
    raw = os.environ.get("SAUDI_MCP_EXTRA_ROOTS", "")
    if raw:
        extra = tuple(Path(p) for p in raw.split(os.pathsep) if p)
    set_runtime(
        Runtime(
            google_source=google,
            transport=transport,
            storage_root=_storage(),
            extra_allowed_roots=extra,
            min_interval_seconds=0.0,
        )
    )


def install_full() -> None:
    _install(google=full_scripted_source(), transport=_listing_transport())


def install_google_fail() -> None:
    class FailingGoogleSource:
        def load_quote_page(self, identity):
            raise RuntimeError("scripted google outage")

        def call_purpose(self, page, purpose) -> DatasetResponse:
            raise RuntimeError("scripted google outage")

    _install(google=FailingGoogleSource(), transport=_listing_transport())


def install_report_fail() -> None:
    _install(google=full_scripted_source(), transport=_listing_transport(empty=True))


def install_invalid_pdf() -> None:
    html = b"<!DOCTYPE html><html><body>Access Denied</body></html>"
    _install(google=full_scripted_source(), transport=_listing_transport(pdf_body=html))


def install_reports_isolation() -> None:
    from saudi_exchange_reports.google_finance.source import LiveGoogleSource

    sentinel = Path(os.environ["SAUDI_MCP_SENTINEL"])

    def boom(self, *args, **kwargs):
        sentinel.write_text("constructed", encoding="utf-8")
        raise AssertionError("report tools must not construct LiveGoogleSource")

    LiveGoogleSource.__init__ = boom  # type: ignore[method-assign]
    _install(google=None, transport=_listing_transport())
