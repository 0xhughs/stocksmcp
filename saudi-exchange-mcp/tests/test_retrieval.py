"""D4/D5: original PDF download, provenance, page inspection, cache/version."""

from __future__ import annotations

import json
from pathlib import Path

from helpers import FakeResponse, FakeTransport, synthetic_pdf_bytes

from saudi_exchange_reports.catalog import MAADEN
from saudi_exchange_reports.listing import ReportType, parse_report_index_html, select_report
from saudi_exchange_reports.retrieval import (
    inspect_pdf_identity,
    retrieve_report,
)

FIXTURES = Path(__file__).parent / "fixtures"

PDF_URL = "https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf"
PAGE_TEXT = "Saudi Arabian Mining Co. Annual Report for the year 2025"


def _selected_report():
    html = (FIXTURES / "maaden_reports.html").read_text(encoding="utf-8")
    reports = parse_report_index_html(html, company=MAADEN)
    selected = select_report(
        reports, period="2025", report_type=ReportType.ANNUAL, language="en"
    )
    assert selected.report is not None
    return selected.report


def test_download_records_provenance_and_pdf_magic(tmp_path: Path):
    pdf = synthetic_pdf_bytes(PAGE_TEXT)
    transport = FakeTransport(
        {PDF_URL: FakeResponse(status=200, body=pdf, headers={"Content-Type": "application/pdf"})}
    )
    result = retrieve_report(
        company=MAADEN,
        report=_selected_report(),
        storage_root=tmp_path / "reports",
        transport=transport,
    )
    assert result.status == "downloaded"
    assert result.record is not None
    assert result.record.local_path.exists()
    data = result.record.local_path.read_bytes()
    assert data.startswith(b"%PDF")
    assert result.record.content_hash
    assert result.record.source_url == PDF_URL
    assert result.record.final_url == PDF_URL
    assert result.record.ticker == "1211"
    assert result.record.retrieved_at
    meta = json.loads(Path(str(result.record.local_path) + ".json").read_text(encoding="utf-8"))
    assert meta["content_hash"] == result.record.content_hash
    assert meta["company_id"] == MAADEN.company_id


def test_inspect_pdf_confirms_identity_and_period(tmp_path: Path):
    pdf = synthetic_pdf_bytes(PAGE_TEXT)
    path = tmp_path / "sample.pdf"
    path.write_bytes(pdf)
    inspection = inspect_pdf_identity(
        path, company=MAADEN, period="2025"
    )
    assert inspection.identity_confirmed is True
    assert inspection.period_confirmed is True
    assert "mining" in inspection.page_text.lower() or "maaden" in inspection.page_text.lower()


def test_repeat_request_reuses_valid_cache(tmp_path: Path):
    pdf = synthetic_pdf_bytes(PAGE_TEXT)
    transport = FakeTransport(
        {PDF_URL: [FakeResponse(status=200, body=pdf, headers={"Content-Type": "application/pdf"})]}
    )
    storage = tmp_path / "reports"
    first = retrieve_report(MAADEN, _selected_report(), storage, transport)
    second = retrieve_report(MAADEN, _selected_report(), storage, transport)
    assert first.status == "downloaded"
    assert second.status == "cache_hit"
    assert second.record.content_hash == first.record.content_hash
    assert len([c for c in transport.calls if c[0] == "GET"]) == 1


def test_changed_source_preserves_prior_bytes(tmp_path: Path):
    pdf_v1 = synthetic_pdf_bytes(PAGE_TEXT)
    pdf_v2 = synthetic_pdf_bytes(PAGE_TEXT + " restated")
    transport = FakeTransport(
        {
            PDF_URL: [
                FakeResponse(status=200, body=pdf_v1, headers={"Content-Type": "application/pdf", "ETag": "v1"}),
                FakeResponse(status=200, body=pdf_v2, headers={"Content-Type": "application/pdf", "ETag": "v2"}),
            ]
        }
    )
    storage = tmp_path / "reports"
    first = retrieve_report(MAADEN, _selected_report(), storage, transport, revalidate=True)
    second = retrieve_report(MAADEN, _selected_report(), storage, transport, revalidate=True)
    assert first.status == "downloaded"
    assert second.status == "updated"
    assert first.record.content_hash != second.record.content_hash
    assert first.record.local_path.exists()
    assert second.record.local_path.exists()
    assert first.record.local_path.read_bytes() == pdf_v1
    assert second.record.local_path.read_bytes() == pdf_v2


def test_corrupt_cache_is_rejected_and_redownloaded(tmp_path: Path):
    pdf = synthetic_pdf_bytes(PAGE_TEXT)
    transport = FakeTransport(
        {
            PDF_URL: [
                FakeResponse(status=200, body=pdf, headers={"Content-Type": "application/pdf"}),
                FakeResponse(status=200, body=pdf, headers={"Content-Type": "application/pdf"}),
            ]
        }
    )
    storage = tmp_path / "reports"
    first = retrieve_report(MAADEN, _selected_report(), storage, transport)
    first.record.local_path.write_bytes(b"not a pdf")
    second = retrieve_report(MAADEN, _selected_report(), storage, transport)
    assert second.status == "downloaded"
    assert second.record.local_path.read_bytes().startswith(b"%PDF")


def test_retrieve_from_known_fspdf_url(tmp_path: Path):
    from saudi_exchange_reports.retrieval import retrieve_from_url

    pdf = synthetic_pdf_bytes(PAGE_TEXT)
    transport = FakeTransport(
        {PDF_URL: FakeResponse(status=200, body=pdf, headers={"Content-Type": "application/pdf"})}
    )
    result = retrieve_from_url(
        company=MAADEN,
        url=PDF_URL,
        storage_root=tmp_path / "reports",
        transport=transport,
        period="2025",
        report_type=ReportType.ANNUAL,
        language="en",
        title="Maaden annual report 2025 (English)",
    )
    assert result.status == "downloaded"
    assert result.record is not None
    assert result.record.source_url == PDF_URL
    assert result.record.local_path.read_bytes().startswith(b"%PDF")
    assert result.inspection is not None
    assert result.inspection.identity_confirmed is True


def test_retrieve_from_url_rejects_non_fspdf_host(tmp_path: Path):
    from saudi_exchange_reports.retrieval import retrieve_from_url

    result = retrieve_from_url(
        company=MAADEN,
        url="https://evil.example/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf",
        storage_root=tmp_path / "reports",
        transport=FakeTransport({}),
        period="2025",
    )
    assert result.status == "failed"
    assert result.record is None


def test_cached_listing_is_labelled_and_not_proof_of_freshness():
    from saudi_exchange_reports.listing import list_reports

    html = (FIXTURES / "maaden_reports.html").read_text(encoding="utf-8")
    cached = list_reports(MAADEN, html=html, from_cache=True)
    assert cached.from_cache is True
    assert cached.unavailable is False
    # Callers must not treat this as evidence that no newer report exists.
    assert cached.from_cache is not False
