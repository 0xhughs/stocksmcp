"""D1: page-level extraction with provenance, tables, and fail-closed paths."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pdf_fixtures import table_pdf, text_pdf

from saudi_exchange_reports.errors import InvalidPdf, UnsafeDestination
from saudi_exchange_reports.reading import extract_report, read_pages, search_extracted


def _put(tmp_path: Path, name: str, data: bytes) -> Path:
    storage = tmp_path / "reports"
    storage.mkdir(parents=True, exist_ok=True)
    path = storage / name
    path.write_bytes(data)
    return path


def test_extracts_per_page_text_with_hash_path_page_and_method(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "two.pdf",
        text_pdf(["Cover page identity Maaden", "Notes share capital SAR 10"]),
    )
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    assert doc.content_hash == digest
    assert Path(doc.local_path) == pdf.resolve()
    assert len(doc.pages) == 2
    assert doc.pages[0].page_number == 1
    assert doc.pages[1].page_number == 2
    assert "Cover page identity Maaden" in doc.pages[0].text
    assert "share capital SAR 10" in doc.pages[1].text
    assert doc.pages[0].method == "native"
    assert doc.pages[1].method == "native"
    for page in doc.pages:
        assert page.content_hash == digest
        assert Path(page.local_path) == pdf.resolve()
        assert page.spans
        for span in page.spans:
            assert span.original
            assert span.content_hash == digest
            assert span.page_number == page.page_number
            assert span.method == "native"


def test_table_cells_keep_original_strings_and_optional_parse(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "table.pdf",
        table_pdf(
            [
                ["Line item", "2025", "2024"],
                ["Revenue", "100", "90"],
                ["Cost", "", "35"],
            ]
        ),
    )
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    page = doc.pages[0]
    assert page.page_number == 1
    assert page.tables
    cells = [cell for table in page.tables for cell in table.cells]
    originals = {(cell.row, cell.column, cell.original) for cell in cells}
    assert (0, 0, "Line item") in originals
    revenue = next(c for c in cells if c.original == "100")
    assert revenue.parsed_number == 100.0
    assert revenue.original == "100"
    assert revenue.page_number == 1
    assert revenue.content_hash == doc.content_hash
    assert revenue.method == "native"
    blank = next(c for c in cells if c.row == 2 and c.column == 1)
    assert blank.original == ""
    assert blank.parsed_number is None
    assert blank.status == "blank"


def test_read_pages_returns_requested_range_only(tmp_path: Path):
    pdf = _put(tmp_path, "range.pdf", text_pdf(["page-one-alpha", "page-two-bravo", "page-three-charlie"]))
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    pages = read_pages(doc, start=2, end=3)
    assert [p.page_number for p in pages] == [2, 3]
    assert "page-two-bravo" in pages[0].text
    assert "page-one-alpha" not in pages[0].text


def test_search_hits_include_page_and_content_hash(tmp_path: Path):
    pdf = _put(tmp_path, "search.pdf", text_pdf(["alpha revenue 12", "notes body"]))
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    result = search_extracted(doc, "revenue")
    assert result.status == "found"
    assert result.hits
    hit = result.hits[0]
    assert hit.page_number == 1
    assert hit.content_hash == doc.content_hash
    assert "revenue" in hit.original.lower()


def test_off_storage_path_is_rejected(tmp_path: Path):
    storage = tmp_path / "reports"
    storage.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(text_pdf(["secret"]))
    with pytest.raises(UnsafeDestination):
        extract_report(outside, storage_root=storage)


def test_non_pdf_bytes_fail_closed(tmp_path: Path):
    path = _put(tmp_path, "not.pdf", b"<html>not a pdf</html>")
    with pytest.raises(InvalidPdf):
        extract_report(path, storage_root=tmp_path / "reports")


def test_path_traversal_is_rejected(tmp_path: Path):
    storage = tmp_path / "reports"
    storage.mkdir()
    outside = tmp_path / "escaped.pdf"
    outside.write_bytes(text_pdf(["nope"]))
    sneaky = storage / ".." / "escaped.pdf"
    with pytest.raises(UnsafeDestination):
        extract_report(sneaky, storage_root=storage)
