# BUILD.md

Slice: 04 — Google Finance earnings and financial statements
Proposed by: Builder dispatch disp-04-draft-001 (not independently accepted; not live BUILD until coordinator replacement)

## Goal
Given a pilot company's Arabic/English name and/or ticker, resolve the **existing** shared company identity (slices 01 and 03) and, through the already revision-pinned reuse of [woodstock-tokyo/google-finance-mcp](https://github.com/woodstock-tokyo/google-finance-mcp) (`319760998e60d4b060fb993b3dc8db94364b019c`), retrieve Google Finance **earnings** (actual versus estimate) and the three **financial statements** — income statement, balance sheet, and cash flow — for that same company. Preserve original Google labels and values, annual and quarterly periods where the source supplies them, units and currency, and explicit coverage/gaps. Prove representative figures against the Google Finance **display** and against the stored Maaden 2025 annual English financial-statement PDF using slice 02 reading APIs. Keep Google responses transient. Do **not** treat Google tables as audited originals. This remains the Google research branch at library/CLI level; MCP host/client install remains slice 05.

## Done when
- **D1 — Earnings, actual versus estimate:** Using the reused Google Finance client (purpose `Earnings history and estimates`, with the advertised alternate only as a fallback when the primary body is empty — not as a second product feed), return a quarterly earnings history for **Aramco** (`2222:TADAWUL`) that includes, **per period, when the payload actually contains them**:
  - reporting period (year and quarter) and period-end date;
  - currency;
  - **revenue actual** and **revenue estimate**, each labelled actual or estimate;
  - **EPS actual** and **EPS estimate**, each labelled actual or estimate;
  - surprise / beat-miss metadata **only when present**;
  - shared identity and Google quote page URL;
  - timezone-aware retrieval time.
  Missing actuals, estimates, publishers of consensus, or surprise fields are `unavailable` — **not** `0` and not proof that the company had no earnings. Future or unreported periods that carry estimates but no actuals must keep actuals `unavailable`. Do not invent an article-style earnings summary. Website presence of an Earnings control, or HTML that still says `Loading Previous Earnings...`, does not satisfy this criterion. Draft-time (2026-09-09) live `Kcy68c` bodies for Aramco and Maaden were non-empty lists of quarterly rows with `SAR` and period-end dates; `ds:9` and `ds:10` were **identical** for Aramco — de-duplicate; do not count the alternate as extra coverage. Upstream `enrich_financials_result` does not label this dataset. Product code in `saudi_exchange_reports.google_finance` must parse it; do not require `labeled_data` from the AVGO financials enricher.

- **D2 — Income statement, original labels/values, annual and quarterly:** Retrieve the Google Finance **Income statement** for Aramco (live) and Maaden (live or the same parser plus fixtures). Return both **quarterly** and **annual** views from the `Financials / estimates` purpose (compiler name; **not** a frozen `ds:19` — draft-time Aramco advertised that purpose at `ds:19` / `Pr8h2e`, Maaden at **`ds:17` / `Pr8h2e`**). For each period include: Google original row **labels**, original values, currency, period end, and duration (`quarterly` versus `annual`). Draft-time Google **display** (quote HTML, quarterly, `All values in SAR`) showed Income statement labels including **Revenue**, **Cost of goods sold**, **Operating expense**, **Operating income**, **Net income**, **Net profit margin**, **Earnings per share**, **EBITDA**, and others, with `-` for missing cells (Maaden EPS blank on some quarters). Preserve those Google labels; do not rename them to IFRS/PDF names. Dataset values are **full SAR amounts** (draft-time Maaden annual 2025 Revenue integer `38577730228`); the page’s `418.16B` / `10.64B` style is a **display abbreviation**, not the stored scale. Record both: original numeric value from the dataset (or original display string if that is the extracted source) and an explicit scale/currency field. Empty or unlabelled positional dumps are not a successful income statement.

