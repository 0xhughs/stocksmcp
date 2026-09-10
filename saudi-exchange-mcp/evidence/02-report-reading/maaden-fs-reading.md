# Stored Maaden 2025 annual English FS reading

**Source of the PDF:** slice 01 stored original, not re-downloaded in this slice.

| Field | Value |
|---|---|
| Ticker | `1211` |
| Object | Financial Statements Annual 2025 (English), **not** the Board/Integrated Report |
| Source URL | `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_En.pdf` |
| SHA-256 | `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e` |
| Local path | `storage/reports/1211/d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e.pdf` |
| Pages | 126 |
| Label | **stored-PDF evidence** (gitignored corpus; not redistributed) |

If the file is absent, retrieve it with the slice 01 CLI (`retrieve --ticker 1211 --period 2025 --type annual --language en`) and re-run the checks below. Do not use Integrated Report `dae44e050e70e412049516a4caea688f9ff0cd918cab44b393ee86ecaf4b02a6`.

Page numbers below are **PDF indices** (cover = page 1). Footer running titles such as `Saudi Arabian Mining Company (Maaden) | 18` appear on **PDF page 19**.

## Commands (2026-09-09)

From `/workspace/saudi-exchange-mcp`:

```bash
PDF=storage/reports/1211/d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e.pdf
PAGES=1,2,4,13-18,19,29,30

PYTHONPATH=src .venv/bin/python -m saudi_exchange_reports extract \
  --path "$PDF" --storage storage/reports --pages "$PAGES"

PYTHONPATH=src .venv/bin/python -m saudi_exchange_reports read \
  --path "$PDF" --storage storage/reports --pages "$PAGES" --page 13

PYTHONPATH=src .venv/bin/python -m saudi_exchange_reports search \
  --path "$PDF" --storage storage/reports --pages "$PAGES" \
  --query "share capital"

PYTHONPATH=src .venv/bin/python -m pytest tests/test_maaden_reading.py -q
```

Full extraction JSON is written under gitignored `storage/reports/_extracted/` and is **not** copied here.

## Per-page method (requested subset)

| PDF page | Method | Notes |
|---|---|---|
| 1 | native | Cover: consolidated financial statements, year ended 31 December 2025 |
| 2 | native | TOC (Directors’ responsibilities → PDF p.4; primary statements → 13–18 in 0-based TOC numbering which is PDF 13–18) |
| 4 | **ocr** | Image-only Directors’ responsibilities. Recovered heading and body; **not unreadable** |
| 13 | **ocr** | Consolidated statement of profit or loss |
| 14 | **ocr** | Consolidated statement of comprehensive income |
| 15 | **ocr** | Consolidated statement of financial position |
| 16 | **ocr** | Consolidated statement of changes in equity |
| 17 | **ocr** | Consolidated statement of cash flows (operating) |
| 18 | **ocr** | Consolidated statement of cash flows (continued, investing/financing) |
| 19 | native | Notes start; footer `Maaden) \| 18` |
| 29 | native | IAS 29 “restated in terms of the measuring unit” — **not** treated as comparative restatement |
| 30 | native | IFRS 15 “standalone selling price” — **not** treated as statement scope |

**Maaden pages 13–18 were OCR’d** (local Tesseract on pdf2image rasters at 200 DPI). None of those pages were flagged `unreadable`. Native notes were not sent through OCR.

## Representative citations

Native notes, PDF page 19:

- Heading: `Notes to the consolidated financial statements` / `for the year ended 31 December 2025` / `(All amounts in Saudi Riyals unless otherwise stated)`
- Share capital: `authorized and issued share capital of the Company amounts to Saudi Riyals (“SAR”) 38,887,634,180 divided into 3,888,763,418 shares with a nominal value of SAR 10 per share`

OCR, PDF page 13 (statement of profit or loss):

- Heading: `Consolidated statement of profit or loss` / `for the year ended 31 December 2025` / `(All amounts in Saudi Riyals unless otherwise stated)`
- Label `Revenue` with original figure string `38,577,730,228` (2025 SAR column)
- `Profit for the year` `8,527,980,356`; basic EPS `1.91`

OCR, PDF page 15 (financial position): `Share capital` original `38,887,634,180` (matches notes).

OCR, PDF page 4: `Statement of Directors’ responsibilities` for the year ended 31 December 2025.

## Metadata (stated vs unknown)

From the extracted subset (not inferred from magnitude):

| Field | Status | Value |
|---|---|---|
| currency | stated | Saudi Riyals (SAR) |
| scale | stated | full riyals (as stated) — wording is “unless otherwise stated”; **not** thousands/millions |
| period | stated | year ended 31 December 2025 |
| duration | stated | year |
| scope | stated | consolidated |
| quarterly vs cumulative | unknown | this annual FS does not label that distinction |
| comparative restatement | unknown | page 29 “restated” is IAS 29 measuring-unit language |

No Aramco PDF was used. No live restatement of Maaden comparatives is claimed.
