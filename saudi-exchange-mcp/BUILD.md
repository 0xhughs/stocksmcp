# BUILD.md

Slice: 05 — One MCP for company research and official reports
Proposed by: Builder dispatch disp-05-draft-001 (not independently accepted; not live BUILD until coordinator replacement)

## Goal
Expose the **already shipped** Hybrid Pilot v0 library (slices 01–04) through **one local stdio MCP server** so a host assistant can research the documented Main Market sample — Saudi Aramco (`2222` / `sa-tdwl-2222`) and Maaden (`1211` / `sa-tdwl-1211`) — from a **single MCP connection**. Wrap existing capabilities; do not re-implement Google parsers, Saudi listing/download, or PDF/OCR. Tools must have **source-specific descriptions**: Google Finance for shared lookup, overview/quotes/statistics, news, profile/about, earnings, and income statement / balance sheet / cash flow; Saudi Exchange for original financial-statement/report listing, PDF download, and page-level read/search. Document **Cursor MCP install** (stdio `mcp.json`) without deploying. Prove the four prompt classes — broad company questions, targeted section queries, original-report requests, and combined requests — by **live `tools/list` + `tools/call` on one stdio MCP client connection**, not by website-tab observation, library-only unit tests, or mocks alone. Preserve Arabic/English identity behaviour, explicit partial failures, and source isolation. This is the **final Hybrid Pilot v0 slice**. Independent **Release gates** in `SLICES.md` apply **after** this slice ships; this contract must leave dated MCP-session evidence those gates can re-check. It is **not** itself a release approval.

## Done when
- **D1 — One product stdio MCP server wrapping existing capabilities:** Ship a single local MCP server that:
  - Speaks [MCP 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) over the [stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports): newline-delimited JSON-RPC on stdin/stdout; **stdout is MCP messages only**; logs (if any) on stderr.
  - Completes initialize (`initialize` + `notifications/initialized`) declaring the `tools` capability, then answers `tools/list` and `tools/call`.
  - Is the **product** process (console script and/or `python -m …` entry). It must **not** be `python -m google_finance_mcp` / `google_finance_mcp.server:main`. The vendored upstream server at `src/google_finance_mcp/server.py` remains in-tree for the pinned client; it is **not** the Hybrid Pilot product. Product `tools/list` must **not** include upstream generic tools (`google_finance_call_rpc`, `google_finance_call_dataset`, `google_finance_call_quote_dataset`, `google_finance_batch_call`, `google_finance_get_quote_holdings`, generated `google_finance_ds_*` names, or explicit live RPC hashes as tool names).
  - Wraps existing product APIs rather than forking parsers:
    - identity: `saudi_exchange_reports.identity.resolve_company` / `catalog.PILOT_COMPANIES`;
    - Google: `saudi_exchange_reports.google_finance.service` (`get_overview`, `get_news`, `get_profile`, `get_earnings`, `get_financials`, `get_coverage` / `get_inventory` as needed);
    - reports: `list_reports_from_source` / `select_report` / `resolve_and_retrieve` / `retrieve_from_url` / `retrieve_report`;
    - reading: `extract_report` / `read_pages` / `search_extracted` / `find_line_item`.
  - Keeps Google Finance modules **separate** from Saudi listing/PDF/OCR modules (same split as slices 03–04). MCP handlers compose both; they do not merge numbers or share cache policy.
  - Publishes a **fixed** product tool list (static names/schemas). Do not advertise changing `ds:N` keys. Hide RPC ids from tool names, descriptions shown to the host, and tool JSON (same rule as slice 03/04 public JSON).
  - Server `instructions` (MCP initialize) must tell the host: Google Finance is primary for everyday company questions and structured tables; Saudi Exchange PDFs are for official reports, notes, and original evidence; installing MCP does not itself perform research; unknown quote freshness is not real-time; Google tables are not audited filings; PDF page citations apply only to PDF-derived facts.

