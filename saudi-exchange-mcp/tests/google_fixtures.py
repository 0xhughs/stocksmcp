"""Synthetic Google Finance HTML and dataset payloads.

Values are invented for tests. They are not live Google dumps.
"""

from __future__ import annotations

import json
from typing import Any

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
<div class="Ey80ee"><div>Loading Previous Earnings...</div></div>
<div class="tdfj4d">Income statement</div>
<table class="IvSrfb" aria-label="Income statement">
<thead><tr class="K5RZUc">
<th><div class="nQ5Kpf RMYu8c">All values in SAR</div></th>
<th><div class="nQ5Kpf">Jun 2025</div></th>
<th><div class="nQ5Kpf">Dec 2025</div></th>
</tr></thead>
<tbody>
<tr class="K5RZUc"><td><div class="sp5q4e">Revenue</div></td>
<td><div class="CNzF7d">1.23B</div></td><td><div class="CNzF7d">10.64B</div></td></tr>
<tr class="K5RZUc"><td><div class="sp5q4e">Cost of goods sold</div></td>
<td><div class="CNzF7d">0.70B</div></td><td><div class="CNzF7d">6.00B</div></td></tr>
<tr class="K5RZUc"><td><div class="sp5q4e">Operating expense</div></td>
<td><div class="CNzF7d">0.12B</div></td><td><div class="CNzF7d">1.10B</div></td></tr>
<tr class="K5RZUc"><td><div class="sp5q4e">Operating income</div></td>
<td><div class="CNzF7d">0.31B</div></td><td><div class="CNzF7d">2.20B</div></td></tr>
<tr class="K5RZUc"><td><div class="sp5q4e">Net income</div></td>
<td><div class="CNzF7d">0.45B</div></td><td><div class="CNzF7d">1.80B</div></td></tr>
<tr class="K5RZUc"><td><div class="sp5q4e">Net profit margin</div></td>
<td><div class="CNzF7d">36.59%</div></td><td><div class="CNzF7d">16.92%</div></td></tr>
<tr class="K5RZUc"><td><div class="sp5q4e">Earnings per share</div></td>
<td><div class="CNzF7d">1.25</div></td><td><div class="CNzF7d">-</div></td></tr>
<tr class="K5RZUc"><td><div class="sp5q4e">EBITDA</div></td>
<td><div class="CNzF7d">0.40B</div></td><td><div class="CNzF7d">3.10B</div></td></tr>
</tbody>
</table>
<button type="button"><span>Balance sheet</span></button>
<button type="button"><span>Cash flow</span></button>
<div>AI content may include mistakes</div>
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
            _ds("ds:10", "XxQsbd", DatasetPurpose.EARNINGS_HISTORY_ALTERNATE),
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


MAADEN_QUOTE_PAGE_HTML = """<!DOCTYPE html>
<html><head><title>Saudi Arabian Mining Company SJSC (1211) Stock Price &amp; News - Google Finance</title></head>
<body>
<div class="zzDege">Saudi Arabian Mining Company SJSC</div>
<div class="Ey80ee"><div>Loading Previous Earnings...</div></div>
<div class="tdfj4d">Income statement</div>
<table class="IvSrfb" aria-label="Income statement">
<thead><tr>
<th><div class="nQ5Kpf RMYu8c">All values in SAR</div></th>
<th><div class="nQ5Kpf">Jun 2025</div></th>
<th><div class="nQ5Kpf">Dec 2025</div></th>
</tr></thead>
<tbody>
<tr><td><div class="sp5q4e">Revenue</div></td>
<td><div class="CNzF7d">1.23B</div></td><td><div class="CNzF7d">10.64B</div></td></tr>
<tr><td><div class="sp5q4e">Cost of goods sold</div></td>
<td><div class="CNzF7d">0.70B</div></td><td><div class="CNzF7d">6.00B</div></td></tr>
<tr><td><div class="sp5q4e">Operating expense</div></td>
<td><div class="CNzF7d">0.12B</div></td><td><div class="CNzF7d">1.10B</div></td></tr>
<tr><td><div class="sp5q4e">Operating income</div></td>
<td><div class="CNzF7d">0.31B</div></td><td><div class="CNzF7d">2.20B</div></td></tr>
<tr><td><div class="sp5q4e">Net income</div></td>
<td><div class="CNzF7d">0.45B</div></td><td><div class="CNzF7d">1.80B</div></td></tr>
<tr><td><div class="sp5q4e">Net profit margin</div></td>
<td><div class="CNzF7d">36.59%</div></td><td><div class="CNzF7d">16.92%</div></td></tr>
<tr><td><div class="sp5q4e">Earnings per share</div></td>
<td><div class="CNzF7d">1.25</div></td><td><div class="CNzF7d">-</div></td></tr>
<tr><td><div class="sp5q4e">EBITDA</div></td>
<td><div class="CNzF7d">0.40B</div></td><td><div class="CNzF7d">3.10B</div></td></tr>
</tbody>
</table>
<button type="button">Balance sheet</button>
<button type="button">Cash flow</button>
</body></html>
"""


