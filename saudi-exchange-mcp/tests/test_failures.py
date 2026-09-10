"""D6: bounded failures — invalid PDF, partial/failed download, blocked, unsafe paths, redirects, retries."""

from __future__ import annotations

from pathlib import Path

from helpers import FakeResponse, FakeTransport, synthetic_pdf_bytes

from saudi_exchange_reports.catalog import MAADEN
from saudi_exchange_reports.errors import (
    BlockedAccess,
    DisallowedRedirect,
    InvalidPdf,
    PartialDownload,
    UnsafeDestination,
)
from saudi_exchange_reports.listing import ReportType, parse_report_index_html, select_report
from saudi_exchange_reports.retrieval import retrieve_report

FIXTURES = Path(__file__).parent / "fixtures"
PDF_URL = "https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf"


def _report():
    html = (FIXTURES / "maaden_reports.html").read_text(encoding="utf-8")
    reports = parse_report_index_html(html, company=MAADEN)
    return select_report(reports, period="2025", report_type=ReportType.ANNUAL, language="en").report


def test_html_as_pdf_is_rejected(tmp_path: Path):
    html = b"<!DOCTYPE html><html><body>Access Denied</body></html>"
    transport = FakeTransport(
        {PDF_URL: FakeResponse(status=200, body=html, headers={"Content-Type": "text/html"})}
    )
    result = retrieve_report(MAADEN, _report(), tmp_path / "reports", transport)
    assert result.status == "failed"
    assert result.error_type == InvalidPdf.__name__
    assert not list((tmp_path / "reports").rglob("*.pdf"))


def test_failed_download_does_not_create_valid_record(tmp_path: Path):
    transport = FakeTransport(
        {PDF_URL: FakeResponse(status=500, body=b"error", headers={"Content-Type": "text/plain"})}
    )
    result = retrieve_report(MAADEN, _report(), tmp_path / "reports", transport)
    assert result.status == "failed"
    assert result.record is None
    assert not list((tmp_path / "reports").rglob("*.json"))


def test_partial_download_rejected(tmp_path: Path):
    pdf = synthetic_pdf_bytes("Saudi Arabian Mining Co. 2025")
    transport = FakeTransport(
        {
            PDF_URL: FakeResponse(
                status=200,
                body=pdf,
                headers={"Content-Type": "application/pdf", "Content-Length": str(len(pdf) + 5000)},
            )
        }
    )
    result = retrieve_report(MAADEN, _report(), tmp_path / "reports", transport)
    assert result.status == "failed"
    assert result.error_type == PartialDownload.__name__


def test_blocked_access_is_explicit(tmp_path: Path):
    body = b"<HTML><HEAD><TITLE>Access Denied</TITLE></HEAD><BODY><H1>Access Denied</H1></BODY></HTML>"
    transport = FakeTransport({PDF_URL: FakeResponse(status=403, body=body, headers={"Content-Type": "text/html"})})
    result = retrieve_report(MAADEN, _report(), tmp_path / "reports", transport)
    assert result.status == "failed"
    assert result.error_type == BlockedAccess.__name__


def test_unsafe_destination_outside_storage_root(tmp_path: Path):
    pdf = synthetic_pdf_bytes("Saudi Arabian Mining Co. 2025")
    transport = FakeTransport(
        {PDF_URL: FakeResponse(status=200, body=pdf, headers={"Content-Type": "application/pdf"})}
    )
    result = retrieve_report(
        MAADEN,
        _report(),
        tmp_path / "reports",
        transport,
        destination=tmp_path / ".." / "escaped.pdf",
    )
    assert result.status == "failed"
    assert result.error_type == UnsafeDestination.__name__


def test_disallowed_redirect_is_rejected(tmp_path: Path):
    transport = FakeTransport(
        {
            PDF_URL: FakeResponse(
                status=302,
                body=b"",
                headers={"Location": "https://evil.example/steal.pdf"},
                url=PDF_URL,
            )
        }
    )
    result = retrieve_report(MAADEN, _report(), tmp_path / "reports", transport)
    assert result.status == "failed"
    assert result.error_type == DisallowedRedirect.__name__


def test_retries_5xx_then_succeeds(tmp_path: Path):
    pdf = synthetic_pdf_bytes("Saudi Arabian Mining Co. 2025")
    transport = FakeTransport(
        {
            PDF_URL: [
                FakeResponse(status=503, body=b"try later"),
                FakeResponse(status=503, body=b"try later"),
                FakeResponse(status=200, body=pdf, headers={"Content-Type": "application/pdf"}),
            ]
        }
    )
    result = retrieve_report(
        MAADEN,
        _report(),
        tmp_path / "reports",
        transport,
        max_retries=3,
        retry_backoff_seconds=0,
    )
    assert result.status == "downloaded"
    get_calls = [c for c in transport.calls if c[0] == "GET"]
    assert len(get_calls) == 3


def test_does_not_retry_forbidden(tmp_path: Path):
    transport = FakeTransport(
        {PDF_URL: FakeResponse(status=403, body=b"no", headers={"Content-Type": "text/html"})}
    )
    result = retrieve_report(
        MAADEN, _report(), tmp_path / "reports", transport, max_retries=3, retry_backoff_seconds=0
    )
    assert result.status == "failed"
    assert len(transport.calls) == 1
