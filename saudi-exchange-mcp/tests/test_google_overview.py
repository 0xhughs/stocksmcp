from __future__ import annotations

import pytest

from saudi_exchange_reports.google_finance.service import get_overview
from saudi_exchange_reports.google_finance.source import ScriptedSource
from tests.google_fixtures import (
    FIXTURE_CURRENCY,
    FIXTURE_DISPLAY_NAME,
    FIXTURE_PRICE,
    FIXTURE_QUOTE_ID,
    dataset_response,
    fixture_quote_page,
    overview_card_payload,
    quote_summary_payload,
)
from tests.test_google_mapping import ARAMCO_HTML, MAADEN_HTML


def _source(**overrides):
    kwargs = {
        "quote_page": fixture_quote_page(),
        "quote_summary": dataset_response(quote_summary_payload()),
        "overview_card": dataset_response(overview_card_payload()),
        "mapping_html": {("2222", "TADAWUL"): ARAMCO_HTML, ("1211", "TADAWUL"): MAADEN_HTML},
    }
    kwargs.update(overrides)
    return ScriptedSource(**kwargs)


def test_overview_maps_existing_2222_identity():
    result = get_overview("ARAMCO", source=_source())
    assert result.identity.ticker == "2222"
    assert result.identity.google.quote_id == FIXTURE_QUOTE_ID
    assert result.identity.google.verified is True
    assert result.display_name == FIXTURE_DISPLAY_NAME
    assert result.currency == FIXTURE_CURRENCY
    assert result.last == pytest.approx(FIXTURE_PRICE)
    assert result.source_url.endswith("/2222:TADAWUL") or "2222:TADAWUL" in result.source_url
    assert result.is_realtime is False
    assert result.freshness in {"quoted_at", "unknown"}
    assert result.unavailable == ()
    assert result.google_rpc_id is None
    assert "ds:" not in (result.source_dataset or "")


def test_overview_does_not_treat_unlabeled_float_as_previous_close():
    result = get_overview("ARAMCO", source=_source())
    assert result.previous_close is None or result.previous_close != pytest.approx(99.99)


def test_overview_marks_missing_quote_unavailable():
    result = get_overview(
        "ARAMCO",
        source=_source(quote_summary=dataset_response([[None]])),
    )
    assert "last" in result.unavailable or result.last is None


def test_overview_unknown_timestamp_is_not_realtime():
    payload = quote_summary_payload()
    payload[0][0][11] = None
    result = get_overview("ARAMCO", source=_source(quote_summary=dataset_response(payload)))
    assert result.is_realtime is False
    assert result.freshness == "unknown"
    assert "quoted_at" in result.unavailable or result.quoted_at is None


@pytest.mark.live_google
def test_live_aramco_overview_identity_not_price_golden():
    result = get_overview("ARAMCO")
    assert result.identity.ticker == "2222"
    assert result.identity.google.quote_id == "2222:TADAWUL"
    assert result.currency == "SAR"
    assert "google.com/finance" in result.source_url
    assert result.retrieved_at
    assert result.is_realtime is False
    if result.last is None:
        assert "last" in result.unavailable
    else:
        assert result.last > 0
