"""D2: Arabic and English extraction; original Arabic labels preserved."""

from __future__ import annotations

import io
from pathlib import Path

from pdf_fixtures import logicalize_arabic, image_only_pdf
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from saudi_exchange_reports.reading import extract_report, search_extracted


def _put(tmp_path: Path, name: str, data: bytes) -> Path:
    storage = tmp_path / "reports"
    storage.mkdir(parents=True, exist_ok=True)
    path = storage / name
    path.write_bytes(data)
    return path


def _english_pdf(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(72, 720, text)
    c.showPage()
    c.save()
    return buf.getvalue()


def _bilingual_pdf(arabic: str, english: str) -> bytes:
    font_name = "NotoNaskhArabic"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(
            TTFont(font_name, "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf")
        )
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont(font_name, 16)
    c.drawString(72, 720, arabic)
    c.showPage()
    c.setFont("Helvetica", 12)
    c.drawString(72, 720, english)
    c.save()
    return buf.getvalue()


def test_arabic_image_only_page_is_ocr(tmp_path: Path):
    pdf = _put(tmp_path, "ar-image.pdf", image_only_pdf(["إيرادات", "قائمة المركز المالي"], arabic=True))
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    page = doc.pages[0]
    assert page.method == "ocr"
    hits = search_extracted(doc, "إيرادات")
    assert hits.status == "found"
    assert any("\u0600" <= ch <= "\u06FF" for ch in page.text)


def test_english_labels_are_extracted(tmp_path: Path):
    pdf = _put(tmp_path, "en.pdf", _english_pdf("Consolidated statement of profit or loss"))
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    assert "Consolidated statement of profit or loss" in doc.pages[0].text
    hits = search_extracted(doc, "profit or loss")
    assert hits.status == "found"


def test_arabic_labels_are_preserved_and_searchable(tmp_path: Path):
    pdf = _put(tmp_path, "ar.pdf", _bilingual_pdf("قائمة المركز المالي إيرادات", "keep-english"))
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    page = doc.pages[0]
    combined = page.text + logicalize_arabic(page.text)
    assert "إيرادات" in combined
    assert any("\u0600" <= ch <= "\u06FF" for ch in page.text), "Arabic must not be dropped"
    hits = search_extracted(doc, "إيرادات")
    assert hits.status == "found"
    assert hits.hits[0].page_number == 1
    assert any(any("\u0600" <= ch <= "\u06FF" for ch in span.original) for span in page.spans)
    assert "iiradat" not in page.text.lower()


def test_arabic_and_english_in_one_document(tmp_path: Path):
    pdf = _put(tmp_path, "both.pdf", _bilingual_pdf("قائمة المركز المالي إيرادات", "Revenue"))
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    assert len(doc.pages) == 2
    ar_hits = search_extracted(doc, "إيرادات")
    en_hits = search_extracted(doc, "Revenue")
    assert ar_hits.status == "found"
    assert en_hits.status == "found"
    assert ar_hits.hits[0].page_number == 1
    assert en_hits.hits[0].page_number == 2
