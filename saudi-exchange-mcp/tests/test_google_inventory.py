from __future__ import annotations

from saudi_exchange_reports.google_finance.service import get_inventory
from saudi_exchange_reports.google_finance.source import ScriptedSource
from tests.google_fixtures import fixture_quote_page
from tests.test_google_mapping import ARAMCO_HTML, MAADEN_HTML


def test_inventory_selects_by_purpose_not_hardcoded_ds3():
    inv = get_inventory(
        "ARAMCO",
        source=ScriptedSource(
            quote_page=fixture_quote_page(),
            mapping_html={("2222", "TADAWUL"): ARAMCO_HTML, ("1211", "TADAWUL"): MAADEN_HTML},
        ),
    )
    purposes = {row.purpose for row in inv.datasets}
    assert "quote_summary" in purposes
    assert "company_profile" in purposes
    assert "security_news" in purposes
    assert "security_overview" in purposes
    keys = {row.key for row in inv.datasets}
    assert "ds:3" not in keys or any(r.purpose != "quote_summary" for r in inv.datasets if r.key == "ds:3")
    quote_rows = [r for r in inv.datasets if r.purpose == "quote_summary"]
    assert quote_rows
    assert quote_rows[0].key != "ds:3"
    assert inv.product_api_hides_rpc_ids is True
    assert all(row.rpc_id_hidden for row in inv.datasets)


def test_inventory_defers_earnings_and_records_empty_init():
    inv = get_inventory(
        "ARAMCO",
        source=ScriptedSource(
            quote_page=fixture_quote_page(),
            mapping_html={("2222", "TADAWUL"): ARAMCO_HTML},
        ),
    )
    by_purpose = {row.purpose: row for row in inv.datasets}
    assert by_purpose["earnings_history"].product == "defer"
    assert by_purpose["financials"].product == "defer"
    assert by_purpose["empty_init"].product == "non_data"
    assert by_purpose["empty_init"].empty is True
    assert by_purpose["market_news"].product == "observe"
    assert inv.product_api_hides_rpc_ids is True


def test_inventory_notes_empty_market_statistics():
    inv = get_inventory(
        "ARAMCO",
        source=ScriptedSource(
            quote_page=fixture_quote_page(),
            mapping_html={("2222", "TADAWUL"): ARAMCO_HTML},
        ),
    )
    stats = [r for r in inv.datasets if r.purpose == "market_statistics"]
    assert stats
    assert all(r.empty for r in stats)