- **D3 — Balance sheet:** From the same Financials dataset, return **annual and quarterly** balance-sheet rows for the pilot companies, with currency, period end (statement of financial position is a **point in time**), and original Google labels **once those labels are verified against a displayed Balance sheet table**. Draft-time quote HTML advertised a **Balance sheet** control but did **not** embed Balance sheet row text (only the Income statement table was populated). Implementation must not fill that gap by copying AVGO positional names. Until a Google display label is verified for a slot, keep the slot `unverified` / `unavailable` as a labelled product row — still allowed to carry a raw value for PDF numeric cross-check with **PDF** labels on the PDF side. Live evidence must either bind display-verified Google BS labels to dataset slots or record an explicit display-label gap. Missing history is a gap, not empty proof of no assets.

- **D4 — Cash flow:** Same rules as D3 for the **Cash flow** statement (operating / investing / financing, and free cash flow **only if** display-verified or explicitly gapped). Draft-time HTML advertised the Cash flow tab without embedding those row labels. Duration is a **period** (quarter or year), not a point in time. Do not treat a missing cash-flow section as proof of no cash activity.

- **D5 — Explicit coverage and gaps:** Produce a dated coverage record (library/CLI plus `evidence/04-google-financials/coverage.md`) for Aramco and Maaden stating, per section (earnings, income statement, balance sheet, cash flow) and per frequency (annual/quarterly): supported, empty/unavailable, display-label unverified, or not applicable. Required gap classes (fixture and/or live):
  - actual missing, estimate present (forward quarter);
  - estimate missing, actual present;
  - display cell `-` / blank;
  - earnings HTML still loading while the dataset is populated (do not treat the loading string as “no earnings”);
  - Financials `ds:N` differing across pilot pages (Aramco `ds:19` vs Maaden `ds:17` at draft-time);
  - unverified metric-vector indices (draft-time vectors were length **106**; only independently verified slots may be named);
  - second metric vector on each Financials row is the **prior-year comparative** for the same frequency (draft-time annual 2025 comparative period-end `[2024, 12, 31]`), **not** a different statement type and not a second company;
  - Google versus PDF **label** mismatch and **value** mismatch (see D6);
  - no notes, auditor opinion, or restatement metadata from Google — those remain slice 02 PDF concerns;
  - `google_finance_mcp.financials.enrich_financials_result` attaches `labeled_data` **only** for the AVGO:NASDAQ signature and **did not** attach it for `2222:TADAWUL` or `1211:TADAWUL` (draft-time `labeled=False`). That enricher is **not** slice 04 product labelling for Saudi companies.
  Update slice 03 inventory product status for earnings and financials from **defer** to **support** (or explicit gap) so a green inventory no longer claims they are out of this slice.

