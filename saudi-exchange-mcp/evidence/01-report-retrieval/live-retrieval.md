# Live retrieval log

Date: 2026-09-09 UTC. Working directory: `/workspace/saudi-exchange-mcp`. Environment: Python 3.12, venv `.venv`, `PYTHONPATH=src`. PDFs stay under `storage/` (gitignored) and are not redistributed here.

## Commands

Identity:

```bash
PYTHONPATH=src python3 -m saudi_exchange_reports resolve --ticker 2222
PYTHONPATH=src python3 -m saudi_exchange_reports resolve --name 'Saudi Arabian'
```

Listing + retrieve by period (live tab unavailable):

```bash
PYTHONPATH=src python3 -m saudi_exchange_reports retrieve \
  --ticker 1211 --period 2025 --type annual --language en \
  --storage storage/reports --interval 0
```

Original PDF (known `/Resources/fsPdf/` URL on the verified host):

```bash
PYTHONPATH=src python3 -m saudi_exchange_reports retrieve-url \
  --ticker 1211 \
  --url 'https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf' \
  --period 2025 --type annual --language en \
  --title 'Maaden financial statements / annual report (English, source filename 370_0_2026-03-29)' \
  --storage storage/reports --interval 1.0
```

Repeat (cache):

```bash
PYTHONPATH=src python3 -m saudi_exchange_reports retrieve-url \
  --ticker 1211 \
  --url 'https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf' \
  --period 2025 --type annual --language en --storage storage/reports --interval 0
```

## Results

### Resolve

- `--ticker 2222` → `matched`, `company_id=sa-tdwl-2222`, `issuer_id=1541`, `google_finance.verified=false`.
- `--name 'Saudi Arabian'` → `ambiguous`, candidates `2222` and `1211` (no silent pick).

### Live listing (Maaden 1211)

Exit code 1. Listing:

- `unavailable: true`
- `count: 0`
- `from_cache: false`
- Reason includes: static profile HTML has no `/Resources/fsPdf/` links; **website `statementsTabData` GET returned HTTP 500** (not an official API).
- Selection was also `unavailable` with that listing reason (not treated as “period 2025 missing from a complete index”).

### Live PDF — success

First `retrieve-url` (2026-09-09T20:36:56+00:00):

| Field | Value |
|---|---|
| status | `downloaded` |
| HTTP | 200, `Content-Type: application/pdf` |
| magic | `%PDF-1.6` |
| bytes | 10216122 |
| content_hash | `dae44e050e70e412049516a4caea688f9ff0cd918cab44b393ee86ecaf4b02a6` |
| etag | `"9be2ba-64e29266f7779"` |
| source/final URL | `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-29_11-05-45_En.pdf` |
| local_path | `storage/reports/1211/dae44e050e70e412049516a4caea688f9ff0cd918cab44b393ee86ecaf4b02a6.pdf` |
| sidecar | `storage/reports/1211/dae44e050e70e412049516a4caea688f9ff0cd918cab44b393ee86ecaf4b02a6.pdf.json` |
| ticker / company_id | `1211` / `sa-tdwl-1211` |
| page_count | 216 |

Page inspection (first pages only; not full extraction):

- Page 1: `INTEGRATED REPORT 2025` / `Unearth Tomorrow` (period **2025**; company name not on the cover).
- Page 3: `Maaden — Integrated Report 2025`, `MAADEN`, “About Maaden…”.
- Bounded library inspection after cache hit: `identity_confirmed=true`, `period_confirmed=true`.

Second `retrieve-url`: `status=cache_hit`, same hash, no second copy. Reason states this is **not** a fresh source check. `revalidate` would GET again and compare hashes (unit-tested; not a live restatement).

### Access header check (same URL, same hour)

- urllib `User-Agent` only → **403**
- urllib `User-Agent` + `Accept: */*` → **200** `%PDF-`
- curl HTTP/1.1 from this IP → **403** Akamai Access Denied

## What was not retrieved

- No Aramco financial-report PDF (no live `fsPdf` URL).
- No Arabic-language Maaden PDF (`…_Ar.pdf` not requested without a listed URL).
- No interim PDF from the live tab.
- PDF corpus is not committed.
