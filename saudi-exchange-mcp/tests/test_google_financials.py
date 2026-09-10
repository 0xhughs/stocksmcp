"""D2–D4: income statement, balance sheet, cash flow. Synthetic fixtures only."""

from __future__ import annotations

import pytest

from google_finance_mcp.financials import enrich_financials_result
from saudi_exchange_reports.google_finance.parse import (
    expand_display_abbreviation,
    parse_financials_payload,
    parse_income_statement_table,
)
from saudi_exchange_reports.google_finance.service import get_financials
from saudi_exchange_reports.google_finance.source import ScriptedSource
from tests.google_fixtures import (
    FIXTURE_Q_DEC_REVENUE,
    FIXTURE_Q_JUN_EPS,
    FIXTURE_Q_JUN_NI,
    FIXTURE_Q_JUN_REVENUE,
    PDF_TOTAL_ASSETS,
    dataset_response,
    earnings_payload,
    financials_payload,
    fixture_quote_page,
    fixture_quote_page_maaden,
    quote_summary_payload,
)
from tests.test_google_mapping import ARAMCO_HTML, MAADEN_HTML


def _source(**overrides):
    kwargs = {
        "quote_page": fixture_quote_page(),
        "earnings": dataset_response(earnings_payload()),
        "financials": dataset_response(financials_payload()),
        "quote_summary": dataset_response(quote_summary_payload()),
        "mapping_html": {("2222", "TADAWUL"): ARAMCO_HTML, ("1211", "TADAWUL"): MAADEN_HTML},
    }
    kwargs.update(overrides)
    return ScriptedSource(**kwargs)


def test_expand_display_abbreviation_is_not_stored_scale():
    value, scale = expand_display_abbreviation("10.64B")
    assert value == pytest.approx(10.64e9)
    assert scale == "display_abbreviation"
    full, stored_scale = expand_display_abbreviation("10640000000")
    assert full == pytest.approx(10_640_000_000)
    assert stored_scale == "full"


def test_parse_income_statement_table_labels():
    html = fixture_quote_page().html
    table = parse_income_statement_table(html)
    assert table is not None
    labels = [row.label for row in table.rows]
    assert "Revenue" in labels
    assert "Net income" in labels
    assert "Cost of goods sold" in labels
    assert "Earnings per share" in labels
    dash = next(row for row in table.rows if row.label == "Earnings per share")
    assert dash.cells[-1].availability == "unavailable"


def test_financials_walks_nested_shape_without_avgo_enricher():
    raw = financials_payload(ticker="2222")
    enriched = enrich_financials_result({"id": "Pr8h2e", "data": raw}, context=None)
    assert "labeled_data" not in enriched
    parsed = parse_financials_payload(raw)
    assert parsed.ticker == ("2222", "TADAWUL")
    assert parsed.quarterly
    assert parsed.annual
    annual_2025 = next(p for p in parsed.annual if p.year == 2025)
    assert annual_2025.currency == "SAR"
    assert annual_2025.period_end == (2025, 12, 31)
    assert annual_2025.comparative_period_end == (2024, 12, 31)
    assert annual_2025.comparative_period_end != annual_2025.period_end
    assert len(annual_2025.metrics) >= 17


def test_income_statement_binds_display_labels_and_full_units():
    result = get_financials("ARAMCO", statement="income_statement", frequency="quarterly", source=_source())
    assert result.identity.ticker == "2222"
    assert result.statement == "income_statement"
    assert result.frequency == "quarterly"
    jun = next(p for p in result.periods if p.period_end == (2025, 6, 30))
    assert jun.duration == "quarterly"
    labels = {row.label: row for row in jun.rows}
    assert labels["Revenue"].value == FIXTURE_Q_JUN_REVENUE
    assert labels["Revenue"].scale == "full"
    assert labels["Revenue"].currency == "SAR"
    assert labels["Revenue"].label_status == "display_verified"
    assert labels["Revenue"].original_label == "Revenue"
    assert labels["Net income"].value == FIXTURE_Q_JUN_NI
    assert labels["Earnings per share"].value == pytest.approx(FIXTURE_Q_JUN_EPS)
    dec = next(p for p in result.periods if p.period_end == (2025, 12, 31))
    dec_labels = {row.label: row for row in dec.rows}
    assert dec_labels["Revenue"].value == FIXTURE_Q_DEC_REVENUE
    assert dec_labels["Revenue"].scale == "full"
    assert dec_labels["Revenue"].display_text == "10.64B"
    assert dec_labels["Earnings per share"].availability == "unavailable"
    assert dec_labels["Earnings per share"].value is None
    dumped = result.to_dict()
    assert "google_rpc_id" not in dumped
    assert dumped.get("source_dataset") in {"financials", None} or not str(dumped.get("source_dataset", "")).startswith("ds:")


def test_income_statement_annual_and_quarterly():
    annual = get_financials("ARAMCO", statement="income_statement", frequency="annual", source=_source())
    quarterly = get_financials("ARAMCO", statement="income_statement", frequency="quarterly", source=_source())
    assert annual.periods
    assert quarterly.periods
    assert all(p.duration == "annual" for p in annual.periods)
    assert all(p.duration == "quarterly" for p in quarterly.periods)
    labels = {row.label for row in annual.periods[0].rows}
    assert "Revenue" in labels
    assert "Net income" in labels


def test_balance_sheet_labels_unverified_until_display():
    result = get_financials("ARAMCO", statement="balance_sheet", frequency="annual", source=_source())
    assert result.periods
    period = next(p for p in result.periods if p.year == 2025)
    assert period.duration == "point_in_time"
    assert period.currency == "SAR"
    named = [row.label for row in period.rows if row.label_status == "display_verified"]
    assert named == []
    unverified = [row for row in period.rows if row.label_status == "unverified"]
    assert unverified
    assert all(row.original_label is None or row.label is None for row in unverified)
    assets = [row for row in unverified if row.value == PDF_TOTAL_ASSETS]
    assert assets
    assert assets[0].label_status == "unverified"


def test_cash_flow_is_a_period_and_empty_section_is_gap():
    result = get_financials("ARAMCO", statement="cash_flow", frequency="annual", source=_source())
    period = next(p for p in result.periods if p.year == 2025)
    assert period.duration == "period"
    assert all(row.label_status == "unverified" for row in period.rows)
    empty = get_financials(
        "ARAMCO",
        statement="cash_flow",
        frequency="annual",
        source=_source(financials=dataset_response([])),
    )
    assert empty.periods == ()
    assert "cash_flow" in empty.unavailable or "financials" in empty.unavailable


def test_financials_selected_by_purpose_not_ds_key():
    maaden = get_financials(
        "MAADEN",
        statement="income_statement",
        frequency="annual",
        source=_source(
            quote_page=fixture_quote_page_maaden(),
            financials=dataset_response(financials_payload(ticker="1211", name="Saudi Arabian Mining Company SJSC")),
        ),
    )
    aramco_keys = {ds.key for ds in fixture_quote_page().datasets if ds.purpose.value == "financials"}
    maaden_keys = {ds.key for ds in fixture_quote_page_maaden().datasets if ds.purpose.value == "financials"}
    assert aramco_keys == {"ds:19"}
    assert maaden_keys == {"ds:17"}
    assert maaden.identity.ticker == "1211"
    assert maaden.periods
