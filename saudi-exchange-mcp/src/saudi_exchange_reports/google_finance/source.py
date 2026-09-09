"""Google Finance retrieval: scripted (tests) or live client (opt-in).

Selects datasets by compiler purpose, not a frozen `ds:3` key. Default tests
inject ScriptedSource and never call Google.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import anyio
import httpx

from google_finance_mcp.client import (
    DEFAULT_HEADERS,
    GoogleFinanceClient,
    parse_mapping_from_html,
)
from saudi_exchange_reports.google_finance.parse import dataset_is_empty
from saudi_exchange_reports.google_finance.types import (
    DatasetMetadata,
    DatasetPurpose,
    DatasetResponse,
    FetchResult,
    QuotePage,
)
from saudi_exchange_reports.models import CompanyIdentity

LIVE_PAYLOAD_DIR = Path("evidence/live-payloads")

_UPSTREAM_PURPOSE: dict[str, DatasetPurpose] = {
    "Quote summary": DatasetPurpose.QUOTE_SUMMARY,
    "Quote summary alternate": DatasetPurpose.QUOTE_SUMMARY_ALTERNATE,
    "Company profile": DatasetPurpose.COMPANY_PROFILE,
    "Market statistics": DatasetPurpose.MARKET_STATISTICS,
    "Key statistics / ratios": DatasetPurpose.MARKET_STATISTICS,
    "Security overview card": DatasetPurpose.SECURITY_OVERVIEW,
    "Security overview card alternate": DatasetPurpose.SECURITY_OVERVIEW_ALTERNATE,
    "Security news feed": DatasetPurpose.SECURITY_NEWS,
    "Market news feed": DatasetPurpose.MARKET_NEWS,
    "Earnings history and estimates": DatasetPurpose.EARNINGS_HISTORY,
    "Earnings history and estimates alternate": DatasetPurpose.EARNINGS_HISTORY_ALTERNATE,
    "Current earnings detail": DatasetPurpose.EARNINGS_HISTORY,
    "Financials / estimates": DatasetPurpose.FINANCIALS,
    "Intraday chart points": DatasetPurpose.INTRADAY_CHART,
    "Intraday OHLCV chart": DatasetPurpose.INTRADAY_CHART,
    "One-month chart points": DatasetPurpose.INTRADAY_CHART,
    "One-month OHLCV chart": DatasetPurpose.INTRADAY_CHART,
    "Related securities": DatasetPurpose.RELATED_SECURITIES,
    "Analyst ratings and price targets": DatasetPurpose.ANALYST_RATINGS,
    "Equity sectors": DatasetPurpose.EQUITY_SECTORS,
    "Market overview quotes": DatasetPurpose.MARKET_OVERVIEW,
    "Empty initialization endpoint": DatasetPurpose.EMPTY_INIT,
    "Empty request endpoint": DatasetPurpose.EMPTY_INIT,
    "No-frame initialization endpoint": DatasetPurpose.EMPTY_INIT,
}

_PURPOSE_GROUP: dict[DatasetPurpose, tuple[DatasetPurpose, ...]] = {
    DatasetPurpose.QUOTE_SUMMARY: (
        DatasetPurpose.QUOTE_SUMMARY,
        DatasetPurpose.QUOTE_SUMMARY_ALTERNATE,
    ),
    DatasetPurpose.SECURITY_OVERVIEW: (
        DatasetPurpose.SECURITY_OVERVIEW,
        DatasetPurpose.SECURITY_OVERVIEW_ALTERNATE,
    ),
    DatasetPurpose.COMPANY_PROFILE: (DatasetPurpose.COMPANY_PROFILE,),
    DatasetPurpose.SECURITY_NEWS: (DatasetPurpose.SECURITY_NEWS,),
    DatasetPurpose.MARKET_STATISTICS: (DatasetPurpose.MARKET_STATISTICS,),
    DatasetPurpose.MARKET_NEWS: (DatasetPurpose.MARKET_NEWS,),
}


def purpose_from_upstream(label: str) -> DatasetPurpose:
    if label in _UPSTREAM_PURPOSE:
        return _UPSTREAM_PURPOSE[label]
    folded = label.casefold()
    if "empty" in folded or "no-frame" in folded or "initialization" in folded:
        return DatasetPurpose.EMPTY_INIT
    return DatasetPurpose.UNKNOWN


class GoogleFinanceSource(Protocol):
    def load_quote_page(self, identity: CompanyIdentity) -> QuotePage: ...

    def call_purpose(self, page: QuotePage, purpose: DatasetPurpose) -> DatasetResponse: ...


@dataclass
class ScriptedSource:
    quote_page: QuotePage
    quote_summary: DatasetResponse | None = None
    overview_card: DatasetResponse | None = None
    news: DatasetResponse | None = None
    profile: DatasetResponse | None = None
    market_statistics: DatasetResponse | None = None
    mapping_html: dict[tuple[str, str], str] = field(default_factory=dict)
    fetch_result: FetchResult | None = None

    def load_quote_page(self, identity: CompanyIdentity) -> QuotePage:
        page = self.quote_page
        if self.fetch_result is not None:
            return QuotePage(
                url=self.fetch_result.final_url or page.url,
                html=self.fetch_result.html,
                datasets=page.datasets,
                source_path=page.source_path,
                batchexecute_url=page.batchexecute_url,
            )
        return page

    def call_purpose(self, page: QuotePage, purpose: DatasetPurpose) -> DatasetResponse:
        grouped = _PURPOSE_GROUP.get(purpose, (purpose,))
        mapping = {
            DatasetPurpose.QUOTE_SUMMARY: self.quote_summary,
            DatasetPurpose.QUOTE_SUMMARY_ALTERNATE: self.quote_summary,
            DatasetPurpose.SECURITY_OVERVIEW: self.overview_card,
            DatasetPurpose.SECURITY_OVERVIEW_ALTERNATE: self.overview_card,
            DatasetPurpose.SECURITY_NEWS: self.news,
            DatasetPurpose.COMPANY_PROFILE: self.profile,
            DatasetPurpose.MARKET_STATISTICS: self.market_statistics,
        }
        for candidate in grouped:
            response = mapping.get(candidate)
            if response is not None:
                return response
        return DatasetResponse(id="", rpc_id="", data=[], error="missing")


class LiveGoogleSource:
    """User-initiated live retrieval via the pinned GoogleFinanceClient."""

    def __init__(self, client: GoogleFinanceClient | None = None, *, dump: bool = False) -> None:
        self.client = client or GoogleFinanceClient()
        self.dump = dump or os.environ.get("SAUDI_LIVE_GOOGLE") == "1"

    def load_quote_page(self, identity: CompanyIdentity) -> QuotePage:
        return anyio.run(self._load_quote_page, identity)

    def call_purpose(self, page: QuotePage, purpose: DatasetPurpose) -> DatasetResponse:
        return anyio.run(self._call_purpose, page, purpose)

    async def _load_quote_page(self, identity: CompanyIdentity) -> QuotePage:
        quote_id = identity.google_finance.quote_id
        if not quote_id:
            raise ValueError("Identity has no verified Google quote_id.")
        url = identity.google_finance.quote_url or f"https://www.google.com/finance/quote/{quote_id}"
        async with httpx.AsyncClient(timeout=self.client.timeout, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
            final_url = str(response.url)
            headers = response.headers
        mapping = parse_mapping_from_html(html, final_url, headers)
        datasets = tuple(
            DatasetMetadata(
                key=req.key,
                hash_id="",
                rpc_id=req.rpc_id,
                purpose=purpose_from_upstream(req.metadata.purpose),
                empty=purpose_from_upstream(req.metadata.purpose) is DatasetPurpose.EMPTY_INIT,
                upstream_purpose=req.metadata.purpose,
            )
            for req in mapping.requests.values()
        )
        page = QuotePage(
            url=final_url,
            html=html,
            datasets=datasets,
            source_path=mapping.source_path,
            batchexecute_url=mapping.batchexecute_url,
        )
        self._last_mapping = mapping
        if self.dump:
            _dump_json(
                f"{identity.ticker.lower()}-mapping-meta.json",
                {
                    "source_url": mapping.source_url,
                    "source_path": mapping.source_path,
                    "batchexecute_url": mapping.batchexecute_url,
                    "init_data_keys": mapping.init_data_keys,
                    "purposes": {
                        key: {
                            "purpose": req.metadata.purpose,
                            "rpc_id": req.rpc_id,
                            "request_shape": req.metadata.request_shape,
                            "source": req.metadata.source,
                        }
                        for key, req in mapping.requests.items()
                    },
                    "cache_control": mapping.cache_policy.cache_control,
                },
            )
            _dump_text(f"{identity.ticker.lower()}-quote.html", html)
        return page

    async def _call_purpose(self, page: QuotePage, purpose: DatasetPurpose) -> DatasetResponse:
        mapping = getattr(self, "_last_mapping", None)
        if mapping is None or mapping.source_path != page.source_path:
            mapping = await self.client.fetch_mapping(page_path=page.source_path or page.url)
            self._last_mapping = mapping
        grouped = _PURPOSE_GROUP.get(purpose, (purpose,))
        wanted = set(grouped)
        candidates = [
            req
            for req in mapping.requests.values()
            if purpose_from_upstream(req.metadata.purpose) in wanted
        ]
        response = await self._first_nonempty(mapping, candidates)
        if dataset_is_empty(response.data) and candidates:
            mapping = await self.client.fetch_mapping(page_path=mapping.source_path)
            self._last_mapping = mapping
            candidates = [
                req
                for req in mapping.requests.values()
                if purpose_from_upstream(req.metadata.purpose) in wanted
            ]
            response = await self._first_nonempty(mapping, candidates)
        if self.dump and not dataset_is_empty(response.data):
            slug = purpose.value
            _dump_json(f"live-{page.source_path.replace('/', '_')}-{slug}.json", {"id": response.id, "data": response.data})
        return response

    async def _first_nonempty(self, mapping: Any, candidates: list[Any]) -> DatasetResponse:
        last = DatasetResponse(id="", rpc_id="", data=[], error="no candidate")
        for req in candidates:
            results = await self.client.batch_call(
                [{"id": req.rpc_id, "request": req.request}],
                source_path=mapping.source_path,
                batchexecute_url=mapping.batchexecute_url,
                hl="en",
            )
            if not results:
                last = DatasetResponse(id=req.rpc_id, rpc_id=req.rpc_id, data=[], error="no_frame")
                continue
            payload = results[0]
            data = payload.get("data")
            last = DatasetResponse(id=str(payload.get("id", "")), rpc_id=req.rpc_id, data=data)
            if not dataset_is_empty(data):
                return last
        return last


def _dump_json(name: str, payload: Any) -> None:
    LIVE_PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (LIVE_PAYLOAD_DIR / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _dump_text(name: str, text: str) -> None:
    LIVE_PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (LIVE_PAYLOAD_DIR / name).write_text(text, encoding="utf-8")
