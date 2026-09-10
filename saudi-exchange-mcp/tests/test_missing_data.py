"""D4: missing is not zero; uncertain / unavailable / not_found outcomes."""

from __future__ import annotations

from pathlib import Path

from pdf_fixtures import faint_text_image_pdf, table_pdf, text_pdf

from saudi_exchange_reports.reading import extract_report, find_line_item, search_extracted


def _put(tmp_path: Path, name: str, data: bytes) -> Path:
    storage = tmp_path / "reports"
    storage.mkdir(parents=True, exist_ok=True)
    path = storage / name
    path.write_bytes(data)
    return path


def test_blank_table_cell_is_blank_not_zero(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "blank.pdf",
        table_pdf([["Item", "Amount"], ["Revenue", "50"], ["Other income", ""]]),
    )
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    cells = [c for table in doc.pages[0].tables for c in table.cells]
    blank = next(c for c in cells if c.row == 2 and c.column == 1)
    assert blank.status == "blank"
    assert blank.parsed_number is None
    assert blank.original == ""


def test_missing_line_item_is_not_found_not_zero(tmp_path: Path):
    pdf = _put(tmp_path, "items.pdf", text_pdf(["Revenue 100\nCost of sales 40"]))
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    result = find_line_item(doc, "operating cash flow")
    assert result.status == "not_found"
    assert result.parsed_number is None
    assert result.reason
    assert "0" not in (result.original or "")
    assert result.parsed_number != 0


def test_empty_search_is_not_found_not_proof_of_no_activity(tmp_path: Path):
    pdf = _put(tmp_path, "search.pdf", text_pdf(["Share capital SAR 10"]))
    result = search_extracted(
        extract_report(pdf, storage_root=tmp_path / "reports"),
        "operating cash flow from discontinued operations",
    )
    assert result.status == "not_found"
    assert result.hits == ()
    reason = result.reason.lower()
    assert "not_found" in result.status
    assert "zero" not in reason
    assert "did not occur" in reason or "not evidence" in reason or "not proof" in reason


def test_low_confidence_ocr_is_uncertain(tmp_path: Path):
    pdf = _put(tmp_path, "faint.pdf", faint_text_image_pdf("hidden figure 999"))
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    page = doc.pages[0]
    assert page.method in {"ocr", "unreadable"}
    if page.method == "unreadable":
        assert page.unreadable_reason
    else:
        assert page.confidence_label == "uncertain" or all(
            span.confidence == "uncertain" for span in page.spans
        )


def test_untrusted_pdf_strings_are_data(tmp_path: Path):
    payload = "javascript:alert(1) os.system('rm -rf /')"
    pdf = _put(tmp_path, "untrusted.pdf", text_pdf([payload]))
    doc = extract_report(pdf, storage_root=tmp_path / "reports")
    assert "javascript:alert(1)" in doc.pages[0].text
    assert (tmp_path / "reports").exists()
    hits = search_extracted(doc, "javascript:alert")
    assert hits.status == "found"
    assert hits.hits[0].original