def fixture_quote_page_maaden() -> QuotePage:
    """Maaden page with Financials advertised at ds:17 (purpose still Financials)."""
    return QuotePage(
        url="https://www.google.com/finance/quote/1211:TADAWUL",
        html=MAADEN_QUOTE_PAGE_HTML,
        datasets=(
            _ds("ds:4", "gCvqoe", DatasetPurpose.QUOTE_SUMMARY),
            _ds("ds:9", "Kcy68c", DatasetPurpose.EARNINGS_HISTORY),
            _ds("ds:10", "XxQsbd", DatasetPurpose.EARNINGS_HISTORY_ALTERNATE),
            _ds("ds:17", "Pr8h2e", DatasetPurpose.FINANCIALS),
            _ds("ds:21", "wdVNWe", DatasetPurpose.SECURITY_NEWS),
        ),
    )


def make_metrics(period_end: list[int], slots: dict[int, Any], *, currency: str = "SAR", length: int = 40) -> list:
    """Hand-written metric vector. Invented numbers; not a live dump."""
    vec: list[Any] = [None] * length
    vec[16] = currency
    vec[17] = list(period_end)
    for index, value in slots.items():
        if index >= length:
            vec.extend([None] * (index + 1 - len(vec)))
        vec[index] = value
    return vec


# Invented earnings figures (not live Google).
FIXTURE_REV_ACTUAL = 1_234_000_000
FIXTURE_REV_ESTIMATE = 1_200_000_000
FIXTURE_EPS_ACTUAL = 1.25
FIXTURE_EPS_ESTIMATE = 1.20
FIXTURE_FUTURE_REV_ESTIMATE = 999_000_000
FIXTURE_FUTURE_EPS_ESTIMATE = 0.50
# Display-abbreviation companion (full units, not a B-scale storage).
FIXTURE_Q_DEC_REVENUE = 10_640_000_000  # display 10.64B
FIXTURE_Q_DEC_NET_INCOME = 1_800_000_000
FIXTURE_Q_JUN_REVENUE = 1_234_000_000
FIXTURE_Q_JUN_COGS = 700_000_000
FIXTURE_Q_JUN_OPEX = 120_000_000
FIXTURE_Q_JUN_OPINC = 310_000_000
FIXTURE_Q_JUN_NI = 450_000_000
FIXTURE_Q_JUN_MARGIN = 0.3659
FIXTURE_Q_JUN_EPS = 1.25
FIXTURE_Q_JUN_EBITDA = 400_000_000
FIXTURE_Q_DEC_COGS = 6_000_000_000
FIXTURE_Q_DEC_OPEX = 1_100_000_000
FIXTURE_Q_DEC_OPINC = 2_200_000_000
FIXTURE_Q_DEC_MARGIN = 0.1692
FIXTURE_Q_DEC_EBITDA = 3_100_000_000
# Published Maaden 2025 FS originals used as fixture Google values for match cases.
PDF_REVENUE_2025 = 38_577_730_228
PDF_PROFIT_FOR_YEAR = 8_527_980_356
PDF_ATTRIBUTABLE_PARENT = 7_347_878_280
PDF_EPS_2025 = 1.91
PDF_TOTAL_ASSETS = 119_757_152_175
PDF_TOTAL_EQUITY = 67_814_366_490
PDF_TOTAL_LIABILITIES = 51_942_785_685
PDF_CFO = 10_927_067_206
PDF_CFI = -10_120_345_838
PDF_CFF = -5_438_421_256
PDF_CASH = 10_583_548_481
PDF_SHARES = 3_888_763_418
# Invented Google cash-like / shares-like values that differ from PDF (not live dumps).
FIXTURE_CASH_LIKE = 11_111_111_111
FIXTURE_SHARES_LIKE = 3_700_000_000
FIXTURE_ANNUAL_NI = PDF_ATTRIBUTABLE_PARENT
FIXTURE_ANNUAL_REVENUE = PDF_REVENUE_2025
FIXTURE_ANNUAL_EPS = PDF_EPS_2025


def _earnings_vector(
    *,
    revenue_actual: float | None,
    revenue_estimate: float | None,
    eps_actual: float | None,
    eps_estimate: float | None,
    period_end: list[int],
    surprise: float | None = None,
) -> list:
    vec: list[Any] = [None] * 18
    vec[0] = revenue_actual
    vec[8] = revenue_estimate
    vec[9] = eps_actual
    vec[10] = eps_estimate
    vec[11] = surprise
    vec[16] = "SAR"
    vec[17] = list(period_end)
    return vec


