# BUILD.md

Slice: 01 — Company report discovery and original-PDF retrieval
Archive: slices/01-report-retrieval.md

## Goal
Given a pilot company's Arabic/English name and/or ticker and a requested period, resolve a shared company identity, identify its Saudi Exchange page, select the appropriate financial statement/report, and save the original PDF with enough provenance to retrieve, inspect, and reuse it reliably. This establishes the report branch of the hybrid MCP; Google Finance overview/news follows in slice 03 and earnings/financial tables in slice 04.

## Done when
- **D1 — Access evidence:** record a reproducible route from the supplied Main Market page to company reports, with dated source URLs and the observed access/download mechanism. Document applicable access conditions and actual limitations. Do not label an undocumented endpoint an official API. At least one real financial-report PDF must be successfully retrieved; an inspection-only report does not satisfy this slice.
- **D2 — Company identity:** resolve Arabic name, English name, or ticker within a documented pilot sample to a shared record containing company identity, exchange/ticker, aliases, and verified Saudi Exchange page/source identifiers. Keep provider-specific identifiers distinct so slice 03 can attach a verified Google Finance mapping without creating a second company identity. Confirm that the source page and saved report belong to the resolved company. Return an explicit ambiguous/not-found/mismatch outcome when applicable; do not silently select a company when name and ticker conflict or assume identical symbols imply the same exchange.
- **D3 — Report selection:** list available financial statements/reports with observed title, period, report type, language, publication date when present, and source/download URLs. Select by the requested period and available type/language; separate annual, interim, and other report types. Mark unavailable metadata and absent reports explicitly.
- **D4 — Original PDF:** download the original bytes to configured local storage, confirm that the response is a readable PDF rather than an HTML/error page, and record company/ticker, report metadata, source/final URL, retrieval time, content hash, and local path. Inspect a source PDF page to confirm identity/period; full automated content extraction belongs to 02.
- **D5 — Cache/version behavior:** repeated requests reuse a valid saved copy. Detect changed source content or metadata using an evidenced freshness/version strategy, preserve provenance of prior downloaded content, and distinguish cached retrieval from a fresh source check. Reject corrupted/incomplete cache entries. Do not treat a cached listing as proof that no newer report exists.
- **D6 — Bounded failures:** handle unavailable reports, blocked/failed access, invalid PDFs, and interrupted downloads without creating apparently valid records. Constrain destinations and accepted source redirects, apply reasonable request pacing/retries, and keep untrusted site content from controlling local operations.
- **D7 — Reproducible proof:** document the actual pilot sample and retrieval commands/results. Use live retrieval evidence plus repeatable fixtures for identity, period selection, cache/version, and failure behavior. Separate verified results from untested coverage; retain only source material appropriate for the local workflow, not a redistributed report corpus.

## Out
- Financial analysis, table normalization, OCR implementation, or answering financial questions from PDF contents.
- MCP server/client integration, public hosting, paid data-service integration, or bulk market/history scraping.
- Forking/installing Google Finance MCP, live quote retrieval, and validating Google identifiers belong to slice 03. Google earnings and financial-table integration belong to 04; final hybrid routing and host integration belong to 05.
- Claiming availability or reliability across all listed companies based on the pilot.

## Constraints
- Execution of Hybrid Pilot v0 through slice 05 is authorized. This Proposed contract still has no plan approval; do not implement until an independent Reviewer returns APPROVE_PLAN for matching contract and baseline identities.
- Use Saudi Exchange as the discovery authority. A report hosted elsewhere is acceptable only when reached through a verified company report link with preserved provenance; do not silently switch to general-web substitutes.
- Prefer a suitable documented API if verified; otherwise assess direct public retrieval and browser-driven report selection as alternatives. Choose based on evidence and permitted access, not assumed endpoints.
- Select the smallest representative pilot sample that can demonstrate the intended inputs and report distinctions, document it, and let independent plan review assess adequacy. Include Saudi Aramco (2222) plus at least one additional Main Market company so Arabic/English/ticker, annual/interim, and language distinctions can be evidenced. The discussion specifies no larger required sample count.
- Runtime for this slice: Python 3.12 with stdio later (slice 05). Choose HTTP and storage libraries from existing-environment evidence; do not introduce paid OCR/model services or credentials as an implicit dependency.
- Re-check current official library documentation when implementation choices are made.
- Observe the shared financial-data and untrusted-source invariants in AGENTS.md.
- Report storage/cache requirements apply to Saudi Exchange reports only. The later Google Finance branch has separate transient-data handling and upstream reuse requirements; this slice must not introduce a shared market-response archive.

