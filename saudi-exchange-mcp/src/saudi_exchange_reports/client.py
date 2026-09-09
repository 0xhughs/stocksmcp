"""Fetch report indexes and PDFs through a constrained HTTP transport."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from saudi_exchange_reports.errors import BlockedAccess, DownloadFailed
from saudi_exchange_reports.http import Pacing, Transport, UrllibTransport, get_with_retries, host_allowed
from saudi_exchange_reports.identity import resolve_company
from saudi_exchange_reports.listing import ReportType, list_reports, select_report, statements_index_url
from saudi_exchange_reports.models import CompanyIdentity, ReportListing, ReportSelection
from saudi_exchange_reports.retrieval import RetrievalResult, retrieve_report
from saudi_exchange_reports.storage import company_dir

LISTING_CACHE_NAME = "listing-cache.json"


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_profile_html(
    company: CompanyIdentity,
    transport: Transport,
    *,
    max_retries: int = 3,
    retry_backoff_seconds: float = 0.5,
    min_interval_seconds: float = 1.0,
) -> tuple[str, str]:
    """GET the observed company-profile URL. HTML is untrusted data."""
    url = company.saudi_exchange.profile_url
    if not host_allowed(url):
        raise DownloadFailed("Profile URL is not on a verified host.")
    response = get_with_retries(
        transport,
        url,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        pacing=Pacing(min_interval_seconds),
        # Akamai 403s this host when Accept is omitted. */* is a working public GET.
        headers={"Accept": "*/*"},
    )
    if response.status in {401, 403}:
        raise BlockedAccess(f"HTTP {response.status} fetching profile {url}")
    if response.status >= 400:
        raise DownloadFailed(f"HTTP {response.status} fetching profile {url}")
    # Treat the body as data even if it looks like instructions.
    return response.body.decode("utf-8", errors="replace"), response.url or url


def _fetch_html(
    transport: Transport,
    url: str,
    *,
    max_retries: int = 3,
    retry_backoff_seconds: float = 0.5,
    min_interval_seconds: float = 1.0,
    referer: str | None = None,
) -> tuple[int, str, str]:
    headers = {"Accept": "*/*"}
    if referer:
        headers["Referer"] = referer
        headers["X-Requested-With"] = "XMLHttpRequest"
    response = get_with_retries(
        transport,
        url,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        pacing=Pacing(min_interval_seconds),
        headers=headers,
    )
    body = response.body.decode("utf-8", errors="replace")
    return response.status, body, response.url or url


def list_reports_from_source(
    company: CompanyIdentity,
    transport: Transport,
    *,
    storage_root: Path | None = None,
    min_interval_seconds: float = 1.0,
    max_retries: int = 3,
    retry_backoff_seconds: float = 0.5,
) -> ReportListing:
    """Always hit the source. A saved listing is never proof that no newer report exists."""
    html, final_url = fetch_profile_html(
        company,
        transport,
        min_interval_seconds=min_interval_seconds,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
    )
    listing = list_reports(
        company,
        html=html,
        source_url=final_url,
        from_cache=False,
        retrieved_at=_utcnow(),
    )
    tab_reason = ""
    if listing.unavailable:
        tab = statements_index_url(
            html, page_url=final_url, symbol=company.saudi_exchange.company_symbol
        )
        if tab:
            status, tab_html, tab_final = _fetch_html(
                transport,
                tab,
                max_retries=max_retries,
                retry_backoff_seconds=retry_backoff_seconds,
                min_interval_seconds=min_interval_seconds,
                referer=final_url,
            )
            if status in {401, 403}:
                raise BlockedAccess(f"HTTP {status} fetching statements tab {tab}")
            if status >= 400:
                tab_reason = (
                    f" Website statementsTabData GET returned HTTP {status} "
                    "(not an official API; WebSphere AJAX from the profile page)."
                )
            else:
                listing = list_reports(
                    company,
                    html=tab_html,
                    source_url=tab_final,
                    from_cache=False,
                    retrieved_at=_utcnow(),
                )
                html = tab_html
                final_url = tab_final
                if listing.unavailable:
                    tab_reason = (
                        " statementsTabData HTML contained no /Resources/fsPdf/ links."
                    )
        else:
            tab_reason = " No statementsTabData URL could be derived from the profile HTML."
    if storage_root is not None:
        cdir = company_dir(storage_root, company.ticker)
        payload = {
            "retrieved_at": listing.retrieved_at,
            "source_url": listing.source_url or final_url,
            "from_cache": False,
            "note": (
                "This cached listing is not proof that no newer report exists. "
                "Re-fetch from source before concluding coverage."
            ),
            "html": html,
        }
        (cdir / LISTING_CACHE_NAME).write_text(
            __import__("json").dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if listing.unavailable:
        return ReportListing(
            reports=listing.reports,
            from_cache=False,
            retrieved_at=listing.retrieved_at,
            unavailable=True,
            reason=(
                listing.reason
                + " Static profile HTML without /Resources/fsPdf/ links is not an empty market."
                + tab_reason
            ),
            source_url=listing.source_url or final_url,
        )
    return listing


def load_listing_cache(company: CompanyIdentity, storage_root: Path) -> ReportListing | None:
    """Return a labelled cache copy. Callers must not use this as a freshness proof."""
    import json

    path = company_dir(storage_root, company.ticker) / LISTING_CACHE_NAME
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    html = data.get("html") or ""
    listing = list_reports(
        company,
        html=html,
        source_url=data.get("source_url"),
        from_cache=True,
        retrieved_at=data.get("retrieved_at"),
    )
    return listing


def resolve_and_retrieve(
    *,
    name: str | None = None,
    ticker: str | None = None,
    period: str,
    report_type: ReportType = ReportType.ANNUAL,
    language: str = "en",
    storage_root: Path,
    transport: Transport | None = None,
    revalidate: bool = False,
    min_interval_seconds: float = 1.0,
) -> tuple[ReportSelection, RetrievalResult | None, ReportListing | None, str]:
    resolved = resolve_company(name=name, ticker=ticker)
    if resolved.status.value != "matched" or resolved.company is None:
        return (
            ReportSelection(
                status=resolved.status.value,
                report=None,
                candidates=(),
                reason=resolved.reason,
            ),
            None,
            None,
            resolved.reason,
        )
    transport = transport or UrllibTransport()
    listing = list_reports_from_source(
        resolved.company,
        transport,
        storage_root=storage_root,
        min_interval_seconds=min_interval_seconds,
    )
    if listing.unavailable:
        return (
            ReportSelection(
                status="unavailable",
                report=None,
                candidates=(),
                reason=listing.reason,
            ),
            None,
            listing,
            listing.reason,
        )
    selection = select_report(
        listing.reports, period=period, report_type=report_type, language=language
    )
    if selection.status != "selected" or selection.report is None:
        return selection, None, listing, selection.reason
    result = retrieve_report(
        resolved.company,
        selection.report,
        storage_root,
        transport,
        revalidate=revalidate,
        min_interval_seconds=min_interval_seconds,
    )
    return selection, result, listing, result.reason
