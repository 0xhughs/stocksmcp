# Project-loop retrospective — Hybrid Pilot v0

**Scope:** the project-loop workflow used to build the hybrid MCP in `saudi-exchange-mcp/`, not a product recap.  
**Sources:** `LOOP.md`, `BUILDER.md`, `REVIEWER.md`, `AGENTS.md`, `SLICES.md`, `BUILD.md`, `loop/identity.py`; archives `slices/01`–`05`; git on `cursor/hybrid-mcp-pilot-6492`; gitignored `loop/manifests/disp-*-result.md` on this VM; this coordinator session (including one conversation summary).  
**Facts vs interpretation** are labelled. Counts are from archives, not reconstructed.

## Workflow version actually followed

`LOOP.md` has no version field. Its contract hash stayed `sha256:bf33e390b76fb4dc669ae2a551a62f776d43d6f0dcd3b3bcc1666a13d95ac7e1` from slice 01 plan review through Complete, so protocol files were not edited during the run.

Followed: Coordinator writes protocol/archives; Builder implements; Reviewer verifies and does not fix. State machine Proposed → plan review → Building → implementation review → Shipped → archive → next draft or release. Identity via `python3 loop/identity.py snapshot|contract`. Retry limits 3 rejections/slice, 2 consecutive no-progress repairs, 3 failed release reviews. Execution budget was not configured.

Tool adapter in BUILD: Cloud Agent coordinator `bc-ee81624b-9342-4c75-b5b0-a03c9edd6492` dispatching Cursor Task subagents. Reviewers recorded as Cursor Grok 4.6. Builder slugs were distinct; not every Builder slug is in BUILD.

`AGENTS.md` allows installed skills but says the pack must stand alone. No `project-loop` skill was in this environment. The run used the repository protocol only.

## 1. What actually happened

The coordinator authorized Hybrid Pilot v0 through slice 05, captured a baseline snapshot (`file_count=10`), and for each slice persisted a dispatch ID, launched a Builder, launched a Reviewer, recomputed identities, wrote BUILD/SLICES, archived, and advanced. After slice 05 it dispatched `disp-release-001` and set Complete only after `APPROVE_RELEASE` matched recomputed hashes.

Builders drafted BUILD (`disp-0N-draft-001`) and implemented (`disp-0N-impl-001`, plus `disp-01-impl-002`). They wrote code, tests, and `evidence/0N-*/` notes—not protocol files or git commits.

Reviewers were separate agents. Five plan reviews all `APPROVE_PLAN` (blockers none). One implementation reject: `disp-01-impl-review-001`, gap `D3-live-listing-and-period-selection`; repair `disp-01-impl-review-002` (`material_improvement=yes`). Slices 02–05 approved first try. Release: `APPROVE_RELEASE`. Git: 25 commits after pack upload.

**Differed from the written text:** LOOP archive step 4 says set Now to `None — target complete`, but `identity.py` hashes Now/Later **bodies**, so that sentence changed the contract away from `6b673206…`. The coordinator used an empty Now body and put mapped slice 05 text under Later. Archiving `slices/05-hybrid-mcp.md` (required, covered) moved snapshot `file_count` 116 → 117 despite “state-only writes must not invalidate approvals.” LOOP’s pending-result field was often left `none` while verdicts sat in gitignored manifests. `HANDOFF.md` was stale after summarization; resume used BUILD/SLICES/git. Pytest ran under `.venv`; some contracts still say `python3 -m pytest`.

## 2. What helped

Independent review mapping Done-when to live evidence. Slice 01 pytest was **50 passed** while live listing returned HTTP 500 and the PDF came from `retrieve-url`. Review rejected D3 only. Repair added Playwright/Chrome tab listing; approval froze rejection count **1**. That stopped shipping a known-URL download as discovery.

Fixture vs live labelling. Slice 05 Builder notes said listing unavailable; release review re-ran JSON-RPC with `SAUDI_MCP_USE_BROWSER=1` and listed 44 reports—not mocks or website tabs.

Out lists. Reviews forbade `google_finance_mcp.server` as product, `2222:SAU`, merging Google `Net income` with PDF `Profit for the year`, and committing live Google bodies. Release `tools/list` had no upstream `ds:*` / `call_rpc` tools. `git ls-files` had no `live-payloads`.

Identity recompute. Uncommitted SLICES edits almost went to release as `23641846…`; recheck restored `6b673206…` first. After summarization, BUILD and git were enough to resume. Slice Out lists (02: no MCP/Google) kept the D3 repair in 01.

## 3. What caused friction

**Workflow — identity vs archive/Now.** Literal Now text and the required archive file both change hashes. Interpretation: LOOP and `identity.py` disagree; release needed an extra “archive-only delta” story.

**Workflow — persist round-trips.** Each slice: draft, plan review, impl, impl review, archive. Plan reviews never rejected but still re-hashed the tree and restated already-authorized v0 / no-deploy Out.

**Workflow — gitignored verdicts.** Full Reviewer reports are not in git. A clone cannot read D3’s blocker text; BUILD/SLICES keep one-line events.

**Environment, not LOOP.** urllib `statementsTabData` HTTP 500 is an access fact. Live listing differed between the slice 05 Builder session and release. No flake rate was measured.

