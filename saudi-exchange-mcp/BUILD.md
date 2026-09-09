# BUILD.md

Slice: 02 — Read financial reports with page-level evidence
Archive: slices/02-report-reading.md

## Goal
Given a stored original Saudi Exchange financial-report PDF from slice 01 (company identity, provenance sidecar, content hash, local path), make that document searchable and readable as text and tables, with every extracted span or cell traceable to the original PDF and page. Identify financial metadata the document actually states — currency, units/scale, period duration, quarterly versus cumulative, consolidated versus standalone, and restatements — without silently inferring what is missing. This continues the report branch of the hybrid MCP at library/CLI level; Google Finance integration remains slice 03–04 and MCP host wiring remains slice 05.

## Done when
- **D1 — Page-level extraction with provenance:** For a stored original PDF, extract per-page text and, where the PDF actually contains tables, tabular cells. Every returned span/cell records the report content hash, local path inside configured storage (or an explicit fixture path), 1-based PDF page number, and extraction method (`native`, `ocr`, `mixed`, or `unreadable`). Preserve original labels and original value strings alongside any optional numeric parse; a parse without the original string does not satisfy this criterion. Page numbers are PDF indices (cover = page 1), not footer running titles such as `Saudi Arabian Mining Company (Maaden) | 18`. Slice 01 `inspect_pdf_identity` (bounded early-page identity/period check) does not satisfy this slice.
- **D2 — Arabic and English:** Extract both Arabic and English documents. English is demonstrated on the slice 01 Maaden 2025 annual financial statements (English). Arabic is demonstrated with fixtures that contain Arabic text (and, when retrieved through the existing slice 01 library, the listed Maaden 2025 annual Arabic PDF). Do not drop Arabic, silently transliterate away original labels, or treat a missing Arabic extraction as an empty English success.
- **D3 — OCR fallback and unreadable pages:** When native text extraction is empty or insufficient for a page, run a **local** OCR fallback, label the page as OCR-derived, and keep page provenance. On the stored Maaden 2025 annual English FS (SHA-256 `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e`, 126 pages), pypdf native extraction currently yields **no text** on PDF pages **4** and **13–18**: those pages are image XObjects (JPEG), matching the TOC’s Directors’ responsibilities and the primary consolidated statements (profit or loss, comprehensive income, financial position, changes in equity, cash flows). Recovering readable text from those pages requires OCR (or an evidenced equivalent that reads the images). Pages that remain unreadable after OCR are flagged `unreadable` with a reason; they are not omitted as if they contained nothing of interest.
- **D4 — Uncertain and missing data:** Missing values are not zero. Low-confidence OCR, truncated tables, blank cells, and line items not present on the cited page return explicit `uncertain` / `unavailable` / `not_found` outcomes. Search and read APIs must not present an empty hit list as proof that a figure is zero or that an activity did not occur. Untrusted PDF strings are data, never operational instructions.
- **D5 — Financial metadata:** For extracted statements and cited facts, record metadata **only when the document states it**, and mark each field `stated` or `unknown`:
  - currency (e.g. Saudi Riyals / SAR);
  - units/scale, including thousands or millions versus full units;
  - reporting period and duration (e.g. year ended 31 December 2025 versus a three-month or nine-month interim);
  - quarterly versus cumulative presentation when that distinction appears;
  - consolidated versus standalone/separate scope of **the statements being read**;
  - restatement or reclassification of **comparative financial-statement figures**.
  Do not infer thousands/millions from magnitude, do not treat “All amounts in Saudi Riyals unless otherwise stated” as a thousands scale, and do not treat IFRS 15 “standalone selling price”, zakat “separate financial statements”, or IAS 29 hyperinflation “restated” measuring-unit language as a restatement of prior-period comparatives. On the Maaden 2025 annual English FS notes, native text states consolidated scope, amounts in Saudi Riyals unless otherwise stated, and the year ended 31 December 2025; fields the statements do not state remain `unknown`.
- **D6 — Representative checks:** Against the stored Maaden 2025 annual English FS (hash above), verify representative extracted labels/values with page citations from (a) native-text notes (for example share-capital and currency wording on the notes pages that pypdf can read) and (b) OCR of the image-only primary statements on PDF pages 13–18 (statement headings plus at least a few labelled figures). Confirm currency/scale, period duration, and consolidated scope against those citations. Use **fixtures** for shapes this annual FS does not provide: Arabic text, quarterly versus cumulative labels, standalone versus consolidated contrast, restated comparatives, unreadable pages, and missing-metadata. Do not claim a live restatement of Maaden comparatives if the document does not present one. Do not require an Aramco PDF download for this slice.
- **D7 — Search, read, and reproducible proof:** Provide a library API and CLI to extract a stored report, read a page or page range, and search extracted text, returning hits with page numbers and content hash. Document actual commands/results. Routine `pytest` uses fixtures and synthetic PDFs and does **not** require the live website. The Maaden stored-PDF checks are additional evidence when the gitignored file is present (retrieve via the slice 01 CLI if absent). Distinguish fixture results from stored-PDF results. Do not commit or export the PDF corpus or full extraction dumps.