## Data / state impact
Creates local company/report metadata, downloaded PDFs, provenance/version records, and a cache in explicitly configured project storage. No broker accounts or financial transactions. Choose exact paths after repository inspection; generated documents, private state, and fixtures must have deliberate retention and version-control treatment. This prepared pack currently contains no downloaded reports, cache, application code, or credentials.

## Tests
- Evidence locations below are proposed, not existing proof: `evidence/01-report-retrieval/access.md`, `sample-manifest.json`, `live-retrieval.md`, and `checks.md`. Record precise paths and real commands when produced.
- D1/D3/D4: live source-to-PDF demonstration; inspect PDF identity/period and compare saved provenance with source. Preserve dated observations and download validation outcome.
- D2/D3: representative Arabic/English/ticker cases plus ambiguous, conflicting, unknown, wrong-exchange, and unavailable-period cases, with expected outcomes independent of implementation. Verify shared identity and separate source identifiers without claiming the Google mapping has already been tested.
- D5: prove reuse and invalid-cache recovery; use controlled source changes to prove new content/version handling without claiming an observed real-world restatement if none was seen.
- D6: exercise HTML-as-PDF, failed/partial download, blocked access, unsafe destination/source redirect, and bounded retry behavior with safe fixtures.
- D7: Reviewer reproduces relevant checks, audits sample coverage, and distinguishes live evidence from deterministic simulations. Do not require a live website in every routine test run.

## Proof
Proposed by Builder repair disp-01-impl-002 (not independently accepted). Slice 01 library `saudi_exchange_reports` resolves the documented two-company Main Market pilot (Saudi Aramco `2222`, Maaden `1211`) and lists Financial Statements/Reports from untrusted HTML (annual / interim / other, en/ar, publication date when present). When urllib website AJAX `statementsTabData` returns HTTP 500, listing falls back to browser-driven public tab HTML on `www.saudiexchange.sa` (Playwright + Chrome clicking `#finacialStatementAndReports`; not an official API). Live Maaden listing returned 44 `/Resources/fsPdf/` rows (22 en + 22 ar). CLI `retrieve --ticker 1211 --period 2025 --type annual --language en` selected `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_En.pdf` from that table and stored original bytes: 8,681,557, `%PDF-1.7`, SHA-256 `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e`, 126 pages, identity/period confirmed. Routine proof: `PYTHONPATH=src python3 -m pytest tests/ -q` (57 passed, coordinator recheck 2026-09-09). Live listing dump: `evidence/01-report-retrieval/live-listing.json`. urllib AJAX still 500; `--no-browser` listing remains unavailable.

## Review
Plan review complete.
Plan approval: APPROVE_PLAN disp-01-plan-001 reviewer=bc-cb10cee8-f0bc-56df-ba45-4799c6c98d0b (Cursor Grok 4.6) contract=sha256:122bc93b0de9d398055a464ad8bfdc933849c80890e0d8285db244d57e23fe91 snapshot=sha256:9f10bc6eeaacaae72f6f57994a8abd9ee29f577e1abf45a8561159d46743e2a6 blockers=none artifact=loop/manifests/disp-01-plan-001-result.md
Implementation approval: APPROVE_IMPLEMENTATION disp-01-impl-review-002 reviewer=bc-96fe6aac-6713-5d45-94a2-8b89225d20d4 (Cursor Grok 4.6) contract=sha256:122bc93b0de9d398055a464ad8bfdc933849c80890e0d8285db244d57e23fe91 candidate=sha256:e68c89956ab1f6f6e3dfb7039faea45e1e3fee82ed91aa3d4d028c6b158358fe material_improvement=yes blockers=none artifact=loop/manifests/disp-01-impl-review-002-result.md
Each result records dispatch ID, reviewer identity, verdict, contract identity, snapshot identity, evidence, and criterion-specific blockers.