**Requirements vs tests, not roles.** D3 live discovery was in the slice 01 contract; pytest did not encode it. Review caught it.

**Unmeasured:** token or wall time per slice (budget not configured).

## 4. Planning and review

Plan reviews checked Now membership, one-slice coherence, observable Done-when, Out, and identity. Slice 05 also checked that wrap APIs already existed. They did **not** catch live listing failure (not knowable from the Proposed page). They **did** repeat settled authority and no-deploy Out every slice. Interpretation: useful as a scope lock; expensive as a second full audit.

Implementation review caught one real gap (D3). Repair review stayed on that gap. No archive records a Builder contesting a finding. `BUILDER.md` has no challenge path—only “report blockers” and “do not weaken criteria.” Whether evidence could overturn a wrong finding is **untested**.

## 5. Testing and confidence

Builders wrote tests; Reviewers and the coordinator re-ran them.

| Slice | Default pytest at ship | Notes |
|---|---|---|
| 01 first review | 50 passed | Live D3 failed |
| 02 | 94 passed | Stored Maaden OCR/native |
| 03 | 125 passed, 3 skipped | `live_google` |
| 04 | 151 passed, 6 skipped | |
| 05 / release | 178 passed, 7 skipped | Live MCP 1 passed at release |

Default suite is offline to Google and does not need the exchange. Intentional, and why slice 01 could look done without listing.

**Still unverified (documented):** Cursor desktop MCP UI; live Arabic FS PDF; Aramco official PDF; market-wide coverage; `is_realtime` true; Google BS/CF display labels. This retrospective did not re-run pytest. No flake statistics.

Misleading pass: slice 01 first candidate. Slice 05 “listing unavailable” was labelled, not a false green; release later succeeded with the browser fallback.

## 6. Retries, interruptions, completion

Archives: slice 01 rejection count **1** (limit 3); slices 02–05 **0**; failed release reviews **0**; no-progress **0**. Counters froze on approval. Limits were never hit.

The run did not stop after slice 01 or after slice 05 implementation approval. It did not start later slices or deploy.

Interruption: summarization during slice 05 advance left identity-breaking SLICES edits. Recovery used live files and git, not HANDOFF. Archives 01–05 were not overwritten. Complete recorded: all slices accepted, Now body empty, matching `APPROVE_RELEASE`, no blocker, run status Complete. Review artifacts remain VM-local.

## 7. Recommendations (ranked)

**1. Align LOOP text with `identity.py` on Now and archives.**  
*Example:* “None — target complete” in Now broke the contract; `slices/05-hybrid-mcp.md` changed the snapshot.  
*Change:* Keep Now body empty at finalization; put the sentence under excluded headings; define release identity as implementation snapshot plus named archive paths; add a unit test that Now/Later moves do not change the contract extract.  
*Tradeoff:* Excluding archives weakens tamper detection unless the archive hash stays in Release evidence.  
*Test:* Archive last slice, write Complete bookkeeping; contract digest unchanged; snapshot delta is only the archive path.

**2. Track Reviewer verdict files in git.**  
*Example:* `disp-01-impl-review-001-result.md` is gitignored.  
*Change:* On persist, copy verdict markdown to `evidence/reviews/` (Reviewer still must not edit the candidate). Keep identity JSON ignored.  
*Tradeoff:* Larger diffs; still ban live Google bodies.  
*Test:* Fresh clone contains the D3 gap text.

**3. Shorten plan review when authority is unchanged.**  
*Example:* Five `APPROVE_PLAN` / blockers-none, each restating v0 authorization and often re-running prior pytest.  
*Change:* Plan review = Now match, new Done-when observability, Out delta, identity match. Prior-slice pytest waits for implementation review unless the plan changes those trees. Keep independent `APPROVE_PLAN` before code.  
*Tradeoff:* A quiet Out expansion waits until implementation review.  
*Test:* Next multi-slice pack: plan-review effort vs whether implementation review still catches the first real gap.

**4. Stop writing `HANDOFF.md`.**  
*Example:* It was stale at the only interruption that mattered; `identity.py` already excludes it.  
*Change:* Resume from BUILD Loop state + SLICES + git only.  
*Tradeoff:* BUILD is denser.  
*Test:* Resume a summarized session with HANDOFF absent.

**5. Put live-path Done-when in Builder tests.**  
*Example:* Slice 01 pytest passed without a source-observed listing.  
*Change:* Opt-in `live_listing` that `retrieve-url` cannot satisfy; labelled skip if the site is down.  
*Tradeoff:* Environmental. Keep opt-in.  
*Test:* A retrieve-url-only candidate fails the marked test.

**Preserve:** independent Reviewer; Reviewer must not edit; Done-when ↔ evidence; rejection counters; source isolation; live vs fixture labels; Coordinator-only protocol writes.  
**Simplify:** HANDOFF; hashed Now sentence; duplicate “already authorized / no deploy” plan-review essays.

## Judgment

**Make targeted improvements; do not redesign.**

Independent review is why a retrieve-url bypass did not ship as discovery, and why Complete required one MCP connection rather than unit tests. Counters, archives, and the stop condition worked once identity was reconciled. Friction was coordinator hashing, gitignored verdicts, stale HANDOFF, and plan reviews that never rejected—not the Builder/Reviewer split. Fix those without adding agents or ceremony.
