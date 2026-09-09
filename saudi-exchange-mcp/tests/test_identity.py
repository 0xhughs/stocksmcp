"""D2: Arabic/English/ticker resolution for the documented pilot sample.

Google Finance quote identifiers are attached to the existing identities
(not a second company table). Network is not required for these lookups.
"""

from __future__ import annotations

import pytest

from saudi_exchange_reports.identity import ResolveStatus, resolve_company


def test_resolve_ticker_2222_to_aramco():
    result = resolve_company(ticker="2222")
    assert result.status is ResolveStatus.MATCHED
    assert result.company is not None
    assert result.company.ticker == "2222"
    assert result.company.english_name == "Saudi Arabian Oil Co."
    assert any("aramco" in alias.lower() for alias in result.company.aliases)
    assert result.company.saudi_exchange.company_symbol == "2222"
    assert result.company.saudi_exchange.market == "Main Market"
    assert result.company.google_finance is not None
    assert result.company.company_id == "sa-tdwl-2222"
    assert result.company.google_finance.quote_symbol == "2222"
    assert result.company.google_finance.exchange == "TADAWUL"
    assert result.company.google_finance.quote_id == "2222:TADAWUL"
    assert result.company.google_finance.verified is True


def test_resolve_english_name_saudi_aramco():
    result = resolve_company(name="Saudi Aramco")
    assert result.status is ResolveStatus.MATCHED
    assert result.company is not None
    assert result.company.ticker == "2222"


def test_resolve_arabic_name_aramco():
    result = resolve_company(name="أرامكو السعودية")
    assert result.status is ResolveStatus.MATCHED
    assert result.company is not None
    assert result.company.ticker == "2222"
    assert result.company.arabic_name


def test_resolve_full_arabic_legal_name():
    result = resolve_company(name="شركة الزيت العربية السعودية")
    assert result.status is ResolveStatus.MATCHED
    assert result.company.ticker == "2222"


def test_resolve_second_pilot_company_maaden_ticker():
    result = resolve_company(ticker="1211")
    assert result.status is ResolveStatus.MATCHED
    assert result.company is not None
    assert result.company.ticker == "1211"
    assert "mining" in result.company.english_name.lower()
    assert result.company.saudi_exchange.company_symbol == "1211"
    assert result.company.company_id != resolve_company(ticker="2222").company.company_id
    assert result.company.company_id == "sa-tdwl-1211"
    assert result.company.google_finance.quote_id == "1211:TADAWUL"
    assert result.company.google_finance.verified is True


def test_resolve_maaden_english_and_short_name():
    by_name = resolve_company(name="Saudi Arabian Mining Co.")
    by_short = resolve_company(name="MAADEN")
    assert by_name.status is ResolveStatus.MATCHED
    assert by_short.status is ResolveStatus.MATCHED
    assert by_name.company.ticker == by_short.company.ticker == "1211"


def test_matching_name_and_ticker_agree():
    result = resolve_company(name="Saudi Aramco", ticker="2222")
    assert result.status is ResolveStatus.MATCHED
    assert result.company.ticker == "2222"


def test_conflicting_name_and_ticker_is_explicit():
    result = resolve_company(name="Saudi Aramco", ticker="1211")
    assert result.status is ResolveStatus.CONFLICTING
    assert result.company is None
    tickers = {c.ticker for c in result.candidates}
    assert tickers == {"2222", "1211"}
    assert "conflict" in result.reason.lower() or "ticker" in result.reason.lower()


def test_ambiguous_shared_prefix_never_silent_picks():
    result = resolve_company(name="Saudi Arabian")
    assert result.status is ResolveStatus.AMBIGUOUS
    assert result.company is None
    assert len(result.candidates) >= 2
    tickers = {c.ticker for c in result.candidates}
    assert "2222" in tickers
    assert "1211" in tickers


def test_unknown_empty_query():
    result = resolve_company()
    assert result.status is ResolveStatus.UNKNOWN
    assert result.company is None


def test_not_found_unknown_ticker():
    result = resolve_company(ticker="9999")
    assert result.status is ResolveStatus.NOT_FOUND
    assert result.company is None


def test_not_found_unknown_name():
    result = resolve_company(name="Definitely Not A Listed Company XYZ")
    assert result.status is ResolveStatus.NOT_FOUND
    assert result.company is None


def test_wrong_exchange_is_not_treated_as_saudi_match():
    result = resolve_company(ticker="2222", exchange="NASDAQ")
    assert result.status is ResolveStatus.WRONG_EXCHANGE
    assert result.company is None


def test_us_ticker_wrong_exchange_even_without_saudi_hit():
    result = resolve_company(ticker="AAPL", exchange="NASDAQ")
    assert result.status is ResolveStatus.WRONG_EXCHANGE
    assert result.company is None


def test_source_identifiers_stay_distinct_from_google_slot():
    company = resolve_company(ticker="2222").company
    assert company.saudi_exchange.company_symbol == "2222"
    assert "companySymbol=2222" in company.saudi_exchange.profile_url
    assert "saudiexchange.sa" in company.saudi_exchange.profile_url
    assert hasattr(company.google_finance, "quote_symbol")
    assert company.google_finance.quote_id == "2222:TADAWUL"
    assert company.google_finance.verified is True
    assert "SAU" not in (company.google_finance.quote_id or "")
    maaden = resolve_company(ticker="1211").company
    assert maaden.google_finance.quote_id == "1211:TADAWUL"
    assert maaden.google_finance.verified is True
    assert maaden.google_finance.quote_id != "1211:SAU"


def test_query_string_dispatch_uses_ticker_when_all_digits():
    result = resolve_company("2222")
    assert result.status is ResolveStatus.MATCHED
    assert result.company.ticker == "2222"


def test_query_string_dispatch_uses_name_when_not_ticker():
    result = resolve_company("أرامكو")
    assert result.status is ResolveStatus.MATCHED
    assert result.company.ticker == "2222"
