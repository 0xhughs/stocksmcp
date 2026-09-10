"""Client: source listing vs labelled cache; blocked profile access."""

from __future__ import annotations

from pathlib import Path

from helpers import FakeResponse, FakeTransport, synthetic_pdf_bytes

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


class FakeTabRenderer:
    def __init__(self, html: str) -> None:
        self.html = html
        self.calls: list[tuple[str, str]] = []

    def fetch_tab_html(self, profile_url: str, *, symbol: str) -> str:
        self.calls.append((profile_url, symbol))
        return self.html


def test_browser_tab_html_used_when_statements_tab_http_500(tmp_path: Path):
    matrix = (Path(__file__).parent / "fixtures" / "maaden_live_matrix.html").read_text(
        encoding="utf-8"
    )
    renderer = FakeTabRenderer(matrix)
    transport = FakeTransport(
        {
            PROFILE: FakeResponse(status=200, body=PROFILE_SHELL.encode("utf-8"), headers={"Content-Type": "text/html"}),
            TAB_URL: FakeResponse(status=500, body=b"Error 500: CWSRV0295E: Error reported: 500\n"),
        }
    )
    listing = list_reports_from_source(
        MAADEN,
        transport,
        storage_root=tmp_path,
        min_interval_seconds=0,
        max_retries=1,
        tab_renderer=renderer,
    )
    assert renderer.calls == [(PROFILE, "1211")]
    assert listing.unavailable is False
    assert listing.reports
    assert any("/Resources/fsPdf/" in r.source_url for r in listing.reports)
    assert any(r.source_url.endswith("370_0_2026-03-11_15-58-59_En.pdf") for r in listing.reports)
    assert "browser" in listing.reason.lower() or "tab" in listing.reason.lower()


def test_resolve_and_retrieve_selects_period_from_browser_listing(tmp_path: Path):
    from saudi_exchange_reports.client import resolve_and_retrieve
    from saudi_exchange_reports.listing import ReportType

    matrix = (Path(__file__).parent / "fixtures" / "maaden_live_matrix.html").read_text(
        encoding="utf-8"
    )
    annual_url = "https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_En.pdf"
    pdf = synthetic_pdf_bytes("Saudi Arabian Mining Co. MAADEN INTEGRATED REPORT 2025")
    renderer = FakeTabRenderer(matrix)
    transport = FakeTransport(
        {
            PROFILE: FakeResponse(status=200, body=PROFILE_SHELL.encode("utf-8"), headers={"Content-Type": "text/html"}),
            TAB_URL: FakeResponse(status=500, body=b"Error 500: CWSRV0295E: Error reported: 500\n"),
            annual_url: FakeResponse(
                status=200, body=pdf, headers={"Content-Type": "application/pdf"}
            ),
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
        tab_renderer=renderer,
    )
    assert listing is not None and listing.unavailable is False
    assert selection.status == "selected"
    assert selection.report is not None
    assert selection.report.source_url == annual_url
    assert retrieval is not None
    assert retrieval.status == "downloaded"
    assert retrieval.record is not None
    assert retrieval.record.source_url == annual_url
    assert (tmp_path / "1211").exists() or list(tmp_path.rglob("*.pdf"))


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


def test_playwright_tab_renderer_rejects_off_host_profile():
    from saudi_exchange_reports.browser_tab import PlaywrightTabRenderer
    from saudi_exchange_reports.errors import DisallowedRedirect

    try:
        PlaywrightTabRenderer().fetch_tab_html("https://evil.example/profile", symbol="1211")
    except DisallowedRedirect:
        return
    raise AssertionError("expected DisallowedRedirect")


def test_profile_url_with_locale_stays_on_host():
    from saudi_exchange_reports.browser_tab import profile_url_with_locale

    url = profile_url("1211")
    ar = profile_url_with_locale(url, "ar")
    assert ar.startswith("https://www.saudiexchange.sa/")
    assert "companySymbol=1211" in ar
    assert "locale=ar" in ar