- **D6 — Representative comparison: Google display AND official PDF (Maaden 2025 FS):** Dual provenance; never merge into one “true” number.

  **A — Google display (required for Aramco live; Maaden live or the same IS parser):** For at least several Income statement cells, show that the MCP-extracted original label + numeric value (after documenting scale) agrees with the visible Google table for the **same** company, statement, frequency, and period. Draft-time examples of the *method* (not pytest goldens, not payloads to commit): Aramco quarterly Jun 2026 display Revenue `521.80B` ↔ dataset `521797000000` SAR; Maaden quarterly Dec 2025 display Revenue `10.64B` ↔ dataset `10639726486` SAR. Earnings actual-versus-estimate columns must be checked against the Earnings display when that table is populated; if the tab still shows `Loading Previous Earnings...`, record that display gap and still prove actual/estimate **labelling** from the dataset plus IS display overlap for actual revenue/EPS where those figures also appear on the Income statement.

  **B — Official PDF (Maaden only; stored original, not Google):** Using slice 02 `extract_report` / `search_extracted` / `find_line_item` / `read_pages` on the gitignored Maaden 2025 annual English FS — SHA-256 `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e`, source `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_En.pdf`, PDF pages **13** (profit or loss), **15** (financial position), **17–18** (cash flows), **19** (notes) — compare representative lines. Reconcile **currency** (both SAR / Saudi Riyals), **scale** (PDF full riyals as stated; Google dataset full riyals; Google UI B/M is display-only), **period** (year ended / as at 31 December 2025 versus a Google **quarter**), **consolidated** scope, and **original labels on each source**. Outcome per pair is `match` | `mismatch` | `unavailable`, with a reason. **Do not** compare a Google quarterly cell to an annual PDF line without labelling the duration mismatch as failed/not-comparable.

  Required PDF comparison pairs (PDF originals from slice 02 stored-PDF evidence; Google side is live-or-parser output at implementation, not a committed payload):

  | PDF original label (page) | PDF original value | What the comparison must show |
  |---|---|---|
  | `Revenue` (p.13) | `38,577,730,228` | Google **annual** 2025 Income statement Revenue, full SAR, same period-end. Draft-time Financials annual primary slot matched this integer. |
  | `Profit for the year` (p.13) | `8,527,980,356` | Must **not** be silently treated as Google `Net income`. Draft-time Google annual `Net income` equalled PDF `Ordinary shareholders of the parent company` `7,347,878,280`, not this total (NCI is in the PDF total). Record **mismatch** of Google Net income vs Profit for the year, and **match** vs attributable-to-parent if that PDF line is cited. Keep both labels. |
  | `Basic and diluted earnings per share` (p.13) | `1.91` | Google annual EPS vs this PDF EPS line (same attribution). Draft-time slot matched `1.91`. |
  | `Total assets` (p.15) | `119,757,152,175` | Google annual/point-in-time total assets. Draft-time slot matched. |
  | `Total equity` (p.15) | `67,814,366,490` | Google total equity. Draft-time slot matched. |
  | `Total liabilities` (p.15) | `51,942,785,685` | Google total liabilities. Draft-time slot matched. |
  | `Net cash generated from operating activities` (p.17) | `10,927,067,206` | Google cash-from-operations. Draft-time slot matched. |
  | `Net cash utilized in investing activities` (p.18) | `(10,120,345,838)` | Google cash-from-investing, sign preserved. Draft-time slot matched the PDF negative. |
  | `Net cash utilized in financing activities` (p.18) | `(5,438,421,256)` | Google cash-from-financing. Draft-time slot matched. |
  | `Cash and cash equivalents` (p.15) | `10,583,548,481` | Must **not** be auto-identified with Google’s cash-like slot if the integer differs. Draft-time Google cash-like value `10823020198` **≠** this PDF line. Record **mismatch** / different definition. |
  | Notes share count (p.19) | `3,888,763,418` shares | Google shares-outstanding-like slot draft-time `3880896664` **≠** issued share capital count. Record **mismatch**. |

  Google tables are **not** the audited original. PDF page citations apply only to PDF-derived facts. Do not require an Aramco PDF. If the gitignored Maaden PDF is absent, retrieve it with the slice 01 CLI then extract; do not substitute a Google table for the filing.

- **D7 — Synthetic fixtures, opt-in live checks, reproducible proof:** Library API + CLI to: resolve identity, return earnings (actual vs estimate), return income statement / balance sheet / cash flow (annual and quarterly), emit coverage/gaps, and emit a dual-provenance Maaden comparison when the stored PDF is present. Routine `pytest` uses **hand-written** earnings and financials fixtures (invented numbers, not live dumps) and existing synthetic Google HTML. Opt-in live checks (`live_google` / `SAUDI_LIVE_GOOGLE=1`, same pattern as slice 03) exercise Aramco earnings + financials through the reused client; Maaden live financials may be additional. Live bodies stay in gitignored `evidence/live-payloads/` or are discarded. Tracked evidence under `evidence/04-google-financials/` records commands, coverage, display-check notes, PDF page citations, and match/mismatch **without** live Google JSON/HTML. Slice 01–03 tests remain passing. Snapshot commands remain compatible with `loop/identity.py`. Distinguish fixture, live Google, and stored-PDF evidence.

