"""D5/D6: listing freshness and untrusted-link constraints."""

from __future__ import annotations

from saudi_exchange_reports.catalog import MAADEN
from saudi_exchange_reports.listing import list_reports, parse_report_index_html


def test_javascript_and_offhost_links_are_ignored():
    html = """
    <table>
      <tr><th>Financial Statements</th></tr>
      <tr>
        <td>2025</td>
        <td>Annual</td>
        <td><a href="javascript:alert(1)">English</a></td>
        <td><a href="https://evil.example/report.pdf">English</a></td>
        <td><a href="https://www.saudiexchange.sa/Resources/not-pdf/370.txt">skip</a></td>
        <td><a href="https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf">English</a></td>
      </tr>
    </table>
    """
    reports = parse_report_index_html(html, company=MAADEN)
    assert len(reports) == 1
    assert reports[0].source_url.endswith("370_0_2026-03-29_11-05-45_En.pdf")


def test_listing_cache_flag_does_not_claim_source_is_current():
    html = """
    <table>
      <tr>
        <td>2025</td><td>Annual</td>
        <td><a href="https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf">English</a></td>
      </tr>
    </table>
    """
    cached = list_reports(MAADEN, html=html, from_cache=True)
    fresh = list_reports(MAADEN, html=html, from_cache=False)
    assert cached.from_cache is True
    assert fresh.from_cache is False
    assert cached.from_cache is not fresh.from_cache
