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
- Execution remains unstarted until the user authorizes a loop and confirms its target. This Proposed contract has no plan approval.
- Use Saudi Exchange as the discovery authority. A report hosted elsewhere is acceptable only when reached through a verified company report link with preserved provenance; do not silently switch to general-web substitutes.
- Prefer a suitable documented API if verified; otherwise assess direct public retrieval and browser-driven report selection as alternatives. Choose based on evidence and permitted access, not assumed endpoints.
- Select the smallest representative pilot sample that can demonstrate the intended inputs and report distinctions, document it, and let independent plan review assess adequacy. The discussion specifies no required sample count.
- Re-check current official library documentation when implementation choices are made. Do not introduce paid OCR/model services as an implicit dependency.
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
Not completed yet. Pack preparation checks are not implementation proof.

## Review
Pending plan review.
Plan approval: none
Implementation approval: none
Each result records dispatch ID, reviewer identity, verdict, contract identity, snapshot identity, evidence, and criterion-specific blockers.

## Loop state
Execution mode / tool adapter: Not configured
Coordinator: none
Worker / role / phase: none
Dispatch ID / launch state / input identity: none
Pending result / last consumed dispatch: none
Snapshot capture and recheck commands / coverage / exclusions: Not configured; record reproducible project-specific commands before first dispatch as required by LOOP.md
Baseline snapshot: none
Contract identity: none
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
Await authorization to execute and confirmation/replacement of the proposed Hybrid Pilot v0 target through slice 05. Then the coordinator inspects the actual implementation workspace, records the tool adapter and snapshot/contract capture commands, captures review inputs, and dispatches independent plan review. Do not implement before a valid APPROVE_PLAN verdict.
