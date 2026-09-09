"""D6: stored Maaden 2025 annual English FS — skipped if the gitignored PDF is absent."""

from __future__ import annotations

from pathlib import Path

import pytest

from saudi_exchange_reports.reading import extract_report, search_extracted

MAADEN_HASH = "d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e"
MAADEN_FS = (
    Path(__file__).resolve().parents[1]
    / "storage"
    / "reports"
    / "1211"
    / f"{MAADEN_HASH}.pdf"
)

pytestmark = pytest.mark.skipif(
    not MAADEN_FS.exists(),
    reason="gitignored Maaden 2025 annual English FS PDF is not in storage",
)

# Cover, image-only primary statements, first notes page, IAS 29 / IFRS 15 notes.
MAADEN_PAGES = (1, 2, 4, 13, 14, 15, 16, 17, 18, 19, 29, 30)


@pytest.fixture(scope="module")
def maaden_doc():
    return extract_report(
        MAADEN_FS,
        storage_root=MAADEN_FS.parents[1],
        pages=MAADEN_PAGES,
    )


def test_maaden_identity_hash_and_page_indices(maaden_doc):
    assert maaden_doc.content_hash == MAADEN_HASH
    assert {p.page_number for p in maaden_doc.pages} == set(MAADEN_PAGES)


def test_maaden_notes_are_native_not_ocr(maaden_doc):
    page = next(p for p in maaden_doc.pages if p.page_number == 19)
    assert page.method == "native"
    text = page.text
    assert "Notes to the consolidated financial statements" in text
    assert "All amounts in Saudi Riyals unless otherwise stated" in text
    assert "year ended 31 December 2025" in text
    assert "38,887,634,180" in text or "38887634180" in text.replace(",", "")
    hits = search_extracted(maaden_doc, "share capital")
    assert hits.status == "found"
    assert any(h.page_number == 19 for h in hits.hits)


def test_maaden_image_pages_are_ocr_or_unreadable(maaden_doc):
    image_pages = [p for p in maaden_doc.pages if p.page_number in (4, 13, 14, 15, 16, 17, 18)]
    assert len(image_pages) == 7
    for page in image_pages:
        assert page.method in {"ocr", "mixed", "unreadable"}
        if page.method == "unreadable":
            assert page.unreadable_reason
        else:
            assert page.text.strip()


def test_maaden_primary_statements_ocr_headings_and_figures(maaden_doc):
    page13 = next(p for p in maaden_doc.pages if p.page_number == 13)
    if page13.method == "unreadable":
        pytest.skip("page 13 OCR recovered no readable text")
    blob = page13.text.lower()
    assert "consolidated statement of profit or loss" in blob
    assert "year ended 31 december 2025" in blob
    assert "revenue" in blob
    compact = page13.text.replace(",", "").replace(" ", "")
    assert "38577730228" in compact or "38,577,730,228" in page13.text


def test_maaden_metadata_from_stated_notes(maaden_doc):
    meta = maaden_doc.metadata
    assert meta.currency.status == "stated"
    assert meta.currency.value
    assert "riyals" in meta.currency.value.lower() or "SAR" in meta.currency.value
    assert meta.scale.status == "stated"
    assert "thousand" not in (meta.scale.value or "").lower()
    assert "million" not in (meta.scale.value or "").lower()
    assert meta.period.status == "stated"
    assert "2025" in (meta.period.value or "")
    assert meta.duration.status == "stated"
    assert meta.scope.status == "stated"
    assert "consolidated" in (meta.scope.value or "").lower()
    assert meta.restatement.status == "unknown"
    assert meta.quarterly_vs_cumulative.status == "unknown"


def test_maaden_page_numbers_are_pdf_indices_not_footer_titles(maaden_doc):
    page19 = next(p for p in maaden_doc.pages if p.page_number == 19)
    assert "Maaden) | 18" in page19.text or "Maaden)|18" in page19.text.replace(" ", "")
    assert page19.page_number == 19
