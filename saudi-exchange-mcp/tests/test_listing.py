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


def test_live_matrix_table_uses_column_year_and_row_type():
    """Live tab is a year-column matrix with empty (SVG) link text, not the fixture list shape."""
    html = (FIXTURES / "maaden_live_matrix.html").read_text(encoding="utf-8")
    reports = parse_report_index_html(html, company=MAADEN)
    by_url = {r.source_url.split("/")[-1]: r for r in reports}
    assert "370_0_2026-03-11_15-58-59_En.pdf" in by_url
    annual = by_url["370_0_2026-03-11_15-58-59_En.pdf"]
    assert annual.period == "2025"
    assert annual.report_type is ReportType.ANNUAL
    assert annual.language == "en"
    assert annual.publication_date == "2026-03-11"
    q3 = by_url["370_0_2025-11-11_15-02-50_En.pdf"]
    assert q3.period == "2025 Q3"
    assert q3.report_type is ReportType.INTERIM
    q1 = by_url["370_0_2025-05-13_16-13-00_En.pdf"]
    assert q1.period == "2025 Q1"
    assert q1.report_type is ReportType.INTERIM
    board = by_url["370_0_2026-03-29_11-05-45_En.pdf"]
    assert board.report_type is ReportType.OTHER
    assert board.period == "2025"
    selected = select_report(
        reports, period="2025", report_type=ReportType.ANNUAL, language="en"
    )
    assert selected.status == "selected"
    assert selected.report is not None
    assert selected.report.source_url.endswith("370_0_2026-03-11_15-58-59_En.pdf")


def test_concatenated_en_and_ar_matrices_select_by_language():
    html_en = (FIXTURES / "maaden_live_matrix.html").read_text(encoding="utf-8")
    html_ar = html_en.replace("_En.pdf", "_Ar.pdf")
    reports = parse_report_index_html(html_en + html_ar, company=MAADEN)
    langs = {r.language for r in reports}
    assert langs == {"en", "ar"}
    selected = select_report(
        reports, period="2025", report_type=ReportType.ANNUAL, language="ar"
    )
    assert selected.status == "selected"
    assert selected.report is not None
    assert selected.report.language == "ar"
    assert selected.report.source_url.endswith("370_0_2026-03-11_15-58-59_Ar.pdf")


def test_arabic_matrix_after_english_esg_section_stays_annual():
    html = """
    <html><table>
      <tr><th>ESG Report</th></tr>
      <tr><td>ESG Report</td>
          <td><a href="/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf"></a></td></tr>
    </table></html>
    <html><table>
      <thead>
        <tr><th colspan="2">القوائم المالية</th></tr>
        <tr><th></th><th>2025</th></tr>
      </thead>
      <tr>
        <td>سنوي</td>
        <td>
          <a href="/Resources/fsPdf/370_0_2026-03-11_15-58-59_Ar.pdf" class="btn-pdf"></a>
          <p>2026-03-11</p>
        </td>
      </tr>
      <tr>
        <td>الربع الثالث</td>
        <td>
          <a href="/Resources/fsPdf/370_0_2025-11-11_15-02-50_Ar.pdf" class="btn-pdf"></a>
          <p>2025-11-12</p>
        </td>
      </tr>
    </table></html>
    """
    reports = parse_report_index_html(html, company=MAADEN)
    by_url = {r.source_url.split("/")[-1]: r for r in reports}
    annual = by_url["370_0_2026-03-11_15-58-59_Ar.pdf"]
    assert annual.report_type is ReportType.ANNUAL
    assert annual.period == "2025"
    assert annual.language == "ar"
    q3 = by_url["370_0_2025-11-11_15-02-50_Ar.pdf"]
    assert q3.report_type is ReportType.INTERIM
    assert q3.period == "2025 Q3"


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
