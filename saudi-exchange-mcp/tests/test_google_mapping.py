"""D2: verified Google mappings attach to existing identities only."""

from __future__ import annotations

from saudi_exchange_reports.catalog import PILOT_COMPANIES
from saudi_exchange_reports.google_finance.mapping import (
    MappingVerdict,
    verify_quote_page,
)
from saudi_exchange_reports.identity import ResolveStatus, resolve_company

ARAMCO_OK_HTML = """
<html><head>
<title>Saudi Arabian Oil Co (2222) Stock Price &amp; News - Google Finance</title>
</head>
<body>
<script>
var AF_initDataKeys = ["ds:3"];
var AF_dataServiceRequests = {'ds:3' : {id:'gCvqoe',request:[[[null,["2222","TADAWUL"]]],1]}};
</script>
Related: 1211 Maaden
</body></html>
"""

SAU_HTML = """
<html><head><title>Google Finance</title></head>
<body>
<script>
var AF_initDataKeys = ["ds:0"];
var AF_dataServiceRequests = {'ds:0' : {id:'x',request:[1]}};
</script>
</body></html>
"""

MAADEN_OK_HTML = """
<html><head>
<title>Saudi Arabian Mining Company SJSC (1211) Stock Price &amp; News - Google Finance</title>
</head>
<body>
<script>
var AF_initDataKeys = ["ds:3"];
var AF_dataServiceRequests = {'ds:3' : {id:'gCvqoe',request:[[[null,["1211","TADAWUL"]]],1]}};
</script>
</body></html>
"""


ARAMCO_HTML = ARAMCO_OK_HTML
MAADEN_HTML = MAADEN_OK_HTML


def test_catalog_has_no_sau_verified_mapping():
    for company in PILOT_COMPANIES:
        qid = company.google_finance.quote_id or ""
        assert not qid.endswith(":SAU")
        assert company.google_finance.exchange != "SAU"


def test_google_hit_does_not_override_ambiguous_name():
    result = resolve_company(name="Saudi Arabian")
    assert result.status is ResolveStatus.AMBIGUOUS
    assert result.company is None


def test_google_hit_does_not_override_conflicting_name_ticker():
    result = resolve_company(name="Saudi Aramco", ticker="1211")
    assert result.status is ResolveStatus.CONFLICTING
    assert result.company is None


def test_nasdaq_2222_still_wrong_exchange():
    result = resolve_company(ticker="2222", exchange="NASDAQ")
    assert result.status is ResolveStatus.WRONG_EXCHANGE
    assert result.company is None


def test_unknown_ticker_still_not_found():
    result = resolve_company(ticker="9999")
    assert result.status is ResolveStatus.NOT_FOUND


def test_verify_aramco_tadawul_page_matches_existing_identity():
    company = resolve_company(ticker="2222").company
    verdict = verify_quote_page(
        ARAMCO_OK_HTML,
        "https://www.google.com/finance/beta/quote/2222:TADAWUL",
        company,
    )
    assert verdict.status is MappingVerdict.MATCHED
    assert verdict.quote_id == "2222:TADAWUL"
    assert verdict.company_id == "sa-tdwl-2222"


def test_verify_rejects_sau_page_without_company_name():
    company = resolve_company(ticker="2222").company
    verdict = verify_quote_page(
        SAU_HTML,
        "https://www.google.com/finance/quote/2222:SAU",
        company,
    )
    assert verdict.status is MappingVerdict.REJECTED
    assert verdict.quote_id == "2222:SAU"
    assert "SAU" in verdict.reason or "match" in verdict.reason.lower() or "title" in verdict.reason.lower()


def test_related_ticker_on_aramco_page_does_not_swap_to_maaden():
    aramco = resolve_company(ticker="2222").company
    maaden = resolve_company(ticker="1211").company
    verdict = verify_quote_page(
        ARAMCO_OK_HTML,
        "https://www.google.com/finance/beta/quote/2222:TADAWUL",
        aramco,
    )
    assert verdict.status is MappingVerdict.MATCHED
    assert verdict.company_id == aramco.company_id
    assert verdict.company_id != maaden.company_id
    swapped = verify_quote_page(
        ARAMCO_OK_HTML,
        "https://www.google.com/finance/beta/quote/2222:TADAWUL",
        maaden,
    )
    assert swapped.status is MappingVerdict.MISMATCH
    assert swapped.company_id == maaden.company_id


def test_verify_maaden_tadawul_page():
    company = resolve_company(ticker="1211").company
    verdict = verify_quote_page(
        MAADEN_OK_HTML,
        "https://www.google.com/finance/beta/quote/1211:TADAWUL",
        company,
    )
    assert verdict.status is MappingVerdict.MATCHED
    assert verdict.quote_id == "1211:TADAWUL"
