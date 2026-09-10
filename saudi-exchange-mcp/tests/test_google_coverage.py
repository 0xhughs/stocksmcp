"""D5: coverage and gap classes. Synthetic fixtures only."""

from __future__ import annotations

from saudi_exchange_reports.google_finance.service import get_coverage, get_inventory
from saudi_exchange_reports.google_finance.source import ScriptedSource
from tests.google_fixtures import (
    dataset_response,
    earnings_payload,
    financials_payload,
    fixture_quote_page,
    fixture_quote_page_maaden,
)
from tests.test_google_mapping import ARAMCO_HTML, MAADEN_HTML


def _source(**overrides):
    kwargs = {
        "quote_page": fixture_quote_page(),
        "earnings": dataset_response(earnings_payload()),
        "financials": dataset_response(financials_payload()),
        "mapping_html": {("2222", "TADAWUL"): ARAMCO_HTML, ("1211", "TADAWUL"): MAADEN_HTML},
    }
    kwargs.update(overrides)
    return ScriptedSource(**kwargs)


def test_coverage_lists_required_gap_classes():
    coverage = get_coverage("ARAMCO", source=_source())
    ids = {gap["id"] for gap in coverage.gap_classes}
    assert "actual_missing_estimate_present" in ids
    assert "estimate_missing_actual_present" in ids
    assert "display_cell_blank" in ids
    assert "earnings_html_loading_dataset_populated" in ids
    assert "financials_dataset_key_differs" in ids
    assert "unverified_metric_indices" in ids
    assert "comparative_is_prior_year" in ids
    assert "google_pdf_label_mismatch" in ids
    assert "google_pdf_value_mismatch" in ids
    assert "no_notes_auditor_restatement_from_google" in ids
    assert "avgo_enricher_not_used" in ids
    demonstrated = {gap["id"] for gap in coverage.gap_classes if gap["demonstrated"]}
    assert "actual_missing_estimate_present" in demonstrated
    assert "estimate_missing_actual_present" in demonstrated
    assert "display_cell_blank" in demonstrated
    assert "earnings_html_loading_dataset_populated" in demonstrated
    assert "comparative_is_prior_year" in demonstrated
    assert "avgo_enricher_not_used" in demonstrated


def test_coverage_sections_for_pilot_company():
    coverage = get_coverage("ARAMCO", source=_source())
    cells = {(c.section, c.frequency): c.status for c in coverage.sections}
    assert cells[("earnings", "quarterly")] == "supported"
    assert cells[("income_statement", "quarterly")] == "supported"
    assert cells[("income_statement", "annual")] == "supported"
    assert cells[("balance_sheet", "annual")] == "display-label unverified"
    assert cells[("cash_flow", "annual")] == "display-label unverified"
    assert coverage.to_dict().get("google_rpc_id") is None


def test_financials_keys_may_differ_while_purpose_stays_financials():
    aramco = get_inventory("ARAMCO", source=_source())
    maaden = get_inventory(
        "MAADEN",
        source=_source(quote_page=fixture_quote_page_maaden()),
    )
    a_keys = {row.key for row in aramco.datasets if row.purpose == "financials"}
    m_keys = {row.key for row in maaden.datasets if row.purpose == "financials"}
    assert a_keys == {"ds:19"}
    assert m_keys == {"ds:17"}
    assert all(row.purpose == "financials" for row in aramco.datasets if row.key in a_keys)
    cov = get_coverage(
        "ARAMCO",
        source=_source(),
        peer_source=_source(quote_page=fixture_quote_page_maaden()),
        peer_query="MAADEN",
    )
    assert any(g["id"] == "financials_dataset_key_differs" and g["demonstrated"] for g in cov.gap_classes)
