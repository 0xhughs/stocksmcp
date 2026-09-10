# Fixture extraction (not a stored filing)

Routine slice 02 proof uses **synthetic PDFs generated in pytest** (`tests/pdf_fixtures.py`). Those files are not live Saudi Exchange filings and are not redistributed here. Off-storage paths and non-PDF bytes fail closed.

## Command

From `/workspace/saudi-exchange-mcp`, after `pip install -r requirements.txt` and Tesseract/poppler as in `README.md`:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_extraction.py tests/test_arabic_english.py tests/test_ocr.py tests/test_missing_data.py tests/test_metadata.py tests/test_cli_reading.py -q
```

Representative CLI against a **temporary** two-page native-text PDF (2026-09-09, not a tracked fixture hash):

```bash
PYTHONPATH=src python3 -m saudi_exchange_reports extract --path "$TMP/reports/demo.pdf" --storage "$TMP/reports"
PYTHONPATH=src python3 -m saudi_exchange_reports read --path "$TMP/reports/demo.pdf" --storage "$TMP/reports" --page 1
PYTHONPATH=src python3 -m saudi_exchange_reports search --path "$TMP/reports/demo.pdf" --storage "$TMP/reports" --query "share capital"
PYTHONPATH=src python3 -m saudi_exchange_reports search --path "$TMP/reports/demo.pdf" --storage "$TMP/reports" --query "operating cash flow from discontinued operations"
```

## Results (fixture / synthetic)

| Check | Result |
|---|---|
| Per-page text | Page 1 native `Share capital SAR 10 per share`; page 2 native notes line; `content_hash` on every span |
| Table cells | Reportlab table: original `"100"` parses to `100.0`; blank `Cost`/`2025` cell is `blank` with `parsed_number=null`, not `0` |
| Arabic | Native Noto Naskh page preserves Arabic script; search for `إيرادات` is `found`. Image-only Arabic page is `method=ocr` with Tesseract `ara` |
| OCR | Image-only English page `method=ocr` recovers “Consolidated statement of financial position”. Native notes pages stay `native` |
| Unreadable | Noise-image page is `unreadable` with a reason and is **not omitted** |
| Search miss | `status=not_found`, `hits=[]`, reason states this is not a numeric amount and not proof the activity did not occur |
| Path fail-closed | Path outside `--storage` → `UnsafeDestination`; HTML bytes named `.pdf` → `InvalidPdf` |

Do not treat these fixture strings as Maaden (or any issuer) figures. Stored-PDF citations are in `maaden-fs-reading.md`.
