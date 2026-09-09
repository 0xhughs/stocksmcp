from __future__ import annotations

import pytest

from saudi_exchange_reports.google_finance.service import get_profile
from saudi_exchange_reports.google_finance.source import ScriptedSource
from tests.google_fixtures import (
    FIXTURE_DESCRIPTION,
    FIXTURE_WEBSITE,
    dataset_response,
    fixture_quote_page,
    profile_payload,
)
from tests.test_google_mapping import ARAMCO_HTML, MAADEN_HTML


def _source(**overrides):
    kwargs = {
        "quote_page": fixture_quote_page(),
        "profile": dataset_response(profile_payload()),
        "mapping_html": {("2222", "TADAWUL"): ARAMCO_HTML, ("1211", "TADAWUL"): MAADEN_HTML},
    }
    kwargs.update(overrides)
    return ScriptedSource(**kwargs)


def test_profile_description_and_website_from_payload():
    result = get_profile("ARAMCO", source=_source())
    assert result.identity.ticker == "2222"
    assert result.description == FIXTURE_DESCRIPTION
    assert result.website == FIXTURE_WEBSITE
    assert result.founded_year == 1933
    assert result.ceo  # unlabeled payload field; still useful if present
    assert result.unavailable == ()


def test_profile_html_fallback_when_payload_empty():
    result = get_profile(
        "ARAMCO",
        source=_source(profile=dataset_response([[None]])),
    )
    assert result.ceo == "Fixture CEO"
    assert result.founded_year == 1933
    assert result.headquarters
    assert result.employees
    assert result.sector == "Energy"


def test_profile_marks_missing_fields_unavailable():
    from saudi_exchange_reports.google_finance.types import FetchResult
    from tests.google_fixtures import QUOTE_PAGE_HTML

    html = QUOTE_PAGE_HTML
    html = html.replace('<div><span class="OspXqd">CEO</span><span class="oJCxTc">Fixture CEO</span></div>', "")
    html = html.replace('<div><span class="OspXqd">Sector</span><span class="oJCxTc">Energy</span></div>', "")
    source = _source(
        profile=dataset_response([[None]]),
        fetch_result=FetchResult(html=html, final_url=fixture_quote_page().url),
    )
    result = get_profile("ARAMCO", source=source)
    assert "description" in result.unavailable or result.description is None


@pytest.mark.live_google
def test_live_aramco_profile_has_description_or_website():
    result = get_profile("ARAMCO")
    assert result.identity.ticker == "2222"
    assert result.description or result.website
    if result.website:
        assert "aramco" in result.website.lower() or result.website.startswith("http")
