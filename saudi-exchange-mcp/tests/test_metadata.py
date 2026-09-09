"""D5: financial metadata only when the document states it."""

from __future__ import annotations

from pathlib import Path

from pdf_fixtures import text_pdf

from saudi_exchange_reports.reading import extract_report


def _put(tmp_path: Path, name: str, data: bytes) -> Path:
    storage = tmp_path / "reports"
    storage.mkdir(parents=True, exist_ok=True)
    path = storage / name
    path.write_bytes(data)
    return path


def test_stated_currency_scale_period_scope(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "stated.pdf",
        text_pdf(
            [
                "Consolidated financial statements\n"
                "for the year ended 31 December 2025\n"
                "(All amounts in Saudi Riyals unless otherwise stated)\n"
                "Revenue 38577730228"
            ]
        ),
    )
    meta = extract_report(pdf, storage_root=tmp_path / "reports").metadata
    assert meta.currency.status == "stated"
    assert meta.currency.value
    assert "riyals" in meta.currency.value.lower() or "SAR" in meta.currency.value
    assert meta.scale.status == "stated"
    assert meta.scale.value is not None
    assert "thousand" not in (meta.scale.value or "").lower()
    assert "million" not in (meta.scale.value or "").lower()
    assert meta.period.status == "stated"
    assert "2025" in (meta.period.value or "")
    assert meta.duration.status == "stated"
    assert meta.scope.status == "stated"
    assert "consolidated" in (meta.scope.value or "").lower()
    assert meta.quarterly_vs_cumulative.status == "unknown"
    assert meta.restatement.status == "unknown"


def test_thousands_scale_only_when_stated(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "thousands.pdf",
        text_pdf(["Amounts in thousands of Saudi Riyals\nRevenue 12"]),
    )
    meta = extract_report(pdf, storage_root=tmp_path / "reports").metadata
    assert meta.scale.status == "stated"
    assert "thousand" in (meta.scale.value or "").lower()


def test_omitted_metadata_is_unknown(tmp_path: Path):
    pdf = _put(tmp_path, "bare.pdf", text_pdf(["Board minutes excerpt without figures"]))
    meta = extract_report(pdf, storage_root=tmp_path / "reports").metadata
    assert meta.currency.status == "unknown"
    assert meta.scale.status == "unknown"
    assert meta.period.status == "unknown"
    assert meta.duration.status == "unknown"
    assert meta.quarterly_vs_cumulative.status == "unknown"
    assert meta.scope.status == "unknown"
    assert meta.restatement.status == "unknown"
    assert meta.currency.value is None


def test_quarterly_versus_cumulative_when_labelled(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "interim.pdf",
        text_pdf(
            [
                "Interim condensed consolidated financial statements\n"
                "For the three-month period ended 30 September 2025 (quarterly)\n"
                "and the nine-month period then ended (cumulative)\n"
                "Revenue three months 10 cumulative nine months 40"
            ]
        ),
    )
    meta = extract_report(pdf, storage_root=tmp_path / "reports").metadata
    assert meta.quarterly_vs_cumulative.status == "stated"
    value = (meta.quarterly_vs_cumulative.value or "").lower()
    assert "quarter" in value and "cumul" in value
    assert meta.duration.status == "stated"


def test_standalone_scope_when_statements_are_standalone(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "solo.pdf",
        text_pdf(
            [
                "Separate financial statements of the parent company\n"
                "These standalone financial statements are presented in Saudi Riyals"
            ]
        ),
    )
    meta = extract_report(pdf, storage_root=tmp_path / "reports").metadata
    assert meta.scope.status == "stated"
    assert "standalone" in (meta.scope.value or "").lower() or "separate" in (meta.scope.value or "").lower()


def test_restated_comparatives_when_stated(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "restated.pdf",
        text_pdf(
            [
                "Consolidated statement of financial position\n"
                "The comparative figures for 2024 have been restated\n"
                "Revenue 2025 100 2024 restated 80"
            ]
        ),
    )
    meta = extract_report(pdf, storage_root=tmp_path / "reports").metadata
    assert meta.restatement.status == "stated"


def test_ias29_restated_measuring_unit_is_not_comparative_restatement(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "ias29.pdf",
        text_pdf(
            [
                "The financial statements of the Group’s subsidiary functioning in a hyperinflationary "
                "economy are restated in terms of the measuring unit current at the end of the reporting period. "
                "The restatements are based on a conversion factor derived from the general price index."
            ]
        ),
    )
    meta = extract_report(pdf, storage_root=tmp_path / "reports").metadata
    assert meta.restatement.status == "unknown"


def test_ifrs15_standalone_selling_price_is_not_statement_scope(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "ifrs15.pdf",
        text_pdf(
            [
                "The disaggregation between separate performance obligations is done based on the "
                "standalone selling price."
            ]
        ),
    )
    meta = extract_report(pdf, storage_root=tmp_path / "reports").metadata
    assert meta.scope.status == "unknown"


def test_zakat_separate_financial_statements_is_not_statement_scope(tmp_path: Path):
    pdf = _put(
        tmp_path,
        "zakat.pdf",
        text_pdf(
            [
                "Zakat return of the Company and wholly owned subsidiaries are submitted to the ZATCA "
                "based on separate financial statements prepared for zakat purposes only."
            ]
        ),
    )
    meta = extract_report(pdf, storage_root=tmp_path / "reports").metadata
    assert meta.scope.status == "unknown"