- **D2 — Shared lookup through MCP (Arabic/English/ticker):** A lookup tool (see Constraints for the reversible name) accepts a company name and/or ticker (and optional exchange) and returns the existing `ResolveResult` shape: `status`, `reason`, `company` (or null), `candidates`. On `matched`, include **both** source identifier blocks without conflating them:
  - shared: `company_id`, English name, Arabic name, ticker, exchange;
  - `saudi_exchange`: `company_symbol`, `profile_url`, `market`, `issuer_id`;
  - `google_finance`: `quote_symbol`, `exchange`, `quote_id`, `quote_url`, `verified`.
  Through **MCP `tools/call`** (not only `resolve_company()` in-process), reproduce the shipped identity cases:
  - Aramco: ticker `2222`, English `Saudi Aramco` / `Aramco`, Arabic `أرامكو` / `أرامكو السعودية` / `شركة الزيت العربية السعودية` → `sa-tdwl-2222`, `2222:TADAWUL`, verified;
  - Maaden: ticker `1211`, English `MAADEN`, Arabic `معادن` → `sa-tdwl-1211`, `1211:TADAWUL`;
  - matching name+ticker `Saudi Aramco` + `2222` → matched;
  - conflicting `Saudi Aramco` + `1211` → `conflicting`, no company, both candidates;
  - ambiguous `Saudi Arabian` → `ambiguous`, no silent pick;
  - unknown/empty and not-found (`9999`) remain explicit;
  - `2222` + `NASDAQ` → `wrong_exchange`;
  - never treat `2222:SAU` / `1211:SAU` as the verified mapping.
  Other Google/Saudi tools that take a company query must call this same resolver first. They must **not** silently pick among ambiguous/conflicting inputs, override a failed resolve with a Google hit, or swap Aramco↔Maaden via related securities.

- **D3 — Google Finance tools through MCP (targeted sections):** On a matched pilot identity, MCP tools return the **existing** slice 03–04 product fields, each result labelled as **Google Finance** (source name + Google quote URL). Do not rename Google labels to IFRS/PDF names. Missing values stay `unavailable`, never `0`. Unknown freshness is not real-time (`is_realtime` remains false unless the payload actually proves otherwise — shipped overview currently does not). Required section tools / equivalent arguments:

  | Capability | Must return (when the library actually has them) | Source label |
  |---|---|---|
  | Overview / quote / statistics | identity, `last` price, currency, `source_url`, timezone-aware `retrieved_at`, `quoted_at` / `quote_timezone` or explicit unavailable, `freshness`, session/delay when present, labelled stats (previous close, ranges, volume, market cap, P/E) or unavailable | Google Finance |
  | News | security/company feed items with publisher, article URL, publication time when present; `read_status` distinguishing headline/snippet from an article actually read; no invented full-story summaries | Google Finance |
  | Profile / about | description, website, CEO, founded, headquarters, employees, sector — original labels/values; missing fields listed in `unavailable` | Google Finance |
  | Earnings | quarterly actual-versus-estimate periods (revenue/EPS actual and estimate labelled; surprise only when present); currency; period-end; `article_summary` remains null | Google Finance |
  | Income statement | annual **and** quarterly (or explicit gap for a missing frequency); original Google labels; full-unit values + scale/currency; duration `annual`/`quarterly` | Google Finance |
  | Balance sheet | annual and quarterly rows from the Financials purpose; Google labels only if display-verified, otherwise `unverified` / `unavailable` as already shipped; point-in-time period-end | Google Finance |
  | Cash flow | same as BS for CF; duration is a period, not a point in time; missing CF is not proof of no cash activity | Google Finance |

  Surface shipped coverage gaps instead of hiding them: earnings HTML may still load while the dataset is populated; BS/CF Google row names remain unverified until a display table exists (`display_label_gap` / coverage status from `get_coverage`). Do not expose Holdings, analyst targets, charts, `call_rpc`, or AVGO `labeled_data` as product tools. `google-crosscheck` stays a library/CLI proof aid; it is **not** a host tool that merges Google and PDF into one number.

