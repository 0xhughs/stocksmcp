"""Opt-in live Google earnings/financials. No golden live integers."""

from __future__ import annotations

import pytest

from saudi_exchange_reports.google_finance.service import get_coverage, get_earnings, get_financials


@pytest.mark.live_google
def test_live_aramco_earnings_presence_not_golden():
    result = get_earnings("ARAMCO")
    assert result.identity.ticker == "2222"
    assert result.identity.google.quote_id == "2222:TADAWUL"
    assert "google.com/finance" in result.source_url
    assert result.retrieved_at.tzinfo is not None
    assert result.article_summary is None
    assert result.periods
    period = result.periods[0]
    assert period.currency in {"SAR", None}
    if period.currency is None:
        assert "currency" in result.unavailable or period.currency is None
    else:
        assert period.currency == "SAR"
    for figure in (period.revenue_actual, period.revenue_estimate, period.eps_actual, period.eps_estimate):
        assert figure.kind in {"actual", "estimate"}
        assert figure.availability in {"present", "unavailable"}
        if figure.availability == "unavailable":
            assert figure.value is None
            assert figure.value != 0


@pytest.mark.live_google
def test_live_aramco_income_statement_annual_and_quarterly():
    annual = get_financials("ARAMCO", statement="income_statement", frequency="annual")
    quarterly = get_financials("ARAMCO", statement="income_statement", frequency="quarterly")
    if not annual.periods:
        assert "annual" in annual.unavailable or "financials" in annual.unavailable
    else:
        labels = {row.label for row in annual.periods[0].rows if row.label_status == "display_verified"}
        assert "Revenue" in labels or "income_statement_display_labels" in annual.unavailable
    if not quarterly.periods:
        assert "quarterly" in quarterly.unavailable or "financials" in quarterly.unavailable
    else:
        labels = {row.label for row in quarterly.periods[0].rows if row.label_status == "display_verified"}
        assert "Revenue" in labels


@pytest.mark.live_google
def test_live_aramco_balance_and_cash_flow_retrieved_or_gapped():
    bs = get_financials("ARAMCO", statement="balance_sheet", frequency="annual")
    cf = get_financials("ARAMCO", statement="cash_flow", frequency="annual")
    assert bs.display_label_gap is True or any(r.label_status == "display_verified" for p in bs.periods for r in p.rows)
    assert cf.display_label_gap is True or any(r.label_status == "display_verified" for p in cf.periods for r in p.rows)
    if not bs.periods:
        assert "balance_sheet" in bs.unavailable or "financials" in bs.unavailable
    if not cf.periods:
        assert "cash_flow" in cf.unavailable or "financials" in cf.unavailable
    coverage = get_coverage("ARAMCO")
    ids = {g["id"] for g in coverage.gap_classes}
    assert "avgo_enricher_not_used" in ids
    assert coverage.identity.ticker == "2222"
