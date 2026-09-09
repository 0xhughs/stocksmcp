"""Synthetic Google Finance HTML and dataset payloads.

Values are invented for tests. They are not live Google dumps.
"""

from __future__ import annotations

import json

from saudi_exchange_reports.google_finance.types import (
    DatasetMetadata,
    DatasetPurpose,
    DatasetResponse,
    FetchResult,
    QuotePage,
)

FIXTURE_QUOTE_ID = "2222:TADAWUL"
FIXTURE_DISPLAY_NAME = "Saudi Arabian Oil Co"
FIXTURE_PRICE = 12.34
FIXTURE_CHANGE = 0.11
FIXTURE_PCT = 0.89
FIXTURE_CURRENCY = "SAR"
FIXTURE_UNIX = 1_778_000_000
FIXTURE_NEWS_URL = "https://news.example.test/aramco-fixture"
FIXTURE_WEBSITE = "https://www.aramco.example.test/"
FIXTURE_DESCRIPTION = "Fixture description of a Saudi listed company."

MAPPING_HTML = """<!DOCTYPE html>
<html><head><title>Saudi Arabian Oil Co (2222) Stock Price &amp; News - Google Finance</title></head>
<body>
<script>AF_initDataCallback({key: 'ds:0', hash: '1', data:[[["2222","TADAWUL","2222:TADAWUL"]],null,null,null,null,null,"2222"], sideChannel: {}})</script>
</body></html>
"""

QUOTE_PAGE_HTML = """<!DOCTYPE html>
<html><head><title>Saudi Arabian Oil Co (2222) Stock Price &amp; News - Google Finance</title></head>
<body>
<div class="zzDege">Saudi Arabian Oil Co</div>
<div>Tadawul - Saudi Arabian Oil Co</div>
<div>Previous close 11.50</div>
<div>Day range 12.00 - 12.80</div>
<div>Year range 10.00 - 15.00</div>
<div>Market cap 1.23T SAR</div>
<div>P/E ratio 15.00</div>
<div>Dividend yield 5.00%</div>
<div>Primary exchange Tadawul</div>
<div><span class="OspXqd">CEO</span><span class="oJCxTc">Fixture CEO</span></div>
<div><span class="OspXqd">Founded</span><span class="oJCxTc">1933</span></div>
<div><span class="OspXqd">Headquarters</span><span class="oJCxTc">Dhahran, Saudi Arabia</span></div>
<div><span class="OspXqd">Employees</span><span class="oJCxTc">79,000</span></div>
<div><span class="OspXqd">Sector</span><span class="oJCxTc">Energy</span></div>
<script>AF_initDataCallback({key: 'ds:4', hash: '1', data:[], sideChannel: {}})</script>
<script>AF_initDataCallback({key: 'ds:5', hash: '2', data:[], sideChannel: {}})</script>
<script>AF_initDataCallback({key: 'ds:11', hash: '3', data:[], sideChannel: {}})</script>
<script>AF_initDataCallback({key: 'ds:21', hash: '4', data:[], sideChannel: {}})</script>
</body></html>
"""

REJECT_SAU_HTML = """<!DOCTYPE html>
<html><head><title>Example Co (2222) Stock Price &amp; News - Google Finance</title></head>
<body>
<script>AF_initDataCallback({key: 'ds:0', hash: '1', data:[[["2222","SAU","2222:SAU"]],null,null,null,null,null,"2222"], sideChannel: {}})</script>
</body></html>
"""


def _ds(key: str, rpc: str, purpose: DatasetPurpose, *, empty: bool = False) -> DatasetMetadata:
    return DatasetMetadata(key=key, hash_id="h", rpc_id=rpc, purpose=purpose, empty=empty)


def fixture_quote_page() -> QuotePage:
    return QuotePage(
        url=f"https://www.google.com/finance/quote/{FIXTURE_QUOTE_ID}",
        html=QUOTE_PAGE_HTML,
        datasets=(
            _ds("ds:4", "gCvqoe", DatasetPurpose.QUOTE_SUMMARY),
            _ds("ds:5", "JL8oKc", DatasetPurpose.COMPANY_PROFILE),
            _ds("ds:6", "smi6ye", DatasetPurpose.MARKET_STATISTICS, empty=True),
            _ds("ds:9", "Kcy68c", DatasetPurpose.EARNINGS_HISTORY),
            _ds("ds:11", "ADgT7b", DatasetPurpose.SECURITY_OVERVIEW),
            _ds("ds:16", "gXxkFd", DatasetPurpose.MARKET_STATISTICS, empty=True),
            _ds("ds:18", "dlNq8b", DatasetPurpose.SECURITY_OVERVIEW_ALTERNATE),
            _ds("ds:19", "Pr8h2e", DatasetPurpose.FINANCIALS),
            _ds("ds:20", "kA4MVd", DatasetPurpose.MARKET_NEWS, empty=True),
            _ds("ds:21", "wdVNWe", DatasetPurpose.SECURITY_NEWS),
            _ds("ds:24", "stRW5d", DatasetPurpose.EMPTY_INIT, empty=True),
        ),
    )


def fixture_fetch_result() -> FetchResult:
    return FetchResult(html=QUOTE_PAGE_HTML, final_url=f"https://www.google.com/finance/quote/{FIXTURE_QUOTE_ID}")


def quote_summary_payload() -> list:
    return [
        [
            [
                None,
                ["2222", "TADAWUL"],
                FIXTURE_DISPLAY_NAME,
                None,
                FIXTURE_CURRENCY,
                [FIXTURE_PRICE, FIXTURE_CHANGE, FIXTURE_PCT],
                None,
                99.99,
                None,
                None,
                None,
                [FIXTURE_UNIX],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [[2026, 9, 9, 10], [2026, 9, 9, 15]],
                None,
                FIXTURE_QUOTE_ID,
            ]
        ]
    ]


def news_payload() -> list:
    return [
        [
            [
                FIXTURE_NEWS_URL,
                "Fixture Aramco headline",
                "Fixture Wire",
                None,
                FIXTURE_UNIX,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "Fixture snippet, not the article body.",
            ]
        ]
    ]


def profile_payload() -> list:
    return [
        [
            [
                None,
                None,
                FIXTURE_DESCRIPTION,
                None,
                [1933],
                "Fixture CEO",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                FIXTURE_WEBSITE,
            ]
        ]
    ]


def overview_card_payload() -> list:
    return [[[None], None, "security overview card fixture"]]


def dataset_response(payload: list) -> DatasetResponse:
    return DatasetResponse(id="id", rpc_id="rpc", data=payload, error=None)


def as_json(payload: list) -> str:
    return json.dumps(payload)
