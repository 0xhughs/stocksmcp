# Live retrieval log

Date: 2026-09-09 UTC. Working directory: `/workspace/saudi-exchange-mcp`. Environment: Python 3.12, venv `.venv`, `PYTHONPATH=src`, Playwright 1.62 + system Google Chrome. PDFs stay under `storage/` (gitignored) and are not redistributed here.

## Commands

Identity:

```bash
PYTHONPATH=src python3 -m saudi_exchange_reports resolve --ticker 2222
PYTHONPATH=src python3 -m saudi_exchange_reports resolve --name 'Saudi Arabian'
```

Listing + retrieve by period (browser-driven tab after urllib `statementsTabData` HTTP 500):

```bash
PYTHONPATH=src python3 -m saudi_exchange_reports retrieve \
  --ticker 1211 --period 2025 --type annual --language en \
  --storage storage/reports --interval 1.0
```

Original PDF by known URL (does **not** satisfy D3; kept only as the earlier Integrated Report object):

```bash
PYTHONPATH=src python3 -m saudi_exchange_reports retrieve-url \
  --ticker 1211 \
  --url 'https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf' \
  --period 2025 --type annual --language en \
  --storage storage/reports --interval 1.0
```

## Results

### Resolve

- `--ticker 2222` → `matched`, `company_id=sa-tdwl-2222`, `issuer_id=1541`, `google_finance.verified=false`.
- `--name 'Saudi Arabian'` → `ambiguous`, candidates `2222` and `1211` (no silent pick).

### Live listing (Maaden 1211)

`list_reports_from_source(..., use_browser=True)` and CLI `retrieve` (browser fallback default):

- `unavailable: false`
- `count: 44` (`22` English from `locale=en`, `22` Arabic from `locale=ar`)
- `from_cache: false`
- Reason: listed from **browser-driven Financial Statements tab HTML** on Saudi Exchange (website UI, not an official API). urllib `statementsTabData` GET still HTTP **500** `CWSRV0295E` in the same run.
- Observed types on the table: **annual** (8), **interim** Q1/Q2/Q3 (28), **other** board reports (8). Q4 cells were dashes (no PDF). ESG cells were empty.
- Row dump: `evidence/01-report-retrieval/live-listing.json` (source-observed `/Resources/fsPdf/` URLs only).

Selection checks on that listing (no invented names):

| Request | Status | Source URL |
|---|---|---|
| 2025 annual en | selected | `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_En.pdf` |
| 2025 annual ar | selected | `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_Ar.pdf` |
| 2025 Q3 interim en | selected | `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2025-11-11_15-02-50_En.pdf` |
| 2025 Q3 interim ar | selected | `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2025-11-11_15-02-50_Ar.pdf` |

Aramco `2222` browser listing in the same environment: **44** `/Resources/fsPdf/` rows, issuer `1541`, English+Arabic. Example annual 2025 en: `https://www.saudiexchange.sa/Resources/fsPdf/1541_0_2026-03-10_08-18-44_En.pdf`. No Aramco PDF downloaded.

### Live PDF via discovery — success

CLI `retrieve --ticker 1211 --period 2025 --type annual --language en` (2026-09-09T21:03:04+00:00):

| Field | Value |
|---|---|
| selection | `selected` from the 44-row live listing |
| source URL | `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_En.pdf` |
| status | `downloaded` |
| HTTP | 200, `Content-Type: application/pdf` |
| magic | `%PDF-1.7` |
| bytes | 8681557 |
| content_hash | `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e` |
| local_path | `storage/reports/1211/d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e.pdf` |
| sidecar | `storage/reports/1211/d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e.pdf.json` |
| ticker / company_id | `1211` / `sa-tdwl-1211` |
| page_count | 126 |
| identity_confirmed | true |
| period_confirmed | true |

Early-page text (bounded inspection, not full extraction): **SAUDI ARABIAN MINING COMPANY (MAADEN)** / **Consolidated financial statements for the year ended 31 December 2025**.

This is the Financial Statements **Annual** cell for 2025, not the Board Report PDF `370_0_2026-03-29_11-05-45_En.pdf` (Integrated Report 2025) previously fetched with `retrieve-url`.

### Prior retrieve-url object (not D3)

Maaden Integrated Report 2025: `370_0_2026-03-29_11-05-45_En.pdf`, SHA-256 `dae44e050e70e412049516a4caea688f9ff0cd918cab44b393ee86ecaf4b02a6`, 10,216,122 bytes, 216 pages. Live listing types this URL as **other** (Board Report / 2025). Repeat `retrieve-url` remains `cache_hit`.

## What was not retrieved

- No Aramco PDF downloaded (listing only).
- No Arabic PDF downloaded (Arabic rows were listed and selectable; English annual was the retrieve demonstration).
- No interim PDF downloaded (Q1/Q2/Q3 rows were listed and selectable).
- PDF corpus is not committed.
