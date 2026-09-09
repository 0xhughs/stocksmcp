"""D1: earnings actual versus estimate. Synthetic fixtures only."""

from __future__ import annotations

import pytest

from saudi_exchange_reports.google_finance.parse import parse_earnings_payload
from saudi_exchange_reports.google_finance.service import get_earnings
from saudi_exchange_reports.google_finance.source import ScriptedSource
from tests.google_fixtures import (
    FIXTURE_EPS_ACTUAL,
    FIXTURE_EPS_ESTIMATE,
    FIXTURE_FUTURE_EPS_ESTIMATE,
    FIXTURE_FUTURE_REV_ESTIMATE,
    FIXTURE_QUOTE_ID,
    FIXTURE_REV_ACTUAL,
    FIXTURE_REV_ESTIMATE,
    dataset_response,
    earnings_payload,
    fixture_quote_page,
)
from tests.test_google_mapping import ARAMCO_HTML, MAADEN_HTML


def _source(**overrides):
    kwargs = {
        "quote_page": fixture_quote_page(),
        "earnings": dataset_response(earnings_payload()),
        "mapping_html": {("2222", "TADAWUL"): ARAMCO_HTML, ("1211", "TADAWUL"): MAADEN_HTML},
    }
    kwargs.update(overrides)
    return ScriptedSource(**kwargs)


def test_parse_earnings_labels_actual_and_estimate():
    periods = parse_earnings_payload(earnings_payload())
    by_key = {(p.year, p.quarter): p for p in periods}
    reported = by_key[(2025, 2)]
    assert reported.currency == "SAR"
    assert reported.period_end == (2025, 6, 30)
    assert reported.revenue_actual.kind == "actual"
    assert reported.revenue_actual.availability == "present"
    assert reported.revenue_actual.value == FIXTURE_REV_ACTUAL
    assert reported.revenue_estimate.kind == "estimate"
    assert reported.revenue_estimate.value == FIXTURE_REV_ESTIMATE
    assert reported.eps_actual.value == pytest.approx(FIXTURE_EPS_ACTUAL)
    assert reported.eps_estimate.value == pytest.approx(FIXTURE_EPS_ESTIMATE)
    assert reported.surprise.availability == "unavailable"
    assert reported.surprise.value is None


def test_parse_earnings_actual_only_and_estimate_only():
    periods = parse_earnings_payload(earnings_payload())
    by_key = {(p.year, p.quarter): p for p in periods}
    actual_only = by_key[(2025, 1)]
    assert actual_only.revenue_actual.availability == "present"
    assert actual_only.revenue_estimate.availability == "unavailable"
    assert actual_only.revenue_estimate.value is None
    assert actual_only.eps_estimate.availability == "unavailable"

    future = by_key[(2026, 4)]
    assert future.revenue_actual.availability == "unavailable"
    assert future.revenue_actual.value is None
    assert future.revenue_actual.value != 0
    assert future.eps_actual.availability == "unavailable"
    assert future.eps_actual.value is None
    assert future.revenue_estimate.value == FIXTURE_FUTURE_REV_ESTIMATE
    assert future.eps_estimate.value == pytest.approx(FIXTURE_FUTURE_EPS_ESTIMATE)


def test_missing_actual_is_not_zero():
    periods = parse_earnings_payload(earnings_payload())
    future = next(p for p in periods if p.year == 2026)
    dumped = future.to_dict()
    assert dumped["revenue_actual"]["value"] is None
    assert dumped["revenue_actual"]["availability"] == "unavailable"
    assert dumped["eps_actual"]["value"] is None
    assert 0 not in (
        dumped["revenue_actual"]["value"],
        dumped["eps_actual"]["value"],
    )


def test_get_earnings_attaches_identity_and_ignores_loading_html():
    result = get_earnings("ARAMCO", source=_source())
    assert result.identity.ticker == "2222"
    assert result.identity.google.quote_id == FIXTURE_QUOTE_ID
    assert "google.com/finance" in result.source_url or "2222:TADAWUL" in result.source_url
    assert result.retrieved_at.tzinfo is not None
    assert result.earnings_html_loading is True
    assert result.periods
    assert result.to_dict().get("google_rpc_id") is None
    assert "ds:" not in str(result.to_dict().get("source_dataset") or "")
    assert result.article_summary is None


def test_identical_alternate_is_not_double_counted():
    payload = earnings_payload()
    result = get_earnings(
        "ARAMCO",
        source=_source(
            earnings=dataset_response(payload),
            earnings_alternate=dataset_response(payload),
        ),
    )
    assert len(result.periods) == 3
    assert result.alternate_deduplicated is True


def test_empty_primary_falls_back_to_alternate():
    result = get_earnings(
        "ARAMCO",
        source=_source(
            earnings=dataset_response([]),
            earnings_alternate=dataset_response(earnings_payload()),
        ),
    )
    assert len(result.periods) == 3
    assert result.used_alternate_fallback is True