- **D4 — Official-report tools through MCP (list / download / read / search):** On a matched pilot identity, MCP tools wrap slice 01–02 without substituting Google tables for a requested filing:

  | Capability | Must return | Source label |
  |---|---|---|
  | List reports | observed title, period, `annual`/`interim`/`other`, language, publication date or `publication_date_unavailable`, source/download URL, listing `from_cache` / `unavailable` / `reason` / `source_url` | Saudi Exchange |
  | Download / retrieve | original PDF to configured storage; status `downloaded` / `cache_hit` / `updated` / `failed`; content hash; local path; source/final URL; retrieval time; identity/period inspection when performed | Saudi Exchange |
  | Read pages | 1-based PDF page text/spans; method `native`/`ocr`/`mixed`/`unreadable`; original strings; content hash; page numbers are PDF indices | Saudi Exchange PDF |
  | Search (and optional line-item) | hits with original string, page, hash, method; empty search is `not_found`, not zero and not “no activity” | Saudi Exchange PDF |

  Distinguish reporting period, publication date, annual versus interim, report language, and report type. Reuse the existing listing route (urllib profile + `statementsTabData`, browser-tab fallback when that AJAX returns 500 — **not** an official API). Constrain downloads to verified `/Resources/fsPdf/` hosts already enforced by slice 01. Read/search paths must stay inside configured storage (or explicit test fixture roots). PDF page citations in tool output apply **only** to these PDF-derived facts. Do not invent filenames. Cached listing is never proof that no newer report exists (always re-fetch for list/retrieve unless the caller explicitly asks to inspect a labelled cache copy).