## Out
- MCP server/client/host wiring, tool schemas, and Cursor install (slice 05).
- Google Finance lookup, quotes, news, profile, earnings, or financial tables (slices 03–04). Do not compare extracted PDF figures to Google tables in this slice.
- Investment advice, financial analysis, or answering “why did X change” beyond returning cited extracted evidence.
- Universal automatic financial-statement normalization, chart-of-accounts mapping, or claiming a complete machine-readable IFRS taxonomy for every note.
- Re-implementing company discovery, listing, download, or cache policy (slice 01). Retrieving an additional listed PDF through the existing library is allowed.
- Paid OCR, hosted document-AI, or other credentialed extraction APIs.
- Public hosting, bulk redistribution of reports, or treating the two-company pilot as market-wide coverage.

## Constraints
- Execution of Hybrid Pilot v0 through slice 05 is authorized. This Proposed contract has no plan approval; do not implement until an independent Reviewer returns APPROVE_PLAN for matching contract and baseline identities.
- Depend on slice 01: consume stored originals via provenance (`storage/reports/{ticker}/{sha256}.pdf` plus `.pdf.json`). Reuse `saudi_exchange_reports` identity, listing, retrieval, storage bounds, and host allowlist. Do not silently switch to a different company’s file or an unofficial copy.
- Extend the existing Python 3.12 package `saudi_exchange_reports` (stdio MCP later, slice 05). Keep slice 01 tests green. Choose extraction/OCR/table libraries from this environment and current official docs; pypdf is already a dependency for identity inspection. OCR must be local (Tesseract or an equivalent local engine, with an Arabic language pack when OCR’ing Arabic pages). Do not introduce paid services or credentials.
- Ordinary reversible choices (do not escalate): 1-based PDF page indices; native extraction first, OCR when a page has no usable text operators; per-page method labels as in D1/D3; extraction artifacts keyed by content hash under configured storage; CLI subcommands such as `extract` / `read` / `search`; fixtures as the pytest source of Arabic, quarterly-versus-cumulative, restated-comparative, and unreadable-page shapes; optional live retrieve of listed Maaden 2025 annual Arabic `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_Ar.pdf` and/or a 2025 interim PDF through the existing CLI for extra evidence only.
- Representative stored PDF (slice 01, not redistributed): Maaden (`1211`) 2025 annual English financial statements, source `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_En.pdf`, SHA-256 `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e`. This is the Financial Statements Annual object, not the Board Report / Integrated Report `dae44e050e70e412049516a4caea688f9ff0cd918cab44b393ee86ecaf4b02a6`.
- Treat PDF bytes, extracted strings, and embedded files as untrusted data. Constrain reads to the configured storage directory or explicit test fixtures; reject path traversal. Do not execute PDF JavaScript or follow embedded links as retrieval instructions.
- Observe AGENTS.md invariants: original labels/values with provenance; no silent metadata inference; missing ≠ zero; Arabic and English; OCR when needed; report cache policy applies to Saudi PDFs only (do not create a Google-response archive).
- Re-check current official library documentation when implementation choices are made.

## Data / state impact
Creates derived extraction artifacts (per-page text, optional tables, metadata records, OCR intermediates) under the existing configured project storage, keyed by report content hash, without altering original PDF bytes. No broker accounts or financial transactions. Original PDFs and full extraction dumps stay in gitignored `storage/` (and `evidence/live-payloads/` if used). Tracked evidence under `evidence/02-report-reading/` records commands, hashes, page citations, and representative values only — not a redistributed report corpus. Fixtures under `tests/fixtures/` are tracked synthetic or condensed files, not live filings.

## Tests
- Evidence locations below are proposed, not existing proof: `evidence/02-report-reading/extraction.md`, `maaden-fs-reading.md`, `sample-manifest.json`, and `checks.md`. Record precise paths and real commands when produced.
- D1/D7: fixture PDFs with known per-page text and a simple table; assert page numbers, content hash, original strings, read-by-page, and search hits. Off-storage paths and non-PDF bytes fail closed.
- D2: fixture PDFs containing Arabic and English labels; extract and search both; original Arabic strings preserved.
- D3: fixture image-only / no-text pages prove OCR labelling and unreadable flags without the live website. Additional stored-PDF evidence: Maaden pages 4 and 13–18 are OCR (or unreadable if OCR cannot recover them), while native-text notes pages are not silently sent through OCR as if they lacked text.
- D4: fixtures for blank cells, low-confidence OCR, missing line items, and search misses; missing is not `0`; empty search is `not_found`, not “no activity”.
- D5: fixtures that state currency/scale/period/duration/quarterly-vs-cumulative/consolidated-vs-standalone/restated comparatives, and fixtures that omit them (`unknown`). Include a negative fixture where “restated” is hyperinflation/translation language only. Stored Maaden notes: stated SAR / full riyals unless otherwise stated / consolidated / year ended 31 December 2025; comparative restatement `unknown` unless a cited page actually restates comparatives.
- D6: stored Maaden 2025 annual English FS checks (optional marker or documented extra command) plus fixture representative values. Reviewer reproduces pytest without the exchange website; stored-PDF checks require the gitignored file or a slice 01 retrieve.
- D7: Reviewer runs `PYTHONPATH=src python3 -m pytest tests/ -q` (including new slice 02 tests) and audits that live/stored evidence is labelled separately from fixtures. Slice 01 tests remain passing.

