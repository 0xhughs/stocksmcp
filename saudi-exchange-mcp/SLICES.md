# Saudi Market Hybrid MCP — product and slices

## Product
One custom MCP server connects an AI assistant to two sources: **Google Finance for broad company research: prices/overview, news, profile/about, earnings, and structured financial statements (income statement, balance sheet, and cash flow)**, and **Saudi Exchange (Tadawul) for official financial statements and reports — القوائم المالية والتقارير**. Reuse and extend the existing Google Finance MCP implementation, adding Saudi Exchange company/report discovery, PDF download, text/table extraction, and page-level evidence. A shared company lookup resolves Arabic/English names and tickers to verified source-specific identifiers. The assistant chooses the appropriate tools and explains the returned evidence; users connect one MCP and ask naturally.

Current release boundary: **Hybrid Pilot v0**, covering broad company lookups, targeted Google Finance section queries, official-report requests, and combined requests for a small, documented sample of Main Market companies. Both branches must work together: name/ticker → relevant Google company sections with source/period/freshness metadata, and name/ticker → report → original PDF → readable evidence → cited answer. A broad company lookup returns a coherent overview of the named sections with explicit coverage/missing-data status; targeted questions fetch the relevant sections. The hybrid scope is included at the user's request; execution of this pilot is authorized. No market-wide coverage promise is made.

## Users and expected requests
The requester researching Saudi-listed companies through an MCP-capable assistant, locally and through user-initiated requests.
- “What is Aramco's price?” → Google Finance quote, currency, quote time, source, and available delay/session information.
- “Tell me about Aramco” → company overview, price/statistics, news, profile/about, earnings, and financial highlights, with links and availability per section.
- “Show Aramco's income statement, balance sheet, and cash flow” → structured Google Finance tables for the requested available periods, clearly labelled as Google-sourced data.
- “Retrieve Aramco's official 2025 financial report PDF” → Saudi Exchange report discovery and original PDF download.
- “Explain the change in operating cash flow” → Google financial figures for the comparison; use original-report notes when needed to substantiate causes, with source/page citations for claims actually derived from PDFs.
- “Give me Aramco's price and summarise its latest results” → Google quote/earnings/financial sections, adding original reports where the request or required evidence warrants them; latest published reporting period is not the quote date.
- Arabic example: “حلّل القوائم المالية لأرامكو، رمز 2222، لعام 2025، وقارن الإيرادات وصافي الربح والتدفقات النقدية بعام 2024، مع ذكر المصادر وأرقام الصفحات.” These years and metrics are examples, not fixed limits.