def _earnings_row(year: int, quarter: int, vector: list, *, name: str = FIXTURE_DISPLAY_NAME, ticker: str = "2222") -> list:
    return [
        "/g/fixture",
        [ticker, "TADAWUL"],
        name,
        year,
        quarter,
        None,
        None,
        None,
        None,
        vector,
        0,
        None,
        0,
    ]


def earnings_payload() -> list:
    """Actual+estimate, actual-only, estimate-only (future), missing surprise."""
    actual_est = _earnings_row(
        2025,
        2,
        _earnings_vector(
            revenue_actual=FIXTURE_REV_ACTUAL,
            revenue_estimate=FIXTURE_REV_ESTIMATE,
            eps_actual=FIXTURE_EPS_ACTUAL,
            eps_estimate=FIXTURE_EPS_ESTIMATE,
            period_end=[2025, 6, 30],
            surprise=None,
        ),
    )
    actual_only = _earnings_row(
        2025,
        1,
        _earnings_vector(
            revenue_actual=1_100_000_000,
            revenue_estimate=None,
            eps_actual=1.10,
            eps_estimate=None,
            period_end=[2025, 3, 31],
        ),
    )
    future_est_only = _earnings_row(
        2026,
        4,
        _earnings_vector(
            revenue_actual=None,
            revenue_estimate=FIXTURE_FUTURE_REV_ESTIMATE,
            eps_actual=None,
            eps_estimate=FIXTURE_FUTURE_EPS_ESTIMATE,
            period_end=[2026, 12, 31],
        ),
    )
    return [[actual_est, actual_only, future_est_only]]


def _is_slots(*, revenue, cogs, opex, opinc, ni, margin, eps, ebitda) -> dict[int, Any]:
    slots: dict[int, Any] = {
        0: revenue,
        1: ni,
        4: opinc,
        7: cogs,
        5: opex,
        9: eps,
        10: margin,
        20: ebitda,
    }
    return {k: v for k, v in slots.items() if v is not None}


def _bs_cf_slots() -> dict[int, Any]:
    return {
        22: FIXTURE_CASH_LIKE,
        23: PDF_TOTAL_ASSETS,
        25: PDF_TOTAL_EQUITY,
        26: PDF_TOTAL_LIABILITIES,
        27: FIXTURE_SHARES_LIKE,
        28: PDF_CFO,
        29: PDF_CFI,
        30: PDF_CFF,
    }


def financials_payload(*, ticker: str = "2222", name: str = FIXTURE_DISPLAY_NAME) -> list:
    q_jun = make_metrics(
        [2025, 6, 30],
        {
            **_is_slots(
                revenue=FIXTURE_Q_JUN_REVENUE,
                cogs=FIXTURE_Q_JUN_COGS,
                opex=FIXTURE_Q_JUN_OPEX,
                opinc=FIXTURE_Q_JUN_OPINC,
                ni=FIXTURE_Q_JUN_NI,
                margin=FIXTURE_Q_JUN_MARGIN,
                eps=FIXTURE_Q_JUN_EPS,
                ebitda=FIXTURE_Q_JUN_EBITDA,
            ),
        },
        length=40,
    )
    q_dec = make_metrics(
        [2025, 12, 31],
        {
            **_is_slots(
                revenue=FIXTURE_Q_DEC_REVENUE,
                cogs=FIXTURE_Q_DEC_COGS,
                opex=FIXTURE_Q_DEC_OPEX,
                opinc=FIXTURE_Q_DEC_OPINC,
                ni=FIXTURE_Q_DEC_NET_INCOME,
                margin=FIXTURE_Q_DEC_MARGIN,
                eps=None,
                ebitda=FIXTURE_Q_DEC_EBITDA,
            ),
        },
        length=40,
    )
    q_jun_comp = make_metrics([2024, 6, 30], {0: 1_000_000_000}, length=40)
    q_dec_comp = make_metrics([2024, 12, 31], {0: 9_000_000_000}, length=40)
    annual = make_metrics(
        [2025, 12, 31],
        {
            0: FIXTURE_ANNUAL_REVENUE,
            1: FIXTURE_ANNUAL_NI,
            4: 10_214_788_331,
            9: FIXTURE_ANNUAL_EPS,
            **_bs_cf_slots(),
        },
        length=40,
    )
    annual_comp = make_metrics([2024, 12, 31], {0: 30_000_000_000, 1: 6_000_000_000}, length=40)
    quarterly_rows = [
        [2025, 2, q_jun, q_jun_comp],
        [2025, 4, q_dec, q_dec_comp],
    ]
    annual_rows = [
        [2025, annual, annual_comp],
    ]
    company = [
        quarterly_rows,
        annual_rows,
        None,
        None,
        None,
        "/g/fixture",
        name,
        [ticker, "TADAWUL"],
    ]
    return [[company]]


def empty_financials_payload() -> list:
    return []