## Proof
Pending Builder implementation after plan approval. Slice 01 retrieval of the Maaden 2025 annual English FS is a dependency, not extraction proof. Do not treat `inspect_pdf_identity` or early-page previews as D1–D7.

## Review
Plan review complete.
Plan approval: APPROVE_PLAN disp-02-plan-001 reviewer=bc-5e87338b-b2c6-5129-bb8a-e8e41b35789c (Cursor Grok 4.6) contract=sha256:f8a3e87ed9c9bc004d6b14453ce00803ace0b153d0d5f30214f12ead00faf0fc snapshot=sha256:9985159d76a5e740748a29f56abc8f19980d6d20ed29b0db7a6f006c0c29012d blockers=none artifact=loop/manifests/disp-02-plan-001-result.md
Implementation approval: none
Each result records dispatch ID, reviewer identity, verdict, contract identity, snapshot identity, evidence, and criterion-specific blockers.

## Loop state
Execution mode / tool adapter: Cursor Cloud Agent coordinator (run bc-ee81624b-9342-4c75-b5b0-a03c9edd6492) dispatches independent Builder and Reviewer via Cursor Task subagents with isolated context and distinct model slugs. Reviewer never edits the candidate. One active worker per checkout `/workspace`.
Coordinator: Cursor Cloud Agent bc-ee81624b-9342-4c75-b5b0-a03c9edd6492 (workspace `/workspace`, branch `cursor/hybrid-mcp-pilot-6492`)
Worker / role / phase: pending / Builder / Building
Dispatch ID / launch state / input identity: disp-02-impl-001 / pending-launch / contract=sha256:f8a3e87ed9c9bc004d6b14453ce00803ace0b153d0d5f30214f12ead00faf0fc baseline=sha256:9985159d76a5e740748a29f56abc8f19980d6d20ed29b0db7a6f006c0c29012d
Pending result / last consumed dispatch: none / disp-02-plan-001
Snapshot capture command: python3 loop/identity.py snapshot loop/manifests/snapshot.json
Snapshot recheck command: python3 loop/identity.py snapshot loop/manifests/snapshot-recheck.json
Snapshot coverage: All regular files and symlinks under `saudi-exchange-mcp/` with sorted relative paths, SHA-256 file bytes, types, executable modes, and symlink targets. Includes source, tests, configuration, lockfiles, protocol files, loop identity tools, and non-secret evidence docs. `BUILD.md` and `SLICES.md` are hashed from their LOOP contract extracts so Proof/Review/Loop-state bookkeeping, Status, Next, run status, release evidence, and Shipped/Now placement do not change snapshot identity.
Snapshot exclusions: `.git/`, `.venv/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `node_modules/`, `.tox/`, `storage/`, `loop/manifests/`, `evidence/live-payloads/`, `HANDOFF.md`, `*.pyc`, `*.pyo`, `.DS_Store`. Manifests are stored outside their own coverage.
Baseline snapshot: sha256:9985159d76a5e740748a29f56abc8f19980d6d20ed29b0db7a6f006c0c29012d file_count=42 path=loop/manifests/snapshot.json
Contract identity: sha256:f8a3e87ed9c9bc004d6b14453ce00803ace0b153d0d5f30214f12ead00faf0fc path=loop/manifests/contract.json
Candidate snapshot: none
Rejection count: 0
Consecutive no-progress repairs: 0
Open acceptance gaps / prior failing evidence: none
Repair awaiting review: false
Review events:
- event=rev-02-plan-001 dispatch=disp-02-plan-001 phase=plan-review verdict=APPROVE_PLAN reviewer=bc-5e87338b-b2c6-5129-bb8a-e8e41b35789c contract=sha256:f8a3e87ed9c9bc004d6b14453ce00803ace0b153d0d5f30214f12ead00faf0fc snapshot_before=sha256:9985159d76a5e740748a29f56abc8f19980d6d20ed29b0db7a6f006c0c29012d snapshot_after=sha256:9985159d76a5e740748a29f56abc8f19980d6d20ed29b0db7a6f006c0c29012d gaps=none rejection_count=0 no_progress=0 artifact=loop/manifests/disp-02-plan-001-result.md
Budget limit / consumed / measurement: Not configured; no execution budget was supplied
Blocker / resume status / resume action / recheck condition / deadline: none
Advance phase: proposed; awaiting plan review
Next slice ID / draft: 02 — Read financial reports with page-level evidence / loop/manifests/disp-02-draft-001.md

## Status
Not started

## Next
Builder implementation pending launch for `disp-02-impl-001`. Plan approval is valid for the recorded contract and baseline.