## Source and evidence
- Entry point: [Saudi Exchange Main Market, Arabic](https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/main-market-watch?locale=ar).
- Discussion, 2026-09-09: the assistant inspected an Aramco company page and observed the Financial Statements and Reports section and annual/quarterly tables. End-to-end PDF retrieval, an official reports API, and automated-access conditions remain **unverified**.
- Reuse candidate: [woodstock-tokyo/google-finance-mcp](https://github.com/woodstock-tokyo/google-finance-mcp), discovered through [MCP Market](https://mcpmarket.com/server/google-finance). Its documentation describes a local stdio server, Google Finance page/quote dataset calls, and website-derived mechanisms whose mappings can change. No fork, installation, code audit, or MCP live test has been performed here.
- The assistant verified that [Google Finance has an Aramco page at 2222:TADAWUL](https://www.google.com/finance/quote/2222:TADAWUL). A further page inspection found news, profile/about details, a populated quarterly income statement, and controls for earnings, balance sheet, and cash flow. The full earnings, balance-sheet, and cash-flow payloads were not verified. Website availability does not prove MCP extraction, full period coverage, or wider Saudi-company support.
- Reviewed [upstream GPL-3.0 license](https://github.com/woodstock-tokyo/google-finance-mcp/blob/master/LICENSE) and [developer usage policy](https://github.com/woodstock-tokyo/google-finance-mcp/blob/master/LEGAL.md). Preserve applicable notices and distinguish code-license obligations from source-data rights. The developer describes local, personal, user-initiated use and excludes hosted/bulk/redistribution use. Re-check current documents before implementation and any distribution.
- [MCP tool specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) supports exposing retrieval tools. Verify the applicable SDK/specification during implementation.
- For comparison, [Aramco official report downloads](https://www.aramco.com/en/investors/annual-report/downloads) include full financial statements and additional report sections. The [2025 full financials](https://www.aramco.com/-/media/publications/corporate-reports/reports-and-presentations/2025/fy/saudi-aramco-fy-2025-full-financials-english.pdf) include notes and auditor material. These sources explain why summary tables need not replace original disclosures; they do not authorize silently substituting another discovery source for Saudi Exchange.
- No application implementation exists in this workspace. The exported folder/ZIP retain their original `saudi-exchange-reports-mcp` names for continuity; the product inside is now the hybrid MCP.

## Product principles and integration boundary
- Share company identity across sources; keep Google identifiers and Saudi Exchange report identifiers distinct and verified.
- Expose clear capabilities for shared lookup, overview/quotes/statistics, news, profile/about, earnings, the three financial statements, report listing/download, and document reading/search. Google Finance is primary for everyday company questions and structured financial comparisons; Saudi Exchange supplies requested official PDFs, notes, and original evidence for gaps or verification. Fetch relevant sections on demand; a broad company lookup assembles the overview with explicit coverage. These are proposed capabilities, not implemented names or schemas.
- Attribute each fact/table to its actual source. News carries publisher/date/article links and distinguishes snippets from articles read. Financial tables preserve labels, units, currencies, reporting periods, and actual-versus-estimate distinctions. Only PDF-derived facts have PDF page references. Do not replace requested official filings with Google summaries or silently merge conflicting figures.
- Keep report period/publication date separate from quote/retrieval time. Display missing timestamp, delay, or extraction metadata explicitly; never infer real-time freshness.
- Cache Saudi report PDFs with provenance and version checks. Handle Google market responses transiently under applicable conditions; never inherit the PDF cache policy for quote data or bundle live Google responses in fixtures/exports.
- Keep provider integrations separate. A source outage may yield an explicit partial answer, but cannot silently switch provenance or satisfy an unfulfilled release gate.
- Reuse upstream code through a documented, revision-pinned fork/integration. Inspect before execution, preserve notices, and avoid exposing unrelated upstream features merely because they exist. The user explicitly broadened scope beyond prices to most company-page information. Inventory available public sections and dataset coverage, including all named core sections, before claiming completeness. The Google Finance AI chat, private portfolios/watchlists, account automation, and trading are not part of this data-retrieval product.

## Loop target
**Confirmed target: Hybrid Pilot v0, through slice 05 — One MCP for company research and official reports.** Slices 01–05 are inside this target. Stop after independent acceptance and final release verification; broader coverage remains outside it.
**Authority:** User instruction dated 2026-09-09 authorized execution of this confirmed target, including Google Finance company research and Saudi Exchange official-report retrieval. No background execution, deployment, publishing, purchases, or work outside this target is authorized.

## Run status
Complete

## Open decisions
- Resolved 2026-09-09: Hybrid Pilot v0 through slice 05 is the confirmed execution target. Release validation host: a local stdio MCP server exercised through an in-workspace MCP client, with Cursor MCP install documented. Ordinary design choices do not require reconfirmation.
- During slice 01: establish a permitted, reliable report-retrieval route and document pilot companies/periods from actual evidence. Aramco is a concrete first candidate from the discussion; sample size is not prescribed.
- During slices 03–04: choose and record the upstream revision, inspect the source and current license/policy, inventory the public company sections, and prove Saudi overview/news/profile/earnings/financial retrieval through the reused integration. Resolve incompatibilities with the intended integration before relying on it; do not claim the code license grants data rights.
- Choose runtime, SDK, integration packaging, report storage, and extraction/OCR libraries from repository evidence and official documentation. The reuse candidate uses Python/stdio, but compatibility of the final package still needs verification. Do not introduce paid services or credentials without existing authority.
- Source simplification remains an open product choice: the user asked whether Google alone would be enough; removing Saudi Exchange was not instructed. Keep official-report capability in this pack. A later Google-only release could be scoped after coverage/accuracy checks and a user decision; do not silently drop PDF requirements.
- No latency target, execution budget, streaming requirement, scheduled monitoring, commercial distribution, or public hosting was supplied. Pilot use is local and user-initiated.

## Release gates
- Independent Reviewer verifies all target slices are accepted and approvals/evidence apply to the final candidate.
- Through a single installed MCP connection in the chosen host, demonstrate a broad company lookup, targeted overview/news/profile/earnings/financial prompts, official-report requests, and combined prompts using the documented Saudi pilot sample, including Aramco. Verify Arabic/English company inputs and correct exchange/source mappings.
- For a real Google Finance quote through the reused code, confirm company/ticker, price, currency, source, and available quote-time/delay metadata. Label unknown freshness and distinguish live source checks from synthetic fixture checks. Preserve test commands/outcomes without committing or exporting live Google response payloads.
- Verify news publisher/link/time provenance, profile/about fields, earnings actuals versus estimates, and readable income-statement/balance-sheet/cash-flow tables with period/currency/scale metadata. Validate all named sections through MCP rather than merely observing website tabs. Record coverage by company/section/period, including missing fields, and reproduce representative Google figures against original disclosures without saving live Google payloads. An upstream gap in a required category needs implementation or an explicit scope decision, not silent release acceptance.
- Demonstrate source-to-original-PDF retrieval, Arabic/English report reading, annual/interim distinctions, and answers citing the actual reports/pages. Reconcile representative figures, currency/scale, period duration, and revisions with PDF evidence.
- Verify report cache/version behavior; ambiguous/conflicting identity; missing reports; unavailable Google sections/quotes; invalid/partial PDFs; uncertain extraction; source isolation; and explicit partial results for mixed requests. Both live branches must pass for release, even though partial responses are supported at runtime.
- Inspect boundary validation and untrusted document/response handling. Confirm the Google branch does not use the report archive, uncontrolled background polling, or source-bypass behavior.
- Document one-client installation, chosen upstream revision/reuse notices, source-specific data handling, tested coverage, limitations, and repeatable checks. Public deployment, continuous price feeds, and investment recommendations are not release gates.

## Release evidence
Now: None — target complete (Now section body empty; mapped slice 05 criteria preserved under Later so contract identity is unchanged).
Verdict: APPROVE_RELEASE disp-release-001. Coordinator independently recomputed contract sha256:6b673206c8507506b5d5b53b89204d3a37558524ea0c1daed23de09d114ddaa3 and post-archive candidate sha256:43aa277543d0a97d4ae46badcb8a19706479168c23651869d99d243ff73ed04a (file_count=117) before applying this result; they matched the Reviewer before/after identities and the dispatch inputs. Implementation-approved candidate sha256:3fd4cb8c7fc8617be28b27490a57c3e35fc538d7db68652298740a5c95316842 (file_count=116); proven covered delta is `slices/05-hybrid-mcp.md` only. Reviewer bc-b0f896e5-a794-56d4-a0cd-613f13187dbd (Cursor Grok 4.6) did not edit the candidate.
Live proof (field-presence only; no live Google bodies in git): one stdio connection to `python -m saudi_exchange_reports.mcp` (initialize, tools/list, tools/call). Default pytest 178 passed, 7 skipped. Live `tests/test_mcp_live.py` 1 passed. Independent live session with `SAUDI_MCP_USE_BROWSER=1`: Arabic/English Aramco lookup matched `2222:TADAWUL`; `2222:SAU` not_found; Google overview/news/profile/earnings/IS through MCP; BS/CF retrieved with `display_label_gap`; live Saudi listing 44 reports after urllib AJAX 500; Maaden original PDF hash `d76aaa7c371da4a0c3a23edbfb0663339590bfa959e1c8396350bf27dcc6767e` read/searched via MCP (notes p.19 native). Combined Google+Saudi calls on the same connection with separate provenance. Artifact: `loop/manifests/disp-release-001-result.md` (gitignored; summary here is the durable git record).
Failed release reviews for this target: 0
Pending release result: none
Release review events / last consumed dispatch:
- event=rev-release-001 dispatch=disp-release-001 phase=release-review verdict=APPROVE_RELEASE reviewer=bc-b0f896e5-a794-56d4-a0cd-613f13187dbd contract=sha256:6b673206c8507506b5d5b53b89204d3a37558524ea0c1daed23de09d114ddaa3 snapshot_before=sha256:43aa277543d0a97d4ae46badcb8a19706479168c23651869d99d243ff73ed04a snapshot_after=sha256:43aa277543d0a97d4ae46badcb8a19706479168c23651869d99d243ff73ed04a gaps=none failed_release_reviews=0 artifact=loop/manifests/disp-release-001-result.md
Last consumed dispatch: disp-release-001

## Shipped
- 01 — Company report discovery and original-PDF retrieval — accepted archive: [slices/01-report-retrieval.md](slices/01-report-retrieval.md). Implementation approval disp-01-impl-review-002, contract sha256:122bc93b0de9d398055a464ad8bfdc933849c80890e0d8285db244d57e23fe91, candidate sha256:e68c89956ab1f6f6e3dfb7039faea45e1e3fee82ed91aa3d4d028c6b158358fe.
- 02 — Read financial reports with page-level evidence — accepted archive: [slices/02-report-reading.md](slices/02-report-reading.md). Implementation approval disp-02-impl-review-001, contract sha256:f8a3e87ed9c9bc004d6b14453ce00803ace0b153d0d5f30214f12ead00faf0fc, candidate sha256:2b288e8d6bad89c4e30336461f5a0066c2812d09edda26a1fb90873b675deaed.

- 03 — Google Finance overview, profile, and news — accepted archive: [slices/03-google-overview.md](slices/03-google-overview.md). Implementation approval disp-03-impl-review-001, contract sha256:b522f4b19a789dcacf99aebdfe72d36e5cabd5ef70e7bd874407f599751e9576, candidate sha256:17b18ff14d853aef4eae735ec45700222eb13c01eddd0063642d1f47eb4a481c.

- 04 — Google Finance earnings and financial statements — accepted archive: [slices/04-google-financials.md](slices/04-google-financials.md). Implementation approval disp-04-impl-review-001, contract sha256:97f9abe0ef503d05119497d8d10ffc182a183fbe56d690a5681a199232feda91, candidate sha256:bb6fd783940ad104932c4345411c449f28131f21b11f88624dee2d1da02b6352.

- 05 — One MCP for company research and official reports — accepted archive: [slices/05-hybrid-mcp.md](slices/05-hybrid-mcp.md). Implementation approval disp-05-impl-review-001, contract sha256:6b673206c8507506b5d5b53b89204d3a37558524ea0c1daed23de09d114ddaa3, candidate sha256:3fd4cb8c7fc8617be28b27490a57c3e35fc538d7db68652298740a5c95316842.

## Now
## Later
### 05 — One MCP for company research and official reports
Goal: expose shared lookup, overview/quotes, news, profile/about, earnings, income statement/balance sheet/cash flow, and original-report retrieval/reading through one MCP connection, with correct source selection and cited answers.
Provides: host installation, clear tool contracts/descriptions, broad-company, targeted-section, official-report, and combined prompt demonstrations, separate provenance, explicit partial-source failures, pilot end-to-end proof, and final release verification. The host assistant composes analysis; a separate server-side model is not required.
Depends on: 01, 02, 03, and 04.
Target membership: inside Hybrid Pilot v0; final target slice.
Out: deployment, public multi-user service, continuous monitoring, trading, or treating pilot coverage as full-market coverage.
Contract: [BUILD.md](BUILD.md). Future accepted archive: `slices/05-hybrid-mcp.md` (not created yet).

### 01 — Company report discovery and original-PDF retrieval (accepted)
Goal: turn a company name/ticker and report period into a verified original financial-report PDF with provenance.
Provides: shared company identity with distinct source identifiers, observed Saudi retrieval route, documented pilot coverage, report selection, bounded local PDF download/cache, and real-report evidence.
Depends on: none; execution authority and target confirmation are recorded.
Target membership: inside Hybrid Pilot v0.
Out: content interpretation, Google Finance quote integration, MCP host wiring, market-wide collection.
Contract: accepted archive [slices/01-report-retrieval.md](slices/01-report-retrieval.md).

### 02 — Read financial reports with page-level evidence (accepted)
Goal: make downloaded reports searchable/readable as text and tables, retaining PDF page provenance and financial metadata.
Provides: Arabic/English extraction, OCR fallback where needed, uncertain/missing-data handling, and representative checks of values, units, periods, and restatements.
Depends on: 01.
Target membership: inside Hybrid Pilot v0.
Out: quote retrieval, MCP host wiring, investment advice, universal automatic financial-statement normalization.
Contract: accepted archive [slices/02-report-reading.md](slices/02-report-reading.md).

### 03 — Google Finance overview, profile, and news (accepted)
Goal: reuse the existing Google Finance MCP code for a verified Saudi-company overview with quotes/statistics, profile/about, and relevant news through shared company identity.
Provides: inspected/revision-pinned integration, preserved notices, verified ticker/exchange mappings, live Aramco coverage, quote/freshness metadata, news publisher/link/time, profile fields, and public-section coverage inventory. Use synthetic fixtures and transient live checks; hide changing source dataset details behind clear capabilities.
Depends on: 01 for shared identity; report extraction in 02 is not a technical dependency.
Target membership: inside Hybrid Pilot v0.
Out: financial-table parsing in 04, report parsing, private accounts, persistent Google payload archives, hosted service, streaming/polling, trading, and silent source substitution.
Contract: accepted archive [slices/03-google-overview.md](slices/03-google-overview.md).

### 04 — Google Finance earnings and financial statements (accepted)
Goal: retrieve and interpret the available earnings, income-statement, balance-sheet, and cash-flow datasets for Saudi companies through the reused integration.
Provides: verified field meanings and actual-versus-estimate labels, annual/quarterly periods where available, units/currency, original labels/values, explicit coverage/gaps, and meaningful comparisons. Prove representative figures against source displays and official PDFs; document missing history and discrepancies rather than guessing field positions or combining incompatible data.
Depends on: 03 for the Google integration and 02 for original-report cross-check evidence.
Target membership: inside Hybrid Pilot v0.
Out: representing Google tables as audited PDF originals, exhaustive coverage claims, invented figures, unrelated AI chat/account functions, or persistent Google response warehousing.
Contract: accepted archive [slices/04-google-financials.md](slices/04-google-financials.md).

### Future consideration — Broader company and historical coverage
Goal: extend beyond the pilot if later requested and access/reliability evidence supports it.
Depends on: accepted Hybrid Pilot v0 and a newly authorized scope/target.
Target membership: outside; a possibility discussed, not a committed release.
Out: automatic execution after slice 05, or inferring permission for Google market-data warehousing from historical-report research.
