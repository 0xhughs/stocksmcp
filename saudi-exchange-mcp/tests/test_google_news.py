from __future__ import annotations

import pytest

from saudi_exchange_reports.google_finance.service import get_news
from saudi_exchange_reports.google_finance.source import ScriptedSource
from tests.google_fixtures import (
    FIXTURE_NEWS_URL,
    dataset_response,
    fixture_quote_page,
    news_payload,
)
from tests.test_google_mapping import ARAMCO_HTML, MAADEN_HTML


def _source(**overrides):
    kwargs = {
        "quote_page": fixture_quote_page(),
        "news": dataset_response(news_payload()),
        "mapping_html": {("2222", "TADAWUL"): ARAMCO_HTML, ("1211", "TADAWUL"): MAADEN_HTML},
    }
    kwargs.update(overrides)
    return ScriptedSource(**kwargs)


def test_news_headlines_and_urls_not_article_bodies():
    result = get_news("ARAMCO", source=_source())
    assert result.identity.ticker == "2222"
    assert len(result.items) >= 1
    item = result.items[0]
    assert item.url == FIXTURE_NEWS_URL
    assert item.headline
    assert item.publisher
    assert item.published_at
    assert item.snippet
    assert item.article_body is None
    assert item.read_status == "not_read"
    assert result.unavailable == ()


def test_news_empty_feed_is_unavailable_not_crash():
    result = get_news("ARAMCO", source=_source(news=dataset_response([])))
    assert result.items == ()
    assert "news" in result.unavailable


def test_news_missing_publisher_and_time_are_explicit():
    row = [
        "https://news.example.test/only-headline",
        "Headline only",
        None,
        None,
        None,
    ]
    result = get_news("ARAMCO", source=_source(news=dataset_response([[row]])))
    assert result.items
    item = result.items[0]
    assert item.headline == "Headline only"
    assert item.article_body is None
    assert item.read_status == "not_read"
    assert "publisher" in item.unavailable
    assert "published_at" in item.unavailable


@pytest.mark.live_google
def test_live_aramco_news_has_url():
    result = get_news("ARAMCO")
    assert result.identity.ticker == "2222"
    live_items = [i for i in result.items if i.url]
    if not live_items:
        assert "news" in result.unavailable
    else:
        assert live_items[0].url.startswith("http")
        assert live_items[0].article_body is None