## Loop state
Execution mode / tool adapter: Cursor Cloud Agent coordinator (run bc-ee81624b-9342-4c75-b5b0-a03c9edd6492) dispatches independent Builder and Reviewer via Cursor Task subagents with isolated context and distinct model slugs. Reviewer never edits the candidate. One active worker per checkout `/workspace`.
Coordinator: Cursor Cloud Agent bc-ee81624b-9342-4c75-b5b0-a03c9edd6492 (workspace `/workspace`, branch `cursor/hybrid-mcp-pilot-6492`)
Worker / role / phase: none
Dispatch ID / launch state / input identity: none
Pending result / last consumed dispatch: none / disp-01-impl-review-002
Snapshot capture command: python3 loop/identity.py snapshot loop/manifests/snapshot.json
Snapshot recheck command: python3 loop/identity.py snapshot loop/manifests/snapshot-recheck.json
Snapshot coverage: All regular files and symlinks under `saudi-exchange-mcp/` with sorted relative paths, SHA-256 file bytes, types, executable modes, and symlink targets. Includes source, tests, configuration, lockfiles, protocol files, loop identity tools, and non-secret evidence docs. `BUILD.md` and `SLICES.md` are hashed from their LOOP contract extracts so Proof/Review/Loop-state bookkeeping, Status, Next, run status, release evidence, and Shipped/Now placement do not change snapshot identity.
Snapshot exclusions: `.git/`, `.venv/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `node_modules/`, `.tox/`, `storage/`, `loop/manifests/`, `evidence/live-payloads/`, `HANDOFF.md`, `*.pyc`, `*.pyo`, `.DS_Store`. Manifests are stored outside their own coverage.
Baseline snapshot: sha256:9f10bc6eeaacaae72f6f57994a8abd9ee29f577e1abf45a8561159d46743e2a6 file_count=10 path=loop/manifests/snapshot.json
Contract identity: sha256:122bc93b0de9d398055a464ad8bfdc933849c80890e0d8285db244d57e23fe91 path=loop/manifests/contract.json
Candidate snapshot: sha256:e68c89956ab1f6f6e3dfb7039faea45e1e3fee82ed91aa3d4d028c6b158358fe file_count=41 path=loop/manifests/candidate.json builder=bc-14cdd35f-e37a-5d39-8369-42cd289d624b
Rejection count: 1
Consecutive no-progress repairs: 0
Open acceptance gaps / prior failing evidence: none (D3 closed by repair; frozen on approval)
Repair awaiting review: false
Review events:
- event=rev-01-plan-001 dispatch=disp-01-plan-001 phase=plan-review verdict=APPROVE_PLAN reviewer=bc-cb10cee8-f0bc-56df-ba45-4799c6c98d0b contract=sha256:122bc93b0de9d398055a464ad8bfdc933849c80890e0d8285db244d57e23fe91 snapshot_before=sha256:9f10bc6eeaacaae72f6f57994a8abd9ee29f577e1abf45a8561159d46743e2a6 snapshot_after=sha256:9f10bc6eeaacaae72f6f57994a8abd9ee29f577e1abf45a8561159d46743e2a6 gaps=none rejection_count=0 no_progress=0 artifact=loop/manifests/disp-01-plan-001-result.md
- event=rev-01-impl-001 dispatch=disp-01-impl-review-001 phase=implementation-review verdict=REJECT_IMPLEMENTATION reviewer=bc-d9884a95-f472-502f-aeca-466f1ea709d4 contract=sha256:122bc93b0de9d398055a464ad8bfdc933849c80890e0d8285db244d57e23fe91 snapshot_before=sha256:d903b340bbb9bc3ea22f90794c9af06dfff29e8d95ed10e8c5fcb201e43bdaae snapshot_after=sha256:d903b340bbb9bc3ea22f90794c9af06dfff29e8d95ed10e8c5fcb201e43bdaae gaps=D3-live-listing-and-period-selection rejection_count=1 no_progress=0 artifact=loop/manifests/disp-01-impl-review-001-result.md
- event=rev-01-impl-002 dispatch=disp-01-impl-review-002 phase=implementation-review verdict=APPROVE_IMPLEMENTATION reviewer=bc-96fe6aac-6713-5d45-94a2-8b89225d20d4 contract=sha256:122bc93b0de9d398055a464ad8bfdc933849c80890e0d8285db244d57e23fe91 snapshot_before=sha256:e68c89956ab1f6f6e3dfb7039faea45e1e3fee82ed91aa3d4d028c6b158358fe snapshot_after=sha256:e68c89956ab1f6f6e3dfb7039faea45e1e3fee82ed91aa3d4d028c6b158358fe gaps=none rejection_count=1 no_progress=0 material_improvement=yes artifact=loop/manifests/disp-01-impl-review-002-result.md
Budget limit / consumed / measurement: Not configured; no execution budget was supplied
Blocker / resume status / resume action / recheck condition / deadline: none
Advance phase: archive pending
Next slice ID / draft: 02 — Read financial reports with page-level evidence / pending Builder draft

## Status
Shipped

## Next
Archive accepted BUILD to `slices/01-report-retrieval.md`, add slice 01 to SLICES Shipped, then draft slice 02. No worker may write application code during advance.