- **D5 — One MCP client connection: four prompt classes + Cursor install docs:** Live validation is an **in-workspace MCP client** that launches the product stdio server as a subprocess, performs initialize, `tools/list`, and `tools/call`, and keeps **one connection** for the whole demonstration. Website tabs, HTML inspection, calling `get_overview()` / `extract_report()` from pytest **without** JSON-RPC, and fixture unit tests **alone** do **not** satisfy this criterion. Cursor desktop UI is **not** the required proof host (Reviewer in this workspace may not have a Cursor MCP session); Cursor install is **documented**, not executed as deployment.

  **A — Cursor install (document, do not deploy).** README (and `evidence/05-hybrid-mcp/`) must include a copy-paste [Cursor `mcp.json`](https://cursor.com/docs/mcp) stdio example: project `.cursor/mcp.json` and/or user `~/.cursor/mcp.json`, `mcpServers` entry with `command` / `args` / optional `env` pointing at the local venv and product entry (workspace-relative paths; `${workspaceFolder}` interpolation is allowed in the example). State clearly: local, personal, user-initiated; not a hosted/multi-user service; not Cursor Marketplace publishing; not Streamable HTTP/SSE remote deployment. Installing or enabling the server does not run research until the host calls tools.

  **B — Four prompt classes on that one connection** (live Google + real report path; see Tests for fixture vs live labelling). Record tool names, arguments (no live Google bodies), field-presence, identity, source labels, and coverage/gaps. Include Aramco in the Google-side demos. Official-report proof may use Maaden (the shipped stored original) and must still go through MCP:

  | Class | User-shaped request (examples, not frozen copy) | Required MCP evidence on the **same** connection |
  |---|---|---|
  | Broad company | “Tell me about Aramco” | Lookup + Google overview, news, profile, earnings, and financials (IS required; BS/CF retrieved or explicitly gapped). Per-section coverage/missing status present. |
  | Targeted | price; news; profile; earnings; “income statement, balance sheet, and cash flow” | The corresponding Google tools (not a website tab). Quote has price, currency, source, retrieved_at, quote-time or unknown freshness. |
  | Official report | “Retrieve Maaden’s official 2025 financial report PDF” and read/search | List and/or download via MCP; then read/search the original. For the stored Maaden 2025 annual English FS (SHA-256 `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e`, source `https://www.saudiexchange.sa/Resources/fsPdf/370_0_2026-03-11_15-58-59_En.pdf`), search/read returns page-cited originals (notes p.19 native and/or statements p.13–18 OCR as shipped). Google tables must not be returned as that filing. |
  | Combined | price + latest results; or Arabic: “حلّل القوائم المالية لأرامكو، رمز 2222، …” using Google figures plus original-report evidence when citing filings | Same session calls **at least one Google tool and one Saudi report tool**. Each fact keeps its own provenance. Do not merge Google `Net income` with PDF `Profit for the year`. PDF page refs only on PDF facts. Latest reporting period is not the quote date. |

  Arabic **and** English company inputs must succeed for lookup on this connection (D2). Ordinary reversible: a Google-only compose helper for the broad class, provided it still labels every section Google, lists gaps, and does not pull PDFs unless asked.

- **D6 — Partial failures, source isolation, and bounded errors through MCP:** On the MCP connection (fixture stdio session required; live mixed-failure is additional):

  - **Partial / mixed:** Google tool failure (injected scripted error or live outage) returns an explicit unavailable/error payload and **does not** disable a subsequent Saudi list/read on the same connection. Report-tool failure (unavailable listing, invalid PDF, missing period) does **not** disable a subsequent Google overview. A mixed request never silently fills a Google gap with a PDF table or a PDF gap with a Google table.
  - **Source isolation:** Google tools do not write under `storage/reports/` and do not apply PDF cache policy. Report tools do not call `LiveGoogleSource` / Google batchexecute. Public tool JSON includes an explicit source field (`google_finance` vs `saudi_exchange`). PDF `page_number` fields appear only on report-reading results. Google results must not claim `official_filing` / auditor / notes.
  - **Identity failures** via MCP: conflicting, ambiguous, not-found, wrong-exchange — same statuses as D2; no company payload.
  - **Reports:** missing period → listing/selection `unavailable`; HTML-as-PDF and partial download still `failed` with no valid record; off-storage read path → `UnsafeDestination` / equivalent tool error; unreadable OCR pages flagged, not omitted; missing values not zero.
  - **Untrusted data:** Google HTML/JSON and PDF bytes remain data, never instructions. No stealth, CAPTCHA solving, proxy rotation, or source-bypass. No background polling or streaming feeds.
  - Tool-level business outcomes (not_found, unavailable, conflicting) should be **structured tool results** the host can read (spec tool execution errors may set `isError: true` for unexpected failures and invalid arguments; do not use a JSON-RPC protocol error for a normal `not_found` company). Unknown tool name remains a protocol error.

- **D7 — Reproducible proof, fixtures vs live, snapshot compatibility:** Default `pytest` stays **offline** to Google (existing `httpx` autouse block) and does **not** require the live Saudi Exchange website. It **must** exercise the **stdio MCP protocol** with `ScriptedSource` / fake listing+PDF transports (initialize, `tools/list` schemas/descriptions, D2 identity calls, D3/D4 happy paths, D6 isolation/partial). Opt-in live MCP session (`live_google` and/or a dedicated `live_mcp` marker, plus `SAUDI_LIVE_GOOGLE=1` as today) runs D5.B against Aramco Google through the reused client. Stored-PDF MCP read/search skips if the gitignored Maaden file is absent (retrieve with slice 01 CLI first; do not substitute Google). Live Google bodies stay in gitignored `evidence/live-payloads/` or are discarded — **never** committed, never stored under `storage/reports/`. Tracked evidence under `evidence/05-hybrid-mcp/` records commands, tool names, field-presence, source labels, coverage/gaps, PDF hash/page citations, Cursor `mcp.json` example, and fixture vs live vs stored-PDF labelling. Slice 01–04 tests remain passing. Snapshot capture/recheck commands remain compatible with `loop/identity.py` (see Loop state). After this slice is independently accepted, coordinator archive/advance sets Now to none and **release pending**; an independent Reviewer then checks `SLICES.md` **Release gates** against the final candidate using this MCP evidence. Passing this slice’s implementation review is **not** Complete.

## Out
- Public deployment, Cursor Marketplace publishing, hosted/multi-user MCP, Streamable HTTP/SSE as the product transport, Cloud Agent / team MCP distribution, continuous monitoring, scheduled polling, streaming prices, trading, brokerage, or investment recommendations.
- Treating Hybrid Pilot coverage as market-wide, adding companies beyond the documented sample, or new identities / `2222:SAU` / `1211:SAU`.
- Re-implementing Google dataset parsing (slice 03–04) or Saudi listing/download/OCR (slice 01–02), except thin MCP handlers and injection hooks for tests.
- Starting or documenting `google_finance_mcp.server` as the product; exposing Holdings, analyst targets, charts, generated `ds:N` tools, or `call_rpc` hashes.
- Silently representing Google tables as original filings, fabricating PDF page citations, presenting unknown freshness as real-time, or merging Google and PDF figures in one “true” number (including exposing `google-crosscheck` as a host merge tool).
- Applying Saudi PDF cache/archive policy to Google responses; committing or exporting live Google payloads, screenshots, or copied Google assets.
- A separate server-side LLM. The host assistant composes analysis; this server only retrieves and labels evidence.
- Changing the vendored upstream revision silently. If `LICENSE` / `LEGAL.md` at the pin differ when re-read, stop and return a contract proposal.
- Completing LOOP **Release gates** inside this slice’s implementation review, skipping independent release review, or claiming run status Complete.

## Constraints
- Execution of Hybrid Pilot v0 through slice 05 is authorized. This Proposed contract has no plan approval; do not implement until an independent Reviewer returns APPROVE_PLAN for matching contract and baseline identities.
- Depend on shipped slices 01–04. Keep `company_id` `sa-tdwl-2222` / `sa-tdwl-1211` and verified Google mappings `2222:TADAWUL` / `1211:TADAWUL`. Upstream pin remains `319760998e60d4b060fb993b3dc8db94364b019c` (`saudi_exchange_reports.google_finance.PINNED_REVISION`). Re-read `vendor/google-finance-mcp/LICENSE` and `LEGAL.md` against hashes in `evidence/03-google-overview/notices.md` (`3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986` / `51dac106bb00d1c896f8c04cc6e39211f715a4e13a13700f8057bc68594e4048`).
- Runtime: existing Python 3.12 package `saudi-exchange-reports` / `saudi_exchange_reports`. Slice 03 recorded that the pinned upstream stdio server needed `mcp>=1.0,<2` in addition to `httpx`/`anyio`. Adding the official MCP Python SDK in that range (or a current 1.x compatible with `tools/list` + `tools/call` + stdio) is in scope now; pin an actual version at implementation from current package docs. Re-check [MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) and [stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) when choosing the SDK. Do not introduce paid services or credentials.
- Ordinary reversible choices (do not escalate):
  - Product module `saudi_exchange_reports.mcp` (or `…server`) + `python -m saudi_exchange_reports.mcp` and/or console script `saudi-exchange-mcp`;
  - SDK `Server` + `stdio_server` (same family as the vendored file) or an equivalent 1.x API that still speaks stdio JSON-RPC;
  - In-workspace proof client using the SDK stdio client (`ClientSession` / `stdio_client`) **or** an equivalent newline-JSON-RPC client that still performs initialize / `tools/list` / `tools/call` — library function calls are not a substitute;
  - Tool names (capabilities are required; names are not frozen): `lookup_company`, `google_overview`, `google_news`, `google_profile`, `google_earnings`, `google_financials` (arguments `statement` + `frequency`), `google_coverage`, `list_official_reports`, `download_official_report`, `read_official_report`, `search_official_report`; optional `research_company` compose for D5 broad class; optional `find_official_line_item`;
  - Tool results as JSON text content (and optional `structuredContent`); each payload includes `source` and existing `to_dict()` fields;
  - Storage root env e.g. `SAUDI_REPORTS_STORAGE` defaulting to `storage/reports`; Google injection env/hook for tests (do not require network in default pytest);
  - `tools.listChanged` false (fixed product list);
  - Example Cursor config committed as `evidence/05-hybrid-mcp/cursor-mcp.json.example` (and README); do not require a machine-specific `~/.cursor/mcp.json` in git;
  - pytest marker `live_mcp` in addition to existing `live_google` / `stored_pdf`;
  - Keep `tests/test_google_notices.py` client-import check: importing `GoogleFinanceClient` still must not import `google_finance_mcp.server`.
- Data-handling: local, personal, user-initiated (LEGAL.md + AGENTS.md). GPL-3.0 licenses reused **code**, not Google or exchange data. Do not claim this repository licenses quotes, news, or filings.
- Untrusted responses: constrain Google to the pinned client’s Finance page/batchexecute URLs; constrain PDFs to existing host allowlists and storage bounds.
- Keep snapshot capture/recheck commands compatible with `loop/identity.py` (see Loop state). Do not move manifests into snapshot coverage.
- `SLICES.md` Release gates apply **after** independent acceptance of this slice. Builder must produce MCP-session evidence those gates will re-check (single connection; Aramco Google quote metadata; news/profile/earnings/financials through MCP; original PDF read with page citations; cache/identity/partial/isolation). Do not treat a green library pytest as those gates.

## Data / state impact
Adds an MCP server module, SDK dependency (`mcp` in `pyproject.toml` / `requirements.txt`), tests that spawn stdio, README/Cursor install docs, and tracked evidence under `evidence/05-hybrid-mcp/`. Does not change PDF original bytes or Google cache policy. Google HTTP remains transient (gitignored `evidence/live-payloads/` only). Report PDFs and extraction caches stay under gitignored `storage/`. No broker accounts, no financial transactions, no public hosting. Example `mcp.json` is documentation, not a deployed service.

## Tests
- Evidence locations below are proposed, not existing proof: `evidence/05-hybrid-mcp/checks.md`, `mcp-session.md` (one-connection tool log, fixture vs live vs stored-PDF), `cursor-mcp.json.example`, `coverage.md` (MCP-visible section status for Aramco/Maaden), `tools.md` (`tools/list` names + source phrases in descriptions).
- D1: `tools/list` after initialize contains the required capabilities; descriptions mention Google Finance vs Saudi Exchange as appropriate; **none** of the forbidden upstream tool names; stdout of a scripted session is parseable JSON-RPC only (no `print` banners). Importing `google_finance_mcp.client.GoogleFinanceClient` still does not import `google_finance_mcp.server`.
- D2: stdio `lookup_company` (or equivalent) for Arabic/English/ticker cases in Tests of slice 01/03 identity; conflicting/ambiguous/wrong-exchange via MCP.
- D3: stdio Google tools with `ScriptedSource` fixtures already used in slices 03–04; assert source label, identity, unavailable≠0, no RPC ids in JSON. Opt-in live Aramco MCP calls: overview price+currency+source+retrieved_at+freshness; news publisher/link/time when present; profile fields; earnings actual/estimate labels; IS annual and quarterly or explicit gap; BS/CF retrieved or gapped as in `evidence/04-google-financials/coverage.md`. **No golden live prices.**
- D4: stdio list/download against fake HTML+PDF transport (existing `FakeTransport` / fixtures); read/search against synthetic PDFs and, when present, stored Maaden FS with page citations. Off-storage path fails closed. List `from_cache` cannot be used as freshness proof.
- D5: documented Cursor example parses as JSON with `mcpServers` + command/args. One-connection script: four prompt classes. Default pytest runs a **scripted** one-connection session covering all four classes. Live MCP session (opt-in) covers Aramco Google broad+targeted and Maaden official-report read (live list/download when the slice 01 route works; otherwise stored PDF after MCP download-from-url or documented skip of live listing only — read/search still required on the stored original). Combined class on the **same** live or scripted connection.
- D6: scripted Google failure then successful report tool; scripted report failure then successful Google tool; isolation tests that Google handlers do not write `storage/reports` and report handlers do not construct `LiveGoogleSource`; invalid PDF / unsafe path via MCP.
- D7: Reviewer runs `PYTHONPATH=src python3 -m pytest tests/ -q` (or project venv) **without** network to Google; live tests skipped by default; stored-PDF skipped if gitignored file missing. Slice 01–04 tests pass. Audit git for live Google bodies. Snapshot commands remain `python3 loop/identity.py snapshot …` as below.

## Proof
Proposed by Builder disp-05-impl-001 (not independently accepted). Product stdio MCP server `python -m saudi_exchange_reports.mcp` wrapping 01–04 APIs (not `google_finance_mcp.server`). Default pytest: 178 passed, 7 skipped (coordinator recheck 2026-09-09). Live one-connection MCP session recorded four prompt classes; live Saudi listing was unavailable in that session; stored Maaden FS was read/searched via MCP. Evidence: `evidence/05-hybrid-mcp/`. Cursor install example only; not deployed.

## Review
Plan review complete.
Plan approval: APPROVE_PLAN disp-05-plan-001 reviewer=bc-77e0572d-cf37-513e-a962-4c16c8137d01 (Cursor Grok 4.6) contract=sha256:6b673206c8507506b5d5b53b89204d3a37558524ea0c1daed23de09d114ddaa3 snapshot=sha256:a99c3c9f3c321c6e3a116c4ffc0ce83e41057efd66503b483544dc88b7b5c8b0 blockers=none artifact=loop/manifests/disp-05-plan-001-result.md
Implementation approval: APPROVE_IMPLEMENTATION disp-05-impl-review-001 reviewer=bc-cbb75edc-d8c4-5121-9eff-9852c0b2df98 (Cursor Grok 4.6) contract=sha256:6b673206c8507506b5d5b53b89204d3a37558524ea0c1daed23de09d114ddaa3 candidate=sha256:3fd4cb8c7fc8617be28b27490a57c3e35fc538d7db68652298740a5c95316842 blockers=none artifact=loop/manifests/disp-05-impl-review-001-result.md
Release approval is recorded in SLICES Release evidence (APPROVE_RELEASE disp-release-001); this page remains the slice 05 Shipped receipt.
Each result records dispatch ID, reviewer identity, verdict, contract identity, snapshot identity, evidence, and criterion-specific blockers.

## Loop state
Execution mode / tool adapter: Cursor Cloud Agent coordinator (run bc-ee81624b-9342-4c75-b5b0-a03c9edd6492) dispatches independent Builder and Reviewer via Cursor Task subagents with isolated context and distinct model slugs. Reviewer never edits the candidate. One active worker per checkout `/workspace`.
Coordinator: Cursor Cloud Agent bc-ee81624b-9342-4c75-b5b0-a03c9edd6492 (workspace `/workspace`, branch `cursor/hybrid-mcp-pilot-6492`)
Worker / role / phase: none / none / complete
Dispatch ID / launch state / input identity: disp-release-001 / consumed / contract=sha256:6b673206c8507506b5d5b53b89204d3a37558524ea0c1daed23de09d114ddaa3 candidate=sha256:43aa277543d0a97d4ae46badcb8a19706479168c23651869d99d243ff73ed04a
Pending result / last consumed dispatch: none / disp-release-001
Snapshot capture command: python3 loop/identity.py snapshot loop/manifests/snapshot.json
Snapshot recheck command: python3 loop/identity.py snapshot loop/manifests/snapshot-recheck.json
Snapshot coverage: All regular files and symlinks under `saudi-exchange-mcp/` with sorted relative paths, SHA-256 file bytes, types, executable modes, and symlink targets. Includes source, tests, configuration, lockfiles, protocol files, loop identity tools, and non-secret evidence docs. `BUILD.md` and `SLICES.md` are hashed from their LOOP contract extracts so Proof/Review/Loop-state bookkeeping, Status, Next, run status, release evidence, and Shipped/Now placement do not change snapshot identity.
Snapshot exclusions: `.git/`, `.venv/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `node_modules/`, `.tox/`, `storage/`, `loop/manifests/`, `evidence/live-payloads/`, `HANDOFF.md`, `*.pyc`, `*.pyo`, `.DS_Store`. Manifests are stored outside their own coverage.
Baseline snapshot: sha256:a99c3c9f3c321c6e3a116c4ffc0ce83e41057efd66503b483544dc88b7b5c8b0 file_count=100 path=loop/manifests/snapshot.json
Contract identity: sha256:6b673206c8507506b5d5b53b89204d3a37558524ea0c1daed23de09d114ddaa3 path=loop/manifests/contract.json
Contract identity: sha256:6b673206c8507506b5d5b53b89204d3a37558524ea0c1daed23de09d114ddaa3 path=loop/manifests/contract.json
Candidate snapshot (implementation-approved): sha256:3fd4cb8c7fc8617be28b27490a57c3e35fc538d7db68652298740a5c95316842 file_count=116 path=loop/manifests/candidate.json builder=bc-cc146335-86c4-58e8-840c-bc0c8b627a0e
Release candidate snapshot (post-archive): sha256:43aa277543d0a97d4ae46badcb8a19706479168c23651869d99d243ff73ed04a file_count=117 path=loop/manifests/candidate-post-archive.json. Coordinator-computed delta versus the implementation-approved snapshot: added covered file `slices/05-hybrid-mcp.md` only; no other covered path changed. Application code/tests/evidence under `src/`, `tests/`, and `evidence/05-hybrid-mcp/` are unchanged from APPROVE_IMPLEMENTATION.
Rejection count: 0
Consecutive no-progress repairs: 0
Open acceptance gaps / prior failing evidence: none
Repair awaiting review: false
Review events:
- event=rev-05-impl-001 dispatch=disp-05-impl-review-001 phase=implementation-review verdict=APPROVE_IMPLEMENTATION reviewer=bc-cbb75edc-d8c4-5121-9eff-9852c0b2df98 contract=sha256:6b673206c8507506b5d5b53b89204d3a37558524ea0c1daed23de09d114ddaa3 snapshot_before=sha256:3fd4cb8c7fc8617be28b27490a57c3e35fc538d7db68652298740a5c95316842 snapshot_after=sha256:3fd4cb8c7fc8617be28b27490a57c3e35fc538d7db68652298740a5c95316842 gaps=none rejection_count=0 no_progress=0 artifact=loop/manifests/disp-05-impl-review-001-result.md
- event=rev-release-001 dispatch=disp-release-001 phase=release-review verdict=APPROVE_RELEASE reviewer=bc-b0f896e5-a794-56d4-a0cd-613f13187dbd contract=sha256:6b673206c8507506b5d5b53b89204d3a37558524ea0c1daed23de09d114ddaa3 snapshot_before=sha256:43aa277543d0a97d4ae46badcb8a19706479168c23651869d99d243ff73ed04a snapshot_after=sha256:43aa277543d0a97d4ae46badcb8a19706479168c23651869d99d243ff73ed04a gaps=none failed_release_reviews=0 artifact=loop/manifests/disp-release-001-result.md (durable summary is SLICES Release evidence)
Budget limit / consumed / measurement: Not configured; no execution budget was supplied
Blocker / resume status / resume action / recheck condition / deadline: none
Advance phase: complete
Next slice ID / draft: None — target complete

## Status
Shipped

## Next
None — target complete. Hybrid Pilot v0 run status is Complete. BUILD.md remains the slice 05 Shipped receipt. No further Loop work without a newly authorized target or repair.
