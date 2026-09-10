"""Download original report PDFs with provenance, cache, and bounded failures."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from saudi_exchange_reports.errors import (
    BlockedAccess,
    DisallowedRedirect,
    DownloadFailed,
    InvalidPdf,
    PartialDownload,
    RetrievalError,
    UnsafeDestination,
)
from saudi_exchange_reports.http import Pacing, Transport, get_with_retries, host_allowed
from saudi_exchange_reports.inspect_pdf import PdfInspection, inspect_pdf_identity
from saudi_exchange_reports.listing import ReportType, report_from_fspdf_url
from saudi_exchange_reports.models import CompanyIdentity, FinancialReport
from saudi_exchange_reports.storage import company_dir, ensure_within, resolve_storage_root

__all__ = [
    "PdfInspection",
    "ProvenanceRecord",
    "RetrievalResult",
    "inspect_pdf_identity",
    "retrieve_from_url",
    "retrieve_report",
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class ProvenanceRecord:
    company_id: str
    ticker: str
    title: str
    period: str
    report_type: str
    language: str
    source_url: str
    final_url: str
    retrieved_at: str
    content_hash: str
    local_path: Path
    from_cache: bool
    etag: str | None = None


@dataclass(frozen=True)
class RetrievalResult:
    status: str
    record: ProvenanceRecord | None
    error_type: str | None
    reason: str
    inspection: PdfInspection | None = None


def _index_path(cdir: Path) -> Path:
    return cdir / "index.json"


def _load_index(cdir: Path) -> dict[str, Any]:
    path = _index_path(cdir)
    if not path.exists():
        return {"by_source_url": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"by_source_url": {}}
    if not isinstance(data, dict):
        return {"by_source_url": {}}
    data.setdefault("by_source_url", {})
    return data


def _save_index(cdir: Path, index: dict[str, Any]) -> None:
    _index_path(cdir).write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _valid_cached_pdf(path: Path, expected_hash: str | None = None) -> bool:
    if not path.is_file():
        return False
    data = path.read_bytes()
    if len(data) < 5 or not data.startswith(b"%PDF"):
        return False
    if expected_hash and hashlib.sha256(data).hexdigest() != expected_hash:
        return False
    return True


def _write_sidecar(pdf_path: Path, record: ProvenanceRecord) -> None:
    payload = {
        "company_id": record.company_id,
        "ticker": record.ticker,
        "title": record.title,
        "period": record.period,
        "report_type": record.report_type,
        "language": record.language,
        "source_url": record.source_url,
        "final_url": record.final_url,
        "retrieved_at": record.retrieved_at,
        "content_hash": record.content_hash,
        "local_path": str(record.local_path),
        "from_cache": record.from_cache,
        "etag": record.etag,
    }
    Path(str(pdf_path) + ".json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _record_from_cache_entry(
    company: CompanyIdentity,
    report: FinancialReport,
    cdir: Path,
    entry: dict[str, Any],
) -> ProvenanceRecord | None:
    digest = entry.get("content_hash")
    relative = entry.get("path")
    if not digest or not relative:
        return None
    path = ensure_within(cdir, cdir / Path(relative).name) if Path(str(relative)).name == Path(str(relative)).as_posix() else cdir / f"{digest}.pdf"
    # Always address files as {hash}.pdf inside the company dir.
    path = cdir / f"{digest}.pdf"
    if not _valid_cached_pdf(path, digest):
        return None
    return ProvenanceRecord(
        company_id=company.company_id,
        ticker=company.ticker,
        title=report.title,
        period=report.period,
        report_type=report.report_type.value,
        language=report.language,
        source_url=report.source_url,
        final_url=entry.get("final_url") or report.source_url,
        retrieved_at=entry.get("retrieved_at") or "",
        content_hash=digest,
        local_path=path,
        from_cache=True,
        etag=entry.get("etag"),
    )


def _validate_pdf_response(response_url: str, status: int, headers: dict[str, str], body: bytes) -> None:
    header_map = {k.lower(): v for k, v in headers.items()}
    if status in {401, 403}:
        raise BlockedAccess(f"HTTP {status} from {response_url}")
    if status == 404:
        raise DownloadFailed(f"HTTP 404 from {response_url}")
    if status >= 400:
        raise DownloadFailed(f"HTTP {status} from {response_url}")
    if not host_allowed(response_url):
        raise DisallowedRedirect(f"Final URL host is not allowed: {response_url}")
    content_type = header_map.get("content-type", "").split(";")[0].strip().lower()
    if body.lstrip().startswith(b"<") or body.lstrip().lower().startswith(b"<!doctype"):
        raise InvalidPdf("Response body is HTML, not a PDF.")
    if not body.startswith(b"%PDF"):
        raise InvalidPdf("Response body does not start with %PDF magic.")
    if content_type in {"text/html", "application/xhtml+xml"}:
        raise InvalidPdf(f"Content-Type {content_type} is not a PDF.")
    length = header_map.get("content-length")
    if length and length.isdigit() and int(length) != len(body):
        raise PartialDownload(
            f"Content-Length {length} does not match received {len(body)} bytes."
        )
    if len(body) < 8:
        raise PartialDownload("PDF body is truncated.")


def retrieve_report(
    company: CompanyIdentity,
    report: FinancialReport,
    storage_root: Path,
    transport: Transport,
    *,
    revalidate: bool = False,
    destination: Path | None = None,
    max_retries: int = 3,
    retry_backoff_seconds: float = 0.5,
    min_interval_seconds: float = 0.0,
) -> RetrievalResult:
    """Download or reuse an original PDF. Failures never look like success."""
    try:
        if not host_allowed(report.source_url) or not host_allowed(report.download_url):
            raise DisallowedRedirect("Report URL is not on a verified Saudi Exchange host.")
        root = resolve_storage_root(storage_root)
        root.mkdir(parents=True, exist_ok=True)
        if destination is not None:
            ensure_within(root, destination)
        cdir = company_dir(root, company.ticker)
        index = _load_index(cdir)
        cached_entry = index.get("by_source_url", {}).get(report.source_url) or {}
        cached_record = _record_from_cache_entry(company, report, cdir, cached_entry)

        if cached_record and not revalidate:
            inspection = inspect_pdf_identity(
                cached_record.local_path, company=company, period=report.period
            )
            return RetrievalResult(
                status="cache_hit",
                record=cached_record,
                error_type=None,
                reason="Reused a valid cached PDF. This is not a fresh source check.",
                inspection=inspection,
            )

        if cached_entry and not cached_record:
            # Corrupt / incomplete cache — do not treat as a valid record.
            cached_record = None

        pacing = Pacing(min_interval_seconds)
        response = get_with_retries(
            transport,
            report.download_url,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            pacing=pacing,
            headers={"Accept": "*/*"},
        )
        _validate_pdf_response(response.url or report.download_url, response.status, response.headers, response.body)
        digest = hashlib.sha256(response.body).hexdigest()
        pdf_path = cdir / f"{digest}.pdf"
        if destination is not None:
            pdf_path = ensure_within(root, destination)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        etag = None
        for key, value in response.headers.items():
            if key.lower() == "etag":
                etag = value
                break
        status = "downloaded"
        if cached_record and cached_record.content_hash != digest:
            status = "updated"
        elif cached_record and cached_record.content_hash == digest:
            status = "cache_hit"
            record = cached_record
            inspection = inspect_pdf_identity(record.local_path, company=company, period=report.period)
            return RetrievalResult(
                status="cache_hit",
                record=record,
                error_type=None,
                reason="Fresh source check matched the cached content hash.",
                inspection=inspection,
            )
        if pdf_path.exists() and pdf_path.read_bytes() != response.body:
            existing = pdf_path.read_bytes()
            existing_ok = existing.startswith(b"%PDF") and hashlib.sha256(existing).hexdigest() == digest
            if existing_ok:
                raise UnsafeDestination(f"Refusing to overwrite {pdf_path} with different content.")
        pdf_path.write_bytes(response.body)
        retrieved_at = _utcnow()
        record = ProvenanceRecord(
            company_id=company.company_id,
            ticker=company.ticker,
            title=report.title,
            period=report.period,
            report_type=report.report_type.value,
            language=report.language,
            source_url=report.source_url,
            final_url=response.url or report.download_url,
            retrieved_at=retrieved_at,
            content_hash=digest,
            local_path=pdf_path,
            from_cache=False,
            etag=etag,
        )
        _write_sidecar(pdf_path, record)
        previous = dict(cached_entry) if cached_entry else {}
        index.setdefault("by_source_url", {})[report.source_url] = {
            "content_hash": digest,
            "path": pdf_path.name,
            "final_url": record.final_url,
            "retrieved_at": retrieved_at,
            "etag": etag,
            "previous": previous or None,
        }
        _save_index(cdir, index)
        inspection = inspect_pdf_identity(pdf_path, company=company, period=report.period)
        return RetrievalResult(
            status=status,
            record=record,
            error_type=None,
            reason="Stored original PDF bytes with provenance.",
            inspection=inspection,
        )
    except RetrievalError as exc:
        return RetrievalResult(
            status="failed",
            record=None,
            error_type=type(exc).__name__,
            reason=str(exc),
        )


def retrieve_from_url(
    company: CompanyIdentity,
    url: str,
    storage_root: Path,
    transport: Transport,
    *,
    period: str,
    report_type: ReportType = ReportType.ANNUAL,
    language: str | None = None,
    title: str | None = None,
    revalidate: bool = False,
    destination: Path | None = None,
    max_retries: int = 3,
    retry_backoff_seconds: float = 0.5,
    min_interval_seconds: float = 0.0,
) -> RetrievalResult:
    """Download a known /Resources/fsPdf/ URL. Does not invent issuer filenames."""
    try:
        report = report_from_fspdf_url(
            company,
            url,
            period=period,
            report_type=report_type,
            language=language,
            title=title,
        )
    except RetrievalError as exc:
        return RetrievalResult(
            status="failed",
            record=None,
            error_type=type(exc).__name__,
            reason=str(exc),
        )
    return retrieve_report(
        company,
        report,
        storage_root,
        transport,
        revalidate=revalidate,
        destination=destination,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        min_interval_seconds=min_interval_seconds,
    )
