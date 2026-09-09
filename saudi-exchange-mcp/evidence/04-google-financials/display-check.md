# D6A — Google display check (field presence; no live payloads)

Google Finance HTML and batchexecute bodies are **not** stored in git. This note records how labels were bound and that live/fixture display agreement was checked. Display abbreviations (B/M) are **not** the stored scale.

## Method

1. Select the Financials dataset by compiler purpose `Financials / estimates` (not a frozen `ds:19`).
2. Walk the nested shape: quarterly rows then annual rows; currency at metrics index 16; period-end date list at 17; second vector is the prior-year comparative.
3. Parse the embedded HTML table `aria-label="Income statement"` (`All values in SAR`, period headers such as `Jun 2026`).
4. Bind a Google original label to a metric index only when the display cell (rounded B/M/`%`/plain EPS) agrees with the dataset value for that period. Dataset values stay **full SAR**.
5. `10.64B` (and similar) is recorded as `display_text` plus `scale=full` on the original integer. It is not stored as scale=billions.
6. `-` / blank display cells are `unavailable`, not `0`.
7. Earnings tab: if HTML still says `Loading Previous Earnings...`, that is a display gap. Actual vs estimate labelling still comes from the earnings dataset; actual revenue/EPS are also checked against Income statement display overlap for the same period-end.

## Income statement labels bound from display

Verified against the displayed Income statement (fixture table and live Aramco quote HTML): **Revenue**, **Cost of goods sold**, **Cost of revenue**, **Operating expense**, **Operating income**, **Net income**, **Net profit margin**, **Earnings per share**, **EBITDA**, and other labels present in that table. Labels are Google originals; they are not renamed to IFRS/PDF names.

Live Aramco (opt-in, 2026-09-09): quarterly and annual income statements both returned. The latest quarterly Revenue cell used a `…B` display abbreviation; the parser stored the full-unit dataset value (`scale=full`) and kept the display string on `display_text`. No live integer is copied here.

## Earnings display

Live Aramco HTML still contained `Loading Previous Earnings...` while the earnings dataset returned quarterly rows with `SAR` and period-end dates. Missing actuals on unreported quarters stay `unavailable` (not `0`). Surprise/beat-miss is not named: the earnings table was not populated for display verification.

## Balance sheet and cash flow

Quote HTML advertised **Balance sheet** and **Cash flow** controls. Those tables were **not** embedded (no `Total assets` / `Free cash flow` row text). Product rows for those statements stay `unverified` / unnamed. Raw values may be used for PDF numeric cross-check with **PDF** labels on the PDF side only.

## AVGO enricher

`google_finance_mcp.financials.enrich_financials_result` does not attach `labeled_data` for `2222:TADAWUL` or `1211:TADAWUL`. Slice 04 product labels come from `saudi_exchange_reports.google_finance.parse`, not from AVGO positional names.

## AI disclaimer

The Google Finance UI included “AI content may include mistakes”. Google tables can differ from filings.
