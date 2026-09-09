"""Client: source listing vs labelled cache; blocked profile access."""

from __future__ import annotations

from pathlib import Path

from helpers import FakeResponse, FakeTransport

from saudi_exchange_reports.catalog import MAADEN, profile_url
from saudi_exchange_reports.client import list_reports_from_source, load_listing_cache
from saudi_exchange_reports.errors import BlockedAccess

PROFILE = profile_url("1211")
HTML = """
<table>
  <tr>
    <td>2025</td><td>Annual</td>
    <td><a href="https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf">English</a></td>
  </tr>
</table>
"""


def test_source_listing_is_not_from_cache(tmp_path: Path):
    transport = FakeTransport(
        {PROFILE: FakeResponse(status=200, body=HTML.encode("utf-8"), headers={"Content-Type": "text/html"})}
    )
    listing = list_reports_from_source(MAADEN, transport, storage_root=tmp_path, min_interval_seconds=0)
    assert listing.from_cache is False
    assert listing.reports
    cached = load_listing_cache(MAADEN, tmp_path)
    assert cached is not None
    assert cached.from_cache is True
    assert cached.from_cache is not listing.from_cache


def test_blocked_profile_raises(tmp_path: Path):
    transport = FakeTransport(
        {
            PROFILE: FakeResponse(
                status=403,
                body=b"<html>Access Denied</html>",
                headers={"Content-Type": "text/html"},
            )
        }
    )
    try:
        list_reports_from_source(MAADEN, transport, storage_root=tmp_path, min_interval_seconds=0)
    except BlockedAccess:
        return
    raise AssertionError("expected BlockedAccess")


PROFILE_SHELL = """
<html>
<head>
  <base href="https://www.saudiexchange.sa/wps/portal/saudiexchange/hidden/company-profile-main/!ut/p/z0/token/"/>
</head>
<body>
  <input type="hidden" id="requestLocale" name="requestLocale" value="en" />
  <li id="finacialStatementAndReports">FINANCIAL STATEMENTS AND REPORTS</li>
  <script>
  $.ajax({
    url:'p0/IZ7_5A602H80O0VC4060O4GML81G57=CZ6_5A602H80OGF2E0QF9BQDEG10K4=NJstatementsTabData=/',
    type:'GET'
  });
  </script>
</body>
</html>
"""

TAB_URL = (
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/hidden/company-profile-main/"
    "!ut/p/z0/token/p0/IZ7_5A602H80O0VC4060O4GML81G57=CZ6_5A602H80OGF2E0QF9BQDEG10K4="
    "NJstatementsTabData=/?statementType=6&reportType=0&requestLocale=en&symbol=1211"
)


def test_lists_reports_from_statements_tab_when_profile_has_no_pdfs(tmp_path: Path):
    tab_html = (Path(__file__).parent / "fixtures" / "maaden_reports.html").read_bytes()
    transport = FakeTransport(
        {
            PROFILE: FakeResponse(status=200, body=PROFILE_SHELL.encode("utf-8"), headers={"Content-Type": "text/html"}),
            TAB_URL: FakeResponse(status=200, body=tab_html, headers={"Content-Type": "text/html"}),
        }
    )
    listing = list_reports_from_source(MAADEN, transport, storage_root=tmp_path, min_interval_seconds=0)
    assert listing.unavailable is False
    assert listing.reports
    assert any(r.source_url.endswith("_En.pdf") for r in listing.reports)
    assert ("GET", TAB_URL) in transport.calls


def test_statements_tab_http_500_is_unavailable_not_empty_market(tmp_path: Path):
    transport = FakeTransport(
        {
            PROFILE: FakeResponse(status=200, body=PROFILE_SHELL.encode("utf-8"), headers={"Content-Type": "text/html"}),
            TAB_URL: FakeResponse(status=500, body=b"Error 500: CWSRV0295E: Error reported: 500\n"),
        }
    )
    listing = list_reports_from_source(
        MAADEN, transport, storage_root=tmp_path, min_interval_seconds=0, max_retries=1
    )
    assert listing.reports == ()
    assert listing.unavailable is True
    assert "500" in listing.reason


def test_resolve_and_retrieve_does_not_treat_failed_index_as_period_miss(tmp_path: Path):
    from saudi_exchange_reports.client import resolve_and_retrieve
    from saudi_exchange_reports.listing import ReportType

    transport = FakeTransport(
        {
            PROFILE: FakeResponse(status=200, body=PROFILE_SHELL.encode("utf-8"), headers={"Content-Type": "text/html"}),
            TAB_URL: FakeResponse(status=500, body=b"Error 500: CWSRV0295E: Error reported: 500\n"),
        }
    )
    selection, retrieval, listing, reason = resolve_and_retrieve(
        ticker="1211",
        period="2025",
        report_type=ReportType.ANNUAL,
        language="en",
        storage_root=tmp_path,
        transport=transport,
        min_interval_seconds=0,
    )
    assert listing is not None and listing.unavailable is True
    assert retrieval is None
    assert selection.status == "unavailable"
    assert "500" in reason
    assert "2025" not in selection.reason or "500" in selection.reason
