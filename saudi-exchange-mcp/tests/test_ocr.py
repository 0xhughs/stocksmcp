"""D3: local OCR fallback, mixed pages, and unreadable flags."""

from __future__ import annotations

from pathlib import Path

from pdf_fixtures import image_only_pdf, mixed_native_and_image_pdf, noise_image_pdf, text_pdf

from saudi_exchange_reports.reading import extract_report


def _put(tmp_path: Path, name: str, data: bytes) -> Path:
    storage = tmp_path / "reports"
    storage.mkdir(parents=True, exist_ok=True)
    path = storage / name
    path.write_bytes(data)
    return path


def test_image_only_page_is_labelled_ocr(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "image.pdf",
        image_only_pdf(["Consolidated statement of financial position", "Revenue 123456"]),
    )
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    page = doc.pages[0]
    assert page.method == "ocr"
    blob = page.text.lower()
    assert "consolidated" in blob
    assert "financial position" in blob
    assert page.unreadable_reason is None
    assert all(span.method == "ocr" for span in page.spans)


def test_native_text_page_is_not_sent_through_ocr(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "notes.pdf",
        text_pdf(["Notes to the consolidated financial statements All amounts in Saudi Riyals"]),
    )
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    assert doc.pages[0].method == "native"
    assert "Saudi Riyals" in doc.pages[0].text


def test_unreadable_page_is_flagged_not_omitted(tmp_path: Path):
    pdf = _put(tmp_path, "noise.pdf", noise_image_pdf())
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    assert len(doc.pages) == 1
    page = doc.pages[0]
    assert page.method == "unreadable"
    assert page.unreadable_reason
    assert page.page_number == 1
    assert page.content_hash == doc.content_hash


def test_mixed_page_uses_native_and_ocr(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "mixed.pdf",
        mixed_native_and_image_pdf(native="12", image_lines=["Directors responsibilities statement"]),
    )
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    page = doc.pages[0]
    assert page.method == "mixed"
    blob = page.text.lower()
    assert "directors" in blob and "responsibilities" in blob