## Out
- MCP server/client/host wiring, Cursor MCP install, tool schemas for a host assistant (slice 05). Reuse of `GoogleFinanceClient` is allowed; demonstrating an installed MCP host is not.
- Treating Google Finance tables, estimates, or “AI content may include mistakes” UI as audited Saudi Exchange filings, auditor opinions, or notes.
- Silently merging Google and PDF figures, renaming Google `Net income` to PDF `Profit for the year`, or comparing quarterly Google cells to annual PDF totals without an explicit not-comparable/mismatch outcome.
- Using `google_finance_mcp.financials` AVGO `labeled_data` / `AVGO_DS16_SIGNATURE` as proof that Tadawul slots are labelled. Guessing the remaining ~106-vector indices.
- Persistent Google payload archives, applying the Saudi PDF cache policy to Google financials, or committing live Google responses, screenshots of Google UI, or copied Google assets.
- Re-implementing PDF discovery/download (slice 01) or extraction/OCR (slice 02) except **consuming** `resolve_company`, catalog identity, and reading APIs.
- New company identities; `2222:SAU` / `1211:SAU`; swapping Aramco↔Maaden via related securities.
- Exposing Holdings, analyst targets, charts, generated `ds:N` tools, or explicit `call_rpc` hashes as product capabilities. `Current earnings detail` (`wKsYyb`) only if the live page advertises it; draft-time Aramco/Maaden mappings did not.
- Hosted/multi-user service, scheduled polling, streaming, trading, investment advice, exhaustive history claims, or paid data APIs.
- Changing the vendored upstream revision silently. If `LICENSE` / `LEGAL.md` at the pin differ when re-read, stop and return a contract proposal.

## Constraints
- Execution of Hybrid Pilot v0 through slice 05 is authorized. This Proposed contract has no plan approval; do not implement until an independent Reviewer returns APPROVE_PLAN for matching contract and baseline identities.
- Depend on slice 03 Google integration (`saudi_exchange_reports.google_finance`, `GoogleFinanceClient`, purpose-based `call_purpose`, verified `2222:TADAWUL` / `1211:TADAWUL`) and slice 01 identity. Depend on slice 02 reading APIs for D6 PDF evidence (`extract_report`, `read_pages`, `search_extracted`, `find_line_item`) and the stored Maaden FS identity above. Do not fork a second company table.
- Keep Google Finance logic in `saudi_exchange_reports.google_finance` (and vendored `google_finance_mcp`) **separate** from Saudi listing/PDF/OCR modules. Comparison **composes** both with separate provenance; a Google failure must not disable PDF reading, and vice versa. Partial results stay source-labelled.
- Runtime: existing Python 3.12 layout, `httpx`, `anyio`, pinned client. Do not add host MCP configuration. Do not require `mcp` for routine pytest. Do not introduce paid services. Re-read `vendor/google-finance-mcp/LICENSE` and `LEGAL.md` at implementation against the pin and hashes in `evidence/03-google-overview/notices.md`.
- Ordinary reversible choices (do not escalate): CLI subcommands under `python -m saudi_exchange_reports` such as `google-earnings`, `google-financials` (statement type + `annual`/`quarterly`), and `google-crosscheck` (or equivalent) for D6; extend `ScriptedSource` with earnings/financials responses and `_PURPOSE_GROUP` fallbacks for earnings alternate; hide `ds:N` / RPC ids from public JSON; `hl=en`; select Financials and Earnings by **compiler purpose** with one retry on empty/no-frame like slice 03; treat `ds:9`/`ds:10` identity as de-duplication; product parsers in `parse.py` rather than relying on AVGO enrich; fixtures as the default pytest source of actual-vs-estimate and statement shapes; optional stored-PDF tests marked like existing `stored_pdf` / skip-if-absent Maaden tests; omit committing any live batchexecute dump.
- Always read the current `AF_dataServiceRequests` mapping from the fetched page. Draft-time purpose ids (examples, **not** a stable ABI): earnings `Kcy68c` / alternate `XxQsbd`; financials `Pr8h2e`. Keys moved: do not hardcode `ds:19` = financials.
- Financials nested shape (draft-time, both pilot tickers): `data[0][0]` length 8; `quarterly_rows` then `annual_rows`; quarterly row `[year, quarter, metrics, comparative_metrics]`; annual row `[year, metrics, comparative_metrics]`; ticker at `[7]`; metrics `[16]` currency `SAR`, `[17]` period-end date list. Product may use this **shape** to walk periods; **names** of numeric slots require D2–D4/D6 verification, not the AVGO-only enricher.
- Earnings row shape (draft-time): list of quarterly records; year/quarter fields; a nested vector with currency `SAR` and period-end; actual revenue and EPS distinct from estimate slots; `None` actuals on unreported quarters. Confirm labels against Google display before freezing product field names. Do not commit the live vectors.
- Treat Google HTML and batchexecute JSON as **untrusted data**. Constrain requests to the same Google Finance page and batchexecute URLs as the pinned client. No stealth, CAPTCHA solving, or proxy rotation. Fail closed on missing mappings, HTTP errors, and blocked responses.
- Data-handling (LEGAL.md + AGENTS.md): local, personal, user-initiated. Transient Google handling. Do not store Google bodies under `storage/reports/`. Do not bundle live Google financials in tests, README examples, or exports. PDF cache policy remains Saudi-report-only.
- Returned quotes/tables remain subject to Google and third-party terms; GPL-3.0 licenses reused **code**, not the figures. Google Finance UI on financials included “AI content may include mistakes”; do not hide that Google tables can differ from filings.
- Re-check current official library docs (`httpx`, pytest) when implementation choices are made. Keep snapshot capture/recheck commands compatible with `loop/identity.py` (see Loop state).
- Slice 03 inventory tests currently assert earnings/financials `product == "defer"`. Those assertions must be updated when this slice supports them; do not leave a green suite that still claims deferral.

