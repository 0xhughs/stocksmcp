"""D3: list and select financial statements/reports from observed table HTML.

Routine tests use fixtures. Missing metadata and absent reports are explicit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from saudi_exchange_reports.catalog import ARAMCO, MAADEN
from saudi_exchange_reports.listing import (
    ReportType,
    list_reports,
    parse_report_index_html,
    select_report,
)
from saudi_exchange_reports.models import ReportListing

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_lists_annual_and_interim_with_languages():
    html = (FIXTURES / "maaden_reports.html").read_text(encoding="utf-8")
    reports = parse_report_index_html(html, company=MAADEN)
    assert reports
    types = {r.report_type for r in reports}
    assert ReportType.ANNUAL in types
    assert ReportType.INTERIM in types
    langs = {r.language for r in reports}
    assert "en" in langs
    assert "ar" in langs
    for report in reports:
        assert report.source_url.startswith("https://www.saudiexchange.sa/Resources/fsPdf/")
        assert report.title
        assert report.period


def test_parse_marks_unavailable_publication_date():
    html = (FIXTURES / "maaden_reports.html").read_text(encoding="utf-8")
    reports = parse_report_index_html(html, company=MAADEN)
    undated = [r for r in reports if r.publication_date is None]
    assert undated
    assert all(r.publication_date_unavailable is True for r in undated)


def test_parse_separates_other_report_types():
    html = (FIXTURES / "maaden_reports.html").read_text(encoding="utf-8")
    reports = parse_report_index_html(html, company=MAADEN)
    others = [r for r in reports if r.report_type is ReportType.OTHER]
    assert others
    assert any("board" in r.title.lower() or r.section == "Board Report" for r in others)


def test_select_by_period_type_language():
    html = (FIXTURES / "maaden_reports.html").read_text(encoding="utf-8")
    reports = parse_report_index_html(html, company=MAADEN)
    selected = select_report(
        reports,
        period="2025",
        report_type=ReportType.ANNUAL,
        language="en",
    )
    assert selected.status == "selected"
    assert selected.report is not None
    assert selected.report.period == "2025"
    assert selected.report.report_type is ReportType.ANNUAL
    assert selected.report.language == "en"


def test_select_unavailable_period_is_explicit():
    html = (FIXTURES / "maaden_reports.html").read_text(encoding="utf-8")
    reports = parse_report_index_html(html, company=MAADEN)
    selected = select_report(reports, period="1999", report_type=ReportType.ANNUAL)
    assert selected.status == "unavailable"
    assert selected.report is None
    assert "1999" in selected.reason


def test_select_ambiguous_language_is_explicit():
    html = (FIXTURES / "maaden_reports.html").read_text(encoding="utf-8")
    reports = parse_report_index_html(html, company=MAADEN)
    selected = select_report(reports, period="2025", report_type=ReportType.ANNUAL)
    assert selected.status == "ambiguous"
    assert selected.report is None
    assert len(selected.candidates) >= 2


def test_list_reports_uses_supplied_html_not_live_http():
    html = (FIXTURES / "maaden_reports.html").read_text(encoding="utf-8")
    listing = list_reports(MAADEN, html=html)
    assert isinstance(listing, ReportListing)
    assert listing.from_cache is False
    assert listing.reports
    assert listing.unavailable is False


def test_empty_index_is_explicit_unavailable():
    listing = list_reports(ARAMCO, html="<html><body>no reports</body></html>")
    assert listing.reports == ()
    assert listing.unavailable is True
    assert listing.reason


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
    data: {
      statementType:stmtType,
      reportType:reportType,
      requestLocale:requestLocale,
      symbol:'1211'
    },
    type:'GET'
  });
  </script>
</body>
</html>
"""

EXPECTED_TAB_URL = (
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/hidden/company-profile-main/"
    "!ut/p/z0/token/p0/IZ7_5A602H80O0VC4060O4GML81G57=CZ6_5A602H80OGF2E0QF9BQDEG10K4="
    "NJstatementsTabData=/?statementType=6&reportType=0&requestLocale=en&symbol=1211"
)


def test_statements_index_url_from_profile_shell():
    from saudi_exchange_reports.listing import statements_index_url

    url = statements_index_url(
        PROFILE_SHELL,
        page_url="https://www.saudiexchange.sa/wps/portal/saudiexchange/hidden/company-profile-main/?companySymbol=1211",
        symbol="1211",
    )
    assert url == EXPECTED_TAB_URL
    assert "statementsTabData" in url
    assert "statementType=6" in url
    assert url.startswith("https://www.saudiexchange.sa/")


def test_statements_index_url_rejects_javascript_and_offhost():
    from saudi_exchange_reports.listing import statements_index_url

    html = """
    <base href="https://evil.example/"/>
    <script>$.ajax({ url:'p0/IZ7_X=CZ6_Y=NJstatementsTabData=/', type:'GET' });</script>
    """
    assert (
        statements_index_url(
            html,
            page_url="https://www.saudiexchange.sa/profile",
            symbol="1211",
        )
        is None
    )
    html_js = """
    <base href="https://www.saudiexchange.sa/ok/"/>
    <script>$.ajax({ url:'javascript:alert(1)', type:'GET' });</script>
    """
    assert (
        statements_index_url(html_js, page_url="https://www.saudiexchange.sa/ok", symbol="1211")
        is None
    )
