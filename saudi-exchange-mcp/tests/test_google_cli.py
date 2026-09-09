from __future__ import annotations

import json

import pytest

from saudi_exchange_reports.cli import main
from saudi_exchange_reports.google_finance.source import ScriptedSource
from tests.google_fixtures import (
    dataset_response,
    earnings_payload,
    financials_payload,
    fixture_quote_page,
    news_payload,
    overview_card_payload,
    profile_payload,
    quote_summary_payload,
)
from tests.test_google_mapping import ARAMCO_HTML, MAADEN_HTML


@pytest.fixture
def scripted(monkeypatch):
    source = ScriptedSource(
        quote_page=fixture_quote_page(),
        quote_summary=dataset_response(quote_summary_payload()),
        overview_card=dataset_response(overview_card_payload()),
        news=dataset_response(news_payload()),
        profile=dataset_response(profile_payload()),
        earnings=dataset_response(earnings_payload()),
        financials=dataset_response(financials_payload()),
        mapping_html={("2222", "TADAWUL"): ARAMCO_HTML, ("1211", "TADAWUL"): MAADEN_HTML},
    )
    monkeypatch.setattr(
        "saudi_exchange_reports.cli.google_source_from_args",
        lambda _args: source,
    )
    return source


def test_cli_google_overview_json(scripted, capsys):
    assert main(["google-overview", "ARAMCO", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["identity"]["ticker"] == "2222"
    assert payload["last"] == pytest.approx(12.34)
    assert payload["is_realtime"] is False


def test_cli_google_news_json(scripted, capsys):
    assert main(["google-news", "ARAMCO", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["items"][0]["url"].startswith("https://")
    assert payload["items"][0]["article_body"] is None


def test_cli_google_profile_json(scripted, capsys):
    assert main(["google-profile", "ARAMCO", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["website"]
    assert payload["description"]


def test_cli_google_inventory_json(scripted, capsys):
    assert main(["google-inventory", "ARAMCO", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert any(d["purpose"] == "quote_summary" for d in payload["datasets"])


def test_cli_resolve_includes_quote_id(capsys):
    assert main(["resolve", "ARAMCO", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["google"]["quote_id"] == "2222:TADAWUL"
    assert payload["google"]["verified"] is True


def test_cli_google_earnings_json(scripted, capsys):
    assert main(["google-earnings", "ARAMCO", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["identity"]["ticker"] == "2222"
    assert payload["periods"]
    actual = payload["periods"][0]["revenue_actual"]
    assert actual["kind"] == "actual"
    assert "ds:" not in json.dumps(payload)


def test_cli_google_financials_json(scripted, capsys):
    assert main(["google-financials", "ARAMCO", "--statement", "income", "--frequency", "quarterly"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["statement"] == "income_statement"
    assert any(row["label"] == "Revenue" for p in payload["periods"] for row in p["rows"])


def test_cli_google_coverage_json(scripted, capsys):
    assert main(["google-coverage", "ARAMCO"]) == 0
    payload = json.loads(capsys.readouterr().out)
    ids = {g["id"] for g in payload["gap_classes"]}
    assert "avgo_enricher_not_used" in ids
    assert any(s["section"] == "earnings" for s in payload["sections"])


def test_cli_google_crosscheck_json(scripted, capsys):
    assert main(["google-crosscheck", "ARAMCO", "--facts", "fixture"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["google_is_not_audited"] is True
    assert any(p["pdf_label"] == "Revenue" for p in payload["pairs"])