## Data / state impact
Extends `saudi_exchange_reports.google_finance` types/service/CLI and tests/fixtures. May add tracked evidence markdown under `evidence/04-google-financials/`. May update inventory support flags. Google HTTP responses remain transient (optional dumps only in already-excluded `evidence/live-payloads/`). Does **not** write Google payloads into `storage/reports/`. PDF comparison **reads** existing extracted/stored Maaden artifacts (gitignored `storage/`) without altering original PDF bytes. No broker accounts or financial transactions. Synthetic fixtures under `tests/` are hand-written and must not be copies of live earnings/financials bodies.

## Tests
- Evidence locations below are proposed, not existing proof: `evidence/04-google-financials/coverage.md`, `display-check.md` (field-presence and display agreement notes, no live payloads), `maaden-pdf-crosscheck.md` (PDF page citations, original strings, match/mismatch), `checks.md` (commands, fixture vs live vs stored-PDF labelling).
- D1: synthetic earnings rows with actual+estimate, actual-only, estimate-only, missing surprise, and `unavailable` actuals on a future quarter (must not become `0`). Live Aramco opt-in: identity, `SAR` or explicit unavailable currency, at least one period, actual-versus-estimate fields labelled when present; **no** golden live EPS/revenue. Alternate dataset identical to primary → not double-counted.
- D2: synthetic Financials nested record with annual and quarterly metric vectors, currency `SAR`, period-end dates, original-label rows including Revenue / Net income; missing cell → `unavailable`. Display-abbreviation fixture (`10.64B`) must not be stored as scale=billions without recording full-unit original. Live Aramco opt-in: income statement annual **and** quarterly both returned or the missing frequency explicitly gapped; original labels present for IS.
- D3/D4: fixtures for BS and CF periods; unverified indices stay unnamed; empty statement section → explicit gap. Live: BS and CF data retrieved from Financials purpose; labels display-verified or gapped in coverage.md.
- D5: inventory no longer `defer` for earnings/financials; coverage function/CLI lists the gap classes; comparative vector period-end ≠ primary period-end; Maaden vs Aramco dataset **keys** may differ in a mapping fixture (`ds:17` vs `ds:19`) while purpose stays Financials.
- D6: fixture comparison: same-scale annual match; quarterly-vs-annual not-comparable; Google Net income vs PDF Profit for the year mismatch fixture using the published PDF originals above (as **fixture strings**, not live Google). Stored-PDF opt-in (skip if PDF absent): reproduce the required pairs via slice 02 APIs + Google parser; record outcomes. Do not assert a live Google integer in default pytest.
- D7: Reviewer runs `PYTHONPATH=src python3 -m pytest tests/ -q` (or project venv) **without** network to Google; live tests marked `live_google` and skipped by default; stored-PDF tests skip if the gitignored file is missing. Slice 01–03 tests pass. Audit that git does not contain live Google bodies. Snapshot commands remain `python3 loop/identity.py snapshot …` as below.

