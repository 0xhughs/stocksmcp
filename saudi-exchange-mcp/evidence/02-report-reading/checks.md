# Checks

Routine tests **do not** require the live website. They use synthetic `%PDF` bytes from `tests/pdf_fixtures.py` and slice 01 HTML fixtures. Stored Maaden FS tests run only when the gitignored PDF is present (`tests/test_maaden_reading.py` skipif).

## Command

From `/workspace/saudi-exchange-mcp`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# system: tesseract-ocr tesseract-ocr-eng tesseract-ocr-ara poppler-utils
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q
```

Equivalent: `PYTHONPATH=src python3 -m pytest tests/ -q` after installing the Python deps. Reviewer does not need the exchange website.

Builder result (2026-09-09, disp-02-impl-001): **94 passed**.

Stored-PDF extra (same suite, file present in this checkout): `tests/test_maaden_reading.py` — 6 passed, pages 4 and 13–18 labelled `ocr` (not unreadable).

## What the tests prove

| Criterion | Tests | Live website? | Stored PDF? |
|---|---|---|---|
| D1 page-level text/tables, hash/path/1-based page/method; original strings; fail-closed paths | `tests/test_extraction.py` | No | No |
| D2 Arabic and English; original Arabic preserved; Arabic OCR | `tests/test_arabic_english.py` | No | No |
| D3 OCR labelling, native not forced through OCR, unreadable flagged | `tests/test_ocr.py` | No | Additional: `tests/test_maaden_reading.py` |
| D4 blank ≠ 0; missing line item `not_found`; empty search `not_found`; untrusted strings are data | `tests/test_missing_data.py` | No | No |
| D5 stated vs unknown metadata; IAS 29 / IFRS 15 / zakat negatives | `tests/test_metadata.py` | No | Additional Maaden notes |
| D6 representative Maaden citations | `tests/test_maaden_reading.py` | No | Yes, gitignored file or slice 01 retrieve |
| D7 CLI extract / read / search | `tests/test_cli_reading.py` | No | Additional CLI in `maaden-fs-reading.md` |
| Slice 01 still green | `tests/test_identity.py` and other slice 01 modules | No | No |

## Labelled separately

- **Fixture / synthetic:** `extraction.md`
- **Stored Maaden FS:** `maaden-fs-reading.md` and `sample-manifest.json` → `stored_pdf_results`
- **Not in this slice:** Google Finance, MCP, Aramco PDF download, full extraction dumps, PDF corpus
