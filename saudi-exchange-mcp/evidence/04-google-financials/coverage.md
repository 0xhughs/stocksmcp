# D5 — Coverage (2026-09-09)

Dated product coverage for the two pilot identities. Library: `get_coverage("ARAMCO")`. CLI: `python3 -m saudi_exchange_reports google-coverage ARAMCO`. Inventory flags for earnings and financials are **support** (no longer `defer`).

Google tables are **not** audited originals. Notes, auditor opinion, and restatements remain slice 02 PDF concerns.

## Aramco (`2222:TADAWUL`)

| Section | Frequency | Status |
|---|---|---|
| earnings | quarterly | supported (dataset; HTML tab may still show loading) |
| earnings | annual | not applicable (Google history is quarterly) |
| income statement | quarterly | supported (display-verified Google labels) |
| income statement | annual | supported (same labels applied to annual vectors) |
| balance sheet | quarterly | display-label unverified (tab advertised; table not embedded) |
| balance sheet | annual | display-label unverified |
| cash flow | quarterly | display-label unverified |
| cash flow | annual | display-label unverified |

Live opt-in (2026-09-09): earnings dataset populated while quote HTML still contained `Loading Previous Earnings...`. Income statement annual and quarterly both returned with original Google labels. Balance sheet and cash flow vectors retrieved from the Financials purpose; Google row names remain unverified. Alternate earnings body identical to primary → not extra coverage. Live Financials key was `ds:19` (purpose `Financials / estimates`). Currency `SAR` when present.

## Maaden (`1211:TADAWUL`)

Same section matrix. Live Financials purpose was also `ds:19` on 2026-09-09 (not a frozen ABI). A mapping **fixture** still demonstrates `ds:17` vs `ds:19` while the purpose stays Financials. Income statement parser is the same as Aramco (fixtures + optional live). PDF comparison is Maaden-only.

## Gap classes

| Gap class | Fixture | Live Aramco (opt-in) |
|---|---|---|
| actual missing, estimate present (forward quarter) | yes | present |
| estimate missing, actual present | yes | not observed on the live sample that day |
| display cell `-` / blank | yes (EPS dash) | present on some IS cells |
| earnings HTML still loading while dataset populated | yes | present |
| Financials `ds:N` differs across issuers | yes (`ds:19` vs `ds:17` fixture) | live keys matched (`ds:19`) |
| unverified metric-vector indices | yes (BS/CF unnamed) | present (no embedded BS/CF table) |
| comparative vector is prior-year comparative | yes | present (annual comparative period-end is the prior year) |
| Google vs PDF label mismatch | yes (`Net income` ≠ `Profit for the year`) | recorded in PDF cross-check |
| Google vs PDF value mismatch | yes (cash / shares definitions) | recorded in PDF cross-check |
| no notes / auditor / restatement from Google | yes | standing gap |
| AVGO enricher not used for Tadawul | yes (`labeled_data` absent) | present |

`Current earnings detail` was not advertised on the live Aramco/Maaden mappings and is not a product feed.