## Proof
Placeholder — pending implementation. This document is a Proposed contract only. Draft-time inspection (2026-09-09) of live mappings/datasets and of stored Maaden PDF extraction is recorded in Done when / Constraints to specify field-meaning and gap classes; it is **not** slice 04 acceptance evidence and must not be copied into git as Google payloads.

## Review
Placeholder — pending independent plan review. No APPROVE_PLAN. Builder cannot approve this proposal.

## Loop state
Execution mode / tool adapter: Cursor Cloud Agent coordinator (run bc-ee81624b-9342-4c75-b5b0-a03c9edd6492) dispatches independent Builder and Reviewer via Cursor Task subagents with isolated context and distinct model slugs. Reviewer never edits the candidate. One active worker per checkout `/workspace`.
Coordinator: Cursor Cloud Agent bc-ee81624b-9342-4c75-b5b0-a03c9edd6492 (workspace `/workspace`, branch `cursor/hybrid-mcp-pilot-6492`)
Worker / role / phase: pending / Reviewer / plan-review
Dispatch ID / launch state / input identity: disp-04-plan-001 / pending-launch / contract=sha256:97f9abe0ef503d05119497d8d10ffc182a183fbe56d690a5681a199232feda91 snapshot=sha256:77fb005da3f5dd1cbe357e717c289f335c97da7b6a52737747bbceed243e1218
Pending result / last consumed dispatch: none / disp-04-draft-001
Snapshot capture command: python3 loop/identity.py snapshot loop/manifests/snapshot.json
Snapshot recheck command: python3 loop/identity.py snapshot loop/manifests/snapshot-recheck.json
Snapshot coverage: All regular files and symlinks under `saudi-exchange-mcp/` with sorted relative paths, SHA-256 file bytes, types, executable modes, and symlink targets. Includes source, tests, configuration, lockfiles, protocol files, loop identity tools, and non-secret evidence docs. `BUILD.md` and `SLICES.md` are hashed from their LOOP contract extracts so Proof/Review/Loop-state bookkeeping, Status, Next, run status, release evidence, and Shipped/Now placement do not change snapshot identity.
Snapshot exclusions: `.git/`, `.venv/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `node_modules/`, `.tox/`, `storage/`, `loop/manifests/`, `evidence/live-payloads/`, `HANDOFF.md`, `*.pyc`, `*.pyo`, `.DS_Store`. Manifests are stored outside their own coverage.
Baseline snapshot: sha256:77fb005da3f5dd1cbe357e717c289f335c97da7b6a52737747bbceed243e1218 file_count=89 path=loop/manifests/snapshot.json
Contract identity: sha256:97f9abe0ef503d05119497d8d10ffc182a183fbe56d690a5681a199232feda91 path=loop/manifests/contract.json
Candidate snapshot: none
Rejection count: 0
Consecutive no-progress repairs: 0
Open acceptance gaps / prior failing evidence: none
Repair awaiting review: false
Review events: none
Budget limit / consumed / measurement: Not configured; no execution budget was supplied
Blocker / resume status / resume action / recheck condition / deadline: none
Advance phase: none
Next slice ID / draft: none

## Status
Proposed

## Next
Independent plan review of this Proposed contract. No application-code implementation until APPROVE_PLAN for matching contract and baseline identities.
