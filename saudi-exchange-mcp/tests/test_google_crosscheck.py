"""D6: dual-provenance Google vs PDF comparison. Fixture strings, not live Google."""

from __future__ import annotations

from pathlib import Path

import pytest

from saudi_exchange_reports.google_finance.service import get_crosscheck
from saudi_exchange_reports.google_finance.source import ScriptedSource
from tests.google_fixtures import (
    PDF_ATTRIBUTABLE_PARENT,
    PDF_CASH,
    PDF_CFF,
    PDF_CFI,
    PDF_CFO,
    PDF_EPS_2025,
    PDF_PROFIT_FOR_YEAR,
    PDF_REVENUE_2025,
    PDF_SHARES,
    PDF_TOTAL_ASSETS,
    PDF_TOTAL_EQUITY,
    PDF_TOTAL_LIABILITIES,
    dataset_response,
    earnings_payload,
    financials_payload,
    fixture_quote_page_maaden,
)
from tests.test_google_mapping import ARAMCO_HTML, MAADEN_HTML

MAADEN_HASH = "d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e"
MAADEN_FS = (
    Path(__file__).resolve().parents[1]
    / "storage"
    / "reports"
    / "1211"
    / f"{MAADEN_HASH}.pdf"
)


def _pdf_facts():
    from saudi_exchange_reports.google_finance.compare import PdfFact

    return (
        PdfFact("Revenue", "38,577,730,228", float(PDF_REVENUE_2025), 13, "annual"),
        PdfFact("Profit for the year", "8,527,980,356", float(PDF_PROFIT_FOR_YEAR), 13, "annual"),
        PdfFact(
            "Ordinary shareholders of the parent company",
            "7,347,878,280",
            float(PDF_ATTRIBUTABLE_PARENT),
            13,
            "annual",
        ),
        PdfFact("Basic and diluted earnings per share", "1.91", float(PDF_EPS_2025), 13, "annual"),
        PdfFact("Total assets", "119,757,152,175", float(PDF_TOTAL_ASSETS), 15, "annual"),
        PdfFact("Total equity", "67,814,366,490", float(PDF_TOTAL_EQUITY), 15, "annual"),
        PdfFact("Total liabilities", "51,942,785,685", float(PDF_TOTAL_LIABILITIES), 15, "annual"),
        PdfFact("Net cash generated from operating activities", "10,927,067,206", float(PDF_CFO), 17, "annual"),
        PdfFact("Net cash utilized in investing activities", "(10,120,345,838)", float(PDF_CFI), 18, "annual"),
        PdfFact("Net cash utilized in financing activities", "(5,438,421,256)", float(PDF_CFF), 18, "annual"),
        PdfFact("Cash and cash equivalents", "10,583,548,481", float(PDF_CASH), 15, "annual"),
        PdfFact("share capital shares", "3,888,763,418", float(PDF_SHARES), 19, "annual"),
    )


def _maaden_source():
    return ScriptedSource(
        quote_page=fixture_quote_page_maaden(),
        earnings=dataset_response(earnings_payload()),
        financials=dataset_response(
            financials_payload(ticker="1211", name="Saudi Arabian Mining Company SJSC")
        ),
        mapping_html={("2222", "TADAWUL"): ARAMCO_HTML, ("1211", "TADAWUL"): MAADEN_HTML},
    )


def test_fixture_annual_revenue_matches_and_keeps_separate_provenance():
    result = get_crosscheck("MAADEN", source=_maaden_source(), pdf_facts=_pdf_facts())
    assert result.google_is_not_audited is True
    revenue = next(p for p in result.pairs if p.pdf_label == "Revenue" and p.google_label == "Revenue")
    assert revenue.outcome == "match"
    assert revenue.pdf_value == PDF_REVENUE_2025
    assert revenue.google_value == PDF_REVENUE_2025
    assert "google" in revenue.google_source
    assert "pdf" in revenue.pdf_source or "PDF" in revenue.pdf_source or revenue.pdf_page == 13


def test_fixture_net_income_is_not_profit_for_the_year():
    result = get_crosscheck("MAADEN", source=_maaden_source(), pdf_facts=_pdf_facts())
    profit = next(p for p in result.pairs if p.pdf_label == "Profit for the year")
    assert profit.outcome == "mismatch"
    assert profit.google_label == "Net income"
    assert "not" in profit.reason.lower() or "mismatch" in profit.reason.lower()
    parent = next(p for p in result.pairs if "parent" in p.pdf_label.lower())
    assert parent.outcome == "match"
    assert parent.google_label == "Net income"


def test_fixture_quarterly_vs_annual_not_comparable():
    result = get_crosscheck(
        "MAADEN",
        source=_maaden_source(),
        pdf_facts=_pdf_facts(),
        google_frequency="quarterly",
    )
    revenue = next(p for p in result.pairs if p.pdf_label == "Revenue")
    assert revenue.outcome == "not_comparable"
    assert "quarter" in revenue.reason.lower() or "duration" in revenue.reason.lower()


def test_fixture_eps_assets_cashflow_and_mismatches():
    result = get_crosscheck("MAADEN", source=_maaden_source(), pdf_facts=_pdf_facts())
    by_pdf = {p.pdf_label: p for p in result.pairs}
    assert by_pdf["Basic and diluted earnings per share"].outcome == "match"
    assert by_pdf["Total assets"].outcome == "match"
    assert by_pdf["Total assets"].google_label_status == "unverified"
    assert by_pdf["Total equity"].outcome == "match"
    assert by_pdf["Total liabilities"].outcome == "match"
    assert by_pdf["Net cash generated from operating activities"].outcome == "match"
    assert by_pdf["Net cash utilized in investing activities"].outcome == "match"
    assert by_pdf["Net cash utilized in investing activities"].google_value == PDF_CFI
    assert by_pdf["Net cash utilized in financing activities"].outcome == "match"
    cash = by_pdf["Cash and cash equivalents"]
    assert cash.outcome == "mismatch"
    assert "auto" in cash.reason.lower() or "definition" in cash.reason.lower() or "unverified" in cash.reason.lower()
    shares = by_pdf["share capital shares"]
    assert shares.outcome == "mismatch"


@pytest.mark.stored_pdf
@pytest.mark.skipif(not MAADEN_FS.exists(), reason="gitignored Maaden 2025 annual English FS PDF is not in storage")
def test_stored_pdf_pairs_via_slice02_apis():
    result = get_crosscheck(
        "MAADEN",
        source=_maaden_source(),
        pdf_path=MAADEN_FS,
        storage_root=MAADEN_FS.parents[1],
    )
    by_pdf = {p.pdf_label: p for p in result.pairs}
    assert by_pdf["Revenue"].outcome == "match"
    assert by_pdf["Profit for the year"].outcome == "mismatch"
    assert by_pdf["Basic and diluted earnings per share"].outcome == "match"
    assert by_pdf["Total assets"].pdf_page == 15
    assert result.google_is_not_audited is True
    assert all(p.pdf_page is not None for p in result.pairs if p.outcome != "unavailable")
